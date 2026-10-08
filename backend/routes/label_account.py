"""V13 label account: history, reviewed identity changes and service orders.

Identity rules follow the prototype (profile_edit / reviewProfile103): label name,
email and person in charge change only after an Admin reviews the request, while
the current profile stays valid; contact and location fields save directly.
"""
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from models import new_id, now_iso
from .deps import (
    admin_user_ids, db, get_label_by_user, log_activity, notify, notify_many, require_admin, require_label,
)

label_account_r = APIRouter(prefix="/label", tags=["label-account"])
admin_profile_change_r = APIRouter(prefix="/admin/kyc/profile-changes", tags=["profile-changes"])

REVIEWED_FIELDS = ("label_name", "pic_name", "email")
FIELD_NAMES = {"label_name": "Nama label", "pic_name": "Penanggung jawab", "email": "Email"}
OPEN_STATUSES = ("pending", "correction")

RELEASE_EVENTS = {
    "submitted": "Pengajuan dikirim", "under_review": "Pemeriksaan dimulai", "awaiting_payment": "Tagihan dibuat",
    "paid": "Pembayaran rilisan diterima", "need_revision": "Perbaikan diminta", "approved": "Rilisan disetujui",
    "delivered": "Dikirim ke distribusi", "live": "Tayang dikonfirmasi", "rejected": "Rilisan ditolak",
    "takedown_requested": "Penurunan diajukan", "taken_down": "Rilisan diturunkan", "draft": "Dikembalikan ke draft",
}


# ---------------- History ----------------

@label_account_r.get("/history")
async def label_history(user: dict = Depends(require_label)):
    """Up to 70 recent events for the label and its releases (prototype history10)."""
    label = await get_label_by_user(user)
    events: List[Dict[str, Any]] = []

    def actor(actor_id: Optional[str]) -> str:
        return "Anda" if actor_id == user["id"] else "Rilis Musik"

    async for release in db.releases.find({"label_id": label["id"]}, {"_id": 0, "id": 1, "release_title": 1, "status_history": 1, "created_at": 1}).sort("updated_at", -1).limit(200):
        title = release.get("release_title") or "Rilisan"
        events.append({"name": "Draft dibuat", "target": title, "at": release.get("created_at"), "actor": "Anda", "link": f"/label/releases/{release['id']}"})
        for item in release.get("status_history") or []:
            name = RELEASE_EVENTS.get(item.get("to"))
            if name and item.get("changed_at"):
                events.append({"name": name, "target": title, "at": item["changed_at"], "actor": actor(item.get("changed_by")), "note": item.get("note"), "link": f"/label/releases/{release['id']}"})
    async for payment in db.payments.find({"label_id": label["id"], "status": "paid"}, {"_id": 0, "description": 1, "paid_at": 1, "amount": 1}).sort("paid_at", -1).limit(50):
        events.append({"name": "Pembayaran berhasil", "target": payment.get("description") or "Pembayaran", "at": payment.get("paid_at"), "actor": "Anda", "link": "/label/invoices"})
    async for item in db.withdraw_requests.find({"label_id": label["id"], "legacy_import": {"$ne": True}}, {"_id": 0, "amount_idr": 1, "created_at": 1, "paid_at": 1, "status": 1}).sort("created_at", -1).limit(30):
        events.append({"name": "Penarikan diajukan", "target": f"Rp{int(item.get('amount_idr') or 0):,}".replace(",", "."), "at": item.get("created_at"), "actor": "Anda", "link": "/label/withdraw"})
        if item.get("paid_at"):
            events.append({"name": "Penarikan dibayar", "target": f"Rp{int(item.get('amount_idr') or 0):,}".replace(",", "."), "at": item["paid_at"], "actor": "Rilis Musik", "link": "/label/withdraw"})
    async for item in db.bank_account_change_requests.find({"label_id": label["id"]}, {"_id": 0}).sort("created_at", -1).limit(20):
        bank = (item.get("proposed_bank") or {}).get("bank_name") or "Rekening"
        events.append({"name": "Rekening diajukan", "target": bank, "at": item.get("created_at"), "actor": "Anda", "link": "/label/profile?tab=bank"})
        if item.get("status") in ("approved", "rejected") and item.get("reviewed_at"):
            events.append({"name": "Rekening disetujui" if item["status"] == "approved" else "Rekening perlu diperbaiki", "target": bank, "at": item["reviewed_at"], "actor": "Rilis Musik", "link": "/label/profile?tab=bank"})
    async for item in db.label_profile_changes.find({"label_id": label["id"]}, {"_id": 0}).sort("created_at", -1).limit(20):
        events.append({"name": "Perubahan identitas diajukan", "target": ", ".join(FIELD_NAMES[k] for k in item.get("after", {})), "at": item.get("created_at"), "actor": "Anda", "link": "/label/profile"})
        if item.get("reviewed_at"):
            events.append({"name": "Perubahan identitas disetujui" if item["status"] == "approved" else "Perubahan identitas perlu diperbaiki", "target": label.get("label_name"), "at": item["reviewed_at"], "actor": "Rilis Musik", "link": "/label/profile"})
    events = [event for event in events if event.get("at")]
    events.sort(key=lambda event: str(event["at"]), reverse=True)
    return {"items": events[:70]}


# ---------------- Identity changes ----------------

class ProfileChangeIn(BaseModel):
    label_name: Optional[str] = Field(default=None, max_length=120)
    pic_name: Optional[str] = Field(default=None, max_length=120)
    email: Optional[str] = Field(default=None, max_length=200)


