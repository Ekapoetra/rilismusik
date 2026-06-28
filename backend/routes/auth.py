"""Authentication router."""
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
from email_service import (
    send_verification_email,
    send_password_reset_email,
)
from royalty_utils import (
    parse_csv_bytes, detect_columns, parse_amount, normalize_header,
    parse_period_from_value, calculate_line, label_percentage_at,
    strip_sensitive,
)
from withdraw_utils import withdraw_window_state, jakarta_now, MIN_WITHDRAW_IDR

# =============================================================================
#                                AUTH
# =============================================================================
auth = APIRouter(prefix="/auth", tags=["auth"])


@auth.post("/register")
async def register(body: RegisterLabelIn, response: Response):
    email = body.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Email sudah terdaftar")
    if not body.mda_accepted:
        raise HTTPException(
            status_code=400,
            detail="Anda harus menyetujui Master Distribution Agreement (MDA) untuk mendaftar.",
        )
    if body.claim_existing and not (body.legacy_label_name and body.legacy_label_name.strip()):
        raise HTTPException(
            status_code=400,
            detail="Nama label lama wajib diisi jika Anda mencentang 'Saya sudah punya data lama'.",
        )

    user_id = new_id()
    user_doc = {
        "id": user_id,
        "name": body.pic_name,
        "email": email,
        "password_hash": hash_password(body.password),
        "role": LABEL_ROLE,
        "email_verified_at": None,
        "status": "active",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    if body.claim_existing:
        user_doc.update({
            "claim_status": "pending_link",
            "claim_legacy_name": body.legacy_label_name.strip(),
            "claim_requested_at": now_iso(),
            "claim_label_name_new": body.label_name,
            "claim_whatsapp": body.whatsapp,
        })
    await db.users.insert_one(user_doc)

    accepted_at = now_iso()

    if body.claim_existing:
        # ---- Claim flow: DO NOT create label doc yet. Admin will link to legacy label. ----
        logger.info(
            "Claim request: user=%s name='%s' legacy='%s'",
            email, body.label_name, body.legacy_label_name,
        )
        # Notify all admins so they can resolve the claim
        admin_ids = []
        async for au in db.users.find(
            {"role": {"$in": ["super_admin", "admin_release", "admin_support"]}, "status": {"$ne": "suspended"}},
            {"_id": 0, "id": 1},
        ):
            admin_ids.append(au["id"])
        if admin_ids:
            now = now_iso()
            await db.notifications.insert_many([{
                "id": new_id(), "user_id": aid, "type": "claim_request",
                "title": "Permintaan claim akun lama",
                "body": f"User {body.pic_name} ({email}) mengaku punya label lama: '{body.legacy_label_name}'. Tinjau di Admin → Migrasi → Claims.",
                "link": "/admin/migrate?tab=claims",
                "meta": {"user_id": user_id, "legacy_label_name": body.legacy_label_name},
                "read_at": None, "created_at": now,
            } for aid in admin_ids])
        label_doc_response = {
            "claim_pending": True,
            "claim_legacy_name": body.legacy_label_name,
            "label_name": body.label_name,
            "pic_name": body.pic_name,
            "email": email,
        }
        verify_token = secrets.token_urlsafe(32)
        await db.email_verification_tokens.insert_one({
            "id": new_id(),
            "user_id": user_id,
            "token": verify_token,
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
            "used": False,
            "created_at": now_iso(),
        })
        # Send verification email (best-effort, won't block registration)
        await send_verification_email(to=email, pic_name=body.pic_name, token=verify_token)
        access = create_access_token(user_id, email, LABEL_ROLE)
        refresh = create_refresh_token(user_id)
        set_auth_cookies(response, access, refresh)
        return {
            "user": public_user(user_doc),
            "label": label_doc_response,
            "claim_pending": True,
            "access_token": access,
            "refresh_token": refresh,
            "verification_token": verify_token,
        }

    # ---- Normal flow: create label doc + auto-MDA ----
    label_id = new_id()
    label_doc = {
        "id": label_id,
        "user_id": user_id,
        "label_name": body.label_name,
        "pic_name": body.pic_name,
        "email": email,
        "whatsapp": body.whatsapp,
        "address": None,
        "city": None,
        "country": "Indonesia",
        "label_type": body.account_type,
        "royalty_percentage_default": 60.0,
        "payment_type": "pay_per_release",
        "subscription_status": "inactive",
        "subscription_expires_at": None,
        "contract_status": "active",
        "account_status": "active",
        "bank_verified": False,
        "blacklisted": False,
        "balance_available_idr": 0,
        "balance_pending_idr": 0,
        "balance_withdraw_requested_idr": 0,
        "mda_accepted_at": accepted_at,
        "created_at": accepted_at,
        "updated_at": accepted_at,
    }
    await db.labels.insert_one(label_doc)
    label_doc.pop("_id", None)

    # ---- Auto-generate Master Distribution Agreement PDF ----
    try:
        from .mda_generator import generate_mda_pdf_bytes
        import storage_service
        legal_setting = await db.landing_settings.find_one({"key": "legal_entity"}, {"_id": 0, "value": 1})
        legal_entity = (legal_setting or {}).get("value") or {}
        contract_id = new_id()
        pdf_bytes = generate_mda_pdf_bytes(label_doc, legal_entity)
        r2_key = f"contract/{contract_id}.pdf"
        await storage_service.upload_bytes(key=r2_key, data=pdf_bytes, content_type="application/pdf")
        file_url = f"/api/files/{r2_key}"
        contract_doc = {
            "id": contract_id,
            "label_id": label_id,
            "label_name": body.label_name,
            "title": "Master Distribution Agreement",
            "kind": "mda",
            "file_url": file_url,
            "filename": f"MDA-{body.label_name[:20]}.pdf",
            "start_date": accepted_at[:10],
            "end_date": None,  # lifetime — no expiry
            "is_lifetime": True,
            "status": "active",
            "notes": "Auto-generated saat registrasi via persetujuan elektronik (checkbox).",
            "accepted_at": accepted_at,
            "accepted_by_name": body.pic_name,
            "accepted_by_email": email,
            "created_at": accepted_at,
            "updated_at": accepted_at,
            "created_by": "system",
        }
        await db.contracts.insert_one(contract_doc)
        logger.info("MDA generated for %s -> %s", body.label_name, r2_key)
    except Exception as e:
        logger.exception("MDA generation failed for label %s: %s", body.label_name, e)
        # Don't block registration on MDA failure — admin can re-generate later


    # Email verification token (sent via Resend; token also returned in dev for testing)
    verify_token = secrets.token_urlsafe(32)
    await db.email_verification_tokens.insert_one({
        "id": new_id(),
        "user_id": user_id,
        "token": verify_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
        "used": False,
        "created_at": now_iso(),
    })
    logger.info("[DEV] Verification token for %s: %s", email, verify_token)
    await send_verification_email(to=email, pic_name=body.pic_name, token=verify_token)

    access = create_access_token(user_id, email, LABEL_ROLE)
    refresh = create_refresh_token(user_id)
    set_auth_cookies(response, access, refresh)

    return {
        "user": public_user(user_doc),
        "label": redact_label_for_self(label_doc),
        "access_token": access,
        "refresh_token": refresh,
        "verification_token": verify_token,  # exposed only in MVP (no email service)
    }


@auth.post("/login")
async def login(body: LoginIn, response: Response, request: Request):
    email = body.email.lower().strip()
    # brute force check — use X-Forwarded-For (set by ingress) for stable client IP
    fwd = request.headers.get("x-forwarded-for") or request.headers.get("x-real-ip")
    client_ip = (fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "na"))
    identifier = f"{client_ip}:{email}"
    attempt = await db.login_attempts.find_one({"identifier": identifier})
    now = datetime.now(timezone.utc)
    if attempt and attempt.get("locked_until"):
        locked_until = datetime.fromisoformat(attempt["locked_until"])
        if locked_until > now:
            raise HTTPException(status_code=429, detail="Terlalu banyak percobaan, coba lagi nanti")

    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        # increment attempts
        attempts = (attempt or {}).get("count", 0) + 1
        update = {"identifier": identifier, "count": attempts, "last_at": now.isoformat()}
        if attempts >= 5:
            update["locked_until"] = (now + timedelta(minutes=15)).isoformat()
            update["count"] = 0
        await db.login_attempts.update_one({"identifier": identifier}, {"$set": update}, upsert=True)
        raise HTTPException(status_code=401, detail="Email atau password salah")

    if user.get("status") == "suspended":
        raise HTTPException(status_code=403, detail="Akun ditangguhkan")

    # Block blacklisted labels at login
    if user["role"] == LABEL_ROLE:
        lab = await db.labels.find_one({"user_id": user["id"]}, {"_id": 0, "account_status": 1, "blacklist_reason": 1})
        if lab and lab.get("account_status") == "blacklisted":
            raise HTTPException(status_code=403, detail=f"Akun di-blacklist. Alasan: {lab.get('blacklist_reason') or 'Hubungi admin'}")

    await db.login_attempts.delete_one({"identifier": identifier})

    access = create_access_token(user["id"], user["email"], user["role"])
    refresh = create_refresh_token(user["id"])
    set_auth_cookies(response, access, refresh)

    payload = {"user": public_user(user), "access_token": access, "refresh_token": refresh}
    if user["role"] == LABEL_ROLE:
        label = await db.labels.find_one({"user_id": user["id"]}, {"_id": 0})
        payload["label"] = redact_label_for_self(label) if label else None
    elif user["role"] == ARTIST_ROLE:
        artist = await db.artists.find_one({"user_id": user["id"]}, {"_id": 0})
        payload["artist"] = artist
    return payload


