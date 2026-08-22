"""Phase 32 — label-facing endpoints must hide legacy-settled royalties/history."""
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


def _db():
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


def _token(email, password):
    response = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_label_endpoints_hide_legacy_and_compute_only_post_cutoff_available():
    db = _db()
    suffix = uuid.uuid4().hex[:10]
    label_id = f"phase32-vis-label-{suffix}"
    user_id = f"phase32-vis-user-{suffix}"
    email = f"phase32-vis-{suffix}@example.com"
    password = "Phase32Vis#2026"
    now = "2026-08-01T00:00:00+00:00"

    db.users.insert_one({
        "id": user_id,
        "name": "Phase 32 Visibility",
        "email": email,
        "password_hash": hash_password(password),
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
        "label_name": f"Phase32 Visibility {suffix}",
        "royalty_percentage_default": 95.0,
        "last_withdrawn_period": "2024-12",
        "balance_pending_idr": 200,
        "balance_available_idr": 300,
        "balance_withdraw_requested_idr": 0,
        "account_status": "active",
        "bank_verified": True,
        "created_at": now,
        "updated_at": now,
    })

    db.royalty_lines.insert_many([
        {
            "id": f"legacy-withdrawn-{suffix}",
            "label_id": label_id,
            "period": "2024-11",
            "status": "withdrawn",
            "legacy_settled": True,
            "label_idr": 100,
            "quantity": 1,
            "track_title_raw": "Legacy Hidden",
            "artist_name_raw": "Legacy",
            "match_status": "matched",
        },
        {
            "id": f"legacy-available-{suffix}",
            "label_id": label_id,
            "period": "2024-12",
            "status": "available",
            "legacy_settled": True,
            "label_idr": 150,
            "quantity": 1,
            "track_title_raw": "Legacy Available Hidden",
            "artist_name_raw": "Legacy",
            "match_status": "matched",
        },
        {
            "id": f"active-pending-{suffix}",
            "label_id": label_id,
            "period": "2025-01",
            "status": "pending",
            "legacy_settled": False,
            "label_idr": 200,
            "quantity": 2,
            "track_title_raw": "Active Pending",
            "artist_name_raw": "Now",
            "match_status": "matched",
        },
        {
            "id": f"active-available-{suffix}",
            "label_id": label_id,
            "period": "2025-02",
            "status": "available",
            "legacy_settled": False,
            "label_idr": 300,
            "quantity": 3,
            "track_title_raw": "Active Available",
            "artist_name_raw": "Now",
            "match_status": "matched",
        },
    ])

    db.withdraw_requests.insert_many([
        {
            "id": f"legacy-wd-{suffix}",
            "label_id": label_id,
            "amount_idr": 123,
            "status": "paid",
            "legacy_import": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": f"normal-wd-{suffix}",
            "label_id": label_id,
            "amount_idr": 77,
            "status": "requested",
            "legacy_import": False,
            "created_at": now,
            "updated_at": now,
        },
    ])

    try:
        token = _token(email, password)

        months = requests.get(f"{API}/royalty/months", headers=_headers(token), timeout=30)
        months.raise_for_status()
        months_data = months.json()
        assert "2024-11" not in months_data
        assert "2024-12" not in months_data
        assert set(months_data) == {"2025-01", "2025-02"}

        summary = requests.get(f"{API}/royalty/summary", headers=_headers(token), timeout=30)
        summary.raise_for_status()
        assert summary.json()["summary"]["total_idr"] == 500

        lines = requests.get(f"{API}/royalty/lines", headers=_headers(token), timeout=30)
        lines.raise_for_status()
        line_ids = {row["id"] for row in lines.json()}
        assert f"legacy-withdrawn-{suffix}" not in line_ids
        assert f"legacy-available-{suffix}" not in line_ids
        assert {f"active-pending-{suffix}", f"active-available-{suffix}"}.issubset(line_ids)

        export_csv = requests.get(f"{API}/royalty/export.csv", headers=_headers(token), timeout=30)
        export_csv.raise_for_status()
        export_text = export_csv.text
        assert "Legacy Hidden" not in export_text
        assert "Legacy Available Hidden" not in export_text
        assert "Active Pending" in export_text
        assert "Active Available" in export_text

        withdraw_history = requests.get(f"{API}/withdraw/label", headers=_headers(token), timeout=30)
        withdraw_history.raise_for_status()
        history_ids = {row["id"] for row in withdraw_history.json()}
        assert f"legacy-wd-{suffix}" not in history_ids
        assert f"normal-wd-{suffix}" in history_ids

        computed = requests.get(f"{API}/withdraw/label/computed", headers=_headers(token), timeout=30)
        computed.raise_for_status()
        computed_data = computed.json()
        assert computed_data["withdrawable_idr"] == 300
        assert computed_data["period_from"] == "2025-02"
        assert computed_data["period_to"] == "2025-02"
    finally:
        db.withdraw_requests.delete_many({"label_id": label_id})
        db.royalty_lines.delete_many({"label_id": label_id})
        db.labels.delete_many({"id": label_id})
        db.users.delete_many({"id": user_id})
