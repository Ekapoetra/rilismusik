"""Extend the existing transaction journal; no second wallet or CSV mutation."""
from .deps import db_bg

ADJUSTMENT_TYPE = "royalty_admin_adjustment"


async def adjustment_balances(label_ids: list[str]) -> dict[str, int]:
    result = {label_id: 0 for label_id in label_ids}
    if not label_ids:
        return result
    async for row in db_bg.balance_transactions.aggregate([
        {"$match": {"label_id": {"$in": label_ids}, "type": ADJUSTMENT_TYPE, "status": "active"}},
        {"$group": {"_id": "$label_id", "amount": {"$sum": "$amount_idr"}}},
    ]):
        result[row["_id"]] = int(row["amount"])
    # An adjustment is spent ONLY when its existing withdrawal is paid.
    async for row in db_bg.withdraw_requests.aggregate([
        {"$match": {"label_id": {"$in": label_ids}, "status": "paid", "adjustment_amount_idr": {"$gt": 0}}},
        {"$group": {"_id": "$label_id", "amount": {"$sum": "$adjustment_amount_idr"}}},
    ]):
        result[row["_id"]] -= int(row["amount"])
    return result


async def unspent_adjustment_ids(label_id: str) -> list[str]:
    used = set()
    async for item in db_bg.withdraw_requests.find(
        {"label_id": label_id, "status": "paid", "adjustment_amount_idr": {"$gt": 0}},
        {"_id": 0, "adjustment_ids": 1},
    ):
        used.update(item.get("adjustment_ids") or [])
    return [item["id"] async for item in db_bg.balance_transactions.find(
        {"label_id": label_id, "type": ADJUSTMENT_TYPE, "status": "active", "id": {"$nin": list(used)}},
        {"_id": 0, "id": 1},
    )]


async def refresh_balance_cache(label_id: str):
    # Cache repair is repeatable; the journal/withdrawal record is authoritative.
    from .balance_utils import compute_label_balance_snapshot
    from models import now_iso
    from .deps import logger
    try:
        snapshot = await compute_label_balance_snapshot(label_id=label_id)
        await db_bg.labels.update_one({"id": label_id}, {"$set": {
            "balance_available_idr": snapshot["balance_available_idr"],
            "balance_pending_idr": snapshot["balance_pending_idr"],
            "balance_withdraw_requested_idr": snapshot["balance_withdraw_requested_idr"],
            "balance_snapshot_updated_at": now_iso(),
            "balance_snapshot_source": "royalty_lines_and_adjustments",
        }})
    except Exception:
        logger.exception("Derived adjustment balance cache refresh failed label=%s", label_id)