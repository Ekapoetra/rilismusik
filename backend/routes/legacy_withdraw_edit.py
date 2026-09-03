"""Guarded period-end edits for admin-only legacy withdrawal history."""
import asyncio
from typing import Any, Dict, Optional

from fastapi import HTTPException

from models import new_id, now_iso
from .balance_utils import compute_label_balance_snapshot
from .deps import db_bg, log_activity, logger
from .royalty_recalculation import trigger_royalty_caches


ACTIVE_STATUSES = ("requested", "approved")
LINE_ACTIVE_STATUSES = ("draft", "pending", "available")


def _max_period(*values: Optional[str]) -> Optional[str]:
    valid = [value for value in values if value]
    return max(valid) if valid else None


def _period_range(*, after: Optional[str], through: Optional[str]) -> Dict[str, Any]:
    value: Dict[str, Any] = {"$type": "string"}
    if after:
        value["$gt"] = after
    if through:
        value["$lte"] = through
    return value


async def _sum_active_after(label_id: str, cutoff: str) -> Dict[str, int]:
    totals = {"pending_idr": 0, "available_idr": 0, "pending_lines": 0, "available_lines": 0}
    async for row in db_bg.royalty_lines.aggregate([
        {"$match": {
            "label_id": label_id, "period": {"$gt": cutoff},
            "status": {"$in": ["pending", "available"]}, "legacy_settled": {"$ne": True},
        }},
        {"$group": {
            "_id": "$status", "amount_idr": {"$sum": {"$ifNull": ["$label_idr", 0]}},
            "lines": {"$sum": 1},
        }},
    ], allowDiskUse=True):
        status = row.get("_id")
        if status in ("pending", "available"):
            totals[f"{status}_idr"] = int(row.get("amount_idr") or 0)
            totals[f"{status}_lines"] = int(row.get("lines") or 0)
    return totals


async def _group_range(label_id: str, after: Optional[str], through: Optional[str]) -> list[Dict[str, Any]]:
    match: Dict[str, Any] = {
        "label_id": label_id,
        "period": _period_range(after=after, through=through),
    }
    return await db_bg.royalty_lines.aggregate([
        {"$match": match},
        {"$group": {
            "_id": {
                "import_id": "$import_id", "status": "$status",
                "legacy_settled": {"$eq": ["$legacy_settled", True]},
            },
            "amount_idr": {"$sum": {"$ifNull": ["$label_idr", 0]}},
            "lines": {"$sum": 1},
        }},
    ], allowDiskUse=True).to_list(None)


async def _import_statuses(groups: list[Dict[str, Any]]) -> Dict[str, str]:
    import_ids = list({(row.get("_id") or {}).get("import_id") for row in groups if (row.get("_id") or {}).get("import_id")})
    if not import_ids:
        return {}
    imports = await db_bg.royalty_imports.find(
        {"id": {"$in": import_ids}}, {"_id": 0, "id": 1, "status": 1},
    ).to_list(len(import_ids))
    return {row["id"]: row.get("status") for row in imports}


def _target_status(import_status: Optional[str], current_status: Optional[str]) -> str:
    if import_status == "dana_received":
        return "available"
    if import_status == "published":
        return "pending"
    if current_status in LINE_ACTIVE_STATUSES:
        return current_status
    return "available"


