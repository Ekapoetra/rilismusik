"""Central account/label entitlement resolver — single source of truth for benefits.

Never scatter `subscription_tier == "annual_vip"` checks across routes. Resolve
capabilities through this module so Multi Label (and any future package) inherits
VIP-equivalent benefits consistently.
"""
from datetime import datetime, timezone
from typing import Any, Dict

DAILY_RELEASE_LIMIT = 7

# Tiers that carry an annual (unlimited-release) subscription entitlement.
_ANNUAL_TIERS = {"annual_normal", "annual_vip", "multi_label"}
# Tiers that carry VIP-equivalent benefits (free WAMI, free add-ons).
_VIP_TIERS = {"annual_vip", "multi_label"}


def _parse_time(value: Any):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def effective_subscription(label: Dict[str, Any], now: datetime = None) -> Dict[str, Any]:
    """Stored subscription, or a scheduled paid change once it has started.

    Downgrades and renewals bought while a package is still running are stored as
    `scheduled_plan_change` and take over at the current end (V13 Packages122).
    The hourly expiry job materializes them; this keeps access correct meanwhile.
    """
    label = label or {}
    now = now or datetime.now(timezone.utc)
    current = {"status": label.get("subscription_status"), "tier": label.get("subscription_tier"),
               "expires_at": label.get("subscription_expires_at")}
    expires = _parse_time(current["expires_at"])
    if current["status"] == "active" and expires and expires > now:
        return current
    change = label.get("scheduled_plan_change") or {}
    starts, ends = _parse_time(change.get("starts_at")), _parse_time(change.get("ends_at"))
    if change.get("tier") in _ANNUAL_TIERS and starts and ends and starts <= now < ends:
        return {"status": "active", "tier": change["tier"], "expires_at": change["ends_at"]}
    return current


def _subscription_active(label: Dict[str, Any]) -> bool:
    current = effective_subscription(label)
    if current["status"] != "active":
        return False
    expires = _parse_time(current["expires_at"])
    return bool(expires and expires > datetime.now(timezone.utc))


PLAN_RANK = {"pay_per_release": 0, "annual_normal": 1, "annual_vip": 2, "multi_label": 3}


def pending_plan_change(label: Dict[str, Any]) -> Dict[str, Any]:
    """The scheduled change that has not started yet, if any."""
    change = (label or {}).get("scheduled_plan_change") or {}
    starts = _parse_time(change.get("starts_at"))
    return change if starts and starts > datetime.now(timezone.utc) else None


# V13 package names over the stored packages (renamed only; benefits unchanged).
PLAN_NAMES = {"pay_per_release": "Basic", "annual_normal": "Studio", "annual_vip": "Pro", "multi_label": "Business"}


def resolve_label_entitlements(label: Dict[str, Any]) -> Dict[str, Any]:
    """Derive the effective capability set for a label/account.

    The account authority for Multi Label lives on the primary label document
    (subscription_tier == "multi_label"). Child labels inherit at higher phases.
    """
    label = label or {}
    active = _subscription_active(label)
    current = effective_subscription(label)
    tier = current["tier"] if active else None
    is_annual = active and tier in _ANNUAL_TIERS
    is_vip = active and tier in _VIP_TIERS
    is_multi = active and tier == "multi_label"
    return {
        "package": tier if is_annual else "pay_per_release",
        "plan_name": PLAN_NAMES.get(tier if is_annual else "pay_per_release", "Basic"),
        "active": active,
        "unlimited_release": is_annual,
        "vip_benefits": is_vip,
        "free_wami": is_vip,
        "free_addons": is_vip,
        "multi_label": is_multi,
        "daily_release_limit": DAILY_RELEASE_LIMIT,
        "subscription_expires_at": current["expires_at"],
        "scheduled_change": pending_plan_change(label),
    }


def has_unlimited_release(label: Dict[str, Any]) -> bool:
    return resolve_label_entitlements(label)["unlimited_release"]


def has_vip_benefits(label: Dict[str, Any]) -> bool:
    return resolve_label_entitlements(label)["vip_benefits"]


def has_free_wami(label: Dict[str, Any]) -> bool:
    return resolve_label_entitlements(label)["free_wami"]


def has_free_addons(label: Dict[str, Any]) -> bool:
    return resolve_label_entitlements(label)["free_addons"]


def has_multi_label(label: Dict[str, Any]) -> bool:
    return resolve_label_entitlements(label)["multi_label"]
