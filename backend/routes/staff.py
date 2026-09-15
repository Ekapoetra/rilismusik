"""PRD-04 Staff Management & Attendance.

Reuses existing systems: admin accounts (db.users + admin_role_id), dynamic RBAC
(assert_admin_permission), activity logs (log_activity), WIB time. Staff = admin
users EXCLUDING super_admin. Attendance is derived from work calendar + schedule +
login evidence + rules; login is evidence, not clock-in. Nothing here duplicates
auth, roles, work, notification or activity systems.
"""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from models import new_id, now_iso
from .deps import db, require_admin, log_activity, notify
from .admin_permission_service import assert_admin_permission, has_permission

staff_r = APIRouter(prefix="/admin", tags=["staff"])

WIB = timezone(timedelta(hours=7))
STATUSES = ["NOT_RECORDED", "PRESENT", "LATE", "ABSENT", "LEAVE", "HOLIDAY"]

DEFAULT_SCHEDULE = {"working_days": [1, 2, 3, 4, 5], "start": "08:00", "end": "17:00",
                    "break_start": "12:00", "break_end": "13:00", "effective_from": "2020-01-01"}
DEFAULT_RULES = {"grace_minutes": 15, "cutoff": "12:00", "evidence_start": "06:00", "effective_from": "2020-01-01"}
DEFAULT_LEAVE = {"types": ["annual", "sick", "permit"]}

# Staff = admin accounts EXCLUDING super_admin. Builtin admins carry role=admin_*;
# custom accounts carry admin_role_id. Labels/artists are never staff. Disabled/
# suspended accounts (soft-deleted via Pengguna Admin) are excluded from all lists.
STAFF_FILTER = {"$and": [{"role": {"$ne": "super_admin"}},
                         {"status": {"$nin": ["disabled", "suspended"]}},
                         {"$or": [{"role": {"$regex": "^admin"}}, {"admin_role_id": {"$ne": None}}]}]}


def _wib_now() -> datetime:
    return datetime.now(WIB)


def _wib_today() -> str:
    return _wib_now().date().isoformat()


def _to_min(hhmm: str) -> int:
    h, m = str(hhmm).split(":")
    return int(h) * 60 + int(m)


def _login_min(iso: str) -> int:
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(WIB)
    return dt.hour * 60 + dt.minute


async def _setting(key: str, default: dict) -> dict:
    doc = await db.admin_ui_settings.find_one({"key": key}, {"_id": 0, "value": 1})
    if not doc:
        await db.admin_ui_settings.update_one({"key": key}, {"$set": {"key": key, "value": default}}, upsert=True)
        return dict(default)
    return doc["value"]


async def _get_config() -> Dict[str, Any]:
    return {
        "schedule": await _setting("staff_work_schedule", DEFAULT_SCHEDULE),
        "rules": await _setting("staff_attendance_rules", DEFAULT_RULES),
        "leave_settings": await _setting("staff_leave_settings", DEFAULT_LEAVE),
    }


async def record_login_evidence(user: dict) -> None:
    """Called from auth on successful login. Stamps the FIRST login of the WIB day
    for an admin staff member as attendance evidence. Best-effort; never raises."""
    try:
        if user.get("role") == "super_admin" or not (user.get("admin_role_id") or user.get("role", "").startswith("admin")):
            return
        date = _wib_today()
        await db.attendance_evidence.update_one(
            {"user_id": user["id"], "date": date},
            {"$setOnInsert": {"id": new_id(), "user_id": user["id"], "date": date, "first_login_at": now_iso()}},
            upsert=True,
        )
    except Exception:
        pass


async def _staff_user_ids() -> List[str]:
    ids = []
    async for u in db.users.find(STAFF_FILTER, {"_id": 0, "id": 1}):
        ids.append(u["id"])
    return ids


async def _is_holiday(date: str) -> Optional[str]:
    doc = await db.staff_holidays.find_one({"date": date}, {"_id": 0, "name": 1})
    return doc["name"] if doc else None


async def _approved_leave(user_id: str, date: str) -> bool:
    return bool(await db.leave_requests.find_one(
        {"user_id": user_id, "status": "approved", "start_date": {"$lte": date}, "end_date": {"$gte": date}},
        {"_id": 0, "id": 1}))


