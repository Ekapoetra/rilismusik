"""Seven distinct successful releases per label/day in Asia/Jakarta."""
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from pydantic import BaseModel
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from models import new_id, now_iso
from .deps import logger

DAILY_LIMIT = 7
WIB = ZoneInfo("Asia/Jakarta")


def quota_window(now=None):
    local = (now or datetime.now(timezone.utc)).astimezone(WIB)
    start = datetime.combine(local.date(), time.min, WIB).astimezone(timezone.utc)
    end = datetime.combine(local.date() + timedelta(days=1), time.min, WIB).astimezone(timezone.utc)
    return local.date().isoformat(), start.isoformat(), end.isoformat()


class SubmissionQuotaOut(BaseModel):
    day: str
    timezone: str = "Asia/Jakarta"
    limit: int = DAILY_LIMIT
    used: int
    pending: int
    remaining: int
    resets_at: str
    already_counted: bool = False


@asynccontextmanager
async def release_operation(db, release_id, operation):
    key = f"{operation}:{release_id}"; token = new_id(); now = now_iso()
    try:
        await db.release_operation_locks.find_one_and_update(
            {"_id": key, "$or": [{"expires_at": {"$lte": now}}, {"expires_at": {"$exists": False}}]},
            {"$set": {"token": token, "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()}},
            upsert=True, return_document=ReturnDocument.AFTER)
    except DuplicateKeyError:
        raise HTTPException(409, "Rilisan sedang diproses. Silakan tunggu lalu coba lagi.")
    try:
        yield token
    finally:
        await db.release_operation_locks.delete_one({"_id": key, "token": token})


async def daily_record(db, label_id, now=None):
    day, start, end = quota_window(now); key = f"{label_id}:{day}"
    record = await db.label_daily_submissions.find_one({"_id": key}, {"_id": 0})
    if not record:
        # Include successful web submissions earlier on the day this feature is enabled.
        historical = await db.releases.find({"label_id": label_id, "imported_legacy": {"$ne": True}, "$or": [
            {"submitted_at": {"$gte": start, "$lt": end}},
            {"status_history": {"$elemMatch": {"to": "submitted", "changed_at": {"$gte": start, "$lt": end}}}}]}, {"_id": 0, "id": 1}).to_list(10000)
        entries = [{"release_id": rid, "state": "committed", "token": "historical"} for rid in dict.fromkeys(r["id"] for r in historical)]
        try:
            await db.label_daily_submissions.update_one({"_id": key}, {"$setOnInsert": {"label_id": label_id, "day": day, "entries": entries}}, upsert=True)
        except DuplicateKeyError:
            pass
        record = await db.label_daily_submissions.find_one({"_id": key}, {"_id": 0})
    # Repair only this ledger's reservations after an interrupted request.
    for entry in record.get("entries", []):
        if entry.get("state") != "pending": continue
        receipt = await db.releases.find_one({"id": entry["release_id"], "label_id": label_id,
            "status_history.quota_token": entry["token"]}, {"_id": 0, "id": 1})
        if receipt:
            await db.label_daily_submissions.update_one({"_id": key, "entries.token": entry["token"]}, {"$set": {"entries.$.state": "committed"}})
        elif entry.get("expires_at", "") < now_iso():
            await db.label_daily_submissions.update_one({"_id": key}, {"$pull": {"entries": {"token": entry["token"], "state": "pending"}}})
    return key, end, await db.label_daily_submissions.find_one({"_id": key}, {"_id": 0})


async def submission_quota(db, label_id, release_id=None, now=None):
    _, end, record = await daily_record(db, label_id, now)
    entries = record.get("entries", []); used = sum(e["state"] == "committed" for e in entries)
    return SubmissionQuotaOut(day=record["day"], used=used, pending=len(entries) - used,
        remaining=max(0, DAILY_LIMIT - len(entries)), resets_at=end,
        already_counted=any(e["release_id"] == release_id and e["state"] == "committed" for e in entries))


@asynccontextmanager
async def submission_slot(db, label_id, release_id):
    async with release_operation(db, release_id, "submit") as token:
        key, end, record = await daily_record(db, label_id)
        existing = next((e for e in record.get("entries", []) if e["release_id"] == release_id), None)
        new_slot = existing is None
        if existing and existing["state"] == "pending":
            raise HTTPException(409, "Pengiriman sebelumnya masih diproses.")
        if new_slot:
            entry = {"release_id": release_id, "token": token, "state": "pending", "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()}
            reserved = await db.label_daily_submissions.find_one_and_update(
                {"_id": key, "entries.release_id": {"$ne": release_id}, f"entries.{DAILY_LIMIT - 1}": {"$exists": False}},
                {"$push": {"entries": entry}}, projection={"_id": 0}, return_document=ReturnDocument.AFTER)
            if not reserved:
                raise HTTPException(429, f"Kuota harian 7 rilisan telah habis. Kuota tersedia kembali pukul 00.00 WIB.", headers={"Retry-After": str(max(1, int((datetime.fromisoformat(end) - datetime.now(timezone.utc)).total_seconds())))})
        try:
            yield {"token": token, "day": record["day"]}
        finally:
            if new_slot:
                # Receipt is written atomically with the actual submitted status/history.
                try:
                    committed = await db.releases.find_one({"id": release_id, "label_id": label_id, "status_history.quota_token": token}, {"_id": 0, "id": 1})
                    if committed:
                        await db.label_daily_submissions.update_one({"_id": key, "entries.token": token}, {"$set": {"entries.$.state": "committed"}})
                    else:
                        await db.label_daily_submissions.update_one({"_id": key}, {"$pull": {"entries": {"token": token, "state": "pending"}}})
                except Exception:
                    logger.exception("Submission quota reservation awaits reconciliation")