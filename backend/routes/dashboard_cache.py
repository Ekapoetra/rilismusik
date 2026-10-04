from background_runtime import run_background, serverless_runtime
import hashlib
"""Dashboard revenue cache with no dependency on route modules."""
import asyncio
import time
from typing import Any, Dict

from .deps import db, db_bg, logger


DASHBOARD_REVENUE_TTL_SEC = 60
_cache: Dict[str, Any] = {
    "total_eur": 0,
    "total_idr": 0,
    "withdrawn_idr": 0,
    "unwithdrawn_idr": 0,
    "computed_at": 0.0,
    "refreshing": False,
}


def snapshot() -> Dict[str, Any]:
    return dict(_cache)


def reset() -> None:
    _cache.update({
        "total_eur": 0, "total_idr": 0, "withdrawn_idr": 0,
        "unwithdrawn_idr": 0, "computed_at": 0.0, "refreshing": False,
    })


async def recompute() -> Dict[str, Any]:
    _cache["refreshing"] = True
    try:
        total_eur = 0
        total_idr = 0
        withdrawn_idr = 0
        pipeline = [{"$group": {
            "_id": None,
            "total_eur": {"$sum": "$revenue_eur"},
            "total_idr": {"$sum": "$label_idr"},
            "withdrawn_idr": {"$sum": {"$cond": [
                {"$or": [
                    {"$eq": ["$status", "withdrawn"]},
                    {"$eq": ["$legacy_settled", True]},
                ]},
                {"$ifNull": ["$label_idr", 0]}, 0,
            ]}},
        }}]
        async for row in db_bg.royalty_lines.aggregate(pipeline, allowDiskUse=True):
            total_eur = row.get("total_eur", 0) or 0
            total_idr = row.get("total_idr", 0) or 0
            withdrawn_idr = row.get("withdrawn_idr", 0) or 0
        unwithdrawn_idr = total_idr - withdrawn_idr
        computed_at = time.time()
        _cache.update({
            "total_eur": total_eur, "total_idr": total_idr,
            "withdrawn_idr": withdrawn_idr, "unwithdrawn_idr": unwithdrawn_idr,
            "computed_at": computed_at,
        })
        try:
            await db_bg.metrics_cache.update_one(
                {"_id": "dashboard_revenue"},
                {"$set": {
                    "total_eur": total_eur, "total_idr": total_idr,
                    "withdrawn_idr": withdrawn_idr, "unwithdrawn_idr": unwithdrawn_idr,
                    "computed_at": computed_at,
                }},
                upsert=True,
            )
        except Exception as exc:
            logger.warning("[DASHBOARD CACHE] mongo persist failed (non-fatal): %s", exc)
    except Exception as exc:
        logger.warning("[DASHBOARD CACHE] recompute failed (non-fatal): %s", exc)
    finally:
        _cache["refreshing"] = False
    return snapshot()


async def _warm_from_mongo() -> None:
    if _cache["computed_at"] and (not serverless_runtime() or time.time() - _cache["computed_at"] < 10):
        return
    try:
        persisted = await db.metrics_cache.find_one({"_id": "dashboard_revenue"}, {"_id": 0})
        if persisted:
            if "withdrawn_idr" not in persisted or "unwithdrawn_idr" not in persisted:
                return
            _cache.update({
                "total_eur": persisted.get("total_eur", 0) or 0,
                "total_idr": persisted.get("total_idr", 0) or 0,
                "withdrawn_idr": persisted.get("withdrawn_idr", 0) or 0,
                "unwithdrawn_idr": persisted.get("unwithdrawn_idr", 0) or 0,
                "computed_at": persisted.get("computed_at", 0) or 0,
            })
    except Exception as exc:
        logger.warning("[DASHBOARD CACHE] mongo warm-load failed: %s", exc)


async def get_stale_while_revalidate() -> Dict[str, Any]:
    await _warm_from_mongo()
    if not _cache["computed_at"]:
        return await recompute()
    age = time.time() - _cache["computed_at"]
    if age > DASHBOARD_REVENUE_TTL_SEC and not _cache["refreshing"]:
        try:
            await schedule_recompute()
        except Exception as exc:
            logger.warning("Dashboard refresh dispatch failed (%s)", type(exc).__name__)
    result = snapshot()
    result["age_sec"] = int(age)
    return result


async def schedule_recompute() -> None:
    if not _cache["refreshing"]:
        if serverless_runtime():
            identity = hashlib.sha256(f"dashboard:{int(time.time() // 60)}".encode()).hexdigest()[:32]
            await run_background(recompute, _dispatch_id=identity)
        else:
            await run_background(recompute)
