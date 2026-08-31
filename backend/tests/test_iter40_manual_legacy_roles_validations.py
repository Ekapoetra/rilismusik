"""Iter 40 — manual legacy withdraw role gate + validation guards."""
import os
import uuid

import pymongo
import requests
from dotenv import load_dotenv

from auth_utils import hash_password
from tests.support_config import FINANCE, SUPERADMIN, SUPPORT, temporary_password


load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/frontend/.env", override=True)
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _token(email: str, password: str) -> str:
    response = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def test_manual_legacy_preview_and_commit_role_guards_and_validations():
    """withdraw/manual-legacy module: role authorization + input/business validation"""
    db = _db()
    suffix = uuid.uuid4().hex[:10]
    label_user_id = f"iter40-user-{suffix}"
    label_id = f"iter40-label-{suffix}"
    email = f"iter40-{suffix}@example.com"
    password = temporary_password("iter40")
    now = "2026-10-01T00:00:00+00:00"

    db.users.insert_one({
        "id": label_user_id,
        "name": "Iter40 Label",
        "email": email,
        "password_hash": hash_password(password),
        "role": "label",
        "status": "active",
        "token_version": 0,
        "email_verified_at": now,
        "created_at": now,
        "updated_at": now,
    })
    db.labels.insert_one({
        "id": label_id,
        "user_id": label_user_id,
        "label_name": f"Iter40 Label {suffix}",
        "account_status": "active",
        "last_withdrawn_period": None,
        "balance_pending_idr": 0,
        "balance_available_idr": 0,
        "balance_withdraw_requested_idr": 0,
        "created_at": now,
        "updated_at": now,
    })
    db.royalty_lines.insert_many([
        {"id": f"iter40-jan-{suffix}", "label_id": label_id, "period": "2026-01", "status": "draft", "legacy_settled": False, "label_idr": 1000},
        {"id": f"iter40-feb-{suffix}", "label_id": label_id, "period": "2026-02", "status": "pending", "legacy_settled": False, "label_idr": 2000},
        {"id": f"iter40-mar-{suffix}", "label_id": label_id, "period": "2026-03", "status": "available", "legacy_settled": False, "label_idr": 3000},
    ])

    payload = {
        "label_id": label_id,
        "period_from": "2026-01",
        "period_to": "2026-03",
        "request_date": "2026-04-01",
        "paid_date": "2026-04-15",
        "note": "iter40 role+validation",
    }

    finance = _token(FINANCE["email"], FINANCE["password"])
    superadmin = _token(SUPERADMIN["email"], SUPERADMIN["password"])
    support = _token(SUPPORT["email"], SUPPORT["password"])

    try:
        support_preview = requests.post(f"{API}/withdraw/admin/legacy-manual/preview", json=payload, headers=_headers(support), timeout=30)
        assert support_preview.status_code == 403
        support_commit = requests.post(f"{API}/withdraw/admin/legacy-manual", json=payload, headers=_headers(support), timeout=30)
        assert support_commit.status_code == 403

        finance_preview = requests.post(f"{API}/withdraw/admin/legacy-manual/preview", json=payload, headers=_headers(finance), timeout=30)
        assert finance_preview.status_code == 200, finance_preview.text
        assert finance_preview.json()["amount_idr"] == 6000

        super_preview = requests.post(f"{API}/withdraw/admin/legacy-manual/preview", json=payload, headers=_headers(superadmin), timeout=30)
        assert super_preview.status_code == 200, super_preview.text

        bad_period = dict(payload)
        bad_period["period_from"] = "2026-04"
        bad_period["period_to"] = "2026-03"
        bad_period_resp = requests.post(f"{API}/withdraw/admin/legacy-manual/preview", json=bad_period, headers=_headers(finance), timeout=30)
        assert bad_period_resp.status_code == 400

        bad_dates = dict(payload)
        bad_dates["request_date"] = "2026-04-10"
        bad_dates["paid_date"] = "2026-04-01"
        bad_dates_resp = requests.post(f"{API}/withdraw/admin/legacy-manual/preview", json=bad_dates, headers=_headers(finance), timeout=30)
        assert bad_dates_resp.status_code == 400

        invalid_label = dict(payload)
        invalid_label["label_id"] = f"missing-{suffix}"
        invalid_label_resp = requests.post(f"{API}/withdraw/admin/legacy-manual/preview", json=invalid_label, headers=_headers(finance), timeout=30)
        assert invalid_label_resp.status_code == 404

        db.withdraw_requests.insert_one({
            "id": f"iter40-active-{suffix}",
            "label_id": label_id,
            "status": "requested",
            "amount_idr": 123,
            "legacy_import": False,
            "created_at": now,
            "updated_at": now,
        })
        blocked_resp = requests.post(f"{API}/withdraw/admin/legacy-manual/preview", json=payload, headers=_headers(finance), timeout=30)
        assert blocked_resp.status_code == 409
        db.withdraw_requests.delete_one({"id": f"iter40-active-{suffix}"})

        db.labels.update_one({"id": label_id}, {"$set": {"last_withdrawn_period": "2025-12"}})
        db.royalty_lines.delete_many({"label_id": label_id})
        db.royalty_lines.insert_many([
            {"id": f"iter40-gap-a-{suffix}", "label_id": label_id, "period": "2026-01", "status": "pending", "legacy_settled": False, "label_idr": 100},
            {"id": f"iter40-gap-b-{suffix}", "label_id": label_id, "period": "2026-03", "status": "available", "legacy_settled": False, "label_idr": 200},
        ])
        gap_payload = dict(payload)
        gap_payload["period_from"] = "2026-03"
        gap_payload["period_to"] = "2026-03"
        gap_resp = requests.post(f"{API}/withdraw/admin/legacy-manual/preview", json=gap_payload, headers=_headers(finance), timeout=30)
        assert gap_resp.status_code == 409
    finally:
        db.migrate_jobs.delete_many({"manual_legacy_key": {"$regex": f"^{label_id}:"}})
        db.balance_transactions.delete_many({"label_id": label_id})
        db.activity_logs.delete_many({"$or": [{"resource_id": {"$regex": f"iter40"}}, {"user_id": label_user_id}]})
        db.withdraw_requests.delete_many({"label_id": label_id})
        db.royalty_lines.delete_many({"label_id": label_id})
        db.labels.delete_one({"id": label_id})
        db.users.delete_one({"id": label_user_id})