async def _load_context(withdrawal_id: str, new_period: str) -> Dict[str, Any]:
    withdrawal = await db_bg.withdraw_requests.find_one({"id": withdrawal_id}, {"_id": 0})
    if not withdrawal:
        raise HTTPException(status_code=404, detail="Riwayat withdrawal tidak ditemukan")
    if withdrawal.get("legacy_import") is not True or withdrawal.get("status") != "paid":
        raise HTTPException(status_code=400, detail="Hanya withdrawal legacy berstatus dibayar yang dapat diedit")
    old_period = withdrawal.get("period_to")
    if not old_period:
        raise HTTPException(status_code=409, detail="Riwayat legacy ini belum memiliki bulan laporan terakhir")
    if new_period == old_period:
        raise HTTPException(status_code=400, detail="Bulan laporan terakhir belum berubah")
    if withdrawal.get("period_from") and new_period < withdrawal["period_from"]:
        raise HTTPException(status_code=400, detail="Bulan laporan terakhir tidak boleh sebelum bulan awal")
    if withdrawal.get("legacy_edit_lock_job_id"):
        raise HTTPException(status_code=409, detail="Riwayat legacy ini sedang diedit")

    label = await db_bg.labels.find_one(
        {"id": withdrawal["label_id"]},
        {"_id": 0, "id": 1, "label_name": 1, "last_withdrawn_period": 1,
         "balance_pending_idr": 1, "balance_available_idr": 1,
         "balance_withdraw_requested_idr": 1},
    )
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    active = await db_bg.withdraw_requests.find_one({
        "label_id": label["id"], "status": {"$in": list(ACTIVE_STATUSES)},
        "legacy_import": {"$ne": True},
    }, {"_id": 0, "id": 1})
    if active:
        raise HTTPException(status_code=409, detail="Label memiliki withdrawal web aktif. Selesaikan atau tolak terlebih dahulu.")

    histories = await db_bg.withdraw_requests.find(
        {"label_id": label["id"], "status": "paid"},
        {"_id": 0, "id": 1, "period_to": 1, "legacy_import": 1},
    ).to_list(5000)
    missing_period = [row for row in histories if row["id"] != withdrawal_id and not row.get("period_to")]
    if missing_period:
        raise HTTPException(status_code=409, detail="Ada withdrawal dibayar tanpa bulan laporan. Edit diblokir agar dana web tidak terbuka kembali.")
    current_history_cutoff = _max_period(*(row.get("period_to") for row in histories))
    label_cutoff = label.get("last_withdrawn_period")
    if label_cutoff and current_history_cutoff and label_cutoff > current_history_cutoff and new_period < label_cutoff:
        raise HTTPException(status_code=409, detail="Cutoff label lebih tinggi dari seluruh riwayat. Jalankan Audit Saldo sebelum menurunkannya.")
    other_cutoff = _max_period(*(row.get("period_to") for row in histories if row["id"] != withdrawal_id))
    old_cutoff = _max_period(label_cutoff, current_history_cutoff)
    new_cutoff = _max_period(other_cutoff, new_period)
    latest = await db_bg.royalty_lines.find_one(
        {"label_id": label["id"], "period": {"$type": "string"}},
        {"_id": 0, "period": 1}, sort=[("period", -1)],
    )
    latest_period = (latest or {}).get("period")
    if latest_period and new_period > latest_period:
        raise HTTPException(status_code=400, detail=f"Bulan laporan terakhir tidak boleh melewati laporan terbaru {latest_period}")
    if withdrawal.get("manual_legacy"):
        new_key = f"{label['id']}:{withdrawal.get('period_from')}:{new_period}:{withdrawal.get('request_date')}:{withdrawal.get('paid_date')}"
        duplicate = await db_bg.withdraw_requests.find_one(
            {"id": {"$ne": withdrawal_id}, "manual_legacy_key": new_key}, {"_id": 0, "id": 1},
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="Perubahan ini sama dengan riwayat legacy manual lain")
    return {
        "withdrawal": withdrawal, "label": label, "old_period_to": old_period,
        "new_period_to": new_period, "old_cutoff": old_cutoff,
        "new_cutoff": new_cutoff, "latest_period": latest_period,
    }


