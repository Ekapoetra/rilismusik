"""Global label-balance audit and source-of-truth reconciliation."""
import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from models import new_id, now_iso
from .balance_utils import compute_label_balance_snapshot
from .deps import db, db_bg, log_activity, logger, require_admin
from .royalty_recalculation import trigger_royalty_caches


balance_audit_r = APIRouter(prefix="/admin/balance-audit", tags=["balance-audit"])
FINANCE_ROLES = ("super_admin", "admin_finance")
ACTIVE_JOB_STATUSES = ["queued", "processing"]


class BalanceAuditCommitIn(BaseModel):
    preview_job_id: str = Field(..., min_length=1, max_length=100)


class BalanceAuditPreviewIn(BaseModel):
    label_ids: Optional[List[str]] = Field(default=None, max_length=1000)


def _require_finance(user: dict) -> None:
    if user.get("role") not in FINANCE_ROLES:
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")


def _empty_row(label: dict, active_amount: int, active_ids: List[str]) -> Dict[str, Any]:
    return {
        "label_id": label["id"],
        "label_name": label.get("label_name") or "—",
        "last_withdrawn_period": label.get("last_withdrawn_period"),
        "latest_report_period": None,
        "eligible_period_from": None,
        "eligible_period_to": None,
        "eligible_pending_lines": 0,
        "eligible_available_lines": 0,
        "stale_cutoff_lines": 0,
        "stale_cutoff_idr": 0,
        "current_pending_idr": int(label.get("balance_pending_idr") or 0),
        "current_available_idr": int(label.get("balance_available_idr") or 0),
        "current_requested_idr": int(label.get("balance_withdraw_requested_idr") or 0),
        "expected_pending_idr": 0,
        "expected_available_source_idr": 0,
        "expected_available_idr": 0,
        "expected_requested_idr": max(active_amount, 0),
        "active_withdraw_ids": active_ids,
        "has_active_withdraw": bool(active_ids),
    }


def _finalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    row["expected_pending_idr"] = max(int(row["expected_pending_idr"]), 0)
    row["expected_available_source_idr"] = max(int(row["expected_available_source_idr"]), 0)
    row["expected_available_idr"] = max(
        row["expected_available_source_idr"] - row["expected_requested_idr"], 0,
    )
    row["pending_delta_idr"] = row["expected_pending_idr"] - row["current_pending_idr"]
    row["available_delta_idr"] = row["expected_available_idr"] - row["current_available_idr"]
    row["requested_delta_idr"] = row["expected_requested_idr"] - row["current_requested_idr"]
    row["has_drift"] = any((
        row["pending_delta_idr"], row["available_delta_idr"], row["requested_delta_idr"],
        row["stale_cutoff_lines"],
    ))
    row["audit_status"] = (
        "blocked_active_withdraw" if row["has_active_withdraw"]
        else "drift" if row["has_drift"]
        else "clean"
    )
    return row


async def _active_job(kind: str) -> Optional[dict]:
    return await db.migrate_jobs.find_one(
        {"kind": kind, "status": {"$in": ACTIVE_JOB_STATUSES}}, {"_id": 0},
    )


@balance_audit_r.post("/preview")
async def start_balance_audit(
    body: Optional[BalanceAuditPreviewIn] = None,
    user: dict = Depends(require_admin),
):
    _require_finance(user)
    existing = await _active_job("balance_audit_preview")
    if existing:
        return {"job_id": existing["id"], "status": existing["status"], "already_running": True}
    job_id = new_id()
    submitted_at = now_iso()
    await db_bg.migrate_jobs.insert_one({
        "id": job_id,
        "kind": "balance_audit_preview",
        "status": "queued",
        "submitted_by": user["id"],
        "submitted_at": submitted_at,
        "updated_at": submitted_at,
        "progress_labels_done": 0,
        "progress_labels_total": 0,
        "phase": "queued",
        "scope_label_ids": body.label_ids if body else None,
    })
    asyncio.create_task(_run_balance_audit_preview(
        job_id=job_id, label_ids=body.label_ids if body else None,
    ))
    return {"job_id": job_id, "status": "queued", "already_running": False}


