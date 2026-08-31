"""Phase 41 — concurrent sessions and token-version refresh regression."""
import os
import uuid

import jwt
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


def _decode(token):
    return jwt.decode(token, options={"verify_signature": False})


def test_two_devices_remain_active_after_one_refreshes():
    db = _db()
    suffix = uuid.uuid4().hex[:10]
    user_id = f"phase41-user-{suffix}"
    label_id = f"phase41-label-{suffix}"
    email = f"phase41-{suffix}@example.com"
    password = temporary_password("MultiDevice")
    now = "2026-09-01T00:00:00+00:00"
    db.users.insert_one({
        "id": user_id,
        "name": "Phase 41 Multi Device",
        "email": email,
        "password_hash": hash_password(password),
        "role": "label",
        "status": "active",
        "token_version": 3,
        "email_verified_at": now,
        "created_at": now,
        "updated_at": now,
    })
    db.labels.insert_one({
        "id": label_id,
        "user_id": user_id,
        "label_name": "Phase 41 Label",
        "account_status": "active",
        "created_at": now,
        "updated_at": now,
    })

    try:
        device_a = requests.Session()
        device_b = requests.Session()
        login_a = device_a.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
        login_b = device_b.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
        assert login_a.status_code == 200, login_a.text
        assert login_b.status_code == 200, login_b.text

        token_a = login_a.json()["access_token"]
        token_b = login_b.json()["access_token"]
        payload_a = _decode(token_a)
        payload_b = _decode(token_b)
        assert payload_a["tv"] == payload_b["tv"] == 3
        assert payload_a["sid"] != payload_b["sid"]
        assert device_a.get(f"{API}/auth/me", timeout=30).status_code == 200
        assert device_b.get(f"{API}/auth/me", timeout=30).status_code == 200

        refreshed = device_a.post(f"{API}/auth/refresh", timeout=30)
        assert refreshed.status_code == 200, refreshed.text
        refreshed_payload = _decode(device_a.cookies["access_token"])
        assert refreshed_payload["tv"] == 3
        assert refreshed_payload["sid"] == payload_a["sid"]
        assert device_a.get(f"{API}/auth/me", timeout=30).status_code == 200
        assert device_b.get(f"{API}/auth/me", timeout=30).status_code == 200
    finally:
        db.labels.delete_one({"id": label_id})
        db.users.delete_one({"id": user_id})


def test_global_revocation_still_invalidates_every_device():
    db = _db()
    suffix = uuid.uuid4().hex[:10]
    user_id = f"phase41-revoke-{suffix}"
    email = f"phase41-revoke-{suffix}@example.com"
    password = temporary_password("Revoke")
    now = "2026-09-01T00:00:00+00:00"
    db.users.insert_one({
        "id": user_id,
        "name": "Phase 41 Revoke",
        "email": email,
        "password_hash": hash_password(password),
        "role": "label",
        "status": "active",
        "token_version": 0,
        "email_verified_at": now,
        "created_at": now,
        "updated_at": now,
    })

    try:
        device_a = requests.Session()
        device_b = requests.Session()
        assert device_a.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30).status_code == 200
        assert device_b.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30).status_code == 200

        db.users.update_one({"id": user_id}, {"$inc": {"token_version": 1}})
        assert device_a.get(f"{API}/auth/me", timeout=30).status_code == 401
        assert device_b.get(f"{API}/auth/me", timeout=30).status_code == 401
        assert device_a.post(f"{API}/auth/refresh", timeout=30).status_code == 401
        assert device_b.post(f"{API}/auth/refresh", timeout=30).status_code == 401
    finally:
        db.users.delete_one({"id": user_id})


def test_disabled_account_cannot_start_or_refresh_session():
    db = _db()
    suffix = uuid.uuid4().hex[:10]
    user_id = f"phase41-disabled-{suffix}"
    email = f"phase41-disabled-{suffix}@example.com"
    password = temporary_password("Disabled")
    now = "2026-09-01T00:00:00+00:00"
    db.users.insert_one({
        "id": user_id,
        "name": "Phase 41 Disabled",
        "email": email,
        "password_hash": hash_password(password),
        "role": "label",
        "status": "active",
        "token_version": 0,
        "email_verified_at": now,
        "created_at": now,
        "updated_at": now,
    })

    try:
        session = requests.Session()
        assert session.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30).status_code == 200
        db.users.update_one({"id": user_id}, {"$set": {"status": "disabled"}})
        assert session.get(f"{API}/auth/me", timeout=30).status_code == 403
        assert session.post(f"{API}/auth/refresh", timeout=30).status_code == 403
        fresh_login = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
        assert fresh_login.status_code == 403
    finally:
        db.users.delete_one({"id": user_id})