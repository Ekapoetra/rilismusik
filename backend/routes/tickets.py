"""Support tickets router."""
from fastapi import APIRouter, HTTPException, Request, Response, Depends, UploadFile, File, Form, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta, date
import os
import csv
import io
import shutil
import secrets
from urllib.parse import urlparse

from .deps import (
    db, logger, UPLOAD_DIR,
    get_current_user, require_label, require_artist, require_admin, require_super_admin,
    require_kyc_for_label_user,
    public_user, get_label_by_user, redact_label_for_self, LABEL_HIDDEN_FIELDS,
    log_activity, notify, notify_many, admin_user_ids, label_user_ids,
    LABEL_ROLE, ARTIST_ROLE, ADMIN_ROLES, SUPER_ADMIN,
)
from models import (
    RegisterLabelIn, LoginIn, ForgotPasswordIn, ResetPasswordIn, VerifyEmailIn,
    LabelProfileUpdate, BankAccountIn,
    ReleaseDraftIn, ReleaseSubmitConfirmation, AdminReleaseAction,
    ArtistIn, ArtistUpdateIn,
    CreateReleasePaymentIn,
    CMSUpdateIn, AdminUserCreateIn, LabelStatusUpdate,
    ExchangeRateIn, RoyaltyImportPublishIn, RoyaltyLineMatchIn,
    WithdrawRequestIn, WithdrawAdminAction,
    TicketCreateIn, TicketCommentIn, TicketAdminUpdateIn,
    ContractCreateIn, ContractExtendIn, ContractTerminateIn,
    BlacklistIn, NotificationMarkIn,
    CreateSubscriptionPaymentIn, CreateWamiOrderIn, AdminWamiUpdateIn,
    now_iso, new_id,
)
from auth_utils import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    set_auth_cookies, clear_auth_cookies, decode_token,
)
from royalty_utils import (
    parse_csv_bytes, detect_columns, parse_amount, normalize_header,
    parse_period_from_value, calculate_line, label_percentage_at,
    strip_sensitive,
)
from withdraw_utils import withdraw_window_state, jakarta_now, MIN_WITHDRAW_IDR
from .ticket_workflow_service import TICKET_CATEGORY_LABELS, ACTIVE_CATEGORIES, TicketCreatedOut, prepare_ticket_submission
from .admin_permission_service import is_admin_identity, has_permission, assert_admin_permission

# =============================================================================
#                              SUPPORT TICKETS
# =============================================================================
ticket_r = APIRouter(prefix="/tickets", tags=["tickets"])

# Statuses that block label cancel (admin must process manually)
TICKET_NON_CANCELLABLE = {"done", "submitted_to_believe", "rejected", "cancelled"}


async def _ticket_visible_to(user: dict, ticket: dict) -> bool:
    if is_admin_identity(user):
        return has_permission(user, "support.view") or has_permission(user, "support.manage")
    if user["role"] == LABEL_ROLE:
        label = await db.labels.find_one({"user_id": user["id"]}, {"_id": 0, "id": 1})
        return bool(label) and ticket.get("label_id") == label["id"]
    return False


@ticket_r.get("/categories")
async def list_ticket_categories(user: dict = Depends(require_kyc_for_label_user)):
    return [{"value": k, "label": TICKET_CATEGORY_LABELS[k]} for k in ACTIVE_CATEGORIES]


