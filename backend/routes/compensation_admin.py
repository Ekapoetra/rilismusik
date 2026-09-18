"""Compensation admin — Bonus Engine (B), Payroll + Allowance + Adjustment (C).

- Bonus = percentage of TOTAL paid Xendit revenue (submit / subscription / WAMI / add-on)
  for the payroll month; royalty is never a revenue source. Each eligible staff earns the
  FULL scheme percent (never split). Scope = all / role / individual staff; lifetime or dated.
- Payroll Item is a SNAPSHOT (salary+allowance+bonus+adjustment) frozen on finalize.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from models import now_iso, new_id
from .deps import db, logger, require_admin, log_activity
from .admin_permission_service import assert_admin_permission
from .compensation_service import resolve_salary, is_staff_user

comp_admin_r = APIRouter(prefix="/compensation", tags=["compensation-admin"])

# ---------- models ----------
class SalaryIn(BaseModel):
    staff_user_id: str
    new_idr: int
    effective_date: str  # YYYY-MM-DD
    reason: Optional[str] = ""

class AllowanceIn(BaseModel):
    staff_user_id: str
    name: str
    amount_idr: int
    effective_from: str
    effective_to: Optional[str] = None

class BonusSchemeIn(BaseModel):
    name: str
    scope: str = "all"                    # all | role | staff
    role_key: Optional[str] = None        # required when scope == role
    staff_user_id: Optional[str] = None   # required when scope == staff
    calc_mode: str = "flat"               # flat | tiered
    percent: float = 0                    # flat: 0-100, % of total Xendit revenue
    tiers: Optional[List[Dict[str, Any]]] = None  # tiered: [{up_to: int|null, percent: float}] (marginal)
    effective_from: Optional[str] = None  # None = lifetime (always applies)
    effective_to: Optional[str] = None

class AdjustmentIn(BaseModel):
    staff_user_id: str
    period_key: str                  # YYYY-MM
    amount_idr: int                  # +/-
    reason: str

class PeriodIn(BaseModel):
    period_key: str                  # YYYY-MM

class TransitionIn(BaseModel):
    to: str                          # review|approved|paid|finalized


def _period_bounds(period_key: str):
    y, m = int(period_key[:4]), int(period_key[5:7])
    start = f"{y:04d}-{m:02d}-01"
    end = f"{y:04d}-{m:02d}-{'31' if m in (1,3,5,7,8,10,12) else ('29' if (m==2 and y%4==0 and (y%100!=0 or y%400==0)) else '28' if m==2 else '30')}"
    return start, end


# ---------- salary ----------
@comp_admin_r.post("/salary")
async def set_salary(body: SalaryIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "compensation.salary.manage")
    if not await is_staff_user(body.staff_user_id):
        raise HTTPException(404, "Staf tidak eligible")
    prof = await db.staff_profiles.find_one({"user_id": body.staff_user_id}, {"_id": 0, "salary_current_idr": 1}) or {}
    prev = int(prof.get("salary_current_idr") or 0)
    await db.staff_salary_history.insert_one({
        "id": new_id(), "user_id": body.staff_user_id, "previous_idr": prev, "new_idr": int(body.new_idr),
        "effective_date": body.effective_date, "reason": body.reason, "changed_by": user["id"], "changed_at": now_iso(),
    })
    # keep salary_current_idr in sync when the change is effective today or earlier
    if str(body.effective_date)[:10] <= now_iso()[:10]:
        await db.staff_profiles.update_one({"user_id": body.staff_user_id},
            {"$set": {"salary_current_idr": int(body.new_idr), "updated_at": now_iso()}}, upsert=True)
    await log_activity(user["id"], "salary_change", "compensation", body.staff_user_id,
                       before={"salary_idr": prev}, after={"salary_idr": int(body.new_idr), "effective_date": body.effective_date})
    return {"ok": True}


# ---------- allowances ----------
@comp_admin_r.get("/allowances")
async def list_allowances(staff_user_id: str = Query(default=None), user: dict = Depends(require_admin)):
    assert_admin_permission(user, "compensation.view_team")
    q = {"active": True}
    if staff_user_id:
        q["staff_user_id"] = staff_user_id
    rows = await db.compensation_allowances.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return {"allowances": rows}


@comp_admin_r.post("/allowances")
async def create_allowance(body: AllowanceIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "compensation.allowance.manage")
    if not await is_staff_user(body.staff_user_id):
        raise HTTPException(404, "Staf tidak eligible")
    doc = {"id": new_id(), "staff_user_id": body.staff_user_id, "name": body.name.strip(),
           "amount_idr": int(body.amount_idr), "effective_from": body.effective_from, "effective_to": body.effective_to,
           "active": True, "created_by": user["id"], "created_at": now_iso(), "updated_at": now_iso()}
    await db.compensation_allowances.insert_one(doc)
    await log_activity(user["id"], "allowance_create", "compensation", doc["id"], after={"name": doc["name"], "amount_idr": doc["amount_idr"]})
    doc.pop("_id", None)
    return doc


@comp_admin_r.delete("/allowances/{allowance_id}")
async def deactivate_allowance(allowance_id: str, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "compensation.allowance.manage")
    r = await db.compensation_allowances.update_one({"id": allowance_id}, {"$set": {"active": False, "updated_at": now_iso()}})
    if not r.matched_count:
        raise HTTPException(404, "Tunjangan tidak ditemukan")
    return {"ok": True}


async def _allowances_for_period(staff_user_id: str, start: str, end: str) -> Dict[str, Any]:
    rows = await db.compensation_allowances.find({"staff_user_id": staff_user_id, "active": True}, {"_id": 0}).to_list(1000)
    applicable = [a for a in rows if str(a.get("effective_from") or "")[:10] <= end and (not a.get("effective_to") or str(a["effective_to"])[:10] >= start)]
    total = sum(int(a.get("amount_idr") or 0) for a in applicable)
    return {"total": total, "breakdown": [{"name": a["name"], "amount_idr": int(a["amount_idr"])} for a in applicable]}


# ---------- bonus schemes (percentage of total Xendit revenue) ----------
@comp_admin_r.get("/bonus/schemes")
async def list_bonus_schemes(user: dict = Depends(require_admin)):
    assert_admin_permission(user, "compensation.bonus.view")
    rows = await db.bonus_schemes.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"schemes": rows}


def _normalize_tiers(tiers_in: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    norm = []
    for t in (tiers_in or []):
        up = t.get("up_to")
        up = None if up in (None, "", 0, "0") else int(up)
        pct = float(t.get("percent") or 0)
        if not (0 < pct <= 100):
            raise HTTPException(400, "Persentase tier harus di antara 0 dan 100")
        norm.append({"up_to": up, "percent": pct})
    if not norm:
        raise HTTPException(400, "Skema bertingkat butuh minimal satu tier")
    norm.sort(key=lambda x: (x["up_to"] is None, x["up_to"] or 0))
    finite = [x["up_to"] for x in norm if x["up_to"] is not None]
    if len(set(finite)) != len(finite):
        raise HTTPException(400, "Ambang tier harus unik dan menaik")
    if sum(1 for x in norm if x["up_to"] is None) > 1:
        raise HTTPException(400, "Hanya boleh satu tier tanpa batas (paling atas)")
    return norm


@comp_admin_r.post("/bonus/schemes")
async def create_bonus_scheme(body: BonusSchemeIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "compensation.bonus.rules.manage")
    if body.scope not in ("all", "role", "staff"):
        raise HTTPException(400, "Cakupan tidak valid")
    if body.calc_mode not in ("flat", "tiered"):
        raise HTTPException(400, "Mode kalkulasi tidak valid")
    if body.scope == "role" and not body.role_key:
        raise HTTPException(400, "Pilih role untuk cakupan role")
    if body.scope == "staff" and (not body.staff_user_id or not await is_staff_user(body.staff_user_id)):
        raise HTTPException(404, "Staf tidak eligible")
    tiers = None
    if body.calc_mode == "tiered":
        tiers = _normalize_tiers(body.tiers)
    elif not (0 < float(body.percent) <= 100):
        raise HTTPException(400, "Persentase harus di antara 0 dan 100")
    doc = {"id": new_id(), "name": body.name.strip(), "scope": body.scope,
           "role_key": body.role_key if body.scope == "role" else None,
           "staff_user_id": body.staff_user_id if body.scope == "staff" else None,
           "calc_mode": body.calc_mode, "percent": float(body.percent) if body.calc_mode == "flat" else 0,
           "tiers": tiers, "effective_from": body.effective_from, "effective_to": body.effective_to,
           "active": True, "created_by": user["id"], "created_at": now_iso(), "updated_at": now_iso()}
    await db.bonus_schemes.insert_one(doc)
    await log_activity(user["id"], "bonus_scheme_create", "compensation", doc["id"],
                       after={"name": doc["name"], "calc_mode": doc["calc_mode"], "percent": doc["percent"], "scope": doc["scope"]})
    doc.pop("_id", None)
    return doc


@comp_admin_r.patch("/bonus/schemes/{scheme_id}")
async def update_bonus_scheme(scheme_id: str, body: Dict[str, Any], user: dict = Depends(require_admin)):
    assert_admin_permission(user, "compensation.bonus.rules.manage")
    allowed = {k: v for k, v in body.items() if k in {"active", "percent", "effective_from", "effective_to", "name", "calc_mode", "tiers"}}
    if allowed.get("calc_mode") == "tiered" or ("tiers" in allowed):
        allowed["tiers"] = _normalize_tiers(allowed.get("tiers"))
        allowed["calc_mode"] = "tiered"
        allowed["percent"] = 0
    elif "percent" in allowed and not (0 < float(allowed["percent"]) <= 100):
        raise HTTPException(400, "Persentase harus di antara 0 dan 100")
    r = await db.bonus_schemes.update_one({"id": scheme_id}, {"$set": {**allowed, "updated_at": now_iso()}})
    if not r.matched_count:
        raise HTTPException(404, "Skema tidak ditemukan")
    await log_activity(user["id"], "bonus_scheme_update", "compensation", scheme_id, after=allowed)
    return {"ok": True}


@comp_admin_r.delete("/bonus/schemes/{scheme_id}")
async def deactivate_bonus_scheme(scheme_id: str, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "compensation.bonus.rules.manage")
    r = await db.bonus_schemes.update_one({"id": scheme_id}, {"$set": {"active": False, "updated_at": now_iso()}})
    if not r.matched_count:
        raise HTTPException(404, "Skema tidak ditemukan")
    return {"ok": True}


async def _revenue_for_period(start: str, end: str) -> int:
    """Total paid Xendit revenue (submit / subscription / WAMI / add-on) whose paid_at
    falls within [start, end]. Royalty is never a `payments` row, so it is excluded."""
    rows = await db.payments.find(
        {"status": "paid", "paid_at": {"$gte": start, "$lte": end + "T23:59:59"}}, {"_id": 0, "amount": 1},
    ).to_list(100000)
    return int(sum(int(r.get("amount") or 0) for r in rows))


def _scheme_active_in(scheme: dict, start: str, end: str) -> bool:
    ef = str(scheme.get("effective_from") or "")[:10]
    et = str(scheme.get("effective_to") or "")[:10]
    if ef and ef > end:
        return False
    if et and et < start:
        return False
    return True


def _scheme_amount(scheme: dict, revenue: int):
    """Return (amount_idr, tiers_used|None). Tiered = marginal across revenue bands."""
    if scheme.get("calc_mode") == "tiered":
        tiers = sorted(scheme.get("tiers") or [], key=lambda t: (t.get("up_to") is None, t.get("up_to") or 0))
        total, used, prev = 0, [], 0
        for t in tiers:
            cap = t.get("up_to")
            upper = revenue if cap is None else min(revenue, int(cap))
            if upper <= prev:
                break
            portion = upper - prev
            pct = float(t.get("percent") or 0)
            amt = round(portion * pct / 100.0)
            total += amt
            used.append({"percent": pct, "from_idr": int(prev), "to_idr": (None if cap is None else int(cap)),
                         "base_idr": int(portion), "amount_idr": int(amt)})
            prev = upper
            if cap is None or revenue <= int(cap):
                break
        return int(total), used
    pct = float(scheme.get("percent") or 0)
    return int(round(revenue * pct / 100.0)), None


def _bonus_for_staff(uid: str, role: str, revenue: int, start: str, end: str, schemes: List[dict]):
    """Sum of every matching active scheme. Each staff earns the FULL amount independently
    (never split). Each entry carries the scheme and (for tiered) per-tier detail."""
    total, breakdown = 0, []
    for s in schemes:
        if not s.get("active", True) or not _scheme_active_in(s, start, end):
            continue
        matches = (s["scope"] == "all"
                   or (s["scope"] == "role" and s.get("role_key") == role)
                   or (s["scope"] == "staff" and s.get("staff_user_id") == uid))
        if not matches:
            continue
        amt, tiers_used = _scheme_amount(s, revenue)
        if amt <= 0:
            continue
        total += amt
        entry = {"scheme_name": s.get("name"), "calc_mode": s.get("calc_mode", "flat"), "amount_idr": int(amt)}
        if s.get("calc_mode") == "tiered":
            entry["tiers"] = tiers_used
        else:
            entry["percent"] = float(s.get("percent") or 0)
        breakdown.append(entry)
    return int(total), breakdown


@comp_admin_r.get("/bonus/preview")
async def bonus_preview(period_key: str = Query(...), user: dict = Depends(require_admin)):
    assert_admin_permission(user, "compensation.bonus.transactions.view")
    start, end = _period_bounds(period_key)
    revenue = await _revenue_for_period(start, end)
    schemes = await db.bonus_schemes.find({"active": True}, {"_id": 0}).to_list(500)
    staff_resp = await list_staff_comp(user)
    items = []
    for s in staff_resp["staff"]:
        total, breakdown = _bonus_for_staff(s["user_id"], s["role"], revenue, start, end, schemes)
        if total:
            items.append({"staff_user_id": s["user_id"], "name": s["name"], "role": s["role"],
                          "bonus_idr": total, "breakdown": breakdown})
    return {"period_key": period_key, "revenue_idr": revenue, "items": items,
            "total_bonus_idr": int(sum(i["bonus_idr"] for i in items))}


# ---------- adjustments ----------
@comp_admin_r.get("/adjustments")
async def list_adjustments(period_key: str = Query(default=None), user: dict = Depends(require_admin)):
    assert_admin_permission(user, "compensation.view_team")
    q = {}
    if period_key:
        q["period_key"] = period_key
    rows = await db.compensation_adjustments.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return {"adjustments": rows}


@comp_admin_r.post("/adjustments")
async def create_adjustment(body: AdjustmentIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "compensation.adjustment.create")
    if not await is_staff_user(body.staff_user_id):
        raise HTTPException(404, "Staf tidak eligible")
    doc = {"id": new_id(), "staff_user_id": body.staff_user_id, "period_key": body.period_key,
           "amount_idr": int(body.amount_idr), "reason": body.reason.strip(), "status": "pending",
           "created_by": user["id"], "approved_by": None, "created_at": now_iso(), "updated_at": now_iso()}
    await db.compensation_adjustments.insert_one(doc)
    doc.pop("_id", None)
    return doc


@comp_admin_r.post("/adjustments/{adj_id}/approve")
async def approve_adjustment(adj_id: str, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "compensation.adjustment.approve")
    r = await db.compensation_adjustments.update_one({"id": adj_id, "status": "pending"},
        {"$set": {"status": "approved", "approved_by": user["id"], "updated_at": now_iso()}})
    if not r.matched_count:
        raise HTTPException(404, "Penyesuaian tidak ditemukan / sudah diproses")
    return {"ok": True}


async def _adjustments_for_period(staff_user_id: str, period_key: str):
    rows = await db.compensation_adjustments.find({"staff_user_id": staff_user_id, "period_key": period_key, "status": "approved"}, {"_id": 0}).to_list(500)
    total = sum(int(a.get("amount_idr") or 0) for a in rows)
    return {"total": total, "breakdown": [{"reason": a["reason"], "amount_idr": int(a["amount_idr"])} for a in rows]}


# ---------- staff list ----------
@comp_admin_r.get("/staff")
async def list_staff_comp(user: dict = Depends(require_admin)):
    assert_admin_permission(user, "compensation.view_team")
    from .deps import ADMIN_ROLES
    users = await db.users.find({"role": {"$in": list(ADMIN_ROLES)}, "status": {"$nin": ["suspended", "disabled", "merged"]}},
                                {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1}).to_list(1000)
    out = []
    for u in users:
        prof = await db.staff_profiles.find_one({"user_id": u["id"]}, {"_id": 0, "employment_status": 1}) or {}
        if prof.get("employment_status", "active") != "active":
            continue
        sal = await resolve_salary(u["id"], now_iso())
        allo = await db.compensation_allowances.find({"staff_user_id": u["id"], "active": True}, {"_id": 0, "amount_idr": 1}).to_list(500)
        out.append({"user_id": u["id"], "name": u.get("name"), "email": u.get("email"), "role": u.get("role"),
                    "salary_idr": sal["salary_idr"], "allowance_idr": int(sum(int(a.get("amount_idr") or 0) for a in allo))})
    return {"staff": out}


# ---------- payroll ----------
@comp_admin_r.get("/payroll/periods")
async def list_periods(user: dict = Depends(require_admin)):
    assert_admin_permission(user, "compensation.payroll.view")
    rows = await db.payroll_periods.find({}, {"_id": 0}).sort("period_key", -1).to_list(200)
    return {"periods": rows}


@comp_admin_r.post("/payroll/periods")
async def create_period(body: PeriodIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "compensation.payroll.manage")
    if await db.payroll_periods.find_one({"period_key": body.period_key}, {"_id": 0, "id": 1}):
        raise HTTPException(409, "Periode payroll sudah ada")
    doc = {"id": new_id(), "period_key": body.period_key, "status": "draft", "totals": {},
           "created_by": user["id"], "created_at": now_iso(), "updated_at": now_iso(),
           "approved_by": None, "paid_by": None, "finalized_by": None}
    await db.payroll_periods.insert_one(doc)
    doc.pop("_id", None)
    return doc


@comp_admin_r.post("/payroll/periods/{period_id}/generate")
async def generate_payroll(period_id: str, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "compensation.payroll.manage")
    period = await db.payroll_periods.find_one({"id": period_id}, {"_id": 0})
    if not period:
        raise HTTPException(404, "Periode tidak ditemukan")
    if period["status"] not in ("draft", "review"):
        raise HTTPException(409, "Payroll hanya dapat dihitung ulang saat draft/review")
    period_key = period["period_key"]
    start, end = _period_bounds(period_key)
    # payment date policy: no proration — use effective salary on the period end date
    staff_resp = await list_staff_comp(user)  # reuses eligible-staff resolution
    revenue = await _revenue_for_period(start, end)  # total paid Xendit revenue this month
    schemes = await db.bonus_schemes.find({"active": True}, {"_id": 0}).to_list(500)
    await db.payroll_items.delete_many({"payroll_period_id": period_id})
    items = []
    grand = 0
    for s in staff_resp["staff"]:
        uid = s["user_id"]
        sal = await resolve_salary(uid, end)
        allo = await _allowances_for_period(uid, start, end)
        adj = await _adjustments_for_period(uid, period_key)
        # bonus = sum of matching schemes' percent × total revenue (each staff earns full %)
        bonus_total, bonus_breakdown = _bonus_for_staff(uid, s["role"], revenue, start, end, schemes)
        gross = int(sal["salary_idr"]) + int(allo["total"]) + bonus_total + int(adj["total"])
        item = {
            "id": new_id(), "payroll_period_id": period_id, "period_key": period_key, "staff_user_id": uid,
            "staff_name": s["name"], "staff_email": s["email"],
            "salary_idr": int(sal["salary_idr"]), "salary_source": sal["source"],
            "allowance_idr": int(allo["total"]), "allowance_breakdown": allo["breakdown"],
            "bonus_idr": bonus_total, "bonus_breakdown": bonus_breakdown, "bonus_revenue_idr": int(revenue),
            "adjustment_idr": int(adj["total"]), "adjustment_breakdown": adj["breakdown"],
            "net_payable_idr": gross, "needs_review": bool(sal.get("needs_review")),
            "calculated_at": now_iso(),
        }
        items.append(item)
        grand += gross
    if items:
        await db.payroll_items.insert_many(items)
    totals = {"staff_count": len(items), "net_total_idr": grand}
    await db.payroll_periods.update_one({"id": period_id}, {"$set": {"totals": totals, "updated_at": now_iso()}})
    return {"ok": True, "totals": totals}


@comp_admin_r.get("/payroll/periods/{period_id}")
async def get_period(period_id: str, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "compensation.payroll.view")
    period = await db.payroll_periods.find_one({"id": period_id}, {"_id": 0})
    if not period:
        raise HTTPException(404, "Periode tidak ditemukan")
    items = await db.payroll_items.find({"payroll_period_id": period_id}, {"_id": 0}).sort("staff_name", 1).to_list(1000)
    return {"period": period, "items": items}


_TRANSITIONS = {
    "review": ("draft", "compensation.payroll.manage"),
    "approved": ("review", "compensation.payroll.approve"),
    "paid": ("approved", "compensation.payroll.mark_paid"),
    "finalized": ("paid", "compensation.payroll.finalize"),
}


@comp_admin_r.post("/payroll/periods/{period_id}/transition")
async def transition_period(period_id: str, body: TransitionIn, user: dict = Depends(require_admin)):
    if body.to not in _TRANSITIONS:
        raise HTTPException(400, "Transisi tidak valid")
    prev_status, perm = _TRANSITIONS[body.to]
    assert_admin_permission(user, perm)
    period = await db.payroll_periods.find_one({"id": period_id}, {"_id": 0})
    if not period:
        raise HTTPException(404, "Periode tidak ditemukan")
    if period["status"] == "finalized":
        raise HTTPException(409, "Payroll sudah final (immutable)")
    if period["status"] != prev_status:
        raise HTTPException(409, f"Transisi ke {body.to} butuh status {prev_status}, saat ini {period['status']}")
    stamp = {"review": None, "approved": "approved_by", "paid": "paid_by", "finalized": "finalized_by"}[body.to]
    fields = {"status": body.to, "updated_at": now_iso()}
    if stamp:
        fields[stamp] = user["id"]
        fields[stamp.replace("_by", "_at")] = now_iso()
    await db.payroll_periods.update_one({"id": period_id}, {"$set": fields})
    # Bonus is snapshotted directly into each payroll_item; immutability is enforced by the
    # finalized period status (no separate ledger to freeze).
    await log_activity(user["id"], f"payroll_{body.to}", "compensation", period_id)
    return {"ok": True, "status": body.to}
