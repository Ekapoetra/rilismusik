"""Monthly finance reporting for admin payment and withdrawal operations."""
import asyncio
from typing import Any, Dict, Optional

from .deps import db


JAKARTA_TIMEZONE = "Asia/Jakarta"


async def _monthly_rollup(
    *, collection, match: Dict[str, Any], date_field: str, year: int,
    amount_field: str = "amount_idr",
) -> Dict[str, Any]:
    result = await collection.aggregate([
        {"$match": match},
        {"$set": {"_report_date": {"$convert": {
            "input": f"${date_field}", "to": "date", "onError": None, "onNull": None,
        }}}},
        {"$match": {"_report_date": {"$ne": None}}},
        {"$set": {
            "_report_year": {"$toInt": {"$dateToString": {
                "format": "%Y", "date": "$_report_date", "timezone": JAKARTA_TIMEZONE,
            }}},
            "_report_month": {"$toInt": {"$dateToString": {
                "format": "%m", "date": "$_report_date", "timezone": JAKARTA_TIMEZONE,
            }}},
        }},
        {"$facet": {
            "months": [
                {"$match": {"_report_year": year}},
                {"$group": {
                    "_id": "$_report_month", "amount_idr": {"$sum": {"$ifNull": [f"${amount_field}", 0]}},
                    "count": {"$sum": 1},
                }},
                {"$sort": {"_id": 1}},
            ],
            "years": [
                {"$group": {"_id": "$_report_year"}}, {"$sort": {"_id": -1}},
            ],
        }},
    ]).to_list(1)
    payload = result[0] if result else {"months": [], "years": []}
    by_month = {
        int(row["_id"]): {"amount_idr": int(row.get("amount_idr") or 0), "count": int(row.get("count") or 0)}
        for row in payload.get("months", [])
    }
    monthly = [
        {"month": month, **by_month.get(month, {"amount_idr": 0, "count": 0})}
        for month in range(1, 13)
    ]
    years = [int(row["_id"]) for row in payload.get("years", []) if row.get("_id")]
    if year not in years:
        years.append(year)
    return {"monthly": monthly, "available_years": sorted(set(years), reverse=True)}


async def payment_income_summary(*, year: int, month: int) -> Dict[str, Any]:
    rollup = await _monthly_rollup(
        collection=db.payments, match={"status": "paid"}, date_field="paid_at",
        amount_field="amount", year=year,
    )
    selected = rollup["monthly"][month - 1]
    return {
        "year": year, "month": month,
        "selected": {"amount_idr": selected["amount_idr"], "count": selected["count"]},
        "year_total": {
            "amount_idr": sum(row["amount_idr"] for row in rollup["monthly"]),
            "count": sum(row["count"] for row in rollup["monthly"]),
        },
        **rollup,
    }


async def withdrawal_cashflow_summary(*, year: int, month: int) -> Dict[str, Any]:
    pending, outgoing = await asyncio.gather(
        _monthly_rollup(
            collection=db.withdraw_requests,
            match={"status": {"$in": ["requested", "approved"]}},
            date_field="request_date", year=year,
        ),
        _monthly_rollup(
            collection=db.withdraw_requests, match={"status": "paid"},
            date_field="paid_date", year=year,
        ),
    )
    monthly = [
        {
            "month": index + 1,
            "pending_idr": pending["monthly"][index]["amount_idr"],
            "pending_count": pending["monthly"][index]["count"],
            "outgoing_idr": outgoing["monthly"][index]["amount_idr"],
            "outgoing_count": outgoing["monthly"][index]["count"],
        }
        for index in range(12)
    ]
    selected = monthly[month - 1]
    return {
        "year": year, "month": month,
        "pending": {"amount_idr": selected["pending_idr"], "count": selected["pending_count"]},
        "outgoing": {"amount_idr": selected["outgoing_idr"], "count": selected["outgoing_count"]},
        "year_total": {
            "pending_idr": sum(row["pending_idr"] for row in monthly),
            "pending_count": sum(row["pending_count"] for row in monthly),
            "outgoing_idr": sum(row["outgoing_idr"] for row in monthly),
            "outgoing_count": sum(row["outgoing_count"] for row in monthly),
        },
        "monthly": monthly,
        "available_years": sorted(set(pending["available_years"] + outgoing["available_years"] + [year]), reverse=True),
    }


def withdrawal_period_filter(*, status: Optional[str], year: int, month: int) -> Dict[str, Any]:
    period = f"^{year:04d}-{month:02d}"
    if status == "paid":
        return {"status": "paid", "paid_date": {"$regex": period}}
    if status:
        return {"status": status, "request_date": {"$regex": period}}
    return {"$or": [
        {"status": "paid", "paid_date": {"$regex": period}},
        {"status": {"$ne": "paid"}, "request_date": {"$regex": period}},
    ]}