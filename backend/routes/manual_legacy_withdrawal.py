"""Manual admin entry for historical withdrawal settlement ranges."""
import asyncio
from datetime import date
from typing import Any, Dict

from fastapi import HTTPException

from models import ManualLegacyWithdrawIn, new_id, now_iso
from .balance_utils import compute_label_balance_snapshot
from .deps import db_bg, log_activity, logger
from .royalty_recalculation import trigger_royalty_caches


ELIGIBLE_STATUSES = ["draft", "pending", "available"]


def _validate_dates(body: ManualLegacyWithdrawIn) -> None:
    if body.period_from > body.period_to:
        raise HTTPException(status_code=400, detail="Bulan awal tidak boleh melewati bulan pencairan terbaru")
    try:
        requested = date.fromisoformat(body.request_date)
        paid = date.fromisoformat(body.paid_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Tanggal harus valid") from exc
    if paid < requested:
        raise HTTPException(status_code=400, detail="Tanggal pencairan tidak boleh sebelum tanggal pengajuan")


def _eligible_filter(body: ManualLegacyWithdrawIn) -> Dict[str, Any]:
    return {
        "label_id": body.label_id,
        "period": {"$gte": body.period_from, "$lte": body.period_to},
        "status": {"$in": ELIGIBLE_STATUSES},
        "legacy_settled": {"$ne": True},
    }


async def preview_manual_legacy_withdrawal(body: ManualLegacyWithdrawIn) -> dict:
    _validate_dates(body)
    label = await db_bg.labels.find_one(
        {"id": body.label_id},
        {"_id": 0, "id": 1, "label_name": 1, "last_withdrawn_period": 1},
    )
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    active = await db_bg.withdraw_requests.find_one({
        "label_id": body.label_id,
        "status": {"$in": ["requested", "approved"]},
        "legacy_import": {"$ne": True},
    }, {"_id": 0, "id": 1})
    if active:
        raise HTTPException(status_code=409, detail="Label memiliki withdraw aktif. Selesaikan atau tolak terlebih dahulu.")
    old_cutoff = label.get("last_withdrawn_period")
    if old_cutoff and body.period_to <= old_cutoff:
        raise HTTPException(status_code=409, detail=f"Rentang ini sudah berada dalam cutoff legacy sampai {old_cutoff}")

    gap_filter: Dict[str, Any] = {
        "label_id": body.label_id,
        "status": {"$in": ELIGIBLE_STATUSES},
        "legacy_settled": {"$ne": True},
        "period": {"$lte": body.period_to},
    }
    if old_cutoff:
        gap_filter["period"]["$gt"] = old_cutoff
    earliest = await db_bg.royalty_lines.find_one(gap_filter, {"_id": 0, "period": 1}, sort=[("period", 1)])
    if earliest and earliest.get("period") and body.period_from > earliest["period"]:
        raise HTTPException(
            status_code=409,
            detail=f"Bulan awal harus {earliest['period']} atau lebih awal agar tidak ada royalti tertinggal sebelum cutoff.",
        )

    summary = {"amount_idr": 0, "lines_count": 0, "draft_lines": 0, "pending_lines": 0, "available_lines": 0}
    async for row in db_bg.royalty_lines.aggregate([
        {"$match": _eligible_filter(body)},
        {"$group": {
            "_id": None,
            "amount_idr": {"$sum": {"$ifNull": ["$label_idr", 0]}},
            "lines_count": {"$sum": 1},
            "draft_lines": {"$sum": {"$cond": [{"$eq": ["$status", "draft"]}, 1, 0]}},
            "pending_lines": {"$sum": {"$cond": [{"$eq": ["$status", "pending"]}, 1, 0]}},
            "available_lines": {"$sum": {"$cond": [{"$eq": ["$status", "available"]}, 1, 0]}},
        }},
    ], allowDiskUse=True):
        summary = {key: int(row.get(key) or 0) for key in summary}
    if summary["lines_count"] == 0:
        raise HTTPException(status_code=400, detail="Tidak ada royalti aktif pada rentang bulan tersebut")
    return {
        **summary,
        "label_id": label["id"],
        "label_name": label.get("label_name"),
        "period_from": body.period_from,
        "period_to": body.period_to,
        "request_date": body.request_date,
        "paid_date": body.paid_date,
        "old_last_withdrawn_period": old_cutoff,
        "new_last_withdrawn_period": body.period_to,
    }


async def queue_manual_legacy_withdrawal(body: ManualLegacyWithdrawIn, user: dict) -> dict:
    preview = await preview_manual_legacy_withdrawal(body)
    manual_key = f"{body.label_id}:{body.period_from}:{body.period_to}:{body.request_date}:{body.paid_date}"
    duplicate = await db_bg.withdraw_requests.find_one({"manual_legacy_key": manual_key}, {"_id": 0, "id": 1})
    if duplicate:
        raise HTTPException(status_code=409, detail="Riwayat legacy manual yang sama sudah tersimpan")
    running = await db_bg.migrate_jobs.find_one({
        "kind": "withdraws_legacy_manual", "manual_legacy_key": manual_key,
        "status": {"$in": ["queued", "processing"]},
    }, {"_id": 0, "id": 1})
    if running:
        raise HTTPException(status_code=409, detail="Riwayat yang sama sedang diproses")
    job_id = new_id()
    submitted_at = now_iso()
    await db_bg.migrate_jobs.insert_one({
        "id": job_id, "kind": "withdraws_legacy_manual", "status": "queued",
        "manual_legacy_key": manual_key, "submitted_by": user["id"],
        "submitted_at": submitted_at, "updated_at": submitted_at,
        "progress_phase": "queued", "request": body.model_dump(), "preview": preview,
    })
    asyncio.create_task(_run_manual_legacy_withdrawal(
        job_id=job_id, body=body, preview=preview, manual_key=manual_key, user_id=user["id"],
    ))
    return {"job_id": job_id, "status": "queued", "preview": preview}


async def _run_manual_legacy_withdrawal(
    *, job_id: str, body: ManualLegacyWithdrawIn, preview: dict, manual_key: str, user_id: str,
) -> None:
    try:
        await db_bg.migrate_jobs.update_one({"id": job_id}, {"$set": {"status": "processing", "progress_phase": "settling_lines", "updated_at": now_iso()}})
        current_label = await db_bg.labels.find_one({"id": body.label_id}, {"_id": 0, "last_withdrawn_period": 1}) or {}
        current_cutoff = current_label.get("last_withdrawn_period")
        new_cutoff = max(filter(None, [current_cutoff, body.period_to]))
        await db_bg.labels.update_one({"id": body.label_id}, {"$set": {
            "last_withdrawn_period": new_cutoff,
            "legacy_withdraw_period_end": new_cutoff,
            "legacy_withdraw_synced_at": now_iso(),
            "updated_at": now_iso(),
        }})

        chunk_size = 5000
        last_oid = None
        flipped = 0
        line_filter = _eligible_filter(body)
        while True:
            query = dict(line_filter)
            if last_oid is not None:
                query["_id"] = {"$gt": last_oid}
            batch = await db_bg.royalty_lines.find(query, {"_id": 1}).sort("_id", 1).limit(chunk_size).to_list(chunk_size)
            if not batch:
                break
            object_ids = [item["_id"] for item in batch]
            last_oid = object_ids[-1]
            await db_bg.royalty_lines.update_many({"_id": {"$in": object_ids}}, {"$set": {
                "status": "withdrawn", "legacy_settled": True,
                "legacy_settled_period_end": body.period_to,
                "legacy_settled_at": now_iso(), "legacy_manual_job_id": job_id,
            }})
            flipped += len(object_ids)

        snapshot = await compute_label_balance_snapshot(label_id=body.label_id)
        await db_bg.labels.update_one({"id": body.label_id}, {"$set": {
            "balance_pending_idr": snapshot["balance_pending_idr"],
            "balance_available_idr": snapshot["balance_available_idr"],
            "balance_withdraw_requested_idr": snapshot["balance_withdraw_requested_idr"],
            "updated_at": now_iso(),
        }})
        withdrawal_id = new_id()
        history = {
            "id": withdrawal_id, "label_id": body.label_id, "status": "paid",
            "amount_idr": preview["amount_idr"], "period_from": body.period_from,
            "period_to": body.period_to, "request_date": body.request_date,
            "paid_date": body.paid_date, "lines_count": flipped,
            "legacy_import": True, "manual_legacy": True,
            "manual_legacy_key": manual_key, "manual_legacy_job_id": job_id,
            "admin_note": body.note or "Riwayat legacy ditambahkan manual oleh admin",
            "created_by": user_id, "created_at": now_iso(), "updated_at": now_iso(),
        }
        await db_bg.withdraw_requests.insert_one(history)
        await db_bg.balance_transactions.insert_one({
            "id": new_id(), "label_id": body.label_id, "type": "withdraw_paid",
            "amount_idr": -int(preview["amount_idr"]), "reference_type": "withdraw_request",
            "reference_id": withdrawal_id,
            "description": f"[Legacy manual] Withdraw {body.period_from} s/d {body.period_to}",
            "legacy_import": True, "created_at": body.paid_date,
        })
        await log_activity(user_id, "manual_legacy_withdrawal", "withdraw", withdrawal_id, after={
            "label_id": body.label_id, "period_from": body.period_from,
            "period_to": body.period_to, "amount_idr": preview["amount_idr"], "lines_flipped": flipped,
        })
        result = {
            "withdrawal_id": withdrawal_id, "amount_idr": preview["amount_idr"],
            "royalty_lines_flipped": flipped, "period_from": body.period_from,
            "period_to": body.period_to, "balance_pending_idr": snapshot["balance_pending_idr"],
            "balance_available_idr": snapshot["balance_available_idr"],
        }
        await db_bg.migrate_jobs.update_one({"id": job_id}, {"$set": {
            "status": "done", "progress_phase": "done", "result": result,
            "finished_at": now_iso(), "updated_at": now_iso(),
        }})
        await trigger_royalty_caches()
    except Exception as exc:
        logger.exception("[MANUAL LEGACY WITHDRAW] job %s failed: %s", job_id, exc)
        await db_bg.migrate_jobs.update_one({"id": job_id}, {"$set": {
            "status": "error", "progress_phase": "error",
            "error_message": f"{type(exc).__name__}: {str(exc)[:400]}",
            "finished_at": now_iso(), "updated_at": now_iso(),
        }})