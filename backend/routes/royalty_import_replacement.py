"""Guarded replacement of a selected royalty import with mandatory preview."""
import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

import storage_service
from models import new_id, now_iso
from royalty_utils import detect_columns, iter_csv_file
from .balance_utils import compute_label_balance_snapshot
from .deps import UPLOAD_DIR, db, db_bg, log_activity, logger, require_admin
from .royalty import _process_csv_import_bg, _trigger_dashboard_recompute


replacement_r = APIRouter(prefix="/royalty/admin/imports", tags=["royalty-import-replacement"])
STABLE_IMPORT_STATUSES = {"published", "dana_received"}
ACTIVE_REPLACEMENT_STATUSES = {"queued", "processing"}


class ReplacementInitiateIn(BaseModel):
    filename: str = Field(..., min_length=1, max_length=200)
    size_bytes: int = Field(..., gt=0, le=5 * 1024 * 1024 * 1024)
    rate_eur_idr: float = Field(..., gt=0)
    note: Optional[str] = Field(default=None, max_length=500)


class ReplacementCommitIn(BaseModel):
    preview_job_id: str = Field(..., min_length=1, max_length=100)
    confirmation: str = Field(..., min_length=1, max_length=30)


def _require_finance(user: dict) -> None:
    if user.get("role") not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")


def _require_super_admin(user: dict) -> None:
    if user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Commit penggantian hanya untuk Super Admin")


def _next_period(period: Optional[str]) -> str:
    if not period:
        return datetime.now(timezone.utc).strftime("%Y-%m")
    year, month = (int(value) for value in period.split("-"))
    return f"{year + (1 if month == 12 else 0):04d}-{1 if month == 12 else month + 1:02d}"


def _import_signature(item: dict) -> dict:
    return {
        "id": item.get("id"), "status": item.get("status"),
        "total_lines": int(item.get("total_lines") or 0),
        "total_revenue_eur": round(float(item.get("total_revenue_eur") or 0), 6),
        "total_label_idr": int(item.get("total_label_idr") or 0),
        "period_start": item.get("period_start"), "period_end": item.get("period_end"),
        "filename": item.get("filename"), "r2_key": item.get("r2_key"),
        "exchange_rate_eur_idr": float(item.get("exchange_rate_eur_idr") or 0),
    }


async def _effective_cutoffs(label_ids: List[str]) -> Dict[str, Optional[str]]:
    labels = await db_bg.labels.find(
        {"id": {"$in": label_ids}}, {"_id": 0, "id": 1, "last_withdrawn_period": 1},
    ).to_list(len(label_ids) or 1)
    cutoffs = {item["id"]: item.get("last_withdrawn_period") for item in labels}
    async for item in db_bg.withdraw_requests.find(
        {"label_id": {"$in": label_ids}, "status": "paid", "period_to": {"$type": "string"}},
        {"_id": 0, "label_id": 1, "period_to": 1},
    ):
        cutoffs[item["label_id"]] = max(filter(None, [cutoffs.get(item["label_id"]), item["period_to"]]))
    return cutoffs


async def _aggregate_import(import_id: str) -> List[dict]:
    return [item async for item in db_bg.royalty_lines.aggregate([
        {"$match": {"import_id": import_id, "label_id": {"$ne": None}}},
        {"$group": {
            "_id": {
                "label_id": "$label_id", "period": "$period", "status": "$status",
                "legacy_settled": {"$eq": ["$legacy_settled", True]},
            },
            "lines": {"$sum": 1},
            "revenue_eur": {"$sum": {"$ifNull": ["$revenue_eur", 0]}},
            "label_idr": {"$sum": {"$ifNull": ["$label_idr", 0]}},
        }},
    ], allowDiskUse=True)]


