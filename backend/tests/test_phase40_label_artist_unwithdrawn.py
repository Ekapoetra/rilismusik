"""Label Artist page must expose unsettled income only."""
import os
import sys
import uuid
from pathlib import Path

import pymongo
import requests
from dotenv import dotenv_values, load_dotenv

sys.path.append(str(Path(__file__).resolve().parents[1]))
from auth_utils import hash_password
from tests.support_config import temporary_password


load_dotenv("/app/backend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"]).rstrip("/")
API = f"{BASE_URL}/api"


def _db():
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


def test_label_artist_cards_exclude_withdrawn_cutoff_draft_and_legacy():
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    label_id = f"ph40-label-{suffix}"
    other_label_id = f"ph40-other-{suffix}"
    user_id = f"ph40-user-{suffix}"
    artist_live_id = f"ph40-artist-live-{suffix}"
    artist_paid_id = f"ph40-artist-paid-{suffix}"
    email = f"ph40-{suffix}@example.com"
    password = temporary_password("phase40")
    now = "2026-08-30T00:00:00+00:00"
    db.users.insert_one({
        "id": user_id, "name": "Phase 40 Label", "email": email,
        "password_hash": hash_password(password), "role": "label", "status": "active",
        "email_verified_at": now, "created_at": now, "updated_at": now, "token_version": 0,
    })
    db.labels.insert_many([
        {
            "id": label_id, "user_id": user_id, "label_name": f"PH40 Label {suffix}",
            "last_withdrawn_period": "2026-06", "account_status": "active",
            "subscription_status": "active", "contract_status": "contract_active",
            "payment_type": "annual_subscription", "bank_verified": True,
        },
        {"id": other_label_id, "label_name": f"PH40 Other {suffix}"},
    ])
    db.artists.insert_many([
        {"id": artist_live_id, "label_id": label_id, "artist_name": "Artist Belum Ditarik", "email": f"live-{suffix}@example.com", "status": "active", "created_at": now},
        {"id": artist_paid_id, "label_id": label_id, "artist_name": "Artist Sudah Ditarik", "email": f"paid-{suffix}@example.com", "status": "active", "created_at": now},
    ])
    db.royalty_lines.insert_many([
        {"id": f"ph40-cutoff-{suffix}", "label_id": label_id, "artist_id": artist_live_id, "period": "2026-06", "status": "pending", "legacy_settled": False, "label_idr": 1_000, "revenue_eur": 1},
        {"id": f"ph40-jul-{suffix}", "label_id": label_id, "artist_id": artist_live_id, "period": "2026-07", "status": "pending", "legacy_settled": False, "label_idr": 200, "revenue_eur": 2},
        {"id": f"ph40-aug-{suffix}", "label_id": label_id, "artist_id": artist_live_id, "period": "2026-08", "status": "available", "legacy_settled": False, "label_idr": 300, "revenue_eur": 3},
        {"id": f"ph40-withdrawn-{suffix}", "label_id": label_id, "artist_id": artist_live_id, "period": "2026-08", "status": "withdrawn", "legacy_settled": False, "label_idr": 9_000, "revenue_eur": 90},
        {"id": f"ph40-draft-{suffix}", "label_id": label_id, "artist_id": artist_live_id, "period": "2026-08", "status": "draft", "legacy_settled": False, "label_idr": 8_000, "revenue_eur": 80},
        {"id": f"ph40-legacy-{suffix}", "label_id": label_id, "artist_id": artist_live_id, "period": "2026-08", "status": "available", "legacy_settled": True, "label_idr": 7_000, "revenue_eur": 70},
        {"id": f"ph40-paid-only-{suffix}", "label_id": label_id, "artist_id": artist_paid_id, "period": "2026-08", "status": "withdrawn", "legacy_settled": False, "label_idr": 6_000, "revenue_eur": 60},
        {"id": f"ph40-other-{suffix}", "label_id": other_label_id, "artist_id": artist_live_id, "period": "2026-08", "status": "available", "legacy_settled": False, "label_idr": 5_000, "revenue_eur": 50},
    ])
    try:
        login = requests.post(
            f"{API}/auth/login", json={"email": email, "password": password}, timeout=30,
        )
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        response = requests.get(f"{API}/artists/", headers=headers, timeout=30)
        assert response.status_code == 200, response.text
        artists = {artist["id"]: artist for artist in response.json()}
        live = artists[artist_live_id]
        assert live["revenue_idr"] == 500
        assert live["revenue_eur"] == 5
        assert live["royalty_lines_count"] == 2
        assert live["first_active_period"] == "2026-07"
        assert live["last_active_period"] == "2026-08"
        assert live["revenue_scope"] == "unwithdrawn"
        paid = artists[artist_paid_id]
        assert paid["revenue_idr"] == 0
        assert paid["royalty_lines_count"] == 0
        assert paid["last_active_period"] is None

        august = requests.get(
            f"{API}/artists/", headers=headers,
            params={"period_from": "2026-08", "period_to": "2026-08"}, timeout=30,
        )
        august_live = {artist["id"]: artist for artist in august.json()}[artist_live_id]
        assert august_live["revenue_idr"] == 300
        assert august_live["royalty_lines_count"] == 1

        settled_range = requests.get(
            f"{API}/artists/", headers=headers,
            params={"period_from": "2026-01", "period_to": "2026-06"}, timeout=30,
        )
        settled_live = {artist["id"]: artist for artist in settled_range.json()}[artist_live_id]
        assert settled_live["revenue_idr"] == 0
        assert settled_live["royalty_lines_count"] == 0
    finally:
        db.royalty_lines.delete_many({"id": {"$regex": f"^ph40-.*-{suffix}$"}})
        db.artists.delete_many({"id": {"$in": [artist_live_id, artist_paid_id]}})
        db.labels.delete_many({"id": {"$in": [label_id, other_label_id]}})
        db.users.delete_one({"id": user_id})