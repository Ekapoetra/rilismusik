"""Releases & track upload router."""
from fastapi import APIRouter, HTTPException, Request, Response, Depends, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta, date
import os
import csv
import io
import json
import re
import shutil
import tempfile
import zipfile
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
from .admin_permission_service import assert_admin_permission
from payment_service import PaymentCreateData, create_payment_document, ppr_pricing, ppr_base_amount, ppr_line_item_text
from email_service import send_release_invoice_email, send_release_submission_email
from .release_workflow_service import (
    EDITABLE_STATUSES, normalize_artist_credits, require_status,
    validate_artist_web_url, validate_release_date, validate_release_submission,
)
from .artist_social_service import resolve_release_artist_credits
from .release_deletion_service import ReleaseDeletionResult, delete_release_record
from .release_list_metadata import ReleaseListItem, enrich_release_list
from .release_submission_quota import SubmissionQuotaOut, submission_quota, submission_slot

# =============================================================================
#                              RELEASES
# =============================================================================
release_r = APIRouter(prefix="/releases", tags=["releases"])


@release_r.get("/", response_model=List[ReleaseListItem])
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
    await enrich_release_list(db, items)
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


@release_r.get("/submission-quota", response_model=SubmissionQuotaOut)
async def get_submission_quota(release_id: Optional[str] = None, user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    if release_id and not await db.releases.find_one({"id": release_id, "label_id": label["id"]}, {"_id": 0, "id": 1}):
        raise HTTPException(404, "Rilisan tidak ditemukan")
    return await submission_quota(db, label["id"], release_id)


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
    shortfall_invoice = None
    if rel.get("ppr_shortfall_payment_id"):
        shortfall_invoice = await db.payments.find_one({"id": rel["ppr_shortfall_payment_id"]}, {"_id": 0})
    label_doc = await db.labels.find_one({"id": rel.get("label_id")}, {"_id": 0, "whatsapp": 1})
    return {**rel, "tracks": tracks, "payment": payment, "shortfall_invoice": shortfall_invoice, "label_whatsapp": rel.get("label_whatsapp_snapshot") or (label_doc or {}).get("whatsapp")}


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

    track_featured = [normalize_artist_credits(track.featured_artists) for track in body.tracks]

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
            "featured_artists": track_featured[idx - 1],
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

    track_featured = [normalize_artist_credits(track.featured_artists) for track in body.tracks]

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
            "featured_artists": track_featured[idx - 1],
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
    for track in tracks:
        all_credits.extend(track.get("featured_artists") or [])
    await resolve_release_artist_credits(db, label["id"], all_credits, persist=False)
    primary_count = len(rel.get("primary_artists") or [])
    featured_count = len(rel.get("featured_artists") or [])

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
        base_amount = ppr_base_amount(rel.get("release_type"), len(tracks), await ppr_pricing())
        payment_status = "not_generated"
        billing_flow = "pay_per_release"
        payment_id = None

    async with submission_slot(db, label["id"], release_id) as slot:
        # Re-check after acquiring the per-release lease to avoid duplicate submissions.
        current = await db.releases.find_one({"id": release_id}, {"_id": 0, "status": 1, "updated_at": 1})
        if not current or current.get("status") != rel.get("status") or current.get("updated_at") != rel.get("updated_at"):
            raise HTTPException(409, "Rilisan telah berubah. Muat ulang sebelum mengirim.")
        resolved_credits = await resolve_release_artist_credits(db, label["id"], all_credits)
        cursor = primary_count + featured_count
        for track in tracks:
            size = len(track.get("featured_artists") or [])
            await db.tracks.update_one({"id": track["id"], "release_id": release_id}, {"$set": {"featured_artists": resolved_credits[cursor:cursor + size]}})
            cursor += size
        result = await db.releases.update_one(
        {"id": release_id, "status": rel.get("status"), "updated_at": rel.get("updated_at"), "$expr": {"$eq": [{"$dateToString": {"date": "$$NOW", "format": "%Y-%m-%d", "timezone": "Asia/Jakarta"}}, slot["day"]]}},
        {"$set": {
            "primary_artists": resolved_credits[:primary_count],
            "featured_artists": resolved_credits[primary_count:primary_count + featured_count],
            "artist_name": ", ".join(item["name"] for item in resolved_credits[:primary_count]),
            "label_whatsapp_snapshot": label.get("whatsapp"),
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
            "quota_token": slot["token"], "submission_day": slot["day"],
            "changed_at": now_iso(), "note": "Submit ulang setelah revisi/penolakan" if rel.get("status") in ("need_revision", "rejected") else "Submit pertama",
        }}},
    )
        if result.modified_count != 1:
            raise HTTPException(409, "Rilisan telah berubah. Muat ulang sebelum mengirim.")
    try:
        await log_activity(user["id"], "submit_release", "release", release_id, after={"status": new_status})
    except Exception:
        logger.exception("Submission audit mirror failed; embedded status history retained")
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


