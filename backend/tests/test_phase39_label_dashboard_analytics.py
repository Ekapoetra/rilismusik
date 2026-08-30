"""Label dashboard analytics and admin financial-summary regressions."""
import os
import sys
import uuid
from pathlib import Path

import pymongo
import requests
from dotenv import dotenv_values, load_dotenv

sys.path.append(str(Path(__file__).resolve().parents[1]))
from auth_utils import hash_password
from tests.support_config import SUPERADMIN, temporary_password


load_dotenv("/app/backend/.env")
FRONTEND_ENV = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or FRONTEND_ENV["REACT_APP_BACKEND_URL"]).rstrip("/")
API = f"{BASE_URL}/api"


def _db():
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


def _login(email, password):
    response = requests.post(
        f"{API}/auth/login", json={"email": email, "password": password}, timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_label_analytics_and_admin_financial_summary_are_complete_and_isolated():
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    label_id = f"ph39-label-{suffix}"
    other_label_id = f"ph39-other-{suffix}"
    user_id = f"ph39-user-{suffix}"
    email = f"ph39-{suffix}@example.com"
    password = temporary_password("phase39")
    now = "2026-08-27T00:00:00+00:00"
    db.users.insert_one({
        "id": user_id, "name": "Phase 39 Label", "email": email,
        "password_hash": hash_password(password), "role": "label", "status": "active",
        "email_verified_at": now, "created_at": now, "updated_at": now, "token_version": 0,
    })
    db.labels.insert_many([
        {
            "id": label_id, "user_id": user_id, "label_name": f"PH39 Label {suffix}",
            "last_withdrawn_period": "2025-12", "balance_pending_idr": 999_999,
            "balance_available_idr": 999_999, "balance_withdraw_requested_idr": 0,
            "account_status": "active", "subscription_status": "active",
            "contract_status": "contract_active", "payment_type": "annual_subscription",
            "bank_verified": True, "created_at": now, "updated_at": now,
        },
        {"id": other_label_id, "label_name": f"PH39 Other {suffix}", "account_status": "active"},
    ])
    lines = [
        # Hidden legacy-settled data must not leak to label analytics.
        {"id": f"ph39-legacy-{suffix}", "label_id": label_id, "period": "2024-12", "status": "withdrawn", "legacy_settled": True, "quantity": 99_999, "label_idr": 9_999_999, "track_title_raw": "Legacy Hidden", "artist_name_raw": "Legacy", "platform": "Legacy DSP", "country": "XX"},
        {"id": f"ph39-jan-{suffix}", "label_id": label_id, "period": "2026-01", "status": "withdrawn", "legacy_settled": False, "quantity": 10, "label_idr": 100, "track_title_raw": "Song A", "artist_name_raw": "Artist A", "platform": "Spotify", "country": "ID"},
        {"id": f"ph39-feb-{suffix}", "label_id": label_id, "period": "2026-02", "status": "withdrawn", "legacy_settled": False, "quantity": 20, "label_idr": 200, "track_title_raw": "Song B", "artist_name_raw": "Artist B", "platform": "Apple Music", "country": "US"},
        {"id": f"ph39-mar-{suffix}", "label_id": label_id, "period": "2026-03", "status": "withdrawn", "legacy_settled": False, "quantity": 30, "label_idr": 300, "track_title_raw": "Song A", "artist_name_raw": "Artist A", "platform": "Spotify", "country": "ID"},
        {"id": f"ph39-apr-{suffix}", "label_id": label_id, "period": "2026-04", "status": "pending", "legacy_settled": False, "quantity": 40, "label_idr": 400, "track_title_raw": "Song C", "artist_name_raw": "Artist C", "platform": "YouTube Music", "country": "ID"},
        {"id": f"ph39-may-{suffix}", "label_id": label_id, "period": "2026-05", "status": "available", "legacy_settled": False, "quantity": 50, "label_idr": 500, "track_title_raw": "Song A", "artist_name_raw": "Artist A", "platform": "Spotify", "country": "ID"},
        {"id": f"ph39-jun-a-{suffix}", "label_id": label_id, "period": "2026-06", "status": "available", "legacy_settled": False, "quantity": 100, "label_idr": 1_000, "track_title_raw": "Song A", "artist_name_raw": "Artist A", "platform": "Spotify", "country": "ID"},
        {"id": f"ph39-jun-b-{suffix}", "label_id": label_id, "period": "2026-06", "status": "available", "legacy_settled": False, "quantity": 50, "label_idr": 2_000, "track_title_raw": "Song B", "artist_name_raw": "Artist B", "platform": "Apple Music", "country": "US"},
        # Draft/unpublished and another label are never visible.
        {"id": f"ph39-draft-{suffix}", "label_id": label_id, "period": "2026-06", "status": "draft", "legacy_settled": False, "quantity": 1_000_000, "label_idr": 1_000_000, "track_title_raw": "Draft Hidden", "artist_name_raw": "Hidden", "platform": "Hidden", "country": "ZZ"},
        {"id": f"ph39-other-line-{suffix}", "label_id": other_label_id, "period": "2026-06", "status": "available", "legacy_settled": False, "quantity": 2_000_000, "label_idr": 2_000_000, "track_title_raw": "Other Hidden", "artist_name_raw": "Other", "platform": "Other", "country": "OO"},
    ]
    db.royalty_lines.insert_many(lines)
    paid_id = f"ph39-paid-{suffix}"
    active_id = f"ph39-active-{suffix}"
    db.withdraw_requests.insert_many([
        {"id": paid_id, "label_id": label_id, "status": "paid", "amount_idr": 600, "legacy_import": False},
        {"id": active_id, "label_id": label_id, "status": "approved", "amount_idr": 500, "legacy_import": False},
    ])
    try:
        label_token = _login(email, password)
        latest_response = requests.get(
            f"{API}/label/analytics", headers=_headers(label_token), params={"window": "latest"}, timeout=30,
        )
        assert latest_response.status_code == 200, latest_response.text
        latest = latest_response.json()
        assert latest["latest_period"] == "2026-06"
        assert latest["period_from"] == "2026-06"
        assert latest["latest_report"] == {"streams": 150, "revenue_idr": 3_000, "lines": 2}
        assert latest["totals"] == latest["latest_report"]
        assert latest["top_tracks"][0]["title"] == "Song A"
        assert latest["top_tracks"][0]["streams"] == 100
        assert latest["top_platforms"][0]["name"] == "Spotify"
        assert latest["top_countries"][0]["name"] == "ID"
        assert all(item["name"] not in ("Hidden", "Other", "Legacy DSP") for item in latest["top_platforms"])

        six_response = requests.get(
            f"{API}/label/analytics", headers=_headers(label_token), params={"window": "6"}, timeout=30,
        )
        assert six_response.status_code == 200
        six = six_response.json()
        assert six["period_from"] == "2026-01"
        assert six["period_to"] == "2026-06"
        assert [row["period"] for row in six["monthly"]] == [
            "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06",
        ]
        assert six["totals"]["streams"] == 300
        assert six["totals"]["revenue_idr"] == 4_500
        assert six["top_tracks"][0]["title"] == "Song A"
        assert six["top_tracks"][0]["streams"] == 190

        twelve = requests.get(
            f"{API}/label/analytics", headers=_headers(label_token), params={"window": "12"}, timeout=30,
        ).json()
        assert len(twelve["monthly"]) == 12
        assert twelve["monthly"][0]["period"] == "2025-07"
        assert twelve["monthly"][0]["streams"] == 0

        dashboard = requests.get(f"{API}/label/dashboard", headers=_headers(label_token), timeout=30)
        assert dashboard.status_code == 200
        stats = dashboard.json()["stats"]
        # Source available 3,500 minus approved reservation 500.
        assert stats["balance_available_idr"] == 3_000
        assert stats["balance_pending_idr"] == 400
        assert stats["balance_withdraw_requested_idr"] == 500
        assert stats["latest_report_period"] == "2026-06"
        assert stats["balance_source"] == "royalty_lines_fifo"

        admin_token = _login(SUPERADMIN["email"], SUPERADMIN["password"])
        admin_detail = requests.get(
            f"{API}/admin/labels/{label_id}", headers=_headers(admin_token), timeout=30,
        )
        assert admin_detail.status_code == 200, admin_detail.text
        summary = admin_detail.json()["financial_summary"]
        # Admin lifetime includes historical/legacy royalty, but excludes draft.
        assert summary["total_royalty_idr"] == 9_999_999 + 4_500
        assert summary["total_streams"] == 99_999 + 300
        assert summary["withdrawn_paid_idr"] == 600
        assert summary["withdraw_processing_idr"] == 500
        assert summary["available_idr"] == 3_000
        assert summary["pending_idr"] == 400
        assert summary["total_unwithdrawn_idr"] == 3_900
        assert summary["latest_period"] == "2026-06"
    finally:
        db.withdraw_requests.delete_many({"id": {"$in": [paid_id, active_id]}})
        db.royalty_lines.delete_many({"id": {"$regex": f"^ph39-.*-{suffix}$"}})
        db.labels.delete_many({"id": {"$in": [label_id, other_label_id]}})
        db.users.delete_one({"id": user_id})