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


def _subscription_active(label: Dict[str, Any]) -> bool:
    if (label or {}).get("subscription_status") != "active":
        return False
    expires = (label or {}).get("subscription_expires_at")
    if not expires:
        return False
    try:
        return datetime.fromisoformat(str(expires).replace("Z", "+00:00")) > datetime.now(timezone.utc)
    except Exception:
        return False


def resolve_label_entitlements(label: Dict[str, Any]) -> Dict[str, Any]:
    """Derive the effective capability set for a label/account.

    The account authority for Multi Label lives on the primary label document
    (subscription_tier == "multi_label"). Child labels inherit at higher phases.
    """
    label = label or {}
    active = _subscription_active(label)
    tier = label.get("subscription_tier") if active else None
    is_annual = active and tier in _ANNUAL_TIERS
    is_vip = active and tier in _VIP_TIERS
    is_multi = active and tier == "multi_label"
    return {
        "package": tier if is_annual else "pay_per_release",
        "active": active,
        "unlimited_release": is_annual,
        "vip_benefits": is_vip,
        "free_wami": is_vip,
        "free_addons": is_vip,
        "multi_label": is_multi,
        "daily_release_limit": DAILY_RELEASE_LIMIT,
        "subscription_expires_at": label.get("subscription_expires_at"),
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
