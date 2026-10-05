"""Customer-facing label analytics for published royalty reports."""
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Literal

from fastapi import APIRouter, Depends, Query

from models import now_iso
from .deps import db_bg, get_label_by_user, get_labels_for_user, account_entitlements, require_label
from fastapi import HTTPException


label_analytics_r = APIRouter(prefix="/label/analytics", tags=["label-analytics"])
VISIBLE_STATUSES = ["pending", "available", "withdrawn"]
# Legacy-settled lines are marked `withdrawn` while their import may still be a
# draft, so they only count once the import itself has been published.
PUBLISHED_IMPORT_STATUSES = ["published", "receiving", "receive_error", "dana_received"]
# Legacy royalty was settled before the label joined and is never disclosed;
# its streams are still the label's own performance and stay visible.
LEGACY_LINE = {"$eq": ["$legacy_settled", True]}
VISIBLE_REVENUE = {"$cond": [LEGACY_LINE, 0, {"$ifNull": ["$label_idr", 0]}]}
LEGACY_STREAMS = {"$cond": [LEGACY_LINE, {"$ifNull": ["$quantity", 0]}, 0]}
LEGACY_COUNT = {"$cond": [LEGACY_LINE, 1, 0]}


async def label_visibility_filter(label_ids: List[str]) -> Dict[str, Any]:
    published_imports = await db_bg.royalty_imports.distinct("id", {"status": {"$in": PUBLISHED_IMPORT_STATUSES}})
    return {
        "label_id": {"$in": label_ids},
        "status": {"$in": VISIBLE_STATUSES},
        "replacement_stage": {"$ne": True},
        "period": {"$type": "string"},
        "$or": [
            {"legacy_settled": {"$ne": True}},
            {"import_id": {"$in": published_imports}},
        ],
    }


def _summary_group(group_id: Any) -> Dict[str, Any]:
    return {
        "_id": group_id,
        "streams": {"$sum": "$quantity"},
        "revenue_idr": {"$sum": VISIBLE_REVENUE},
        "lines": {"$sum": 1},
        "legacy_streams": {"$sum": LEGACY_STREAMS},
        "legacy_lines": {"$sum": LEGACY_COUNT},
    }


def _summary(row: Dict[str, Any]) -> Dict[str, int]:
    return {
        "streams": int(row.get("streams") or 0),
        "revenue_idr": int(row.get("revenue_idr") or 0),
        "lines": int(row.get("lines") or 0),
    }


def _shift_month(period: str, offset: int) -> str:
    parsed = datetime.strptime(period, "%Y-%m")
    month_index = parsed.year * 12 + parsed.month - 1 + offset
    return f"{month_index // 12:04d}-{month_index % 12 + 1:02d}"


def _period_sequence(period_from: str, period_to: str) -> List[str]:
    periods = []
    current = period_from
    while current <= period_to and len(periods) < 120:
        periods.append(current)
        current = _shift_month(current, 1)
    return periods


