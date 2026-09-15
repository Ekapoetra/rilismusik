"""PRD-02 Work Responsibility & Tracking — projection/reconciliation layer.

Work is computed from real business state + activity_logs, WITHOUT modifying business
endpoints. A Work instance is OPEN while its source entity sits in the mapped open
condition and becomes COMPLETED (idempotently) when the entity leaves that condition;
Completed By/At are derived from trusted backend sources (activity_logs / entity fields).
"""
import time
from datetime import datetime, timezone, date, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from models import new_id, now_iso
from .deps import db, log_activity, require_admin
from .admin_permission_service import assert_admin_permission, has_permission


work_r = APIRouter(prefix="/admin/work", tags=["work"])

# Discovered Work Types (grounded in the codebase audit). priority: critical|high|normal|low
WORK_TYPES: List[Dict[str, Any]] = [
    {"key": "release_review", "label_id": "Proses Rilisan", "label_en": "Release Processing", "icon": "Disc3",
     "link": "/admin/releases", "permission": "releases.review", "priority": "normal", "sla_days_default": 2},
    {"key": "release_go_live", "label_id": "Finalisasi Tayang (UPC/ISRC)", "label_en": "Finalize Go-Live", "icon": "Rocket",
     "link": "/admin/releases?status=delivered", "permission": "releases.review", "priority": "high", "sla_days_default": 1},
    {"key": "withdraw_verification", "label_id": "Verifikasi Penarikan", "label_en": "Withdrawal Verification", "icon": "Banknote",
     "link": "/admin/withdraw", "permission": "withdraw.manage", "priority": "high", "sla_days_default": 1},
    {"key": "kyc_review", "label_id": "Review Verifikasi Akun", "label_en": "KYC Review", "icon": "ShieldCheck",
     "link": "/admin/kyc", "permission": "kyc.view", "priority": "normal", "sla_days_default": 2},
    {"key": "support_ticket", "label_id": "Tiket Bantuan", "label_en": "Support Tickets", "icon": "MessageSquare",
     "link": "/admin/tickets", "permission": "support.view", "priority": "normal", "sla_days_default": 2},
    {"key": "legacy_claim", "label_id": "Klaim Akun Lama", "label_en": "Legacy Account Claims", "icon": "DatabaseZap",
     "link": "/admin/migrate?tab=claims", "permission": "migration.view", "priority": "normal", "sla_days_default": 3},
    {"key": "addon_processing", "label_id": "Proses Add-on", "label_en": "Add-on Processing", "icon": "Sparkles",
     "link": "/admin/addon-orders", "permission": "addon.manage", "priority": "normal", "sla_days_default": 3},
    {"key": "sensitive_approval", "label_id": "Persetujuan Aksi Sensitif", "label_en": "Sensitive Approvals", "icon": "ShieldCheck",
     "link": "/admin/rate-changes", "permission": "labels.rate.approve", "priority": "high", "sla_days_default": 2},
    {"key": "bank_verification", "label_id": "Verifikasi Rekening", "label_en": "Bank Account Verification", "icon": "Landmark",
     "link": "/admin/bank-verifications", "permission": "labels.manage", "priority": "high", "sla_days_default": 2},
]
WORK_TYPE_MAP = {w["key"]: w for w in WORK_TYPES}

DEFAULT_RESPONSIBILITY = {
    "release_review": ["admin_release"], "release_go_live": ["admin_release"], "addon_processing": ["admin_release"],
    "withdraw_verification": ["admin_finance"],
    "kyc_review": ["admin_support"], "support_ticket": ["admin_support"],
    "legacy_claim": ["admin_support"], "sensitive_approval": ["super_admin"],
    "bank_verification": [],  # seeded dynamically to roles holding `labels.manage`
}
DEFAULT_SLA_DAYS = {w["key"]: w["sla_days_default"] for w in WORK_TYPES}

_MODULE_MAP = {"releases": "release", "withdraw_requests": "withdraw", "kyc_documents": "kyc",
               "support_tickets": "support", "payments": "payment", "wami_orders": "wami", "service_orders": "service",
               "addon_orders": "addon", "bank_account_change_requests": "bank_account"}
_RECON = {"at": 0.0}