async def build_legacy_withdraw_edit_preview(withdrawal_id: str, new_period: str, user_id: str) -> Dict[str, Any]:
    context = await _load_context(withdrawal_id, new_period)
    old_cutoff, new_cutoff = context["old_cutoff"], context["new_cutoff"]
    before = await compute_label_balance_snapshot(label_id=context["label"]["id"], label=context["label"])
    after = await _sum_active_after(context["label"]["id"], new_cutoff)
    groups = await _group_range(
        context["label"]["id"],
        after=min(old_cutoff, new_cutoff) if old_cutoff else None,
        through=max(old_cutoff, new_cutoff) if old_cutoff else new_cutoff,
    ) if old_cutoff != new_cutoff else []
    statuses = await _import_statuses(groups)
    lines_to_restore = lines_to_settle = amount_to_restore = amount_to_settle = 0
    restored_pending = restored_available = restored_pending_lines = restored_available_lines = 0
    direction = "unchanged"
    if old_cutoff and new_cutoff < old_cutoff:
        direction = "decrease"
        for row in groups:
            key = row.get("_id") or {}
            legacy = key.get("legacy_settled") is True or key.get("status") == "withdrawn"
            target = _target_status(statuses.get(key.get("import_id")), key.get("status"))
            amount = int(row.get("amount_idr") or 0)
            count = int(row.get("lines") or 0)
            if legacy:
                lines_to_restore += count
                amount_to_restore += amount
            if legacy or key.get("status") == "draft":
                if target == "pending":
                    restored_pending += amount; restored_pending_lines += count
                elif target == "available":
                    restored_available += amount; restored_available_lines += count
        after["pending_idr"] += restored_pending
        after["available_idr"] += restored_available
        after["pending_lines"] += restored_pending_lines
        after["available_lines"] += restored_available_lines
    elif not old_cutoff or new_cutoff > old_cutoff:
        direction = "increase"
        for row in groups:
            key = row.get("_id") or {}
            if key.get("status") in LINE_ACTIVE_STATUSES and key.get("legacy_settled") is not True:
                lines_to_settle += int(row.get("lines") or 0)
                amount_to_settle += int(row.get("amount_idr") or 0)

    preview_id = new_id()
    response = {
        "preview_id": preview_id, "withdrawal_id": withdrawal_id,
        "label_id": context["label"]["id"], "label_name": context["label"].get("label_name"),
        "old_period_to": context["old_period_to"], "new_period_to": context["new_period_to"],
        "old_cutoff": old_cutoff, "new_cutoff": new_cutoff, "latest_report_period": context["latest_period"],
        "direction": direction, "lines_to_restore": lines_to_restore,
        "lines_to_settle": lines_to_settle, "amount_to_restore_idr": amount_to_restore,
        "amount_to_settle_idr": amount_to_settle,
        "balance_before": {
            "pending_idr": before["balance_pending_idr"], "available_idr": before["balance_available_idr"],
        },
        "balance_after": {
            "pending_idr": max(after["pending_idr"], 0), "available_idr": max(after["available_idr"], 0),
        },
    }
    await db_bg.legacy_withdraw_edit_previews.insert_one({
        "id": preview_id, **response,
        "created_by": user_id, "created_at": now_iso(), "consumed_at": None,
    })
    return response


async def _chunk_settle(*, label_id: str, after: Optional[str], through: str, job_id: str, withdrawal_id: str) -> int:
    total = 0
    last_oid = None
    while True:
        query: Dict[str, Any] = {
            "label_id": label_id, "period": _period_range(after=after, through=through),
            "status": {"$in": list(LINE_ACTIVE_STATUSES)}, "legacy_settled": {"$ne": True},
        }
        if last_oid is not None:
            query["_id"] = {"$gt": last_oid}
        batch = await db_bg.royalty_lines.find(query, {"_id": 1}).sort("_id", 1).limit(5000).to_list(5000)
        if not batch:
            break
        object_ids = [row["_id"] for row in batch]
        last_oid = object_ids[-1]
        result = await db_bg.royalty_lines.update_many(
            {"_id": {"$in": object_ids}},
            [{"$set": {
                "legacy_status_before_settlement": "$status", "status": "withdrawn",
                "legacy_settled": True, "legacy_settled_period_end": through,
                "legacy_settled_at": now_iso(), "legacy_edit_job_id": job_id,
                "legacy_edit_withdrawal_id": withdrawal_id,
            }}],
        )
        total += result.modified_count
    return total