@label_analytics_r.get("")
async def get_label_dashboard_analytics(
    window: Literal["latest", "6", "12"] = Query(default="latest"),
    label_id: str = Query(default=None),
    user: dict = Depends(require_label),
):
    # Multi Label defaults to ALL owned labels (aggregated). A label_id filter must
    # belong to the account (ownership enforced server-side). Only final label_idr is
    # exposed — no distributor fee / gross / EUR split ever leaves the server.
    owned = await get_labels_for_user(user)
    owned_ids = [l["id"] for l in owned]
    name_map = {l["id"]: l.get("label_name") for l in owned}
    ent = await account_entitlements(user)
    if label_id:
        if label_id not in owned_ids:
            raise HTTPException(status_code=404, detail="Label tidak ditemukan pada akun ini")
        label_ids = [label_id]
        scope = "label"
    elif ent.get("multi_label") and len(owned_ids) > 1:
        label_ids = owned_ids
        scope = "all"
    else:
        active = await get_label_by_user(user)
        label_ids = [active["id"]]
        scope = "label"
    visibility = await label_visibility_filter(label_ids)
    latest_doc = await db_bg.royalty_lines.find_one(
        visibility, {"_id": 0, "period": 1}, sort=[("period", -1)],
    )
    latest_period = (latest_doc or {}).get("period")
    legacy_empty = {"streams": 0, "lines": 0, "periods": [], "revenue_hidden": True}
    if not latest_period:
        return {
            "window": window,
            "period_from": None,
            "period_to": None,
            "latest_period": None,
            "available_periods": [],
            "scope": scope,
            "selected_label_id": label_id,
            "labels": [{"id": l["id"], "label_name": l.get("label_name")} for l in owned],
            "totals": {"streams": 0, "revenue_idr": 0, "lines": 0},
            "latest_report": {"streams": 0, "revenue_idr": 0, "lines": 0},
            "latest_report_revenue_hidden": False,
            "legacy": legacy_empty,
            "monthly": [], "top_tracks": [], "top_platforms": [], "top_countries": [],
            "generated_at": now_iso(),
        }

    months = 1 if window == "latest" else int(window)
    period_from = _shift_month(latest_period, -(months - 1))
    period_filter = {"$gte": period_from, "$lte": latest_period}
    match = {**visibility, "period": period_filter}
    ranked = [{"$sort": {"streams": -1, "revenue_idr": -1}}, {"$limit": 8}]
    facet = [{"$match": match}, {"$facet": {
        "monthly": [{"$group": _summary_group("$period")}, {"$sort": {"_id": 1}}],
        "latest_report": [{"$match": {"period": latest_period}}, {"$group": _summary_group(None)}],
        "totals": [{"$group": _summary_group(None)}],
        "top_tracks": [
            {"$group": {
                "_id": {
                    "track_id": "$track_id",
                    "label_id": "$label_id",
                    "title": {"$ifNull": ["$track_title_raw", "Unknown"]},
                    "artist": {"$ifNull": ["$artist_name_raw", "Unknown"]},
                },
                "streams": {"$sum": "$quantity"},
                "revenue_idr": {"$sum": VISIBLE_REVENUE},
            }},
            *ranked,
        ],
        "top_platforms": [
            {"$group": {
                "_id": {"$ifNull": ["$platform", "Unknown"]},
                "streams": {"$sum": "$quantity"},
                "revenue_idr": {"$sum": VISIBLE_REVENUE},
            }},
            *ranked,
        ],
        "top_countries": [
            {"$group": {
                "_id": {"$ifNull": ["$country", "Unknown"]},
                "streams": {"$sum": "$quantity"},
                "revenue_idr": {"$sum": VISIBLE_REVENUE},
            }},
            *ranked,
        ],
    }}]

    async def run_facet() -> Dict[str, Any]:
        async for row in db_bg.royalty_lines.aggregate(facet, allowDiskUse=True):
            return row
        return {}

    result, available_periods = await asyncio.gather(
        run_facet(), db_bg.royalty_lines.distinct("period", visibility),
    )

    legacy_periods = []
    monthly_map = {}
    for row in result.get("monthly", []):
        monthly_map[row["_id"]] = {
            "period": row["_id"],
            **_summary(row),
            "legacy_streams": int(row.get("legacy_streams") or 0),
            "revenue_hidden": bool(row.get("legacy_lines")),
        }
        if row.get("legacy_lines"):
            legacy_periods.append(row["_id"])
    monthly = [
        monthly_map.get(period, {"period": period, "streams": 0, "revenue_idr": 0, "lines": 0,
                                 "legacy_streams": 0, "revenue_hidden": False})
        for period in _period_sequence(period_from, latest_period)
    ]
    total_row = (result.get("totals") or [{}])[0]
    latest_row = (result.get("latest_report") or [{}])[0]
    return {
        "window": window,
        "period_from": period_from,
        "period_to": latest_period,
        "latest_period": latest_period,
        "available_periods": sorted([period for period in available_periods if isinstance(period, str)], reverse=True),
        "scope": scope,
        "selected_label_id": label_id,
        "labels": [{"id": l["id"], "label_name": l.get("label_name")} for l in owned],
        "totals": _summary(total_row),
        "latest_report": _summary(latest_row),
        "latest_report_revenue_hidden": bool(latest_row.get("legacy_lines")),
        "legacy": {
            "streams": int(total_row.get("legacy_streams") or 0),
            "lines": int(total_row.get("legacy_lines") or 0),
            "periods": legacy_periods,
            "revenue_hidden": True,
        },
        "monthly": monthly,
        "top_tracks": [{
            "track_id": row["_id"].get("track_id"),
            "label_id": row["_id"].get("label_id"),
            "label_name": name_map.get(row["_id"].get("label_id")),
            "title": row["_id"].get("title") or "Unknown",
            "artist": row["_id"].get("artist") or "Unknown",
            "streams": int(row.get("streams") or 0),
            "revenue_idr": int(row.get("revenue_idr") or 0),
        } for row in result.get("top_tracks", [])],
        "top_platforms": [{
            "name": row.get("_id") or "Unknown",
            "streams": int(row.get("streams") or 0),
            "revenue_idr": int(row.get("revenue_idr") or 0),
        } for row in result.get("top_platforms", [])],
        "top_countries": [{
            "name": row.get("_id") or "Unknown",
            "streams": int(row.get("streams") or 0),
            "revenue_idr": int(row.get("revenue_idr") or 0),
        } for row in result.get("top_countries", [])],
        "generated_at": now_iso(),
    }
