"""Idempotent monthly royalty summary email service."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from email_service import send_monthly_royalty_summary_email
from models import now_iso
from .deps import db, logger


async def build_monthly_summary(label_id: str, period: str) -> dict | None:
    totals = await db.royalty_lines.aggregate([
        {"$match": {"label_id": label_id, "period": period}},
        {"$group": {"_id": None, "total_idr": {"$sum": {"$ifNull": ["$label_idr", 0]}}, "streams": {"$sum": {"$ifNull": ["$quantity", 0]}}, "lines": {"$sum": 1}}},
    ]).to_list(1)
    if not totals:
        return None
    top_tracks = await db.royalty_lines.aggregate([
        {"$match": {"label_id": label_id, "period": period}},
        {"$group": {"_id": {"$ifNull": ["$track_title_raw", "Unknown"]}, "streams": {"$sum": {"$ifNull": ["$quantity", 0]}}, "revenue_idr": {"$sum": {"$ifNull": ["$label_idr", 0]}}}},
        {"$sort": {"streams": -1, "revenue_idr": -1}}, {"$limit": 5},
    ]).to_list(5)
    row = totals[0]
    return {
        "label_id": label_id, "period": period, "total_idr": int(row.get("total_idr") or 0),
        "streams": int(row.get("streams") or 0), "lines": int(row.get("lines") or 0),
        "top_tracks": [{"title": item.get("_id") or "Unknown", "streams": int(item.get("streams") or 0), "revenue_idr": int(item.get("revenue_idr") or 0)} for item in top_tracks],
    }


async def send_one_monthly_summary(label_id: str, period: str) -> str:
    existing = await db.monthly_email_deliveries.find_one({"label_id": label_id, "period": period}, {"_id": 0, "status": 1})
    if existing and existing.get("status") in {"sent", "processing"}:
        return "already-sent" if existing["status"] == "sent" else "already-processing"
    try:
        claimed = await db.monthly_email_deliveries.find_one_and_update(
            {"label_id": label_id, "period": period, "status": {"$in": ["pending", "failed"]}},
            {"$set": {"status": "processing", "updated_at": now_iso()}, "$setOnInsert": {"label_id": label_id, "period": period, "created_at": now_iso()}, "$inc": {"attempts": 1}},
            upsert=True, return_document=ReturnDocument.AFTER,
        )
    except DuplicateKeyError:
        return "already-processing"
    if not claimed:
        return "already-processing"
    summary = await build_monthly_summary(label_id, period)
    label = await db.labels.find_one({"id": label_id}, {"_id": 0, "label_name": 1, "user_id": 1})
    recipient = await db.users.find_one({"id": (label or {}).get("user_id")}, {"_id": 0, "email": 1, "status": 1}) if label else None
    if not summary or not recipient or not recipient.get("email") or recipient.get("status") in {"disabled", "suspended"}:
        await db.monthly_email_deliveries.update_one({"label_id": label_id, "period": period}, {"$set": {"status": "failed", "error": "missing_summary_or_recipient", "updated_at": now_iso()}})
        return "failed"
    message_id = await send_monthly_royalty_summary_email(
        to=recipient["email"], label_name=(label or {}).get("label_name") or "Label", period=period,
        total_idr=summary["total_idr"], streams=summary["streams"], top_tracks=summary["top_tracks"],
    )
    if message_id:
        await db.monthly_email_deliveries.update_one({"label_id": label_id, "period": period}, {"$set": {"status": "sent", "message_id": message_id, "summary": summary, "sent_at": now_iso(), "updated_at": now_iso()}, "$unset": {"error": ""}})
        return "sent"
    await db.monthly_email_deliveries.update_one({"label_id": label_id, "period": period}, {"$set": {"status": "failed", "error": "smtp_failed", "updated_at": now_iso()}})
    return "failed"


async def send_monthly_summaries(period: str | None = None) -> dict:
    if not period:
        local_now = datetime.now(ZoneInfo("Asia/Jakarta"))
        period = (local_now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    label_rows = await db.royalty_lines.aggregate([
        {"$match": {"period": period, "label_id": {"$ne": None}}},
        {"$group": {"_id": "$label_id"}},
    ]).to_list(None)
    result = {"period": period, "sent": 0, "failed": 0, "skipped": 0}
    for row in label_rows:
        try:
            status = await send_one_monthly_summary(str(row["_id"]), period)
            if status == "sent": result["sent"] += 1
            elif status == "failed": result["failed"] += 1
            else: result["skipped"] += 1
        except Exception as exc:
            logger.exception("Monthly royalty email failed label=%s period=%s: %s", row["_id"], period, exc)
            result["failed"] += 1
    return result