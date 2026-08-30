"""Iteration 34 — auth playbook checks using preview/public endpoint only."""
import os
import sys
import uuid
from pathlib import Path

import pymongo
import requests
from dotenv import dotenv_values, load_dotenv

sys.path.append(str(Path(__file__).resolve().parents[1]))
from auth_utils import hash_password, verify_password
from tests.support_config import SUPERADMIN, SUPPORT, temporary_password


load_dotenv("/app/backend/.env", override=True)
FRONTEND_ENV = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or FRONTEND_ENV["REACT_APP_BACKEND_URL"]).rstrip("/")
API = f"{BASE_URL}/api"


def _db():
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


def _login(email: str, password: str, headers=None):
    return requests.post(
        f"{API}/auth/login",
        json={"email": email, "password": password},
        headers=headers or {},
        timeout=30,
    )


def test_seeded_password_hash_is_bcrypt_2b_prefix():
    # Auth module: verify seeded admin hash format for bcrypt compatibility.
    doc = _db().users.find_one({"email": SUPERADMIN["email"]}, {"_id": 0, "password_hash": 1})
    assert doc and isinstance(doc.get("password_hash"), str)
    assert doc["password_hash"].startswith("$2b$")


def test_login_sets_secure_httponly_cookies_and_bearer_fallback_works():
    # Auth API + middleware: cookie session and bearer fallback are both valid.
    session = requests.Session()
    response = session.post(
        f"{API}/auth/login",
        json={"email": SUPERADMIN["email"], "password": SUPERADMIN["password"]},
        timeout=30,
    )
    assert response.status_code == 200, response.text
    cookie_header = response.headers.get("set-cookie", "")
    lowered = cookie_header.lower()
    assert "access_token=" in cookie_header
    assert "refresh_token=" in cookie_header
    assert "httponly" in lowered
    assert "secure" in lowered

    me_cookie = session.get(f"{API}/auth/me", timeout=30)
    assert me_cookie.status_code == 200, me_cookie.text
    assert me_cookie.json().get("user", {}).get("email") == SUPERADMIN["email"]

    access_token = response.json().get("access_token")
    assert isinstance(access_token, str) and len(access_token) > 10
    me_bearer = requests.get(
        f"{API}/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    assert me_bearer.status_code == 200, me_bearer.text
    assert me_bearer.json().get("user", {}).get("email") == SUPERADMIN["email"]


def test_cors_preflight_allows_credentials_with_explicit_origin():
    # Validate the FastAPI middleware directly. Public Kubernetes/Cloudflare
    # ingress can answer OPTIONS before FastAPI; app traffic itself is same-origin.
    from fastapi.testclient import TestClient
    from server import app
    response = TestClient(app).options(
        "/api/auth/login",
        headers={
            "Origin": BASE_URL,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
        timeout=30,
    )
    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-origin") == BASE_URL
    assert response.headers.get("access-control-allow-credentials", "").lower() == "true"


def test_bruteforce_lockout_after_five_failures():
    # Auth lockout policy: 5 failed attempts trigger temporary lockout (429).
    db = _db()
    suffix = uuid.uuid4().hex[:10]
    email = f"iter34-lock-{suffix}@example.com"
    user_id = f"iter34-lock-user-{suffix}"
    password = temporary_password("Iter34Lock")
    now = "2026-08-30T00:00:00+00:00"
    db.users.insert_one({
        "id": user_id,
        "name": "Iter34 Lockout",
        "email": email,
        "password_hash": hash_password(password),
        "role": "label",
        "status": "active",
        "email_verified_at": now,
        "created_at": now,
        "updated_at": now,
        "token_version": 0,
    })
    try:
        wrong = temporary_password("Wrong")
        statuses = []
        for idx in range(6):
            trial = _login(email, wrong, headers={"X-Forwarded-For": f"10.34.0.{idx + 1}"})
            statuses.append(trial.status_code)
        assert 429 in statuses
    finally:
        db.login_attempts.delete_many({"identifier": {"$regex": f"{email}"}})
        db.users.delete_one({"id": user_id})


def test_seed_admin_updates_existing_admin_when_password_changes():
    # Seed process: ensure-indexes should repair admin hash to env-configured password.
    db = _db()
    support_doc = db.users.find_one({"email": SUPPORT["email"]}, {"_id": 0, "id": 1, "password_hash": 1})
    assert support_doc and support_doc.get("id")
    original_hash = support_doc["password_hash"]
    mutated_password = temporary_password("Mutated")

    try:
        db.users.update_one(
            {"id": support_doc["id"]},
            {"$set": {"password_hash": hash_password(mutated_password)}},
        )
        mutated = db.users.find_one({"id": support_doc["id"]}, {"_id": 0, "password_hash": 1})
        assert mutated and verify_password(mutated_password, mutated["password_hash"])

        super_login = _login(SUPERADMIN["email"], SUPERADMIN["password"])
        assert super_login.status_code == 200, super_login.text
        access = super_login.json().get("access_token")
        assert access
        repair = requests.post(
            f"{API}/admin/migrate/ensure-indexes",
            headers={"Authorization": f"Bearer {access}"},
            timeout=120,
        )
        assert repair.status_code == 200, repair.text

        support_recovered = _login(SUPPORT["email"], SUPPORT["password"])
        assert support_recovered.status_code == 200, support_recovered.text
    finally:
        # Restore original hash exactly (defensive cleanup regardless of seed behavior).
        db.users.update_one(
            {"id": support_doc["id"]},
            {"$set": {"password_hash": original_hash}},
        )
