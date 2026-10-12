"""D4 — monthly benefit quota + discretionary bonus grants (benefit_grants).

Package members no longer get unlimited free WAMI / add-on services: every
account receives `monthly_quota[tier]` free services per Asia/Jakarta month,
counted from real orders (Option B — no counters that can drift). Super Admin
can additionally grant expiring bonuses to a specific label/account as a
reward or win-back incentive.

Funding order for a benefit-eligible action:
  1. an active grant matching the service (nearest expiry first)
  2. the monthly package quota
  3. a paid invoice (member is never blocked)

"service" values: "wami" for WAMI registration, or a payment_products id for
add-on services. Grants may target "any" service.
"""
from datetime import datetime, time, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from models import now_iso
from routes.deps import db, logger

WIB = ZoneInfo("Asia/Jakarta")

BENEFIT_DEFAULTS = {
    "monthly_quota": {
        "pay_per_release": 0,
        "annual_normal": 1,
        "annual_vip": 2,
        "multi_label": 3,
    },
}
BENEFIT_TIERS = set(BENEFIT_DEFAULTS["monthly_quota"])
GRANTABLE_SERVICES = {"any", "wami"}
# Orders in these states no longer consume the monthly quota — a rejected or
# cancelled request returns the benefit to the member.
TERMINAL_EXCLUDED = ("refunded", "cancelled", "rejected")


def month_window(now: Optional[datetime] = None) -> Dict[str, str]:
    local = (now or datetime.now(timezone.utc)).astimezone(WIB)
    start = datetime.combine(local.date().replace(day=1), time.min, WIB).astimezone(timezone.utc)
    nxt = local.replace(year=local.year + 1, month=1, day=1) if local.month == 12 \
        else local.replace(month=local.month + 1, day=1)
    end = datetime.combine(nxt.date(), time.min, WIB).astimezone(timezone.utc)
    return {"key": local.strftime("%Y-%m"), "start": start.isoformat(), "end": end.isoformat()}


async def benefit_config() -> Dict[str, Any]:
    doc = await db.system_settings.find_one({"area": "benefits"}, {"_id": 0, "published": 1})
    stored = (doc or {}).get("published") or {}
    merged = dict(BENEFIT_DEFAULTS)
    merged["monthly_quota"] = {**BENEFIT_DEFAULTS["monthly_quota"], **(stored.get("monthly_quota") or {})}
    return merged


async def resolve_benefit_scope(user: dict, label: Optional[dict] = None) -> Dict[str, Any]:
    """Benefits are account-scoped: Multi Label shares quota across child labels."""
    from routes.deps import get_labels_for_user, _account_authority
    from routes.entitlements import resolve_label_entitlements
    labels = await get_labels_for_user(user)
    authority = _account_authority(labels, user) if labels else (label or {})
    ent = resolve_label_entitlements(authority)
    label_ids = [l["id"] for l in labels] or ([label["id"]] if label else [])
    key = f"acct:{user['id']}" if len(label_ids) > 1 else (label_ids[0] if label_ids else f"acct:{user['id']}")
    return {
        "key": key,
        "label_ids": label_ids,
        "package": ent.get("package") or "pay_per_release",
        "vip_benefits": bool(ent.get("vip_benefits")),
    }


async def scope_for_label_id(label_id: str) -> Optional[Dict[str, Any]]:
    """Admin-side scope resolution for grant targeting: child label of a Multi
    Label account resolves to the whole account scope."""
    label = await db.labels.find_one({"id": label_id}, {"_id": 0})
    if not label or not label.get("user_id"):
        return None
    user = {"id": label["user_id"]}
    return await resolve_benefit_scope(user, label)


async def monthly_usage(scope: Dict[str, Any], now: Optional[datetime] = None) -> int:
    """Free-benefit orders this WIB month. Grant-funded orders carry grant_id and
    are excluded — they draw from their own budget."""
    window = month_window(now)
    base = {"label_id": {"$in": scope["label_ids"]},
            "created_at": {"$gte": window["start"], "$lt": window["end"]},
            "grant_id": {"$exists": False},
            "status": {"$nin": TERMINAL_EXCLUDED}}
    wami = await db.wami_orders.count_documents({**base, "is_free_vip": True})
    addons = await db.addon_orders.count_documents({**base, "source": "subscription_free"})
    return wami + addons


