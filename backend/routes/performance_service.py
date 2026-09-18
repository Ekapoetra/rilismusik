"""PRD-05 KPI & Performance — derived measurement layer.

Performance is COMPUTED from authoritative Work / Work History data (work_items),
Role/Responsibility mapping, and Staff/Attendance. It never duplicates Work records
and never mutates history. Business-sensitive configuration (weights, targets,
scoring curve, category thresholds, confidence policy) is stored in admin_ui_settings,
effective-dated, and every change is audited. Finalized periods snapshot the config
used so later configuration changes cannot silently rewrite finalized results.
"""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from models import new_id, now_iso
from .deps import db, require_admin, log_activity
from .admin_permission_service import assert_admin_permission, has_permission
from .work_service import WORK_TYPES, WORK_TYPE_MAP, applicable_work_types, get_work_settings
from .staff import STAFF_FILTER

perf_r = APIRouter(prefix="/admin/performance", tags=["performance"])

WIB = timezone(timedelta(hours=7))

# ---- Reasonable DEFAULTS (editable in the Configuration page; not permanent policy) ----
DEFAULT_WEIGHTS = {
    "release_review": 3.0, "release_go_live": 2.0, "withdraw_verification": 2.0,
    "kyc_review": 2.0, "support_ticket": 1.0, "legacy_claim": 2.0,
    "addon_processing": 2.0, "wami_registration": 1.0, "sensitive_approval": 3.0,
    "bank_verification": 2.0,
}
DEFAULT_SCORING = {
    "component_weights": {"achievement": 0.4, "timeliness": 0.4, "complexity": 0.2, "quality": 0.0},
    "achievement_curve": {"cap": 100},          # achievement% capped at 100 (no unbounded scores)
    "complexity_reference": {"default": None, "roles": {}},  # weighted-output reference; unset → unavailable
    "categories": [
        {"key": "excellent", "name_id": "Sangat Baik", "name_en": "Excellent", "min": 90},
        {"key": "strong", "name_id": "Kuat", "name_en": "Strong", "min": 75},
        {"key": "meets", "name_id": "Memenuhi Ekspektasi", "name_en": "Meets Expectations", "min": 60},
        {"key": "needs_improvement", "name_id": "Perlu Peningkatan", "name_en": "Needs Improvement", "min": 40},
        {"key": "below", "name_id": "Di Bawah Ekspektasi", "name_en": "Below Expectations", "min": 0},
    ],
    "confidence": {"high": 20, "moderate": 8, "low": 1},  # completed-work sample thresholds
    "min_sample_to_show": 1,   # below this the overall score is suppressed (insufficient data)
}
# Targets default to EMPTY (Not Applicable) so we never invent business target numbers.
DEFAULT_TARGETS: Dict[str, Any] = {}


# ---------- config (admin_ui_settings; effective-dated + audited) ----------
async def _cfg_doc(key: str, default: Any) -> Dict[str, Any]:
    doc = await db.admin_ui_settings.find_one({"key": key}, {"_id": 0})
    if not doc:
        doc = {"key": key, "value": default, "effective_from": _wib_today(), "updated_at": now_iso()}
        await db.admin_ui_settings.update_one({"key": key}, {"$set": doc}, upsert=True)
    return doc


async def get_perf_config() -> Dict[str, Any]:
    weights = (await _cfg_doc("performance_weights", DEFAULT_WEIGHTS))["value"]
    # Backfill any newly-added work type weight without overwriting customized values.
    changed = False
    for wt in WORK_TYPES:
        if wt["key"] not in weights:
            weights[wt["key"]] = DEFAULT_WEIGHTS.get(wt["key"], 1.0); changed = True
    if changed:
        await db.admin_ui_settings.update_one({"key": "performance_weights"}, {"$set": {"value": weights}})
    targets = (await _cfg_doc("performance_targets", DEFAULT_TARGETS))["value"]
    scoring = (await _cfg_doc("performance_scoring", DEFAULT_SCORING))["value"]
    for k, v in DEFAULT_SCORING.items():
        scoring.setdefault(k, v)
    return {"weights": weights, "targets": targets, "scoring": scoring}