@auth.post("/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"ok": True}


@auth.get("/me")
async def me(user: dict = Depends(get_current_user)):
    payload = {"user": public_user(user)}
    if user["role"] == LABEL_ROLE:
        label = await db.labels.find_one({"user_id": user["id"]}, {"_id": 0})
        payload["label"] = redact_label_for_self(label) if label else None
    elif user["role"] == ARTIST_ROLE:
        artist = await db.artists.find_one({"user_id": user["id"]}, {"_id": 0})
        payload["artist"] = artist
    return payload


@auth.post("/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user = await db.users.find_one({"id": payload["sub"]})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    access = create_access_token(user["id"], user["email"], user["role"])
    new_refresh = create_refresh_token(user["id"])
    set_auth_cookies(response, access, new_refresh)
    return {"ok": True}


@auth.post("/verify-email")
async def verify_email(body: VerifyEmailIn):
    rec = await db.email_verification_tokens.find_one({"token": body.token, "used": False})
    if not rec:
        raise HTTPException(status_code=400, detail="Token tidak valid")
    if datetime.fromisoformat(rec["expires_at"]) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token kadaluarsa")
    await db.email_verification_tokens.update_one({"id": rec["id"]}, {"$set": {"used": True}})
    await db.users.update_one({"id": rec["user_id"]}, {"$set": {"email_verified_at": now_iso()}})
    return {"ok": True}


@auth.post("/resend-verification")
async def resend_verification(user: dict = Depends(get_current_user)):
    if user.get("email_verified_at"):
        return {"ok": True, "already_verified": True}
    token = secrets.token_urlsafe(32)
    await db.email_verification_tokens.insert_one({
        "id": new_id(),
        "user_id": user["id"],
        "token": token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
        "used": False,
        "created_at": now_iso(),
    })
    logger.info("[DEV] Verification token for %s: %s", user["email"], token)
    # Look up label.pic_name (fall back to email local part for sub-admins/artists)
    label = await db.labels.find_one({"user_id": user["id"]}, {"_id": 0, "pic_name": 1})
    pic_name = (label or {}).get("pic_name") or user["email"].split("@")[0]
    await send_verification_email(to=user["email"], pic_name=pic_name, token=token)
    return {"ok": True, "verification_token": token}


@auth.post("/forgot-password")
async def forgot_password(body: ForgotPasswordIn):
    user = await db.users.find_one({"email": body.email.lower().strip()})
    # Always return ok to prevent email enumeration
    if not user:
        return {"ok": True}
    token = secrets.token_urlsafe(32)
    await db.password_reset_tokens.insert_one({
        "id": new_id(),
        "user_id": user["id"],
        "token": token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "used": False,
        "created_at": now_iso(),
    })
    logger.info("[DEV] Password reset token for %s: %s", user["email"], token)
    await send_password_reset_email(to=user["email"], token=token)
    return {"ok": True, "reset_token": token}  # exposed only in MVP


@auth.post("/reset-password")
async def reset_password(body: ResetPasswordIn):
    rec = await db.password_reset_tokens.find_one({"token": body.token, "used": False})
    if not rec:
        raise HTTPException(status_code=400, detail="Token tidak valid")
    if datetime.fromisoformat(rec["expires_at"]) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token kadaluarsa")
    await db.users.update_one({"id": rec["user_id"]}, {"$set": {"password_hash": hash_password(body.password), "updated_at": now_iso()}})
    await db.password_reset_tokens.update_one({"id": rec["id"]}, {"$set": {"used": True}})
    return {"ok": True}


