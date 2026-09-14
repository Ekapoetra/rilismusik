"""Generic Sensitive Action request→approval workflow for Blacklist and Package changes.

Mirrors the Rate/Fee pattern: a non-super admin submits a request, the live value
never changes until a Super Admin (or an authorized approver) approves. Direct-permission
holders bypass the request flow via the existing direct endpoints. Every change is audited.
"""
import secrets
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from models import new_id, now_iso
from .deps import db, log_activity, notify, notify_many, require_admin
from .admin_permission_service import assert_admin_permission, has_permission
from .label_package_service import LabelPackageUpdate, change_label_package


sensitive_r = APIRouter(prefix="/admin", tags=["sensitive-requests"])

# type -> {request, view, approve} permission keys
_PERMS = {
    "blacklist": {"request": "labels.blacklist.request", "view": "labels.blacklist.request.view", "approve": "labels.blacklist.approve"},
    "package": {"request": "labels.package.request", "view": "labels.package.request.view", "approve": "labels.package.approve"},
}


class BlacklistRequestIn(BaseModel):
    action: Literal["blacklist", "unblacklist"]
    reason: str = Field(default="", max_length=1000)


class PackageRequestIn(BaseModel):
    package: Literal["pay_per_release", "annual_normal", "annual_vip"]
    expires_on: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    reason: str = Field(min_length=3, max_length=1000)
    expected_revision: int = Field(ge=0)


class SensitiveDecisionIn(BaseModel):
    action: Literal["approve", "reject"]
    note: Optional[str] = Field(default=None, max_length=1000)


def _reference_id() -> str:
    return "SA-" + secrets.token_hex(4).upper()


def _actor_name(user: dict) -> str:
    return user.get("name") or user.get("role_name") or user.get("email") or user["id"]


async def _get_label(label_id: str) -> dict:
    label = await db.labels.find_one({"id": label_id}, {"_id": 0})
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    return label


async def _approver_ids(action_type: str) -> List[str]:
    approve_perm = _PERMS[action_type]["approve"]
    role_ids = await db.admin_roles.distinct("id", {"permissions": approve_perm, "active": {"$ne": False}})
    ids = []
    async for u in db.users.find(
        {"$or": [{"role": "super_admin"}, {"admin_role_id": {"$in": role_ids}}], "status": {"$nin": ["suspended", "disabled"]}},
        {"_id": 0, "id": 1},
    ):
        ids.append(u["id"])
    return ids


async def _create_request(*, action_type: str, label: dict, summary: str, payload: dict, user: dict) -> dict:
    existing = await db.sensitive_action_requests.find_one(
        {"label_id": label["id"], "action_type": action_type, "status": "pending"}, {"_id": 0, "id": 1})
    if existing:
        raise HTTPException(status_code=409, detail="Sudah ada permintaan menunggu persetujuan untuk aksi ini pada label ini")
    doc = {
        "id": new_id(), "reference_id": _reference_id(), "action_type": action_type,
        "label_id": label["id"], "label_name": label.get("label_name"),
        "summary": summary, "payload": payload, "reason": payload.get("reason") or "",
        "status": "pending", "requested_by": user["id"], "requested_by_name": _actor_name(user),
        "requested_at": now_iso(), "decided_by": None, "decided_by_name": None,
        "decided_at": None, "decision_note": None, "applied": False,
    }
    await db.sensitive_action_requests.insert_one(doc)
    doc.pop("_id", None)
    await log_activity(user["id"], f"{action_type}_request", "sensitive_action", doc["id"], after=doc)
    approvers = await _approver_ids(action_type)
    await notify_many(approvers, "sensitive_request", "Permintaan Persetujuan",
                      f"{label.get('label_name')}: {summary} menunggu persetujuan.",
                      link="/admin/rate-changes", meta={"request_id": doc["id"], "action_type": action_type})
    return doc


@sensitive_r.post("/labels/{label_id}/blacklist-request")
async def request_blacklist(label_id: str, body: BlacklistRequestIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "labels.blacklist.request")
    label = await _get_label(label_id)
    reason = (body.reason or "").strip()
    if body.action == "blacklist" and not reason:
        raise HTTPException(status_code=400, detail="Alasan blacklist wajib diisi")
    is_blacklisted = label.get("account_status") == "blacklisted"
    if body.action == "blacklist" and is_blacklisted:
        raise HTTPException(status_code=400, detail="Label sudah di-blacklist")
    if body.action == "unblacklist" and not is_blacklisted:
        raise HTTPException(status_code=400, detail="Label tidak sedang di-blacklist")
    summary = "Blacklist label" if body.action == "blacklist" else "Lepas blacklist label"
    return await _create_request(action_type="blacklist", label=label, summary=summary,
                                 payload={"action": body.action, "reason": reason}, user=user)


