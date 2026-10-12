"""D4 benefit endpoints — label status view + admin bonus grants & monitor.

Monitor signals (each carries a plain-language reason so the admin sees WHY a
label is a bonus candidate):

  new_member    label created/claimed within the last 30 days — welcome gift
  milestone     total releases sits one below a multiple of 10 — approaching a
                milestone worth celebrating
  dormant       no release submitted for 60+ days but has 3+ lifetime releases —
                win-back candidate
  loyal         account older than 6 months with 10+ releases — loyalty reward
  quota_max     this month's free-service quota fully used — engaged heavy user
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import benefit_service as ben
from models import new_id, now_iso
from .deps import (
    db, require_admin, require_label, get_label_by_user,
    log_activity, notify_many, label_user_ids,
)
from .admin_permission_service import assert_admin_permission

benefit_label_r = APIRouter(prefix="/label/benefits", tags=["benefits"])
benefit_admin_r = APIRouter(prefix="/admin/benefits", tags=["benefits"])

SERVICE_LABELS = {"any": "Semua layanan gratis", "wami": "Registrasi WAMI"}


class GrantIn(BaseModel):
    label_id: str
    service: str = Field(min_length=1, max_length=80)
    quantity: int = Field(ge=1, le=100)
    days: int = Field(ge=1, le=365)
    note: str = Field(min_length=3, max_length=500)


def _days_since(iso: Optional[str]) -> Optional[int]:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return (datetime.now(timezone.utc) - dt).days


# ---------------- Label ----------------

@benefit_label_r.get("")
async def label_benefits(user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    scope = await ben.resolve_benefit_scope(user, label)
    return await ben.benefit_status(scope)


# ---------------- Admin: grants ----------------

@benefit_admin_r.get("/grants")
async def list_grants(active: bool = True, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "benefits.view")
    query: Dict[str, Any] = {}
    if active:
        query["expires_at"] = {"$gt": now_iso()}
    rows = await db.benefit_grants.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    for g in rows:
        g["remaining"] = max(0, int(g.get("quantity") or 0) - int(g.get("used") or 0))
    return {"items": rows}


@benefit_admin_r.post("/grant")
async def create_grant(body: GrantIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "benefits.manage")
    label = await db.labels.find_one({"id": body.label_id}, {"_id": 0})
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    scope = await ben.scope_for_label_id(body.label_id)
    if not scope:
        raise HTTPException(status_code=409, detail="Label belum terhubung ke akun pengguna")
    service = body.service.strip()
    if service not in ben.GRANTABLE_SERVICES:
        product = await db.payment_products.find_one({"id": service, "active": True}, {"_id": 0, "id": 1})
        if not product:
            raise HTTPException(status_code=400, detail="Layanan tidak dikenal")
    grant = {
        "id": new_id(), "scope_key": scope["key"],
        "label_id": label["id"], "label_name": label.get("label_name"),
        "service": service, "quantity": body.quantity, "used": 0,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=body.days)).isoformat(),
        "days": body.days, "note": body.note.strip(),
        "granted_by": user["id"], "revoked": False,
        "created_at": now_iso(), "updated_at": now_iso(),
    }
    await db.benefit_grants.insert_one(grant)
    grant.pop("_id", None)
    service_label = SERVICE_LABELS.get(service) or "Layanan tambahan"
    await notify_many(
        await label_user_ids(label["id"]), "benefit_granted",
        f"Bonus {body.quantity}× {service_label}!",
        f"Anda mendapat bonus {body.quantity}× {service_label} — berlaku {body.days} hari. Gunakan sebelum hangus!",
        "/label/wallet", {},
    )
    await log_activity(user["id"], "benefit_granted", "benefit", grant["id"],
                       after={"label_id": label["id"], "service": service,
                              "quantity": body.quantity, "days": body.days, "note": body.note.strip()})
    return grant


@benefit_admin_r.post("/grants/{grant_id}/revoke")
async def revoke_grant(grant_id: str, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "benefits.manage")
    res = await db.benefit_grants.update_one(
        {"id": grant_id, "revoked": {"$ne": True}},
        {"$set": {"revoked": True, "expires_at": now_iso(), "updated_at": now_iso(),
                  "revoked_by": user["id"]}},
    )
    if not getattr(res, "modified_count", 0):
        raise HTTPException(status_code=404, detail="Bonus tidak ditemukan")
    await log_activity(user["id"], "benefit_revoked", "benefit", grant_id)
    return {"ok": True}


# ---------------- Admin: monitor ----------------

async def _release_stats() -> Dict[str, Dict[str, Any]]:
    stats: Dict[str, Dict[str, Any]] = {}
    rows = await db.releases.find(
        {"imported_legacy": {"$ne": True}},
        {"_id": 0, "label_id": 1, "created_at": 1},
    ).to_list(200000)
    for row in rows:
        s = stats.setdefault(row["label_id"], {"count": 0, "last": None})
        s["count"] += 1
        if row.get("created_at") and (s["last"] is None or row["created_at"] > s["last"]):
            s["last"] = row["created_at"]
    return stats


@benefit_admin_r.get("/monitor")
async def bonus_monitor(user: dict = Depends(require_admin)):
    """Labels worth a discretionary bonus, each with clear recommendation signals."""
    assert_admin_permission(user, "benefits.view")
    labels = await db.labels.find(
        {"user_id": {"$exists": True, "$ne": None}},
        {"_id": 0, "id": 1, "label_name": 1, "user_id": 1, "created_at": 1,
         "claim_resolved_at": 1, "subscription_tier": 1, "subscription_status": 1,
         "subscription_expires_at": 1},
    ).sort("label_name", 1).to_list(1000)
    rel_stats = await _release_stats()
    cfg = await ben.benefit_config()
    window = ben.month_window()
    # account-scoped monthly usage (Multi Label children share the account quota)
    usage: Dict[str, int] = {}
    for coll_name, extra in (("wami_orders", {"is_free_vip": True}),
                             ("addon_orders", {"source": "subscription_free"})):
        rows = await getattr(db, coll_name).find(
            {"created_at": {"$gte": window["start"], "$lt": window["end"]},
             "grant_id": {"$exists": False}, **extra},
            {"_id": 0, "label_id": 1},
        ).to_list(200000)
        for row in rows:
            usage[row["label_id"]] = usage.get(row["label_id"], 0) + 1

    # Multi Label children share the account quota — aggregate usage by scope.
    by_user: Dict[str, List[str]] = {}
    for l in labels:
        by_user.setdefault(l["user_id"], []).append(l["id"])

    def scope_of(label_id: str) -> str:
        for l in labels:
            if l["id"] == label_id:
                ids = by_user.get(l["user_id"]) or [label_id]
                return f"acct:{l['user_id']}" if len(ids) > 1 else label_id
        return label_id

    scope_used: Dict[str, int] = {}
    for l in labels:
        key = scope_of(l["id"])
        scope_used[key] = scope_used.get(key, 0) + usage.get(l["id"], 0)

    from .entitlements import resolve_label_entitlements
    items: List[Dict[str, Any]] = []
    for label in labels:
        stats = rel_stats.get(label["id"], {"count": 0, "last": None})
        age = _days_since(label.get("claim_resolved_at") or label.get("created_at"))
        idle = _days_since(stats["last"])
        used = scope_used.get(scope_of(label["id"]), 0)
        package = resolve_label_entitlements(label)["package"]
        quota = int(cfg["monthly_quota"].get(package, 0))
        signals: List[Dict[str, str]] = []
        if age is not None and age <= 30:
            signals.append({"key": "new_member",
                            "text": f"Member baru — bergabung {age} hari lalu. Bonus sambutan memperkuat kesan pertama."})
        if stats["count"] and stats["count"] % 10 == 9:
            signals.append({"key": "milestone",
                            "text": f"Mendekati {stats['count'] + 1} rilisan — bonus di momen milestone terasa personal."})
        if idle is not None and idle >= 60 and stats["count"] >= 3:
            signals.append({"key": "dormant",
                            "text": f"Tidak ada rilisan {idle} hari (punya {stats['count']}) — bonus win-back bisa membangunkan."})
        if age is not None and age >= 180 and stats["count"] >= 10:
            signals.append({"key": "loyal",
                            "text": f"Label setia {age // 30} bulan dengan {stats['count']} rilisan — layak apresiasi."})
        if quota > 0 and used >= quota:
            signals.append({"key": "quota_max",
                            "text": f"Kuota gratis bulan ini habis ({used}/{quota}) — pengguna paling aktif bulan ini."})
        if signals:
            items.append({
                "label_id": label["id"], "label_name": label.get("label_name"),
                "package": package, "signals": signals,
                "stats": {"releases": stats["count"], "last_release_at": stats["last"],
                          "age_days": age, "quota_used": used, "quota": quota},
            })
    items.sort(key=lambda i: (-len(i["signals"]), i["label_name"] or ""))
    return {"items": items, "month": window["key"], "signal_keys": {
        "new_member": "Member baru", "milestone": "Mendekati milestone",
        "dormant": "Tidak aktif", "loyal": "Label setia", "quota_max": "Kuota habis",
    }}