@ticket_r.post("/upload-attachment")
async def upload_ticket_attachment(
    file: UploadFile = File(...),
    purpose: str = Form("general"),  # general | audio | cover
    user: dict = Depends(require_kyc_for_label_user),
):
    """Upload attachment for ticket (audio WAV for edit_audio, cover for edit_cover, or generic attachment)."""
    if is_admin_identity(user):
        assert_admin_permission(user, "support.manage")
    elif user["role"] != LABEL_ROLE:
        raise HTTPException(403, "Hanya label dan admin support yang dapat mengunggah lampiran tiket")
    import storage_service
    ext = (file.filename or "").lower().split(".")[-1]
    if purpose == "audio":
        if ext != "wav":
            raise HTTPException(status_code=400, detail="File audio harus berformat WAV")
        sub = "audio"
    elif purpose == "cover":
        if ext not in ("jpg", "jpeg", "png"):
            raise HTTPException(status_code=400, detail="Cover harus JPG/PNG")
        # validate 3000x3000
        from PIL import Image
        contents = await file.read()
        try:
            img = Image.open(io.BytesIO(contents))
        except Exception:
            raise HTTPException(status_code=400, detail="File cover tidak valid")
        if img.size != (3000, 3000):
            raise HTTPException(status_code=400, detail=f"Cover harus 3000x3000 (terdeteksi {img.size[0]}x{img.size[1]})")
        fid = new_id()
        key = f"cover/ticket_{fid}.{ext}"
        ct = "image/png" if ext == "png" else "image/jpeg"
        await storage_service.upload_bytes(key=key, data=contents, content_type=ct)
        return {"url": f"/api/files/{key}", "filename": file.filename}
    else:
        if ext not in ("jpg", "jpeg", "png", "pdf", "wav", "mp3", "txt", "docx", "doc"):
            raise HTTPException(status_code=400, detail="Format file tidak didukung")
        sub = "ticket"
    # generic upload
    fid = new_id()
    key = f"{sub}/ticket_{fid}.{ext}"
    ct = storage_service.guess_content_type(file.filename or key)
    await storage_service.upload_fileobj(key=key, fileobj=file.file, content_type=ct)
    return {"url": f"/api/files/{key}", "filename": file.filename}