async def _active_withdraw_projection(
    *, label_id: str, old_import_id: str, replacement_import_id: str,
    period_from: Optional[str], period_to: Optional[str], adjustment_idr: int,
    include_staged_replacement: bool = True, adjustment_period: Optional[str] = None,
) -> Dict[str, int]:
    if not period_from or not period_to:
        return {"amount_idr": 0, "lines_count": 0}
    other = {"amount_idr": 0, "lines_count": 0}
    async for item in db_bg.royalty_lines.aggregate([
        {"$match": {
            "label_id": label_id, "import_id": {"$nin": [old_import_id, replacement_import_id]},
            "status": "available", "legacy_settled": {"$ne": True},
            "period": {"$gte": period_from, "$lte": period_to},
        }},
        {"$group": {"_id": None, "amount_idr": {"$sum": "$label_idr"}, "lines_count": {"$sum": 1}}},
    ], allowDiskUse=True):
        other = {"amount_idr": int(item.get("amount_idr") or 0), "lines_count": int(item.get("lines_count") or 0)}
    replacement = {"amount_idr": 0, "lines_count": 0}
    if include_staged_replacement:
        async for item in db_bg.royalty_lines.aggregate([
            {"$match": {
                "import_id": replacement_import_id, "label_id": label_id,
                "period": {"$gte": period_from, "$lte": period_to},
            }},
            {"$group": {"_id": None, "amount_idr": {"$sum": "$label_idr"}, "lines_count": {"$sum": 1}}},
        ], allowDiskUse=True):
            replacement = {"amount_idr": int(item.get("amount_idr") or 0), "lines_count": int(item.get("lines_count") or 0)}
    eligible_adjustment = adjustment_idr if (
        adjustment_idr and adjustment_period and period_from <= adjustment_period <= period_to
    ) else 0
    projected_amount = other["amount_idr"] + replacement["amount_idr"] + eligible_adjustment
    return {
        "amount_idr": max(0, projected_amount),
        "lines_count": other["lines_count"] + replacement["lines_count"] + (1 if eligible_adjustment else 0),
    }


