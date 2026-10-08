"""System maintenance windows (D13).

Super Admin schedules maintenance: title, kind, mode, WIB start/end range,
affected modules, member-facing message and announcement lead time.
Labels read the active/upcoming windows for the member banner.

Status model mirrors the prototype: the stored ``status`` is the manual
override — ``active``/``completed``/``cancelled`` always win over the
time-derived state; ``scheduled`` defers to the clock.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from models import new_id, now_iso
from .deps import db, get_current_user, log_activity, require_super_admin

maint_r = APIRouter(prefix="/maintenance", tags=["maintenance"])
maint_admin_r = APIRouter(prefix="/admin/maintenance", tags=["maintenance"])

KINDS = ("scheduled", "emergency")
MODES = ("info", "readonly")
NOTIFY = ("none", "start", "1h", "24h")
MODULES = ("all", "releases", "payments", "royalty", "tickets", "wami", "addons", "account")
MANUAL_STATUS = ("active", "completed", "cancelled")
LEAD_MS = {"start": 0, "1h": 3_600_000, "24h": 86_400_000}


class MaintenanceIn(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    kind: Literal["scheduled", "emergency"] = "scheduled"
    mode: Literal["info", "readonly"] = "info"
    start_at: str
    end_at: str
    modules: List[str] = Field(min_length=1)
    message: str = Field(min_length=3, max_length=1000)
    notify: Literal["none", "start", "1h", "24h"] = "start"
    note: Optional[str] = Field(default=None, max_length=1000)


class MaintenancePatch(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=160)
    kind: Optional[Literal["scheduled", "emergency"]] = None
    mode: Optional[Literal["info", "readonly"]] = None
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    modules: Optional[List[str]] = None
    message: Optional[str] = Field(default=None, min_length=3, max_length=1000)
    notify: Optional[Literal["none", "start", "1h", "24h"]] = None
    note: Optional[str] = Field(default=None, max_length=1000)


class MaintenanceStatusIn(BaseModel):
    status: Literal["scheduled", "active", "completed", "cancelled"]
    note: Optional[str] = Field(default=None, max_length=1000)


def _parse(iso: str, field: str) -> datetime:
    try:
        v = iso.replace("Z", "+00:00") if iso.endswith("Z") else iso
        d = datetime.fromisoformat(v)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        raise HTTPException(status_code=400, detail=f"{field} bukan tanggal ISO yang valid")


def _validate(body: MaintenanceIn) -> None:
    start, end = _parse(body.start_at, "start_at"), _parse(body.end_at, "end_at")
    if end <= start:
        raise HTTPException(status_code=400, detail="Waktu selesai harus setelah waktu mulai")
    if not set(body.modules) <= set(MODULES):
        raise HTTPException(status_code=400, detail="Modul tidak dikenal")


def _ms(d: datetime) -> int:
    return int(d.timestamp() * 1000)


def effective_status(w: Dict[str, Any], now: Optional[datetime] = None) -> str:
    """Manual override wins; otherwise derived from the time range."""
    if w.get("status") in MANUAL_STATUS:
        return w["status"]
    now = now or datetime.now(timezone.utc)
    start, end = _parse(w["start_at"], "start_at"), _parse(w["end_at"], "end_at")
    if start <= now <= end:
        return "active"
    if now > end:
        return "completed"
    return "scheduled"


def _public(w: Dict[str, Any], now: datetime) -> Dict[str, Any]:
    start, end = _parse(w["start_at"], "start_at"), _parse(w["end_at"], "end_at")
    return {
        "id": w["id"], "title": w["title"], "kind": w["kind"], "mode": w["mode"],
        "status": effective_status(w, now), "start_at": w["start_at"], "end_at": w["end_at"],
        "duration_minutes": int((_ms(end) - _ms(start)) / 60000),
        "modules": w["modules"], "message": w["message"],
    }


def _visible(w: Dict[str, Any], now: datetime) -> bool:
    """Member-facing: announced from the chosen lead time until window end."""
    status = effective_status(w, now)
    if status in ("cancelled", "completed") or w.get("notify") == "none":
        return False
    if w.get("status") == "active":
        return True
    start, end = _parse(w["start_at"], "start_at"), _parse(w["end_at"], "end_at")
    lead = LEAD_MS.get(w.get("notify") or "start", 0)
    return _ms(start) - lead <= _ms(now) <= _ms(end)


@maint_r.get("/active")
async def active_windows(user: dict = Depends(get_current_user)):
    """Windows the signed-in member should see right now."""
    now = datetime.now(timezone.utc)
    rows = await db.maintenance_windows.find({}, {"_id": 0, "history": 0, "note": 0}).to_list(50)
    visible = [_public(w, now) for w in rows if _visible(w, now)]
    return {"windows": visible}


@maint_admin_r.get("")
async def list_windows(user: dict = Depends(require_super_admin)):
    rows = await db.maintenance_windows.find({}, {"_id": 0}).sort("start_at", -1).to_list(200)
    now = datetime.now(timezone.utc)
    for w in rows:
        w["effective_status"] = effective_status(w, now)
    return {"windows": rows}


@maint_admin_r.post("")
async def create_window(body: MaintenanceIn, user: dict = Depends(require_super_admin)):
    _validate(body)
    doc = {
        **body.model_dump(), "id": "MW-" + new_id()[:8].upper(),
        "status": "scheduled", "created_by": user["id"],
        "created_at": now_iso(), "updated_at": now_iso(),
        "history": [{"at": now_iso(), "by": user["id"], "action": "created", "note": body.note}],
    }
    await db.maintenance_windows.insert_one(doc)
    await log_activity(user["id"], "maintenance_create", "maintenance", doc["id"], after={"title": doc["title"]})
    doc.pop("_id", None)
    return doc


@maint_admin_r.patch("/{wid}")
async def update_window(wid: str, body: MaintenancePatch, user: dict = Depends(require_super_admin)):
    w = await db.maintenance_windows.find_one({"id": wid}, {"_id": 0})
    if not w:
        raise HTTPException(status_code=404, detail="Jadwal tidak ditemukan")
    patch = body.model_dump(exclude_unset=True)
    merged = MaintenanceIn(**{**{k: w[k] for k in MaintenanceIn.model_fields}, **patch})
    _validate(merged)
    changes = {k: v for k, v in patch.items() if w.get(k) != v}
    if not changes:
        return w
    await db.maintenance_windows.update_one(
        {"id": wid},
        {"$set": {**changes, "updated_at": now_iso()},
         "$push": {"history": {"at": now_iso(), "by": user["id"], "action": "updated", "note": body.note}}},
    )
    await log_activity(user["id"], "maintenance_update", "maintenance", wid, before={k: w.get(k) for k in changes}, after=changes)
    return await db.maintenance_windows.find_one({"id": wid}, {"_id": 0})


@maint_admin_r.post("/{wid}/status")
async def set_status(wid: str, body: MaintenanceStatusIn, user: dict = Depends(require_super_admin)):
    """Manual override: activate early, complete, or cancel. 'scheduled' clears the override."""
    w = await db.maintenance_windows.find_one({"id": wid}, {"_id": 0})
    if not w:
        raise HTTPException(status_code=404, detail="Jadwal tidak ditemukan")
    if w.get("status") == body.status:
        raise HTTPException(status_code=409, detail="Status sudah sama")
    await db.maintenance_windows.update_one(
        {"id": wid},
        {"$set": {"status": body.status, "updated_at": now_iso()},
         "$push": {"history": {"at": now_iso(), "by": user["id"], "action": f"status:{body.status}", "note": body.note}}},
    )
    await log_activity(user["id"], f"maintenance_{body.status}", "maintenance", wid,
                       before={"status": w.get("status")}, after={"status": body.status})
    return await db.maintenance_windows.find_one({"id": wid}, {"_id": 0})
