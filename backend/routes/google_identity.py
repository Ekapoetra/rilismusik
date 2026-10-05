"""Google Identity Services for existing label accounts, with cached certificates."""
import asyncio
import hashlib
import json
import os
import re
import secrets
import time
from types import SimpleNamespace
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from google.auth.exceptions import GoogleAuthError
from google.oauth2 import id_token
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from auth_utils import create_access_token, create_refresh_token, set_auth_cookies
from models import now_iso, new_id
from .deps import db, logger, get_current_user, public_user, redact_label_for_self, log_activity, LABEL_ROLE

google_r = APIRouter(prefix="/auth/google", tags=["auth"])
CERTS_URL = "https://www.googleapis.com/oauth2/v1/certs"
NONCE_COOKIE = "__Host-rilismusik_google_nonce"
NONCE_SECONDS = 600
_cert_cache = {"data": b"", "until": 0.0}
_cert_lock = asyncio.Lock()


class GoogleCredentialIn(BaseModel):
    credential: str = Field(min_length=20, max_length=8192)


def _client_id() -> str:
    value = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    if not value or not value.endswith(".apps.googleusercontent.com"):
        raise HTTPException(503, "Login Google belum tersedia. Gunakan email dan password.")
    return value


def _require_same_origin(request: Request) -> None:
    origin = urlsplit(request.headers.get("origin", ""))
    host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or "").split(",")[0].strip().lower()
    if origin.scheme != "https" or origin.netloc.lower() != host or origin.path or origin.query or origin.fragment:
        raise HTTPException(403, "Permintaan login tidak valid. Buka kembali halaman login.")


async def _certificates() -> bytes:
    if _cert_cache["data"] and time.monotonic() < _cert_cache["until"]:
        return _cert_cache["data"]
    async with _cert_lock:
        if _cert_cache["data"] and time.monotonic() < _cert_cache["until"]:
            return _cert_cache["data"]
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(CERTS_URL)
            response.raise_for_status()
            certs = response.json()
            if not isinstance(certs, dict) or not certs:
                raise ValueError("Invalid certificates")
            match = re.search(r"(?:^|,)\s*max-age=(\d+)", response.headers.get("cache-control", ""))
            ttl = int(match[1]) if match else 300
            age = int(response.headers.get("age", "0"))
            ttl = max(0, min(ttl - age, 3600))
            _cert_cache.update(data=json.dumps(certs).encode(), until=time.monotonic() + ttl)
        except (httpx.HTTPError, ValueError):
            raise HTTPException(503, "Google belum dapat dihubungi. Coba lagi sebentar.") from None
        return _cert_cache["data"]


async def verify_google_credential(credential: str, client_id: str) -> dict:
    certs = await _certificates()

    def certificate_request(url, method="GET", **kwargs):
        if url != CERTS_URL or method != "GET":
            raise ValueError("Unexpected certificate request")
        return SimpleNamespace(status=200, data=certs)

    try:
        return await asyncio.to_thread(
            id_token.verify_oauth2_token, credential, certificate_request, client_id,
        )
    except (GoogleAuthError, ValueError, TypeError):
        raise HTTPException(401, "Sesi Google tidak valid atau kedaluwarsa. Coba login kembali.") from None


@google_r.get("/nonce")
async def google_nonce(response: Response):
    _client_id()
    nonce = secrets.token_urlsafe(32)
    response.set_cookie(NONCE_COOKIE, nonce, max_age=NONCE_SECONDS, path="/",
                        secure=True, httponly=True, samesite="lax")
    response.headers["Cache-Control"] = "no-store"
    return {"nonce": nonce}


async def _verified_identity(body: GoogleCredentialIn, request: Request) -> dict:
    _require_same_origin(request)
    nonce = request.cookies.get(NONCE_COOKIE)
    if not nonce:
        raise HTTPException(401, "Sesi login sudah berakhir. Muat ulang tombol Google.")
    claims = await verify_google_credential(body.credential, _client_id())
    token_nonce = claims.get("nonce")
    if not isinstance(token_nonce, str) or not secrets.compare_digest(nonce, token_nonce):
        raise HTTPException(401, "Sesi login tidak cocok. Muat ulang tombol Google.")
    if claims.get("email_verified") is not True or not claims.get("email") or not claims.get("sub"):
        raise HTTPException(401, "Email akun Google belum terverifikasi.")
    return claims


async def _check_label_user(user: dict):
    if not user or user.get("role") != LABEL_ROLE:
        raise HTTPException(403, "Google Login hanya tersedia untuk akun label yang sudah terdaftar dengan email yang sama.")
    if user.get("status") in {"merged", "suspended", "disabled"}:
        raise HTTPException(403, "Akun tidak aktif. Gunakan akun utama atau hubungi admin.")
    label = await db.labels.find_one({"user_id": user["id"]}, {"_id": 0})
    if label and label.get("account_status") == "blacklisted":
        raise HTTPException(403, "Akun tidak aktif. Hubungi admin.")
    return label