async def _run_replacement_preview(job_id: str, old_import_id: str, replacement_import_id: str) -> None:
    try:
        await db_bg.migrate_jobs.update_one({"id": job_id}, {"$set": {
            "status": "processing", "phase": "menghitung_perubahan", "updated_at": now_iso(),
        }})
        old_import = await db_bg.royalty_imports.find_one({"id": old_import_id}, {"_id": 0})
        new_import = await db_bg.royalty_imports.find_one({"id": replacement_import_id}, {"_id": 0})
        if not old_import or not new_import:
            raise RuntimeError("Import lama atau file pengganti tidak ditemukan")
        if old_import.get("status") not in STABLE_IMPORT_STATUSES:
            raise RuntimeError("Status import lama berubah dan tidak lagi dapat diganti")
        if new_import.get("status") != "replacement_preview":
            raise RuntimeError("File pengganti belum selesai diproses")
        old_rows, new_rows = await asyncio.gather(
            _aggregate_import(old_import_id), _aggregate_import(replacement_import_id),
        )
        label_ids = list({
            (item.get("_id") or {}).get("label_id") for item in old_rows + new_rows
            if (item.get("_id") or {}).get("label_id")
        })
        cutoffs = await _effective_cutoffs(label_ids)
        labels = await db_bg.labels.find(
            {"id": {"$in": label_ids}}, {"_id": 0, "id": 1, "label_name": 1},
        ).to_list(len(label_ids) or 1)
        names = {item["id"]: item.get("label_name") for item in labels}
        values: Dict[str, Dict[str, Any]] = {}
        for label_id in label_ids:
            values[label_id] = {
                "label_id": label_id, "label_name": names.get(label_id) or "—",
                "cutoff": cutoffs.get(label_id), "old_active_idr": 0, "new_active_idr": 0,
                "old_historical_idr": 0, "new_historical_idr": 0,
                "old_lines": 0, "new_lines": 0, "old_revenue_eur": 0.0, "new_revenue_eur": 0.0,
                "new_active_periods": [],
            }
        for source, rows in (("old", old_rows), ("new", new_rows)):
            for item in rows:
                key = item.get("_id") or {}
                label_id = key.get("label_id")
                period = key.get("period")
                row = values[label_id]
                amount = int(item.get("label_idr") or 0)
                historical = bool(row["cutoff"] and period and period <= row["cutoff"])
                if source == "old":
                    row["old_lines"] += int(item.get("lines") or 0)
                    row["old_revenue_eur"] += float(item.get("revenue_eur") or 0)
                    if historical:
                        row["old_historical_idr"] += amount
                    elif key.get("status") in ("pending", "available") and not key.get("legacy_settled"):
                        row["old_active_idr"] += amount
                else:
                    row["new_lines"] += int(item.get("lines") or 0)
                    row["new_revenue_eur"] += float(item.get("revenue_eur") or 0)
                    if historical:
                        row["new_historical_idr"] += amount
                    else:
                        row["new_active_idr"] += amount
                        if period:
                            row["new_active_periods"].append(period)
        active_withdraws = await db_bg.withdraw_requests.find({
            "label_id": {"$in": label_ids}, "status": {"$in": ["requested", "approved"]},
            "legacy_import": {"$ne": True},
        }, {"_id": 0}).to_list(10000)
        active_by_label = {item["label_id"]: item for item in active_withdraws}
        output = []
        await db_bg.royalty_import_replacement_rows.delete_many({"job_id": job_id})
        for row in values.values():
            row["old_revenue_eur"] = round(row["old_revenue_eur"], 12)
            row["new_revenue_eur"] = round(row["new_revenue_eur"], 12)
            row["historical_adjustment_idr"] = row["new_historical_idr"] - row["old_historical_idr"]
            row["active_delta_idr"] = row["new_active_idr"] - row["old_active_idr"]
            row["projected_balance_delta_idr"] = row["active_delta_idr"] + row["historical_adjustment_idr"]
            row["adjustment_period"] = max(row["new_active_periods"]) if row["new_active_periods"] else _next_period(row["cutoff"])
            row.pop("new_active_periods", None)
            withdraw = active_by_label.get(row["label_id"])
            row["active_withdraw"] = None
            if withdraw:
                missing_period = not withdraw.get("period_from") or not withdraw.get("period_to")
                projected = {"amount_idr": int(withdraw.get("amount_idr") or 0), "lines_count": int(withdraw.get("lines_count") or 0)}
                if not missing_period:
                    projected = await _active_withdraw_projection(
                        label_id=row["label_id"], old_import_id=old_import_id,
                        replacement_import_id=replacement_import_id,
                        period_from=withdraw.get("period_from"), period_to=withdraw.get("period_to"),
                        adjustment_idr=row["historical_adjustment_idr"] if old_import["status"] == "dana_received" else 0,
                        include_staged_replacement=old_import["status"] == "dana_received",
                        adjustment_period=row["adjustment_period"],
                    )
                row["active_withdraw"] = {
                    "id": withdraw["id"], "status": withdraw.get("status"),
                    "period_from": withdraw.get("period_from"), "period_to": withdraw.get("period_to"),
                    "old_amount_idr": int(withdraw.get("amount_idr") or 0),
                    "new_amount_idr": projected["amount_idr"], "new_lines_count": projected["lines_count"],
                    "blocked_missing_period": missing_period,
                }
            row_doc = {"id": new_id(), "job_id": job_id, **row}
            await db_bg.royalty_import_replacement_rows.insert_one(row_doc)
            row_doc.pop("_id", None)
            output.append(row_doc)
        summary = {
            "affected_labels": len(output),
            "old_lines": sum(item["old_lines"] for item in output),
            "new_lines": sum(item["new_lines"] for item in output),
            "old_revenue_eur": round(sum(item["old_revenue_eur"] for item in output), 12),
            "new_revenue_eur": round(sum(item["new_revenue_eur"] for item in output), 12),
            "old_label_idr": int(old_import.get("total_label_idr") or 0),
            "new_label_idr": int(new_import.get("total_label_idr") or 0),
            "active_balance_delta_idr": sum(item["active_delta_idr"] for item in output),
            "historical_adjustment_idr": sum(item["historical_adjustment_idr"] for item in output),
            "active_withdraws_recalculated": sum(1 for item in output if item["active_withdraw"]),
            "blocked_active_withdraws": sum(
                1 for item in output if item["active_withdraw"] and item["active_withdraw"]["blocked_missing_period"]
            ),
        }
        finished = now_iso()
        await db_bg.migrate_jobs.update_one({"id": job_id}, {"$set": {
            "status": "done", "phase": "done", "summary": summary,
            "old_import_signature": _import_signature(old_import),
            "replacement_import_signature": _import_signature(new_import),
            "finished_at": finished, "updated_at": finished,
        }})
    except Exception as exc:
        logger.exception("[IMPORT REPLACEMENT PREVIEW] %s failed: %s", job_id, exc)
        await db_bg.migrate_jobs.update_one({"id": job_id}, {"$set": {
            "status": "error", "phase": "error", "error_message": f"{type(exc).__name__}: {str(exc)[:400]}",
            "finished_at": now_iso(), "updated_at": now_iso(),
        }})


async def _delete_import_lines(import_id: str, job_id: str) -> int:
    deleted = 0
    while True:
        batch = await db_bg.royalty_lines.find({"import_id": import_id}, {"_id": 1}).limit(5000).to_list(5000)
        if not batch:
            break
        result = await db_bg.royalty_lines.delete_many({"_id": {"$in": [item["_id"] for item in batch]}})
        deleted += result.deleted_count
        await db_bg.migrate_jobs.update_one({"id": job_id}, {"$set": {
            "progress_lines_deleted": deleted, "updated_at": now_iso(),
        }})
    return deleted