async def _audit_config(actor: str, section: str, before: Any, after: Any, reason: str) -> None:
    await db.performance_config_audit.insert_one({
        "id": new_id(), "section": section, "actor": actor, "reason": reason,
        "before": before, "after": after, "created_at": now_iso(),
    })
    await log_activity(actor, "performance_config_update", "performance", section,
                       before={"value": before}, after={"value": after, "reason": reason})


# ---------- time helpers ----------
def _wib_now() -> datetime:
    return datetime.now(WIB)


def _wib_today() -> str:
    return _wib_now().date().isoformat()


def _parse(iso: Optional[str]) -> Optional[datetime]:
    if not iso:
        return None
    try:
        d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _period_bounds(period: str) -> tuple:
    y, m = int(period[:4]), int(period[5:7])
    start = datetime(y, m, 1, tzinfo=WIB)
    end = datetime(y + (m // 12), (m % 12) + 1, 1, tzinfo=WIB)
    return start.astimezone(timezone.utc).isoformat(), end.astimezone(timezone.utc).isoformat()


def current_period() -> str:
    return _wib_now().strftime("%Y-%m")


# ---------- period finalization state ----------
async def _period_state(period: str) -> Dict[str, Any]:
    doc = await db.performance_periods.find_one({"period": period}, {"_id": 0})
    return doc or {"period": period, "state": "open"}


def _resolve_target(targets: Dict[str, Any], wt: str, role_id: str, user_id: str) -> Optional[float]:
    node = targets.get(wt) or {}
    users = node.get("users") or {}
    roles = node.get("roles") or {}
    if user_id in users and users[user_id] is not None:
        return float(users[user_id])
    if role_id in roles and roles[role_id] is not None:
        return float(roles[role_id])
    if node.get("default") is not None:
        return float(node["default"])
    return None


def _category(scoring: Dict[str, Any], score: Optional[float]) -> Optional[Dict[str, Any]]:
    if score is None:
        return None
    for c in sorted(scoring["categories"], key=lambda x: -x["min"]):
        if score >= c["min"]:
            return {"key": c["key"], "name_id": c["name_id"], "name_en": c["name_en"]}
    return None


def _confidence(scoring: Dict[str, Any], sample: int) -> str:
    conf = scoring.get("confidence", DEFAULT_SCORING["confidence"])
    if sample >= conf.get("high", 20):
        return "high"
    if sample >= conf.get("moderate", 8):
        return "moderate"
    if sample >= conf.get("low", 1):
        return "low"
    return "insufficient"


# ---------- core computation ----------
async def compute_staff_performance(user_id: str, role_id: str, period: str,
                                    cfg: Dict[str, Any], sla: Dict[str, int],
                                    role_perms_map: Dict[str, Any]) -> Dict[str, Any]:
    weights = cfg["weights"]
    targets = cfg["targets"]
    scoring = cfg["scoring"]
    start_utc, end_utc = _period_bounds(period)

    # Completed work attributed to this staff in-period (exclude super-admin completions).
    items = await db.work_items.find(
        {"status": "completed", "completed_by": user_id, "completed_by_super": {"$ne": True},
         "completed_at": {"$gte": start_utc, "$lt": end_utc}},
        {"_id": 0, "work_type": 1, "opened_at": 1, "completed_at": 1},
    ).to_list(50000)

    by_type: Dict[str, int] = {}
    on_time = late = 0
    resolution_hours: List[float] = []
    for it in items:
        wt = it["work_type"]
        by_type[wt] = by_type.get(wt, 0) + 1
        opened, completed = _parse(it.get("opened_at")), _parse(it.get("completed_at"))
        if opened and completed:
            resolution_hours.append(max(0.0, (completed - opened).total_seconds() / 3600.0))
            due = opened + timedelta(days=int(sla.get(wt, 2)))
            if completed <= due:
                on_time += 1
            else:
                late += 1

    completed_count = len(items)
    weighted_output = round(sum(cnt * float(weights.get(wt, 1.0)) for wt, cnt in by_type.items()), 2)

    # Applicable work types = those this staff's role holds the permission for.
    applicable = applicable_work_types(role_perms_map.get(role_id) or set())

    # --- Achievement (needs configured targets) ---
    ach_entries = []
    for wt in applicable:
        target = _resolve_target(targets, wt, role_id, user_id)
        if target and target > 0:
            actual = by_type.get(wt, 0)
            ach_entries.append({
                "work_type": wt, "actual": actual, "target": target,
                "achievement_pct": round(actual / target * 100, 1), "weight": float(weights.get(wt, 1.0)),
            })
    achievement_component = None
    achievement_avg = None
    if ach_entries:
        wsum = sum(e["weight"] for e in ach_entries) or 1.0
        achievement_avg = round(sum(e["achievement_pct"] * e["weight"] for e in ach_entries) / wsum, 1)
        cap = scoring["achievement_curve"].get("cap", 100)
        achievement_component = min(float(cap), achievement_avg)

    # --- Timeliness ---
    timed = on_time + late
    timeliness_component = round(on_time / timed * 100, 1) if timed > 0 else None

    # --- Complexity (needs configured weighted-output reference) ---
    comp_ref = (scoring.get("complexity_reference") or {})
    reference = (comp_ref.get("roles") or {}).get(role_id, comp_ref.get("default"))
    complexity_component = None
    if reference and float(reference) > 0:
        complexity_component = min(100.0, round(weighted_output / float(reference) * 100, 1))

    # --- Quality (no reliable per-staff evidence in codebase) ---
    quality_component = None
    quality_status = "unavailable"

    # --- Overall (normalize over AVAILABLE components) ---
    cw = scoring["component_weights"]
    components = {
        "achievement": {"score": achievement_component, "weight": cw.get("achievement", 0)},
        "timeliness": {"score": timeliness_component, "weight": cw.get("timeliness", 0)},
        "complexity": {"score": complexity_component, "weight": cw.get("complexity", 0)},
        "quality": {"score": quality_component, "weight": cw.get("quality", 0)},
    }
    avail = {k: v for k, v in components.items() if v["score"] is not None and v["weight"] > 0}
    overall = None
    if avail and completed_count >= scoring.get("min_sample_to_show", 1):
        wsum = sum(v["weight"] for v in avail.values()) or 1.0
        overall = round(sum(v["score"] * v["weight"] for v in avail.values()) / wsum, 1)

    confidence = _confidence(scoring, completed_count)

    return {
        "user_id": user_id, "role_id": role_id, "period": period,
        "completed_count": completed_count,
        "weighted_output": weighted_output,
        "by_type": [{"work_type": wt, "label_id": WORK_TYPE_MAP.get(wt, {}).get("label_id", wt),
                     "label_en": WORK_TYPE_MAP.get(wt, {}).get("label_en", wt),
                     "count": cnt, "weight": float(weights.get(wt, 1.0))}
                    for wt, cnt in sorted(by_type.items(), key=lambda x: -x[1])],
        "timeliness": {"on_time": on_time, "late": late,
                       "on_time_pct": timeliness_component},
        "work_timing": {
            "queue_time": None, "processing_time": None,  # started_at not tracked → Not Available
            "resolution_time_hours": round(sum(resolution_hours) / len(resolution_hours), 1) if resolution_hours else None,
            "unavailable_reason": "started_at (waktu mulai) tidak dilacak di sistem Work saat ini",
        },
        "achievement": {"entries": ach_entries, "weighted_pct": achievement_avg},
        "quality": {"status": quality_status, "value": quality_component},
        "components": components,
        "overall_score": overall,
        "category": _category(scoring, overall),
        "confidence": confidence,
    }


async def _active_staff() -> List[Dict[str, Any]]:
    users = await db.users.find(STAFF_FILTER, {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1, "admin_role_id": 1}).to_list(2000)
    out = []
    for u in users:
        prof = await db.staff_profiles.find_one({"user_id": u["id"]}, {"_id": 0, "employment_status": 1})
        if (prof or {}).get("employment_status", "active") != "active":
            continue
        out.append(u)
    return out


async def _config_for_period(period: str) -> Dict[str, Any]:
    """Finalized periods use their frozen snapshot; open periods use current config."""
    st = await _period_state(period)
    if st.get("state") == "finalized" and st.get("config_snapshot"):
        return st["config_snapshot"]
    return await get_perf_config()


# ---------- endpoints ----------
def _ensure(user: dict, permission: str) -> None:
    assert_admin_permission(user, permission)


@perf_r.get("/config")
async def get_config(user: dict = Depends(require_admin)):
    if not (has_permission(user, "performance.config.manage") or has_permission(user, "performance.view_team")):
        raise HTTPException(status_code=403, detail={"code": "PERMISSION_DENIED", "message": "Tidak diizinkan"})
    cfg = await get_perf_config()
    role_names = {r["id"]: r["name"] async for r in db.admin_roles.find({}, {"_id": 0, "id": 1, "name": 1})}
    return {
        **cfg,
        "work_types": [{"key": w["key"], "label_id": w["label_id"], "label_en": w["label_en"]} for w in WORK_TYPES],
        "roles": [{"id": rid, "name": nm} for rid, nm in role_names.items()],
        "can_manage": has_permission(user, "performance.config.manage"),
    }


class ConfigIn(BaseModel):
    section: str  # weights | targets | scoring
    value: Dict[str, Any]
    reason: str = Field(default="", max_length=500)


@perf_r.put("/config")
async def update_config(body: ConfigIn, user: dict = Depends(require_admin)):
    _ensure(user, "performance.config.manage")
    key_map = {"weights": "performance_weights", "targets": "performance_targets", "scoring": "performance_scoring"}
    if body.section not in key_map:
        raise HTTPException(status_code=400, detail="Section tidak valid")
    key = key_map[body.section]
    prev = await db.admin_ui_settings.find_one({"key": key}, {"_id": 0, "value": 1})
    before = (prev or {}).get("value")
    await db.admin_ui_settings.update_one(
        {"key": key},
        {"$set": {"key": key, "value": body.value, "effective_from": _wib_today(),
                  "updated_by": user["id"], "updated_at": now_iso()}},
        upsert=True,
    )
    await _audit_config(user["id"], body.section, before, body.value, body.reason)
    return {"ok": True, "section": body.section, "value": body.value}


async def _role_perms_map() -> Dict[str, set]:
    """{role_id/key -> set(permissions)} for all admin roles (KPI applicability source)."""
    out: Dict[str, set] = {}
    async for r in db.admin_roles.find({}, {"_id": 0, "id": 1, "key": 1, "permissions": 1}):
        perms = set(r.get("permissions") or [])
        out[r["id"]] = perms
        if r.get("key"):
            out.setdefault(r["key"], perms)
    return out


@perf_r.get("/me")
async def my_performance(period: Optional[str] = None, user: dict = Depends(require_admin)):
    _ensure(user, "performance.view_own")
    if user.get("role") == "super_admin":
        return {"is_staff": False, "message": "Super Admin tidak dinilai sebagai staf"}
    period = period or current_period()
    cfg = await _config_for_period(period)
    sla = (await get_work_settings())["sla_days"]
    role_perms_map = await _role_perms_map()
    role_id = user.get("admin_role_id") or user.get("role")
    data = await compute_staff_performance(user["id"], role_id, period, cfg, sla, role_perms_map)
    st = await _period_state(period)
    return {"is_staff": True, "period": period, "period_state": st.get("state", "open"),
            "name": user.get("name") or user.get("email"), **data}


@perf_r.get("/overview")
async def overview(period: Optional[str] = None, user: dict = Depends(require_admin)):
    _ensure(user, "performance.view_team")
    period = period or current_period()
    cfg = await _config_for_period(period)
    sla = (await get_work_settings())["sla_days"]
    role_perms_map = await _role_perms_map()
    role_names = {r["id"]: r["name"] async for r in db.admin_roles.find({}, {"_id": 0, "id": 1, "name": 1})}
    rows = []
    for u in await _active_staff():
        role_id = u.get("admin_role_id") or u.get("role")
        d = await compute_staff_performance(u["id"], role_id, period, cfg, sla, role_perms_map)
        rows.append({
            "user_id": u["id"], "name": u.get("name") or u.get("email"),
            "role_id": role_id, "role_name": role_names.get(role_id, role_id),
            "completed_count": d["completed_count"], "weighted_output": d["weighted_output"],
            "on_time_pct": d["timeliness"]["on_time_pct"], "overall_score": d["overall_score"],
            "category": d["category"], "confidence": d["confidence"],
        })
    rows.sort(key=lambda r: (r["overall_score"] is None, -(r["overall_score"] or 0), (r["name"] or "").lower()))
    st = await _period_state(period)
    return {"period": period, "period_state": st.get("state", "open"), "rows": rows,
            "can_finalize": has_permission(user, "performance.period.manage")}


@perf_r.get("/staff/{user_id}")
async def staff_performance(user_id: str, period: Optional[str] = None, user: dict = Depends(require_admin)):
    if not (has_permission(user, "performance.view_team") or (user["id"] == user_id and has_permission(user, "performance.view_own"))):
        raise HTTPException(status_code=403, detail={"code": "PERMISSION_DENIED", "message": "Tidak diizinkan"})
    target = await db.users.find_one({"id": user_id}, {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1, "admin_role_id": 1})
    if not target or target.get("role") == "super_admin":
        raise HTTPException(status_code=404, detail="Staf tidak ditemukan")
    period = period or current_period()
    cfg = await _config_for_period(period)
    sla = (await get_work_settings())["sla_days"]
    role_perms_map = await _role_perms_map()
    role_id = target.get("admin_role_id") or target.get("role")
    data = await compute_staff_performance(user_id, role_id, period, cfg, sla, role_perms_map)
    # Attendance indicators (shown separately, NOT part of the score).
    attendance = None
    if has_permission(user, "performance.view_team") or user["id"] == user_id:
        try:
            from .staff import evaluate, _get_config, STATUSES
            acfg = await _get_config()
            counts = {s: 0 for s in STATUSES}
            start_utc, end_utc = _period_bounds(period)
            start_d = datetime.fromisoformat(start_utc).astimezone(WIB).date()
            end_d = datetime.fromisoformat(end_utc).astimezone(WIB).date()
            today = _wib_now().date()
            d = start_d
            while d < end_d and d <= today:
                r = await evaluate(user_id, d.isoformat(), acfg)
                counts[r["status"]] = counts.get(r["status"], 0) + 1
                d += timedelta(days=1)
            attendance = counts
        except Exception:
            attendance = None
    st = await _period_state(period)
    return {"name": target.get("name") or target.get("email"), "period_state": st.get("state", "open"),
            "attendance": attendance, **data}


@perf_r.get("/periods")
async def list_periods(user: dict = Depends(require_admin)):
    _ensure(user, "performance.view_team")
    docs = await db.performance_periods.find({}, {"_id": 0, "config_snapshot": 0}).sort("period", -1).to_list(120)
    return {"periods": docs, "current": current_period()}


class PeriodActionIn(BaseModel):
    period: str
    action: str  # finalize | reopen


@perf_r.post("/periods/action")
async def period_action(body: PeriodActionIn, user: dict = Depends(require_admin)):
    _ensure(user, "performance.period.manage")
    if body.action not in ("finalize", "reopen"):
        raise HTTPException(status_code=400, detail="Aksi tidak dikenal")
    if body.action == "finalize":
        snapshot = await get_perf_config()
        await db.performance_periods.update_one(
            {"period": body.period},
            {"$set": {"period": body.period, "state": "finalized", "config_snapshot": snapshot,
                      "finalized_by": user["id"], "finalized_at": now_iso()}},
            upsert=True,
        )
        await log_activity(user["id"], "performance_period_finalize", "performance", body.period)
    else:
        await db.performance_periods.update_one(
            {"period": body.period},
            {"$set": {"state": "open", "reopened_by": user["id"], "reopened_at": now_iso()}},
            upsert=True,
        )
        await log_activity(user["id"], "performance_period_reopen", "performance", body.period)
    return {"ok": True, "period": body.period, "state": "finalized" if body.action == "finalize" else "open"}
