"""Phase 47 — manual legacy withdrawal range from Admin Withdraw."""
import os
import time
import uuid

import pymongo
import requests
from dotenv import load_dotenv

from auth_utils import hash_password
from tests.support_config import FINANCE, temporary_password


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


def _wait_job(token, job_id, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = requests.get(f"{API}/admin/migrate/jobs/{job_id}", headers=_headers(token), timeout=30)
        assert response.status_code == 200, response.text
        job = response.json()
        if job["status"] in {"done", "error"}:
            return job
        time.sleep(0.5)
    raise AssertionError(f"Job {job_id} timeout")


def test_manual_history_auto_amount_settles_range_and_stays_hidden_from_label():
    db = _db()
    suffix = uuid.uuid4().hex[:10]
    user_id = f"phase47-user-{suffix}"
    label_id = f"phase47-label-{suffix}"
    email = f"phase47-{suffix}@example.com"
    password = temporary_password("ManualLegacy")
    now = "2026-09-01T00:00:00+00:00"
    db.users.insert_one({
        "id": user_id, "name": "Phase 47 Label", "email": email,
        "password_hash": hash_password(password), "role": "label", "status": "active",
        "token_version": 0, "email_verified_at": now, "created_at": now, "updated_at": now,
    })
    db.labels.insert_one({
        "id": label_id, "user_id": user_id, "label_name": f"Phase 47 {suffix}",
        "account_status": "active", "last_withdrawn_period": None,
        "balance_pending_idr": 999999, "balance_available_idr": 999999,
        "balance_withdraw_requested_idr": 0, "created_at": now, "updated_at": now,
    })
    lines = [
        {"id": f"phase47-jan-{suffix}", "label_id": label_id, "period": "2026-01", "status": "draft", "legacy_settled": False, "label_idr": 1000},
        {"id": f"phase47-feb-{suffix}", "label_id": label_id, "period": "2026-02", "status": "pending", "legacy_settled": False, "label_idr": 2000},
        {"id": f"phase47-mar-{suffix}", "label_id": label_id, "period": "2026-03", "status": "available", "legacy_settled": False, "label_idr": 3000},
        {"id": f"phase47-apr-{suffix}", "label_id": label_id, "period": "2026-04", "status": "pending", "legacy_settled": False, "label_idr": 4000},
        {"id": f"phase47-may-{suffix}", "label_id": label_id, "period": "2026-05", "status": "available", "legacy_settled": False, "label_idr": 5000},
    ]
    db.royalty_lines.insert_many(lines)
    finance_token = _login(FINANCE["email"], FINANCE["password"])
    label_token = _login(email, password)
    payload = {
        "label_id": label_id, "period_from": "2026-01", "period_to": "2026-03",
        "request_date": "2026-04-02", "paid_date": "2026-04-18",
        "note": "Migrasi manual Phase 47",
    }
    job_id = None
    try:
        preview = requests.post(f"{API}/withdraw/admin/legacy-manual/preview", json=payload, headers=_headers(finance_token), timeout=30)
        assert preview.status_code == 200, preview.text
        preview_data = preview.json()
        assert preview_data["amount_idr"] == 6000
        assert preview_data["lines_count"] == 3
        assert preview_data["draft_lines"] == 1
        assert preview_data["pending_lines"] == 1
        assert preview_data["available_lines"] == 1

        queued = requests.post(f"{API}/withdraw/admin/legacy-manual", json=payload, headers=_headers(finance_token), timeout=30)
        assert queued.status_code == 200, queued.text
        job_id = queued.json()["job_id"]
        job = _wait_job(finance_token, job_id)
        assert job["status"] == "done", job.get("error_message")
        assert job["result"]["amount_idr"] == 6000
        assert job["result"]["royalty_lines_flipped"] == 3

        settled = list(db.royalty_lines.find({"label_id": label_id, "period": {"$lte": "2026-03"}}, {"_id": 0}))
        assert all(row["status"] == "withdrawn" and row["legacy_settled"] is True for row in settled)
        future = list(db.royalty_lines.find({"label_id": label_id, "period": {"$gt": "2026-03"}}, {"_id": 0}))
        assert {row["status"] for row in future} == {"pending", "available"}
        label = db.labels.find_one({"id": label_id}, {"_id": 0})
        assert label["last_withdrawn_period"] == "2026-03"
        assert label["balance_pending_idr"] == 4000
        assert label["balance_available_idr"] == 5000

        history = db.withdraw_requests.find_one({"label_id": label_id, "manual_legacy": True}, {"_id": 0})
        assert history["amount_idr"] == 6000
        assert history["period_from"] == "2026-01"
        assert history["period_to"] == "2026-03"
        assert history["request_date"] == "2026-04-02"
        assert history["paid_date"] == "2026-04-18"
        assert history["legacy_import"] is True

        label_history = requests.get(f"{API}/withdraw/label", headers=_headers(label_token), timeout=30)
        assert label_history.status_code == 200, label_history.text
        assert history["id"] not in {item["id"] for item in label_history.json()}
        computed = requests.get(f"{API}/withdraw/label/computed", headers=_headers(label_token), timeout=30)
        assert computed.status_code == 200, computed.text
        assert computed.json()["balance_pending_idr"] == 4000
        assert computed.json()["withdrawable_idr"] == 5000

        duplicate = requests.post(f"{API}/withdraw/admin/legacy-manual", json=payload, headers=_headers(finance_token), timeout=30)
        assert duplicate.status_code == 409
    finally:
        if job_id:
            db.migrate_jobs.delete_many({"id": job_id})
        history_ids = [item["id"] for item in db.withdraw_requests.find({"label_id": label_id}, {"_id": 0, "id": 1})]
        db.balance_transactions.delete_many({"reference_id": {"$in": history_ids}})
        db.activity_logs.delete_many({"reference_id": {"$in": history_ids}})
        db.withdraw_requests.delete_many({"label_id": label_id})
        db.royalty_lines.delete_many({"label_id": label_id})
        db.labels.delete_one({"id": label_id})
        db.users.delete_one({"id": user_id})