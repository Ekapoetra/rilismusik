"""Phase 17 — Security hardening regression suite.

Covers the four security-audit findings remediated in this iteration:
- SEC-001 (token-leak): forgot-password / register no longer return tokens (already covered by `test_rilismusik_api.py` and `test_refactor_smoke.py`; this file re-asserts to keep them grouped).
- SEC-001 (webhook): /api/payments/webhook/xendit is auth-locked (HMAC token).
- SEC-002: per-email login lockout cannot be bypassed by rotating X-Forwarded-For.
- SEC-003: password reset invalidates ALL existing access/refresh tokens (token_version bump) AND every other unused reset token.
- SEC-004: HTML escape in transactional emails (unit test on email_service.h()).
"""
import os
import uuid
import time
import requests
from tests.support_config import SUPERADMIN, temporary_password
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://lanjut-core.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"
SUPER_EMAIL = SUPERADMIN["email"]
SUPER_PASS = SUPERADMIN["password"]
TEST_USER_PASSWORD = temporary_password("security-user")
TEST_NEW_PASSWORD = temporary_password("security-new")
WRONG_PASSWORD = temporary_password("wrong")


def _session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _rand_email(prefix="sec"):
    return f"TEST_{prefix}_{uuid.uuid4().hex[:8]}@example.com"


def _mongo_db():
    import pymongo
    from pathlib import Path
    # Load backend .env so DB_NAME/MONGO_URL match the live API
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    client = pymongo.MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db_name = os.environ.get("DB_NAME") or "rilismusik_db"
    return client[db_name]


def _latest_reset_token(email: str) -> str:
    db = _mongo_db()
    user = db.users.find_one({"email": email.lower().strip()})
    assert user, f"user not found: {email}"
    cur = db.password_reset_tokens.find({"user_id": user["id"], "used": False}).sort("created_at", -1).limit(1)
    docs = list(cur)
    assert docs, f"no unused reset token found for {email}"
    return docs[0]["token"]


# =============================================================================
# SEC-001 — token-leak fix (already remediated; re-asserted here for completeness)
# =============================================================================
def test_sec001_forgot_password_does_not_leak_token():
    r = requests.post(f"{API}/auth/forgot-password", json={"email": SUPER_EMAIL}, timeout=30)
    assert r.status_code == 200
    assert r.json() == {"ok": True}, "SEC-001: forgot-password response must be exactly {ok: True}"


def test_sec001_register_does_not_leak_token():
    email = _rand_email("regleak")
    r = requests.post(f"{API}/auth/register", json={
        "label_name": "SEC Test", "pic_name": "PIC", "email": email,
        "whatsapp": "+628111", "password": TEST_USER_PASSWORD, "mda_accepted": True,
    }, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "verification_token" not in body, "SEC-001: verification_token leaked in register body"
    assert "reset_token" not in body


# =============================================================================
# SEC-001 — Xendit webhook is locked down
# =============================================================================
def test_sec001_xendit_webhook_rejects_unauthenticated_calls():
    """Without XENDIT_CALLBACK_TOKEN, the webhook must fail-closed (503).
    With token set but wrong header → 401.
    """
    r = requests.post(
        f"{API}/payments/webhook/xendit",
        json={"id": "mock_anything", "status": "paid"},
        timeout=30,
    )
    # Either 503 (no token configured) or 401 (token configured but missing header)
    assert r.status_code in (401, 503), f"webhook must reject unauthenticated calls, got {r.status_code}: {r.text}"


# =============================================================================
# SEC-002 — per-email lockout cannot be bypassed by header rotation
# =============================================================================
def test_sec002_login_lockout_per_email_even_with_rotating_xff():
    s = _session()
    email = _rand_email("bflock")
    s.post(f"{API}/auth/register", json={
        "label_name": "X", "pic_name": "X", "email": email,
        "whatsapp": "+628111", "password": TEST_USER_PASSWORD, "mda_accepted": True,
    })
    codes = []
    for i in range(6):
        r = s.post(
            f"{API}/auth/login",
            json={"email": email, "password": WRONG_PASSWORD},
            headers={"X-Forwarded-For": f"10.99.99.{i+1}"},  # rotate IP each request
            timeout=30,
        )
        codes.append(r.status_code)
    assert 429 in codes, f"SEC-002: per-email lockout must trigger; got codes {codes}"


# =============================================================================
# SEC-003 — password reset invalidates old access tokens and outstanding reset tokens
# =============================================================================
def test_sec003_reset_invalidates_old_access_token():
    """After password reset, the old JWT (`access_token`) must no longer authenticate."""
    s = _session()
    email = _rand_email("sessinv")
    # 1) Register and capture an access token
    r = s.post(f"{API}/auth/register", json={
        "label_name": "SessInv", "pic_name": "PIC", "email": email,
        "whatsapp": "+628111", "password": TEST_USER_PASSWORD, "mda_accepted": True,
    })
    assert r.status_code == 200, r.text
    old_access = r.json()["access_token"]
    # Sanity: token works initially
    me_ok = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {old_access}"}, timeout=30)
    assert me_ok.status_code == 200

    # 2) Reset password
    requests.post(f"{API}/auth/forgot-password", json={"email": email}, timeout=30).raise_for_status()
    token = _latest_reset_token(email)
    r2 = requests.post(f"{API}/auth/reset-password", json={"token": token, "password": TEST_NEW_PASSWORD}, timeout=30)
    assert r2.status_code == 200

    # 3) Old access token MUST no longer work
    me_after = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {old_access}"}, timeout=30)
    assert me_after.status_code == 401, f"SEC-003: old access token still valid after reset (got {me_after.status_code})"


def test_sec003_reset_invalidates_other_outstanding_reset_tokens():
    """Issuing two reset tokens then consuming one MUST invalidate the other."""
    email = _rand_email("twin")
    requests.post(f"{API}/auth/register", json={
        "label_name": "Twin", "pic_name": "PIC", "email": email,
        "whatsapp": "+628111", "password": TEST_USER_PASSWORD, "mda_accepted": True,
    }, timeout=30)
    # Issue two reset tokens
    requests.post(f"{API}/auth/forgot-password", json={"email": email}, timeout=30).raise_for_status()
    requests.post(f"{API}/auth/forgot-password", json={"email": email}, timeout=30).raise_for_status()
    # Read BOTH tokens directly from DB
    db = _mongo_db()
    user = db.users.find_one({"email": email.lower()})
    docs = list(db.password_reset_tokens.find({"user_id": user["id"], "used": False}).sort("created_at", -1))
    assert len(docs) >= 2, "should have 2 unused reset tokens"
    token_new, token_old = docs[0]["token"], docs[1]["token"]
    # Consume the newer one
    r = requests.post(f"{API}/auth/reset-password", json={"token": token_new, "password": temporary_password("third")}, timeout=30)
    assert r.status_code == 200
    # The other (older) token MUST now be rejected as already-used
    r2 = requests.post(f"{API}/auth/reset-password", json={"token": token_old, "password": temporary_password("fourth")}, timeout=30)
    assert r2.status_code == 400, f"SEC-003: outstanding reset token still valid after another reset (got {r2.status_code})"


# =============================================================================
# SEC-004 — HTML escape in email body
# =============================================================================
def test_sec004_email_h_escapes_html():
    from email_service import h
    assert h("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"
    assert h("Smith & Co \"Records\"") == "Smith &amp; Co &quot;Records&quot;"
    assert h(None) == ""
    assert h(42) == "42"