async def _activate_replacement_lines(
    *, replacement_import_id: str, old_status: str, cutoffs: Dict[str, Optional[str]], job_id: str,
) -> int:
    activated = 0
    last_oid = None
    while True:
        query: Dict[str, Any] = {"import_id": replacement_import_id, "replacement_stage": True}
        if last_oid is not None:
            query["_id"] = {"$gt": last_oid}
        batch = await db_bg.royalty_lines.find(
            query, {"_id": 1, "label_id": 1, "period": 1, "replacement_original_match_status": 1},
        ).sort("_id", 1).limit(5000).to_list(5000)
        if not batch:
            break
        last_oid = batch[-1]["_id"]
        grouped: Dict[tuple, List[Any]] = defaultdict(list)
        for item in batch:
            cutoff = cutoffs.get(item.get("label_id"))
            historical = bool(cutoff and item.get("period") and item["period"] <= cutoff)
            status = "withdrawn" if historical else (
                "available" if old_status == "dana_received" else "pending" if old_status == "published" else "draft"
            )
            grouped[(status, historical, item.get("replacement_original_match_status") or "unmatched", cutoff)].append(item["_id"])
        for (status, historical, match_status, cutoff), object_ids in grouped.items():
            await db_bg.royalty_lines.update_many({"_id": {"$in": object_ids}}, {
                "$set": {
                    "status": status, "legacy_settled": historical,
                    "legacy_settled_period_end": cutoff if historical else None,
                    "match_status": match_status, "replacement_stage": False,
                    "replacement_activated_at": now_iso(), "replacement_commit_job_id": job_id,
                },
                "$unset": {"replacement_original_match_status": ""},
            })
        activated += len(batch)
        await db_bg.migrate_jobs.update_one({"id": job_id}, {"$set": {
            "progress_lines_activated": activated, "updated_at": now_iso(),
        }})
    return activated