async def _chunk_restore(*, label_id: str, after: str, through: str, job_id: str) -> int:
    total = 0
    last_oid = None
    while True:
        query: Dict[str, Any] = {
            "label_id": label_id, "period": _period_range(after=after, through=through),
            "$or": [{"status": "withdrawn"}, {"legacy_settled": True}, {"status": "draft"}],
        }
        if last_oid is not None:
            query["_id"] = {"$gt": last_oid}
        batch = await db_bg.royalty_lines.find(
            query, {"_id": 1, "import_id": 1, "status": 1, "legacy_settled": 1},
        ).sort("_id", 1).limit(5000).to_list(5000)
        if not batch:
            break
        last_oid = batch[-1]["_id"]
        imports = await db_bg.royalty_imports.find(
            {"id": {"$in": list({row.get('import_id') for row in batch if row.get('import_id')})}},
            {"_id": 0, "id": 1, "status": 1},
        ).to_list(5000)
        status_map = {row["id"]: row.get("status") for row in imports}
        grouped: Dict[str, list[Any]] = {"draft": [], "pending": [], "available": []}
        for row in batch:
            target = _target_status(status_map.get(row.get("import_id")), row.get("status"))
            grouped[target].append(row["_id"])
        for target, object_ids in grouped.items():
            if not object_ids:
                continue
            result = await db_bg.royalty_lines.update_many(
                {"_id": {"$in": object_ids}},
                {"$set": {
                    "status": target, "legacy_settled": False,
                    "restored_by_legacy_edit": True, "legacy_edit_job_id": job_id,
                    "legacy_restored_at": now_iso(),
                }, "$unset": {
                    "legacy_settled_period_end": "", "legacy_settled_at": "",
                    "legacy_manual_job_id": "", "legacy_edit_withdrawal_id": "",
                    "settled_by_period_cutoff": "", "settled_by_period_cutoff_at": "",
                    "settled_by_balance_reconciliation": "", "settled_at": "",
                }},
            )
            total += result.modified_count
    return total


async def queue_legacy_withdraw_edit(withdrawal_id: str, preview_id: str, user: dict) -> Dict[str, Any]:
    preview = await db_bg.legacy_withdraw_edit_previews.find_one(
        {"id": preview_id, "withdrawal_id": withdrawal_id, "created_by": user["id"], "consumed_at": None},
        {"_id": 0},
    )
    if not preview:
        raise HTTPException(status_code=404, detail="Preview tidak ditemukan atau sudah digunakan")
    context = await _load_context(withdrawal_id, preview["new_period_to"])
    if context["old_period_to"] != preview["old_period_to"] or context["old_cutoff"] != preview["old_cutoff"]:
        raise HTTPException(status_code=409, detail="Data berubah setelah preview. Muat ulang preview sebelum menyimpan.")
    job_id = new_id()
    claimed = await db_bg.withdraw_requests.update_one(
        {"id": withdrawal_id, "period_to": preview["old_period_to"], "legacy_import": True,
         "$or": [{"legacy_edit_lock_job_id": {"$exists": False}}, {"legacy_edit_lock_job_id": None}]},
        {"$set": {"legacy_edit_lock_job_id": job_id, "updated_at": now_iso()}},
    )
    if claimed.modified_count != 1:
        raise HTTPException(status_code=409, detail="Riwayat berubah atau sedang diproses")
    await db_bg.legacy_withdraw_edit_previews.update_one({"id": preview_id}, {"$set": {"consumed_at": now_iso(), "job_id": job_id}})
    await db_bg.migrate_jobs.insert_one({
        "id": job_id, "kind": "withdraw_legacy_edit", "status": "queued",
        "withdrawal_id": withdrawal_id, "label_id": preview["label_id"],
        "submitted_by": user["id"], "submitted_at": now_iso(), "updated_at": now_iso(),
        "preview_id": preview_id, "preview": {key: value for key, value in preview.items() if key != "_id"},
    })
    asyncio.create_task(_run_legacy_withdraw_edit(job_id=job_id, preview=preview, user_id=user["id"]))
    return {"job_id": job_id, "status": "queued", "preview": {key: value for key, value in preview.items() if key != "_id"}}


