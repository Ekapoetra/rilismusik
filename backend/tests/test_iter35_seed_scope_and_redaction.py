"""Iteration 35 — seed scope repair and auth/admin secret redaction checks."""
import os
import uuid

import pymongo
import requests
from dotenv import dotenv_values

from auth_utils import hash_password, verify_password
from tests.support_config import FINANCE, SUPPORT, SUPERADMIN, temporary_password


BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"]).rstrip("/")
API = f"{BASE_URL}/api"


def _db():
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


def _login_token(email: str, password: str) -> str:
    response = requests.post(
        f"{API}/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    assert response.status_code == 200, response.text
    token = response.json().get("access_token")
    assert isinstance(token, str) and len(token) > 10
    return token


def _headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def _contains_password_hash(payload):
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == "password_hash":
                return True
            if _contains_password_hash(value):
                return True
    elif isinstance(payload, list):
        for item in payload:
            if _contains_password_hash(item):
                return True
    return False


def test_seed_repair_is_scoped_to_seeded_subadmins_and_does_not_reset_unrelated_users():
    # Seed/migrate module: deterministic sub-admin repair should not touch unrelated users.
    db = _db()
    support_doc = db.users.find_one({"email": SUPPORT["email"]}, {"_id": 0, "id": 1, "password_hash": 1})
    finance_doc = db.users.find_one({"email": FINANCE["email"]}, {"_id": 0, "id": 1, "password_hash": 1})
    assert support_doc and support_doc.get("id") and support_doc.get("password_hash")
    assert finance_doc and finance_doc.get("id") and finance_doc.get("password_hash")

    original_support_hash = support_doc["password_hash"]
    original_finance_hash = finance_doc["password_hash"]

    suffix = uuid.uuid4().hex[:10]
    unrelated_user_id = f"iter35-unrelated-{suffix}"
    unrelated_email = f"iter35-unrelated-{suffix}@example.com"
    unrelated_password = temporary_password("Iter35Stable")
    now = "2026-08-30T00:00:00+00:00"

    db.users.insert_one({
        "id": unrelated_user_id,
        "name": "Iter35 Unrelated",
        "email": unrelated_email,
        "password_hash": hash_password(unrelated_password),
        "role": "label",
        "status": "active",
        "email_verified_at": now,
        "created_at": now,
        "updated_at": now,
        "token_version": 0,
    })
    unrelated_before = db.users.find_one({"id": unrelated_user_id}, {"_id": 0, "password_hash": 1})
    assert unrelated_before and unrelated_before.get("password_hash")

    try:
        mutated_password = temporary_password("Mutated")
        db.users.update_one(
            {"id": support_doc["id"]},
            {"$set": {"password_hash": hash_password(mutated_password)}},
        )
        mutated_support = db.users.find_one({"id": support_doc["id"]}, {"_id": 0, "password_hash": 1})
        assert mutated_support and verify_password(mutated_password, mutated_support["password_hash"])

        token = _login_token(SUPERADMIN["email"], SUPERADMIN["password"])
        repair = requests.post(
            f"{API}/admin/migrate/ensure-indexes",
            headers=_headers(token),
            timeout=120,
        )
        assert repair.status_code == 200, repair.text

        support_after = db.users.find_one({"id": support_doc["id"]}, {"_id": 0, "password_hash": 1})
        finance_after = db.users.find_one({"id": finance_doc["id"]}, {"_id": 0, "password_hash": 1})
        unrelated_after = db.users.find_one({"id": unrelated_user_id}, {"_id": 0, "password_hash": 1})

        assert support_after and verify_password(SUPPORT["password"], support_after["password_hash"])
        assert finance_after and finance_after["password_hash"] == original_finance_hash
        assert unrelated_after and unrelated_after["password_hash"] == unrelated_before["password_hash"]
    finally:
        db.users.update_one(
            {"id": support_doc["id"]},
            {"$set": {"password_hash": original_support_hash}},
        )
        db.users.delete_one({"id": unrelated_user_id})


def test_auth_and_admin_responses_do_not_expose_password_hash_fields():
    # Auth/admin APIs: response payloads should never expose password hashes.
    login_response = requests.post(
        f"{API}/auth/login",
        json={"email": SUPERADMIN["email"], "password": SUPERADMIN["password"]},
        timeout=30,
    )
    assert login_response.status_code == 200, login_response.text
    login_json = login_response.json()
    assert _contains_password_hash(login_json) is False
    assert "password_hash" not in login_response.text.lower()

    token = login_json["access_token"]
    me_response = requests.get(
        f"{API}/auth/me",
        headers=_headers(token),
        timeout=30,
    )
    assert me_response.status_code == 200, me_response.text
    me_json = me_response.json()
    assert _contains_password_hash(me_json) is False
    assert "password_hash" not in me_response.text.lower()

    labels_response = requests.get(
        f"{API}/admin/labels",
        headers=_headers(token),
        params={"q": "Demo Label PPR"},
        timeout=30,
    )
    assert labels_response.status_code == 200, labels_response.text
    labels_json = labels_response.json()
    assert _contains_password_hash(labels_json) is False
    assert "password_hash" not in labels_response.text.lower()
