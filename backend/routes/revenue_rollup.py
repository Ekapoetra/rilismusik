"""Revenue rollup helpers.

Phase 21: live aggregate against royalty_lines (slow on 1M+ rows).
Phase 24: read from materialized `monthly_analytics` cache (sub-second).
         Live fallback kept for graceful degradation if the cache is empty
         (e.g. brand-new deploy, or right after a backfill before the
         async recompute finishes).

Used by Artist Management, Release Management, Label list endpoints — anywhere
we need "total revenue per N entities, optionally filtered by period range".

Period filter format: YYYY-MM strings (matches `royalty_lines.period` and the
cache's `monthly_analytics.period`).
"""
from typing import Any, Dict, List, Optional

from .deps import db_bg


# Mapping from "logical dim" → field name in royalty_lines used by the live
# aggregate. The cache reads use `dim=` directly.
DIM_FIELD_MAP = {
    "artist": "artist_id",
    "release": "release_id",
    "label": "label_id",
    "track": "track_id",
}


async def _rollup_from_cache(
    *,
    dim: str,
    ids: List[str],
    period_from: Optional[str],
    period_to: Optional[str],
) -> Dict[str, Dict[str, Any]]:
    """Read rolled-up revenue from `monthly_analytics` (Phase 24 fast path).

    Each `monthly_analytics` doc is one (period, dim, key) slice. We sum
    across the requested period range per entity. Returns empty dict if the
    cache has zero docs for this dim (signals to caller to fall back to live).
    """
    match: Dict[str, Any] = {"dim": dim, "key": {"$in": ids}}
    if period_from or period_to:
        period_filter: Dict[str, Any] = {}
        if period_from:
            period_filter["$gte"] = period_from
        if period_to:
            period_filter["$lte"] = period_to
        match["period"] = period_filter

    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": "$key",
            "revenue_eur": {"$sum": "$revenue_eur"},
            "revenue_idr": {"$sum": "$revenue_idr"},
            "lines": {"$sum": "$lines_count"},
            "first_period": {"$min": "$period"},
            "last_period": {"$max": "$period"},
            "quantity": {"$sum": "$quantity"},
        }},
    ]
    out: Dict[str, Dict[str, Any]] = {}
    async for r in db_bg.monthly_analytics.aggregate(pipeline, allowDiskUse=True):
        if not r.get("_id"):
            continue
        out[r["_id"]] = {
            "revenue_eur": round(r.get("revenue_eur") or 0, 4),
            "revenue_idr": int(r.get("revenue_idr") or 0),
            "lines": int(r.get("lines") or 0),
            "first_period": r.get("first_period"),
            "last_period": r.get("last_period"),
            "quantity": int(r.get("quantity") or 0),
        }
    return out


async def _rollup_live(
    *,
    field: str,
    ids: List[str],
    period_from: Optional[str],
    period_to: Optional[str],
) -> Dict[str, Dict[str, Any]]:
    """Slow path: live aggregate over royalty_lines. Used as fallback when
    the materialized cache hasn't been built yet.
    """
    match: Dict[str, Any] = {
        field: {"$in": ids},
        "match_status": {"$in": ["matched", "manually_matched"]},
    }
    if period_from or period_to:
        period_filter: Dict[str, Any] = {}
        if period_from:
            period_filter["$gte"] = period_from
        if period_to:
            period_filter["$lte"] = period_to
        match["period"] = period_filter

    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": f"${field}",
            "revenue_eur": {"$sum": "$revenue_eur"},
            "revenue_idr": {"$sum": "$label_idr"},
            "lines": {"$sum": 1},
            "first_period": {"$min": "$period"},
            "last_period": {"$max": "$period"},
            "quantity": {"$sum": "$quantity"},
        }},
    ]
    out: Dict[str, Dict[str, Any]] = {}
    async for r in db_bg.royalty_lines.aggregate(pipeline, allowDiskUse=True):
        if not r.get("_id"):
            continue
        out[r["_id"]] = {
            "revenue_eur": round(r.get("revenue_eur") or 0, 4),
            "revenue_idr": int(r.get("revenue_idr") or 0),
            "lines": int(r.get("lines") or 0),
            "first_period": r.get("first_period"),
            "last_period": r.get("last_period"),
            "quantity": int(r.get("quantity") or 0),
        }
    return out


async def rollup_revenue_by_id(
    *,
    field: str,
    ids: List[str],
    period_from: Optional[str] = None,
    period_to: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """Aggregate revenue per `<field>` key.

    `field` must be one of: 'artist_id', 'release_id', 'label_id', 'track_id'.
    Returns: { id: {revenue_eur, revenue_idr, lines, first_period, last_period, quantity} }

    Phase 24: tries the materialized cache first (sub-second). If the cache
    is empty for this dim (e.g. fresh deploy, post-restart, post-backfill),
    falls back to a live aggregate over royalty_lines and silently triggers
    a cache rebuild in the background.

    Lines whose match_status isn't matched/manually_matched are excluded by
    the cache builder (and by the live fallback). Unmatched lines have
    unreliable FK to label/release/artist so they'd pollute the totals.
    """
    if not ids:
        return {}

    # Derive logical dim from field name. Supports both 'artist_id' and 'artist'.
    dim = field[:-3] if field.endswith("_id") else field
    if dim not in DIM_FIELD_MAP:
        # Unknown dim → live path is the only safe option
        return await _rollup_live(
            field=field, ids=ids, period_from=period_from, period_to=period_to,
        )

    # Fast path: read from monthly_analytics cache.
    cached = await _rollup_from_cache(
        dim=dim, ids=ids, period_from=period_from, period_to=period_to,
    )
    if cached:
        return cached

    # Cache miss for this dim — fall back to live and trigger a rebuild
    # asynchronously so the next page load is fast.
    import asyncio
    import logging
    logger = logging.getLogger("rilismusik")
    logger.warning("[ROLLUP] cache empty for dim=%s, falling back to live", dim)
    try:
        from .admin_analytics import recompute_monthly_analytics
        asyncio.create_task(recompute_monthly_analytics())
    except Exception:
        pass

    return await _rollup_live(
        field=DIM_FIELD_MAP[dim], ids=ids, period_from=period_from, period_to=period_to,
    )