async def active_grants(scope: Dict[str, Any], service: Optional[str] = None,
                        now: Optional[datetime] = None) -> List[dict]:
    stamp = (now or datetime.now(timezone.utc)).isoformat()
    rows = await db.benefit_grants.find(
        {"scope_key": scope["key"], "expires_at": {"$gt": stamp}},
        {"_id": 0},
    ).sort("expires_at", 1).to_list(200)
    rows = [g for g in rows if int(g.get("used") or 0) < int(g.get("quantity") or 0)]
    if service:
        rows = [g for g in rows if g.get("service") in ("any", service)]
    return rows


async def consume_benefit(scope: Dict[str, Any], service: str,
                          now: Optional[datetime] = None,
                          reserved: int = 0) -> Dict[str, Any]:
    """Decide funding for one benefit-eligible action. The caller records the
    returned funding on the order document (grant_id / benefit_source).

    `reserved` counts in-flight quota consumptions within the same batch —
    orders don't exist yet while consume_benefits loops, so without it every
    iteration would see the same persisted usage and exceed the quota.

    Grants are honoured for ANY account (Super Admin may gift a Basic member);
    the monthly quota applies to whichever package the account holds."""
    for g in await active_grants(scope, service, now):
        res = await db.benefit_grants.update_one(
            {"id": g["id"], "used": {"$lt": int(g.get("quantity") or 0)}},
            {"$inc": {"used": 1}, "$set": {"updated_at": now_iso()}},
        )
        if getattr(res, "modified_count", 0):
            return {"kind": "grant", "grant_id": g["id"], "grant": g}
    cfg = await benefit_config()
    quota = int(cfg["monthly_quota"].get(scope["package"], 0))
    used = await monthly_usage(scope, now)
    if used + reserved < quota:
        return {"kind": "quota", "grant_id": None, "used": used + reserved, "quota": quota}
    return {"kind": "paid", "grant_id": None, "used": used + reserved, "quota": quota, "exhausted": True}


async def consume_benefits(scope: Dict[str, Any], service_keys: List[str],
                           now: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Fund N benefit actions (e.g. add-ons selected at submit). All-or-nothing:
    any shortfall rolls back grant increments already taken."""
    results: List[Dict[str, Any]] = []
    reserved = 0
    for sk in service_keys:
        r = await consume_benefit(scope, sk, now, reserved=reserved)
        if r["kind"] == "paid":
            await rollback_funding(results)
            raise HTTPException(
                status_code=400,
                detail="Kuota layanan gratis bulan ini habis — hapus layanan tambahan atau beli terpisah.",
            )
        if r["kind"] == "quota":
            reserved += 1
        results.append(r)
    return results


async def rollback_funding(funding: List[Dict[str, Any]]) -> None:
    """Return grant increments when the surrounding operation fails (e.g. release
    submit rejected after benefits were pre-consumed)."""
    for r in funding or []:
        gid = r.get("grant_id")
        if not gid:
            continue
        try:
            await db.benefit_grants.update_one(
                {"id": gid, "used": {"$gt": 0}},
                {"$inc": {"used": -1}, "$set": {"updated_at": now_iso()}},
            )
        except Exception:
            logger.exception("Benefit grant rollback failed for %s", gid)


async def benefit_status(scope: Dict[str, Any], now: Optional[datetime] = None) -> Dict[str, Any]:
    cfg = await benefit_config()
    quota = int(cfg["monthly_quota"].get(scope["package"], 0))
    used = await monthly_usage(scope, now) if scope["label_ids"] else 0
    grants = await active_grants(scope, now=now)
    window = month_window(now)
    return {
        "package": scope["package"],
        "vip_benefits": scope.get("vip_benefits", False),
        "has_benefits": bool(quota > 0 or grants),
        "quota": quota, "used": used,
        "remaining": max(0, quota - used),
        "month": window["key"], "resets_at": window["end"],
        "grants": [{
            "id": g["id"], "service": g.get("service"),
            "quantity": g.get("quantity"), "used": g.get("used") or 0,
            "expires_at": g.get("expires_at"),
            "label_id": g.get("label_id"),
        } for g in grants],
    }