# ---------- config (stored in admin_ui_settings, lazily seeded) ----------
async def _roles_with_permission(perm: str) -> List[str]:
    """Admin role ids (excluding super_admin, who sees everything) whose permission
    set includes `perm`. Used to auto-assign responsibility to the right team."""
    out: List[str] = []
    async for r in db.admin_roles.find({"permissions": perm}, {"_id": 0, "id": 1}):
        if r["id"] != "super_admin":
            out.append(r["id"])
    return out


async def get_responsibility() -> Dict[str, List[str]]:
    doc = await db.admin_ui_settings.find_one({"key": "work_responsibility"}, {"_id": 0, "mapping": 1})
    mapping = (doc or {}).get("mapping") or {}
    changed = False
    for k, v in DEFAULT_RESPONSIBILITY.items():
        if k not in mapping:
            if k == "bank_verification":
                mapping[k] = await _roles_with_permission("labels.manage")
            else:
                mapping[k] = list(v)
            changed = True
    if not doc or changed:
        await db.admin_ui_settings.update_one({"key": "work_responsibility"}, {"$set": {"mapping": mapping}}, upsert=True)
    return {k: mapping.get(k, []) for k in DEFAULT_RESPONSIBILITY}


async def get_work_settings() -> Dict[str, Any]:
    doc = await db.admin_ui_settings.find_one({"key": "work_settings"}, {"_id": 0, "sla_days": 1})
    sla = (doc or {}).get("sla_days") or {}
    changed = False
    for k, v in DEFAULT_SLA_DAYS.items():
        if k not in sla:
            sla[k] = v; changed = True
    if not doc or changed:
        await db.admin_ui_settings.update_one({"key": "work_settings"}, {"$set": {"sla_days": sla}}, upsert=True)
    return {"sla_days": sla}