async def _run_replacement_commit(job_id: str) -> None:
    try:
        job = await db_bg.migrate_jobs.find_one({"id": job_id}, {"_id": 0})
        old_id, new_id_value, preview_id = job["old_import_id"], job["replacement_import_id"], job["preview_job_id"]
        old_snapshot = job["old_import_snapshot"]
        rows = await db_bg.royalty_import_replacement_rows.find(
            {"job_id": preview_id}, {"_id": 0},
        ).to_list(50000)
        affected_labels = [item["label_id"] for item in rows]
        cutoffs = await _effective_cutoffs(affected_labels)
        await db_bg.migrate_jobs.update_one({"id": job_id}, {"$set": {
            "status": "processing", "phase": "menghapus_data_lama", "updated_at": now_iso(),
        }})
        deleted_lines = await _delete_import_lines(old_id, job_id)
        await db_bg.migrate_jobs.update_one({"id": job_id}, {"$set": {
            "phase": "mengaktifkan_data_baru", "updated_at": now_iso(),
        }})
        activated_lines = await _activate_replacement_lines(
            replacement_import_id=new_id_value, old_status=old_snapshot["status"], cutoffs=cutoffs, job_id=job_id,
        )
        adjustments = 0
        for row in rows:
            delta = int(row.get("historical_adjustment_idr") or 0)
            if not delta:
                continue
            adjustment_id = f"replacement-adjustment:{new_id_value}:{row['label_id']}"
            status = "available" if old_snapshot["status"] == "dana_received" else "pending"
            await db_bg.royalty_lines.update_one({"id": adjustment_id}, {"$setOnInsert": {
                "id": adjustment_id, "import_id": new_id_value, "label_id": row["label_id"],
                "period": row["adjustment_period"], "track_title_raw": "Penyesuaian penggantian laporan royalti",
                "artist_name_raw": "Penyesuaian", "release_title_raw": "Penyesuaian",
                "quantity": 0, "revenue_eur": 0.0, "revenue_idr": 0,
                "label_eur": 0.0, "label_idr": delta, "distributor_idr": -delta,
                "match_status": "matched", "match_by": "replacement_adjustment",
                "status": status, "legacy_settled": False, "replacement_adjustment": True,
                "replacement_commit_job_id": job_id, "created_at": now_iso(),
            }}, upsert=True)
            await db_bg.balance_transactions.update_one({"id": adjustment_id}, {"$setOnInsert": {
                "id": adjustment_id, "label_id": row["label_id"], "type": "royalty_replacement_adjustment",
                "amount_idr": delta, "reference_type": "royalty_import_replacement",
                "reference_id": new_id_value,
                "description": "Penyesuaian data lama yang pembayarannya dipertahankan",
                "created_at": now_iso(),
            }}, upsert=True)
            adjustments += 1
        withdraws_changed = 0
        for row in rows:
            active = row.get("active_withdraw")
            if not active:
                continue
            current = await db_bg.withdraw_requests.find_one({
                "id": active["id"], "status": {"$in": ["requested", "approved"]},
            }, {"_id": 0})
            if not current:
                continue
            projected = await _active_withdraw_projection(
                label_id=row["label_id"], old_import_id=old_id, replacement_import_id="(activated)",
                period_from=current.get("period_from"), period_to=current.get("period_to"),
                adjustment_idr=0,
                include_staged_replacement=False,
            )
            revision = {
                "replacement_job_id": job_id, "old_amount_idr": int(current.get("amount_idr") or 0),
                "new_amount_idr": projected["amount_idr"], "changed_at": now_iso(),
            }
            await db_bg.withdraw_requests.update_one({"id": current["id"]}, {
                "$set": {
                    "amount_idr": projected["amount_idr"], "lines_count": projected["lines_count"],
                    "replacement_recalculated_at": now_iso(), "updated_at": now_iso(),
                }, "$push": {"replacement_revisions": revision},
            })
            await db_bg.balance_transactions.update_many({
                "reference_id": current["id"], "type": "withdraw_request",
            }, {"$set": {"amount_idr": -projected["amount_idr"], "updated_at": now_iso()}})
            withdraws_changed += 1
        await db_bg.balance_transactions.delete_many({
            "reference_type": "royalty_import", "reference_id": old_id,
        })
        tx_type = "royalty_available" if old_snapshot["status"] == "dana_received" else "royalty_pending"
        if old_snapshot["status"] in ("published", "dana_received"):
            for row in rows:
                amount = int(row.get("new_active_idr") or 0)
                if not amount:
                    continue
                await db_bg.balance_transactions.update_one({
                    "label_id": row["label_id"], "type": tx_type,
                    "reference_type": "royalty_import", "reference_id": new_id_value,
                }, {"$setOnInsert": {
                    "id": new_id(), "label_id": row["label_id"], "type": tx_type,
                    "amount_idr": amount, "reference_type": "royalty_import", "reference_id": new_id_value,
                    "description": "Royalti dari file pengganti", "created_at": now_iso(),
                }}, upsert=True)
        for collection in (db_bg.labels, db_bg.releases, db_bg.tracks, db_bg.artists):
            await collection.update_many({"auto_created_from": old_id}, {"$set": {"auto_created_from": new_id_value}})
        await db_bg.royalty_imports.update_one({"id": new_id_value}, {
            "$set": {
                "status": old_snapshot["status"], "replacement_stage": False,
                "replaced_import_id": old_id, "replacement_commit_job_id": job_id,
                "replacement_completed_at": now_iso(), "updated_at": now_iso(),
                "published_at": old_snapshot.get("published_at"),
                "dana_received_at": old_snapshot.get("dana_received_at"),
            }, "$unset": {"replacement_target_status": ""},
        })
        await db_bg.royalty_imports.delete_one({"id": old_id})
        if old_snapshot.get("r2_key"):
            try:
                await storage_service.delete_object(key=old_snapshot["r2_key"])
            except Exception as exc:
                logger.warning("[IMPORT REPLACEMENT] old R2 cleanup failed %s: %s", old_id, exc)
        for extension in (".csv", ".csv.gz"):
            (UPLOAD_DIR / "csv" / f"{old_id}{extension}").unlink(missing_ok=True)
        for label_id in affected_labels:
            label = await db_bg.labels.find_one({"id": label_id}, {"_id": 0})
            if not label:
                continue
            snapshot = await compute_label_balance_snapshot(label_id=label_id, label=label)
            await db_bg.labels.update_one({"id": label_id}, {"$set": {
                "balance_pending_idr": snapshot["balance_pending_idr"],
                "balance_available_idr": snapshot["balance_available_idr"],
                "balance_withdraw_requested_idr": snapshot["balance_withdraw_requested_idr"],
                "updated_at": now_iso(),
            }})
        result = {
            "old_import_id": old_id, "replacement_import_id": new_id_value,
            "old_lines_deleted": deleted_lines, "new_lines_activated": activated_lines,
            "historical_adjustments_created": adjustments,
            "active_withdraws_recalculated": withdraws_changed,
            "affected_labels": len(affected_labels),
        }
        await db_bg.royalty_import_replacements.update_one({"id": job_id}, {"$set": {
            "id": job_id, "status": "done", "old_import": old_snapshot,
            "replacement_import_id": new_id_value, "preview_job_id": preview_id,
            "result": result, "completed_at": now_iso(),
        }}, upsert=True)
        await db_bg.migrate_jobs.update_one({"id": job_id}, {"$set": {
            "status": "done", "phase": "done", "result": result,
            "finished_at": now_iso(), "updated_at": now_iso(),
        }})
        _trigger_dashboard_recompute()
        await log_activity(job.get("submitted_by") or "system", "replace_royalty_import", "royalty", new_id_value, before={
            "old_import_id": old_id, "filename": old_snapshot.get("filename"),
        }, after=result)
    except Exception as exc:
        logger.exception("[IMPORT REPLACEMENT COMMIT] %s failed: %s", job_id, exc)
        await db_bg.migrate_jobs.update_one({"id": job_id}, {"$set": {
            "status": "error", "phase": "error", "error_message": f"{type(exc).__name__}: {str(exc)[:500]}",
            "finished_at": now_iso(), "updated_at": now_iso(),
        }})


