"""Iteration 42 — forgot/reset password public API regression."""
import os
import uuid

import pymongo
import requests
from dotenv import load_dotenv

from auth_utils import hash_password
from tests.support_config import temporary_password


load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/frontend/.env", override=True)
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def test_forgot_reset_flow_hides_token_and_invalidates_old_sessions():
    # Auth module: forgot/reset endpoint behavior, token single-use, token_version revocation.
    db = _db()
    suffix = uuid.uuid4().hex[:10]
    user_id = f"iter42-user-{suffix}"
    label_id = f"iter42-label-{suffix}"
    email = f"iter42-{suffix}@example.com"
    old_password = temporary_password("OldPwd")
    new_password = temporary_password("NewPwd")
    now = "2026-09-01T00:00:00+00:00"

    db.users.insert_one({
        "id": user_id,
        "name": "Iter42 Forgot User",
        "email": email,
        "password_hash": hash_password(old_password),
        "role": "label",
        "status": "active",
        "token_version": 0,
        "email_verified_at": now,
        "created_at": now,
        "updated_at": now,
    })
    db.labels.insert_one({
        "id": label_id,
        "user_id": user_id,
        "label_name": "Iter42 Label",
        "account_status": "active",
        "created_at": now,
        "updated_at": now,
    })

    try:
        active_session = requests.Session()
        login_before = active_session.post(
            f"{API}/auth/login", json={"email": email, "password": old_password}, timeout=30,
        )
        assert login_before.status_code == 200, login_before.text
        assert active_session.get(f"{API}/auth/me", timeout=30).status_code == 200

        unknown = requests.post(
            f"{API}/auth/forgot-password", json={"email": f"unknown-{suffix}@example.com"}, timeout=30,
        )
        known = requests.post(
            f"{API}/auth/forgot-password", json={"email": email}, timeout=30,
        )
        assert unknown.status_code == 200, unknown.text
        assert known.status_code == 200, known.text
        assert "token" not in unknown.json()
        assert "token" not in known.json()

        token_doc = db.password_reset_tokens.find_one(
            {"user_id": user_id, "used": False},
            sort=[("created_at", pymongo.DESCENDING)],
        )
        assert token_doc and token_doc.get("token")

        reset = requests.post(
            f"{API}/auth/reset-password",
            json={"token": token_doc["token"], "password": new_password},
            timeout=30,
        )
        assert reset.status_code == 200, reset.text

        replay = requests.post(
            f"{API}/auth/reset-password",
            json={"token": token_doc["token"], "password": temporary_password("Replay")},
            timeout=30,
        )
        assert replay.status_code == 400, replay.text

        user_after = db.users.find_one({"id": user_id}, {"_id": 0, "token_version": 1})
        assert user_after and int(user_after.get("token_version") or 0) == 1
        assert db.password_reset_tokens.count_documents({"user_id": user_id, "used": False}) == 0

        old_login = requests.post(
            f"{API}/auth/login", json={"email": email, "password": old_password}, timeout=30,
        )
        new_login = requests.post(
            f"{API}/auth/login", json={"email": email, "password": new_password}, timeout=30,
        )
        assert old_login.status_code == 401, old_login.text
        assert new_login.status_code == 200, new_login.text

        old_session_after_reset = active_session.get(f"{API}/auth/me", timeout=30)
        assert old_session_after_reset.status_code == 401, old_session_after_reset.text
    finally:
        db.login_attempts.delete_many({"identifier": {"$regex": f"{email}"}})
        db.password_reset_tokens.delete_many({"user_id": user_id})
        db.labels.delete_one({"id": label_id})
        db.users.delete_one({"id": user_id})