@balance_audit_r.get("/jobs/{job_id}")
async def get_balance_audit_job(job_id: str, user: dict = Depends(require_admin)):
    _require_finance(user)
    job = await db.migrate_jobs.find_one(
        {"id": job_id, "kind": {"$in": ["balance_audit_preview", "balance_reconcile"]}},
        {"_id": 0},
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job audit saldo tidak ditemukan")
    return job


@balance_audit_r.get("/jobs/{job_id}/rows")
async def get_balance_audit_rows(
    job_id: str,
    user: dict = Depends(require_admin),
    status: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
):
    _require_finance(user)
    query: Dict[str, Any] = {"job_id": job_id}
    if status:
        query["audit_status"] = status
    if search:
        query["label_name"] = {"$regex": search, "$options": "i"}
    total = await db.balance_audit_rows.count_documents(query)
    rows = await db.balance_audit_rows.find(query, {"_id": 0}).sort([
        ("has_drift", -1), ("label_name", 1),
    ]).skip((page - 1) * limit).limit(limit).to_list(limit)
    return {"items": rows, "total": total, "page": page, "limit": limit}


@balance_audit_r.post("/commit")
async def commit_balance_reconciliation(body: BalanceAuditCommitIn, user: dict = Depends(require_admin)):
    _require_finance(user)
    preview = await db.migrate_jobs.find_one(
        {"id": body.preview_job_id, "kind": "balance_audit_preview"}, {"_id": 0},
    )
    if not preview or preview.get("status") != "done":
        raise HTTPException(status_code=400, detail="Preview audit harus selesai terlebih dahulu")
    if preview.get("commit_job_id"):
        current = await db.migrate_jobs.find_one({"id": preview["commit_job_id"]}, {"_id": 0, "status": 1})
        return {"job_id": preview["commit_job_id"], "status": (current or {}).get("status"), "already_started": True}
    active_import = await db.royalty_imports.find_one({
        "status": {"$in": ["processing", "publishing", "receiving", "deleting"]},
    }, {"_id": 0, "id": 1, "status": 1})
    if active_import:
        raise HTTPException(status_code=409, detail="Tunggu proses import/penerimaan royalti aktif selesai")
    active_recalc = await db.migrate_jobs.find_one({
        "kind": {"$in": ["recalculate_label_unwithdrawn", "recalculate_all_unwithdrawn", "label_rate_sync"]},
        "status": {"$in": ACTIVE_JOB_STATUSES},
    }, {"_id": 0, "id": 1})
    if active_recalc:
        raise HTTPException(status_code=409, detail="Tunggu recalculation rate aktif selesai")

    job_id = new_id()
    queued_at = now_iso()
    claimed = await db_bg.migrate_jobs.update_one(
        {"id": body.preview_job_id, "kind": "balance_audit_preview", "commit_job_id": {"$exists": False}},
        {"$set": {"commit_job_id": job_id, "updated_at": queued_at}},
    )
    if claimed.modified_count != 1:
        refreshed = await db.migrate_jobs.find_one({"id": body.preview_job_id}, {"_id": 0, "commit_job_id": 1})
        return {"job_id": (refreshed or {}).get("commit_job_id"), "status": "queued", "already_started": True}
    total = await db.balance_audit_rows.count_documents({
        "job_id": body.preview_job_id,
        "has_drift": True,
        "has_active_withdraw": False,
    })
    await db_bg.migrate_jobs.insert_one({
        "id": job_id,
        "kind": "balance_reconcile",
        "preview_job_id": body.preview_job_id,
        "status": "queued",
        "submitted_by": user["id"],
        "submitted_at": queued_at,
        "updated_at": queued_at,
        "progress_labels_done": 0,
        "progress_labels_total": total,
        "phase": "queued",
    })
    asyncio.create_task(_run_balance_reconciliation(
        job_id=job_id, preview_job_id=body.preview_job_id, user_id=user["id"],
    ))
    return {"job_id": job_id, "status": "queued", "already_started": False}


async def _run_balance_audit_preview(*, job_id: str, label_ids: Optional[List[str]] = None) -> None:
    try:
        await db_bg.migrate_jobs.update_one(
            {"id": job_id}, {"$set": {"status": "processing", "phase": "loading_labels", "started_at": now_iso(), "updated_at": now_iso()}},
        )
        label_query: Dict[str, Any] = {"id": {"$in": label_ids}} if label_ids is not None else {}
        labels = await db_bg.labels.find(label_query, {
            "_id": 0, "id": 1, "label_name": 1, "last_withdrawn_period": 1,
            "balance_pending_idr": 1, "balance_available_idr": 1,
            "balance_withdraw_requested_idr": 1,
        }).to_list(20000)
        active_by_label: Dict[str, Dict[str, Any]] = {}
        async for withdraw in db_bg.withdraw_requests.find({
            "status": {"$in": ["requested", "approved"]}, "legacy_import": {"$ne": True},
        }, {"_id": 0, "id": 1, "label_id": 1, "amount_idr": 1}):
            bucket = active_by_label.setdefault(withdraw["label_id"], {"amount": 0, "ids": []})
            bucket["amount"] += int(withdraw.get("amount_idr") or 0)
            bucket["ids"].append(withdraw["id"])
        rows_by_label = {
            label["id"]: _empty_row(
                label,
                active_by_label.get(label["id"], {}).get("amount", 0),
                active_by_label.get(label["id"], {}).get("ids", []),
            ) for label in labels
        }
        await db_bg.balance_audit_rows.delete_many({"job_id": job_id})
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {"phase": "aggregating_royalty_lines", "progress_labels_total": len(labels), "updated_at": now_iso()}},
        )
        pipeline = [
            {"$match": {
                "label_id": {"$in": label_ids} if label_ids is not None else {"$ne": None},
                "period": {"$type": "string"},
                "status": {"$in": ["draft", "pending", "available", "withdrawn"]},
            }},
            {"$group": {
                "_id": {
                    "label_id": "$label_id",
                    "period": "$period",
                    "status": "$status",
                    "legacy_settled": {"$eq": ["$legacy_settled", True]},
                },
                "amount_idr": {"$sum": "$label_idr"},
                "lines_count": {"$sum": 1},
            }},
        ]
        async for grouped in db_bg.royalty_lines.aggregate(pipeline, allowDiskUse=True):
            key = grouped["_id"]
            row = rows_by_label.get(key["label_id"])
            if not row:
                continue
            period = key["period"]
            status = key["status"]
            amount = int(grouped.get("amount_idr") or 0)
            count = int(grouped.get("lines_count") or 0)
            if not row["latest_report_period"] or period > row["latest_report_period"]:
                row["latest_report_period"] = period
            if key["legacy_settled"]:
                continue
            cutoff = row["last_withdrawn_period"]
            if cutoff and period <= cutoff and status in ("draft", "pending", "available"):
                row["stale_cutoff_lines"] += count
                row["stale_cutoff_idr"] += amount
                continue
            if status not in ("pending", "available"):
                continue
            if not row["eligible_period_from"] or period < row["eligible_period_from"]:
                row["eligible_period_from"] = period
            if not row["eligible_period_to"] or period > row["eligible_period_to"]:
                row["eligible_period_to"] = period
            if status == "pending":
                row["expected_pending_idr"] += amount
                row["eligible_pending_lines"] += count
            else:
                row["expected_available_source_idr"] += amount
                row["eligible_available_lines"] += count

        rows = [_finalize_row(row) for row in rows_by_label.values()]
        summary = {
            "total_labels": len(rows),
            "drift_labels": sum(1 for row in rows if row["has_drift"] and not row["has_active_withdraw"]),
            "clean_labels": sum(1 for row in rows if not row["has_drift"]),
            "blocked_active_withdraw": sum(1 for row in rows if row["has_active_withdraw"]),
            "negative_balance_labels": sum(1 for row in rows if row["current_pending_idr"] < 0 or row["current_available_idr"] < 0),
            "stale_cutoff_lines": sum(row["stale_cutoff_lines"] for row in rows),
            "pending_delta_idr": sum(row["pending_delta_idr"] for row in rows if not row["has_active_withdraw"]),
            "available_delta_idr": sum(row["available_delta_idr"] for row in rows if not row["has_active_withdraw"]),
        }
        for start in range(0, len(rows), 500):
            docs = [{"id": new_id(), "job_id": job_id, **row} for row in rows[start:start + 500]]
            if docs:
                await db_bg.balance_audit_rows.insert_many(docs, ordered=False)
            await db_bg.migrate_jobs.update_one(
                {"id": job_id},
                {"$set": {"progress_labels_done": min(start + 500, len(rows)), "phase": "saving_preview", "updated_at": now_iso()}},
            )
        finished_at = now_iso()
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "done", "phase": "done", "summary": summary, "finished_at": finished_at, "updated_at": finished_at}},
        )
    except Exception as exc:
        logger.exception("[BALANCE AUDIT] preview job=%s failed: %s", job_id, exc)
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "error", "error_message": f"{type(exc).__name__}: {str(exc)[:400]}", "finished_at": now_iso(), "updated_at": now_iso()}},
        )


