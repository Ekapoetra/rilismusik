"""Materialize source-of-truth available balances without blocking list requests."""
import asyncio
import time

from pymongo import UpdateOne
from pymongo.errors import DuplicateKeyError

from models import now_iso
from .balance_utils import compute_labels_available_balances
from .deps import db_bg, logger


SNAPSHOT_ID = "label_available_balances"
FRESH_SECONDS = 10 * 60
STALE_RUNNING_SECONDS = 60 * 60


async def snapshot_status() -> dict:
    document = await db_bg.metrics_cache.find_one({"_id": SNAPSHOT_ID}, {"_id": 0})
    return document or {"status": "never_run", "labels_count": 0}


async def start_label_balance_snapshot_refresh(*, force: bool = False, reason: str = "scheduled") -> dict:
    now_epoch = time.time()
    current = await db_bg.metrics_cache.find_one({"_id": SNAPSHOT_ID}, {"_id": 0}) or {}
    if current.get("status") == "running" and now_epoch - float(current.get("started_epoch") or 0) < STALE_RUNNING_SECONDS:
        return {**current, "already_running": True}
    if not force and current.get("status") == "done" and now_epoch - float(current.get("finished_epoch") or 0) < FRESH_SECONDS:
        return {**current, "already_fresh": True}
    stale_before = now_epoch - STALE_RUNNING_SECONDS
    claim_filter = {
        "_id": SNAPSHOT_ID,
        "$or": [
            {"status": {"$ne": "running"}},
            {"started_epoch": {"$lt": stale_before}},
            {"started_epoch": {"$exists": False}},
        ],
    }
    try:
        claimed = await db_bg.metrics_cache.update_one(
            claim_filter,
            {"$set": {
                "status": "running", "reason": reason, "started_at": now_iso(),
                "started_epoch": now_epoch, "updated_at": now_iso(), "error_message": None,
            }},
            upsert=not bool(current),
        )
    except DuplicateKeyError:
        return {**(await snapshot_status()), "already_running": True}
    if not claimed.matched_count and not claimed.upserted_id:
        return {**(await snapshot_status()), "already_running": True}
    asyncio.create_task(recompute_label_balance_snapshots())
    return {**(await snapshot_status()), "queued": True}


async def recompute_label_balance_snapshots() -> dict:
    started = time.perf_counter()
    try:
        labels = await db_bg.labels.find({}, {
            "_id": 0, "id": 1, "last_withdrawn_period": 1,
        }).to_list(20000)
        balances = await compute_labels_available_balances(labels)
        timestamp = now_iso()
        operations = [
            UpdateOne(
                {"id": label["id"]},
                {"$set": {
                    "balance_available_idr": int(balances.get(label["id"], 0)),
                    "balance_snapshot_updated_at": timestamp,
                    "balance_snapshot_source": "royalty_lines",
                }},
            ) for label in labels
        ]
        for start in range(0, len(operations), 500):
            await db_bg.labels.bulk_write(operations[start:start + 500], ordered=False)
        duration = round(time.perf_counter() - started, 3)
        result = {"labels_count": len(labels), "duration_seconds": duration}
        await db_bg.metrics_cache.update_one({"_id": SNAPSHOT_ID}, {"$set": {
            "status": "done", "result": result, "labels_count": len(labels),
            "finished_at": now_iso(), "finished_epoch": time.time(), "updated_at": now_iso(),
        }}, upsert=True)
        logger.info("[LABEL BALANCE SNAPSHOT] updated %d labels in %.3fs", len(labels), duration)
        return result
    except Exception as exc:
        logger.exception("[LABEL BALANCE SNAPSHOT] failed: %s", exc)
        await db_bg.metrics_cache.update_one({"_id": SNAPSHOT_ID}, {"$set": {
            "status": "error", "error_message": f"{type(exc).__name__}: {str(exc)[:400]}",
            "finished_at": now_iso(), "finished_epoch": time.time(), "updated_at": now_iso(),
        }}, upsert=True)
        raise