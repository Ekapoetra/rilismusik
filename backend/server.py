"""RILIS MUSIK — backend API (Phase 1 MVP).

Modules:
  - Auth (label/admin/artist) with JWT + httpOnly cookies
  - Label profile, dashboard, bank account
  - Releases (label CRUD, admin review workflow)
  - Artists (label sub-accounts)
  - Admin (label management, admin users, dashboard metrics)
  - Payments (MOCK Xendit: pay-per-release + annual subscription)
  - CMS (landing page settings)
"""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import logging
import secrets
import shutil
import csv
import io
from datetime import datetime, timezone, timedelta, date
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, UploadFile, File, Form, Query
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

from auth_utils import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    set_auth_cookies, clear_auth_cookies, decode_token,
    extract_token_from_request, make_get_current_user,
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
    now_iso, new_id,
)
from royalty_utils import (
    parse_csv_bytes, detect_columns, parse_amount, normalize_header,
    parse_period_from_value, calculate_line, label_percentage_at,
    strip_sensitive,
)
from withdraw_utils import withdraw_window_state, jakarta_now, MIN_WITHDRAW_IDR

logger = logging.getLogger("rilismusik")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/app/backend/uploads"))
for sub in ("audio", "cover", "csv", "contract", "ticket", "landing"):
    (UPLOAD_DIR / sub).mkdir(parents=True, exist_ok=True)

# ---------- DB ----------
client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="RILIS MUSIK API", version="0.1.0")

# Serve uploaded media (audio, cover, etc.) under /api/files
app.mount("/api/files", StaticFiles(directory=str(UPLOAD_DIR)), name="files")

api = APIRouter(prefix="/api")

get_current_user = make_get_current_user(db)


