"""Global label-balance audit and source-of-truth reconciliation."""
import asyncio
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from models import new_id, now_iso
from .balance_utils import compute_label_balance_snapshot
from .deps import db, db_bg, log_activity, logger, require_admin
from .royalty_recalculation import (
    close_stale_recalculation_jobs,
    recalculate_label_unwithdrawn,
    trigger_royalty_caches,
)


balance_audit_r = APIRouter(prefix="/admin/balance-audit", tags=["balance-audit"])
FINANCE_ROLES = ("super_admin", "admin_finance")
ACTIVE_JOB_STATUSES = ["queued", "processing"]
KNOWN_LINE_STATUSES = {"draft", "pending", "available", "withdrawn"}


class BalanceAuditCommitIn(BaseModel):
    preview_job_id: str = Field(..., min_length=1, max_length=100)


class BalanceAuditPreviewIn(BaseModel):
    label_ids: Optional[List[str]] = Field(default=None, max_length=1000)


def _diagnostic_classification(
    *, status: str, legacy_settled: bool, period: str, period_type: str,
    cutoff: Optional[str], import_status: Optional[str],
) -> str:
    if period_type != "string" or not re.fullmatch(r"\d{4}-\d{2}", period or ""):
        return "periode_tidak_valid"
    after_cutoff = not cutoff or period > cutoff
    if after_cutoff and (status == "withdrawn" or legacy_settled):
        return "keliru_dianggap_sudah_dibayar"
    if cutoff and period <= cutoff:
        return "riwayat_sebelum_batas_tarik"
    if status not in KNOWN_LINE_STATUSES:
        return "status_tidak_dikenal"
    if import_status == "dana_received" and status in ("draft", "pending"):
        return "belum_mengikuti_laporan_diterima"
    if import_status == "published" and status == "draft":
        return "belum_mengikuti_laporan_terbit"
    if status in ("pending", "available"):
        return "aktif_dalam_saldo"
    if status == "draft":
        return "draft_laporan_belum_terbit"
    return "lainnya"


def _require_finance(user: dict) -> None:
    if user.get("role") not in FINANCE_ROLES:
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")


def _max_period(*values: Optional[str]) -> Optional[str]:
    valid = [value for value in values if value]
    return max(valid) if valid else None


