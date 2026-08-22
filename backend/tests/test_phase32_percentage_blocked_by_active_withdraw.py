"""Phase 32 — changing label percentage must be blocked while withdraw is active."""
import os
import sys
import uuid
from pathlib import Path

import pymongo
import requests
from dotenv import dotenv_values, load_dotenv

sys.path.append(str(Path(__file__).resolve().parents[1]))
from auth_utils import hash_password


load_dotenv("/app/backend/.env")
FRONTEND_ENV = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or FRONTEND_ENV["REACT_APP_BACKEND_URL"]).rstrip("/")
API = f"{BASE}/api"
SUPER = {"email": "superadmin@rilismusik.com", "password": "SuperAdmin#2026"}


def _db():
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


def _token(credentials):
    response = requests.post(f"{API}/auth/login", json=credentials, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_patch_label_percentage_returns_409_when_withdraw_requested_exists():
    db = _db()
    suffix = uuid.uuid4().hex[:10]
    label_id = f"phase32-lock-label-{suffix}"
    user_id = f"phase32-lock-user-{suffix}"
    now = "2026-08-01T00:00:00+00:00"

    db.users.insert_one({
        "id": user_id,
        "name": "Phase32 Lock",
        "email": f"phase32-lock-{suffix}@example.com",
        "password_hash": hash_password("Phase32Lock#2026"),
        "role": "label",
        "status": "active",
        "email_verified_at": now,
        "created_at": now,
        "updated_at": now,
        "token_version": 0,
    })
    db.labels.insert_one({
        "id": label_id,
        "user_id": user_id,
        "label_name": f"Phase32 Lock {suffix}",
        "royalty_percentage_default": 60.0,
        "balance_pending_idr": 0,
        "balance_available_idr": 0,
        "balance_withdraw_requested_idr": 0,
        "account_status": "active",
        "bank_verified": True,
        "created_at": now,
        "updated_at": now,
    })
    db.withdraw_requests.insert_one({
        "id": f"phase32-lock-wd-{suffix}",
        "label_id": label_id,
        "status": "requested",
        "amount_idr": 100_000,
        "legacy_import": False,
        "created_at": now,
        "updated_at": now,
    })

    try:
        super_token = _token(SUPER)
        response = requests.patch(
            f"{API}/admin/labels/{label_id}",
            json={"royalty_percentage_default": 95, "royalty_change_reason": "blocked test"},
            headers=_headers(super_token),
            timeout=30,
        )
        assert response.status_code == 409, response.text
        assert "withdraw aktif" in response.text.lower()
    finally:
        db.withdraw_requests.delete_many({"label_id": label_id})
        db.labels.delete_many({"id": label_id})
        db.users.delete_many({"id": user_id})
