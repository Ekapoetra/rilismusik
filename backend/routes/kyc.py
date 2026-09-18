"""Label KYC uploads and Super Admin/Admin Support review queue."""
import hashlib
import io
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from PIL import Image, UnidentifiedImageError

import storage_service
from models import KycReviewActionIn, new_id, now_iso
from .deps import (
    admin_user_ids, db, get_label_by_user, log_activity, notify, notify_many,
    require_admin, require_label, assert_admin_permission,
)
from .kyc_service import compute_kyc_state


kyc_r = APIRouter(tags=["kyc"])
IMAGE_TYPES = {"image/jpeg": "jpg", "image/png": "png"}


def _reviewer(user: dict) -> None:
    assert_admin_permission(user, "kyc.review")


def _kyc_approver(user: dict) -> None:
    """Only Super Admin may APPROVE/REJECT KYC (process verification)."""
    if user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Hanya Super Admin yang dapat memproses verifikasi akun")


async def _read_image(file: UploadFile, max_bytes: int, label: str) -> tuple[bytes, str, str, int, int]:
    content_type = (file.content_type or "").lower()
    if content_type not in IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=f"{label} wajib JPG atau PNG")
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail=f"{label} melebihi batas {max_bytes // (1024 * 1024)} MB")
    try:
        image = Image.open(io.BytesIO(data)); image.verify()
        image = Image.open(io.BytesIO(data)); width, height = image.size
        actual = (image.format or "").upper()
        if actual not in ("JPEG", "PNG"):
            raise HTTPException(status_code=400, detail=f"{label} wajib JPG atau PNG")
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail=f"File {label.lower()} tidak valid")
    ext = "jpg" if actual == "JPEG" else "png"
    media_type = "image/jpeg" if actual == "JPEG" else "image/png"
    return data, ext, media_type, int(width), int(height)