@sensitive_r.post("/labels/{label_id}/package-request")
async def request_package(label_id: str, body: PackageRequestIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "labels.package.request")
    label = await _get_label(label_id)
    if body.package != "pay_per_release" and not body.expires_on:
        raise HTTPException(status_code=422, detail="Isi tanggal masa berlaku untuk paket tahunan.")
    if body.package == "pay_per_release" and body.expires_on:
        raise HTTPException(status_code=422, detail="Pay Per Release tidak menggunakan masa berlaku.")
    names = {"pay_per_release": "Pay Per Release", "annual_normal": "Annual", "annual_vip": "VIP"}
    current = label.get("subscription_tier") if label.get("payment_type") == "annual_subscription" else "pay_per_release"
    summary = f"{names.get(current, current)} → {names[body.package]}" + (f" (s/d {body.expires_on})" if body.expires_on else "")
    payload = {"package": body.package, "expires_on": body.expires_on, "reason": body.reason.strip()}
    return await _create_request(action_type="package", label=label, summary=summary, payload=payload, user=user)


@sensitive_r.get("/sensitive-requests")
async def list_sensitive_requests(status: Optional[str] = None, label_id: Optional[str] = None,
                                  action_type: Optional[str] = None, user: dict = Depends(require_admin)):
    viewable = [t for t, p in _PERMS.items() if has_permission(user, p["view"])]
    if not viewable:
        raise HTTPException(status_code=403, detail="Anda tidak memiliki izin melihat permintaan aksi sensitif")
    query: Dict[str, Any] = {"action_type": {"$in": viewable}}
    if action_type:
        if action_type not in viewable:
            raise HTTPException(status_code=403, detail="Tidak diizinkan untuk jenis ini")
        query["action_type"] = action_type
    if status:
        if status not in {"pending", "approved", "rejected"}:
            raise HTTPException(status_code=400, detail="Status tidak valid")
        query["status"] = status
    if label_id:
        query["label_id"] = label_id
    return await db.sensitive_action_requests.find(query, {"_id": 0}).sort("requested_at", -1).to_list(500)


async def _apply_blacklist(*, label: dict, payload: dict, actor: dict) -> None:
    label_id = label["id"]
    if payload["action"] == "blacklist":
        await db.labels.update_one({"id": label_id}, {"$set": {
            "account_status": "blacklisted", "blacklisted": True,
            "blacklist_reason": payload.get("reason"), "blacklisted_at": now_iso(),
            "blacklisted_by": actor["id"], "updated_at": now_iso(),
        }})
        await log_activity(actor["id"], "blacklist_label", "label", label_id, after={"reason": payload.get("reason")})
    else:
        await db.labels.update_one({"id": label_id}, {"$set": {
            "account_status": "active", "blacklisted": False,
            "blacklist_reason": None, "updated_at": now_iso(),
        }})
        await log_activity(actor["id"], "unblacklist_label", "label", label_id)


async def _apply_package(*, label: dict, payload: dict, actor: dict) -> None:
    from datetime import date
    fresh = await db.labels.find_one({"id": label["id"]}, {"_id": 0, "package_revision": 1})
    revision = int((fresh or {}).get("package_revision") or 0)
    body = LabelPackageUpdate(
        package=payload["package"],
        expires_on=date.fromisoformat(payload["expires_on"]) if payload.get("expires_on") else None,
        reason=payload["reason"], expected_revision=revision, confirm=True,
    )
    await change_label_package(label["id"], body, actor)


@sensitive_r.post("/sensitive-requests/{request_id}/decision")
async def decide_sensitive_request(request_id: str, body: SensitiveDecisionIn, user: dict = Depends(require_admin)):
    req = await db.sensitive_action_requests.find_one({"id": request_id}, {"_id": 0})
    if not req:
        raise HTTPException(status_code=404, detail="Permintaan tidak ditemukan")
    action_type = req["action_type"]
    assert_admin_permission(user, _PERMS[action_type]["approve"])
    if req.get("status") != "pending":
        raise HTTPException(status_code=409, detail="Permintaan sudah diproses")
    now = now_iso()
    decision: Dict[str, Any] = {
        "decided_by": user["id"], "decided_by_name": _actor_name(user),
        "decided_at": now, "decision_note": (body.note or "").strip() or None,
    }
    if body.action == "reject":
        decision["status"] = "rejected"
        await db.sensitive_action_requests.update_one({"id": request_id}, {"$set": decision})
        await log_activity(user["id"], f"{action_type}_reject", "sensitive_action", request_id, before=req, after={**req, **decision})
        await notify(req["requested_by"], "sensitive_decided", "Permintaan Ditolak",
                     f"Permintaan {req.get('reference_id')} untuk {req.get('label_name')} ditolak.",
                     link=f"/admin/labels/{req['label_id']}", meta={"request_id": request_id})
        return {**req, **decision}
    label = await _get_label(req["label_id"])
    if action_type == "blacklist":
        await _apply_blacklist(label=label, payload=req["payload"], actor=user)
    else:
        await _apply_package(label=label, payload=req["payload"], actor=user)
    decision.update({"status": "approved", "applied": True})
    await db.sensitive_action_requests.update_one({"id": request_id}, {"$set": decision})
    await log_activity(user["id"], f"{action_type}_approve", "sensitive_action", request_id, before=req, after={**req, **decision})
    await notify(req["requested_by"], "sensitive_decided", "Permintaan Disetujui",
                 f"Permintaan {req.get('reference_id')} untuk {req.get('label_name')} disetujui: {req.get('summary')}.",
                 link=f"/admin/labels/{req['label_id']}", meta={"request_id": request_id})
    return {**req, **decision}
