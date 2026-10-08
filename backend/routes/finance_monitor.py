"""V13 Financial Monitoring for Super Admin.

Keeps four money facts apart: label entitlement still owed (royalty lines not yet
withdrawn, the same source as the withdrawal balance), distributor receipts,
confirmed payouts and manually observed cash. The reports only read; recording a
cash observation is the single write and never touches balances.
"""
import calendar
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from models import new_id, now_iso
from withdraw_utils import MIN_WITHDRAW_IDR
from .deps import db, db_bg, require_super_admin
from .royalty_adjustment_balance import adjustment_balances

finance_monitor_r = APIRouter(prefix="/admin/finance-monitor", tags=["finance-monitor"])

CACHE_SECONDS = 300
AGE_KEYS = ("d0_90", "d91_180", "d181_365", "d365_plus", "unknown")
INACTIVE_DAYS = 90
_cache: Dict[str, Any] = {}


async def _cached(key: str, refresh: bool, build):
    hit = _cache.get(key)
    if hit and not refresh and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    value = await build()
    _cache[key] = (time.time(), value)
    return value


def _period_end(period: str) -> Optional[date]:
    try:
        year, month = int(period[:4]), int(period[5:7])
        return date(year, month, calendar.monthrange(year, month)[1])
    except (TypeError, ValueError, IndexError):
        return None


def _age_key(period: str, today: date) -> str:
    end = _period_end(period)
    if not end:
        return "unknown"
    days = (today - end).days
    if days <= 90:
        return "d0_90"
    if days <= 180:
        return "d91_180"
    if days <= 365:
        return "d181_365"
    return "d365_plus"


def _previous_period(period: str) -> Optional[str]:
    end = _period_end(period)
    if not end:
        return None
    first = end.replace(day=1) - timedelta(days=1)
    return f"{first.year:04d}-{first.month:02d}"