# ---------- source discovery (OPEN conditions) ----------
async def _sources(work_type: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    def add(source, doc, opened_field, ref, label_id=None, label_name=None):
        out.append({"source": source, "entity_id": doc["id"],
                    "opened_at": doc.get(opened_field) or doc.get("created_at") or now_iso(),
                    "ref": ref, "label_id": label_id, "label_name": label_name})

    if work_type == "release_review":
        async for d in db.releases.find(
            {"status": {"$in": ["submitted", "under_review", "paid", "approved"]}},
            {"_id": 0, "id": 1, "submitted_at": 1, "created_at": 1, "release_title": 1, "title": 1, "label_id": 1, "label_name": 1},
        ):
            add("releases", d, "submitted_at", d.get("release_title") or d.get("title") or "Rilisan", d.get("label_id"), d.get("label_name"))
    elif work_type == "release_go_live":
        today_wib = (datetime.now(timezone.utc) + timedelta(hours=7)).date().isoformat()
        async for d in db.releases.find(
            {"status": "delivered", "release_date": {"$ne": None, "$lte": today_wib}},
            {"_id": 0, "id": 1, "delivered_to_believe_at": 1, "created_at": 1, "release_title": 1, "release_date": 1, "label_id": 1, "label_name": 1},
        ):
            add("releases", d, "delivered_to_believe_at", d.get("release_title") or "Rilisan", d.get("label_id"), d.get("label_name"))
    elif work_type == "withdraw_verification":
        async for d in db.withdraw_requests.find({"status": "requested", "legacy_import": {"$ne": True}}, {"_id": 0, "id": 1, "created_at": 1, "label_id": 1, "label_name": 1, "amount_idr": 1}):
            add("withdraw_requests", d, "created_at", f"Rp {int(d.get('amount_idr') or 0):,}".replace(",", "."), d.get("label_id"), d.get("label_name"))
    elif work_type == "kyc_review":
        async for d in db.kyc_documents.find({"status": "pending_review", "is_current": True}, {"_id": 0, "id": 1, "uploaded_at": 1, "created_at": 1, "label_id": 1, "label_name": 1}):
            add("kyc_documents", d, "uploaded_at", "Verifikasi identitas", d.get("label_id"), d.get("label_name"))
    elif work_type == "support_ticket":
        async for d in db.support_tickets.find({"status": {"$nin": ["done", "rejected", "cancelled"]}}, {"_id": 0, "id": 1, "created_at": 1, "subject": 1, "category": 1, "label_id": 1}):
            add("support_tickets", d, "created_at", d.get("subject") or d.get("category") or "Tiket", d.get("label_id"))
    elif work_type == "legacy_claim":
        async for d in db.users.find({"role": "label", "claim_status": "pending_link"}, {"_id": 0, "id": 1, "claim_requested_at": 1, "created_at": 1, "email": 1, "name": 1}):
            add("users", d, "claim_requested_at", d.get("email") or d.get("name") or "Klaim", None, d.get("name"))
    elif work_type == "addon_processing":
        async for d in db.wami_orders.find({"status": {"$in": ["pending", "in_progress"]}}, {"_id": 0, "id": 1, "created_at": 1, "label_id": 1, "label_name": 1}):
            add("wami_orders", d, "created_at", "WAMI", d.get("label_id"), d.get("label_name"))
        async for d in db.addon_orders.find({"status": {"$in": ["pending", "in_progress"]}}, {"_id": 0, "id": 1, "created_at": 1, "label_id": 1, "label_name": 1, "product_name": 1}):
            add("addon_orders", d, "created_at", d.get("product_name") or "Add-on", d.get("label_id"), d.get("label_name"))
        async for d in db.service_orders.find({"status": {"$in": ["paid", "in_progress"]}}, {"_id": 0, "id": 1, "created_at": 1, "label_id": 1, "label_name": 1, "service_name": 1}):
            add("service_orders", d, "created_at", d.get("service_name") or "Layanan", d.get("label_id"), d.get("label_name"))
    elif work_type == "sensitive_approval":
        async for d in db.label_rate_change_requests.find({"status": "pending"}, {"_id": 0, "id": 1, "requested_at": 1, "label_id": 1, "label_name": 1, "current_value": 1, "proposed_value": 1}):
            add("label_rate_change_requests", d, "requested_at", f"Rate {d.get('current_value')}%→{d.get('proposed_value')}%", d.get("label_id"), d.get("label_name"))
        async for d in db.sensitive_action_requests.find({"status": "pending"}, {"_id": 0, "id": 1, "requested_at": 1, "label_id": 1, "label_name": 1, "summary": 1}):
            add("sensitive_action_requests", d, "requested_at", d.get("summary") or "Aksi sensitif", d.get("label_id"), d.get("label_name"))
    elif work_type == "bank_verification":
        async for d in db.bank_account_change_requests.find({"status": "pending_admin_approval"}, {"_id": 0, "id": 1, "created_at": 1, "label_id": 1, "label_name": 1, "bank_name": 1, "account_number": 1}):
            ref = f"{d.get('bank_name') or 'Rekening'} · {d.get('account_number') or ''}".strip(" ·")
            add("bank_account_change_requests", d, "created_at", ref or "Verifikasi rekening", d.get("label_id"), d.get("label_name"))
    return out


# ---------- completion attribution (trusted sources) ----------
async def _resolve_completion(source: str, entity_id: str):
    if source in ("label_rate_change_requests", "sensitive_action_requests"):
        doc = await db[source].find_one({"id": entity_id}, {"_id": 0, "decided_by": 1, "decided_at": 1})
        if doc and doc.get("decided_by"):
            return doc["decided_by"], doc.get("decided_at"), "decision"
    elif source == "users":  # legacy claim resolved on the linked label
        lab = await db.labels.find_one({"user_id": entity_id}, {"_id": 0, "claim_resolved_by": 1, "claim_resolved_at": 1})
        if lab and lab.get("claim_resolved_by"):
            return lab["claim_resolved_by"], lab.get("claim_resolved_at"), "claim_link"
    mod = _MODULE_MAP.get(source)
    if mod:
        log = await db.activity_logs.find_one({"module": mod, "reference_id": entity_id}, {"_id": 0, "user_id": 1, "created_at": 1, "action": 1}, sort=[("created_at", -1)])
        if log:
            return log.get("user_id"), log.get("created_at"), log.get("action")
    return None, now_iso(), "auto_closed"


async def _actor_info(actor_id: Optional[str], cache: Dict[str, Any]) -> Dict[str, Any]:
    if not actor_id:
        return {"name": "Sistem", "super": False}
    if actor_id in cache:
        return cache[actor_id]
    u = await db.users.find_one({"id": actor_id}, {"_id": 0, "name": 1, "email": 1, "role": 1})
    info = {"name": (u or {}).get("name") or (u or {}).get("email") or "—", "super": (u or {}).get("role") == "super_admin"}
    cache[actor_id] = info
    return info


# ---------- reconciliation (idempotent) ----------
async def reconcile_work(force: bool = False) -> None:
    if not force and (time.time() - _RECON["at"]) < 8:
        return
    _RECON["at"] = time.time()
    cache: Dict[str, Any] = {}
    for wt in WORK_TYPES:
        key = wt["key"]
        current = await _sources(key)
        current_keys = set()
        for it in current:
            dk = f"{key}:{it['source']}:{it['entity_id']}"
            current_keys.add(dk)
            await db.work_items.update_one(
                {"dedupe_key": dk, "status": "open"},
                {"$setOnInsert": {
                    "id": new_id(), "dedupe_key": dk, "work_type": key, "source": it["source"],
                    "entity_id": it["entity_id"], "entity_ref": it.get("ref"),
                    "label_id": it.get("label_id"), "label_name": it.get("label_name"),
                    "status": "open", "opened_at": it["opened_at"], "created_at": now_iso(),
                }},
                upsert=True,
            )
        async for wi in db.work_items.find({"work_type": key, "status": "open"}, {"_id": 0}):
            if wi["dedupe_key"] in current_keys:
                continue
            actor, at, action = await _resolve_completion(wi["source"], wi["entity_id"])
            info = await _actor_info(actor, cache)
            await db.work_items.update_one(
                {"id": wi["id"], "status": "open"},
                {"$set": {"status": "completed", "completed_by": actor, "completed_by_name": info["name"],
                          "completed_by_super": info["super"], "completed_at": at or now_iso(),
                          "completion_action": action, "updated_at": now_iso()}},
            )


# ---------- aging ----------
def _age_days(opened_at: Optional[str]) -> int:
    if not opened_at:
        return 0
    try:
        d = datetime.fromisoformat(opened_at.replace("Z", "+00:00"))
    except Exception:
        return 0
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return max(0, (datetime.now(timezone.utc) - d).days)


def _is_overdue(opened_at: Optional[str], sla_days: int) -> bool:
    if not opened_at:
        return False
    try:
        opened = datetime.fromisoformat(opened_at.replace("Z", "+00:00")).date()
    except Exception:
        return False
    due = opened + timedelta(days=int(sla_days))
    return date.today() > due  # overdue only AFTER the expected completion day has passed


async def _role_names() -> Dict[str, str]:
    names = {}
    async for r in db.admin_roles.find({}, {"_id": 0, "id": 1, "name": 1}):
        names[r["id"]] = r["name"]
    return names


# ---------- endpoints ----------
@work_r.get("/queue")
async def work_queue(scope: str = "my", user: dict = Depends(require_admin)):
    assert_admin_permission(user, "work.view")
    await reconcile_work()
    mapping = await get_responsibility()
    settings = await get_work_settings()
    role_names = await _role_names()
    user_role = user.get("admin_role_id")
    is_super = user.get("role") == "super_admin"
    is_manage = has_permission(user, "work.manage")
    if scope == "team" and not (is_manage or is_super):
        raise HTTPException(status_code=403, detail="Hanya pengelola yang dapat melihat Team Monitor")
    rank = {"critical": 0, "high": 1, "normal": 2, "low": 3}
    items = []
    for wt in WORK_TYPES:
        key = wt["key"]
        roles = mapping.get(key, [])
        is_gap = len(roles) == 0
        responsible = user_role in roles
        if scope == "my":
            show = (responsible or is_gap) if is_super else responsible
        else:
            show = True
        if not show:
            continue
        opens = await db.work_items.find({"work_type": key, "status": "open"}, {"_id": 0, "opened_at": 1}).to_list(20000)
        sla = int(settings["sla_days"].get(key, wt["sla_days_default"]))
        overdue = sum(1 for o in opens if _is_overdue(o.get("opened_at"), sla))
        oldest = min((o.get("opened_at") for o in opens if o.get("opened_at")), default=None)
        items.append({
            "work_type": key, "label_id": wt["label_id"], "label_en": wt["label_en"], "icon": wt["icon"],
            "link": wt["link"], "permission": wt["permission"], "priority": wt["priority"],
            "open_count": len(opens), "overdue_count": overdue, "oldest_open_at": oldest,
            "oldest_age_days": _age_days(oldest) if oldest else 0, "sla_days": sla,
            "is_gap": is_gap, "responsible_roles": [role_names.get(r, r) for r in roles],
            "can_act": has_permission(user, wt["permission"]),
        })
    items.sort(key=lambda d: (0 if d["overdue_count"] else 1, rank.get(d["priority"], 9), d.get("oldest_open_at") or "9999"))
    gaps = [i for i in items if i["is_gap"]] if (is_super or is_manage) else []
    return {"scope": scope, "items": items, "gaps": gaps, "is_manager": bool(is_manage or is_super)}


@work_r.get("/history")
async def work_history(work_type: Optional[str] = None, limit: int = 100, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "work.view")
    await reconcile_work()
    query: Dict[str, Any] = {"status": "completed"}
    if work_type:
        query["work_type"] = work_type
    rows = await db.work_items.find(query, {"_id": 0}).sort("completed_at", -1).to_list(min(int(limit), 500))
    for r in rows:
        wt = WORK_TYPE_MAP.get(r["work_type"], {})
        r["work_type_label_id"] = wt.get("label_id", r["work_type"])
        r["work_type_label_en"] = wt.get("label_en", r["work_type"])
    return {"items": rows}


@work_r.get("/responsibilities")
async def get_responsibilities(user: dict = Depends(require_admin)):
    assert_admin_permission(user, "work.view")
    mapping = await get_responsibility()
    settings = await get_work_settings()
    role_names = await _role_names()
    roles = [{"id": rid, "name": name} for rid, name in role_names.items()]
    types = [{"key": w["key"], "label_id": w["label_id"], "label_en": w["label_en"], "permission": w["permission"],
              "priority": w["priority"], "sla_days": int(settings["sla_days"].get(w["key"], w["sla_days_default"])),
              "responsible_role_ids": mapping.get(w["key"], []), "is_gap": len(mapping.get(w["key"], [])) == 0}
             for w in WORK_TYPES]
    return {"work_types": types, "roles": roles}


class ResponsibilityUpdateIn(BaseModel):
    work_type: str
    role_ids: List[str] = Field(default_factory=list, max_length=50)


@work_r.put("/responsibilities")
async def update_responsibility(body: ResponsibilityUpdateIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "work.manage")
    if body.work_type not in WORK_TYPE_MAP:
        raise HTTPException(status_code=404, detail="Work Type tidak ditemukan")
    valid_role_ids = set(await db.admin_roles.distinct("id"))
    role_ids = [r for r in dict.fromkeys(body.role_ids) if r in valid_role_ids]
    mapping = await get_responsibility()
    before = mapping.get(body.work_type, [])
    mapping[body.work_type] = role_ids
    await db.admin_ui_settings.update_one({"key": "work_responsibility"}, {"$set": {"mapping": mapping}}, upsert=True)
    await log_activity(user["id"], "work_responsibility_update", "work", body.work_type, before={"role_ids": before}, after={"role_ids": role_ids})
    return {"work_type": body.work_type, "role_ids": role_ids}


class SlaUpdateIn(BaseModel):
    work_type: str
    sla_days: int = Field(ge=0, le=90)


@work_r.put("/settings/sla")
async def update_sla(body: SlaUpdateIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "work.manage")
    if body.work_type not in WORK_TYPE_MAP:
        raise HTTPException(status_code=404, detail="Work Type tidak ditemukan")
    settings = await get_work_settings()
    before = settings["sla_days"].get(body.work_type)
    settings["sla_days"][body.work_type] = int(body.sla_days)
    await db.admin_ui_settings.update_one({"key": "work_settings"}, {"$set": {"sla_days": settings["sla_days"]}}, upsert=True)
    await log_activity(user["id"], "work_sla_update", "work", body.work_type, before={"sla_days": before}, after={"sla_days": int(body.sla_days)})
    return {"work_type": body.work_type, "sla_days": int(body.sla_days)}
