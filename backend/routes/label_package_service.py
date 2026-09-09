"""Granular manual package changes; no payment/invoice or royalty mutations."""
from datetime import date, datetime, time, timezone
from typing import Literal, Optional
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from models import new_id, now_iso
from .admin_permission_service import assert_admin_permission
from .deps import db, log_activity, logger

PACKAGE_FIELDS = ("payment_type", "subscription_tier", "subscription_status", "subscription_expires_at")


class LabelPackageUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    package: Literal["pay_per_release", "annual_normal", "annual_vip"]
    expires_on: Optional[date] = None
    reason: str = Field(min_length=3, max_length=1000)
    expected_revision: int = Field(ge=0)
    confirm: Literal[True]


class LabelPackageResult(BaseModel):
    ok: bool = True
    label_id: str
    payment_type: str
    subscription_tier: Optional[str]
    subscription_status: str
    subscription_expires_at: Optional[str]
    package_revision: int
    audit_id: str


async def change_label_package(label_id: str, body: LabelPackageUpdate, user: dict):
    assert_admin_permission(user, "labels.package")
    label = await db.labels.find_one({"id": label_id}, {"_id": 0, "package_change_history": 0})
    if not label:
        raise HTTPException(404, "Label tidak ditemukan")
    if body.package == "pay_per_release":
        if body.expires_on is not None:
            raise HTTPException(422, "Pay Per Release tidak menggunakan masa berlaku.")
        update = dict(payment_type="pay_per_release", subscription_tier=None, subscription_status="inactive", subscription_expires_at=None)
    else:
        if not body.expires_on:
            raise HTTPException(422, "Isi tanggal masa berlaku untuk paket tahunan.")
        expires = datetime.combine(body.expires_on, time(23, 59, 59), ZoneInfo("Asia/Jakarta")).astimezone(timezone.utc)
        update = dict(payment_type="annual_subscription", subscription_tier=body.package,
                      subscription_status="active" if expires > datetime.now(timezone.utc) else "expired",
                      subscription_expires_at=expires.isoformat())
    revision = int(label.get("package_revision") or 0)
    if revision != body.expected_revision:
        raise HTTPException(409, "Paket telah diubah admin lain. Muat ulang label sebelum menyimpan.")
    before = {key: label.get(key) for key in PACKAGE_FIELDS}
    audit = {"id": new_id(), "actor_id": user["id"], "actor_role": user.get("assigned_role", user.get("role")),
             "created_at": now_iso(), "reason": body.reason, "before": before, "after": update.copy()}
    # Store the immutable audit entry atomically with the package, including on standalone MongoDB.
    guard = {"id": label_id, **before}
    guard["package_revision"] = revision if "package_revision" in label else {"$exists": False}
    result = await db.labels.update_one(guard, {"$set": {**update, "updated_at": audit["created_at"]},
                                              "$inc": {"package_revision": 1}, "$push": {"package_change_history": audit}})
    if not result.matched_count:
        raise HTTPException(409, "Paket telah berubah. Muat ulang label sebelum menyimpan.")
    try:
        await log_activity(user["id"], "change_label_package", "label", label_id, before=before,
                           after={**update, "reason": body.reason, "audit_id": audit["id"], "package_revision": revision + 1})
    except Exception:
        logger.exception("Package activity-log mirror failed; durable label audit exists: %s", audit["id"])
    return LabelPackageResult(label_id=label_id, **update, package_revision=revision + 1, audit_id=audit["id"])