@release_r.delete("/{release_id}", response_model=ReleaseDeletionResult)
async def delete_release(release_id: str, user: dict = Depends(require_label)):
    """Label deletes its own release. Allowed only for draft or rejected releases."""
    label = await get_label_by_user(user)
    return await delete_release_record(release_id, user["id"], label_id=label["id"])



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
        track_count = await db.tracks.count_documents({"release_id": release_id})
        base_amount = ppr_base_amount(rel.get("release_type"), track_count, await ppr_pricing())
        base_name, base_desc = ppr_line_item_text(rel.get("release_type"), track_count)
        selected_addons = rel.get("selected_addons") or []
        addon_amount = sum(int(item.get("amount") or 0) for item in selected_addons)
        total_amount = base_amount + addon_amount
        line_items = [{
            "reference_id": f"release-base-{release_id}",
            "name": base_name,
            "description": f"{rel.get('release_title')} — {base_desc}",
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
    elif body.action == "override_status":
        override_allowed = ("draft", "submitted", "under_review", "approved", "delivered", "live", "need_revision", "rejected", "taken_down")
        target = (body.target_status or "").strip()
        if target not in override_allowed:
            raise HTTPException(status_code=400, detail="Status tujuan tidak valid untuk koreksi status")
        if not (body.note or "").strip():
            raise HTTPException(status_code=400, detail="Alasan koreksi status wajib diisi")
        if target == rel.get("status"):
            raise HTTPException(status_code=400, detail="Status tujuan sama dengan status saat ini")
        new_status = target
    else:
        require_status(rel, ("live",), "Turunkan rilisan")
        if not (body.note or "").strip():
            raise HTTPException(status_code=400, detail="Alasan penurunan rilisan wajib diisi")
        new_status = "taken_down"
    upd = {"status": new_status, "updated_at": now_iso()}
    if body.action in ("need_revision", "reject") and body.note:
        upd["admin_note"] = body.note
    if body.action == "override_status" and body.note:
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
        "override_status": ("Status rilisan diperbarui", f"Status '{rel.get('release_title')}' diperbarui admin. {body.note or ''}"),
    }
    if body.action in titles:
        t, msg = titles[body.action]
        await notify_many(label_uids, f"release_{body.action}", t, msg, f"/label/releases/{release_id}", {"release_id": release_id})
    return await db.releases.find_one({"id": release_id}, {"_id": 0})




def _require_release_finance(user: dict) -> None:
    if user.get("role") not in ("super_admin", "admin_finance", "admin_release"):
        raise HTTPException(status_code=403, detail="Hanya Super Admin, Admin Finance, atau Admin Release")


async def _ppr_paid_base(release_id: str) -> int:
    """Total PPR base already settled for a release (excludes add-ons)."""
    total = 0
    async for payment in db.payments.find(
        {"release_id": release_id, "type": {"$in": ["pay_per_release", "release_shortfall"]}, "status": "paid"},
        {"_id": 0, "type": 1, "amount": 1, "base_amount": 1, "addon_amount": 1},
    ):
        if payment.get("type") == "release_shortfall":
            total += int(payment.get("amount") or 0)
        else:
            base = payment.get("base_amount")
            if base is None:
                base = int(payment.get("amount") or 0) - int(payment.get("addon_amount") or 0)
            total += int(base or 0)
    return total


async def _shortfall_state(release_id: str) -> dict:
    rel = await db.releases.find_one({"id": release_id}, {"_id": 0})
    if not rel:
        raise HTTPException(status_code=404, detail="Rilisan tidak ditemukan")
    pricing = await ppr_pricing()
    album_price = int(pricing["album"])
    paid_base = await _ppr_paid_base(release_id)
    is_album = (rel.get("release_type") or "").lower() == "album"
    shortfall = max(0, album_price - paid_base) if is_album else 0
    pending = await db.payments.find_one(
        {"release_id": release_id, "type": "release_shortfall", "status": {"$in": ["pending", "expired", "cancelled", "failed"]}},
        {"_id": 0, "id": 1, "amount": 1, "status": 1}, sort=[("created_at", -1)],
    )
    open_id = (pending or {}).get("id") if pending and pending.get("status") == "pending" else None
    return {
        "release_id": release_id,
        "release_title": rel.get("release_title"),
        "release_type": rel.get("release_type"),
        "is_album": is_album,
        "has_prior_payment": paid_base > 0,
        "album_package_price_idr": album_price,
        "already_paid_idr": paid_base,
        "shortfall_idr": shortfall,
        "open_shortfall_invoice_id": open_id,
        "eligible": is_album and paid_base > 0 and shortfall > 0 and not open_id,
    }


@release_r.get("/{release_id}/admin/shortfall-preview")
async def admin_shortfall_preview(release_id: str, user: dict = Depends(require_admin)):
    _require_release_finance(user)
    return await _shortfall_state(release_id)


@release_r.post("/{release_id}/admin/shortfall-invoice")
async def admin_create_shortfall_invoice(release_id: str, user: dict = Depends(require_admin)):
    _require_release_finance(user)
    rel = await db.releases.find_one({"id": release_id}, {"_id": 0})
    if not rel:
        raise HTTPException(status_code=404, detail="Rilisan tidak ditemukan")
    state = await _shortfall_state(release_id)
    if not state["is_album"]:
        raise HTTPException(status_code=400, detail="Invoice kekurangan hanya untuk rilisan tipe ALBUM")
    if not state["has_prior_payment"]:
        raise HTTPException(status_code=400, detail="Belum ada pembayaran per lagu untuk rilisan ini")
    if state["open_shortfall_invoice_id"]:
        raise HTTPException(status_code=409, detail="Invoice kekurangan masih menunggu pembayaran label")
    if state["shortfall_idr"] <= 0:
        raise HTTPException(status_code=400, detail="Tidak ada kekurangan pembayaran untuk rilisan ini")
    amount = int(state["shortfall_idr"])
    invoice_doc = await create_payment_document(PaymentCreateData(
        label_id=rel["label_id"], payment_type="release_shortfall", amount=amount,
        release_id=release_id, description=f"Kekurangan paket album — {rel.get('release_title')}",
        return_path=f"/label/releases/{release_id}", reference_id=f"ppr-shortfall-{release_id}-{new_id()[:8]}",
        line_items=[{
            "reference_id": f"shortfall-{release_id}",
            "name": "Kekurangan Paket Album Pay Per Release",
            "description": f"Selisih menuju paket album Rp {state['album_package_price_idr']:,.0f} (sudah dibayar Rp {state['already_paid_idr']:,.0f})",
            "amount": amount, "quantity": 1,
        }],
        base_amount=amount, addon_amount=0, approval_required_before_payment=True,
    ))
    await db.releases.update_one({"id": release_id}, {"$set": {
        "ppr_shortfall_payment_id": invoice_doc["id"], "updated_at": now_iso(),
    }})
    await log_activity(user["id"], "admin_create_shortfall_invoice", "release", release_id, after={
        "payment_id": invoice_doc["id"], "amount": amount,
        "album_price": state["album_package_price_idr"], "already_paid": state["already_paid_idr"],
    })
    amount_label = f"{amount:,}".replace(",", ".")
    await notify_many(
        await label_user_ids(rel["label_id"]), "release_shortfall_invoice", "Invoice kekurangan paket album",
        f"Rilisan '{rel.get('release_title')}' kurang Rp {amount_label} untuk paket album. Selesaikan pembayaran di halaman rilisan atau menu Invoice.",
        f"/label/releases/{release_id}", {"release_id": release_id, "payment_id": invoice_doc["id"]},
    )
    label_doc = await db.labels.find_one({"id": rel["label_id"]}, {"_id": 0, "label_name": 1, "user_id": 1})
    label_user = await db.users.find_one({"id": (label_doc or {}).get("user_id")}, {"_id": 0, "email": 1})
    if label_user and label_user.get("email"):
        asyncio.create_task(send_release_invoice_email(
            to=label_user["email"], label_name=(label_doc or {}).get("label_name") or "Label",
            release_title=rel.get("release_title") or "Rilisan", amount_idr=amount,
            payment_id=invoice_doc["id"], release_id=release_id,
        ))
    return {"invoice": invoice_doc, "state": await _shortfall_state(release_id)}


def _safe_name(text: str, fallback: str = "untitled") -> str:
    text = (text or "").strip() or fallback
    text = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return (text[:80] or fallback)


def _artist_names(credits) -> str:
    if not credits:
        return ""
    return ", ".join([c.get("name") for c in credits if c.get("name")])


def _release_metadata_json(rel: dict, tracks: list) -> dict:
    return {
        "release_id": rel.get("id"),
        "release_title": rel.get("release_title"),
        "release_type": rel.get("release_type"),
        "primary_artist": rel.get("artist_name"),
        "primary_artists": [c.get("name") for c in (rel.get("primary_artists") or []) if c.get("name")],
        "featured_artists": [c.get("name") for c in (rel.get("featured_artists") or []) if c.get("name")],
        "label": rel.get("label_name_snapshot"),
        "genre": rel.get("genre"),
        "subgenre": rel.get("subgenre"),
        "language": rel.get("language"),
        "release_date": rel.get("release_date"),
        "year": rel.get("year"),
        "copyright_line": rel.get("copyright_line"),
        "p_line": rel.get("p_line"),
        "upc": rel.get("upc"),
        "explicit": rel.get("explicit"),
        "status": rel.get("status"),
        "responsible_name": rel.get("responsible_name"),
        "artist_web_url": rel.get("artist_web_url"),
        "tracks": [{
            "track_number": t.get("track_number"),
            "track_title": t.get("track_title"),
            "artist_name": t.get("artist_name"),
            "featured_artists": [c.get("name") for c in (t.get("featured_artists") or []) if c.get("name")],
            "isrc": t.get("isrc"),
            "composer": t.get("composer"),
            "lyricist": t.get("lyricist"),
            "arranger": t.get("arranger"),
            "producer": t.get("producer"),
            "performer": t.get("performer"),
            "genre": t.get("genre"),
            "title_language": t.get("title_language"),
            "lyric_language": t.get("lyric_language"),
            "vocal_type": t.get("vocal_type"),
            "explicit": t.get("explicit"),
            "preview_start_seconds": t.get("preview_start_seconds"),
            "audio_filename": t.get("audio_filename"),
            "audio_sample_rate": t.get("audio_sample_rate"),
            "lyrics": t.get("lyrics"),
        } for t in tracks],
    }


def _release_metadata_txt(rel: dict, tracks: list) -> str:
    lines = []
    add = lines.append
    add("=" * 60)
    add("INFORMASI RILISAN — RILIS MUSIK")
    add("=" * 60)
    add(f"Kode Submit      : {(rel.get('id') or '').replace('-', '')[:8]}")
    add(f"ID Rilisan       : {rel.get('id')}")
    add(f"Judul            : {rel.get('release_title')}")
    add(f"Tipe             : {str(rel.get('release_type') or '').upper()}")
    add(f"Artis Utama      : {rel.get('artist_name')}")
    prim = _artist_names(rel.get("primary_artists"))
    if prim:
        add(f"Artis Utama (rinci): {prim}")
    feat = _artist_names(rel.get("featured_artists"))
    if feat:
        add(f"Artis Featuring  : {feat}")
    add(f"Label            : {rel.get('label_name_snapshot')}")
    add(f"Genre / Subgenre : {' / '.join([x for x in [rel.get('genre'), rel.get('subgenre')] if x])}")
    add(f"Bahasa           : {rel.get('language') or '-'}")
    add(f"Tanggal Rilis    : {rel.get('release_date')}")
    add(f"Tahun Produksi   : {rel.get('year') or '-'}")
    add(f"C Line           : {rel.get('copyright_line') or '-'}")
    add(f"P Line           : {rel.get('p_line') or '-'}")
    add(f"UPC              : {rel.get('upc') or '-'}")
    add(f"Explicit         : {'YA' if rel.get('explicit') else 'TIDAK'}")
    add(f"Status           : {rel.get('status')}")
    add(f"Penanggung Jawab : {rel.get('responsible_name') or '-'}")
    add(f"Web Artis        : {rel.get('artist_web_url') or '-'}")
    add("")
    add("=" * 60)
    add(f"TRACK ({len(tracks)})")
    add("=" * 60)
    for index, t in enumerate(tracks, 1):
        num = t.get("track_number") or index
        add("")
        add(f"[{num:02d}] {t.get('track_title')}")
        add("-" * 60)
        add(f"  Artis            : {t.get('artist_name') or rel.get('artist_name')}")
        tfeat = _artist_names(t.get("featured_artists"))
        if tfeat:
            add(f"  Featuring        : {tfeat}")
        add(f"  ISRC             : {t.get('isrc') or '-'}")
        add(f"  Vokal            : {'Instrumental' if t.get('vocal_type') == 'instrumental' else 'Ada Vokal'}")
        add(f"  Writer/Lyricist  : {t.get('lyricist') or '-'}")
        add(f"  Komposer         : {t.get('composer') or '-'}")
        add(f"  Arranger         : {t.get('arranger') or '-'}")
        add(f"  Produser         : {t.get('producer') or '-'}")
        add(f"  Performer        : {t.get('performer') or '-'}")
        add(f"  Genre            : {t.get('genre') or '-'}")
        add(f"  Bahasa Judul     : {t.get('title_language') or '-'}")
        add(f"  Bahasa Lirik     : {t.get('lyric_language') or '-'}")
        add(f"  Explicit         : {'YA' if t.get('explicit') else 'TIDAK'}")
        add(f"  Preview          : {t.get('preview_start_seconds') or 0} detik")
        sr = t.get("audio_sample_rate")
        add(f"  Audio            : {('WAV ' + str(round(sr / 1000, 1)) + ' kHz') if sr else '-'}")
        add(f"  File Audio Asli  : {t.get('audio_filename') or '-'}")
        add("")
        add("  LIRIK:")
        lyrics = (t.get("lyrics") or "").strip()
        if lyrics:
            for line in lyrics.splitlines():
                add(f"    {line}")
        else:
            add("    (Tidak ada lirik)")
    add("")
    add("=" * 60)
    add(f"Diekspor: {now_iso()}")
    return "\n".join(lines)


@release_r.get("/{release_id}/admin/export-package")
async def admin_export_release_package(release_id: str, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "releases.review")
    rel = await db.releases.find_one({"id": release_id}, {"_id": 0})
    if not rel:
        raise HTTPException(status_code=404, detail="Rilisan tidak ditemukan")
    if rel.get("status") == "draft":
        raise HTTPException(status_code=400, detail="Paket hanya tersedia untuk rilisan yang sudah dikirim")
    tracks = await db.tracks.find({"release_id": release_id}, {"_id": 0}).sort("track_number", 1).to_list(200)

    import storage_service
    short_code = (release_id or "").replace("-", "")[:8]
    base_name = f"{short_code}_{_safe_name(rel.get('artist_name'), 'artist')}_{_safe_name(rel.get('release_title'), 'release')}"

    tmp_dir = tempfile.mkdtemp(prefix="rlspkg_")
    zip_path = os.path.join(tmp_dir, f"{base_name}.zip")
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED, allowZip64=True) as zf:
            zf.writestr("metadata.txt", _release_metadata_txt(rel, tracks))
            zf.writestr("metadata.json", json.dumps(_release_metadata_json(rel, tracks), ensure_ascii=False, indent=2))
            if rel.get("cover_url"):
                cover_key = rel["cover_url"].split("/api/files/", 1)[-1]
                cover_ext = cover_key.rsplit(".", 1)[-1].lower() if "." in cover_key else "jpg"
                cover_local = os.path.join(tmp_dir, f"cover.{cover_ext}")
                try:
                    await storage_service.download_to_file(key=cover_key, local_path=cover_local)
                    zf.write(cover_local, f"cover.{cover_ext}")
                    os.remove(cover_local)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("[export] cover download failed release=%s: %s", release_id, exc)
            for index, t in enumerate(tracks, 1):
                if not t.get("audio_url"):
                    continue
                num = t.get("track_number") or index
                audio_key = f"audio/{t['id']}.wav"
                local = os.path.join(tmp_dir, f"track_{num:02d}.wav")
                try:
                    await storage_service.download_to_file(key=audio_key, local_path=local)
                    zf.write(local, f"audio/{num:02d} - {_safe_name(t.get('track_title'), f'track{num}')}.wav")
                    os.remove(local)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("[export] audio download failed track=%s: %s", t.get("id"), exc)
    except Exception as exc:  # noqa: BLE001
        shutil.rmtree(tmp_dir, ignore_errors=True)
        logger.exception("[export] package build failed release=%s: %s", release_id, exc)
        raise HTTPException(status_code=500, detail="Gagal membuat paket rilisan")

    await log_activity(user["id"], "admin_export_release_package", "release", release_id, after={"file": f"{base_name}.zip"})
    return FileResponse(
        zip_path, media_type="application/zip", filename=f"{base_name}.zip",
        background=BackgroundTask(shutil.rmtree, tmp_dir, ignore_errors=True),
    )