def _empty_row(
    label: dict,
    active_amount: int,
    active_ids: List[str],
    paid_period_to: Optional[str],
    paid_missing_period_count: int,
) -> Dict[str, Any]:
    label_cutoff = label.get("last_withdrawn_period")
    effective_cutoff = _max_period(label_cutoff, paid_period_to)
    return {
        "label_id": label["id"],
        "label_name": label.get("label_name") or "—",
        "last_withdrawn_period": label_cutoff,
        "paid_withdraw_period_to": paid_period_to,
        "effective_withdraw_cutoff": effective_cutoff,
        "cutoff_needs_sync": bool(effective_cutoff and effective_cutoff != label_cutoff),
        "paid_withdraw_missing_period_count": paid_missing_period_count,
        "restore_blocked": paid_missing_period_count > 0,
        "latest_report_period": None,
        "eligible_period_from": None,
        "eligible_period_to": None,
        "eligible_pending_lines": 0,
        "eligible_available_lines": 0,
        "stale_cutoff_lines": 0,
        "stale_cutoff_idr": 0,
        "orphan_withdrawn_lines": 0,
        "orphan_withdrawn_idr": 0,
        "orphan_legacy_settled_lines": 0,
        "orphan_legacy_settled_idr": 0,
        "wrongly_settled_lines": 0,
        "wrongly_settled_idr": 0,
        "import_status_mismatch_lines": 0,
        "import_status_mismatch_idr": 0,
        "calculation_mismatch_lines": 0,
        "calculation_mismatch_current_idr": 0,
        "calculation_mismatch_projected_idr": 0,
        "calculation_missing_lines": 0,
        "exchange_rate_backfill_lines": 0,
        "royalty_percentage_current": float(
            60 if label.get("royalty_percentage_default") is None else label["royalty_percentage_default"]
        ),
        "draft_under_received_import_lines": 0,
        "pending_under_received_import_lines": 0,
        "draft_under_published_import_lines": 0,
        "orphan_period_from": None,
        "orphan_period_to": None,
        "unverified_withdrawn_lines": 0,
        "unverified_withdrawn_idr": 0,
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
        row["stale_cutoff_lines"], row["wrongly_settled_lines"], row["cutoff_needs_sync"],
        row["calculation_mismatch_lines"],
    ))
    row["audit_status"] = (
        "blocked_active_withdraw" if row["has_active_withdraw"]
        else "blocked_withdraw_history" if row["restore_blocked"]
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
    requested_scope = body.label_ids if body else None
    existing = await _active_job("balance_audit_preview")
    if existing:
        if existing.get("scope_label_ids") == requested_scope:
            return {"job_id": existing["id"], "status": existing["status"], "already_running": True}
        raise HTTPException(status_code=409, detail="Audit saldo lain sedang berjalan. Tunggu hingga selesai.")
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
        "scope_label_ids": requested_scope,
    })
    asyncio.create_task(_run_balance_audit_preview(
        job_id=job_id, label_ids=requested_scope,
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


@balance_audit_r.get("/labels/{label_id}/diagnostic")
async def get_label_balance_diagnostic(label_id: str, user: dict = Depends(require_admin)):
    """Read-only grouped evidence for one label; never mutates balance or line state."""
    _require_finance(user)
    label = await db.labels.find_one(
        {"id": label_id},
        {"_id": 0, "id": 1, "label_name": 1, "last_withdrawn_period": 1,
         "royalty_percentage_default": 1, "balance_pending_idr": 1,
         "balance_available_idr": 1, "balance_withdraw_requested_idr": 1},
    )
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    guard = await _paid_withdraw_guard(
        label_id=label_id, label_cutoff=label.get("last_withdrawn_period"),
    )
    grouped = []
    async for item in db_bg.royalty_lines.aggregate([
        {"$match": {"label_id": label_id}},
        {"$group": {
            "_id": {
                "import_id": "$import_id",
                "status": {"$ifNull": ["$status", "(kosong)"]},
                "match_status": {"$ifNull": ["$match_status", "(kosong)"]},
                "legacy_settled": {"$eq": ["$legacy_settled", True]},
                "period_type": {"$type": "$period"},
                "period": {"$convert": {
                    "input": "$period", "to": "string",
                    "onError": "(tidak valid)", "onNull": "(kosong)",
                }},
            },
            "lines": {"$sum": 1},
            "revenue_eur": {"$sum": {"$ifNull": ["$revenue_eur", 0]}},
            "label_idr": {"$sum": {"$ifNull": ["$label_idr", 0]}},
        }},
    ], allowDiskUse=True):
        grouped.append(item)
    import_ids = list({
        (item.get("_id") or {}).get("import_id") for item in grouped
        if (item.get("_id") or {}).get("import_id")
    })
    imports = await db_bg.royalty_imports.find(
        {"id": {"$in": import_ids}},
        {"_id": 0, "id": 1, "filename": 1, "status": 1, "exchange_rate_eur_idr": 1},
    ).to_list(len(import_ids) or 1)
    import_by_id = {item["id"]: item for item in imports}
    categories: Dict[str, Dict[str, Any]] = {}
    groups = []
    cutoff = guard["effective_cutoff"]
    for item in grouped:
        key = item.get("_id") or {}
        import_doc = import_by_id.get(key.get("import_id"), {})
        category = _diagnostic_classification(
            status=key.get("status") or "(kosong)",
            legacy_settled=bool(key.get("legacy_settled")),
            period=key.get("period") or "(kosong)",
            period_type=key.get("period_type") or "missing",
            cutoff=cutoff,
            import_status=import_doc.get("status"),
        )
        bucket = categories.setdefault(category, {"lines": 0, "revenue_eur": 0.0, "label_idr": 0})
        bucket["lines"] += int(item.get("lines") or 0)
        bucket["revenue_eur"] += float(item.get("revenue_eur") or 0)
        bucket["label_idr"] += int(item.get("label_idr") or 0)
        groups.append({
            "category": category,
            "import_id": key.get("import_id"),
            "import_filename": import_doc.get("filename"),
            "import_status": import_doc.get("status") or "(tidak ditemukan)",
            "exchange_rate": import_doc.get("exchange_rate_eur_idr"),
            "period": key.get("period"),
            "period_type": key.get("period_type"),
            "status": key.get("status"),
            "match_status": key.get("match_status"),
            "legacy_settled": bool(key.get("legacy_settled")),
            "lines": int(item.get("lines") or 0),
            "revenue_eur": round(float(item.get("revenue_eur") or 0), 12),
            "label_idr": int(item.get("label_idr") or 0),
        })
    for bucket in categories.values():
        bucket["revenue_eur"] = round(bucket["revenue_eur"], 12)
    groups.sort(key=lambda item: (
        item.get("category") or "", item.get("period") or "",
        item.get("import_filename") or "", item.get("status") or "",
    ))
    return {
        "label": label,
        "effective_withdraw_cutoff": cutoff,
        "paid_withdraw_period_to": guard["paid_period_to"],
        "paid_withdraw_missing_period_count": guard["missing_period_count"],
        "categories": categories,
        "totals": {
            "lines": sum(item["lines"] for item in groups),
            "revenue_eur": round(sum(item["revenue_eur"] for item in groups), 12),
            "label_idr": sum(item["label_idr"] for item in groups),
        },
        "groups": groups,
        "read_only": True,
    }


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
    stale_recalc = await close_stale_recalculation_jobs()
    active_recalc = await db.migrate_jobs.find_one({
        "kind": {"$in": ["recalculate_label_unwithdrawn", "recalculate_all_unwithdrawn", "label_rate_sync"]},
        "status": {"$in": ACTIVE_JOB_STATUSES},
    }, {"_id": 0, "id": 1, "kind": 1, "updated_at": 1})
    if active_recalc:
        raise HTTPException(status_code=409, detail="Tunggu proses hitung ulang persentase yang masih aktif selesai")

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
        "restore_blocked": {"$ne": True},
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
        "stale_recalculation_jobs_closed": stale_recalc["closed"],
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
            "balance_withdraw_requested_idr": 1, "royalty_percentage_default": 1,
        }).to_list(20000)
        scope_filter = {"label_id": {"$in": label_ids}} if label_ids is not None else {}
        active_by_label: Dict[str, Dict[str, Any]] = {}
        async for withdraw in db_bg.withdraw_requests.find({
            **scope_filter,
            "status": {"$in": ["requested", "approved"]}, "legacy_import": {"$ne": True},
        }, {"_id": 0, "id": 1, "label_id": 1, "amount_idr": 1}):
            bucket = active_by_label.setdefault(withdraw["label_id"], {"amount": 0, "ids": []})
            bucket["amount"] += int(withdraw.get("amount_idr") or 0)
            bucket["ids"].append(withdraw["id"])
        paid_by_label: Dict[str, Dict[str, Any]] = {}
        async for withdraw in db_bg.withdraw_requests.find(
            {**scope_filter, "status": "paid"},
            {"_id": 0, "label_id": 1, "period_to": 1},
        ):
            bucket = paid_by_label.setdefault(withdraw["label_id"], {"period_to": None, "missing": 0})
            period_to = withdraw.get("period_to")
            if period_to:
                bucket["period_to"] = _max_period(bucket["period_to"], period_to)
            else:
                bucket["missing"] += 1
        rows_by_label = {
            label["id"]: _empty_row(
                label,
                active_by_label.get(label["id"], {}).get("amount", 0),
                active_by_label.get(label["id"], {}).get("ids", []),
                paid_by_label.get(label["id"], {}).get("period_to"),
                paid_by_label.get(label["id"], {}).get("missing", 0),
            ) for label in labels
        }
        await db_bg.balance_audit_rows.delete_many({"job_id": job_id})
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {"phase": "aggregating_royalty_lines", "progress_labels_total": len(labels), "updated_at": now_iso()}},
        )
        import_docs = await db_bg.royalty_imports.find(
            {}, {"_id": 0, "id": 1, "status": 1},
        ).to_list(100000)
        import_status_by_id = {
            item["id"]: item.get("status") for item in import_docs if item.get("id")
        }
        enhanced_projection = label_ids is not None
        pipeline = [
            {"$match": {
                "label_id": {"$in": label_ids} if label_ids is not None else {"$ne": None},
                "period": {"$type": "string"},
                "status": {"$in": ["draft", "pending", "available", "withdrawn"]},
            }},
        ]
        if enhanced_projection:
            pipeline.extend([{"$lookup": {
                "from": "labels", "localField": "label_id", "foreignField": "id", "as": "_audit_label",
            }},
            {"$lookup": {
                "from": "royalty_imports", "localField": "import_id", "foreignField": "id", "as": "_audit_import",
            }},
            {"$set": {
                "_audit_percentage": {"$ifNull": [
                    {"$arrayElemAt": ["$_audit_label.royalty_percentage_default", 0]}, 60,
                ]},
                "_audit_import_rate": {"$arrayElemAt": ["$_audit_import.exchange_rate_eur_idr", 0]},
            }},
            {"$set": {
                "_audit_rate": {"$ifNull": ["$exchange_rate", "$_audit_import_rate"]},
            }},
            {"$set": {
                "_audit_ready": {"$and": [
                    {"$ne": ["$revenue_eur", None]}, {"$gt": [{"$ifNull": ["$_audit_rate", 0]}, 0]},
                ]},
                "_audit_expected_label_idr": {"$convert": {
                    "input": {"$round": [{"$multiply": [
                        {"$round": [{"$multiply": [
                            {"$ifNull": ["$revenue_eur", 0]}, {"$divide": ["$_audit_percentage", 100]},
                        ]}, 6]},
                        {"$ifNull": ["$_audit_rate", 0]},
                    ]}, 0]},
                    "to": "long", "onError": 0, "onNull": 0,
                }},
            }},
            ])
        pipeline.append({"$group": {
                "_id": {
                    "label_id": "$label_id",
                    "period": "$period",
                    "status": "$status",
                    "legacy_settled": {"$eq": ["$legacy_settled", True]},
                    "import_id": "$import_id",
                },
                "amount_idr": {"$sum": "$label_idr"},
                **({
                    "projected_amount_idr": {"$sum": {"$cond": [
                        "$_audit_ready", "$_audit_expected_label_idr", {"$ifNull": ["$label_idr", 0]},
                    ]}},
                    "calculation_mismatch_lines": {"$sum": {"$cond": [
                        {"$and": ["$_audit_ready", {"$ne": [
                            {"$ifNull": ["$label_idr", 0]}, "$_audit_expected_label_idr",
                        ]}]}, 1, 0,
                    ]}},
                    "calculation_mismatch_current_idr": {"$sum": {"$cond": [
                        {"$and": ["$_audit_ready", {"$ne": [
                            {"$ifNull": ["$label_idr", 0]}, "$_audit_expected_label_idr",
                        ]}]}, {"$ifNull": ["$label_idr", 0]}, 0,
                    ]}},
                    "calculation_mismatch_projected_idr": {"$sum": {"$cond": [
                        {"$and": ["$_audit_ready", {"$ne": [
                            {"$ifNull": ["$label_idr", 0]}, "$_audit_expected_label_idr",
                        ]}]}, "$_audit_expected_label_idr", 0,
                    ]}},
                    "calculation_missing_lines": {"$sum": {"$cond": ["$_audit_ready", 0, 1]}},
                    "exchange_rate_backfill_lines": {"$sum": {"$cond": [
                        {"$and": [
                            {"$eq": [{"$ifNull": ["$exchange_rate", None]}, None]},
                            {"$gt": [{"$ifNull": ["$_audit_import_rate", 0]}, 0]},
                        ]}, 1, 0,
                    ]}},
                } if enhanced_projection else {}),
                "lines_count": {"$sum": 1},
            }})
        async for grouped in db_bg.royalty_lines.aggregate(pipeline, allowDiskUse=True):
            key = grouped["_id"]
            row = rows_by_label.get(key["label_id"])
            if not row:
                continue
            period = key["period"]
            status = key["status"]
            import_status = import_status_by_id.get(key.get("import_id"))
            target_status = None
            import_target_status = None
            if import_status == "dana_received":
                import_target_status = "available"
            elif import_status == "published":
                import_target_status = "pending"
            if import_target_status == "available" and status in ("draft", "pending"):
                target_status = "available"
            elif import_target_status == "pending" and status == "draft":
                target_status = "pending"
            amount = int(grouped.get("amount_idr") or 0)
            projected_raw = grouped.get("projected_amount_idr")
            projected_amount = amount if projected_raw is None else int(projected_raw or 0)
            count = int(grouped.get("lines_count") or 0)
            if not row["latest_report_period"] or period > row["latest_report_period"]:
                row["latest_report_period"] = period
            cutoff = row["effective_withdraw_cutoff"]
            is_marked_settled = status == "withdrawn" or key["legacy_settled"]
            if is_marked_settled:
                if not cutoff:
                    row["unverified_withdrawn_lines"] += count
                    row["unverified_withdrawn_idr"] += amount
                    row["restore_blocked"] = True
                elif period > cutoff:
                    row["wrongly_settled_lines"] += count
                    row["wrongly_settled_idr"] += amount
                    if status == "withdrawn":
                        row["orphan_withdrawn_lines"] += count
                        row["orphan_withdrawn_idr"] += amount
                    else:
                        row["orphan_legacy_settled_lines"] += count
                        row["orphan_legacy_settled_idr"] += amount
                    row["orphan_period_from"] = min(filter(None, [row["orphan_period_from"], period]))
                    row["orphan_period_to"] = max(filter(None, [row["orphan_period_to"], period]))
                    if not row["restore_blocked"]:
                        destination = import_target_status or ("available" if status == "withdrawn" else status)
                        row["calculation_mismatch_lines"] += int(grouped.get("calculation_mismatch_lines") or 0)
                        row["calculation_mismatch_current_idr"] += int(grouped.get("calculation_mismatch_current_idr") or 0)
                        row["calculation_mismatch_projected_idr"] += int(grouped.get("calculation_mismatch_projected_idr") or 0)
                        row["calculation_missing_lines"] += int(grouped.get("calculation_missing_lines") or 0)
                        row["exchange_rate_backfill_lines"] += int(grouped.get("exchange_rate_backfill_lines") or 0)
                        if destination in ("draft", "pending"):
                            row["expected_pending_idr"] += projected_amount
                            row["eligible_pending_lines"] += count
                        else:
                            row["expected_available_source_idr"] += projected_amount
                            row["eligible_available_lines"] += count
                        row["eligible_period_from"] = min(filter(None, [row["eligible_period_from"], period]))
                        row["eligible_period_to"] = max(filter(None, [row["eligible_period_to"], period]))
                continue
            if cutoff and period <= cutoff and status in ("draft", "pending", "available"):
                row["stale_cutoff_lines"] += count
                row["stale_cutoff_idr"] += amount
                continue
            if target_status:
                row["wrongly_settled_lines"] += count
                row["wrongly_settled_idr"] += amount
                row["import_status_mismatch_lines"] += count
                row["import_status_mismatch_idr"] += amount
                if import_status == "dana_received" and status == "draft":
                    row["draft_under_received_import_lines"] += count
                elif import_status == "dana_received" and status == "pending":
                    row["pending_under_received_import_lines"] += count
                elif import_status == "published" and status == "draft":
                    row["draft_under_published_import_lines"] += count
                row["orphan_period_from"] = min(filter(None, [row["orphan_period_from"], period]))
                row["orphan_period_to"] = max(filter(None, [row["orphan_period_to"], period]))
                row["eligible_period_from"] = min(filter(None, [row["eligible_period_from"], period]))
                row["eligible_period_to"] = max(filter(None, [row["eligible_period_to"], period]))
                row["calculation_mismatch_lines"] += int(grouped.get("calculation_mismatch_lines") or 0)
                row["calculation_mismatch_current_idr"] += int(grouped.get("calculation_mismatch_current_idr") or 0)
                row["calculation_mismatch_projected_idr"] += int(grouped.get("calculation_mismatch_projected_idr") or 0)
                row["calculation_missing_lines"] += int(grouped.get("calculation_missing_lines") or 0)
                row["exchange_rate_backfill_lines"] += int(grouped.get("exchange_rate_backfill_lines") or 0)
                if target_status == "available":
                    row["expected_available_source_idr"] += projected_amount
                    row["eligible_available_lines"] += count
                else:
                    row["expected_pending_idr"] += projected_amount
                    row["eligible_pending_lines"] += count
                continue
            if status not in ("pending", "available"):
                continue
            row["calculation_mismatch_lines"] += int(grouped.get("calculation_mismatch_lines") or 0)
            row["calculation_mismatch_current_idr"] += int(grouped.get("calculation_mismatch_current_idr") or 0)
            row["calculation_mismatch_projected_idr"] += int(grouped.get("calculation_mismatch_projected_idr") or 0)
            row["calculation_missing_lines"] += int(grouped.get("calculation_missing_lines") or 0)
            row["exchange_rate_backfill_lines"] += int(grouped.get("exchange_rate_backfill_lines") or 0)
            if not row["eligible_period_from"] or period < row["eligible_period_from"]:
                row["eligible_period_from"] = period
            if not row["eligible_period_to"] or period > row["eligible_period_to"]:
                row["eligible_period_to"] = period
            if status == "pending":
                row["expected_pending_idr"] += projected_amount
                row["eligible_pending_lines"] += count
            else:
                row["expected_available_source_idr"] += projected_amount
                row["eligible_available_lines"] += count

        rows = [_finalize_row(row) for row in rows_by_label.values()]
        summary = {
            "total_labels": len(rows),
            "drift_labels": sum(1 for row in rows if row["audit_status"] == "drift"),
            "clean_labels": sum(1 for row in rows if row["audit_status"] == "clean"),
            "blocked_active_withdraw": sum(1 for row in rows if row["has_active_withdraw"]),
            "blocked_withdraw_history": sum(1 for row in rows if row["audit_status"] == "blocked_withdraw_history"),
            "negative_balance_labels": sum(1 for row in rows if row["current_pending_idr"] < 0 or row["current_available_idr"] < 0),
            "stale_cutoff_lines": sum(row["stale_cutoff_lines"] for row in rows),
            "orphan_withdrawn_labels": sum(1 for row in rows if row["orphan_withdrawn_lines"]),
            "orphan_withdrawn_lines": sum(row["orphan_withdrawn_lines"] for row in rows),
            "orphan_withdrawn_idr": sum(row["orphan_withdrawn_idr"] for row in rows),
            "orphan_legacy_settled_labels": sum(1 for row in rows if row["orphan_legacy_settled_lines"]),
            "orphan_legacy_settled_lines": sum(row["orphan_legacy_settled_lines"] for row in rows),
            "orphan_legacy_settled_idr": sum(row["orphan_legacy_settled_idr"] for row in rows),
            "wrongly_settled_labels": sum(1 for row in rows if row["wrongly_settled_lines"]),
            "wrongly_settled_lines": sum(row["wrongly_settled_lines"] for row in rows),
            "wrongly_settled_idr": sum(row["wrongly_settled_idr"] for row in rows),
            "import_status_mismatch_labels": sum(1 for row in rows if row["import_status_mismatch_lines"]),
            "import_status_mismatch_lines": sum(row["import_status_mismatch_lines"] for row in rows),
            "import_status_mismatch_idr": sum(row["import_status_mismatch_idr"] for row in rows),
            "calculation_mismatch_labels": sum(1 for row in rows if row["calculation_mismatch_lines"]),
            "calculation_mismatch_lines": sum(row["calculation_mismatch_lines"] for row in rows),
            "calculation_mismatch_current_idr": sum(row["calculation_mismatch_current_idr"] for row in rows),
            "calculation_mismatch_projected_idr": sum(row["calculation_mismatch_projected_idr"] for row in rows),
            "calculation_missing_lines": sum(row["calculation_missing_lines"] for row in rows),
            "exchange_rate_backfill_lines": sum(row["exchange_rate_backfill_lines"] for row in rows),
            "unverified_withdrawn_lines": sum(row["unverified_withdrawn_lines"] for row in rows),
            "cutoff_sync_labels": sum(1 for row in rows if row["cutoff_needs_sync"]),
            "pending_delta_idr": sum(row["pending_delta_idr"] for row in rows if row["audit_status"] == "drift"),
            "available_delta_idr": sum(row["available_delta_idr"] for row in rows if row["audit_status"] == "drift"),
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


async def _paid_withdraw_guard(*, label_id: str, label_cutoff: Optional[str]) -> Dict[str, Any]:
    paid_period_to = None
    missing_period_count = 0
    async for withdraw in db_bg.withdraw_requests.find(
        {"label_id": label_id, "status": "paid"},
        {"_id": 0, "period_to": 1},
    ):
        period_to = withdraw.get("period_to")
        if period_to:
            paid_period_to = _max_period(paid_period_to, period_to)
        else:
            missing_period_count += 1
    return {
        "paid_period_to": paid_period_to,
        "effective_cutoff": _max_period(label_cutoff, paid_period_to),
        "missing_period_count": missing_period_count,
    }


async def _restore_orphan_withdrawn_lines(
    *, label_id: str, cutoff: Optional[str], job_id: str,
) -> Dict[str, int]:
    if not cutoff:
        return {"lines": 0, "amount_before_idr": 0}
    total = 0
    amount = 0
    last_oid = None
    while True:
        query: Dict[str, Any] = {
            "label_id": label_id,
            "period": {"$gt": cutoff},
            "$or": [
                {"status": "withdrawn"},
                {"legacy_settled": True},
            ],
        }
        if last_oid is not None:
            query["_id"] = {"$gt": last_oid}
        batch = await db_bg.royalty_lines.find(
            query, {"_id": 1, "label_idr": 1, "status": 1, "import_id": 1},
        ).sort("_id", 1).limit(5000).to_list(5000)
        if not batch:
            break
        object_ids = [item["_id"] for item in batch]
        last_oid = object_ids[-1]
        import_ids = list({item.get("import_id") for item in batch if item.get("import_id")})
        imports = await db_bg.royalty_imports.find(
            {"id": {"$in": import_ids}}, {"_id": 0, "id": 1, "status": 1},
        ).to_list(len(import_ids) or 1)
        import_status = {item["id"]: item.get("status") for item in imports}
        withdrawn_by_target: Dict[str, List[Any]] = {"available": [], "pending": []}
        for item in batch:
            if item.get("status") != "withdrawn":
                continue
            target = "pending" if import_status.get(item.get("import_id")) == "published" else "available"
            withdrawn_by_target[target].append(item["_id"])
        amount += sum(int(item.get("label_idr") or 0) for item in batch)
        result = await db_bg.royalty_lines.update_many(
            {
                "_id": {"$in": object_ids},
                "period": {"$gt": cutoff},
                "$or": [{"status": "withdrawn"}, {"legacy_settled": True}],
            },
            {
                "$set": {
                    "legacy_settled": False,
                    "restored_by_balance_reconciliation": True,
                    "restored_by_balance_reconciliation_job_id": job_id,
                    "restored_at": now_iso(),
                },
                "$unset": {
                    "legacy_settled_period_end": "",
                    "legacy_settled_at": "",
                    "legacy_manual_job_id": "",
                    "settled_by_period_cutoff": "",
                    "settled_by_period_cutoff_at": "",
                    "settled_by_balance_reconciliation": "",
                    "settled_at": "",
                },
            },
        )
        for target, withdrawn_ids in withdrawn_by_target.items():
            if not withdrawn_ids:
                continue
            await db_bg.royalty_lines.update_many(
                {
                    "_id": {"$in": withdrawn_ids},
                    "status": "withdrawn",
                    "period": {"$gt": cutoff},
                    "restored_by_balance_reconciliation_job_id": job_id,
                },
                {"$set": {"status": target}},
            )
        total += result.modified_count
    return {"lines": total, "amount_before_idr": amount}


async def _backfill_exchange_rates(
    *, label_id: str, cutoff: Optional[str], job_id: str,
) -> int:
    period_filter: Dict[str, Any] = {"$type": "string"}
    if cutoff:
        period_filter["$gt"] = cutoff
    import_ids = await db_bg.royalty_lines.distinct("import_id", {
        "label_id": label_id,
        "status": {"$in": ["draft", "pending", "available"]},
        "legacy_settled": {"$ne": True},
        "period": period_filter,
        "revenue_eur": {"$ne": None},
        "$or": [{"exchange_rate": {"$exists": False}}, {"exchange_rate": None}],
    })
    if not import_ids:
        return 0
    imports = await db_bg.royalty_imports.find(
        {"id": {"$in": import_ids}, "exchange_rate_eur_idr": {"$gt": 0}},
        {"_id": 0, "id": 1, "exchange_rate_eur_idr": 1},
    ).to_list(len(import_ids))
    total = 0
    for item in imports:
        result = await db_bg.royalty_lines.update_many(
            {
                "label_id": label_id, "import_id": item["id"],
                "status": {"$in": ["draft", "pending", "available"]},
                "legacy_settled": {"$ne": True}, "period": period_filter,
                "$or": [{"exchange_rate": {"$exists": False}}, {"exchange_rate": None}],
            },
            {"$set": {
                "exchange_rate": float(item["exchange_rate_eur_idr"]),
                "exchange_rate_backfilled_by_balance_reconciliation": True,
                "exchange_rate_backfilled_job_id": job_id,
                "exchange_rate_backfilled_at": now_iso(),
            }},
        )
        total += result.modified_count
    return total


async def _sync_lines_with_import_status(
    *, label_id: str, cutoff: Optional[str], job_id: str,
) -> Dict[str, int]:
    period_filter: Dict[str, Any] = {"$type": "string"}
    if cutoff:
        period_filter["$gt"] = cutoff
    import_ids = await db_bg.royalty_lines.distinct("import_id", {
        "label_id": label_id,
        "status": {"$in": ["draft", "pending"]},
        "legacy_settled": {"$ne": True},
        "period": period_filter,
    })
    if not import_ids:
        return {"lines": 0, "amount_before_idr": 0, "to_pending": 0, "to_available": 0}
    imports = await db_bg.royalty_imports.find(
        {"id": {"$in": import_ids}, "status": {"$in": ["published", "dana_received"]}},
        {"_id": 0, "id": 1, "status": 1},
    ).to_list(len(import_ids))
    totals = {"lines": 0, "amount_before_idr": 0, "to_pending": 0, "to_available": 0}
    for item in imports:
        target_status = "available" if item.get("status") == "dana_received" else "pending"
        source_statuses = ["draft", "pending"] if target_status == "available" else ["draft"]
        last_oid = None
        while True:
            query: Dict[str, Any] = {
                "label_id": label_id,
                "import_id": item["id"],
                "status": {"$in": source_statuses},
                "legacy_settled": {"$ne": True},
                "period": period_filter,
            }
            if last_oid is not None:
                query["_id"] = {"$gt": last_oid}
            batch = await db_bg.royalty_lines.find(
                query, {"_id": 1, "label_idr": 1},
            ).sort("_id", 1).limit(5000).to_list(5000)
            if not batch:
                break
            object_ids = [line["_id"] for line in batch]
            last_oid = object_ids[-1]
            result = await db_bg.royalty_lines.update_many(
                {"_id": {"$in": object_ids}, "status": {"$in": source_statuses}},
                {"$set": {
                    "status": target_status,
                    "status_reconciled_from_import": True,
                    "status_reconciled_from_import_job_id": job_id,
                    "status_reconciled_at": now_iso(),
                }},
            )
            totals["lines"] += result.modified_count
            totals["amount_before_idr"] += sum(int(line.get("label_idr") or 0) for line in batch)
            totals["to_available" if target_status == "available" else "to_pending"] += result.modified_count
    return totals


async def _run_balance_reconciliation(*, job_id: str, preview_job_id: str, user_id: str) -> None:
    totals = {
        "labels_reconciled": 0,
        "labels_clean_after_recheck": 0,
        "labels_skipped_active_withdraw": 0,
        "labels_skipped_withdraw_history": 0,
        "labels_failed": 0,
        "stale_lines_settled": 0,
        "orphan_lines_restored": 0,
        "orphan_amount_before_idr": 0,
        "import_status_lines_synchronized": 0,
        "import_status_amount_before_idr": 0,
        "import_status_lines_to_pending": 0,
        "import_status_lines_to_available": 0,
        "calculation_mismatch_lines": 0,
        "exchange_rate_lines_backfilled": 0,
        "orphan_lines_recalculated": 0,
        "cutoffs_synchronized": 0,
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
            "restore_blocked": {"$ne": True},
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
                guard = await _paid_withdraw_guard(
                    label_id=label_id, label_cutoff=label.get("last_withdrawn_period"),
                )
                if guard["missing_period_count"]:
                    totals["labels_skipped_withdraw_history"] += 1
                    await db_bg.balance_audit_rows.update_one(
                        {"job_id": preview_job_id, "label_id": label_id},
                        {"$set": {
                            "apply_status": "blocked_withdraw_history",
                            "apply_message": "Riwayat withdraw paid tanpa period_to muncul setelah preview",
                        }},
                    )
                    continue
                effective_cutoff = guard["effective_cutoff"]
                cutoff_synchronized = bool(
                    effective_cutoff and effective_cutoff != label.get("last_withdrawn_period")
                )
                if cutoff_synchronized:
                    await db_bg.labels.update_one(
                        {"id": label_id},
                        {"$set": {
                            "last_withdrawn_period": effective_cutoff,
                            "updated_at": now_iso(),
                        }},
                    )
                    label["last_withdrawn_period"] = effective_cutoff
                    totals["cutoffs_synchronized"] += 1
                settled = await _flip_stale_cutoff_lines(
                    label_id=label_id, cutoff=effective_cutoff,
                )
                restored = await _restore_orphan_withdrawn_lines(
                    label_id=label_id, cutoff=effective_cutoff, job_id=job_id,
                )
                synchronized = await _sync_lines_with_import_status(
                    label_id=label_id, cutoff=effective_cutoff, job_id=job_id,
                )
                backfilled_rates = await _backfill_exchange_rates(
                    label_id=label_id, cutoff=effective_cutoff, job_id=job_id,
                )
                recalc = {"lines_recalculated": 0}
                if (
                    restored["lines"] or synchronized["lines"] or backfilled_rates
                    or int(audit_row.get("calculation_mismatch_lines") or 0)
                ):
                    recalc = await recalculate_label_unwithdrawn(
                        label_id=label_id,
                        percentage=float(
                            60 if label.get("royalty_percentage_default") is None
                            else label["royalty_percentage_default"]
                        ),
                        job_id=job_id,
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
                if not any(deltas.values()) and not settled and not restored["lines"] and not synchronized["lines"] and not cutoff_synchronized:
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
                    totals["orphan_lines_restored"] += restored["lines"]
                    totals["orphan_amount_before_idr"] += restored["amount_before_idr"]
                    totals["import_status_lines_synchronized"] += synchronized["lines"]
                    totals["import_status_amount_before_idr"] += synchronized["amount_before_idr"]
                    totals["import_status_lines_to_pending"] += synchronized["to_pending"]
                    totals["import_status_lines_to_available"] += synchronized["to_available"]
                    totals["calculation_mismatch_lines"] += int(audit_row.get("calculation_mismatch_lines") or 0)
                    totals["exchange_rate_lines_backfilled"] += backfilled_rates
                    totals["orphan_lines_recalculated"] += int(recalc.get("lines_recalculated") or 0)
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
                    {"$set": {
                        "apply_status": "done",
                        "applied_job_id": job_id,
                        "applied_at": now_iso(),
                        "applied_balances": expected,
                        "applied_effective_cutoff": effective_cutoff,
                        "applied_orphan_lines_restored": restored["lines"],
                        "applied_orphan_amount_before_idr": restored["amount_before_idr"],
                        "applied_import_status_lines_synchronized": synchronized["lines"],
                        "applied_import_status_amount_before_idr": synchronized["amount_before_idr"],
                        "applied_calculation_mismatch_lines": int(audit_row.get("calculation_mismatch_lines") or 0),
                        "applied_exchange_rate_lines_backfilled": backfilled_rates,
                    }},
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