@kyc_r.get("/label/kyc")
async def label_kyc_status(user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    return await compute_kyc_state(user=user, label=label)


@kyc_r.post("/label/logo")
async def upload_label_logo(file: UploadFile = File(...), user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    data, ext, media_type, width, height = await _read_image(file, 5 * 1024 * 1024, "Logo")
    key = f"label-logo/{label['id']}/{new_id()}.{ext}"
    await storage_service.upload_bytes(key=key, data=data, content_type=media_type)
    old_key = label.get("logo_storage_key")
    await db.labels.update_one({"id": label["id"]}, {"$set": {
        "logo_url": f"/api/files/{key}", "logo_storage_key": key,
        "logo_filename": file.filename, "logo_width": width, "logo_height": height,
        "logo_updated_at": now_iso(), "updated_at": now_iso(),
    }})
    if old_key and old_key != key:
        await storage_service.delete_object(key=old_key)
    await log_activity(user["id"], "label_logo_upload", "label", label["id"], after={"filename": file.filename, "width": width, "height": height})
    return {"logo_url": f"/api/files/{key}", "width": width, "height": height}


@kyc_r.post("/label/kyc/ktp")
async def upload_ktp(file: UploadFile = File(...), user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    state = await compute_kyc_state(user=user, label=label)
    if not state["prerequisites_complete"]:
        raise HTTPException(status_code=409, detail="Lengkapi seluruh checklist profil sebelum mengunggah KTP")
    if state["status"] == "pending_review":
        raise HTTPException(status_code=409, detail="KTP sedang menunggu review admin")
    if state["is_verified"]:
        raise HTTPException(status_code=409, detail="Akun sudah terverifikasi")
    data, ext, media_type, width, height = await _read_image(file, 10 * 1024 * 1024, "KTP")
    doc_id = new_id(); key = f"kyc-private/{label['id']}/{doc_id}.{ext}"
    await storage_service.upload_bytes(key=key, data=data, content_type=media_type)
    old_doc = await db.kyc_documents.find_one({"label_id": label["id"], "is_current": True}, {"_id": 0})
    await db.kyc_documents.update_many({"label_id": label["id"], "is_current": True}, {"$set": {"is_current": False, "replaced_at": now_iso()}})
    doc = {
        "id": doc_id, "label_id": label["id"], "storage_key": key,
        "original_filename": file.filename, "content_type": media_type,
        "size": len(data), "width": width, "height": height,
        "sha256": hashlib.sha256(data).hexdigest(), "status": "pending_review",
        "is_current": True, "uploaded_by": user["id"], "uploaded_at": now_iso(),
        "reviewed_by": None, "reviewed_at": None, "rejection_reason": None,
    }
    await db.kyc_documents.insert_one(doc)
    await db.labels.update_one({"id": label["id"]}, {"$set": {
        "kyc_document_id": doc_id, "kyc_status": "pending_review",
        "kyc_rejection_reason": None, "kyc_submitted_at": now_iso(), "updated_at": now_iso(),
    }})
    if old_doc and old_doc.get("storage_key"):
        await storage_service.delete_object(key=old_doc["storage_key"])
    await notify_many(
        await admin_user_ids(("super_admin", "admin_support")),
        "kyc_review_required", "Verifikasi Akun baru perlu direview",
        f"{label.get('label_name')} mengunggah foto KTP.", "/admin/kyc",
        {"label_id": label["id"], "kyc_document_id": doc_id},
    )
    await log_activity(user["id"], "kyc_ktp_submit", "kyc", doc_id, after={"label_id": label["id"], "status": "pending_review"})
    return {"id": doc_id, "status": "pending_review", "uploaded_at": doc["uploaded_at"], "original_filename": file.filename}


async def _document_response(doc: dict) -> Response:
    try:
        data = await storage_service.download_bytes(key=doc["storage_key"])
    except Exception:
        raise HTTPException(status_code=502, detail="Foto KTP tidak dapat dimuat dari penyimpanan")
    return Response(
        content=data, media_type=doc.get("content_type") or "application/octet-stream",
        headers={"Cache-Control": "no-store, private", "Content-Disposition": "inline"},
    )


@kyc_r.get("/label/kyc/ktp")
async def view_own_ktp(user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    doc = await db.kyc_documents.find_one({"id": label.get("kyc_document_id"), "label_id": label["id"], "is_current": True}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Foto KTP belum tersedia")
    return await _document_response(doc)


@kyc_r.get("/admin/kyc")
async def admin_kyc_queue(status: Optional[str] = "pending_review", user: dict = Depends(require_admin)):
    _reviewer(user)
    query = {"is_current": True}
    if status:
        query["status"] = status
    docs = await db.kyc_documents.find(query, {"_id": 0, "storage_key": 0, "sha256": 0}).sort("uploaded_at", 1).to_list(1000)
    label_ids = list({doc["label_id"] for doc in docs})
    labels = await db.labels.find({"id": {"$in": label_ids}}, {"_id": 0}).to_list(len(label_ids) or 1)
    label_map = {label["id"]: label for label in labels}
    user_ids = [label.get("user_id") for label in labels if label.get("user_id")]
    users = await db.users.find({"id": {"$in": user_ids}}, {"_id": 0, "id": 1, "email": 1, "name": 1, "email_verified_at": 1, "status": 1}).to_list(len(user_ids) or 1)
    user_map = {item["id"]: item for item in users}
    items = []
    for doc in docs:
        label = label_map.get(doc["label_id"], {})
        owner = user_map.get(label.get("user_id"), {})
        state = await compute_kyc_state(user=owner, label=label) if label and owner else None
        items.append({**doc, "label_name": label.get("label_name"), "pic_name": label.get("pic_name") or owner.get("name"), "email": owner.get("email"), "whatsapp": label.get("whatsapp"), "address": label.get("address"), "city": label.get("city"), "kyc": state})
    return items


@kyc_r.get("/admin/kyc/{label_id}")
async def admin_kyc_detail(label_id: str, user: dict = Depends(require_admin)):
    _reviewer(user)
    label = await db.labels.find_one({"id": label_id}, {"_id": 0})
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    owner = await db.users.find_one({"id": label.get("user_id")}, {"_id": 0, "password_hash": 0})
    state = await compute_kyc_state(user=owner or {}, label=label)
    bank = await db.bank_accounts.find_one({"label_id": label_id}, {"_id": 0})
    return {"label": label, "user": owner, "bank": bank, "kyc": state}


@kyc_r.get("/admin/kyc/{label_id}/ktp")
async def admin_view_ktp(label_id: str, user: dict = Depends(require_admin)):
    _reviewer(user)
    label = await db.labels.find_one({"id": label_id}, {"_id": 0, "kyc_document_id": 1})
    doc = await db.kyc_documents.find_one({"id": (label or {}).get("kyc_document_id"), "label_id": label_id, "is_current": True}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Foto KTP tidak ditemukan")
    return await _document_response(doc)


@kyc_r.post("/admin/kyc/{label_id}/action")
async def admin_review_kyc(label_id: str, body: KycReviewActionIn, user: dict = Depends(require_admin)):
    _kyc_approver(user)
    if body.action == "reject" and not str(body.reason or "").strip():
        raise HTTPException(status_code=400, detail="Alasan penolakan wajib diisi")
    label = await db.labels.find_one({"id": label_id}, {"_id": 0})
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    owner = await db.users.find_one({"id": label.get("user_id")}, {"_id": 0, "password_hash": 0})
    state = await compute_kyc_state(user=owner or {}, label=label)
    if body.action == "approve" and not state["prerequisites_complete"]:
        raise HTTPException(status_code=409, detail="Checklist label belum lengkap")
    doc_id = label.get("kyc_document_id")
    next_status = "verified" if body.action == "approve" else "rejected"
    claimed = await db.kyc_documents.update_one(
        {"id": doc_id, "label_id": label_id, "status": "pending_review", "is_current": True},
        {"$set": {"status": next_status, "reviewed_by": user["id"], "reviewed_at": now_iso(), "rejection_reason": str(body.reason or "").strip() or None}},
    )
    if claimed.modified_count != 1:
        raise HTTPException(status_code=409, detail="KYC sudah direview atau dokumen berubah")
    update = {
        "kyc_status": next_status, "kyc_reviewed_by": user["id"],
        "kyc_reviewed_at": now_iso(), "kyc_rejection_reason": str(body.reason or "").strip() or None,
        "updated_at": now_iso(),
    }
    if next_status == "verified":
        update["kyc_verified_at"] = now_iso(); update["kyc_verified_by"] = user["id"]
    await db.labels.update_one({"id": label_id, "kyc_document_id": doc_id}, {"$set": update})
    if label.get("user_id"):
        await notify(
            label["user_id"], f"kyc_{next_status}",
            "Akun Terverifikasi" if next_status == "verified" else "Verifikasi Akun ditolak",
            "Akun label Anda sudah terverifikasi." if next_status == "verified" else f"Alasan: {body.reason}",
            "/label/profile", {"label_id": label_id, "status": next_status},
        )
    await log_activity(user["id"], f"kyc_{body.action}", "kyc", doc_id, before={"status": "pending_review"}, after={"status": next_status, "reason": body.reason})
    return await admin_kyc_detail(label_id, user)