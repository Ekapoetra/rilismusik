"""Iteration 37 — suspended account auth/session invalidation regression checks."""
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


def test_suspended_account_cannot_login_use_access_or_refresh():
    # Auth module: suspended users must be blocked for login, me, and refresh.
    db = _db()
    suffix = uuid.uuid4().hex[:10]
    user_id = f"iter37-suspended-{suffix}"
    email = f"iter37-suspended-{suffix}@example.com"
    password = temporary_password("Suspended")
    now = "2026-09-01T00:00:00+00:00"

    db.users.insert_one({
        "id": user_id,
        "name": "Iter37 Suspended",
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
        first_login = session.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
        assert first_login.status_code == 200, first_login.text

        db.users.update_one({"id": user_id}, {"$set": {"status": "suspended"}})

        me_after_suspend = session.get(f"{API}/auth/me", timeout=30)
        assert me_after_suspend.status_code == 403, me_after_suspend.text

        refresh_after_suspend = session.post(f"{API}/auth/refresh", timeout=30)
        assert refresh_after_suspend.status_code == 403, refresh_after_suspend.text

        suspended_login = requests.post(
            f"{API}/auth/login",
            json={"email": email, "password": password},
            timeout=30,
        )
        assert suspended_login.status_code == 403, suspended_login.text
    finally:
        db.users.delete_one({"id": user_id})