async def _run_legacy_withdraw_edit(*, job_id: str, preview: Dict[str, Any], user_id: str) -> None:
    withdrawal_id = preview["withdrawal_id"]
    try:
        await db_bg.migrate_jobs.update_one({"id": job_id}, {"$set": {"status": "processing", "progress_phase": "updating_royalty_lines", "updated_at": now_iso()}})
        old_cutoff, new_cutoff = preview.get("old_cutoff"), preview["new_cutoff"]
        lines_changed = 0
        if old_cutoff and new_cutoff < old_cutoff:
            lines_changed = await _chunk_restore(
                label_id=preview["label_id"], after=new_cutoff, through=old_cutoff, job_id=job_id,
            )
        elif not old_cutoff or new_cutoff > old_cutoff:
            lines_changed = await _chunk_settle(
                label_id=preview["label_id"], after=old_cutoff, through=new_cutoff,
                job_id=job_id, withdrawal_id=withdrawal_id,
            )
        now = now_iso()
        withdrawal = await db_bg.withdraw_requests.find_one({"id": withdrawal_id}, {"_id": 0}) or {}
        update_set: Dict[str, Any] = {
            "period_to": preview["new_period_to"], "legacy_period_edited_at": now,
            "legacy_period_edited_by": user_id, "updated_at": now,
        }
        if withdrawal.get("manual_legacy"):
            update_set["manual_legacy_key"] = f"{withdrawal['label_id']}:{withdrawal.get('period_from')}:{preview['new_period_to']}:{withdrawal.get('request_date')}:{withdrawal.get('paid_date')}"
        await db_bg.withdraw_requests.update_one(
            {"id": withdrawal_id, "legacy_edit_lock_job_id": job_id},
            {"$set": update_set, "$push": {"legacy_period_revisions": {
                "old_period_to": preview["old_period_to"], "new_period_to": preview["new_period_to"],
                "old_cutoff": old_cutoff, "new_cutoff": new_cutoff, "job_id": job_id,
                "edited_by": user_id, "edited_at": now,
            }}},
        )
        await db_bg.labels.update_one({"id": preview["label_id"]}, {"$set": {
            "last_withdrawn_period": new_cutoff, "legacy_withdraw_period_end": new_cutoff,
            "legacy_withdraw_synced_at": now, "updated_at": now,
        }})
        snapshot = await compute_label_balance_snapshot(label_id=preview["label_id"])
        await db_bg.labels.update_one({"id": preview["label_id"]}, {"$set": {
            "balance_pending_idr": snapshot["balance_pending_idr"],
            "balance_available_idr": snapshot["balance_available_idr"],
            "balance_withdraw_requested_idr": snapshot["balance_withdraw_requested_idr"],
            "balance_snapshot_updated_at": now_iso(), "balance_snapshot_source": "legacy_withdraw_edit",
            "updated_at": now_iso(),
        }})
        await db_bg.balance_transactions.update_many(
            {"reference_id": withdrawal_id, "legacy_import": True},
            {"$set": {"description": f"[Legacy] Withdraw hingga laporan {preview['new_period_to']}", "updated_at": now_iso()}},
        )
        result = {
            "withdrawal_id": withdrawal_id, "old_period_to": preview["old_period_to"],
            "new_period_to": preview["new_period_to"], "old_cutoff": old_cutoff,
            "new_cutoff": new_cutoff, "royalty_lines_changed": lines_changed,
            "balance_pending_idr": snapshot["balance_pending_idr"],
            "balance_available_idr": snapshot["balance_available_idr"],
        }
        await log_activity(user_id, "legacy_withdraw_period_edit", "withdraw", withdrawal_id, before={
            "period_to": preview["old_period_to"], "cutoff": old_cutoff,
        }, after=result)
        await db_bg.migrate_jobs.update_one({"id": job_id}, {"$set": {
            "status": "done", "progress_phase": "done", "result": result,
            "finished_at": now_iso(), "updated_at": now_iso(),
        }})
        await trigger_royalty_caches()
    except Exception as exc:
        logger.exception("[LEGACY WITHDRAW EDIT] job=%s failed: %s", job_id, exc)
        await db_bg.migrate_jobs.update_one({"id": job_id}, {"$set": {
            "status": "error", "progress_phase": "error",
            "error_message": f"{type(exc).__name__}: {str(exc)[:400]}",
            "finished_at": now_iso(), "updated_at": now_iso(),
        }})
    finally:
        await db_bg.withdraw_requests.update_one(
            {"id": withdrawal_id, "legacy_edit_lock_job_id": job_id},
            {"$unset": {"legacy_edit_lock_job_id": ""}},
        )