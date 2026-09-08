"""One atomic journal write per adjustment; source balances are derived."""
from datetime import datetime, timezone
from fastapi import HTTPException
from models import now_iso
from .deps import db, log_activity, logger
from .financial_lock import label_financial_lock
from .royalty_adjustment_balance import ADJUSTMENT_TYPE, refresh_balance_cache
from .royalty_adjustment_service import source_summary, balance_fingerprint
from .royalty_adjustment_models import AdjustmentRecord, AdjustmentResult


async def _audit(user, action, record):
    try:
        await log_activity(user["id"], action, "royalty_adjustment", record["id"], after={
            key: record.get(key) for key in ("label_id", "amount_idr", "reason", "reference", "status", "void_reason", "balance_before_idr", "balance_after_idr")
        })
    except Exception:
        # Complete audit identity/reason/balances also live in the financial record.
        logger.exception("Adjustment activity-log mirror failed id=%s", record["id"])


async def commit_adjustment(label_id, preview_id, user):
    adjustment_id = f"AJ-{preview_id}"
    async with label_financial_lock(label_id):
        existing = await db.balance_transactions.find_one({"_id": adjustment_id, "label_id": label_id}, {"_id": 0})
        if existing:
            if existing["created_by"] != user["id"]:
                raise HTTPException(403, "Pratinjau bukan milik admin ini")
            await refresh_balance_cache(label_id)
            summary, _ = await source_summary(label_id)
            return AdjustmentResult(adjustment=AdjustmentRecord(**existing), replayed=True, balance_available_idr=summary["balance_available_idr"])
        preview = await db.royalty_adjustment_previews.find_one({"_id": preview_id, "label_id": label_id}, {"_id": 0})
        if not preview:
            raise HTTPException(404, "Pratinjau tidak ditemukan")
        if preview["created_by"] != user["id"]:
            raise HTTPException(403, "Pratinjau bukan milik admin ini")
        if datetime.fromisoformat(preview["expires_at"]) <= datetime.now(timezone.utc):
            raise HTTPException(409, "Pratinjau kedaluwarsa. Buat pratinjau baru.")
        summary, balance = await source_summary(label_id, preview["legacy_period_to"])
        if balance["has_active_withdraw"] or balance_fingerprint(balance) != preview["fingerprint"] or summary["believe_legacy_idr"] != preview["legacy_balance_before_idr"]:
            raise HTTPException(409, "Saldo berubah sejak pratinjau. Tinjau ulang sebelum mengonfirmasi.")
        record = {
            "id": adjustment_id, "label_id": label_id, "type": ADJUSTMENT_TYPE,
            "source": "ADMIN_ADJUSTMENT", **preview["payload"], "status": "active",
            "balance_before_idr": preview["balance_before_idr"], "balance_after_idr": preview["balance_after_idr"],
            "legacy_balance_before_idr": preview["legacy_balance_before_idr"],
            "created_by": user["id"], "created_by_name": user.get("name") or user["id"], "created_at": now_iso(),
            "reference_type": "royalty_adjustment", "reference_id": adjustment_id,
            "idempotency_key": preview_id, "description": preview["reason"],
        }
        # _id is the durable idempotency constraint, even before background indexes finish.
        await db.balance_transactions.insert_one({"_id": adjustment_id, **record})
        await _audit(user, "royalty_adjustment_created", record)
        await refresh_balance_cache(label_id)
        return AdjustmentResult(adjustment=AdjustmentRecord(**record, can_void=True), balance_available_idr=record["balance_after_idr"])


async def void_adjustment(label_id, adjustment_id, reason, user):
    async with label_financial_lock(label_id):
        record = await db.balance_transactions.find_one({"id": adjustment_id, "label_id": label_id, "type": ADJUSTMENT_TYPE}, {"_id": 0})
        if not record:
            raise HTTPException(404, "Penyesuaian tidak ditemukan")
        summary, balance = await source_summary(label_id)
        if record["status"] == "voided":
            return AdjustmentResult(adjustment=AdjustmentRecord(**record), replayed=True, balance_available_idr=balance["balance_available_idr"])
        allocated = await db.withdraw_requests.find_one({
            "label_id": label_id, "adjustment_ids": adjustment_id, "status": {"$in": ["requested", "approved", "paid"]},
        }, {"_id": 0, "id": 1})
        if allocated or balance["has_active_withdraw"]:
            raise HTTPException(409, "Penyesuaian tidak dapat dibatalkan karena dana sedang diproses atau sudah ditarik.")
        if balance["balance_available_idr"] < record["amount_idr"]:
            raise HTTPException(409, "Pembatalan akan membuat saldo negatif.")
        update = {
            "status": "voided", "voided_by": user["id"], "voided_by_name": user.get("name") or user["id"],
            "voided_at": now_iso(), "void_reason": reason,
            "void_balance_before_idr": balance["balance_available_idr"],
            "void_balance_after_idr": balance["balance_available_idr"] - record["amount_idr"],
        }
        await db.balance_transactions.update_one({"id": adjustment_id, "status": "active"}, {"$set": update})
        record.update(update)
        await _audit(user, "royalty_adjustment_voided", record)
        await refresh_balance_cache(label_id)
        return AdjustmentResult(adjustment=AdjustmentRecord(**record), balance_available_idr=update["void_balance_after_idr"])