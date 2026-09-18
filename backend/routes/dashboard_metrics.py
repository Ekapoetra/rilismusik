"""Dashboard data foundations (fase-2): period KPIs with day/week/month trends,
step-based In Progress %, and a real Work Summary donut. Money & counts are computed
directly from timestamps so trends are real (no fabricated numbers)."""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional

from .deps import db, require_admin, has_permission
from models import now_iso

dashboard_metrics_r = APIRouter(prefix="/admin/dashboard", tags=["dashboard-metrics"])

WIB = timedelta(hours=7)


def _period_windows(period: str):
    """Return (cur_start, cur_end, prev_start, prev_end) as UTC ISO strings."""
    now = datetime.now(timezone.utc)
    wib_now = now + WIB
    if period == "week":
        wib_start = (wib_now - timedelta(days=wib_now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        wib_start = wib_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:  # today
        wib_start = wib_now.replace(hour=0, minute=0, second=0, microsecond=0)
    cur_start = wib_start - WIB  # back to UTC
    cur_len = now - cur_start
    prev_start = cur_start - cur_len
    return cur_start.isoformat(), now.isoformat(), prev_start.isoformat(), cur_start.isoformat()


def _trend(cur: float, prev: float):
    if prev <= 0:
        direction = "up" if cur > 0 else "flat"
        return {"direction": direction, "pct": None, "delta": cur - prev}
    pct = round((cur - prev) / prev * 100, 1)
    return {"direction": "up" if pct > 0 else ("down" if pct < 0 else "flat"), "pct": pct, "delta": cur - prev}


async def _sum(coll, match, field="amount"):
    cur = db[coll].aggregate([{"$match": match}, {"$group": {"_id": None, "s": {"$sum": f"${field}"}}}])
    async for r in cur:
        return float(r.get("s") or 0)
    return 0.0


async def _count(coll, match):
    return await db[coll].count_documents(match)


def _period_windows_dt(period: str):
    """Same windows as _period_windows but returns tz-aware datetimes (for date-typed comparisons)."""
    now = datetime.now(timezone.utc)
    wib_now = now + WIB
    if period == "week":
        wib_start = (wib_now - timedelta(days=wib_now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        wib_start = wib_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        wib_start = wib_now.replace(hour=0, minute=0, second=0, microsecond=0)
    cur_start = wib_start - WIB
    cur_len = now - cur_start
    prev_start = cur_start - cur_len
    return cur_start, now, prev_start, cur_start


async def _est(coll):
    """Fast collection total (metadata count) — never blocks the dashboard on large collections."""
    try:
        return await db[coll].estimated_document_count()
    except Exception:
        return 0


async def _count_fast(coll, match, ms=4000):
    try:
        return await db[coll].count_documents(match, maxTimeMS=ms)
    except Exception:
        return 0


async def _sum_by_date(coll, base_match, date_field, cs_dt, ce_dt, field="amount_idr"):
    """Sum `field` where the (string or date) `date_field` falls in [cs_dt, ce_dt]. Robust to mixed formats."""
    try:
        cur = db[coll].aggregate([
            {"$match": base_match},
            {"$set": {"_d": {"$convert": {"input": f"${date_field}", "to": "date", "onError": None, "onNull": None}}}},
            {"$match": {"_d": {"$gte": cs_dt, "$lte": ce_dt}}},
            {"$group": {"_id": None, "s": {"$sum": {"$ifNull": [f"${field}", 0]}}}},
        ], maxTimeMS=6000)
        async for r in cur:
            return float(r.get("s") or 0)
    except Exception:
        return 0.0
    return 0.0


async def _withdrawal_total(cs_dt, ce_dt):
    """Requested withdrawal = paid (by paid_date) + pending (requested/approved by request_date).
    Mirrors the canonical Arus Dana Withdrawal cashflow so numbers match the Withdraw page."""
    paid = await _sum_by_date("withdraw_requests", {"status": "paid"}, "paid_date", cs_dt, ce_dt)
    pending = await _sum_by_date("withdraw_requests", {"status": {"$in": ["requested", "approved"]}}, "request_date", cs_dt, ce_dt)
    return paid + pending


async def _latest_royalty_income():
    """Royalty income = total EUR of the most recently imported CSV, converted to IDR at its own rate."""
    proj = {"_id": 0, "total_revenue_eur": 1, "exchange_rate_eur_idr": 1, "period": 1, "filename": 1, "created_at": 1}
    imp = await db.royalty_imports.find_one({"total_revenue_eur": {"$gt": 0}}, proj, sort=[("created_at", -1)])
    if not imp:
        return {"value": 0, "currency": "IDR", "eur": 0, "rate": 0, "period": None, "filename": None, "trend": _trend(0, 0)}
    eur = float(imp.get("total_revenue_eur") or 0)
    rate = float(imp.get("exchange_rate_eur_idr") or 0)
    idr = round(eur * rate)
    prev = await db.royalty_imports.find_one(
        {"total_revenue_eur": {"$gt": 0}, "created_at": {"$lt": imp.get("created_at")}}, proj, sort=[("created_at", -1)])
    prev_idr = round(float(prev.get("total_revenue_eur") or 0) * float(prev.get("exchange_rate_eur_idr") or 0)) if prev else 0
    return {"value": idr, "currency": "IDR", "eur": round(eur, 2), "rate": rate,
            "period": imp.get("period"), "filename": imp.get("filename"), "trend": _trend(idr, prev_idr)}


@dashboard_metrics_r.get("/metrics")
async def dashboard_metrics(period: str = Query("today"), user: dict = Depends(require_admin)):
    cs, ce, ps, pe = _period_windows(period)
    cs_dt, ce_dt, ps_dt, pe_dt = _period_windows_dt(period)
    can_withdraw = has_permission(user, "withdraw.view") or user.get("role") == "super_admin"
    can_royalty = has_permission(user, "royalty.view") or has_permission(user, "analytics.view") or user.get("role") == "super_admin"
    out = {"period": period}

    # Sales Revenue — pure Xendit income (paid payments) by paid_at.
    sr_cur = await _sum("payments", {"provider": "xendit", "status": "paid", "paid_at": {"$gte": cs, "$lte": ce}})
    sr_prev = await _sum("payments", {"provider": "xendit", "status": "paid", "paid_at": {"$gte": ps, "$lt": pe}})
    out["sales_revenue"] = {"value": sr_cur, "currency": "IDR", "trend": _trend(sr_cur, sr_prev)}

    # Total labels / artists / releases — fast metadata totals + best-effort added-in-period trend.
    for key, coll in (("total_labels", "labels"), ("total_artists", "artists"), ("total_releases", "releases")):
        total = await _est(coll)
        added_cur = await _count_fast(coll, {"created_at": {"$gte": cs, "$lte": ce}})
        added_prev = await _count_fast(coll, {"created_at": {"$gte": ps, "$lt": pe}})
        out[key] = {"value": total, "added": added_cur, "trend": _trend(added_cur, added_prev)}

    # Active members — accounts that have been activated (claimed & active, not blacklisted).
    active_match = {"account_status": "active", "blacklisted": {"$ne": True}}
    active_total = await _count_fast("labels", active_match, ms=5000)
    am_cur = await _count_fast("labels", {**active_match, "created_at": {"$gte": cs, "$lte": ce}})
    am_prev = await _count_fast("labels", {**active_match, "created_at": {"$gte": ps, "$lt": pe}})
    out["active_members"] = {"value": active_total, "added": am_cur, "trend": _trend(am_cur, am_prev)}

    if can_withdraw:
        wd_cur = await _withdrawal_total(cs_dt, ce_dt)
        wd_prev = await _withdrawal_total(ps_dt, pe_dt)
        out["requested_withdrawal"] = {"value": wd_cur, "currency": "IDR", "trend": _trend(wd_cur, wd_prev)}
    if can_royalty:
        out["royalty_income"] = await _latest_royalty_income()

    out["finance_visible"] = can_withdraw or can_royalty
    return out


_MONEY_KINDS = ("sales", "withdrawal")


@dashboard_metrics_r.get("/money")
async def dashboard_money(kind: str = Query("sales"), period: str = Query("today"), user: dict = Depends(require_admin)):
    """Single money KPI scoped to its own period (used by cards with an independent dropdown)."""
    if kind not in _MONEY_KINDS:
        raise HTTPException(status_code=400, detail="kind tidak dikenal")
    cs, ce, ps, pe = _period_windows(period)
    if kind == "withdrawal":
        if not (has_permission(user, "withdraw.view") or user.get("role") == "super_admin"):
            raise HTTPException(status_code=403, detail="Akses ditolak")
        cs_dt, ce_dt, ps_dt, pe_dt = _period_windows_dt(period)
        cur = await _withdrawal_total(cs_dt, ce_dt)
        prev = await _withdrawal_total(ps_dt, pe_dt)
    else:  # sales — pure Xendit income (paid) by paid_at
        cur = await _sum("payments", {"provider": "xendit", "status": "paid", "paid_at": {"$gte": cs, "$lte": ce}})
        prev = await _sum("payments", {"provider": "xendit", "status": "paid", "paid_at": {"$gte": ps, "$lt": pe}})
    return {"kind": kind, "period": period, "value": cur, "currency": "IDR", "trend": _trend(cur, prev)}


# ---------------- In Progress (step-based %, 0-based: open/submitted = 0%) ----------------
_PIPELINES = {
    "releases": {"total_steps": 4, "map": {"submitted": 0, "under_review": 1, "awaiting_payment": 1, "paid": 2, "approved": 2, "delivered": 3},
                 "title": "release_title", "link": "/admin/releases/{id}", "cat": "Manajemen Rilisan"},
    "support_tickets": {"total_steps": 3, "map": {"open": 0, "in_progress": 1, "submitted_to_believe": 2},
                        "title": "subject", "link": "/admin/tickets/{id}", "cat": "Tiket Bantuan"},
    "withdraw_requests": {"total_steps": 2, "map": {"requested": 0, "processing": 1, "approved": 1}, "extra_match": {"child_withdraw_ids": {"$exists": False}},
                          "title": "label_name", "link": "/admin/withdraw", "cat": "Penarikan Dana"},
    "addon_orders": {"total_steps": 3, "map": {"pending": 0, "in_progress": 1, "delivered": 2},
                     "title": "product_name", "link": "/admin/addon-orders", "cat": "Layanan Tambahan"},
}
_STATUS_LABEL = {"submitted": "Diajukan", "under_review": "Ditinjau", "awaiting_payment": "Menunggu Bayar",
                 "paid": "Dibayar", "approved": "Disetujui", "delivered": "Dikirim", "open": "Terbuka",
                 "in_progress": "Diproses", "submitted_to_believe": "Submit ke Believe", "requested": "Diminta",
                 "processing": "Diproses", "pending": "Menunggu"}
_MODULE_PERM = {"releases": "releases.view", "support_tickets": "support.view", "withdraw_requests": "payments.view", "addon_orders": "addons.view"}


@dashboard_metrics_r.get("/in-progress")
async def in_progress(user: dict = Depends(require_admin)):
    is_super = user.get("role") == "super_admin"
    items = []
    for coll, cfg in _PIPELINES.items():
        perm = _MODULE_PERM.get(coll)
        if not is_super and perm and not has_permission(user, perm):
            continue
        active_statuses = list(cfg["map"].keys())
        match = {"status": {"$in": active_statuses}}
        if cfg.get("extra_match"):
            match.update(cfg["extra_match"])
        total_steps = cfg["total_steps"]
        async for d in db[coll].find(match, {"_id": 0}).sort("updated_at", -1).limit(10):
            step = cfg["map"].get(d.get("status"), 0)
            percent = round(step / total_steps * 100)
            items.append({
                "id": d.get("id"), "title": d.get(cfg["title"]) or cfg["cat"], "category": cfg["cat"],
                "percent": percent, "step": step, "total_steps": total_steps, "status": d.get("status"),
                "status_label": _STATUS_LABEL.get(d.get("status"), d.get("status")),
                "link": cfg["link"].format(id=d.get("id")), "updated_at": d.get("updated_at") or d.get("created_at"),
            })
    items.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
    return {"items": items[:8]}


# ---------------- Work Summary donut ----------------
@dashboard_metrics_r.get("/work-summary")
async def work_summary(period: str = Query("today"), user: dict = Depends(require_admin)):
    from .work_service import WORK_TYPES
    cs, ce, _, _ = _period_windows(period)
    completed = await _count("work_items", {"status": "completed", "completed_at": {"$gte": cs, "$lte": ce}})
    open_total = 0
    overdue = 0
    now = datetime.now(timezone.utc)
    sla_map = {w["key"]: int(w.get("sla_days_default") or 2) for w in WORK_TYPES}
    async for wi in db.work_items.find({"status": "open"}, {"_id": 0, "work_type": 1, "opened_at": 1}):
        open_total += 1
        try:
            opened = datetime.fromisoformat(str(wi.get("opened_at")).replace("Z", "+00:00"))
            if opened.tzinfo is None:
                opened = opened.replace(tzinfo=timezone.utc)
            if opened + timedelta(days=sla_map.get(wi.get("work_type"), 2)) < now:
                overdue += 1
        except Exception:
            pass
    ip = await in_progress(user)
    in_progress_count = len(ip["items"])
    total = completed + open_total + in_progress_count
    return {"period": period, "total": total, "completed": completed, "in_progress": in_progress_count,
            "open": open_total, "overdue": overdue}
