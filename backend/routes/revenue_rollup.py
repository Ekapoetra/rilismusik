"""Revenue rollup helpers — Phase 21.

Given a list of artist_ids or release_ids and an optional period range, return
the aggregate revenue (EUR + IDR) and earliest/latest period each entity was
active in. Reads from `royalty_lines` via the CSOT-uncapped `db_bg` client
because production has 1M+ rows.

Used by both admin & label list endpoints so the table can render:
  - Total revenue per artist / release
  - Last active "bulan laporan"
  - Number of royalty lines

Period filter format: YYYY-MM strings (matches `royalty_lines.period`).
"""
from typing import Any, Dict, List, Optional

from .deps import db_bg


async def rollup_revenue_by_id(
    *,
    field: str,
    ids: List[str],
    period_from: Optional[str] = None,
    period_to: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """Aggregate revenue per `<field>` key over `royalty_lines`.

    `field` must be one of: 'artist_id', 'release_id', 'label_id', 'track_id'.
    Returns: { id: {revenue_eur, revenue_idr, lines, first_period, last_period} }

    Lines whose match_status isn't matched/manually_matched are excluded
    because their FK to label/release/artist is unreliable.
    """
    if not ids:
        return {}

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
