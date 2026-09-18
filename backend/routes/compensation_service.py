"""Compensation & Payroll — Phase A foundation.

Reuses existing Staff identity (Admin users excl. Super Admin), existing
`staff_profiles.salary_current_idr` and `staff_salary_history`. NO parallel salary
master, NO new user type. Salary is resolved effective-dated and snapshotted into
payroll; today's salary is never used for historical periods.
"""
import asyncio
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from models import now_iso
from .deps import db, require_admin, SUPER_ADMIN
from .admin_permission_service import assert_admin_permission
from .compensation_payslip import generate_payslip_pdf, period_label

compensation_r = APIRouter(prefix="/compensation", tags=["compensation"])


async def resolve_salary(user_id: str, as_of_date: str) -> Dict[str, Any]:
    """Return the salary applicable on `as_of_date` (YYYY-MM-DD) from effective-dated
    history. Never silently uses today's salary for a historical date."""
    as_of = (as_of_date or now_iso())[:10]
    hist = await db.staff_salary_history.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
    applicable = [h for h in hist if str(h.get("effective_date") or "")[:10] <= as_of]
    if applicable:
        chosen = max(applicable, key=lambda h: str(h.get("effective_date") or ""))
        return {"salary_idr": int(chosen.get("new_idr") or 0), "source": "history",
                "effective_date": chosen.get("effective_date"), "needs_review": False}
    prof = await db.staff_profiles.find_one({"user_id": user_id}, {"_id": 0, "salary_current_idr": 1})
    if prof and prof.get("salary_current_idr") is not None:
        # No history entry effective on/before the date: fall back to current but flag if
        # future-dated history exists (must not silently apply a future salary).
        return {"salary_idr": int(prof["salary_current_idr"]), "source": "current_fallback",
                "effective_date": None, "needs_review": bool(hist)}
    return {"salary_idr": 0, "source": "none", "effective_date": None, "needs_review": True}


async def is_staff_user(user_id: str) -> bool:
    """Staff = active Admin user, excluding Super Admin."""
    u = await db.users.find_one({"id": user_id}, {"_id": 0, "role": 1, "status": 1})
    if not u or u.get("role") == SUPER_ADMIN or u.get("role") in {None, "label", "artist"}:
        return False
    if u.get("status") in {"suspended", "disabled", "merged"}:
        return False
    prof = await db.staff_profiles.find_one({"user_id": user_id}, {"_id": 0, "employment_status": 1})
    return (prof or {}).get("employment_status", "active") == "active"


async def _own_compensation(user_id: str) -> Dict[str, Any]:
    salary = await resolve_salary(user_id, now_iso())
    history = await db.staff_salary_history.find({"user_id": user_id}, {"_id": 0}).sort("changed_at", -1).to_list(50)
    # Payroll history: only rows from periods that are paid/finalized (immutable snapshots).
    payroll_periods = await db.payroll_periods.find({"status": {"$in": ["paid", "finalized"]}}, {"_id": 0, "id": 1, "status": 1}).to_list(500)
    status_by_period = {p["id"]: p["status"] for p in payroll_periods}
    period_ids = list(status_by_period.keys())
    payroll = await db.payroll_items.find(
        {"staff_user_id": user_id, "payroll_period_id": {"$in": period_ids}}, {"_id": 0},
    ).sort("calculated_at", -1).to_list(100) if period_ids else []
    for p in payroll:
        p["period_status"] = status_by_period.get(p.get("payroll_period_id"))
    # Bonus is realized through payroll snapshots (percent of Xendit revenue).
    bonus_history = [{
        "period_key": p.get("period_key"), "bonus_idr": int(p.get("bonus_idr") or 0),
        "breakdown": p.get("bonus_breakdown") or [], "revenue_idr": int(p.get("bonus_revenue_idr") or 0),
        "period_status": p.get("period_status"),
    } for p in payroll if int(p.get("bonus_idr") or 0)]
    return {
        "salary": salary,
        "salary_history": history,
        "payroll_history": payroll,
        "bonus_history": bonus_history,
        "bonus_total_idr": int(sum(b["bonus_idr"] for b in bonus_history)),
    }


@compensation_r.get("/me")
async def my_compensation(user: dict = Depends(require_admin)):
    assert_admin_permission(user, "compensation.view_own")
    return await _own_compensation(user["id"])


@compensation_r.get("/staff/{user_id}")
async def staff_compensation(user_id: str, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "compensation.view_team")
    if not await is_staff_user(user_id):
        raise HTTPException(status_code=404, detail="Staf tidak ditemukan atau tidak eligible")
    data = await _own_compensation(user_id)
    prof = await db.users.find_one({"id": user_id}, {"_id": 0, "name": 1, "email": 1, "role": 1})
    return {"staff": prof, **data}


@compensation_r.get("/payslip/{period_id}")
async def download_payslip(period_id: str, staff_user_id: Optional[str] = Query(default=None), user: dict = Depends(require_admin)):
    """Payslip PDF for a FINALIZED period. Self-service (view_own) for one's own
    slip; downloading another staff's slip requires view_team."""
    target = staff_user_id or user["id"]
    if target == user["id"]:
        assert_admin_permission(user, "compensation.view_own")
    else:
        assert_admin_permission(user, "compensation.view_team")
    period = await db.payroll_periods.find_one({"id": period_id}, {"_id": 0})
    if not period:
        raise HTTPException(status_code=404, detail="Periode payroll tidak ditemukan")
    if period.get("status") != "finalized":
        raise HTTPException(status_code=409, detail="Slip gaji hanya tersedia untuk periode yang sudah difinalisasi")
    item = await db.payroll_items.find_one({"payroll_period_id": period_id, "staff_user_id": target}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Slip gaji tidak ditemukan untuk staf ini pada periode tersebut")
    staff = await db.users.find_one({"id": target}, {"_id": 0, "name": 1, "email": 1, "role": 1}) or {}
    if not staff.get("name"):
        staff["name"] = item.get("staff_name")
        staff["email"] = item.get("staff_email")
    pdf_bytes = await asyncio.to_thread(generate_payslip_pdf, staff, period, item)
    safe_name = "".join(c for c in (staff.get("name") or "staf") if c.isalnum() or c in " -_").strip().replace(" ", "-")
    filename = f"Slip-Gaji-{safe_name}-{period['period_key']}.pdf"
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store, private"})
