"""Releases & track upload router."""
from fastapi import APIRouter, HTTPException, Request, Response, Depends, UploadFile, File, Form, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta, date
import os
import csv
import io
import shutil
import secrets
import asyncio
import wave

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
from payment_service import PaymentCreateData, create_payment_document, payment_price
from email_service import send_release_invoice_email, send_release_submission_email
from .release_workflow_service import (
    EDITABLE_STATUSES, normalize_artist_credits, require_status,
    validate_artist_web_url, validate_release_date, validate_release_submission,
)
from .artist_social_service import resolve_release_artist_credits

# =============================================================================
#                              RELEASES
# =============================================================================
release_r = APIRouter(prefix="/releases", tags=["releases"])


@release_r.get("/")
async def list_releases(
    user: dict = Depends(require_kyc_for_label_user),
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
async def get_release(release_id: str, user: dict = Depends(require_kyc_for_label_user)):
    rel = await db.releases.find_one({"id": release_id}, {"_id": 0})
    if not rel:
        raise HTTPException(status_code=404, detail="Rilisan tidak ditemukan")
    if user["role"] == LABEL_ROLE:
        label = await get_label_by_user(user)
        if rel["label_id"] != label["id"]:
            raise HTTPException(status_code=403, detail="Bukan rilisan Anda")
    tracks = await db.tracks.find({"release_id": release_id}, {"_id": 0}).sort("track_number", 1).to_list(200)
    payment = None
    if rel.get("payment_id"):
        payment = await db.payments.find_one({"id": rel["payment_id"]}, {"_id": 0})
    label_doc = await db.labels.find_one({"id": rel.get("label_id")}, {"_id": 0, "whatsapp": 1})
    return {**rel, "tracks": tracks, "payment": payment, "label_whatsapp": rel.get("label_whatsapp_snapshot") or (label_doc or {}).get("whatsapp")}


@release_r.get("/{release_id}/copyright-letter")
async def download_copyright_letter(release_id: str, user: dict = Depends(require_kyc_for_label_user)):
    rel = await db.releases.find_one({"id": release_id}, {"_id": 0})
    if not rel:
        raise HTTPException(status_code=404, detail="Rilisan tidak ditemukan")
    if user["role"] == LABEL_ROLE:
        label = await get_label_by_user(user)
        if rel.get("label_id") != label["id"]:
            raise HTTPException(status_code=403, detail="Tidak diizinkan")
    elif user["role"] not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Tidak diizinkan")
    if rel.get("status") not in {"approved", "delivered", "live"}:
        raise HTTPException(status_code=409, detail="Surat hak cipta tersedia setelah rilisan disetujui")
    document_setting = await db.landing_settings.find_one({"key": "documents"}, {"_id": 0, "value": 1})
    legal_setting = await db.landing_settings.find_one({"key": "legal_entity"}, {"_id": 0, "value": 1})
    documents = (document_setting or {}).get("value") or {}
    signature_url = documents.get("signature_url")
    if not signature_url or "/api/files/" not in signature_url:
        raise HTTPException(status_code=400, detail="Tanda tangan penanggung jawab belum diunggah di CMS")
    import storage_service
    signature_key = signature_url.split("/api/files/", 1)[1]
    signature_bytes = await storage_service.download_bytes(key=signature_key)
    stamp_bytes = None
    stamp_url = documents.get("stamp_url")
    if stamp_url and "/api/files/" in stamp_url:
        stamp_bytes = await storage_service.download_bytes(key=stamp_url.split("/api/files/", 1)[1])
    tracks = await db.tracks.find({"release_id": release_id}, {"_id": 0}).sort("track_number", 1).to_list(500)
    label_doc = await db.labels.find_one({"id": rel.get("label_id")}, {"_id": 0, "label_name": 1})
    enriched_release = {**rel, "label_name": (label_doc or {}).get("label_name")}
    from .copyright_generator import generate_copyright_pdf_bytes
    pdf_bytes = generate_copyright_pdf_bytes(
        release=enriched_release, tracks=tracks,
        legal_entity=(legal_setting or {}).get("value") or {}, document_settings=documents,
        signature_bytes=signature_bytes, stamp_bytes=stamp_bytes,
    )
    pdf_key = f"copyright/{release_id}.pdf"
    try:
        await storage_service.delete_object(key=pdf_key)
        await storage_service.upload_bytes(key=pdf_key, data=pdf_bytes, content_type="application/pdf")
        await db.releases.update_one({"id": release_id}, {"$set": {"copyright_pdf_url": f"/api/files/{pdf_key}", "copyright_pdf_generated_at": now_iso()}})
    except Exception as exc:
        logger.warning("Copyright PDF persistence failed release=%s: %s", release_id, exc)
    safe_title = "".join(char for char in (rel.get("release_title") or release_id) if char.isalnum() or char in "-_ ").strip().replace(" ", "-")
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Surat-Hak-Cipta-{safe_title}.pdf"'},
    )