def _parse_time(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _condition(row: Dict[str, Any]) -> str:
    if row["anomalies"]:
        return "check_source"
    if row["processing_idr"] > 0:
        return "has_request"
    if row["available_idr"] > MIN_WITHDRAW_IDR:
        return "minimum_reached"
    if row["available_idr"] > 0:
        return "accumulating"
    return "settled"


async def _build_funds() -> Dict[str, Any]:
    today = datetime.now(timezone.utc).date()
    labels = await db_bg.labels.find({}, {
        "_id": 0, "id": 1, "label_name": 1, "user_id": 1, "last_withdrawn_period": 1,
        "bank_verified": 1, "account_status": 1,
    }).to_list(50000)
    by_id = {label["id"]: label for label in labels if label.get("id")}
    label_ids = list(by_id)

    # Same eligibility as balance_utils: unsettled lines after the withdrawn cutoff.
    lots: Dict[str, Dict[str, int]] = {label_id: {} for label_id in label_ids}
    pending: Dict[str, int] = {label_id: 0 for label_id in label_ids}
    async for row in db_bg.royalty_lines.aggregate([
        {"$match": {"status": {"$in": ["pending", "available"]}, "legacy_settled": {"$ne": True}, "period": {"$type": "string"}}},
        {"$group": {"_id": {"label_id": "$label_id", "period": "$period", "status": "$status"}, "amount_idr": {"$sum": {"$ifNull": ["$label_idr", 0]}}}},
    ], allowDiskUse=True):
        key = row.get("_id") or {}
        label_id, period = str(key.get("label_id") or ""), key.get("period")
        if label_id not in by_id:
            continue
        cutoff = by_id[label_id].get("last_withdrawn_period")
        if cutoff and period <= cutoff:
            continue
        amount = int(row.get("amount_idr") or 0)
        if key.get("status") == "pending":
            pending[label_id] += amount
        else:
            lots[label_id][period] = lots[label_id].get(period, 0) + amount

    processing: Dict[str, int] = {}
    async for row in db_bg.withdraw_requests.aggregate([
        {"$match": {"status": {"$in": ["requested", "approved"]}, "legacy_import": {"$ne": True}}},
        {"$group": {"_id": "$label_id", "amount_idr": {"$sum": {"$ifNull": ["$amount_idr", 0]}}}},
    ], allowDiskUse=True):
        processing[str(row.get("_id") or "")] = int(row.get("amount_idr") or 0)

    paid: Dict[str, Dict[str, Any]] = {}
    async for row in db_bg.withdraw_requests.aggregate([
        {"$match": {"status": "paid"}},
        {"$group": {"_id": "$label_id", "amount_idr": {"$sum": {"$ifNull": ["$amount_idr", 0]}},
                    "last_paid_at": {"$max": {"$ifNull": ["$paid_at", "$updated_at"]}}}},
    ], allowDiskUse=True):
        paid[str(row.get("_id") or "")] = {"amount_idr": int(row.get("amount_idr") or 0), "last_paid_at": row.get("last_paid_at")}

    income: Dict[str, Dict[str, Any]] = {}
    async for row in db_bg.monthly_analytics.aggregate([
        {"$match": {"dim": "label"}},
        {"$sort": {"period": -1}},
        {"$group": {"_id": "$key", "period": {"$first": "$period"}, "revenue_idr": {"$first": "$revenue_idr"}}},
    ], allowDiskUse=True):
        income[str(row.get("_id") or "")] = {"period": row.get("period"), "amount_idr": int(row.get("revenue_idr") or 0)}

    activity: Dict[str, Any] = {}
    async for row in db_bg.releases.aggregate([
        {"$group": {"_id": "$label_id", "last": {"$max": {"$ifNull": ["$updated_at", "$created_at"]}}}},
    ], allowDiskUse=True):
        activity[str(row.get("_id") or "")] = row.get("last")

    adjustments = await adjustment_balances(label_ids) if label_ids else {}

    accounts: Dict[str, Dict[str, Any]] = {}
    for label_id, label in by_id.items():
        reserved = processing.get(label_id, 0)
        adjustment = int(adjustments.get(label_id, 0))
        raw_available = sum(lots[label_id].values()) + adjustment - reserved
        available = max(raw_available, 0)
        # Age the remaining entitlement by report period, oldest lots consumed first
        # by open requests (withdrawals settle the oldest periods first).
        age = {key: 0 for key in AGE_KEYS}
        remaining_reserve = reserved
        for period in sorted(lots[label_id]):
            amount = lots[label_id][period]
            used = min(amount, remaining_reserve)
            remaining_reserve -= used
            if amount - used > 0:
                age[_age_key(period, today)] += amount - used
        age["unknown"] += adjustment - remaining_reserve
        anomalies = []
        if raw_available < 0:
            anomalies.append("negative_balance")
        if age["unknown"] < 0:
            anomalies.append("negative_adjustment")
        if not (available or reserved or pending[label_id] or paid.get(label_id) or adjustment):
            continue
        account_key = label.get("user_id") or f"label:{label_id}"
        account = accounts.setdefault(account_key, {
            "id": account_key, "labels": [], "available_idr": 0, "processing_idr": 0, "pending_idr": 0,
            "paid_idr": 0, "age": {key: 0 for key in AGE_KEYS}, "last_income": None, "last_paid_at": None,
            "last_activity_at": None, "bank_verified": True, "anomalies": [],
        })
        account["labels"].append({"id": label_id, "label_name": label.get("label_name"), "available_idr": available,
                                  "processing_idr": reserved, "pending_idr": pending[label_id]})
        account["available_idr"] += available
        account["processing_idr"] += reserved
        account["pending_idr"] += pending[label_id]
        account["paid_idr"] += (paid.get(label_id) or {}).get("amount_idr", 0)
        for key in AGE_KEYS:
            account["age"][key] += age[key]
        account["bank_verified"] = account["bank_verified"] and bool(label.get("bank_verified"))
        account["anomalies"].extend(anomalies)
        last_income = income.get(label_id)
        if last_income and (not account["last_income"] or last_income["period"] > account["last_income"]["period"]):
            account["last_income"] = dict(last_income)
        elif last_income and last_income["period"] == account["last_income"]["period"]:
            account["last_income"]["amount_idr"] += last_income["amount_idr"]
        for field, value in (("last_paid_at", (paid.get(label_id) or {}).get("last_paid_at")), ("last_activity_at", activity.get(label_id))):
            if value and (not account[field] or str(value) > str(account[field])):
                account[field] = value

    now = datetime.now(timezone.utc)
    rows = []
    for account in accounts.values():
        account["labels"].sort(key=lambda item: -item["available_idr"])
        account["name"] = account["labels"][0]["label_name"] if len(account["labels"]) == 1 else f"{account['labels'][0]['label_name']} +{len(account['labels']) - 1}"
        account["label_count"] = len(account["labels"])
        account["unpaid_idr"] = account["available_idr"] + account["processing_idr"]
        last_activity = _parse_time(account["last_activity_at"])
        account["inactive"] = bool(account["last_income"]) and (not last_activity or (now - last_activity).days > INACTIVE_DAYS)
        account["never_paid"] = account["paid_idr"] == 0
        account["condition"] = _condition(account)
        rows.append(account)
    rows.sort(key=lambda item: -item["available_idr"])
    totals = {
        "unpaid_idr": sum(row["unpaid_idr"] for row in rows),
        "available_idr": sum(row["available_idr"] for row in rows),
        "processing_idr": sum(row["processing_idr"] for row in rows),
        "pending_idr": sum(row["pending_idr"] for row in rows),
        "age_365_plus_idr": sum(row["age"]["d365_plus"] for row in rows),
        "age_unknown_idr": sum(row["age"]["unknown"] for row in rows),
        "accounts": len(rows),
    }
    return {"generated_at": now_iso(), "min_withdraw_idr": MIN_WITHDRAW_IDR, "age_basis": "report_period", "totals": totals, "rows": rows}


@finance_monitor_r.get("/funds")
async def funds(refresh: bool = Query(False), user: dict = Depends(require_super_admin)):
    return await _cached("funds", refresh, _build_funds)


async def _build_catalogue() -> Dict[str, Any]:
    totals = await db_bg.monthly_analytics.find({"dim": "total"}, {"_id": 0, "period": 1, "revenue_idr": 1}).sort("period", -1).to_list(24)
    periods = [row["period"] for row in totals if row.get("period")]
    current = periods[0] if periods else None
    previous = _previous_period(current) if current else None
    comparable = bool(current and previous in periods)
    revenue: Dict[str, Dict[str, int]] = {}
    if current:
        async for row in db_bg.monthly_analytics.find({"dim": "label", "period": {"$in": [p for p in (current, previous) if p]}}, {"_id": 0, "key": 1, "period": 1, "revenue_idr": 1}):
            revenue.setdefault(str(row.get("key")), {})[row["period"]] = int(row.get("revenue_idr") or 0)
    since = (datetime.now(timezone.utc) - timedelta(days=INACTIVE_DAYS)).isoformat()
    submissions: Dict[str, int] = {}
    async for row in db_bg.releases.aggregate([
        {"$match": {"created_at": {"$gte": since}, "status": {"$ne": "draft"}}},
        {"$group": {"_id": "$label_id", "count": {"$sum": 1}}},
    ]):
        submissions[str(row.get("_id") or "")] = int(row.get("count") or 0)
    names = {label["id"]: label.get("label_name") async for label in db_bg.labels.find({"id": {"$in": list(revenue)}}, {"_id": 0, "id": 1, "label_name": 1})}
    rows = []
    for label_id, values in revenue.items():
        now_value, before = values.get(current, 0), values.get(previous) if previous else None
        change = None
        if comparable and before:
            change = round((now_value - before) / before * 100, 1)
        rows.append({"label_id": label_id, "label_name": names.get(label_id) or label_id, "revenue_idr": now_value,
                     "previous_idr": before, "change_pct": change, "releases_90d": submissions.get(label_id, 0)})
    rows.sort(key=lambda item: -item["revenue_idr"])
    return {"generated_at": now_iso(), "period": current, "previous_period": previous, "comparable": comparable, "rows": rows}


@finance_monitor_r.get("/catalogue")
async def catalogue(refresh: bool = Query(False), user: dict = Depends(require_super_admin)):
    return await _cached("catalogue", refresh, _build_catalogue)


async def _build_cash() -> Dict[str, Any]:
    imports = await db_bg.royalty_imports.find(
        {"status": {"$in": ["published", "receiving", "receive_error", "dana_received"]}},
        {"_id": 0, "id": 1, "filename": 1, "period": 1, "reporting_period": 1, "status": 1, "total_revenue_eur": 1,
         "exchange_rate_eur_idr": 1, "total_label_idr": 1, "dana_received_at": 1, "published_at": 1, "created_at": 1},
    ).sort("created_at", -1).to_list(500)
    receipts, received_idr, received_label_idr, pending_label_idr = [], 0, 0, 0
    for item in imports:
        gross = int(round(float(item.get("total_revenue_eur") or 0) * float(item.get("exchange_rate_eur_idr") or 0)))
        label_idr = int(item.get("total_label_idr") or 0)
        received = item.get("status") == "dana_received"
        if received:
            received_idr += gross
            received_label_idr += label_idr
        else:
            pending_label_idr += label_idr
        receipts.append({"id": item.get("id"), "filename": item.get("filename"), "period": item.get("reporting_period") or item.get("period"),
                         "status": item.get("status"), "gross_idr": gross, "label_idr": label_idr,
                         "received_at": item.get("dana_received_at"), "published_at": item.get("published_at")})
    paid_idr = 0
    async for row in db_bg.withdraw_requests.aggregate([
        {"$match": {"status": "paid"}}, {"$group": {"_id": None, "amount_idr": {"$sum": {"$ifNull": ["$amount_idr", 0]}}}},
    ]):
        paid_idr = int(row.get("amount_idr") or 0)
    observations = await db_bg.finance_cash_observations.find({}, {"_id": 0}).sort("observed_at", -1).to_list(10)
    return {
        "generated_at": now_iso(),
        "totals": {"received_idr": received_idr, "received_label_idr": received_label_idr,
                   "pending_label_idr": pending_label_idr, "paid_idr": paid_idr,
                   "latest_cash_idr": observations[0]["amount_idr"] if observations else None},
        # The ledger has no bank statement, so a cash gap cannot be concluded yet.
        "conclusion": "not_determinable",
        "receipts": receipts, "observations": observations,
    }


@finance_monitor_r.get("/cash")
async def cash(refresh: bool = Query(False), user: dict = Depends(require_super_admin)):
    return await _cached("cash", refresh, _build_cash)


class CashObservationIn(BaseModel):
    amount_idr: int = Field(ge=0)
    observed_at: datetime
    scope: str = Field(min_length=1, max_length=150)
    note: str = Field(default="", max_length=1000)


@finance_monitor_r.post("/cash-observations")
async def record_cash_observation(body: CashObservationIn, user: dict = Depends(require_super_admin)):
    observed = body.observed_at if body.observed_at.tzinfo else body.observed_at.replace(tzinfo=timezone.utc)
    if observed > datetime.now(timezone.utc) + timedelta(minutes=1):
        raise HTTPException(status_code=400, detail="Waktu posisi kas tidak boleh di masa depan")
    document = {"id": new_id(), "amount_idr": body.amount_idr, "observed_at": observed.isoformat(), "scope": body.scope.strip(),
                "note": body.note.strip(), "recorded_by": user["id"], "recorded_by_name": user.get("name"), "created_at": now_iso()}
    await db.finance_cash_observations.insert_one(dict(document))
    _cache.pop("cash", None)
    return document