async def _flip_stale_cutoff_lines(*, label_id: str, cutoff: Optional[str]) -> int:
    if not cutoff:
        return 0
    total = 0
    last_oid = None
    while True:
        query: Dict[str, Any] = {
            "label_id": label_id,
            "status": {"$in": ["draft", "pending", "available"]},
            "legacy_settled": {"$ne": True},
            "period": {"$lte": cutoff},
        }
        if last_oid is not None:
            query["_id"] = {"$gt": last_oid}
        batch = await db_bg.royalty_lines.find(query, {"_id": 1}).sort("_id", 1).limit(5000).to_list(5000)
        if not batch:
            break
        object_ids = [item["_id"] for item in batch]
        last_oid = object_ids[-1]
        result = await db_bg.royalty_lines.update_many(
            {"_id": {"$in": object_ids}},
            {"$set": {"status": "withdrawn", "settled_by_balance_reconciliation": True, "settled_at": now_iso()}},
        )
        total += result.modified_count
    return total


async def _run_balance_reconciliation(*, job_id: str, preview_job_id: str, user_id: str) -> None:
    totals = {
        "labels_reconciled": 0,
        "labels_clean_after_recheck": 0,
        "labels_skipped_active_withdraw": 0,
        "labels_failed": 0,
        "stale_lines_settled": 0,
        "pending_adjustment_idr": 0,
        "available_adjustment_idr": 0,
        "requested_adjustment_idr": 0,
    }
    try:
        await db_bg.migrate_jobs.update_one(
            {"id": job_id}, {"$set": {"status": "processing", "phase": "reconciling", "started_at": now_iso(), "updated_at": now_iso()}},
        )
        rows = await db_bg.balance_audit_rows.find({
            "job_id": preview_job_id,
            "has_drift": True,
            "has_active_withdraw": False,
            "apply_status": {"$ne": "done"},
        }, {"_id": 0}).sort("label_name", 1).to_list(20000)
        for index, audit_row in enumerate(rows, start=1):
            label_id = audit_row["label_id"]
            try:
                label = await db_bg.labels.find_one({"id": label_id}, {"_id": 0})
                if not label:
                    raise RuntimeError("Label tidak ditemukan")
                snapshot_before = await compute_label_balance_snapshot(label_id=label_id, label=label)
                if snapshot_before["has_active_withdraw"]:
                    totals["labels_skipped_active_withdraw"] += 1
                    await db_bg.balance_audit_rows.update_one(
                        {"job_id": preview_job_id, "label_id": label_id},
                        {"$set": {"apply_status": "blocked_active_withdraw", "apply_message": "Withdraw aktif muncul setelah preview"}},
                    )
                    continue
                settled = await _flip_stale_cutoff_lines(
                    label_id=label_id, cutoff=label.get("last_withdrawn_period"),
                )
                snapshot = await compute_label_balance_snapshot(label_id=label_id, label=label)
                expected = {
                    "balance_pending_idr": max(snapshot["balance_pending_idr"], 0),
                    "balance_available_idr": max(snapshot["balance_available_idr"], 0),
                    "balance_withdraw_requested_idr": 0,
                }
                current = {
                    "balance_pending_idr": int(label.get("balance_pending_idr") or 0),
                    "balance_available_idr": int(label.get("balance_available_idr") or 0),
                    "balance_withdraw_requested_idr": int(label.get("balance_withdraw_requested_idr") or 0),
                }
                deltas = {field: expected[field] - current[field] for field in expected}
                if not any(deltas.values()) and not settled:
                    totals["labels_clean_after_recheck"] += 1
                else:
                    reconciled_at = now_iso()
                    await db_bg.labels.update_one(
                        {"id": label_id},
                        {"$set": {
                            **expected,
                            "balance_last_reconciled_at": reconciled_at,
                            "balance_reconciliation_job_id": job_id,
                            "balance_source": "royalty_lines_fifo",
                            "updated_at": reconciled_at,
                        }},
                    )
                    totals["labels_reconciled"] += 1
                    totals["stale_lines_settled"] += settled
                    totals["pending_adjustment_idr"] += deltas["balance_pending_idr"]
                    totals["available_adjustment_idr"] += deltas["balance_available_idr"]
                    totals["requested_adjustment_idr"] += deltas["balance_withdraw_requested_idr"]
                    for field, delta in deltas.items():
                        if not delta:
                            continue
                        bucket = field.replace("balance_", "").replace("_idr", "")
                        await db_bg.balance_transactions.update_one(
                            {"id": f"balance-reconcile:{job_id}:{label_id}:{bucket}"},
                            {"$setOnInsert": {
                                "id": f"balance-reconcile:{job_id}:{label_id}:{bucket}",
                                "label_id": label_id,
                                "type": "balance_reconciliation",
                                "balance_bucket": bucket,
                                "amount_idr": delta,
                                "reference_type": "balance_reconciliation",
                                "reference_id": job_id,
                                "description": f"Rekonsiliasi saldo FIFO setelah withdraw {label.get('last_withdrawn_period') or 'belum ada'}",
                                "created_at": reconciled_at,
                            }},
                            upsert=True,
                        )
                await db_bg.balance_audit_rows.update_one(
                    {"job_id": preview_job_id, "label_id": label_id},
                    {"$set": {"apply_status": "done", "applied_job_id": job_id, "applied_at": now_iso(), "applied_balances": expected}},
                )
            except Exception as exc:
                totals["labels_failed"] += 1
                logger.exception("[BALANCE RECONCILE] label=%s failed: %s", label_id, exc)
                await db_bg.balance_audit_rows.update_one(
                    {"job_id": preview_job_id, "label_id": label_id},
                    {"$set": {"apply_status": "error", "apply_message": f"{type(exc).__name__}: {str(exc)[:240]}"}},
                )
            finally:
                await db_bg.migrate_jobs.update_one(
                    {"id": job_id},
                    {"$set": {"progress_labels_done": index, "updated_at": now_iso()}},
                )
        final_status = "done_with_errors" if totals["labels_failed"] else "done"
        finished_at = now_iso()
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": final_status, "phase": "done", "result": totals, "finished_at": finished_at, "updated_at": finished_at}},
        )
        await log_activity(user_id, "reconcile_all_label_balances", "label", None, after=totals)
        await trigger_royalty_caches()
    except Exception as exc:
        logger.exception("[BALANCE RECONCILE] job=%s failed: %s", job_id, exc)
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "error", "error_message": f"{type(exc).__name__}: {str(exc)[:400]}", "finished_at": now_iso(), "updated_at": now_iso()}},
        )


async def resume_balance_audit_jobs() -> None:
    jobs = await db_bg.migrate_jobs.find({
        "kind": {"$in": ["balance_audit_preview", "balance_reconcile"]},
        "status": {"$in": ACTIVE_JOB_STATUSES},
    }, {"_id": 0, "id": 1, "kind": 1, "preview_job_id": 1, "submitted_by": 1, "scope_label_ids": 1}).to_list(10)
    for job in jobs:
        if job["kind"] == "balance_audit_preview":
            asyncio.create_task(_run_balance_audit_preview(
                job_id=job["id"], label_ids=job.get("scope_label_ids"),
            ))
        elif job.get("preview_job_id"):
            asyncio.create_task(_run_balance_reconciliation(
                job_id=job["id"],
                preview_job_id=job["preview_job_id"],
                user_id=job.get("submitted_by") or "system",
            ))