@replacement_r.post("/{old_import_id}/replacement/initiate")
async def initiate_replacement(old_import_id: str, body: ReplacementInitiateIn, user: dict = Depends(require_admin)):
    _require_finance(user)
    old_import = await db.royalty_imports.find_one({"id": old_import_id}, {"_id": 0})
    if not old_import:
        raise HTTPException(status_code=404, detail="Import lama tidak ditemukan")
    if old_import.get("status") not in STABLE_IMPORT_STATUSES:
        raise HTTPException(status_code=409, detail="Import hanya dapat diganti setelah prosesnya selesai")
    running = await db.royalty_imports.find_one({
        "replacement_of_import_id": old_import_id,
        "status": {"$in": ["awaiting_upload", "processing", "replacement_preview", "replacement_committing"]},
    }, {"_id": 0, "id": 1, "status": 1})
    if running:
        raise HTTPException(status_code=409, detail="Penggantian untuk import ini sudah ada")
    filename = body.filename.strip()
    if not filename.lower().endswith((".csv", ".csv.gz")):
        raise HTTPException(status_code=400, detail="File pengganti wajib CSV atau CSV.GZ")
    replacement_id = new_id()
    extension = ".csv.gz" if filename.lower().endswith(".gz") else ".csv"
    object_key = f"csv-replacements/{old_import_id}/{replacement_id}{extension}"
    content_type = "application/gzip" if extension == ".csv.gz" else "text/csv"
    upload_url = await storage_service.generate_presigned_put_url(key=object_key, content_type=content_type, ttl=7200)
    created = now_iso()
    await db_bg.royalty_imports.insert_one({
        "id": replacement_id, "period": "multi", "period_start": None, "period_end": None,
        "period_breakdown": {}, "is_multi_period": False, "source": "believe",
        "filename": filename, "file_url": f"/api/files/{object_key}", "r2_key": object_key,
        "file_size_bytes": body.size_bytes, "exchange_rate_eur_idr": body.rate_eur_idr,
        "fee_percent": 0.0, "total_lines": 0, "processed_lines": 0, "progress_pct": 0,
        "matched_lines": 0, "unmatched_lines": 0, "invalid_period_rows": 0,
        "auto_created_labels": 0, "auto_created_releases": 0, "auto_created_tracks": 0,
        "auto_created_artists": 0, "total_revenue_eur": 0.0, "total_label_idr": 0,
        "status": "awaiting_upload", "error_message": None, "replacement_stage": True,
        "replacement_of_import_id": old_import_id, "replacement_target_status": old_import["status"],
        "uploaded_by": user["id"], "note": body.note, "created_at": created, "updated_at": created,
    })
    return {
        "replacement_import_id": replacement_id, "upload_url": upload_url,
        "content_type": content_type, "expires_in": 7200,
    }


