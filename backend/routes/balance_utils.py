"""Source-of-truth balance helpers based on FIFO royalty-line state."""
from typing import Any, Dict, Optional

from .deps import db_bg


async def compute_label_balance_snapshot(
    *, label_id: str, label: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    label_doc = label or await db_bg.labels.find_one(
        {"id": label_id},
        {
            "_id": 0,
            "last_withdrawn_period": 1,
            "balance_pending_idr": 1,
            "balance_available_idr": 1,
            "balance_withdraw_requested_idr": 1,
        },
    ) or {}
    cutoff = label_doc.get("last_withdrawn_period")
    period_filter: Dict[str, Any] = {"$exists": True, "$ne": None}
    if cutoff:
        period_filter["$gt"] = cutoff
    match = {
        "label_id": label_id,
        "status": {"$in": ["pending", "available"]},
        "legacy_settled": {"$ne": True},
        "period": period_filter,
    }
    grouped = {
        "pending_idr": 0,
        "available_idr": 0,
        "pending_lines": 0,
        "available_lines": 0,
        "period_from": None,
        "period_to": None,
        "available_period_from": None,
        "available_period_to": None,
    }
    async for row in db_bg.royalty_lines.aggregate([
        {"$match": match},
        {"$group": {
            "_id": None,
            "pending_idr": {"$sum": {"$cond": [{"$eq": ["$status", "pending"]}, "$label_idr", 0]}},
            "available_idr": {"$sum": {"$cond": [{"$eq": ["$status", "available"]}, "$label_idr", 0]}},
            "pending_lines": {"$sum": {"$cond": [{"$eq": ["$status", "pending"]}, 1, 0]}},
            "available_lines": {"$sum": {"$cond": [{"$eq": ["$status", "available"]}, 1, 0]}},
            "period_from": {"$min": "$period"},
            "period_to": {"$max": "$period"},
            "available_period_from": {"$min": {"$cond": [{"$eq": ["$status", "available"]}, "$period", None]}},
            "available_period_to": {"$max": {"$cond": [{"$eq": ["$status", "available"]}, "$period", None]}},
        }},
    ], allowDiskUse=True):
        grouped.update({
            "pending_idr": int(row.get("pending_idr") or 0),
            "available_idr": int(row.get("available_idr") or 0),
            "pending_lines": int(row.get("pending_lines") or 0),
            "available_lines": int(row.get("available_lines") or 0),
            "period_from": row.get("period_from"),
            "period_to": row.get("period_to"),
            "available_period_from": row.get("available_period_from"),
            "available_period_to": row.get("available_period_to"),
        })

    active_withdraws = await db_bg.withdraw_requests.find({
        "label_id": label_id,
        "status": {"$in": ["requested", "approved"]},
        "legacy_import": {"$ne": True},
    }, {"_id": 0, "id": 1, "amount_idr": 1}).to_list(100)
    active_amount = sum(int(item.get("amount_idr") or 0) for item in active_withdraws)
    # Existing active requests reserve lines while their status is still
    # `available`; subtract the reserved amount for a truthful display.
    effective_available = max(grouped["available_idr"] - active_amount, 0)
    latest = await db_bg.royalty_lines.find_one(
        {"label_id": label_id, "period": {"$type": "string"}},
        {"_id": 0, "period": 1},
        sort=[("period", -1)],
    )
    return {
        "last_withdrawn_period": cutoff,
        "latest_report_period": (latest or {}).get("period"),
        "balance_pending_idr": max(grouped["pending_idr"], 0),
        "balance_available_idr": effective_available,
        "balance_withdraw_requested_idr": max(active_amount, 0),
        "source_available_idr": max(grouped["available_idr"], 0),
        "pending_lines": grouped["pending_lines"],
        "available_lines": grouped["available_lines"],
        "period_from": grouped["period_from"],
        "period_to": grouped["period_to"],
        "available_period_from": grouped["available_period_from"],
        "available_period_to": grouped["available_period_to"],
        "active_withdraw_ids": [item["id"] for item in active_withdraws],
        "has_active_withdraw": bool(active_withdraws),
        "stored_pending_idr": int(label_doc.get("balance_pending_idr") or 0),
        "stored_available_idr": int(label_doc.get("balance_available_idr") or 0),
        "stored_withdraw_requested_idr": int(label_doc.get("balance_withdraw_requested_idr") or 0),
    }