async def require_label(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != LABEL_ROLE:
        raise HTTPException(status_code=403, detail="Hanya untuk akun label")
    return user


async def require_artist(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != ARTIST_ROLE:
        raise HTTPException(status_code=403, detail="Hanya untuk akun artist")
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Akses admin diperlukan")
    return user


async def require_super_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Super Admin diperlukan")
    return user


# ---------- helpers ----------
def public_user(u: dict) -> dict:
    u = {**u}
    u.pop("password_hash", None)
    u.pop("_id", None)
    return u


async def get_label_by_user(user: dict) -> dict:
    label = await db.labels.find_one({"user_id": user["id"]}, {"_id": 0})
    if not label:
        raise HTTPException(status_code=404, detail="Label belum diset")
    return label


async def log_activity(actor_id: str, action: str, module: str, ref_id: Optional[str] = None,
                       before: Optional[dict] = None, after: Optional[dict] = None) -> None:
    def _clean(d):
        if not isinstance(d, dict):
            return d
        return {k: v for k, v in d.items() if k != "_id"}
    await db.activity_logs.insert_one({
        "id": new_id(),
        "user_id": actor_id,
        "action": action,
        "module": module,
        "reference_id": ref_id,
        "before_data": _clean(before),
        "after_data": _clean(after),
        "created_at": now_iso(),
    })


# =============================================================================
#                                AUTH
# =============================================================================
auth = APIRouter(prefix="/auth", tags=["auth"])


@auth.post("/register")
async def register(body: RegisterLabelIn, response: Response):
    email = body.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Email sudah terdaftar")

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
    await db.users.insert_one(user_doc)

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
        "contract_status": "pending_contract",
        "account_status": "active",
        "bank_verified": False,
        "blacklisted": False,
        "balance_available_idr": 0,
        "balance_pending_idr": 0,
        "balance_withdraw_requested_idr": 0,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.labels.insert_one(label_doc)
    label_doc.pop("_id", None)

    # Email verification token (logged in dev, no email service in MVP)
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

    access = create_access_token(user_id, email, LABEL_ROLE)
    refresh = create_refresh_token(user_id)
    set_auth_cookies(response, access, refresh)

    return {
        "user": public_user(user_doc),
        "label": label_doc,
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
        payload["label"] = label
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
        payload["label"] = label
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


# =============================================================================
#                                LABEL
# =============================================================================
label_r = APIRouter(prefix="/label", tags=["label"])


@label_r.get("/me")
async def label_me(user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    return label


@label_r.patch("/me")
async def label_update(body: LabelProfileUpdate, user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    upd = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    upd["updated_at"] = now_iso()
    await db.labels.update_one({"id": label["id"]}, {"$set": upd})
    return await db.labels.find_one({"id": label["id"]}, {"_id": 0})


@label_r.get("/dashboard")
async def label_dashboard(user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    total_releases = await db.releases.count_documents({"label_id": label["id"]})
    active_releases = await db.releases.count_documents({"label_id": label["id"], "status": {"$in": ["approved", "delivered", "live"]}})
    total_tracks = await db.tracks.count_documents({"label_id": label["id"]})
    total_artists = await db.artists.count_documents({"label_id": label["id"]})
    active_tickets = await db.support_tickets.count_documents({"label_id": label["id"], "status": {"$nin": ["done", "rejected"]}})
    pending_invoices = await db.payments.count_documents({"label_id": label["id"], "status": "pending"})

    # last month revenue (latest published royalty period for this label)
    last_revenue = 0
    last_period = None
    pipeline = [
        {"$match": {"label_id": label["id"], "status": {"$in": ["pending", "available", "withdrawn"]}}},
        {"$group": {"_id": "$period", "total": {"$sum": "$label_idr"}}},
        {"$sort": {"_id": -1}},
        {"$limit": 1},
    ]
    async for row in db.royalty_lines.aggregate(pipeline):
        last_revenue = row["total"]
        last_period = row["_id"]
        break

    return {
        "label": label,
        "stats": {
            "balance_available_idr": label.get("balance_available_idr", 0),
            "balance_pending_idr": label.get("balance_pending_idr", 0),
            "balance_withdraw_requested_idr": label.get("balance_withdraw_requested_idr", 0),
            "last_month_revenue_idr": last_revenue,
            "last_month_period": last_period,
            "total_releases": total_releases,
            "active_releases": active_releases,
            "total_tracks": total_tracks,
            "total_artists": total_artists,
            "active_tickets": active_tickets,
            "pending_invoices": pending_invoices,
            "subscription_status": label.get("subscription_status"),
            "subscription_expires_at": label.get("subscription_expires_at"),
            "contract_status": label.get("contract_status"),
            "account_status": label.get("account_status"),
            "bank_verified": label.get("bank_verified", False),
            "payment_type": label.get("payment_type"),
        },
    }


@label_r.get("/bank-account")
async def get_bank(user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    bank = await db.bank_accounts.find_one({"label_id": label["id"]}, {"_id": 0})
    return bank or None


@label_r.post("/bank-account")
async def submit_bank(body: BankAccountIn, user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    existing = await db.bank_accounts.find_one({"label_id": label["id"]})
    if existing:
        raise HTTPException(status_code=409, detail="Rekening sudah pernah diinput. Hubungi admin untuk perubahan.")
    bank = {
        "id": new_id(),
        "label_id": label["id"],
        "bank_name": body.bank_name,
        "account_number": body.account_number,
        "account_holder_name": body.account_holder_name,
        "verified_status": "pending",
        "verified_by": None,
        "verified_at": None,
        "created_at": now_iso(),
    }
    await db.bank_accounts.insert_one(bank)
    bank.pop("_id", None)
    return bank


@label_r.get("/invoices")
async def list_invoices(user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    items = await db.payments.find({"label_id": label["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return items


# =============================================================================
#                              RELEASES
# =============================================================================
release_r = APIRouter(prefix="/releases", tags=["releases"])


@release_r.get("/")
async def list_releases(user: dict = Depends(get_current_user), status: Optional[str] = None, q: Optional[str] = None):
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

    target = UPLOAD_DIR / "cover" / f"{release_id}.{ext}"
    with open(target, "wb") as f:
        f.write(file_bytes)
    url = f"/api/files/cover/{release_id}.{ext}"
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

    target = UPLOAD_DIR / "audio" / f"{track_id}.wav"
    with open(target, "wb") as f:
        shutil.copyfileobj(file.file, f)
    url = f"/api/files/audio/{track_id}.wav"
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
        # create pay-per-release invoice (MOCK Xendit)
        invoice_id = new_id()
        invoice_doc = {
            "id": invoice_id,
            "label_id": label["id"],
            "release_id": release_id,
            "type": "pay_per_release",
            "xendit_invoice_id": f"mock_{invoice_id[:12]}",
            "xendit_invoice_url": f"/payments/mock-checkout/{invoice_id}",
            "amount": 35000,
            "currency": "IDR",
            "status": "pending",
            "paid_at": None,
            "expired_at": (now + timedelta(days=3)).isoformat(),
            "created_at": now_iso(),
        }
        await db.payments.insert_one(invoice_doc)
        payment_status = "pending"
        payment_id = invoice_id

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
    label_user_ids = await _label_user_ids(rel["label_id"])
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
        await notify_many(label_user_ids, f"release_{body.action}", t, msg, f"/label/releases/{release_id}", {"release_id": release_id})
    return await db.releases.find_one({"id": release_id}, {"_id": 0})


# =============================================================================
#                              ARTISTS
# =============================================================================
artist_r = APIRouter(prefix="/artists", tags=["artists"])


@artist_r.get("/")
async def list_artists(user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    items = await db.artists.find({"label_id": label["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return items


@artist_r.post("/")
async def create_artist(body: ArtistIn, user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    email = body.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Email sudah terdaftar")

    user_id = new_id()
    artist_id = new_id()
    user_doc = {
        "id": user_id,
        "name": body.artist_name,
        "email": email,
        "password_hash": hash_password(body.password),
        "role": ARTIST_ROLE,
        "email_verified_at": None,
        "status": "active",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.users.insert_one(user_doc)

    default_visibility = {
        "show_amount": True,
        "show_percentage": False,
        "show_per_song": True,
        "show_monthly_history": True,
    }
    visibility = {**default_visibility, **(body.visibility_settings or {})}
    artist_doc = {
        "id": artist_id,
        "label_id": label["id"],
        "user_id": user_id,
        "artist_name": body.artist_name,
        "email": email,
        "whatsapp": body.whatsapp,
        "visibility_settings": visibility,
        "status": "active",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.artists.insert_one(artist_doc)
    artist_doc.pop("_id", None)
    return artist_doc


@artist_r.get("/{artist_id}")
async def get_artist(artist_id: str, user: dict = Depends(get_current_user)):
    artist = await db.artists.find_one({"id": artist_id}, {"_id": 0})
    if not artist:
        raise HTTPException(status_code=404, detail="Artist tidak ditemukan")
    if user["role"] == LABEL_ROLE:
        label = await get_label_by_user(user)
        if artist["label_id"] != label["id"]:
            raise HTTPException(status_code=403, detail="Bukan artist Anda")
    elif user["role"] == ARTIST_ROLE:
        if artist["user_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Bukan akun Anda")
    return artist


@artist_r.patch("/{artist_id}")
async def update_artist(artist_id: str, body: ArtistUpdateIn, user: dict = Depends(require_label)):
    artist = await db.artists.find_one({"id": artist_id})
    if not artist:
        raise HTTPException(status_code=404, detail="Artist tidak ditemukan")
    label = await get_label_by_user(user)
    if artist["label_id"] != label["id"]:
        raise HTTPException(status_code=403, detail="Bukan artist Anda")
    upd = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    upd["updated_at"] = now_iso()
    await db.artists.update_one({"id": artist_id}, {"$set": upd})
    return await db.artists.find_one({"id": artist_id}, {"_id": 0})


# =============================================================================
#                              PAYMENTS (MOCK XENDIT)
# =============================================================================
pay_r = APIRouter(prefix="/payments", tags=["payments"])


@pay_r.post("/subscription")
async def create_subscription_invoice(user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    invoice_id = new_id()
    invoice = {
        "id": invoice_id,
        "label_id": label["id"],
        "release_id": None,
        "type": "annual_subscription",
        "xendit_invoice_id": f"mock_{invoice_id[:12]}",
        "xendit_invoice_url": f"/payments/mock-checkout/{invoice_id}",
        "amount": 500000,
        "currency": "IDR",
        "status": "pending",
        "paid_at": None,
        "expired_at": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
        "created_at": now_iso(),
    }
    await db.payments.insert_one(invoice)
    invoice.pop("_id", None)
    return invoice


@pay_r.post("/mock-pay/{invoice_id}")
async def mock_pay(invoice_id: str, user: dict = Depends(get_current_user)):
    """MOCK: simulate Xendit payment success. Will be replaced with real webhook later."""
    inv = await db.payments.find_one({"id": invoice_id})
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice tidak ditemukan")

    # Label can only pay their own; admin/super_admin can simulate any
    if user["role"] == LABEL_ROLE:
        label = await get_label_by_user(user)
        if inv["label_id"] != label["id"]:
            raise HTTPException(status_code=403, detail="Bukan invoice Anda")
    elif user["role"] not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Tidak diperbolehkan")

    if inv["status"] == "paid":
        return {"ok": True, "already_paid": True}

    await db.payments.update_one({"id": invoice_id}, {"$set": {"status": "paid", "paid_at": now_iso()}})

    if inv["type"] == "pay_per_release":
        await db.releases.update_one(
            {"id": inv["release_id"]},
            {"$set": {"payment_status": "paid", "status": "under_review", "updated_at": now_iso()}},
        )
    elif inv["type"] == "annual_subscription":
        now = datetime.now(timezone.utc)
        expires = (now + timedelta(days=365)).isoformat()
        await db.labels.update_one(
            {"id": inv["label_id"]},
            {"$set": {
                "subscription_status": "active",
                "subscription_expires_at": expires,
                "payment_type": "annual_subscription",
                "updated_at": now_iso(),
            }},
        )

    await log_activity(user["id"], "mock_pay", "payment", invoice_id)
    return {"ok": True, "invoice": await db.payments.find_one({"id": invoice_id}, {"_id": 0})}


@pay_r.post("/webhook/xendit")
async def xendit_webhook(payload: Dict[str, Any]):
    """Real Xendit webhook placeholder (idempotent). Not used in MVP mock flow."""
    invoice_id_external = payload.get("id") or payload.get("external_id")
    status = (payload.get("status") or "").lower()
    if not invoice_id_external:
        raise HTTPException(status_code=400, detail="Missing invoice id")
    inv = await db.payments.find_one({"xendit_invoice_id": invoice_id_external})
    if not inv:
        return {"ok": True, "ignored": True}
    if inv["status"] == "paid":
        return {"ok": True, "already_paid": True}
    if status == "paid":
        await db.payments.update_one({"id": inv["id"]}, {"$set": {"status": "paid", "paid_at": now_iso()}})
        if inv["type"] == "pay_per_release":
            await db.releases.update_one({"id": inv["release_id"]}, {"$set": {"payment_status": "paid", "status": "under_review", "updated_at": now_iso()}})
        elif inv["type"] == "annual_subscription":
            now = datetime.now(timezone.utc)
            await db.labels.update_one({"id": inv["label_id"]}, {"$set": {
                "subscription_status": "active",
                "subscription_expires_at": (now + timedelta(days=365)).isoformat(),
                "payment_type": "annual_subscription",
                "updated_at": now_iso(),
            }})
    elif status in ("expired", "failed", "cancelled"):
        await db.payments.update_one({"id": inv["id"]}, {"$set": {"status": status}})
    return {"ok": True}


# =============================================================================
#                                CMS
# =============================================================================
cms_r = APIRouter(prefix="/cms", tags=["cms"])


@cms_r.get("/landing")
async def get_landing(user: Optional[dict] = None):
    """Public endpoint — returns all landing page settings as key/value map."""
    settings = await db.landing_settings.find({}, {"_id": 0}).to_list(500)
    result = {s["key"]: s["value"] for s in settings}
    return result


@cms_r.patch("/landing")
async def update_landing(body: CMSUpdateIn, user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_content"):
        raise HTTPException(status_code=403, detail="Hanya Admin Content/CMS atau Super Admin")
    for k, v in body.settings.items():
        await db.landing_settings.update_one(
            {"key": k},
            {"$set": {"key": k, "value": v, "updated_by": user["id"], "updated_at": now_iso()}},
            upsert=True,
        )
    await log_activity(user["id"], "update_landing", "cms", None, after=body.settings)
    settings = await db.landing_settings.find({}, {"_id": 0}).to_list(500)
    return {s["key"]: s["value"] for s in settings}


@cms_r.post("/landing/upload-image")
async def upload_landing_image(file: UploadFile = File(...), user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_content"):
        raise HTTPException(status_code=403, detail="Hanya Admin Content/CMS atau Super Admin")
    ext = (file.filename or "").lower().split(".")[-1]
    if ext not in ("jpg", "jpeg", "png", "webp", "svg"):
        raise HTTPException(status_code=400, detail="Format gambar tidak didukung")
    fid = new_id()
    target = UPLOAD_DIR / "landing" / f"{fid}.{ext}"
    with open(target, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"url": f"/api/files/landing/{fid}.{ext}"}


# =============================================================================
#                                ADMIN
# =============================================================================
admin_r = APIRouter(prefix="/admin", tags=["admin"])


@admin_r.get("/dashboard")
async def admin_dashboard(user: dict = Depends(require_admin)):
    total_labels = await db.labels.count_documents({})
    total_artists = await db.artists.count_documents({})
    total_releases = await db.releases.count_documents({})
    pending_review = await db.releases.count_documents({"status": "under_review"})
    delivered = await db.releases.count_documents({"status": "delivered"})
    live = await db.releases.count_documents({"status": "live"})
    pending_invoices = await db.payments.count_documents({"status": "pending"})
    paid_invoices = await db.payments.count_documents({"status": "paid"})
    pending_withdraws = await db.withdraw_requests.count_documents({"status": "requested"})
    active_tickets = await db.support_tickets.count_documents({"status": {"$nin": ["done", "rejected"]}})
    active_subscriptions = await db.labels.count_documents({"subscription_status": "active"})
    suspended_labels = await db.labels.count_documents({"account_status": "suspended"})

    # total revenue EUR + IDR from royalty_lines
    revenue_pipeline = [
        {"$group": {"_id": None, "total_eur": {"$sum": "$revenue_eur"}, "total_idr": {"$sum": "$label_idr"}}},
    ]
    total_eur = 0
    total_idr = 0
    async for r in db.royalty_lines.aggregate(revenue_pipeline):
        total_eur = r.get("total_eur", 0)
        total_idr = r.get("total_idr", 0)

    last_csv = await db.royalty_imports.find_one({}, {"_id": 0}, sort=[("created_at", -1)])

    return {
        "total_labels": total_labels,
        "total_artists": total_artists,
        "total_releases": total_releases,
        "pending_review": pending_review,
        "delivered": delivered,
        "live": live,
        "pending_invoices": pending_invoices,
        "paid_invoices": paid_invoices,
        "pending_withdraws": pending_withdraws,
        "active_tickets": active_tickets,
        "active_subscriptions": active_subscriptions,
        "suspended_labels": suspended_labels,
        "total_revenue_eur": total_eur,
        "total_revenue_idr": total_idr,
        "last_csv_import": last_csv,
    }


@admin_r.get("/labels")
async def admin_list_labels(user: dict = Depends(require_admin), q: Optional[str] = None, status: Optional[str] = None):
    filt: Dict[str, Any] = {}
    if status:
        filt["account_status"] = status
    if q:
        filt["label_name"] = {"$regex": q, "$options": "i"}
    items = await db.labels.find(filt, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return items


@admin_r.get("/labels/{label_id}")
async def admin_get_label(label_id: str, user: dict = Depends(require_admin)):
    label = await db.labels.find_one({"id": label_id}, {"_id": 0})
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    bank = await db.bank_accounts.find_one({"label_id": label_id}, {"_id": 0})
    artists_count = await db.artists.count_documents({"label_id": label_id})
    releases_count = await db.releases.count_documents({"label_id": label_id})
    return {"label": label, "bank_account": bank, "artists_count": artists_count, "releases_count": releases_count}


@admin_r.patch("/labels/{label_id}")
async def admin_update_label(label_id: str, body: LabelStatusUpdate, user: dict = Depends(require_admin)):
    label = await db.labels.find_one({"id": label_id})
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    upd: Dict[str, Any] = {}
    if body.account_status is not None:
        upd["account_status"] = body.account_status
        if body.account_status == "blacklisted":
            upd["blacklisted"] = True
    if body.royalty_percentage_default is not None:
        # only super_admin or admin_finance
        if user["role"] not in ("super_admin", "admin_finance"):
            raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
        upd["royalty_percentage_default"] = body.royalty_percentage_default
        await db.royalty_percentage_history.insert_one({
            "id": new_id(),
            "label_id": label_id,
            "percentage": body.royalty_percentage_default,
            "effective_month": datetime.now(timezone.utc).strftime("%Y-%m"),
            "changed_by": user["id"],
            "changed_at": now_iso(),
            "reason": body.royalty_change_reason,
        })
    if upd:
        upd["updated_at"] = now_iso()
        await db.labels.update_one({"id": label_id}, {"$set": upd})
        await log_activity(user["id"], "update_label", "label", label_id, before=label, after=upd)
    return await db.labels.find_one({"id": label_id}, {"_id": 0})


@admin_r.get("/releases")
async def admin_list_releases(user: dict = Depends(require_admin), status: Optional[str] = None, q: Optional[str] = None):
    filt: Dict[str, Any] = {}
    if status:
        filt["status"] = status
    if q:
        filt["release_title"] = {"$regex": q, "$options": "i"}
    items = await db.releases.find(filt, {"_id": 0}).sort("created_at", -1).to_list(1000)
    # enrich with label_name
    label_ids = list({i["label_id"] for i in items})
    labels = await db.labels.find({"id": {"$in": label_ids}}, {"_id": 0, "id": 1, "label_name": 1}).to_list(1000)
    name_map = {lab["id"]: lab["label_name"] for lab in labels}
    for it in items:
        it["label_name"] = name_map.get(it["label_id"])
    return items


@admin_r.get("/artists")
async def admin_list_artists(user: dict = Depends(require_admin), q: Optional[str] = None):
    filt: Dict[str, Any] = {}
    if q:
        filt["artist_name"] = {"$regex": q, "$options": "i"}
    items = await db.artists.find(filt, {"_id": 0}).sort("created_at", -1).to_list(1000)
    label_ids = list({i["label_id"] for i in items})
    labels = await db.labels.find({"id": {"$in": label_ids}}, {"_id": 0, "id": 1, "label_name": 1}).to_list(1000)
    name_map = {lab["id"]: lab["label_name"] for lab in labels}
    for it in items:
        it["label_name"] = name_map.get(it["label_id"])
    return items


@admin_r.get("/payments")
async def admin_list_payments(user: dict = Depends(require_admin), status: Optional[str] = None, ptype: Optional[str] = None):
    filt: Dict[str, Any] = {}
    if status:
        filt["status"] = status
    if ptype:
        filt["type"] = ptype
    items = await db.payments.find(filt, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return items


@admin_r.get("/admin-users")
async def admin_list_admin_users(user: dict = Depends(require_super_admin)):
    items = await db.users.find({"role": {"$in": list(ADMIN_ROLES)}}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(500)
    return items


@admin_r.post("/admin-users")
async def admin_create_admin_user(body: AdminUserCreateIn, user: dict = Depends(require_super_admin)):
    email = body.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Email sudah terdaftar")
    user_id = new_id()
    doc = {
        "id": user_id,
        "name": body.name,
        "email": email,
        "password_hash": hash_password(body.password),
        "role": body.role,
        "email_verified_at": now_iso(),  # admins are auto-verified
        "status": "active",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.users.insert_one(doc)
    doc.pop("_id", None)
    doc.pop("password_hash", None)
    return doc


@admin_r.patch("/admin-users/{user_id}")
async def admin_update_admin_user(user_id: str, body: Dict[str, Any], user: dict = Depends(require_super_admin)):
    target = await db.users.find_one({"id": user_id})
    if not target or target.get("role") not in ADMIN_ROLES:
        raise HTTPException(status_code=404, detail="Admin user tidak ditemukan")
    upd = {}
    if "role" in body and body["role"] in ADMIN_ROLES:
        upd["role"] = body["role"]
    if "status" in body and body["status"] in ("active", "suspended"):
        upd["status"] = body["status"]
    if "name" in body:
        upd["name"] = body["name"]
    if "password" in body and body["password"]:
        upd["password_hash"] = hash_password(body["password"])
    if upd:
        upd["updated_at"] = now_iso()
        await db.users.update_one({"id": user_id}, {"$set": upd})
    return await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})


@admin_r.get("/activity-logs")
async def admin_activity_logs(user: dict = Depends(require_admin), limit: int = 200):
    items = await db.activity_logs.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return items


# =============================================================================
#                              ROYALTY (ADMIN + LABEL/ARTIST)
# =============================================================================
royalty_r = APIRouter(prefix="/royalty", tags=["royalty"])


def _match_line(row: Dict[str, Any], col_idx: Dict[str, Optional[int]], headers: List[str]) -> Dict[str, Any]:
    """Extract raw fields from a CSV row using detected columns."""
    def get(key: str) -> Optional[str]:
        idx = col_idx.get(key)
        if idx is None:
            return None
        # row dict keys are normalized headers
        h = normalize_header(headers[idx]) if idx < len(headers) else None
        return row.get(h) if h else None

    return {
        "isrc": (get("isrc") or "").strip() or None,
        "upc": (get("upc") or "").strip() or None,
        "track_title": (get("track_title") or "").strip() or None,
        "artist_name": (get("artist_name") or "").strip() or None,
        "release_title": (get("release_title") or "").strip() or None,
        "label_name": (get("label_name") or "").strip() or None,
        "platform": (get("platform") or "").strip() or None,
        "country": (get("country") or "").strip() or None,
        "quantity": int(parse_amount(get("quantity") or "0") or 0),
        "revenue_eur": parse_amount(get("revenue_eur") or "0"),
        # Admin-only / sensitive (will be stripped from label/artist responses)
        "gross_revenue_eur": parse_amount(get("gross_revenue_eur") or "0") or None,
        "unit_price_eur": parse_amount(get("unit_price_eur") or "0") or None,
        "mechanical_cost_eur": parse_amount(get("mechanical_cost_eur") or "0") or None,
        "client_share_rate": parse_amount(get("client_share_rate") or "0") or None,
        # Optional metadata
        "sales_type": (get("sales_type") or "").strip() or None,
        "subscription_type": (get("subscription_type") or "").strip() or None,
        "row_period": parse_period_from_value(get("period")),
    }


@royalty_r.post("/admin/imports")
async def admin_upload_royalty_csv(
    period: str = Form(...),
    rate_eur_idr: float = Form(...),
    file: UploadFile = File(...),
    note: Optional[str] = Form(None),
    user: dict = Depends(require_admin),
):
    """Upload CSV royalti Believe. Hanya menyimpan + parsing + matching. Belum mempengaruhi saldo."""
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    # validate period
    try:
        datetime.strptime(period, "%Y-%m")
    except Exception:
        raise HTTPException(status_code=400, detail="Format period harus YYYY-MM")
    if rate_eur_idr <= 0:
        raise HTTPException(status_code=400, detail="Kurs harus > 0")

    content = await file.read()
    headers, rows = parse_csv_bytes(content)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV kosong atau tidak terbaca")
    col_idx = detect_columns(headers)
    if col_idx["revenue_eur"] is None:
        raise HTTPException(status_code=400, detail="Kolom revenue/amount tidak ditemukan di CSV")

    import_id = new_id()
    # save file
    target = UPLOAD_DIR / "csv" / f"{import_id}.csv"
    with open(target, "wb") as f:
        f.write(content)
    file_url = f"/api/files/csv/{import_id}.csv"

    # cache fee + percent history
    fee_settings = await db.landing_settings.find_one({"key": "pricing"})
    fee_percent = float((fee_settings or {}).get("value", {}).get("distributor_fee_percent", 5) or 5)

    # Pre-fetch all labels + tracks for matching
    all_tracks = {}
    async for t in db.tracks.find({"isrc": {"$exists": True, "$ne": None}}, {"_id": 0, "id": 1, "isrc": 1, "release_id": 1, "label_id": 1, "artist_id": 1, "track_title": 1, "artist_name": 1}):
        if t.get("isrc"):
            all_tracks[(t["isrc"] or "").strip().upper()] = t

    all_releases_by_upc = {}
    async for r in db.releases.find({"upc": {"$exists": True, "$ne": None}}, {"_id": 0, "id": 1, "upc": 1, "label_id": 1, "release_title": 1}):
        if r.get("upc"):
            all_releases_by_upc[(r["upc"] or "").strip().upper()] = r

    # Pre-fetch all labels' percentage history
    labels = {lab["id"]: lab async for lab in db.labels.find({}, {"_id": 0})}
    labels_by_name = {(lab.get("label_name") or "").strip().lower(): lab for lab in labels.values()}
    pct_history: Dict[str, List[Dict[str, Any]]] = {}
    async for h in db.royalty_percentage_history.find({}, {"_id": 0}):
        pct_history.setdefault(h["label_id"], []).append(h)

    total_revenue_eur = 0.0
    total_label_idr = 0
    matched = 0
    unmatched = 0
    line_docs: List[Dict[str, Any]] = []

    for row in rows:
        raw = _match_line(row, col_idx, headers)
        revenue_eur = raw["revenue_eur"]
        total_revenue_eur += revenue_eur

        track = None
        release = None
        label_id = None
        match_by = None
        # Try ISRC match
        if raw["isrc"]:
            t = all_tracks.get(raw["isrc"].upper())
            if t:
                track = t
                label_id = t["label_id"]
                match_by = "isrc"
        # Try UPC match
        if not label_id and raw["upc"]:
            r = all_releases_by_upc.get(raw["upc"].upper())
            if r:
                release = r
                label_id = r["label_id"]
                match_by = "upc"
        # Fallback: match by label name (lowercase)
        if not label_id and raw["label_name"]:
            lab = labels_by_name.get(raw["label_name"].strip().lower())
            if lab:
                label_id = lab["id"]
                match_by = "label_name"

        match_status = "matched" if label_id else "unmatched"
        if match_status == "matched":
            matched += 1
            label = labels.get(label_id, {})
            default_pct = float(label.get("royalty_percentage_default", 60) or 60)
            history = pct_history.get(label_id, [])
            label_pct = label_percentage_at(history, default_pct, period)
            calc = calculate_line(revenue_eur, fee_percent, label_pct, rate_eur_idr)
            total_label_idr += calc["label_idr"]
        else:
            unmatched += 1
            label_pct = 0.0
            calc = calculate_line(revenue_eur, fee_percent, 0.0, rate_eur_idr)

        line_docs.append({
            "id": new_id(),
            "import_id": import_id,
            "period": period,
            "isrc": raw["isrc"],
            "upc": raw["upc"],
            "track_title_raw": raw["track_title"],
            "artist_name_raw": raw["artist_name"],
            "release_title_raw": raw["release_title"],
            "label_name_raw": raw["label_name"],
            "platform": raw["platform"],
            "country": raw["country"],
            "quantity": raw["quantity"],
            "revenue_eur": revenue_eur,
            "sales_type": raw.get("sales_type"),
            "subscription_type": raw.get("subscription_type"),
            "row_period": raw.get("row_period"),
            # admin-only sensitive fields:
            "gross_revenue_eur": raw.get("gross_revenue_eur"),
            "unit_price_eur": raw.get("unit_price_eur"),
            "mechanical_cost_eur": raw.get("mechanical_cost_eur"),
            "client_share_rate": raw.get("client_share_rate"),
            "track_id": track["id"] if track else None,
            "release_id": (track or release or {}).get("release_id") or (release or {}).get("id"),
            "label_id": label_id,
            "artist_id": track.get("artist_id") if track else None,
            "match_by": match_by,
            "label_percentage_applied": label_pct,
            "fee_percent_applied": fee_percent,
            "exchange_rate": rate_eur_idr,
            **calc,
            "match_status": match_status,
            "status": "draft",  # draft -> pending (on publish) -> available (when dana received)
            "created_at": now_iso(),
        })

    if line_docs:
        await db.royalty_lines.insert_many(line_docs)

    import_doc = {
        "id": import_id,
        "period": period,
        "source": "believe",
        "filename": file.filename,
        "file_url": file_url,
        "exchange_rate_eur_idr": rate_eur_idr,
        "fee_percent": fee_percent,
        "total_lines": len(line_docs),
        "matched_lines": matched,
        "unmatched_lines": unmatched,
        "total_revenue_eur": round(total_revenue_eur, 4),
        "total_label_idr": total_label_idr,
        "status": "pending_review",  # pending_review -> published -> dana_received
        "dana_received_at": None,
        "published_at": None,
        "uploaded_by": user["id"],
        "note": note,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.royalty_imports.insert_one(import_doc)
    await log_activity(user["id"], "upload_royalty_csv", "royalty", import_id, after={"period": period, "matched": matched, "unmatched": unmatched})
    import_doc.pop("_id", None)
    return import_doc


@royalty_r.get("/admin/imports")
async def admin_list_imports(user: dict = Depends(require_admin)):
    items = await db.royalty_imports.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return items


@royalty_r.get("/admin/imports/{import_id}")
async def admin_get_import(import_id: str, user: dict = Depends(require_admin)):
    imp = await db.royalty_imports.find_one({"id": import_id}, {"_id": 0})
    if not imp:
        raise HTTPException(status_code=404, detail="Import tidak ditemukan")
    lines = await db.royalty_lines.find({"import_id": import_id}, {"_id": 0}).sort("revenue_eur", -1).limit(500).to_list(500)

    # per-label breakdown
    pipeline = [
        {"$match": {"import_id": import_id, "label_id": {"$ne": None}}},
        {"$group": {"_id": "$label_id", "total_idr": {"$sum": "$label_idr"}, "total_eur": {"$sum": "$revenue_eur"}, "lines": {"$sum": 1}}},
        {"$sort": {"total_idr": -1}},
    ]
    per_label = []
    async for r in db.royalty_lines.aggregate(pipeline):
        label = await db.labels.find_one({"id": r["_id"]}, {"_id": 0, "label_name": 1, "id": 1})
        per_label.append({**r, "label": label})

    return {"import": imp, "lines": lines, "per_label": per_label}


@royalty_r.post("/admin/imports/{import_id}/line/{line_id}/match")
async def admin_manually_match_line(import_id: str, line_id: str, body: RoyaltyLineMatchIn, user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    imp = await db.royalty_imports.find_one({"id": import_id})
    if not imp:
        raise HTTPException(status_code=404, detail="Import tidak ditemukan")
    if imp["status"] not in ("pending_review",):
        raise HTTPException(status_code=400, detail="Hanya bisa diubah saat status pending_review")
    line = await db.royalty_lines.find_one({"id": line_id, "import_id": import_id})
    if not line:
        raise HTTPException(status_code=404, detail="Line tidak ditemukan")
    if not body.track_id:
        raise HTTPException(status_code=400, detail="track_id wajib")
    track = await db.tracks.find_one({"id": body.track_id})
    if not track:
        raise HTTPException(status_code=404, detail="Track tidak ditemukan")
    label = await db.labels.find_one({"id": track["label_id"]}, {"_id": 0})
    history = await db.royalty_percentage_history.find({"label_id": track["label_id"]}, {"_id": 0}).to_list(500)
    label_pct = label_percentage_at(history, float(label.get("royalty_percentage_default", 60) or 60), imp["period"])
    calc = calculate_line(line["revenue_eur"], imp["fee_percent"], label_pct, imp["exchange_rate_eur_idr"])
    new_total_label_idr = imp["total_label_idr"] - line.get("label_idr", 0) + calc["label_idr"]
    await db.royalty_lines.update_one({"id": line_id}, {"$set": {
        "track_id": track["id"],
        "release_id": track["release_id"],
        "label_id": track["label_id"],
        "artist_id": track.get("artist_id"),
        "label_percentage_applied": label_pct,
        **calc,
        "match_status": "manually_matched",
    }})
    await db.royalty_imports.update_one({"id": import_id}, {
        "$inc": {"matched_lines": 1, "unmatched_lines": -1 if line["match_status"] == "unmatched" else 0},
        "$set": {"total_label_idr": new_total_label_idr, "updated_at": now_iso()},
    })
    return await db.royalty_lines.find_one({"id": line_id}, {"_id": 0})


@royalty_r.post("/admin/imports/{import_id}/publish")
async def admin_publish_import(import_id: str, body: RoyaltyImportPublishIn, user: dict = Depends(require_admin)):
    """Publish CSV → moves all matched lines to status=pending and accumulates to label.balance_pending_idr."""
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    imp = await db.royalty_imports.find_one({"id": import_id})
    if not imp:
        raise HTTPException(status_code=404, detail="Import tidak ditemukan")
    if imp["status"] != "pending_review":
        raise HTTPException(status_code=400, detail="Import sudah dipublish atau status tidak valid")

    # Aggregate per label & notify
    pipeline = [
        {"$match": {"import_id": import_id, "match_status": {"$in": ["matched", "manually_matched"]}}},
        {"$group": {"_id": "$label_id", "total_idr": {"$sum": "$label_idr"}}},
    ]
    per_label = []
    async for r in db.royalty_lines.aggregate(pipeline):
        per_label.append(r)
        await db.labels.update_one({"id": r["_id"]}, {"$inc": {"balance_pending_idr": int(r["total_idr"])}, "$set": {"updated_at": now_iso()}})
        await db.balance_transactions.insert_one({
            "id": new_id(),
            "label_id": r["_id"],
            "type": "royalty_pending",
            "amount_idr": int(r["total_idr"]),
            "reference_type": "royalty_import",
            "reference_id": import_id,
            "description": f"Royalti periode {imp['period']} ke saldo pending",
            "created_at": now_iso(),
        })

    await db.royalty_lines.update_many(
        {"import_id": import_id, "match_status": {"$in": ["matched", "manually_matched"]}},
        {"$set": {"status": "pending"}},
    )
    await db.royalty_imports.update_one({"id": import_id}, {"$set": {"status": "published", "published_at": now_iso(), "updated_at": now_iso()}})
    await log_activity(user["id"], "publish_royalty", "royalty", import_id)
    # Notify each label with a personalized amount
    for r in per_label:
        user_ids = await _label_user_ids(r["_id"])
        amt = f"Rp {int(r['total_idr']):,}".replace(",", ".")
        await notify_many(
            user_ids, "royalty_published",
            f"Royalti periode {imp['period']} terbit",
            f"{amt} masuk ke saldo pending. Lihat detail di dashboard.",
            "/label/royalty", {"period": imp["period"]},
        )
    return await db.royalty_imports.find_one({"id": import_id}, {"_id": 0})


@royalty_r.post("/admin/imports/{import_id}/mark-dana-received")
async def admin_mark_dana_received(import_id: str, user: dict = Depends(require_admin)):
    """Saat dana Believe masuk: pindahkan saldo pending → available."""
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    imp = await db.royalty_imports.find_one({"id": import_id})
    if not imp:
        raise HTTPException(status_code=404, detail="Import tidak ditemukan")
    if imp["status"] != "published":
        raise HTTPException(status_code=400, detail="Import harus dipublish terlebih dahulu")
    if imp.get("dana_received_at"):
        raise HTTPException(status_code=400, detail="Dana sudah ditandai diterima")

    pipeline = [
        {"$match": {"import_id": import_id, "status": "pending"}},
        {"$group": {"_id": "$label_id", "total_idr": {"$sum": "$label_idr"}}},
    ]
    async for r in db.royalty_lines.aggregate(pipeline):
        await db.labels.update_one({"id": r["_id"]}, {"$inc": {
            "balance_pending_idr": -int(r["total_idr"]),
            "balance_available_idr": int(r["total_idr"]),
        }, "$set": {"updated_at": now_iso()}})
        await db.balance_transactions.insert_one({
            "id": new_id(),
            "label_id": r["_id"],
            "type": "royalty_available",
            "amount_idr": int(r["total_idr"]),
            "reference_type": "royalty_import",
            "reference_id": import_id,
            "description": f"Dana royalti periode {imp['period']} diterima — saldo tersedia",
            "created_at": now_iso(),
        })

    await db.royalty_lines.update_many({"import_id": import_id, "status": "pending"}, {"$set": {"status": "available"}})
    await db.royalty_imports.update_one({"id": import_id}, {"$set": {"status": "dana_received", "dana_received_at": now_iso(), "updated_at": now_iso()}})
    await log_activity(user["id"], "mark_dana_received", "royalty", import_id)
    return await db.royalty_imports.find_one({"id": import_id}, {"_id": 0})


@royalty_r.post("/admin/reset-demo-data")
async def admin_reset_demo_royalty_data(
    confirm: str = Form(...),
    user: dict = Depends(require_admin),
):
    """⚠️ DANGER ZONE — Wipe all royalty data (imports + lines + balance transactions)
    and reset every label's balance to zero. Used to clear dummy data before going live.
    Requires confirm='RESET' to proceed. Super Admin only.
    """
    if user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Hanya Super Admin")
    if confirm != "RESET":
        raise HTTPException(status_code=400, detail="Konfirmasi tidak cocok. Ketik 'RESET' untuk melanjutkan.")

    n_imports = (await db.royalty_imports.delete_many({})).deleted_count
    n_lines = (await db.royalty_lines.delete_many({})).deleted_count
    n_tx = (await db.balance_transactions.delete_many({"type": {"$in": ["royalty_pending", "royalty_available"]}})).deleted_count
    n_labels = (await db.labels.update_many({}, {"$set": {
        "balance_pending_idr": 0,
        "balance_available_idr": 0,
        "updated_at": now_iso(),
    }})).modified_count
    # Also delete uploaded CSV files
    csv_dir = UPLOAD_DIR / "csv"
    deleted_files = 0
    if csv_dir.exists():
        for p in csv_dir.iterdir():
            if p.is_file():
                try:
                    p.unlink()
                    deleted_files += 1
                except Exception:
                    pass
    await log_activity(user["id"], "reset_demo_royalty", "system", "all", after={
        "imports": n_imports, "lines": n_lines, "transactions": n_tx,
        "labels_reset": n_labels, "files_deleted": deleted_files,
    })
    return {
        "ok": True,
        "imports_deleted": n_imports,
        "lines_deleted": n_lines,
        "transactions_deleted": n_tx,
        "labels_reset": n_labels,
        "csv_files_deleted": deleted_files,
    }


# -------- LABEL royalty endpoints --------
@royalty_r.get("/months")
async def label_royalty_months(user: dict = Depends(get_current_user)):
    """List periods that have published royalty data visible to the current user."""
    if user["role"] == LABEL_ROLE:
        label = await get_label_by_user(user)
        filt = {"label_id": label["id"], "status": {"$in": ["pending", "available", "withdrawn"]}}
    elif user["role"] == ARTIST_ROLE:
        filt = {"artist_id": user["id"], "status": {"$in": ["pending", "available", "withdrawn"]}}
    elif user["role"] in ADMIN_ROLES:
        filt = {"status": {"$in": ["pending", "available", "withdrawn"]}}
    else:
        raise HTTPException(status_code=403, detail="Tidak diperbolehkan")
    months = await db.royalty_lines.distinct("period", filt)
    months.sort(reverse=True)
    return months


@royalty_r.get("/summary")
async def label_royalty_summary(user: dict = Depends(get_current_user), period: Optional[str] = None):
    if user["role"] == LABEL_ROLE:
        label = await get_label_by_user(user)
        base = {"label_id": label["id"]}
    elif user["role"] == ARTIST_ROLE:
        base = {"artist_id": user["id"]}
    else:
        raise HTTPException(status_code=403, detail="Tidak diperbolehkan")
    if period:
        base["period"] = period

    pipeline = [
        {"$match": {**base, "status": {"$in": ["pending", "available", "withdrawn"]}}},
        {"$group": {
            "_id": None,
            "total_idr": {"$sum": "$label_idr"},
            "total_streams": {"$sum": "$quantity"},
            "total_lines": {"$sum": 1},
        }},
    ]
    summary = {"total_idr": 0, "total_streams": 0, "total_lines": 0}
    async for row in db.royalty_lines.aggregate(pipeline):
        summary = {"total_idr": row["total_idr"], "total_streams": row["total_streams"], "total_lines": row["total_lines"]}

    # per-platform
    by_platform = []
    async for row in db.royalty_lines.aggregate([
        {"$match": {**base, "status": {"$in": ["pending", "available", "withdrawn"]}}},
        {"$group": {"_id": "$platform", "total_idr": {"$sum": "$label_idr"}, "streams": {"$sum": "$quantity"}}},
        {"$sort": {"total_idr": -1}},
    ]):
        by_platform.append({"platform": row["_id"] or "Unknown", "total_idr": row["total_idr"], "streams": row["streams"]})

    by_country = []
    async for row in db.royalty_lines.aggregate([
        {"$match": {**base, "status": {"$in": ["pending", "available", "withdrawn"]}}},
        {"$group": {"_id": "$country", "total_idr": {"$sum": "$label_idr"}}},
        {"$sort": {"total_idr": -1}},
        {"$limit": 10},
    ]):
        by_country.append({"country": row["_id"] or "Unknown", "total_idr": row["total_idr"]})

    by_track = []
    async for row in db.royalty_lines.aggregate([
        {"$match": {**base, "status": {"$in": ["pending", "available", "withdrawn"]}}},
        {"$group": {"_id": {"track_id": "$track_id", "title": "$track_title_raw"}, "total_idr": {"$sum": "$label_idr"}, "streams": {"$sum": "$quantity"}}},
        {"$sort": {"total_idr": -1}},
        {"$limit": 15},
    ]):
        by_track.append({"track_id": row["_id"].get("track_id"), "title": row["_id"].get("title") or "Unknown", "total_idr": row["total_idr"], "streams": row["streams"]})

    return {"summary": summary, "by_platform": by_platform, "by_country": by_country, "by_track": by_track}


@royalty_r.get("/lines")
async def label_royalty_lines(
    user: dict = Depends(get_current_user),
    period: Optional[str] = None,
    platform: Optional[str] = None,
    country: Optional[str] = None,
    track_id: Optional[str] = None,
    artist_id: Optional[str] = None,
    limit: int = 500,
):
    filt: Dict[str, Any] = {"status": {"$in": ["pending", "available", "withdrawn"]}}
    if user["role"] == LABEL_ROLE:
        label = await get_label_by_user(user)
        filt["label_id"] = label["id"]
    elif user["role"] == ARTIST_ROLE:
        filt["artist_id"] = user["id"]
    elif user["role"] in ADMIN_ROLES:
        pass
    else:
        raise HTTPException(status_code=403, detail="Tidak diperbolehkan")
    if period:
        filt["period"] = period
    if platform:
        filt["platform"] = platform
    if country:
        filt["country"] = country
    if track_id:
        filt["track_id"] = track_id
    if artist_id:
        filt["artist_id"] = artist_id
    items = await db.royalty_lines.find(filt, {"_id": 0}).sort("label_idr", -1).limit(limit).to_list(limit)
    # Hide sensitive fields from label/artist responses
    if user["role"] in (LABEL_ROLE, ARTIST_ROLE):
        items = [strip_sensitive(it) for it in items]
    return items


@royalty_r.get("/export.csv")
async def label_royalty_export_csv(
    user: dict = Depends(get_current_user),
    period: Optional[str] = None,
):
    """Stream CSV export of royalty lines for the current label/period."""
    from fastapi.responses import StreamingResponse
    filt: Dict[str, Any] = {"status": {"$in": ["pending", "available", "withdrawn"]}}
    if user["role"] == LABEL_ROLE:
        label = await get_label_by_user(user)
        filt["label_id"] = label["id"]
    elif user["role"] == ARTIST_ROLE:
        filt["artist_id"] = user["id"]
    else:
        raise HTTPException(status_code=403, detail="Tidak diperbolehkan")
    if period:
        filt["period"] = period

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "period", "release_title", "track_title", "artist_name", "platform", "country",
        "isrc", "upc", "streams", "revenue_eur", "label_percent_applied", "label_idr", "status",
    ])
    cursor = db.royalty_lines.find(filt, {"_id": 0}).sort("period", -1)
    async for it in cursor:
        writer.writerow([
            it.get("period"),
            it.get("release_title_raw"),
            it.get("track_title_raw"),
            it.get("artist_name_raw"),
            it.get("platform"),
            it.get("country"),
            it.get("isrc"),
            it.get("upc"),
            it.get("quantity"),
            it.get("revenue_eur"),
            it.get("label_percentage_applied"),
            it.get("label_idr"),
            it.get("status"),
        ])
    buf.seek(0)
    filename = f"royalty_{period or 'all'}.csv"
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


# =============================================================================
#                              WITHDRAW
# =============================================================================
withdraw_r = APIRouter(prefix="/withdraw", tags=["withdraw"])


@withdraw_r.get("/window")
async def get_window_state(user: dict = Depends(get_current_user)):
    return withdraw_window_state()


@withdraw_r.post("/label/request")
async def label_request_withdraw(body: WithdrawRequestIn, user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    state = withdraw_window_state()
    if not state["request_open"]:
        raise HTTPException(status_code=400, detail=f"Permintaan withdraw ditutup. {state['message']}")
    if body.amount_idr < MIN_WITHDRAW_IDR:
        raise HTTPException(status_code=400, detail=f"Minimum withdraw Rp {MIN_WITHDRAW_IDR:,.0f}")
    if body.amount_idr > (label.get("balance_available_idr") or 0):
        raise HTTPException(status_code=400, detail="Saldo tersedia tidak mencukupi")
    if not label.get("bank_verified"):
        # MVP: allow if bank account exists; admin must verify it manually
        bank = await db.bank_accounts.find_one({"label_id": label["id"]})
        if not bank:
            raise HTTPException(status_code=400, detail="Rekening bank belum diinput")
    bank = await db.bank_accounts.find_one({"label_id": label["id"]}, {"_id": 0})

    wd_id = new_id()
    await db.labels.update_one({"id": label["id"]}, {"$inc": {
        "balance_available_idr": -body.amount_idr,
        "balance_withdraw_requested_idr": body.amount_idr,
    }, "$set": {"updated_at": now_iso()}})
    await db.balance_transactions.insert_one({
        "id": new_id(),
        "label_id": label["id"],
        "type": "withdraw_request",
        "amount_idr": -body.amount_idr,
        "reference_type": "withdraw",
        "reference_id": wd_id,
        "description": "Withdraw diminta",
        "created_at": now_iso(),
    })
    wd = {
        "id": wd_id,
        "label_id": label["id"],
        "amount_idr": body.amount_idr,
        "status": "requested",
        "request_date": now_iso(),
        "approved_date": None,
        "paid_date": None,
        "approved_by": None,
        "paid_by": None,
        "bank_snapshot": bank,
        "payment_proof_url": None,
        "payment_reference": None,
        "admin_note": None,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.withdraw_requests.insert_one(wd)
    await log_activity(user["id"], "withdraw_request", "withdraw", wd_id, after={"amount_idr": body.amount_idr})
    wd.pop("_id", None)
    return wd


@withdraw_r.get("/label")
async def label_list_withdraws(user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    items = await db.withdraw_requests.find({"label_id": label["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return items


@withdraw_r.get("/admin")
async def admin_list_withdraws(user: dict = Depends(require_admin), status: Optional[str] = None):
    filt: Dict[str, Any] = {}
    if status:
        filt["status"] = status
    items = await db.withdraw_requests.find(filt, {"_id": 0}).sort("created_at", -1).to_list(500)
    # enrich with label_name
    label_ids = list({i["label_id"] for i in items})
    labels = await db.labels.find({"id": {"$in": label_ids}}, {"_id": 0, "id": 1, "label_name": 1}).to_list(1000)
    name_map = {lab["id"]: lab["label_name"] for lab in labels}
    for it in items:
        it["label_name"] = name_map.get(it["label_id"])
    return items


@withdraw_r.post("/admin/{wd_id}/action")
async def admin_withdraw_action(wd_id: str, body: WithdrawAdminAction, user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    wd = await db.withdraw_requests.find_one({"id": wd_id})
    if not wd:
        raise HTTPException(status_code=404, detail="Withdraw tidak ditemukan")

    if body.action == "approve":
        if wd["status"] != "requested":
            raise HTTPException(status_code=400, detail="Hanya request yang bisa di-approve")
        await db.withdraw_requests.update_one({"id": wd_id}, {"$set": {
            "status": "approved", "approved_date": now_iso(), "approved_by": user["id"], "admin_note": body.note, "updated_at": now_iso(),
        }})
    elif body.action == "reject":
        if wd["status"] not in ("requested", "approved"):
            raise HTTPException(status_code=400, detail="Tidak bisa ditolak pada status saat ini")
        # refund balance
        await db.labels.update_one({"id": wd["label_id"]}, {"$inc": {
            "balance_available_idr": wd["amount_idr"],
            "balance_withdraw_requested_idr": -wd["amount_idr"],
        }, "$set": {"updated_at": now_iso()}})
        await db.balance_transactions.insert_one({
            "id": new_id(), "label_id": wd["label_id"], "type": "withdraw_refund",
            "amount_idr": wd["amount_idr"], "reference_type": "withdraw", "reference_id": wd_id,
            "description": f"Withdraw ditolak — refund ke saldo tersedia. {body.note or ''}",
            "created_at": now_iso(),
        })
        await db.withdraw_requests.update_one({"id": wd_id}, {"$set": {
            "status": "rejected", "admin_note": body.note, "updated_at": now_iso(),
        }})
    elif body.action == "mark_paid":
        if wd["status"] != "approved":
            raise HTTPException(status_code=400, detail="Hanya yang sudah approved bisa di-mark paid")
        # Finance dapat memproses kapan saja; window 15-20 hanya sebagai panduan operasional.
        await db.labels.update_one({"id": wd["label_id"]}, {"$inc": {
            "balance_withdraw_requested_idr": -wd["amount_idr"],
        }, "$set": {"updated_at": now_iso()}})
        await db.balance_transactions.insert_one({
            "id": new_id(), "label_id": wd["label_id"], "type": "withdraw_paid",
            "amount_idr": -wd["amount_idr"], "reference_type": "withdraw", "reference_id": wd_id,
            "description": f"Withdraw dibayar. Ref: {body.payment_reference or '-'}",
            "created_at": now_iso(),
        })
        # mark linked royalty_lines as withdrawn for this label (FIFO simplified: mark proportionally is complex; for MVP we don't lock specific lines)
        await db.withdraw_requests.update_one({"id": wd_id}, {"$set": {
            "status": "paid", "paid_date": now_iso(), "paid_by": user["id"],
            "payment_proof_url": body.payment_proof_url, "payment_reference": body.payment_reference,
            "admin_note": body.note, "updated_at": now_iso(),
        }})
    else:
        raise HTTPException(status_code=400, detail="Aksi tidak dikenal")

    await log_activity(user["id"], f"withdraw_{body.action}", "withdraw", wd_id)
    # Notify label
    wd = await db.withdraw_requests.find_one({"id": wd_id}, {"_id": 0})
    user_ids = await _label_user_ids(wd["label_id"])
    titles = {
        "approve": ("Withdraw disetujui", "Permintaan withdraw Anda telah disetujui. Menunggu pembayaran."),
        "reject": ("Withdraw ditolak", f"Permintaan withdraw ditolak. Alasan: {body.note or 'Lihat detail'}"),
        "mark_paid": ("Withdraw dibayar ✓", "Pembayaran telah dilakukan. Cek bukti transfer di dashboard."),
    }
    if body.action in titles:
        title, msg = titles[body.action]
        await notify_many(user_ids, f"withdraw_{body.action}", title, msg, "/label/withdraw", {"withdraw_id": wd_id})
    return wd


@withdraw_r.post("/admin/upload-proof")
async def admin_upload_proof(file: UploadFile = File(...), user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    ext = (file.filename or "").lower().split(".")[-1]
    if ext not in ("jpg", "jpeg", "png", "pdf"):
        raise HTTPException(status_code=400, detail="Format harus JPG/PNG/PDF")
    fid = new_id()
    target = UPLOAD_DIR / "contract" / f"proof_{fid}.{ext}"
    with open(target, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"url": f"/api/files/contract/proof_{fid}.{ext}"}


@withdraw_r.post("/admin/verify-bank/{label_id}")
async def admin_verify_bank(label_id: str, user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    bank = await db.bank_accounts.find_one({"label_id": label_id})
    if not bank:
        raise HTTPException(status_code=404, detail="Rekening tidak ditemukan")
    await db.bank_accounts.update_one({"label_id": label_id}, {"$set": {"verified_status": "verified", "verified_by": user["id"], "verified_at": now_iso()}})
    await db.labels.update_one({"id": label_id}, {"$set": {"bank_verified": True, "updated_at": now_iso()}})
    await log_activity(user["id"], "verify_bank", "label", label_id)
    return {"ok": True}


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
async def list_ticket_categories(user: dict = Depends(get_current_user)):
    return [{"value": k, "label": v} for k, v in TICKET_CATEGORY_LABELS.items()]


@ticket_r.post("/upload-attachment")
async def upload_ticket_attachment(
    file: UploadFile = File(...),
    purpose: str = Form("general"),  # general | audio | cover
    user: dict = Depends(get_current_user),
):
    """Upload attachment for ticket (audio WAV for edit_audio, cover for edit_cover, or generic attachment)."""
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
        target = UPLOAD_DIR / "cover" / f"ticket_{fid}.{ext}"
        with open(target, "wb") as f:
            f.write(contents)
        return {"url": f"/api/files/cover/ticket_{fid}.{ext}", "filename": file.filename}
    else:
        if ext not in ("jpg", "jpeg", "png", "pdf", "wav", "mp3", "txt", "docx", "doc"):
            raise HTTPException(status_code=400, detail="Format file tidak didukung")
        sub = "ticket"
    # generic streaming write
    fid = new_id()
    target = UPLOAD_DIR / sub / f"ticket_{fid}.{ext}"
    with open(target, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"url": f"/api/files/{sub}/ticket_{fid}.{ext}", "filename": file.filename}


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
    admin_ids = await _admin_user_ids(("super_admin", "admin_support", "admin_release"))
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
async def get_ticket(ticket_id: str, user: dict = Depends(get_current_user)):
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
async def post_ticket_comment(ticket_id: str, body: TicketCommentIn, user: dict = Depends(get_current_user)):
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


# =============================================================================
#                              NOTIFICATIONS
# =============================================================================
notif_r = APIRouter(prefix="/notifications", tags=["notifications"])


async def notify(user_id: str, ntype: str, title: str, body: str, link: Optional[str] = None, meta: Optional[Dict[str, Any]] = None):
    """Create an in-app notification for a user."""
    doc = {
        "id": new_id(),
        "user_id": user_id,
        "type": ntype,
        "title": title,
        "body": body,
        "link": link,
        "meta": meta or {},
        "read_at": None,
        "created_at": now_iso(),
    }
    await db.notifications.insert_one(doc)
    return doc


async def notify_many(user_ids: List[str], ntype: str, title: str, body: str, link: Optional[str] = None, meta: Optional[Dict[str, Any]] = None):
    if not user_ids:
        return
    now = now_iso()
    docs = [{
        "id": new_id(), "user_id": uid, "type": ntype, "title": title, "body": body,
        "link": link, "meta": meta or {}, "read_at": None, "created_at": now,
    } for uid in user_ids]
    await db.notifications.insert_many(docs)


async def _admin_user_ids(allowed_roles: tuple = ADMIN_ROLES) -> List[str]:
    ids = []
    async for u in db.users.find({"role": {"$in": list(allowed_roles)}, "status": {"$ne": "suspended"}}, {"_id": 0, "id": 1}):
        ids.append(u["id"])
    return ids


async def _label_user_ids(label_id: str) -> List[str]:
    label = await db.labels.find_one({"id": label_id}, {"_id": 0, "user_id": 1})
    return [label["user_id"]] if label and label.get("user_id") else []


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
        user_ids = await _label_user_ids(ticket["label_id"])
        title = f"Tiket {ticket['ticket_no']} — Update Admin"
        body = f"Admin {'mengubah status' if kind == 'status' else 'membalas'} tiket Anda."
        await notify_many(user_ids, "ticket_update", title, body, link_label, {"ticket_id": ticket_id})
    else:
        # Notify admins (support + super_admin)
        user_ids = await _admin_user_ids(("super_admin", "admin_support", "admin_release"))
        title = f"Tiket {ticket['ticket_no']} — Label membalas"
        body = f"{actor.get('name') or 'Label'} membalas tiket."
        await notify_many(user_ids, "ticket_update", title, body, link_admin, {"ticket_id": ticket_id})


@notif_r.get("/me")
async def my_notifications(user: dict = Depends(get_current_user), limit: int = 20, unread_only: bool = False):
    filt = {"user_id": user["id"]}
    if unread_only:
        filt["read_at"] = None
    items = await db.notifications.find(filt, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    unread = await db.notifications.count_documents({"user_id": user["id"], "read_at": None})
    return {"items": items, "unread_count": unread}


@notif_r.post("/mark-read/{nid}")
async def mark_read(nid: str, user: dict = Depends(get_current_user)):
    n = await db.notifications.find_one({"id": nid})
    if not n or n["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Notifikasi tidak ditemukan")
    await db.notifications.update_one({"id": nid}, {"$set": {"read_at": now_iso()}})
    return {"ok": True}


@notif_r.post("/mark-all-read")
async def mark_all_read(user: dict = Depends(get_current_user)):
    res = await db.notifications.update_many(
        {"user_id": user["id"], "read_at": None},
        {"$set": {"read_at": now_iso()}},
    )
    return {"ok": True, "updated": res.modified_count}


# =============================================================================
#                              CONTRACTS
# =============================================================================
contract_r = APIRouter(prefix="/contracts", tags=["contracts"])


def _contract_effective_status(c: Dict[str, Any]) -> str:
    """Compute effective status from stored status + dates."""
    if c.get("status") == "terminated":
        return "terminated"
    today = datetime.now(timezone.utc).date().isoformat()
    end = c.get("end_date") or ""
    if end and end < today:
        return "expired"
    # within 30 days?
    try:
        end_dt = datetime.strptime(end, "%Y-%m-%d").date()
        today_dt = datetime.now(timezone.utc).date()
        days_left = (end_dt - today_dt).days
        if 0 <= days_left <= 30:
            return "expiring_soon"
    except Exception:
        pass
    return "active"


def _enrich_contract(c: Dict[str, Any]) -> Dict[str, Any]:
    c["effective_status"] = _contract_effective_status(c)
    try:
        end_dt = datetime.strptime(c.get("end_date", ""), "%Y-%m-%d").date()
        today_dt = datetime.now(timezone.utc).date()
        c["days_left"] = (end_dt - today_dt).days
    except Exception:
        c["days_left"] = None
    return c


@contract_r.post("/admin/upload-pdf")
async def contract_upload_pdf(file: UploadFile = File(...), user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_release"):
        raise HTTPException(status_code=403, detail="Hanya Admin Release / Super Admin")
    ext = (file.filename or "").lower().rsplit(".", 1)[-1]
    if ext != "pdf":
        raise HTTPException(status_code=400, detail="File kontrak harus PDF")
    fid = new_id()
    target = UPLOAD_DIR / "contract" / f"{fid}.pdf"
    with open(target, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"url": f"/api/files/contract/{fid}.pdf", "filename": file.filename}


@contract_r.post("/admin")
async def contract_create(body: ContractCreateIn, user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_release"):
        raise HTTPException(status_code=403, detail="Hanya Admin Release / Super Admin")
    label = await db.labels.find_one({"id": body.label_id}, {"_id": 0, "id": 1, "label_name": 1, "user_id": 1})
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    if body.end_date <= body.start_date:
        raise HTTPException(status_code=400, detail="Tanggal berakhir harus setelah tanggal mulai")
    cid = new_id()
    doc = {
        "id": cid,
        "label_id": body.label_id,
        "label_name": label.get("label_name"),
        "file_url": body.file_url,
        "filename": body.filename,
        "start_date": body.start_date,
        "end_date": body.end_date,
        "notes": body.notes,
        "status": "active",
        "terminated_at": None,
        "terminated_reason": None,
        "created_by": user["id"],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.contracts.insert_one(doc)
    await log_activity(user["id"], "contract_create", "contract", cid, after={"label_id": body.label_id, "end_date": body.end_date})
    if label.get("user_id"):
        await notify(
            label["user_id"], "contract_created",
            "Kontrak baru ditambahkan",
            f"Kontrak berlaku {body.start_date} → {body.end_date}.",
            "/label/contract", {"contract_id": cid},
        )
    return _enrich_contract({k: v for k, v in doc.items() if k != "_id"})


@contract_r.get("/admin")
async def contract_list_admin(
    user: dict = Depends(require_admin),
    label_id: Optional[str] = None,
    status: Optional[str] = None,  # active|expiring_soon|expired|terminated
):
    filt: Dict[str, Any] = {}
    if label_id:
        filt["label_id"] = label_id
    items = await db.contracts.find(filt, {"_id": 0}).sort("created_at", -1).to_list(1000)
    items = [_enrich_contract(c) for c in items]
    if status:
        items = [c for c in items if c["effective_status"] == status]
    return items


@contract_r.get("/admin/{cid}")
async def contract_detail_admin(cid: str, user: dict = Depends(require_admin)):
    c = await db.contracts.find_one({"id": cid}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Kontrak tidak ditemukan")
    return _enrich_contract(c)


@contract_r.post("/admin/{cid}/extend")
async def contract_extend(cid: str, body: ContractExtendIn, user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_release"):
        raise HTTPException(status_code=403, detail="Hanya Admin Release / Super Admin")
    c = await db.contracts.find_one({"id": cid})
    if not c:
        raise HTTPException(status_code=404, detail="Kontrak tidak ditemukan")
    if body.new_end_date <= c["start_date"]:
        raise HTTPException(status_code=400, detail="Tanggal baru harus setelah tanggal mulai")
    await db.contracts.update_one({"id": cid}, {"$set": {
        "end_date": body.new_end_date, "status": "active", "terminated_at": None, "terminated_reason": None,
        "notes": body.notes or c.get("notes"), "updated_at": now_iso(),
    }})
    await log_activity(user["id"], "contract_extend", "contract", cid, after={"new_end_date": body.new_end_date})
    user_ids = await _label_user_ids(c["label_id"])
    await notify_many(user_ids, "contract_extended", "Kontrak diperpanjang",
                      f"Berlaku hingga {body.new_end_date}.", "/label/contract", {"contract_id": cid})
    return _enrich_contract(await db.contracts.find_one({"id": cid}, {"_id": 0}))


@contract_r.post("/admin/{cid}/terminate")
async def contract_terminate(cid: str, body: ContractTerminateIn, user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_release"):
        raise HTTPException(status_code=403, detail="Hanya Admin Release / Super Admin")
    c = await db.contracts.find_one({"id": cid})
    if not c:
        raise HTTPException(status_code=404, detail="Kontrak tidak ditemukan")
    await db.contracts.update_one({"id": cid}, {"$set": {
        "status": "terminated", "terminated_at": now_iso(),
        "terminated_reason": body.reason, "updated_at": now_iso(),
    }})
    await log_activity(user["id"], "contract_terminate", "contract", cid, after={"reason": body.reason})
    user_ids = await _label_user_ids(c["label_id"])
    await notify_many(user_ids, "contract_terminated", "Kontrak diakhiri",
                      f"Alasan: {body.reason}", "/label/contract", {"contract_id": cid})
    return _enrich_contract(await db.contracts.find_one({"id": cid}, {"_id": 0}))


@contract_r.get("/label")
async def contract_list_label(user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    items = await db.contracts.find({"label_id": label["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return [_enrich_contract(c) for c in items]


# =============================================================================
#                              BLACKLIST (Admin action)
# =============================================================================
@admin_r.post("/labels/{label_id}/blacklist")
async def admin_blacklist_label(label_id: str, body: BlacklistIn, user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin",):
        raise HTTPException(status_code=403, detail="Hanya Super Admin")
    label = await db.labels.find_one({"id": label_id})
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    await db.labels.update_one({"id": label_id}, {"$set": {
        "account_status": "blacklisted", "blacklisted": True,
        "blacklist_reason": body.reason, "blacklisted_at": now_iso(),
        "blacklisted_by": user["id"], "updated_at": now_iso(),
    }})
    await log_activity(user["id"], "blacklist_label", "label", label_id, after={"reason": body.reason})
    return {"ok": True}


@admin_r.post("/labels/{label_id}/unblacklist")
async def admin_unblacklist_label(label_id: str, user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin",):
        raise HTTPException(status_code=403, detail="Hanya Super Admin")
    label = await db.labels.find_one({"id": label_id}, {"_id": 0, "id": 1})
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    await db.labels.update_one({"id": label_id}, {"$set": {
        "account_status": "active", "blacklisted": False,
        "blacklist_reason": None, "updated_at": now_iso(),
    }})
    await log_activity(user["id"], "unblacklist_label", "label", label_id)
    return {"ok": True}


# =============================================================================
#                              REGISTER ROUTERS
# =============================================================================
api.include_router(auth)
api.include_router(label_r)
api.include_router(release_r)
api.include_router(artist_r)
api.include_router(pay_r)
api.include_router(cms_r)
api.include_router(admin_r)
api.include_router(royalty_r)
api.include_router(withdraw_r)
api.include_router(ticket_r)
api.include_router(contract_r)
api.include_router(notif_r)


@api.get("/")
async def api_root():
    return {"name": "RILIS MUSIK API", "version": "0.1.0"}


@api.get("/health")
async def health():
    return {"ok": True, "time": now_iso()}


app.include_router(api)


# =============================================================================
#                                CORS
# =============================================================================
frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# =============================================================================
#                            STARTUP / SEED
# =============================================================================
DEFAULT_LANDING_SETTINGS: Dict[str, Any] = {
    "general": {
        "site_title": "RILIS MUSIK — Distribusi Musik Digital",
        "brand_name": "RILIS MUSIK",
        "logo_url": None,
        "favicon_url": None,
        "primary_color": "#FF3B30",
        "support_email": "support@rilismusik.com",
        "whatsapp": "+6281234567890",
        "social": {"instagram": "https://instagram.com/rilismusik", "tiktok": "", "twitter": ""},
    },
    "hero": {
        "headline": "Distribusi Musik Lebih Rapi, Royalti Lebih Transparan.",
        "subheadline": "Platform distribusi musik digital untuk label musik dan artis independen. Upload rilisan, kelola artist, dan pantau royalti dari satu dashboard.",
        "cta_primary_text": "Daftar Sekarang",
        "cta_primary_url": "/register",
        "cta_secondary_text": "Login Dashboard",
        "cta_secondary_url": "/login",
        "hero_image_url": "https://images.unsplash.com/photo-1580656449278-e8381933522c?w=1600&q=85",
    },
    "benefits": [
        {"title": "Upload Rilisan dari Dashboard", "desc": "Submit lagu, EP, atau album tanpa WhatsApp. Cukup dari dashboard."},
        {"title": "Laporan Royalti Transparan", "desc": "Lihat revenue per lagu, platform, dan negara dalam IDR."},
        {"title": "Withdraw Terjadwal", "desc": "Cairkan saldo setiap tanggal 1–14 dengan invoice yang rapi."},
        {"title": "Support Takedown & Edit", "desc": "Ajukan takedown, edit metadata, audio, atau cover dengan mudah."},
        {"title": "YouTube Content ID", "desc": "Ajukan dan kelola klaim Content ID untuk lagu Anda."},
        {"title": "Dashboard Artist", "desc": "Artist Anda punya akun sendiri dan bisa lihat royalti lagu mereka."},
        {"title": "Simulasi Royalti", "desc": "Hitung estimasi pendapatan dari revenue Believe."},
        {"title": "Data Granular", "desc": "Per lagu, platform, dan negara. Semuanya rapi & detail."},
    ],
    "how_it_works": [
        "Daftar akun label",
        "Submit rilisan",
        "Bayar per rilis atau aktifkan subscription",
        "Admin review",
        "Rilisan dikirim ke Believe",
        "Royalti masuk dari laporan bulanan",
        "Withdraw sesuai jadwal",
    ],
    "pricing": {
        "pay_per_release_price": 35000,
        "annual_subscription_price": 500000,
        "distributor_fee_percent": 5,
        "description": "Pilih skema yang paling cocok untuk skala katalog Anda.",
        "features_pay": ["Unlimited revisi sebelum approve", "Audit metadata oleh admin", "Distribusi ke 150+ DSP via Believe"],
        "features_sub": ["Submit unlimited release", "Prioritas review", "Diskon Content ID & layanan tambahan"],
    },
    "royalty_sim": {
        "default_revenue_eur": 100,
        "default_rate": 17500,
        "fee_percent": 5,
        "label_percent_default": 60,
    },
    "dashboard_previews": [
        "https://images.unsplash.com/photo-1636226570637-3fbda7ca09dc?w=1200&q=85",
    ],
    "testimonials": [
        {"name": "Adit Soemardi", "role": "Founder, Nada Kala Records", "quote": "Akhirnya nggak perlu chat-chat WA buat submit lagu lagi. Royalti juga jelas per lagu."},
        {"name": "Rara Wijaya", "role": "Artis Independen", "quote": "Dashboard-nya enak banget di HP. Withdraw juga cepet."},
    ],
    "faq": [
        {"q": "Apa itu RILIS MUSIK?", "a": "Platform distribusi musik digital ke 150+ DSP via Believe. Cocok untuk label dan artis independen Indonesia."},
        {"q": "Berapa biaya distribusi?", "a": "Rp35.000 per rilis (Pay Per Release) atau Rp500.000 per tahun (Annual Subscription)."},
        {"q": "Apakah bisa upload album?", "a": "Bisa. Kami mendukung Single, EP, Album, dan Compilation."},
        {"q": "Kapan royalti cair?", "a": "Request withdraw tanggal 1–14, pembayaran tanggal 15–20 setiap bulan."},
        {"q": "Apakah ada YouTube Content ID?", "a": "Ada. Anda bisa mengajukan klaim Content ID via support ticket."},
        {"q": "Apakah artis bisa lihat royalti?", "a": "Bisa. Label dapat membuat akun artist dengan visibilitas royalti yang diatur."},
        {"q": "Apakah bisa takedown?", "a": "Bisa via support ticket."},
    ],
    "seo": {
        "page_title": "RILIS MUSIK — Distribusi Musik Digital Indonesia",
        "meta_description": "Distribusi lagu Anda ke 150+ DSP via Believe. Royalti transparan dalam IDR. Cocok untuk label dan artis independen.",
        "og_title": "RILIS MUSIK",
        "og_description": "Distribusi musik digital. Laporan royalti transparan. Withdraw rapi.",
        "og_image": "",
        "canonical_url": "https://rilismusik.com",
    },
    "footer": {
        "description": "Platform distribusi musik digital Indonesia. Dari demo ke 150+ platform.",
        "support_email": "support@rilismusik.com",
        "legal_links": [{"text": "Syarat & Ketentuan", "url": "/terms"}, {"text": "Privacy Policy", "url": "/privacy"}],
    },
}


async def seed_indexes_and_admins():
    # indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.labels.create_index("user_id")
    await db.labels.create_index("id", unique=True)
    await db.artists.create_index("user_id")
    await db.artists.create_index("label_id")
    await db.releases.create_index("label_id")
    await db.releases.create_index("status")
    await db.tracks.create_index("release_id")
    await db.tracks.create_index("artist_id")
    await db.payments.create_index("label_id")
    await db.payments.create_index("status")
    await db.payments.create_index("xendit_invoice_id")
    await db.password_reset_tokens.create_index("token")
    await db.email_verification_tokens.create_index("token")
    await db.login_attempts.create_index("identifier")
    await db.activity_logs.create_index("created_at")
    await db.landing_settings.create_index("key", unique=True)
    await db.royalty_imports.create_index("created_at")
    await db.royalty_lines.create_index("import_id")
    await db.royalty_lines.create_index("label_id")
    await db.royalty_lines.create_index("artist_id")
    await db.royalty_lines.create_index("period")
    await db.royalty_lines.create_index("status")
    await db.withdraw_requests.create_index("label_id")
    await db.withdraw_requests.create_index("status")
    await db.balance_transactions.create_index("label_id")
    await db.bank_accounts.create_index("label_id", unique=True)
    await db.support_tickets.create_index("label_id")
    await db.support_tickets.create_index("status")
    await db.support_tickets.create_index("category")
    await db.support_tickets.create_index("created_at")
    await db.ticket_comments.create_index("ticket_id")
    await db.contracts.create_index("label_id")
    await db.contracts.create_index("status")
    await db.contracts.create_index("end_date")
    await db.notifications.create_index("user_id")
    await db.notifications.create_index([("user_id", 1), ("read_at", 1)])
    await db.notifications.create_index("created_at")

    # Seed super admin
    admin_email = os.environ.get("ADMIN_EMAIL", "superadmin@rilismusik.com").lower().strip()
    admin_password = os.environ.get("ADMIN_PASSWORD", "SuperAdmin#2026")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        await db.users.insert_one({
            "id": new_id(),
            "name": "Super Admin",
            "email": admin_email,
            "password_hash": hash_password(admin_password),
            "role": SUPER_ADMIN,
            "email_verified_at": now_iso(),
            "status": "active",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        })
        logger.info("Super admin seeded: %s", admin_email)
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password), "updated_at": now_iso()}})
        logger.info("Super admin password updated for: %s", admin_email)

    # Seed sub-admin accounts (idempotent — only create if missing)
    sub_admins = [
        ("Admin Support", "support1@rilismusik.com", "Support#2026", "admin_support"),
        ("Admin Finance", "finance1@rilismusik.com", "Finance#2026", "admin_finance"),
        ("Admin Release", "release1@rilismusik.com", "Release#2026", "admin_release"),
        ("Admin Marketing", "marketing1@rilismusik.com", "Marketing#2026", "admin_marketing"),
    ]
    for name, email, pwd, role in sub_admins:
        if await db.users.find_one({"email": email}) is None:
            await db.users.insert_one({
                "id": new_id(),
                "name": name,
                "email": email,
                "password_hash": hash_password(pwd),
                "role": role,
                "email_verified_at": now_iso(),
                "status": "active",
                "created_at": now_iso(),
                "updated_at": now_iso(),
            })
            logger.info("Sub-admin seeded: %s (%s)", email, role)

    # Seed default landing settings
    for key, value in DEFAULT_LANDING_SETTINGS.items():
        existing_setting = await db.landing_settings.find_one({"key": key})
        if not existing_setting:
            await db.landing_settings.insert_one({
                "id": new_id(),
                "key": key,
                "value": value,
                "updated_by": None,
                "updated_at": now_iso(),
            })


@app.on_event("startup")
async def on_startup():
    await seed_indexes_and_admins()
    logger.info("RILIS MUSIK API started")


@app.on_event("shutdown")
async def on_shutdown():
    client.close()