@replacement_r.post("/{old_import_id}/replacement/{replacement_import_id}/finalize")
async def finalize_replacement(old_import_id: str, replacement_import_id: str, user: dict = Depends(require_admin)):
    _require_finance(user)
    replacement = await db.royalty_imports.find_one({
        "id": replacement_import_id, "replacement_of_import_id": old_import_id,
    }, {"_id": 0})
    if not replacement:
        raise HTTPException(status_code=404, detail="File pengganti tidak ditemukan")
    if replacement.get("status") != "awaiting_upload":
        raise HTTPException(status_code=409, detail="File pengganti sudah difinalisasi")
    metadata = await storage_service.head_object(key=replacement["r2_key"])
    if not metadata:
        raise HTTPException(status_code=400, detail="Upload file pengganti belum selesai")
    actual_size = int(metadata.get("ContentLength") or 0)
    if actual_size != int(replacement.get("file_size_bytes") or 0):
        raise HTTPException(status_code=400, detail="Ukuran file pengganti tidak sesuai")
    extension = ".csv.gz" if replacement["r2_key"].endswith(".gz") else ".csv"
    local_path = UPLOAD_DIR / "csv" / f"{replacement_import_id}{extension}"
    local_path.parent.mkdir(parents=True, exist_ok=True)
    await storage_service.download_to_file(key=replacement["r2_key"], local_path=str(local_path))
    headers = []
    has_rows = False
    try:
        for parsed_headers, row in iter_csv_file(str(local_path)):
            if row is None:
                headers = parsed_headers
                continue
            has_rows = True
            break
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"File pengganti tidak dapat dibaca: {exc}")
    columns = detect_columns(headers) if headers else {}
    if not has_rows or columns.get("revenue_eur") is None or columns.get("period") is None:
        raise HTTPException(status_code=400, detail="File pengganti wajib berisi Bulan laporan dan Pendapatan Bersih")
    await db_bg.royalty_imports.update_one({"id": replacement_import_id}, {"$set": {
        "status": "processing", "file_size_bytes": actual_size, "started_at": now_iso(), "updated_at": now_iso(),
    }})
    asyncio.create_task(_process_csv_import_bg(
        import_id=replacement_import_id, file_path=str(local_path), period=None,
        rate_eur_idr=float(replacement["exchange_rate_eur_idr"]), fee_percent=0,
        user_id=user["id"], staged_replacement=True,
    ))
    return {"replacement_import_id": replacement_import_id, "status": "processing"}


@replacement_r.post("/{old_import_id}/replacement/{replacement_import_id}/preview")
async def preview_replacement(old_import_id: str, replacement_import_id: str, user: dict = Depends(require_admin)):
    _require_finance(user)
    replacement = await db.royalty_imports.find_one({
        "id": replacement_import_id, "replacement_of_import_id": old_import_id,
    }, {"_id": 0, "status": 1})
    if not replacement or replacement.get("status") != "replacement_preview":
        raise HTTPException(status_code=409, detail="File pengganti belum siap untuk preview")
    existing = await db.migrate_jobs.find_one({
        "kind": "royalty_import_replacement_preview", "old_import_id": old_import_id,
        "replacement_import_id": replacement_import_id, "status": {"$in": list(ACTIVE_REPLACEMENT_STATUSES)},
    }, {"_id": 0, "id": 1, "status": 1})
    if existing:
        return {"job_id": existing["id"], "status": existing["status"], "already_running": True}
    job_id = new_id()
    await db_bg.migrate_jobs.insert_one({
        "id": job_id, "kind": "royalty_import_replacement_preview", "status": "queued",
        "old_import_id": old_import_id, "replacement_import_id": replacement_import_id,
        "submitted_by": user["id"], "submitted_at": now_iso(), "updated_at": now_iso(), "phase": "queued",
    })
    asyncio.create_task(_run_replacement_preview(job_id, old_import_id, replacement_import_id))
    return {"job_id": job_id, "status": "queued", "already_running": False}


@replacement_r.get("/{old_import_id}/replacement/{replacement_import_id}/status")
async def get_replacement_status(old_import_id: str, replacement_import_id: str, user: dict = Depends(require_admin)):
    _require_finance(user)
    replacement = await db.royalty_imports.find_one({
        "id": replacement_import_id, "replacement_of_import_id": old_import_id,
    }, {"_id": 0})
    if not replacement:
        raise HTTPException(status_code=404, detail="File pengganti tidak ditemukan")
    return replacement


@replacement_r.delete("/{old_import_id}/replacement/{replacement_import_id}")
async def cancel_replacement(old_import_id: str, replacement_import_id: str, user: dict = Depends(require_admin)):
    _require_finance(user)
    replacement = await db.royalty_imports.find_one({
        "id": replacement_import_id, "replacement_of_import_id": old_import_id,
    }, {"_id": 0})
    if not replacement:
        raise HTTPException(status_code=404, detail="File pengganti tidak ditemukan")
    if replacement.get("status") == "replacement_committing":
        raise HTTPException(status_code=409, detail="Penggantian sedang dijalankan dan tidak dapat dibatalkan")
    deleted_lines = await _delete_import_lines(replacement_import_id, replacement_import_id)
    for collection in (db_bg.tracks, db_bg.releases, db_bg.artists, db_bg.labels):
        await collection.delete_many({"auto_created_from": replacement_import_id})
    if replacement.get("r2_key"):
        try:
            await storage_service.delete_object(key=replacement["r2_key"])
        except Exception as exc:
            logger.warning("[IMPORT REPLACEMENT] staged R2 cleanup failed %s: %s", replacement_import_id, exc)
    await db_bg.royalty_imports.delete_one({"id": replacement_import_id})
    return {"ok": True, "deleted_lines": deleted_lines}


