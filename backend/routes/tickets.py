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

# =============================================================================
#                              SUPPORT TICKETS
# =============================================================================
ticket_r = APIRouter(prefix="/tickets", tags=["tickets"])

TICKET_CATEGORY_LABELS = {
    "takedown": "Takedown Rilisan",
    "edit_metadata": "Edit Metadata",
    "edit_audio": "Edit Audio",
    "edit_cover": "Edit Cover",
    "content_id_claim": "Pengajuan YouTube Content ID",
    "content_id_release": "Cabut YouTube Content ID",
    "royalty_issue": "Masalah Royalti",
    "other": "Lainnya",
}

# Statuses that block label cancel (admin must process manually)
TICKET_NON_CANCELLABLE = {"done", "submitted_to_believe", "rejected", "cancelled"}


async def _ticket_visible_to(user: dict, ticket: dict) -> bool:
    if user["role"] in ADMIN_ROLES:
        return True
    if user["role"] == LABEL_ROLE:
        label = await db.labels.find_one({"user_id": user["id"]}, {"_id": 0, "id": 1})
        return bool(label) and ticket.get("label_id") == label["id"]
    return False


@ticket_r.get("/categories")
async def list_ticket_categories(user: dict = Depends(require_kyc_for_label_user)):
    return [{"value": k, "label": v} for k, v in TICKET_CATEGORY_LABELS.items()]


@ticket_r.post("/upload-attachment")
async def upload_ticket_attachment(
    file: UploadFile = File(...),
    purpose: str = Form("general"),  # general | audio | cover
    user: dict = Depends(require_kyc_for_label_user),
):
    """Upload attachment for ticket (audio WAV for edit_audio, cover for edit_cover, or generic attachment)."""
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


@ticket_r.post("/label/create")
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

    # Category-specific validation
    if body.category == "edit_audio":
        if not body.new_audio_url:
            raise HTTPException(status_code=400, detail="Upload file WAV baru wajib untuk edit audio")
        if not body.new_audio_track_id:
            raise HTTPException(status_code=400, detail="Pilih track yang ingin di-edit audionya")
    elif body.category == "edit_cover":
        if not body.new_cover_url:
            raise HTTPException(status_code=400, detail="Upload cover baru 3000x3000 wajib untuk edit cover")
    elif body.category == "edit_metadata":
        if not body.new_metadata:
            raise HTTPException(status_code=400, detail="Metadata baru wajib diisi")
        if not body.reason:
            raise HTTPException(status_code=400, detail="Alasan perubahan wajib diisi")
    elif body.category == "takedown":
        if not body.reason:
            raise HTTPException(status_code=400, detail="Alasan takedown wajib diisi")
    elif body.category == "content_id_claim":
        if not body.originality_declared:
            raise HTTPException(status_code=400, detail="Pernyataan originalitas wajib disetujui")
        parsed_youtube = urlparse(body.youtube_url or "")
        if parsed_youtube.scheme != "https" or parsed_youtube.netloc.lower().removeprefix("www.") not in {"youtube.com", "youtu.be", "music.youtube.com"}:
            raise HTTPException(status_code=400, detail="Link YouTube valid wajib diisi untuk pengajuan Content ID")

    ticket_id = new_id()
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
    }
    await db.support_tickets.insert_one(doc)
    # Seed first comment with the description so it's visible in chat
    await db.ticket_comments.insert_one({
        "id": new_id(),
        "ticket_id": ticket_id,
        "user_id": user["id"],
        "user_name": user.get("name"),
        "role": LABEL_ROLE,
        "body": body.description,
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
    return doc


@ticket_r.get("/label")
async def label_list_tickets(user: dict = Depends(require_label), status: Optional[str] = None):
    label = await get_label_by_user(user)
    filt: Dict[str, Any] = {"label_id": label["id"]}
    if status:
        filt["status"] = status
    items = await db.support_tickets.find(filt, {"_id": 0}).sort("created_at", -1).to_list(500)
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
    if user["role"] in ADMIN_ROLES and ticket["status"] in ("open", "waiting_admin", "in_progress"):
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
    return await db.support_tickets.find_one({"id": ticket_id}, {"_id": 0})


@ticket_r.post("/admin/{ticket_id}/status")
async def admin_update_ticket(ticket_id: str, body: TicketAdminUpdateIn, user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_support", "admin_release"):
        raise HTTPException(status_code=403, detail="Hanya Admin Support / Release / Super Admin")
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
    actor_is_admin = actor.get("role") in ADMIN_ROLES
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



