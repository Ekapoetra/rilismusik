"""Customer-facing label analytics for published royalty reports."""
from datetime import datetime
from typing import Any, Dict, List, Literal

from fastapi import APIRouter, Depends, Query

from models import now_iso
from .deps import db_bg, get_label_by_user, get_labels_for_user, account_entitlements, require_label
from fastapi import HTTPException


label_analytics_r = APIRouter(prefix="/label/analytics", tags=["label-analytics"])
VISIBLE_STATUSES = ["pending", "available", "withdrawn"]


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
    visibility = {
        "label_id": {"$in": label_ids},
        "status": {"$in": VISIBLE_STATUSES},
        "legacy_settled": {"$ne": True},
        "period": {"$type": "string"},
    }
    latest_doc = await db_bg.royalty_lines.find_one(
        visibility, {"_id": 0, "period": 1}, sort=[("period", -1)],
    )
    latest_period = (latest_doc or {}).get("period")
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
            "monthly": [], "top_tracks": [], "top_platforms": [], "top_countries": [],
            "generated_at": now_iso(),
        }

    months = 1 if window == "latest" else int(window)
    period_from = _shift_month(latest_period, -(months - 1))
    period_filter = {"$gte": period_from, "$lte": latest_period}
    match = {**visibility, "period": period_filter}
    facet = [{"$match": match}, {"$facet": {
        "monthly": [
            {"$group": {
                "_id": "$period",
                "streams": {"$sum": "$quantity"},
                "revenue_idr": {"$sum": "$label_idr"},
                "lines": {"$sum": 1},
            }},
            {"$sort": {"_id": 1}},
        ],
        "latest_report": [
            {"$match": {"period": latest_period}},
            {"$group": {
                "_id": None,
                "streams": {"$sum": "$quantity"},
                "revenue_idr": {"$sum": "$label_idr"},
                "lines": {"$sum": 1},
            }},
        ],
        "totals": [
            {"$group": {
                "_id": None,
                "streams": {"$sum": "$quantity"},
                "revenue_idr": {"$sum": "$label_idr"},
                "lines": {"$sum": 1},
            }},
        ],
        "top_tracks": [
            {"$group": {
                "_id": {
                    "track_id": "$track_id",
                    "label_id": "$label_id",
                    "title": {"$ifNull": ["$track_title_raw", "Unknown"]},
                    "artist": {"$ifNull": ["$artist_name_raw", "Unknown"]},
                },
                "streams": {"$sum": "$quantity"},
                "revenue_idr": {"$sum": "$label_idr"},
            }},
            {"$sort": {"streams": -1, "revenue_idr": -1}},
            {"$limit": 8},
        ],
        "top_platforms": [
            {"$group": {
                "_id": {"$ifNull": ["$platform", "Unknown"]},
                "streams": {"$sum": "$quantity"},
                "revenue_idr": {"$sum": "$label_idr"},
            }},
            {"$sort": {"streams": -1, "revenue_idr": -1}},
            {"$limit": 8},
        ],
        "top_countries": [
            {"$group": {
                "_id": {"$ifNull": ["$country", "Unknown"]},
                "streams": {"$sum": "$quantity"},
                "revenue_idr": {"$sum": "$label_idr"},
            }},
            {"$sort": {"streams": -1, "revenue_idr": -1}},
            {"$limit": 8},
        ],
    }}]
    result: Dict[str, Any] = {}
    async for row in db_bg.royalty_lines.aggregate(facet, allowDiskUse=True):
        result = row
        break

    monthly_map = {
        row["_id"]: {
            "period": row["_id"],
            "streams": int(row.get("streams") or 0),
            "revenue_idr": int(row.get("revenue_idr") or 0),
            "lines": int(row.get("lines") or 0),
        } for row in result.get("monthly", [])
    }
    monthly = [monthly_map.get(period, {"period": period, "streams": 0, "revenue_idr": 0, "lines": 0}) for period in _period_sequence(period_from, latest_period)]
    total_row = (result.get("totals") or [{}])[0]
    latest_row = (result.get("latest_report") or [{}])[0]
    available_periods = await db_bg.royalty_lines.distinct("period", visibility)
    return {
        "window": window,
        "period_from": period_from,
        "period_to": latest_period,
        "latest_period": latest_period,
        "available_periods": sorted([period for period in available_periods if isinstance(period, str)], reverse=True),
        "scope": scope,
        "selected_label_id": label_id,
        "labels": [{"id": l["id"], "label_name": l.get("label_name")} for l in owned],
        "totals": {
            "streams": int(total_row.get("streams") or 0),
            "revenue_idr": int(total_row.get("revenue_idr") or 0),
            "lines": int(total_row.get("lines") or 0),
        },
        "latest_report": {
            "streams": int(latest_row.get("streams") or 0),
            "revenue_idr": int(latest_row.get("revenue_idr") or 0),
            "lines": int(latest_row.get("lines") or 0),
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