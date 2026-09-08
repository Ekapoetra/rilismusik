"""Read-only source breakdown and server-owned adjustment previews."""
import hashlib
import json
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from fastapi import HTTPException

from .deps import db, db_bg
from .balance_utils import compute_label_balance_snapshot
from .royalty_adjustment_balance import ADJUSTMENT_TYPE
from .royalty_adjustment_models import AdjustmentInput, AdjustmentPreview


def balance_fingerprint(balance: dict) -> str:
    values = {key: value for key, value in balance.items() if not key.startswith("stored_")}
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


async def source_summary(label_id: str, legacy_period_to: str | None = None):
    label = await db.labels.find_one({"id": label_id}, {"_id": 0})
    if not label:
        raise HTTPException(404, "Label tidak ditemukan")
    latest = await db.balance_transactions.find_one(
        {"label_id": label_id, "type": ADJUSTMENT_TYPE}, {"_id": 0, "legacy_period_to": 1},
        sort=[("created_at", -1)],
    )
    boundary = legacy_period_to or (latest or {}).get("legacy_period_to")
    balance = await compute_label_balance_snapshot(label_id=label_id, label=label)
    legacy = 0
    if boundary:
        periods = {"$lte": boundary}
        if balance["last_withdrawn_period"]:
            periods["$gt"] = balance["last_withdrawn_period"]
        async for row in db_bg.royalty_lines.aggregate([
            {"$match": {"label_id": label_id, "status": "available", "legacy_settled": {"$ne": True}, "period": periods}},
            {"$group": {"_id": None, "amount": {"$sum": "$label_idr"}}},
        ]):
            legacy = int(row["amount"])
    return {
        "label_id": label_id, "label_name": label.get("label_name") or label_id,
        "legacy_period_to": boundary,
        "believe_legacy_idr": legacy if boundary else None,
        "new_royalty_idr": balance["source_available_idr"] - legacy if boundary else None,
        "unclassified_csv_idr": 0 if boundary else balance["source_available_idr"],
        "admin_adjustment_idr": balance["adjustment_available_idr"],
        "withdraw_reserved_idr": balance["balance_withdraw_requested_idr"],
        "balance_available_idr": balance["balance_available_idr"],
        "has_active_withdraw": balance["has_active_withdraw"],
        "legacy_needs_review": bool(boundary and legacy > 0),
    }, balance


async def preview_adjustment(label_id: str, body: AdjustmentInput, user: dict):
    summary, balance = await source_summary(label_id, body.legacy_period_to)
    if balance["has_active_withdraw"]:
        raise HTTPException(409, "Selesaikan atau tolak penarikan yang sedang diproses sebelum menyesuaikan saldo.")
    if balance["adjustment_available_idr"] < 0:
        raise HTTPException(409, "Jurnal penyesuaian tidak konsisten. Periksa riwayat sebelum melanjutkan.")
    timestamp = datetime.now(timezone.utc)
    preview_id = str(uuid4())
    result = AdjustmentPreview(
        preview_id=preview_id, label_id=label_id, label_name=summary["label_name"],
        amount_idr=body.amount_idr, balance_before_idr=balance["balance_available_idr"],
        balance_after_idr=balance["balance_available_idr"] + body.amount_idr,
        legacy_balance_before_idr=summary["believe_legacy_idr"],
        new_royalty_before_idr=summary["new_royalty_idr"],
        existing_adjustment_idr=summary["admin_adjustment_idr"],
        legacy_period_to=body.legacy_period_to, reason=body.reason, reference=body.reference,
        reference_amount_idr=body.reference_amount_idr,
        reference_difference_idr=(body.reference_amount_idr - summary["believe_legacy_idr"] if body.reference_amount_idr is not None else None),
        expires_at=(timestamp + timedelta(minutes=15)).isoformat(),
    )
    await db.royalty_adjustment_previews.insert_one({
        "_id": preview_id, **result.model_dump(), "payload": body.model_dump(),
        "created_by": user["id"], "created_at": timestamp.isoformat(),
        "fingerprint": balance_fingerprint(balance),
    })
    return result