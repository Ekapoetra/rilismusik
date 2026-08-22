"""Releases & track upload router."""
from fastapi import APIRouter, HTTPException, Request, Response, Depends, UploadFile, File, Form, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta, date
import os
import csv
import io
import shutil
import secrets

from .deps import (
    db, logger, UPLOAD_DIR,
    get_current_user, require_label, require_artist, require_admin, require_super_admin,
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
from payment_service import create_payment_document, payment_price

# =============================================================================
#                              RELEASES
# =============================================================================
release_r = APIRouter(prefix="/releases", tags=["releases"])


@release_r.get("/")
async def list_releases(
    user: dict = Depends(get_current_user),
    status: Optional[str] = None,
    q: Optional[str] = None,
    period_from: Optional[str] = Query(None, description="Inclusive YYYY-MM"),
    period_to: Optional[str] = Query(None, description="Inclusive YYYY-MM"),
):
    filt: Dict[str, Any] = {}
    if user["role"] == LABEL_ROLE:
        label = await get_label_by_user(user)
        filt["label_id"] = label["id"]
    elif user["role"] == ARTIST_ROLE:
        # Artists can only see releases via tracks they're linked to
        tracks = await db.tracks.find({"artist_id": user["id"]}, {"release_id": 1, "_id": 0}).to_list(1000)
        release_ids = list({t["release_id"] for t in tracks})
        filt["id"] = {"$in": release_ids}
    if status:
        filt["status"] = status
    if q:
        filt["release_title"] = {"$regex": q, "$options": "i"}
    items = await db.releases.find(filt, {"_id": 0}).sort("created_at", -1).to_list(500)
    # Phase 21: enrich with revenue rollup + last_active_period
    from .revenue_rollup import rollup_revenue_by_id
    rollup = await rollup_revenue_by_id(
        field="release_id",
        ids=[i["id"] for i in items],
        period_from=period_from,
        period_to=period_to,
    )
    for it in items:
        r = rollup.get(it["id"], {})
        it["revenue_eur"] = r.get("revenue_eur", 0)
        it["revenue_idr"] = r.get("revenue_idr", 0)
        it["royalty_lines_count"] = r.get("lines", 0)
        it["last_active_period"] = r.get("last_period")
        it["first_active_period"] = r.get("first_period")
    return items


@release_r.get("/{release_id}")
async def get_release(release_id: str, user: dict = Depends(get_current_user)):
    rel = await db.releases.find_one({"id": release_id}, {"_id": 0})
    if not rel:
        raise HTTPException(status_code=404, detail="Rilisan tidak ditemukan")
    if user["role"] == LABEL_ROLE:
        label = await get_label_by_user(user)
        if rel["label_id"] != label["id"]:
            raise HTTPException(status_code=403, detail="Bukan rilisan Anda")
    tracks = await db.tracks.find({"release_id": release_id}, {"_id": 0}).sort("track_number", 1).to_list(200)
    return {**rel, "tracks": tracks}


@release_r.post("/draft")
async def create_release_draft(body: ReleaseDraftIn, user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    if label.get("account_status") in ("suspended", "blacklisted"):
        raise HTTPException(status_code=403, detail="Akun tidak dapat membuat rilisan")
    if label.get("contract_status") == "contract_expired":
        raise HTTPException(status_code=403, detail="Kontrak expired - tidak bisa submit rilisan baru")

    # validate release date >= today+7
    try:
        rdate = date.fromisoformat(body.release_date)
    except Exception:
        raise HTTPException(status_code=400, detail="Tanggal rilis tidak valid")
    if rdate < (date.today() + timedelta(days=7)):
        raise HTTPException(status_code=400, detail="Tanggal rilis minimal 7 hari setelah hari ini")

    release_id = new_id()
    rel = {
        "id": release_id,
        "label_id": label["id"],
        "release_title": body.release_title,
        "release_type": body.release_type,
        "artist_name": body.artist_name,
        "release_date": body.release_date,
        "year": body.year or rdate.year,
        "genre": body.genre,
        "subgenre": body.subgenre,
        "language": body.language,
        "explicit": body.explicit,
        "copyright_line": body.copyright_line,
        "p_line": body.p_line,
        "platforms": body.platforms,
        "notes": body.notes,
        "cover_url": None,
        "upc": None,
        "status": "draft",
        "payment_status": "none",  # none, pending, paid, free_subscription
        "payment_id": None,
        "contract_declaration_checked": False,
        "admin_note": None,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.releases.insert_one(rel)

    # tracks
    for idx, t in enumerate(body.tracks, start=1):
        t_doc = {
            "id": new_id(),
            "release_id": release_id,
            "label_id": label["id"],
            "artist_id": t.artist_id,
            "track_title": t.track_title,
            "track_number": t.track_number or idx,
            "artist_name": t.artist_name,
            "composer": t.composer,
            "lyricist": t.lyricist,
            "producer": t.producer,
            "arranger": t.arranger,
            "performer": t.performer,
            "genre": t.genre,
            "language": t.language,
            "explicit": t.explicit,
            "audio_url": t.audio_url,
            "isrc": t.isrc,
            "status": "draft",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        await db.tracks.insert_one(t_doc)
    await log_activity(user["id"], "create_draft", "release", release_id)
    return await db.releases.find_one({"id": release_id}, {"_id": 0})


@release_r.patch("/{release_id}")
async def update_release(release_id: str, body: ReleaseDraftIn, user: dict = Depends(require_label)):
    rel = await db.releases.find_one({"id": release_id})
    if not rel:
        raise HTTPException(status_code=404, detail="Rilisan tidak ditemukan")
    label = await get_label_by_user(user)
    if rel["label_id"] != label["id"]:
        raise HTTPException(status_code=403, detail="Bukan rilisan Anda")
    if rel["status"] not in ("draft", "need_revision"):
        raise HTTPException(status_code=400, detail="Rilisan tidak dapat diedit pada status saat ini")

    try:
        rdate = date.fromisoformat(body.release_date)
    except Exception:
        raise HTTPException(status_code=400, detail="Tanggal rilis tidak valid")
    if rdate < (date.today() + timedelta(days=7)):
        raise HTTPException(status_code=400, detail="Tanggal rilis minimal 7 hari setelah hari ini")

    upd = {
        "release_title": body.release_title,
        "release_type": body.release_type,
        "artist_name": body.artist_name,
        "release_date": body.release_date,
        "year": body.year or rdate.year,
        "genre": body.genre,
        "subgenre": body.subgenre,
        "language": body.language,
        "explicit": body.explicit,
        "copyright_line": body.copyright_line,
        "p_line": body.p_line,
        "platforms": body.platforms,
        "notes": body.notes,
        "updated_at": now_iso(),
    }
    await db.releases.update_one({"id": release_id}, {"$set": upd})

    # replace tracks (simplest approach for MVP)
    await db.tracks.delete_many({"release_id": release_id})
    for idx, t in enumerate(body.tracks, start=1):
        t_doc = {
            "id": new_id(),
            "release_id": release_id,
            "label_id": label["id"],
            "artist_id": t.artist_id,
            "track_title": t.track_title,
            "track_number": t.track_number or idx,
            "artist_name": t.artist_name,
            "composer": t.composer,
            "lyricist": t.lyricist,
            "producer": t.producer,
            "arranger": t.arranger,
            "performer": t.performer,
            "genre": t.genre,
            "language": t.language,
            "explicit": t.explicit,
            "audio_url": t.audio_url,
            "isrc": t.isrc,
            "status": "draft",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        await db.tracks.insert_one(t_doc)

    await log_activity(user["id"], "update_release", "release", release_id)
    return await db.releases.find_one({"id": release_id}, {"_id": 0})


@release_r.post("/{release_id}/upload-cover")
async def upload_cover(release_id: str, file: UploadFile = File(...), user: dict = Depends(require_label)):
    rel = await db.releases.find_one({"id": release_id})
    if not rel:
        raise HTTPException(status_code=404, detail="Rilisan tidak ditemukan")
    label = await get_label_by_user(user)
    if rel["label_id"] != label["id"]:
        raise HTTPException(status_code=403, detail="Bukan rilisan Anda")
    if rel["status"] not in ("draft", "need_revision"):
        raise HTTPException(status_code=400, detail="Cover hanya bisa diubah pada status draft/need_revision")
    ext = (file.filename or "").lower().split(".")[-1]
    if ext not in ("jpg", "jpeg", "png"):
        raise HTTPException(status_code=400, detail="Format cover harus JPG/PNG")

    # Validate 3000x3000 square. Use Pillow if available; else skip dimension check.
    file_bytes = await file.read()
    try:
        from PIL import Image
        from io import BytesIO
        img = Image.open(BytesIO(file_bytes))
        w, h = img.size
        if w != h:
            raise HTTPException(status_code=400, detail="Cover harus square (rasio 1:1)")
        if w < 3000 or h < 3000:
            raise HTTPException(status_code=400, detail="Resolusi cover minimal 3000x3000 px")
    except ImportError:
        pass  # Pillow not installed; rely on size check by client

    import storage_service
    key = f"cover/{release_id}.{ext}"
    content_type = "image/png" if ext == "png" else "image/jpeg"
    await storage_service.upload_bytes(key=key, data=file_bytes, content_type=content_type)
    url = f"/api/files/{key}"
    await db.releases.update_one({"id": release_id}, {"$set": {"cover_url": url, "updated_at": now_iso()}})
    return {"cover_url": url}


@release_r.post("/{release_id}/upload-audio")
async def upload_audio(release_id: str, track_id: str = Form(...), file: UploadFile = File(...), user: dict = Depends(require_label)):
    rel = await db.releases.find_one({"id": release_id})
    if not rel:
        raise HTTPException(status_code=404, detail="Rilisan tidak ditemukan")
    label = await get_label_by_user(user)
    if rel["label_id"] != label["id"]:
        raise HTTPException(status_code=403, detail="Bukan rilisan Anda")
    if rel["status"] not in ("draft", "need_revision"):
        raise HTTPException(status_code=400, detail="Audio hanya bisa diupload pada status draft/need_revision")
    track = await db.tracks.find_one({"id": track_id, "release_id": release_id})
    if not track:
        raise HTTPException(status_code=404, detail="Track tidak ditemukan")
    name = (file.filename or "").lower()
    if not name.endswith(".wav"):
        raise HTTPException(status_code=400, detail="Audio harus berformat WAV")

    import storage_service
    key = f"audio/{track_id}.wav"
    # Use multipart-aware upload for large WAV files (boto3 auto-chunks >8MB)
    await storage_service.upload_fileobj(key=key, fileobj=file.file, content_type="audio/wav")
    url = f"/api/files/{key}"
    await db.tracks.update_one({"id": track_id}, {"$set": {"audio_url": url, "updated_at": now_iso()}})
    return {"audio_url": url}


@release_r.post("/{release_id}/submit")
async def submit_release(release_id: str, body: ReleaseSubmitConfirmation, user: dict = Depends(require_label)):
    rel = await db.releases.find_one({"id": release_id})
    if not rel:
        raise HTTPException(status_code=404, detail="Rilisan tidak ditemukan")
    label = await get_label_by_user(user)
    if rel["label_id"] != label["id"]:
        raise HTTPException(status_code=403, detail="Bukan rilisan Anda")
    if rel["status"] not in ("draft", "need_revision"):
        raise HTTPException(status_code=400, detail="Status saat ini tidak dapat disubmit")
    if not body.contract_declaration_checked:
        raise HTTPException(status_code=400, detail="Deklarasi hak cipta harus disetujui")

    # validate completeness
    if not rel.get("cover_url"):
        raise HTTPException(status_code=400, detail="Cover belum diupload")
    tracks = await db.tracks.find({"release_id": release_id}).to_list(200)
    if not tracks:
        raise HTTPException(status_code=400, detail="Rilisan harus memiliki minimal 1 track")
    for t in tracks:
        if not t.get("audio_url"):
            raise HTTPException(status_code=400, detail=f"Audio belum diupload untuk track '{t['track_title']}'")

    # release date >= today+7 again (safety)
    try:
        rdate = date.fromisoformat(rel["release_date"])
    except Exception:
        raise HTTPException(status_code=400, detail="Tanggal rilis tidak valid")
    if rdate < (date.today() + timedelta(days=7)):
        raise HTTPException(status_code=400, detail="Tanggal rilis minimal 7 hari dari hari ini, mohon update")

    # Determine payment flow
    now = datetime.now(timezone.utc)
    is_subscribed = False
    if label.get("subscription_status") == "active" and label.get("subscription_expires_at"):
        try:
            expires = datetime.fromisoformat(label["subscription_expires_at"])
            if expires > now:
                is_subscribed = True
        except Exception:
            is_subscribed = False

    if is_subscribed:
        new_status = "under_review"
        payment_status = "free_subscription"
        payment_id = None
    else:
        new_status = "awaiting_payment"
        amount = await payment_price("pay_per_release")
        invoice_doc = await create_payment_document(
            label_id=label["id"], payment_type="pay_per_release", amount=amount,
            release_id=release_id,
            description=f"Distribusi rilisan — {rel.get('release_title')}",
            return_path=f"/label/releases/{release_id}",
        )
        payment_status = "pending"
        payment_id = invoice_doc["id"]

    await db.releases.update_one(
        {"id": release_id},
        {"$set": {
            "status": new_status,
            "payment_status": payment_status,
            "payment_id": payment_id,
            "contract_declaration_checked": True,
            "updated_at": now_iso(),
        }},
    )
    await log_activity(user["id"], "submit_release", "release", release_id, after={"status": new_status})
    return await db.releases.find_one({"id": release_id}, {"_id": 0})


@release_r.post("/{release_id}/admin/action")
async def admin_release_action(release_id: str, body: AdminReleaseAction, user: dict = Depends(require_admin)):
    rel = await db.releases.find_one({"id": release_id})
    if not rel:
        raise HTTPException(status_code=404, detail="Rilisan tidak ditemukan")

    # Admin Release / Super Admin only for review actions
    if user["role"] not in ("super_admin", "admin_release"):
        raise HTTPException(status_code=403, detail="Hanya Admin Release atau Super Admin")

    if rel["payment_status"] == "pending" and body.action in ("approve", "deliver", "mark_live"):
        raise HTTPException(status_code=400, detail="Invoice belum dibayar, rilisan tidak bisa diproses")

    action_to_status = {
        "approve": "approved",
        "need_revision": "need_revision",
        "reject": "rejected",
        "deliver": "delivered",
        "mark_live": "live",
        "takedown": "taken_down",
    }
    new_status = action_to_status[body.action]
    upd = {"status": new_status, "updated_at": now_iso()}
    if body.action in ("need_revision", "reject") and body.note:
        upd["admin_note"] = body.note
    if body.upc:
        upd["upc"] = body.upc
    await db.releases.update_one({"id": release_id}, {"$set": upd})
    if body.isrc:
        # apply to first track if only one provided
        await db.tracks.update_many({"release_id": release_id}, {"$set": {"isrc": body.isrc}})
    await log_activity(user["id"], f"admin_{body.action}", "release", release_id, before={"status": rel["status"]}, after={"status": new_status})
    # Notify label
    label_uids = await label_user_ids(rel["label_id"])
    titles = {
        "approve": ("Rilisan disetujui ✓", f"'{rel.get('release_title')}' telah disetujui."),
        "need_revision": ("Rilisan perlu revisi", f"'{rel.get('release_title')}' perlu revisi. {body.note or ''}"),
        "reject": ("Rilisan ditolak", f"'{rel.get('release_title')}' ditolak. {body.note or ''}"),
        "deliver": ("Rilisan didistribusikan", f"'{rel.get('release_title')}' sedang didistribusikan ke DSP."),
        "mark_live": ("Rilisan LIVE 🎉", f"'{rel.get('release_title')}' sudah live di platform."),
        "takedown": ("Rilisan di-takedown", f"'{rel.get('release_title')}' telah di-takedown."),
    }
    if body.action in titles:
        t, msg = titles[body.action]
        await notify_many(label_uids, f"release_{body.action}", t, msg, f"/label/releases/{release_id}", {"release_id": release_id})
    return await db.releases.find_one({"id": release_id}, {"_id": 0})