@release_r.post("/draft")
async def create_release_draft(body: ReleaseDraftIn, user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    if label.get("account_status") in ("suspended", "blacklisted"):
        raise HTTPException(status_code=403, detail="Akun tidak dapat membuat rilisan")
    if label.get("contract_status") == "contract_expired":
        raise HTTPException(status_code=403, detail="Kontrak expired - tidak bisa submit rilisan baru")

    # validate release date >= today+7
    rdate = validate_release_date(body.release_date)
    primary_artists = normalize_artist_credits(body.primary_artists, body.artist_name)
    featured_artists = normalize_artist_credits(body.featured_artists)
    validate_artist_web_url(body.artist_web_url)

    release_id = new_id()
    rel = {
        "id": release_id,
        "label_id": label["id"],
        "release_title": body.release_title,
        "release_type": body.release_type,
        "artist_name": ", ".join(item["name"] for item in primary_artists),
        "primary_artists": primary_artists,
        "featured_artists": featured_artists,
        "artist_web_url": str(body.artist_web_url or "").strip() or None,
        "label_name_snapshot": label.get("label_name"),
        "responsible_name": user.get("name") or label.get("pic_name"),
        "label_whatsapp_snapshot": label.get("whatsapp"),
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
            "preview_start_seconds": t.preview_start_seconds,
            "title_language": t.title_language,
            "lyric_language": t.lyric_language,
            "track_type": t.track_type,
            "featuring_artist_id": t.featuring_artist_id,
            "featuring_artist_name": t.featuring_artist_name,
            "spotify_artist_id": t.spotify_artist_id,
            "youtube_artist_id": t.youtube_artist_id,
            "lyrics": t.lyrics,
            "vocal_type": t.vocal_type,
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
    if rel["status"] not in EDITABLE_STATUSES:
        raise HTTPException(status_code=400, detail="Rilisan tidak dapat diedit pada status saat ini")

    rdate = validate_release_date(body.release_date)
    primary_artists = normalize_artist_credits(body.primary_artists, body.artist_name)
    featured_artists = normalize_artist_credits(body.featured_artists)
    validate_artist_web_url(body.artist_web_url)

    upd = {
        "release_title": body.release_title,
        "release_type": body.release_type,
        "artist_name": ", ".join(item["name"] for item in primary_artists),
        "primary_artists": primary_artists,
        "featured_artists": featured_artists,
        "artist_web_url": str(body.artist_web_url or "").strip() or None,
        "label_name_snapshot": label.get("label_name"),
        "responsible_name": user.get("name") or label.get("pic_name"),
        "label_whatsapp_snapshot": label.get("whatsapp"),
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

    existing_tracks = {
        item["id"]: item for item in await db.tracks.find(
            {"release_id": release_id}, {"_id": 0},
        ).to_list(500)
    }
    retained_ids = []
    for idx, t in enumerate(body.tracks, start=1):
        existing = existing_tracks.get(t.id) if t.id else None
        track_id = (existing or {}).get("id") or new_id()
        retained_ids.append(track_id)
        t_doc = {
            "id": track_id,
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
            "audio_url": t.audio_url or (existing or {}).get("audio_url"),
            "audio_filename": (existing or {}).get("audio_filename"),
            "audio_sample_rate": (existing or {}).get("audio_sample_rate"),
            "isrc": t.isrc or (existing or {}).get("isrc"),
            "preview_start_seconds": t.preview_start_seconds,
            "title_language": t.title_language,
            "lyric_language": t.lyric_language,
            "track_type": t.track_type,
            "featuring_artist_id": t.featuring_artist_id,
            "featuring_artist_name": t.featuring_artist_name,
            "spotify_artist_id": t.spotify_artist_id,
            "youtube_artist_id": t.youtube_artist_id,
            "lyrics": t.lyrics,
            "vocal_type": t.vocal_type,
            "status": "draft",
            "created_at": (existing or {}).get("created_at") or now_iso(),
            "updated_at": now_iso(),
        }
        await db.tracks.replace_one({"id": track_id, "release_id": release_id}, t_doc, upsert=True)
    await db.tracks.delete_many({"release_id": release_id, "id": {"$nin": retained_ids}})

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
    if rel["status"] not in EDITABLE_STATUSES:
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
        if w != 3000 or h != 3000:
            raise HTTPException(status_code=400, detail="Cover harus tepat 3000x3000 px")
    except ImportError:
        pass  # Pillow not installed; rely on size check by client

    import storage_service
    key = f"cover/{release_id}.{ext}"
    content_type = "image/png" if ext == "png" else "image/jpeg"
    await storage_service.upload_bytes(key=key, data=file_bytes, content_type=content_type)
    url = f"/api/files/{key}"
    await db.releases.update_one({"id": release_id}, {"$set": {
        "cover_url": url, "cover_width": 3000, "cover_height": 3000,
        "cover_content_type": content_type, "updated_at": now_iso(),
    }})
    return {"cover_url": url, "width": 3000, "height": 3000}


@release_r.post("/{release_id}/upload-audio")
async def upload_audio(release_id: str, track_id: str = Form(...), file: UploadFile = File(...), user: dict = Depends(require_label)):
    rel = await db.releases.find_one({"id": release_id})
    if not rel:
        raise HTTPException(status_code=404, detail="Rilisan tidak ditemukan")
    label = await get_label_by_user(user)
    if rel["label_id"] != label["id"]:
        raise HTTPException(status_code=403, detail="Bukan rilisan Anda")
    if rel["status"] not in EDITABLE_STATUSES:
        raise HTTPException(status_code=400, detail="Audio hanya bisa diupload pada status draft/need_revision")
    track = await db.tracks.find_one({"id": track_id, "release_id": release_id})
    if not track:
        raise HTTPException(status_code=404, detail="Track tidak ditemukan")
    name = (file.filename or "").lower()
    if not name.endswith(".wav"):
        raise HTTPException(status_code=400, detail="Audio harus berformat WAV")
    try:
        file.file.seek(0)
        with wave.open(file.file, "rb") as wav:
            sample_rate = int(wav.getframerate())
            if sample_rate not in (44100, 48000):
                raise HTTPException(status_code=400, detail="Sample rate audio harus 44,1 kHz atau 48 kHz")
    except HTTPException:
        raise
    except (wave.Error, EOFError):
        raise HTTPException(status_code=400, detail="File WAV tidak valid")
    finally:
        file.file.seek(0)

    import storage_service
    key = f"audio/{track_id}.wav"
    # Use multipart-aware upload for large WAV files (boto3 auto-chunks >8MB)
    await storage_service.upload_fileobj(key=key, fileobj=file.file, content_type="audio/wav")
    url = f"/api/files/{key}"
    await db.tracks.update_one({"id": track_id}, {"$set": {
        "audio_url": url, "audio_filename": file.filename,
        "audio_sample_rate": sample_rate, "updated_at": now_iso(),
    }})
    return {"audio_url": url, "sample_rate": sample_rate}


@release_r.post("/{release_id}/submit")
async def submit_release(release_id: str, body: ReleaseSubmitConfirmation, user: dict = Depends(require_label)):
    rel = await db.releases.find_one({"id": release_id})
    if not rel:
        raise HTTPException(status_code=404, detail="Rilisan tidak ditemukan")
    label = await get_label_by_user(user)
    if rel["label_id"] != label["id"]:
        raise HTTPException(status_code=403, detail="Bukan rilisan Anda")
    if rel["status"] not in EDITABLE_STATUSES:
        raise HTTPException(status_code=400, detail="Status saat ini tidak dapat disubmit")
    if not body.contract_declaration_checked:
        raise HTTPException(status_code=400, detail="Deklarasi hak cipta harus disetujui")

    tracks = await db.tracks.find({"release_id": release_id}, {"_id": 0}).sort("track_number", 1).to_list(200)
    validate_release_submission(rel, tracks)
    all_credits = list(rel.get("primary_artists") or []) + list(rel.get("featured_artists") or [])
    resolved_credits = await resolve_release_artist_credits(db, label["id"], all_credits)
    primary_count = len(rel.get("primary_artists") or [])
    resolved_primary = resolved_credits[:primary_count]
    resolved_featured = resolved_credits[primary_count:]
    resolved_artist_name = ", ".join(item["name"] for item in resolved_primary)
    await db.releases.update_one({"id": release_id}, {"$set": {
        "primary_artists": resolved_primary,
        "featured_artists": resolved_featured,
        "artist_name": resolved_artist_name,
        "label_whatsapp_snapshot": label.get("whatsapp"),
    }})
    rel = {**rel, "primary_artists": resolved_primary, "featured_artists": resolved_featured, "artist_name": resolved_artist_name}

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

    selected_addons = []
    addon_ids = list(dict.fromkeys(body.addon_product_ids))
    if addon_ids:
        selected_addons = await db.payment_products.find(
            {"id": {"$in": addon_ids}, "active": True}, {"_id": 0, "id": 1, "name": 1, "description": 1, "amount": 1},
        ).to_list(200)
        if len(selected_addons) != len(addon_ids):
            raise HTTPException(status_code=400, detail="Salah satu layanan tambahan tidak tersedia")

    if is_subscribed:
        if selected_addons:
            raise HTTPException(status_code=400, detail="Layanan tambahan gabungan saat submit hanya tersedia untuk Pay Per Release")
        new_status = "submitted"
        payment_status = "free_subscription"
        billing_flow = "subscription"
        payment_id = None
        base_amount = 0
    else:
        new_status = "submitted"
        base_amount = await payment_price("pay_per_release")
        payment_status = "not_generated"
        billing_flow = "pay_per_release"
        payment_id = None

    await db.releases.update_one(
        {"id": release_id},
        {"$set": {
            "status": new_status,
            "payment_status": payment_status,
            "payment_id": payment_id,
            "ppr_base_amount": base_amount,
            "selected_addons": selected_addons,
            "selected_addon_product_ids": addon_ids,
            "billing_flow": billing_flow,
            "submitted_at": now_iso(),
            "contract_declaration_checked": True,
            "admin_note": None,
            "updated_at": now_iso(),
        }, "$push": {"status_history": {
            "from": rel.get("status"), "to": "submitted", "changed_by": user["id"],
            "changed_at": now_iso(), "note": "Submit ulang setelah revisi" if rel.get("status") == "need_revision" else "Submit pertama",
        }}},
    )
    await log_activity(user["id"], "submit_release", "release", release_id, after={"status": new_status})
    admin_ids = await admin_user_ids(("super_admin", "admin_release"))
    await notify_many(
        admin_ids, "release_submitted", "Rilisan baru menunggu review",
        f"{label.get('label_name')} mengirim '{rel.get('release_title')}'.",
        f"/admin/releases/{release_id}", {"release_id": release_id},
    )
    admin_emails = await db.users.find(
        {"id": {"$in": admin_ids}, "status": {"$nin": ["disabled", "suspended"]}},
        {"_id": 0, "email": 1},
    ).to_list(100)
    for admin_doc in admin_emails:
        if admin_doc.get("email"):
            asyncio.create_task(send_release_submission_email(
                to=admin_doc["email"], label_name=label.get("label_name") or "Label",
                release_title=rel.get("release_title") or "Rilisan", release_id=release_id,
            ))
    return await db.releases.find_one({"id": release_id}, {"_id": 0})


@release_r.post("/{release_id}/admin/action")
async def admin_release_action(release_id: str, body: AdminReleaseAction, user: dict = Depends(require_admin)):
    rel = await db.releases.find_one({"id": release_id})
    if not rel:
        raise HTTPException(status_code=404, detail="Rilisan tidak ditemukan")

    # Admin Release / Super Admin only for review actions
    if user["role"] not in ("super_admin", "admin_release"):
        raise HTTPException(status_code=403, detail="Hanya Admin Release atau Super Admin")

    billing_flow = rel.get("billing_flow") or (
        "pay_per_release" if rel.get("payment_status") in ("not_generated", "pending", "paid") else "subscription"
    )
    if body.action == "start_review":
        require_status(rel, ("submitted",), "Mulai pemeriksaan")
        new_status = "under_review"
    elif body.action == "send_payment":
        if rel.get("status") == "awaiting_payment" and rel.get("payment_id"):
            return await db.releases.find_one({"id": release_id}, {"_id": 0})
        require_status(rel, ("under_review",), "Kirim tautan pembayaran")
        if billing_flow != "pay_per_release" or rel.get("payment_status") != "not_generated":
            raise HTTPException(status_code=409, detail="Rilisan ini tidak memerlukan invoice Pay Per Release")
        base_amount = int(await payment_price("pay_per_release"))
        selected_addons = rel.get("selected_addons") or []
        addon_amount = sum(int(item.get("amount") or 0) for item in selected_addons)
        total_amount = base_amount + addon_amount
        line_items = [{
            "reference_id": f"release-base-{release_id}",
            "name": "Biaya Distribusi Pay Per Release",
            "description": rel.get("release_title"),
            "amount": base_amount, "quantity": 1,
        }] + [{
            "reference_id": f"addon-{item['id']}",
            "name": item.get("name") or "Layanan Tambahan",
            "description": item.get("description"),
            "amount": int(item.get("amount") or 0), "quantity": 1,
        } for item in selected_addons]
        invoice_doc = await create_payment_document(PaymentCreateData(
            label_id=rel["label_id"], payment_type="pay_per_release", amount=total_amount,
            release_id=release_id, description=f"Distribusi rilisan — {rel.get('release_title')}",
            return_path=f"/label/releases/{release_id}", reference_id=f"ppr-release-{release_id}",
            line_items=line_items, base_amount=base_amount, addon_amount=addon_amount,
            addon_product_ids=[item["id"] for item in selected_addons],
            approval_required_before_payment=True,
        ))
        await db.releases.update_one({"id": release_id}, {"$set": {
            "status": "awaiting_payment", "payment_status": "pending", "payment_id": invoice_doc["id"],
            "metadata_validated_at": now_iso(), "metadata_validated_by": user["id"], "updated_at": now_iso(),
        }, "$push": {"status_history": {
            "from": rel.get("status"), "to": "awaiting_payment", "changed_by": user["id"],
            "changed_at": now_iso(), "note": "Metadata valid; invoice dikirim",
        }}})
        await log_activity(user["id"], "admin_send_ppr_invoice", "release", release_id, before={"status": rel.get("status")}, after={"status": "awaiting_payment", "payment_id": invoice_doc["id"], "amount": total_amount})
        await notify_many(
            await label_user_ids(rel["label_id"]), "release_invoice_ready", "Metadata valid — invoice tersedia",
            f"Metadata '{rel.get('release_title')}' telah valid. Selesaikan pembayaran invoice gabungan Rp {total_amount:,.0f}.",
            f"/label/releases/{release_id}", {"release_id": release_id, "payment_id": invoice_doc["id"]},
        )
        label_doc = await db.labels.find_one({"id": rel["label_id"]}, {"_id": 0, "label_name": 1, "user_id": 1})
        label_user = await db.users.find_one({"id": (label_doc or {}).get("user_id")}, {"_id": 0, "email": 1})
        if label_user and label_user.get("email"):
            asyncio.create_task(send_release_invoice_email(
                to=label_user["email"], label_name=(label_doc or {}).get("label_name") or "Label",
                release_title=rel.get("release_title") or "Rilisan", amount_idr=total_amount,
                payment_id=invoice_doc["id"], release_id=release_id,
            ))
        return await db.releases.find_one({"id": release_id}, {"_id": 0})
    elif body.action == "approve":
        if billing_flow == "pay_per_release":
            require_status(rel, ("paid",), "Setujui")
            if rel.get("payment_status") != "paid":
                raise HTTPException(status_code=409, detail="Pembayaran belum dikonfirmasi Xendit")
        else:
            require_status(rel, ("under_review",), "Setujui")
        new_status = "approved"
    elif body.action == "need_revision":
        require_status(rel, ("submitted", "under_review"), "Minta revisi")
        if not (body.note or "").strip():
            raise HTTPException(status_code=400, detail="Catatan revisi wajib diisi")
        new_status = "need_revision"
    elif body.action == "reject":
        require_status(rel, ("submitted", "under_review", "need_revision"), "Tolak")
        if not (body.note or "").strip():
            raise HTTPException(status_code=400, detail="Alasan penolakan wajib diisi")
        new_status = "rejected"
    elif body.action == "deliver":
        require_status(rel, ("approved",), "Kirim ke Believe")
        new_status = "delivered"
    elif body.action == "mark_live":
        require_status(rel, ("delivered",), "Tandai tayang")
        if not (body.upc or rel.get("upc") or "").strip():
            raise HTTPException(status_code=400, detail="UPC wajib diisi sebelum status Tayang")
        tracks = await db.tracks.find({"release_id": release_id}, {"_id": 0, "id": 1, "isrc": 1}).to_list(500)
        missing_isrc = []
        resolved_isrcs = {}
        for track in tracks:
            candidate = (body.track_isrcs.get(track["id"]) or track.get("isrc") or "").strip()
            if not candidate:
                missing_isrc.append(track["id"])
            else:
                resolved_isrcs[track["id"]] = candidate
        if missing_isrc:
            raise HTTPException(status_code=400, detail="ISRC wajib diisi untuk setiap track sebelum status Tayang")
        for track_id, candidate in resolved_isrcs.items():
            await db.tracks.update_one({"id": track_id}, {"$set": {"isrc": candidate, "updated_at": now_iso()}})
        new_status = "live"
    else:
        require_status(rel, ("live",), "Turunkan rilisan")
        if not (body.note or "").strip():
            raise HTTPException(status_code=400, detail="Alasan penurunan rilisan wajib diisi")
        new_status = "taken_down"
    upd = {"status": new_status, "updated_at": now_iso()}
    if body.action in ("need_revision", "reject") and body.note:
        upd["admin_note"] = body.note
    if body.upc:
        upd["upc"] = body.upc
    if body.action == "start_review":
        upd["review_started_at"] = now_iso()
        upd["review_started_by"] = user["id"]
    if body.action == "deliver":
        upd["delivered_to_believe_at"] = now_iso()
    if body.action == "mark_live":
        upd["live_at"] = now_iso()
    await db.releases.update_one({"id": release_id}, {"$set": upd, "$push": {"status_history": {
        "from": rel.get("status"), "to": new_status, "changed_by": user["id"],
        "changed_at": now_iso(), "note": body.note,
    }}})
    await log_activity(user["id"], f"admin_{body.action}", "release", release_id, before={"status": rel["status"]}, after={"status": new_status})
    # Notify label
    label_uids = await label_user_ids(rel["label_id"])
    titles = {
        "approve": ("Rilisan disetujui ✓", f"'{rel.get('release_title')}' telah disetujui."),
        "start_review": ("Rilisan sedang direview", f"'{rel.get('release_title')}' sedang diperiksa admin."),
        "need_revision": ("Rilisan perlu revisi", f"'{rel.get('release_title')}' perlu revisi. {body.note or ''}"),
        "reject": ("Rilisan ditolak", f"'{rel.get('release_title')}' ditolak. {body.note or ''}"),
        "deliver": ("Rilisan didistribusikan", f"'{rel.get('release_title')}' sedang didistribusikan ke DSP."),
        "mark_live": ("Rilisan sudah tayang", f"'{rel.get('release_title')}' sudah tayang di platform."),
        "takedown": ("Rilisan diturunkan", f"'{rel.get('release_title')}' telah diturunkan dari platform."),
    }
    if body.action in titles:
        t, msg = titles[body.action]
        await notify_many(label_uids, f"release_{body.action}", t, msg, f"/label/releases/{release_id}", {"release_id": release_id})
    return await db.releases.find_one({"id": release_id}, {"_id": 0})