async def evaluate(user_id: str, date: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Derive attendance for a staff/date. Frozen past days are read from
    attendance_records; corrections override. Returns dict with status + evidence."""
    correction = await db.attendance_corrections.find_one({"user_id": user_id, "date": date}, {"_id": 0}, sort=[("created_at", -1)])
    frozen = await db.attendance_records.find_one({"user_id": user_id, "date": date}, {"_id": 0})
    if frozen:
        out = {"status": frozen["status"], "evidence_login_at": frozen.get("evidence_login_at"), "frozen": True}
        if correction:
            out.update({"status": correction["final_status"], "corrected": True, "original_status": correction["original_status"]})
        return out

    schedule, rules = cfg["schedule"], cfg["rules"]
    holiday = await _is_holiday(date)
    weekday_iso = datetime.fromisoformat(date).isoweekday()
    ev = await db.attendance_evidence.find_one({"user_id": user_id, "date": date}, {"_id": 0, "first_login_at": 1})
    login_at = ev["first_login_at"] if ev else None

    if holiday or weekday_iso not in schedule.get("working_days", DEFAULT_SCHEDULE["working_days"]):
        status = "HOLIDAY"
    elif await _approved_leave(user_id, date):
        status = "LEAVE"
    elif login_at:
        lm = _login_min(login_at)
        start_m, grace = _to_min(schedule["start"]), int(rules.get("grace_minutes", 15))
        cutoff = _to_min(rules.get("cutoff", "12:00"))
        if lm > cutoff:
            status = "ABSENT"  # first evidence only after cutoff is not valid morning attendance
        elif lm <= start_m + grace:
            status = "PRESENT"
        else:
            status = "LATE"
    else:
        is_today = date == _wib_today()
        past_cutoff = (_wib_now().hour * 60 + _wib_now().minute) >= _to_min(rules.get("cutoff", "12:00"))
        status = ("NOT_RECORDED" if (is_today and not past_cutoff) else "ABSENT") if is_today else "ABSENT"

    result = {"status": status, "evidence_login_at": login_at, "frozen": False}
    # Freeze finalized past working days so later config changes cannot rewrite history.
    if date < _wib_today() and status != "NOT_RECORDED":
        await db.attendance_records.update_one(
            {"user_id": user_id, "date": date},
            {"$setOnInsert": {"id": new_id(), "user_id": user_id, "date": date, "status": status,
                              "evidence_login_at": login_at, "schedule_snapshot": schedule, "created_at": now_iso()}},
            upsert=True,
        )
    if correction:
        result.update({"status": correction["final_status"], "corrected": True, "original_status": correction["original_status"]})
    return result


# ---------- Staff list & detail ----------
async def _staff_row(u: dict) -> dict:
    prof = await db.staff_profiles.find_one({"user_id": u["id"]}, {"_id": 0}) or {}
    return {
        "user_id": u["id"], "name": u.get("name") or u.get("email"), "email": u.get("email"),
        "role": u.get("role"), "admin_role_id": u.get("admin_role_id") or u.get("role"),
        "employment_status": prof.get("employment_status", "active"),
        "join_date": prof.get("join_date"), "salary_idr": prof.get("salary_current_idr"),
    }


@staff_r.get("/staff")
async def list_staff(user: dict = Depends(require_admin), include_inactive: bool = True):
    assert_admin_permission(user, "staff.view")
    users = await db.users.find(STAFF_FILTER, {"_id": 0}).to_list(1000)
    rows = [await _staff_row(u) for u in users]
    if not include_inactive:
        rows = [r for r in rows if r["employment_status"] == "active"]
    role_names = {r["id"]: r["name"] async for r in db.admin_roles.find({}, {"_id": 0, "id": 1, "name": 1})}
    for r in rows:
        r["role_name"] = role_names.get(r["admin_role_id"], r["admin_role_id"])
    rows.sort(key=lambda r: (r["employment_status"] != "active", (r["name"] or "").lower()))
    return {"staff": rows}


@staff_r.get("/staff/config")
async def get_staff_config(user: dict = Depends(require_admin)):
    assert_admin_permission(user, "staff.view")
    cfg = await _get_config()
    cfg["holidays"] = await db.staff_holidays.find({}, {"_id": 0}).sort("date", 1).to_list(500)
    return cfg


class ConfigSectionIn(BaseModel):
    section: str
    value: Dict[str, Any]


@staff_r.put("/staff/config")
async def update_staff_config(body: ConfigSectionIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "staff.config.manage")
    key_map = {"schedule": "staff_work_schedule", "rules": "staff_attendance_rules", "leave_settings": "staff_leave_settings"}
    if body.section not in key_map:
        raise HTTPException(status_code=400, detail="Section tidak valid")
    key = key_map[body.section]
    before = await _setting(key, {})
    value = dict(body.value)
    if body.section in ("schedule", "rules"):
        value["effective_from"] = value.get("effective_from") or _wib_today()
    await db.admin_ui_settings.update_one({"key": key}, {"$set": {"key": key, "value": value, "updated_by": user["id"], "updated_at": now_iso()}}, upsert=True)
    await log_activity(user["id"], "staff_config_update", "staff", body.section, before={"value": before}, after={"value": value})
    return {"ok": True, "section": body.section, "value": value}


class HolidayIn(BaseModel):
    date: str
    name: str = Field(min_length=1, max_length=120)


@staff_r.post("/staff/config/holidays")
async def add_holiday(body: HolidayIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "staff.config.manage")
    doc = {"id": new_id(), "date": body.date, "name": body.name, "created_at": now_iso()}
    await db.staff_holidays.update_one({"date": body.date}, {"$set": {"name": body.name}, "$setOnInsert": {"id": doc["id"], "date": body.date, "created_at": doc["created_at"]}}, upsert=True)
    await log_activity(user["id"], "staff_holiday_add", "staff", body.date, after={"name": body.name})
    return {"ok": True}


@staff_r.delete("/staff/config/holidays/{date}")
async def remove_holiday(date: str, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "staff.config.manage")
    await db.staff_holidays.delete_one({"date": date})
    await log_activity(user["id"], "staff_holiday_remove", "staff", date)
    return {"ok": True}


class EmploymentIn(BaseModel):
    status: str  # active | inactive


@staff_r.post("/staff/{user_id}/employment")
async def set_employment(user_id: str, body: EmploymentIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "staff.manage")
    if body.status not in ("active", "inactive"):
        raise HTTPException(status_code=400, detail="Status tidak valid")
    target = await db.users.find_one({"id": user_id}, {"_id": 0, "id": 1, "role": 1})
    if not target or target.get("role") == "super_admin":
        raise HTTPException(status_code=404, detail="Staf tidak ditemukan")
    prof = await db.staff_profiles.find_one({"user_id": user_id}, {"_id": 0, "employment_status": 1})
    before = (prof or {}).get("employment_status", "active")
    await db.staff_profiles.update_one({"user_id": user_id}, {"$set": {"employment_status": body.status, "updated_at": now_iso()}, "$setOnInsert": {"id": new_id(), "user_id": user_id}}, upsert=True)
    await log_activity(user["id"], "staff_employment_update", "staff", user_id, before={"employment_status": before}, after={"employment_status": body.status})
    return {"ok": True}


class SalaryIn(BaseModel):
    salary_idr: int = Field(ge=0)
    effective_date: Optional[str] = None
    join_date: Optional[str] = None


@staff_r.post("/staff/{user_id}/salary")
async def set_salary(user_id: str, body: SalaryIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "staff.manage")
    prof = await db.staff_profiles.find_one({"user_id": user_id}, {"_id": 0}) or {}
    prev = prof.get("salary_current_idr")
    eff = body.effective_date or _wib_today()
    await db.staff_salary_history.insert_one({"id": new_id(), "user_id": user_id, "previous_idr": prev,
                                              "new_idr": int(body.salary_idr), "effective_date": eff,
                                              "changed_by": user["id"], "changed_at": now_iso()})
    setter = {"salary_current_idr": int(body.salary_idr), "updated_at": now_iso()}
    if body.join_date:
        setter["join_date"] = body.join_date
    await db.staff_profiles.update_one({"user_id": user_id}, {"$set": setter, "$setOnInsert": {"id": new_id(), "user_id": user_id, "employment_status": "active"}}, upsert=True)
    await log_activity(user["id"], "staff_salary_update", "staff", user_id, before={"salary_idr": prev}, after={"salary_idr": int(body.salary_idr), "effective_date": eff})
    return {"ok": True}


@staff_r.get("/staff/{user_id}")
async def staff_detail(user_id: str, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "staff.view")
    u = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not u or u.get("role") == "super_admin":
        raise HTTPException(status_code=404, detail="Staf tidak ditemukan")
    row = await _staff_row(u)
    row["salary_history"] = await db.staff_salary_history.find({"user_id": user_id}, {"_id": 0}).sort("changed_at", -1).to_list(50)
    # 30-day attendance summary
    cfg = await _get_config()
    summary = {s: 0 for s in STATUSES}
    today = _wib_now().date()
    for i in range(30):
        d = (today - timedelta(days=i)).isoformat()
        res = await evaluate(user_id, d, cfg)
        summary[res["status"]] = summary.get(res["status"], 0) + 1
    row["attendance_summary_30d"] = summary
    return row


# ---------- Attendance ----------
@staff_r.get("/attendance")
async def attendance_day(date: Optional[str] = None, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "staff.attendance.view")
    date = date or _wib_today()
    cfg = await _get_config()
    users = await db.users.find(STAFF_FILTER, {"_id": 0, "id": 1, "name": 1, "email": 1}).to_list(1000)
    rows = []
    for u in users:
        prof = await db.staff_profiles.find_one({"user_id": u["id"]}, {"_id": 0, "employment_status": 1})
        if (prof or {}).get("employment_status", "active") != "active":
            continue
        res = await evaluate(u["id"], date, cfg)
        rows.append({"user_id": u["id"], "name": u.get("name") or u.get("email"), **res})
    return {"date": date, "rows": rows}


class CorrectionIn(BaseModel):
    date: str
    final_status: str
    reason: str = Field(min_length=3, max_length=500)


@staff_r.post("/attendance/{user_id}/correct")
async def correct_attendance(user_id: str, body: CorrectionIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "staff.attendance.correct")
    if body.final_status not in STATUSES:
        raise HTTPException(status_code=400, detail="Status tidak valid")
    cfg = await _get_config()
    current = await evaluate(user_id, body.date, cfg)
    await db.attendance_corrections.insert_one({"id": new_id(), "user_id": user_id, "date": body.date,
                                                "original_status": current["status"], "final_status": body.final_status,
                                                "reason": body.reason, "actor": user["id"], "created_at": now_iso()})
    await log_activity(user["id"], "attendance_correction", "staff", f"{user_id}:{body.date}",
                       before={"status": current["status"]}, after={"status": body.final_status, "reason": body.reason})
    return {"ok": True, "final_status": body.final_status}


# ---------- Leave ----------
class LeaveIn(BaseModel):
    type: str = "permit"
    start_date: str
    end_date: str
    reason: str = Field(min_length=3, max_length=500)


@staff_r.get("/leave")
async def list_leave(status: Optional[str] = None, user: dict = Depends(require_admin)):
    can_view_all = has_permission(user, "staff.leave.approve") or has_permission(user, "staff.attendance.view")
    q: Dict[str, Any] = {}
    if not can_view_all:
        q["user_id"] = user["id"]  # self-service scope
    if status:
        q["status"] = status
    items = await db.leave_requests.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    uids = list({i["user_id"] for i in items})
    names = {u["id"]: (u.get("name") or u.get("email")) async for u in db.users.find({"id": {"$in": uids}}, {"_id": 0, "id": 1, "name": 1, "email": 1})}
    for i in items:
        i["staff_name"] = names.get(i["user_id"], i["user_id"])
    return {"items": items, "can_approve": has_permission(user, "staff.leave.approve")}


@staff_r.post("/leave")
async def submit_leave(body: LeaveIn, user: dict = Depends(require_admin)):
    if user.get("role") == "super_admin":
        raise HTTPException(status_code=400, detail="Super Admin bukan staf")
    if body.end_date < body.start_date:
        raise HTTPException(status_code=400, detail="Tanggal selesai sebelum mulai")
    doc = {"id": new_id(), "user_id": user["id"], "type": body.type, "start_date": body.start_date,
           "end_date": body.end_date, "reason": body.reason, "status": "pending", "created_at": now_iso()}
    await db.leave_requests.insert_one(doc)
    await log_activity(user["id"], "leave_request", "staff", doc["id"], after={"range": f"{body.start_date}..{body.end_date}"})
    return {"ok": True, "id": doc["id"]}


class LeaveActionIn(BaseModel):
    action: str  # approve | reject
    note: Optional[str] = None


@staff_r.post("/leave/{leave_id}/action")
async def action_leave(leave_id: str, body: LeaveActionIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "staff.leave.approve")
    if body.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Aksi tidak dikenal")
    lr = await db.leave_requests.find_one({"id": leave_id}, {"_id": 0})
    if not lr or lr["status"] != "pending":
        raise HTTPException(status_code=404, detail="Permohonan tidak ditemukan / sudah diproses")
    new_status = "approved" if body.action == "approve" else "rejected"
    await db.leave_requests.update_one({"id": leave_id}, {"$set": {"status": new_status, "decided_by": user["id"], "decided_at": now_iso(), "decision_note": body.note}})
    await log_activity(user["id"], f"leave_{body.action}", "staff", leave_id, after={"status": new_status})
    label = "disetujui" if new_status == "approved" else "ditolak"
    await notify(
        lr["user_id"], "leave_decision",
        f"Permohonan cuti {label}",
        f"Cuti Anda ({lr['start_date']} → {lr['end_date']}) telah {label}." + (f" Catatan: {body.note}" if body.note else ""),
        "/admin/status", {"leave_id": leave_id, "status": new_status},
    )
    return {"ok": True, "status": new_status}


# ---------- Workspace → Status ----------
@staff_r.get("/status/me")
async def status_me(user: dict = Depends(require_admin)):
    if user.get("role") == "super_admin":
        return {"is_staff": False}
    cfg = await _get_config()
    res = await evaluate(user["id"], _wib_today(), cfg)
    summary = {s: 0 for s in STATUSES}
    today = _wib_now().date()
    for i in range(30):
        r = await evaluate(user["id"], (today - timedelta(days=i)).isoformat(), cfg)
        summary[r["status"]] = summary.get(r["status"], 0) + 1
    return {"is_staff": True, "today": res, "summary_30d": summary}


@staff_r.get("/status/team")
async def status_team(user: dict = Depends(require_admin)):
    assert_admin_permission(user, "staff.attendance.view")
    return await attendance_day(date=_wib_today(), user=user)


@staff_r.get("/attendance/summary")
async def attendance_summary(date: Optional[str] = None, user: dict = Depends(require_admin)):
    """Today's attendance counts for the Dashboard card. Requires team-view permission."""
    assert_admin_permission(user, "staff.attendance.view")
    date = date or _wib_today()
    data = await attendance_day(date=date, user=user)
    counts = {s: 0 for s in STATUSES}
    for r in data["rows"]:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"date": date, "total": len(data["rows"]), "counts": counts}


async def finalize_yesterday_attendance():
    """Daily cron: freeze the previous WIB day's attendance for all active staff so
    'Tidak Hadir' (and other) statuses become immutable history, even if no one opened
    the Attendance page. evaluate() persists a frozen snapshot for any past working day."""
    from .deps import logger
    date = (_wib_now().date() - timedelta(days=1)).isoformat()
    cfg = await _get_config()
    frozen = 0
    users = await db.users.find(STAFF_FILTER, {"_id": 0, "id": 1}).to_list(2000)
    for u in users:
        prof = await db.staff_profiles.find_one({"user_id": u["id"]}, {"_id": 0, "employment_status": 1})
        if (prof or {}).get("employment_status", "active") != "active":
            continue
        res = await evaluate(u["id"], date, cfg)
        if res.get("frozen") or res["status"] != "NOT_RECORDED":
            frozen += 1
    logger.info("[STAFF] finalized attendance for %s: %d staff", date, frozen)
    return {"date": date, "finalized": frozen}