@ticket_r.post("/label/create", response_model=TicketCreatedOut)
async def label_create_ticket(body: TicketCreateIn, user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    if label.get("account_status") in ("suspended", "blacklisted"):
        raise HTTPException(status_code=403, detail="Akun tidak dapat membuat tiket")

    # Validate release ownership
    release = await db.releases.find_one({"id": body.release_id}, {"_id": 0})
    if not release:
        raise HTTPException(status_code=404, detail="Rilisan tidak ditemukan")
    if release["label_id"] != label["id"]:
        raise HTTPException(status_code=403, detail="Rilisan ini bukan milik Anda")

    if body.category == "content_id_claim":
        if not body.content_id_request_id:
            raise HTTPException(400, "Identitas pengajuan Content ID wajib tersedia")
        from .contentid_service import contentid_ticket_id
        candidate_id = contentid_ticket_id(label["id"], body.content_id_request_id)
        existing = await db.support_tickets.find_one({"id": candidate_id, "label_id": label["id"]}, {"_id": 0})
        if existing:
            await db.contentid_assets.update_many({"ticket_id": candidate_id, "status": "reserved"}, {"$set": {"status": "bound"}})
            await db.contentid_requests.delete_one({"_id": candidate_id})
            return TicketCreatedOut(**existing, submission_replayed=True)
        if await db.contentid_requests.find_one({"_id": candidate_id}, {"_id": 1}):
            raise HTTPException(409, "Pengajuan ini sedang diproses. Tunggu sebentar lalu periksa daftar tiket.")
    elif body.content_id_creators or body.content_id_track_ids:
        raise HTTPException(400, "Surat pencipta hanya untuk Pengajuan Content ID")
    submission = await prepare_ticket_submission(body, release)
    # Retain the existing audio/cover workflows.
    if body.category == "edit_audio":
        if not body.new_audio_url:
            raise HTTPException(status_code=400, detail="Upload file WAV baru wajib untuk edit audio")
        if not body.new_audio_track_id:
            raise HTTPException(status_code=400, detail="Pilih track yang ingin di-edit audionya")
        if not await db.tracks.find_one({"id": body.new_audio_track_id, "release_id": body.release_id}, {"_id": 0, "id": 1}):
            raise HTTPException(status_code=400, detail="Track bukan bagian dari rilisan terpilih")
    elif body.category == "edit_cover":
        if not body.new_cover_url:
            raise HTTPException(status_code=400, detail="Upload cover baru 3000x3000 wajib untuk edit cover")

    ticket_id = candidate_id if body.category == "content_id_claim" else new_id()
    content_id_documents = []
    if body.category == "content_id_claim":
        from .contentid_service import build_contentid_documents
        content_id_documents = await build_contentid_documents(body, release, label, ticket_id, user)
    # short ticket number for display: RM-YYMMDD-XXXXX
    short_no = f"RM-{datetime.now(timezone.utc).strftime('%y%m%d')}-{ticket_id[:5].upper()}"
    doc = {
        "id": ticket_id,
        "ticket_no": short_no,
        "label_id": label["id"],
        "release_id": body.release_id,
        "release_title": release.get("release_title"),
        "release_cover_url": release.get("cover_url"),
        "created_by_user_id": user["id"],
        "category": body.category,
        "category_label": TICKET_CATEGORY_LABELS[body.category],
        "subject": body.subject,
        "description": body.description,
        "new_metadata": body.new_metadata,
        "new_audio_url": body.new_audio_url,
        "new_audio_track_id": body.new_audio_track_id,
        "new_cover_url": body.new_cover_url,
        "reason": body.reason,
        "originality_declared": body.originality_declared,
        "youtube_url": body.youtube_url,
        "attachments": body.attachments,
        "status": "open",
        "assigned_admin_id": None,
        "internal_note": None,
        "submitted_to_believe_at": None,
        "resolved_at": None,
        "cancelled_at": None,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        **submission,
    }
    if body.category == "content_id_claim":
        doc.update({"content_id_documents": content_id_documents, "content_id_track_ids": body.content_id_track_ids,
                    "content_id_request_id": body.content_id_request_id, "content_id_consent_at": now_iso()})
    try:
        await db.support_tickets.insert_one(doc)
    except Exception:
        if body.category == "content_id_claim":
            from .contentid_service import rollback_contentid
            await rollback_contentid(ticket_id)
        raise
    if content_id_documents:
        await db.contentid_assets.update_many({"ticket_id": ticket_id, "status": "reserved"}, {"$set": {"status": "bound"}})
        await db.contentid_requests.delete_one({"_id": ticket_id})
    # Seed first comment with the description so it's visible in chat
    await db.ticket_comments.insert_one({
        "id": new_id(),
        "ticket_id": ticket_id,
        "user_id": user["id"],
        "user_name": user.get("name"),
        "role": LABEL_ROLE,
        "body": submission["description"] or submission["reason"] or submission["subject"],
        "attachments": body.attachments,
        "is_system": False,
        "created_at": now_iso(),
    })
    await log_activity(user["id"], "ticket_create", "support", ticket_id, after={"category": body.category, "release_id": body.release_id})
    # Notify admins
    admin_ids = await admin_user_ids(("super_admin", "admin_support", "admin_release"))
    await notify_many(
        admin_ids, "ticket_new",
        f"Tiket baru {short_no}",
        f"{label.get('label_name')} mengajukan {TICKET_CATEGORY_LABELS[body.category]}.",
        f"/admin/tickets/{ticket_id}", {"ticket_id": ticket_id},
    )
    doc.pop("_id", None)
    return TicketCreatedOut(**doc)


@ticket_r.get("/label")
async def label_list_tickets(user: dict = Depends(require_label), status: Optional[str] = None):
    label = await get_label_by_user(user)
    filt: Dict[str, Any] = {"label_id": label["id"]}
    if status:
        filt["status"] = status
    items = await db.support_tickets.find(filt, {"_id": 0, "internal_note": 0}).sort("created_at", -1).to_list(500)
    return items


@ticket_r.get("/admin")
async def admin_list_tickets(
    user: dict = Depends(require_admin),
    status: Optional[str] = None,
    category: Optional[str] = None,
    label_id: Optional[str] = None,
    q: Optional[str] = None,
):
    filt: Dict[str, Any] = {}
    if status:
        filt["status"] = status
    if category:
        filt["category"] = category
    if label_id:
        filt["label_id"] = label_id
    if q:
        filt["$or"] = [
            {"subject": {"$regex": q, "$options": "i"}},
            {"ticket_no": {"$regex": q, "$options": "i"}},
        ]
    items = await db.support_tickets.find(filt, {"_id": 0}).sort("created_at", -1).to_list(500)
    label_ids = list({i["label_id"] for i in items})
    labels = await db.labels.find({"id": {"$in": label_ids}}, {"_id": 0, "id": 1, "label_name": 1}).to_list(1000)
    name_map = {lab["id"]: lab["label_name"] for lab in labels}
    for it in items:
        it["label_name"] = name_map.get(it["label_id"])
    return items


@ticket_r.get("/{ticket_id}")
async def get_ticket(ticket_id: str, user: dict = Depends(require_kyc_for_label_user)):
    ticket = await db.support_tickets.find_one({"id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Tiket tidak ditemukan")
    if not await _ticket_visible_to(user, ticket):
        raise HTTPException(status_code=403, detail="Tidak diizinkan")
    comments = await db.ticket_comments.find({"ticket_id": ticket_id}, {"_id": 0}).sort("created_at", 1).to_list(1000)
    label = await db.labels.find_one({"id": ticket["label_id"]}, {"_id": 0, "id": 1, "label_name": 1, "pic_name": 1, "email": 1})
    ticket["label"] = label
    if user["role"] == LABEL_ROLE:
        ticket.pop("internal_note", None)
    return {"ticket": ticket, "comments": comments}


@ticket_r.post("/{ticket_id}/comment")
async def post_ticket_comment(ticket_id: str, body: TicketCommentIn, user: dict = Depends(require_kyc_for_label_user)):
    ticket = await db.support_tickets.find_one({"id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Tiket tidak ditemukan")
    if not await _ticket_visible_to(user, ticket):
        raise HTTPException(status_code=403, detail="Tidak diizinkan")
    if ticket["status"] in ("done", "rejected", "cancelled"):
        raise HTTPException(status_code=400, detail="Tiket sudah ditutup")
    if is_admin_identity(user):
        assert_admin_permission(user, "support.manage")

    comment = {
        "id": new_id(),
        "ticket_id": ticket_id,
        "user_id": user["id"],
        "user_name": user.get("name"),
        "role": user["role"],
        "body": body.body,
        "attachments": body.attachments,
        "is_system": False,
        "created_at": now_iso(),
    }
    await db.ticket_comments.insert_one(comment)
    # update status flow: if admin comments → status waiting_label; if label comments → waiting_admin
    new_status = ticket["status"]
    if is_admin_identity(user) and ticket["status"] in ("open", "waiting_admin", "in_progress"):
        new_status = "waiting_label"
    elif user["role"] == LABEL_ROLE and ticket["status"] in ("waiting_label",):
        new_status = "waiting_admin"
    elif user["role"] == LABEL_ROLE and ticket["status"] == "open":
        new_status = "waiting_admin"

    update_doc = {"updated_at": now_iso()}
    if new_status != ticket["status"]:
        update_doc["status"] = new_status
    await db.support_tickets.update_one({"id": ticket_id}, {"$set": update_doc})
    await _notify_ticket_event(ticket_id, actor=user, kind="comment")
    comment.pop("_id", None)
    return {"comment": comment, "new_status": update_doc.get("status", ticket["status"])}


@ticket_r.post("/{ticket_id}/cancel")
async def label_cancel_ticket(ticket_id: str, user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    ticket = await db.support_tickets.find_one({"id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Tiket tidak ditemukan")
    if ticket["label_id"] != label["id"]:
        raise HTTPException(status_code=403, detail="Bukan tiket Anda")
    if ticket["status"] in TICKET_NON_CANCELLABLE:
        raise HTTPException(status_code=400, detail="Status tidak dapat dibatalkan langsung. Hubungi admin.")
    await db.support_tickets.update_one({"id": ticket_id}, {"$set": {
        "status": "cancelled", "cancelled_at": now_iso(), "updated_at": now_iso(),
    }})
    await db.ticket_comments.insert_one({
        "id": new_id(), "ticket_id": ticket_id, "user_id": user["id"], "user_name": user.get("name"),
        "role": LABEL_ROLE, "body": "Tiket dibatalkan oleh label.", "attachments": [], "is_system": True,
        "created_at": now_iso(),
    })
    await log_activity(user["id"], "ticket_cancel", "support", ticket_id)
    return await db.support_tickets.find_one({"id": ticket_id}, {"_id": 0, "internal_note": 0})


@ticket_r.post("/admin/{ticket_id}/status")
async def admin_update_ticket(ticket_id: str, body: TicketAdminUpdateIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "support.manage")
    ticket = await db.support_tickets.find_one({"id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Tiket tidak ditemukan")
    upd: Dict[str, Any] = {"updated_at": now_iso()}
    if body.status:
        upd["status"] = body.status
        if body.status == "submitted_to_believe":
            upd["submitted_to_believe_at"] = now_iso()
        if body.status in ("done", "rejected"):
            upd["resolved_at"] = now_iso()
        upd["assigned_admin_id"] = user["id"]
    if body.internal_note is not None:
        upd["internal_note"] = body.internal_note
    if body.status == ticket.get("status") and (body.internal_note is None or body.internal_note == ticket.get("internal_note")):
        return await db.support_tickets.find_one({"id": ticket_id}, {"_id": 0})
    if ticket.get("category") == "takedown" and body.status == "done":
        from .ticket_takedown_service import complete_takedown_ticket
        await complete_takedown_ticket(ticket, upd, user)
    else:
        await db.support_tickets.update_one({"id": ticket_id}, {"$set": upd})
    # System comment
    if body.status:
        status_labels = {
            "open": "Open", "waiting_admin": "Menunggu Admin", "waiting_label": "Menunggu Label",
            "in_progress": "Sedang Diproses", "submitted_to_believe": "Disubmit ke Believe",
            "done": "Selesai", "rejected": "Ditolak", "cancelled": "Dibatalkan",
        }
        await db.ticket_comments.insert_one({
            "id": new_id(), "ticket_id": ticket_id, "user_id": user["id"], "user_name": user.get("name"),
            "role": user["role"], "body": f"Status diubah ke: {status_labels.get(body.status, body.status)}",
            "attachments": [], "is_system": True, "created_at": now_iso(),
        })
    await log_activity(user["id"], "ticket_update", "support", ticket_id, after=upd)
    # Notify label about status change / admin reply
    await _notify_ticket_event(ticket_id, actor=user, kind=("status" if body.status else "note"))
    return await db.support_tickets.find_one({"id": ticket_id}, {"_id": 0})



async def _notify_ticket_event(ticket_id: str, actor: Dict[str, Any], kind: str = "comment"):
    """When a comment/status change happens, notify the OTHER side."""
    ticket = await db.support_tickets.find_one({"id": ticket_id}, {"_id": 0})
    if not ticket:
        return
    actor_is_admin = is_admin_identity(actor)
    link_label = f"/label/support/{ticket_id}"
    link_admin = f"/admin/tickets/{ticket_id}"
    if actor_is_admin:
        # Notify label
        user_ids = await label_user_ids(ticket["label_id"])
        title = f"Tiket {ticket['ticket_no']} — Update Admin"
        body = f"Admin {'mengubah status' if kind == 'status' else 'membalas'} tiket Anda."
        await notify_many(user_ids, "ticket_update", title, body, link_label, {"ticket_id": ticket_id})
    else:
        # Notify admins (support + super_admin)
        user_ids = await admin_user_ids(("super_admin", "admin_support", "admin_release"))
        title = f"Tiket {ticket['ticket_no']} — Label membalas"
        body = f"{actor.get('name') or 'Label'} membalas tiket."
        await notify_many(user_ids, "ticket_update", title, body, link_admin, {"ticket_id": ticket_id})



