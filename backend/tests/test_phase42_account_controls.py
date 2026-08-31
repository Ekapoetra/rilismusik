"""Phase 42 — bank-change approvals and safe admin deletion."""
import os
import uuid

import pymongo
import requests
from dotenv import load_dotenv

from auth_utils import hash_password
from tests.support_config import SUPERADMIN, temporary_password


load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/frontend/.env", override=True)
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _login(email, password):
    response = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _seed_label(db, suffix):
    now = "2026-09-01T00:00:00+00:00"
    user_id = f"phase42-user-{suffix}"
    label_id = f"phase42-label-{suffix}"
    bank_id = f"phase42-bank-{suffix}"
    email = f"phase42-label-{suffix}@example.com"
    password = temporary_password("BankFlow")
    db.users.insert_one({
        "id": user_id, "name": "Phase 42 Label", "email": email,
        "password_hash": hash_password(password), "role": "label", "status": "active",
        "token_version": 0, "email_verified_at": now, "created_at": now, "updated_at": now,
    })
    db.labels.insert_one({
        "id": label_id, "user_id": user_id, "label_name": "Phase 42 Label",
        "account_status": "active", "bank_verified": True, "created_at": now, "updated_at": now,
    })
    db.bank_accounts.insert_one({
        "id": bank_id, "label_id": label_id, "bank_name": "Bank Lama",
        "account_number": "11112222", "account_holder_name": "Pemilik Lama",
        "verified_status": "verified", "created_at": now, "updated_at": now,
    })
    return {"user_id": user_id, "label_id": label_id, "bank_id": bank_id, "email": email, "password": password}


def _cleanup_label(db, seeded):
    db.bank_account_change_requests.delete_many({"label_id": seeded["label_id"]})
    db.bank_accounts.delete_many({"label_id": seeded["label_id"]})
    db.notifications.delete_many({"meta.label_id": seeded["label_id"]})
    db.activity_logs.delete_many({"reference_id": {"$regex": "^phase42"}})
    db.labels.delete_one({"id": seeded["label_id"]})
    db.users.delete_one({"id": seeded["user_id"]})


def test_label_requests_change_and_admin_approves_without_early_mutation():
    db = _db()
    seeded = _seed_label(db, uuid.uuid4().hex[:10])
    label_token = _login(seeded["email"], seeded["password"])
    admin_token = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    proposed = {
        "bank_name": "Bank Baru", "account_number": "99990000",
        "account_holder_name": "Pemilik Baru", "reason": "Rekening operasional baru",
    }
    try:
        created = requests.post(
            f"{API}/label/bank-account/change-request", json=proposed,
            headers=_headers(label_token), timeout=30,
        )
        assert created.status_code == 200, created.text
        request_doc = created.json()
        assert request_doc["status"] == "pending_admin_approval"
        unchanged = db.bank_accounts.find_one({"label_id": seeded["label_id"]}, {"_id": 0})
        assert unchanged["bank_name"] == "Bank Lama"

        approved = requests.post(
            f"{API}/admin/bank-account-change-requests/{request_doc['id']}/action",
            json={"action": "approve", "note": "Data sesuai"},
            headers=_headers(admin_token), timeout=30,
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["status"] == "approved"
        changed = db.bank_accounts.find_one({"label_id": seeded["label_id"]}, {"_id": 0})
        assert changed["bank_name"] == "Bank Baru"
        assert changed["account_number"] == "99990000"
        assert changed["verified_status"] == "verified"
    finally:
        _cleanup_label(db, seeded)


def test_admin_requests_change_and_label_approves():
    db = _db()
    seeded = _seed_label(db, uuid.uuid4().hex[:10])
    label_token = _login(seeded["email"], seeded["password"])
    admin_token = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    try:
        created = requests.post(
            f"{API}/admin/labels/{seeded['label_id']}/bank-change-request",
            json={
                "bank_name": "Bank Admin", "account_number": "33334444",
                "account_holder_name": "Usulan Admin", "reason": "Koreksi data",
            },
            headers=_headers(admin_token), timeout=30,
        )
        assert created.status_code == 200, created.text
        request_doc = created.json()
        assert request_doc["status"] == "pending_label_approval"
        assert db.bank_accounts.find_one({"label_id": seeded["label_id"]})["bank_name"] == "Bank Lama"

        approved = requests.post(
            f"{API}/label/bank-account/change-requests/{request_doc['id']}/action",
            json={"action": "approve"}, headers=_headers(label_token), timeout=30,
        )
        assert approved.status_code == 200, approved.text
        assert db.bank_accounts.find_one({"label_id": seeded["label_id"]})["bank_name"] == "Bank Admin"
    finally:
        _cleanup_label(db, seeded)


def test_delete_admin_revokes_sessions_and_same_email_can_be_restored():
    db = _db()
    suffix = uuid.uuid4().hex[:10]
    email = f"phase42-admin-{suffix}@example.com"
    password = temporary_password("AdminDelete")
    admin_token = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    try:
        created = requests.post(
            f"{API}/admin/admin-users",
            json={"name": "Temporary Admin", "email": email, "password": password, "role": "admin_support"},
            headers=_headers(admin_token), timeout=30,
        )
        assert created.status_code == 200, created.text
        target_id = created.json()["id"]
        target_token = _login(email, password)

        deleted = requests.delete(f"{API}/admin/admin-users/{target_id}", headers=_headers(admin_token), timeout=30)
        assert deleted.status_code == 200, deleted.text
        assert requests.get(f"{API}/auth/me", headers=_headers(target_token), timeout=30).status_code == 403
        assert requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30).status_code == 403
        listing = requests.get(f"{API}/admin/admin-users", headers=_headers(admin_token), timeout=30).json()
        assert target_id not in {item["id"] for item in listing}

        restored_password = temporary_password("AdminRestore")
        restored = requests.post(
            f"{API}/admin/admin-users",
            json={"name": "Restored Admin", "email": email, "password": restored_password, "role": "admin_marketing"},
            headers=_headers(admin_token), timeout=30,
        )
        assert restored.status_code == 200, restored.text
        assert restored.json()["id"] == target_id
        assert restored.json()["status"] == "active"
        assert _login(email, restored_password)
    finally:
        target = db.users.find_one({"email": email}, {"_id": 0, "id": 1})
        if target:
            db.activity_logs.delete_many({"reference_id": target["id"]})
            db.users.delete_one({"id": target["id"]})


def test_super_admin_cannot_delete_self():
    admin_token = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    me = requests.get(f"{API}/auth/me", headers=_headers(admin_token), timeout=30).json()["user"]
    response = requests.delete(f"{API}/admin/admin-users/{me['id']}", headers=_headers(admin_token), timeout=30)
    assert response.status_code == 400