@replacement_r.post("/{old_import_id}/replacement/{replacement_import_id}/commit")
async def commit_replacement(
    old_import_id: str, replacement_import_id: str, body: ReplacementCommitIn,
    user: dict = Depends(require_admin),
):
    _require_super_admin(user)
    if body.confirmation.strip().upper() != "GANTI DATA":
        raise HTTPException(status_code=400, detail="Ketik GANTI DATA untuk melanjutkan")
    preview = await db.migrate_jobs.find_one({
        "id": body.preview_job_id, "kind": "royalty_import_replacement_preview", "status": "done",
        "old_import_id": old_import_id, "replacement_import_id": replacement_import_id,
    }, {"_id": 0})
    if not preview:
        raise HTTPException(status_code=404, detail="Preview penggantian yang selesai tidak ditemukan")
    if int((preview.get("summary") or {}).get("blocked_active_withdraws") or 0) > 0:
        raise HTTPException(status_code=409, detail="Ada pengajuan penarikan aktif tanpa rentang bulan. Lengkapi datanya sebelum commit.")
    existing = await db.migrate_jobs.find_one({
        "kind": "royalty_import_replacement_commit", "preview_job_id": body.preview_job_id,
    }, {"_id": 0, "id": 1, "status": 1})
    if existing:
        return {"job_id": existing["id"], "status": existing["status"], "already_running": True}
    old_import = await db.royalty_imports.find_one({"id": old_import_id}, {"_id": 0})
    replacement = await db.royalty_imports.find_one({"id": replacement_import_id}, {"_id": 0})
    if not old_import or not replacement:
        raise HTTPException(status_code=404, detail="Import lama atau file pengganti tidak ditemukan")
    if _import_signature(old_import) != preview.get("old_import_signature"):
        raise HTTPException(status_code=409, detail="Import lama berubah setelah preview. Buat preview baru.")
    if _import_signature(replacement) != preview.get("replacement_import_signature"):
        raise HTTPException(status_code=409, detail="File pengganti berubah setelah preview. Buat preview baru.")
    job_id = new_id()
    await db_bg.migrate_jobs.insert_one({
        "id": job_id, "kind": "royalty_import_replacement_commit", "status": "queued",
        "old_import_id": old_import_id, "replacement_import_id": replacement_import_id,
        "preview_job_id": body.preview_job_id, "old_import_snapshot": old_import,
        "submitted_by": user["id"], "submitted_at": now_iso(), "updated_at": now_iso(), "phase": "queued",
    })
    await db_bg.royalty_imports.update_many({"id": {"$in": [old_import_id, replacement_import_id]}}, {
        "$set": {"status": "replacement_committing", "replacement_commit_job_id": job_id, "updated_at": now_iso()},
    })
    asyncio.create_task(_run_replacement_commit(job_id))
    return {"job_id": job_id, "status": "queued", "already_running": False}


@replacement_r.get("/replacement/jobs/{job_id}")
async def get_replacement_job(job_id: str, user: dict = Depends(require_admin)):
    _require_finance(user)
    job = await db.migrate_jobs.find_one({
        "id": job_id, "kind": {"$in": ["royalty_import_replacement_preview", "royalty_import_replacement_commit"]},
    }, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Pekerjaan penggantian tidak ditemukan")
    return job


@replacement_r.get("/replacement/jobs/{job_id}/rows")
async def get_replacement_rows(
    job_id: str, user: dict = Depends(require_admin),
    page: int = Query(default=1, ge=1), limit: int = Query(default=100, ge=1, le=500),
):
    _require_finance(user)
    query = {"job_id": job_id}
    total = await db.royalty_import_replacement_rows.count_documents(query)
    rows = await db.royalty_import_replacement_rows.find(query, {"_id": 0}).sort(
        "projected_balance_delta_idr", -1,
    ).skip((page - 1) * limit).limit(limit).to_list(limit)
    return {"items": rows, "total": total, "page": page, "limit": limit}


async def resume_replacement_jobs() -> None:
    jobs = await db_bg.migrate_jobs.find({
        "kind": "royalty_import_replacement_commit", "status": {"$in": list(ACTIVE_REPLACEMENT_STATUSES)},
    }, {"_id": 0, "id": 1}).to_list(20)
    for job in jobs:
        asyncio.create_task(_run_replacement_commit(job["id"]))