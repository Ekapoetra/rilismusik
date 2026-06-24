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
    now_iso, new_id,
)

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
    # brute force check
    identifier = f"{request.client.host if request.client else 'na'}:{email}"
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
        {"$match": {"label_id": label["id"], "status": "published"}},
        {"$group": {"_id": "$period", "total": {"$sum": "$label_royalty_idr"}}},
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
        {"$group": {"_id": None, "total_eur": {"$sum": "$label_royalty_eur"}, "total_idr": {"$sum": "$label_royalty_idr"}}},
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
#                              REGISTER ROUTERS
# =============================================================================
api.include_router(auth)
api.include_router(label_r)
api.include_router(release_r)
api.include_router(artist_r)
api.include_router(pay_r)
api.include_router(cms_r)
api.include_router(admin_r)


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