async def _bind_and_consume(user: dict, claims: dict, credential: str, *, mark_email_verified: bool = True):
    # _id uniqueness also works when preview index seeding is disabled.
    # Use Google's stable subject, not Emergent's historical provider id.
    binding = {"_id": claims["sub"], "user_id": user["id"], "created_at": now_iso()}
    try:
        await db.google_identities.insert_one(binding)
    except DuplicateKeyError:
        existing = await db.google_identities.find_one({"_id": claims["sub"]})
        if not existing or existing.get("user_id") != user["id"]:
            raise HTTPException(409, "Akun Google sudah terhubung ke akun lain.") from None
    digest = hashlib.sha256(credential.encode()).hexdigest()
    session = new_id()
    try:
        await db.google_auth_sessions.insert_one({
            "_id": "gis:" + digest, "id": new_id(), "user_id": user["id"],
            "session_id_hash": "gis:" + digest, "provider_user_id": claims["sub"],
            "provider": "google_identity_services", "app_session_id": session,
            "created_at": now_iso(), "token_expires_at": claims["exp"],
        })
    except DuplicateKeyError:
        raise HTTPException(409, "Sesi Google sudah digunakan. Muat ulang tombol Google.") from None
    fields = {
        "google_subject": claims["sub"], "google_picture": claims.get("picture"),
        "google_email": claims["email"].lower().strip(),
        "google_last_login_at": now_iso(), "updated_at": now_iso(),
    }
    if not user.get("google_linked_at"):
        fields["google_linked_at"] = now_iso()
    # Connecting Google from the profile is only a sign-in method; it never
    # changes the account's verification state (email or Verifikasi Akun).
    if mark_email_verified and not user.get("email_verified_at"):
        fields["email_verified_at"] = now_iso()
    result = await db.users.update_one({"id": user["id"], "$or": [
        {"google_subject": {"$exists": False}}, {"google_subject": None},
        {"google_subject": claims["sub"]},
    ]}, {"$set": fields})
    if result.matched_count != 1:
        raise HTTPException(409, "Akun ini sudah terhubung ke akun Google lain.")
    user.update(fields)
    return session


@google_r.post("/id-token")
async def google_id_token_login(body: GoogleCredentialIn, response: Response, request: Request):
    claims = await _verified_identity(body, request)
    binding = await db.google_identities.find_one({"_id": claims["sub"]})
    email = claims["email"].lower().strip()
    user = await db.users.find_one({"id": binding["user_id"]} if binding else {"email": email})
    label = await _check_label_user(user)
    # Google is not authoritative for third-party email addresses. Link those
    # from an authenticated account instead of silently linking by email.
    if not binding and not (email.endswith("@gmail.com") or claims.get("hd")):
        raise HTTPException(403, "Masuk dengan email/password, lalu hubungkan Google melalui Profil & Rekening.")
    if user.get("google_subject") and user["google_subject"] != claims["sub"]:
        raise HTTPException(409, "Akun ini sudah terhubung ke akun Google lain.")
    session = await _bind_and_consume(user, claims, body.credential)
    version = int(user.get("token_version") or 0)
    access = create_access_token(user["id"], user["email"], LABEL_ROLE, version, session)
    refresh = create_refresh_token(user["id"], version, session)
    set_auth_cookies(response, access, refresh)
    response.delete_cookie(NONCE_COOKIE, path="/", secure=True, httponly=True, samesite="lax")
    response.headers["Cache-Control"] = "no-store"
    return {"user": public_user(user), "label": redact_label_for_self(label) if label else None}


@google_r.post("/link")
async def google_link(body: GoogleCredentialIn, response: Response, request: Request,
                      user: dict = Depends(get_current_user)):
    claims = await _verified_identity(body, request)
    await _check_label_user(user)
    if claims["email"].lower().strip() != user["email"].lower().strip():
        raise HTTPException(403, "Pilih akun Google dengan email yang sama seperti akun label Anda.")
    if user.get("google_subject") and user["google_subject"] != claims["sub"]:
        raise HTTPException(409, "Akun ini sudah terhubung ke akun Google lain.")
    await _bind_and_consume(user, claims, body.credential, mark_email_verified=False)
    try:
        await log_activity(user["id"], "google_link", "user", user["id"], after={"google_email": user.get("google_email")})
    except Exception as exc:  # noqa: BLE001 - the link itself already succeeded
        logger.warning("google link audit log failed: %s", type(exc).__name__)
    response.delete_cookie(NONCE_COOKIE, path="/", secure=True, httponly=True, samesite="lax")
    response.headers["Cache-Control"] = "no-store"
    return {"ok": True, "google_email": user.get("google_email"), "google_linked_at": user.get("google_linked_at")}
