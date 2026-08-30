"""Iteration 36: label /artists unsettled-only rollup regression checks."""
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


load_dotenv("/app/backend/.env", override=True)
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"]).rstrip("/")
API = f"{BASE_URL}/api"


def _db():
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


def _login(email: str, password: str):
    response = requests.post(
        f"{API}/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    assert response.status_code == 200, response.text
    token = response.json().get("access_token")
    assert token
    return {"Authorization": f"Bearer {token}"}


def test_label_artists_unwithdrawn_scope_with_cutoff_and_filters():
    # Module: /artists label-facing unsettled rollup and period filters.
    db = _db()
    suffix = uuid.uuid4().hex[:8]

    label_id = f"iter36-label-{suffix}"
    other_label_id = f"iter36-other-{suffix}"
    user_id = f"iter36-user-{suffix}"
    active_artist_id = f"iter36-artist-active-{suffix}"
    paid_artist_id = f"iter36-artist-paid-{suffix}"
    email = f"iter36-label-{suffix}@example.com"
    password = temporary_password("Iter36Label")
    now = "2026-02-20T00:00:00+00:00"

    db.users.insert_one({
        "id": user_id,
        "name": "ITER36 Label",
        "email": email,
        "password_hash": hash_password(password),
        "role": "label",
        "status": "active",
        "email_verified_at": now,
        "created_at": now,
        "updated_at": now,
        "token_version": 0,
    })
    db.labels.insert_many([
        {
            "id": label_id,
            "user_id": user_id,
            "label_name": f"ITER36 Label {suffix}",
            "last_withdrawn_period": "2026-08",
            "account_status": "active",
            "subscription_status": "active",
            "contract_status": "contract_active",
            "payment_type": "annual_subscription",
            "bank_verified": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": other_label_id,
            "label_name": f"ITER36 Other {suffix}",
            "created_at": now,
            "updated_at": now,
        },
    ])
    db.artists.insert_many([
        {
            "id": active_artist_id,
            "label_id": label_id,
            "artist_name": "ITER36 Artist Name With Very Long Name For Overflow Regression Check",
            "email": f"active-{suffix}@example.com",
            "status": "active",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": paid_artist_id,
            "label_id": label_id,
            "artist_name": "ITER36 Paid Artist",
            "email": f"paid-{suffix}@example.com",
            "status": "active",
            "created_at": now,
            "updated_at": now,
        },
    ])
    db.royalty_lines.insert_many([
        {"id": f"iter36-cutoff-{suffix}", "label_id": label_id, "artist_id": active_artist_id, "period": "2026-08", "status": "pending", "legacy_settled": False, "label_idr": 10_000, "revenue_eur": 1},
        {"id": f"iter36-pending-{suffix}", "label_id": label_id, "artist_id": active_artist_id, "period": "2026-09", "status": "pending", "legacy_settled": False, "label_idr": 1_500_000, "revenue_eur": 15},
        {"id": f"iter36-available-{suffix}", "label_id": label_id, "artist_id": active_artist_id, "period": "2026-10", "status": "available", "legacy_settled": False, "label_idr": 2_100_000, "revenue_eur": 21},
        {"id": f"iter36-withdrawn-{suffix}", "label_id": label_id, "artist_id": active_artist_id, "period": "2026-10", "status": "withdrawn", "legacy_settled": False, "label_idr": 9_000_000, "revenue_eur": 90},
        {"id": f"iter36-draft-{suffix}", "label_id": label_id, "artist_id": active_artist_id, "period": "2026-10", "status": "draft", "legacy_settled": False, "label_idr": 8_000_000, "revenue_eur": 80},
        {"id": f"iter36-legacy-{suffix}", "label_id": label_id, "artist_id": active_artist_id, "period": "2026-10", "status": "available", "legacy_settled": True, "label_idr": 7_000_000, "revenue_eur": 70},
        {"id": f"iter36-other-label-{suffix}", "label_id": other_label_id, "artist_id": active_artist_id, "period": "2026-10", "status": "available", "legacy_settled": False, "label_idr": 6_000_000, "revenue_eur": 60},
        {"id": f"iter36-paid-only-{suffix}", "label_id": label_id, "artist_id": paid_artist_id, "period": "2026-10", "status": "withdrawn", "legacy_settled": False, "label_idr": 5_000_000, "revenue_eur": 50},
    ])

    try:
        label_headers = _login(email, password)

        label_list = requests.get(f"{API}/artists/", headers=label_headers, timeout=30)
        assert label_list.status_code == 200, label_list.text
        items = label_list.json()
        by_id = {artist["id"]: artist for artist in items}
        assert active_artist_id in by_id and paid_artist_id in by_id

        active = by_id[active_artist_id]
        assert "_id" not in active
        assert active["revenue_scope"] == "unwithdrawn"
        assert active["revenue_idr"] == 3_600_000
        assert active["revenue_eur"] == 36
        assert active["royalty_lines_count"] == 2
        assert active["first_active_period"] == "2026-09"
        assert active["last_active_period"] == "2026-10"

        paid = by_id[paid_artist_id]
        assert paid["revenue_idr"] == 0
        assert paid["royalty_lines_count"] == 0
        assert paid["first_active_period"] is None
        assert paid["last_active_period"] is None

        period_filtered = requests.get(
            f"{API}/artists/",
            headers=label_headers,
            params={"period_from": "2026-10", "period_to": "2026-10"},
            timeout=30,
        )
        assert period_filtered.status_code == 200
        active_oct = {artist["id"]: artist for artist in period_filtered.json()}[active_artist_id]
        assert active_oct["revenue_idr"] == 2_100_000
        assert active_oct["royalty_lines_count"] == 1

        strict_cutoff = requests.get(
            f"{API}/artists/",
            headers=label_headers,
            params={"period_from": "2026-01", "period_to": "2026-08"},
            timeout=30,
        )
        assert strict_cutoff.status_code == 200
        active_cutoff = {artist["id"]: artist for artist in strict_cutoff.json()}[active_artist_id]
        assert active_cutoff["revenue_idr"] == 0
        assert active_cutoff["royalty_lines_count"] == 0

        # Admin endpoint remains available and keeps its own rollup pipeline.
        admin_headers = _login(SUPERADMIN["email"], SUPERADMIN["password"])
        admin_list = requests.get(f"{API}/admin/artists", headers=admin_headers, timeout=30)
        assert admin_list.status_code == 200, admin_list.text
        admin_item = next((a for a in admin_list.json() if a.get("id") == paid_artist_id), None)
        assert admin_item is not None
        assert "revenue_idr" in admin_item
        assert "royalty_lines_count" in admin_item
    finally:
        db.royalty_lines.delete_many({"id": {"$regex": f"^iter36-.*-{suffix}$"}})
        db.artists.delete_many({"id": {"$in": [active_artist_id, paid_artist_id]}})
        db.labels.delete_many({"id": {"$in": [label_id, other_label_id]}})
        db.users.delete_one({"id": user_id})