async def _current_identity(label: Dict[str, Any], user: dict) -> Dict[str, str]:
    owner = await db.users.find_one({"id": label.get("user_id") or user["id"]}, {"_id": 0, "email": 1}) or {}
    return {"label_name": label.get("label_name") or "", "pic_name": label.get("pic_name") or "", "email": owner.get("email") or label.get("email") or ""}


@label_account_r.get("/profile-change")
async def get_profile_change(user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    request = await db.label_profile_changes.find_one({"label_id": label["id"]}, {"_id": 0}, sort=[("created_at", -1)])
    return {"request": request, "reviewed_fields": list(REVIEWED_FIELDS)}


@label_account_r.post("/profile-change")
async def submit_profile_change(body: ProfileChangeIn, user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    current = await _current_identity(label, user)
    after = {}
    for field in REVIEWED_FIELDS:
        value = getattr(body, field)
        if value is not None and value.strip() and value.strip() != current[field]:
            after[field] = value.strip().lower() if field == "email" else value.strip()
    open_request = await db.label_profile_changes.find_one({"label_id": label["id"], "status": {"$in": list(OPEN_STATUSES)}}, {"_id": 0})
    if open_request and open_request["status"] == "pending":
        raise HTTPException(status_code=409, detail="Perubahan identitas sebelumnya masih diperiksa.")
    if not after:
        if open_request:  # resubmitting a correction without changes withdraws it
            await db.label_profile_changes.update_one({"id": open_request["id"]}, {"$set": {"status": "withdrawn", "updated_at": now_iso()}})
            return {"request": None}
        raise HTTPException(status_code=400, detail="Tidak ada perubahan pada nama label, email, atau penanggung jawab.")
    if "email" in after and await db.users.find_one({"email": after["email"], "id": {"$ne": label.get("user_id")}}, {"_id": 1}):
        raise HTTPException(status_code=409, detail="Email ini sudah dipakai akun lain")
    document = {"id": new_id(), "label_id": label["id"], "label_name": label.get("label_name"), "user_id": user["id"],
                "before": {field: current[field] for field in after}, "after": after, "status": "pending",
                "created_at": now_iso(), "updated_at": now_iso()}
    if open_request:
        await db.label_profile_changes.update_one({"id": open_request["id"]}, {"$set": {"status": "superseded", "updated_at": now_iso()}})
    await db.label_profile_changes.insert_one(dict(document))
    await log_activity(user["id"], "profile_change_request", "label", label["id"], before=document["before"], after=after)
    await notify_many(await admin_user_ids(("super_admin", "admin_support")), "profile_change_request", "Perubahan identitas label",
                      f"{label.get('label_name')} mengajukan perubahan {', '.join(FIELD_NAMES[k].lower() for k in after)}.",
                      "/admin/kyc?tab=profile-changes", {"label_id": label["id"], "request_id": document["id"]})
    return {"request": document}


@admin_profile_change_r.get("")
async def list_profile_changes(status: str = "pending", user: dict = Depends(require_admin)):
    query = {} if status == "all" else {"status": status}
    return {"items": await db.label_profile_changes.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)}


class ProfileChangeReviewIn(BaseModel):
    action: Literal["approve", "correct"]
    note: Optional[str] = Field(default=None, max_length=1000)


@admin_profile_change_r.post("/{request_id}/review")
async def review_profile_change(request_id: str, body: ProfileChangeReviewIn, user: dict = Depends(require_admin)):
    request = await db.label_profile_changes.find_one({"id": request_id}, {"_id": 0})
    if not request or request.get("status") != "pending":
        raise HTTPException(status_code=404, detail="Pengajuan tidak ditemukan atau sudah ditinjau")
    if body.action == "correct" and not (body.note or "").strip():
        raise HTTPException(status_code=400, detail="Catatan perbaikan wajib diisi")
    label = await db.labels.find_one({"id": request["label_id"]}, {"_id": 0})
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    if body.action == "approve":
        after = request["after"]
        if after.get("email"):
            from .admin_label_service import change_label_email
            await change_label_email(label_id=label["id"], new_email=after["email"], send_notification=True, user=user)
        fields = {k: v for k, v in after.items() if k in ("label_name", "pic_name")}
        if fields:
            await db.labels.update_one({"id": label["id"]}, {"$set": {**fields, "updated_at": now_iso()}})
    status = "approved" if body.action == "approve" else "correction"
    claimed = await db.label_profile_changes.update_one({"id": request_id, "status": "pending"}, {"$set": {
        "status": status, "review_note": (body.note or "").strip() or None, "reviewed_by": user["id"],
        "reviewed_by_name": user.get("name"), "reviewed_at": now_iso(), "updated_at": now_iso()}})
    if not claimed.modified_count:
        raise HTTPException(status_code=409, detail="Pengajuan sudah ditinjau")
    await log_activity(user["id"], f"profile_change_{body.action}", "label", label["id"], before=request["before"], after=request["after"])
    if label.get("user_id"):
        if status == "approved":
            await notify(label["user_id"], "profile_change_approved", "Perubahan identitas disetujui", "Profil labelmu sudah diperbarui.", "/label/profile")
        else:
            await notify(label["user_id"], "profile_change_correction", "Perubahan identitas perlu diperbaiki", "Buka Profil Label untuk melihat catatan.", "/label/profile")
    return {"request": await db.label_profile_changes.find_one({"id": request_id}, {"_id": 0})}


# ---------------- Service orders ----------------

@label_account_r.get("/service-orders")
async def label_service_orders(user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    return {"items": await db.service_orders.find({"label_id": label["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)}
