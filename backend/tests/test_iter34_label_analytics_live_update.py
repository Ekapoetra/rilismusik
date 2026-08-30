"""Iteration 34 — label analytics should reflect live source-line updates."""
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


load_dotenv("/app/backend/.env", override=True)
FRONTEND_ENV = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or FRONTEND_ENV["REACT_APP_BACKEND_URL"]).rstrip("/")
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
    return token


def _headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def test_label_analytics_reads_live_lines_and_keeps_withdrawn_visible():
    # Label analytics endpoint: live source read, withdrawn modern lines remain visible.
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    user_id = f"iter34-live-user-{suffix}"
    label_id = f"iter34-live-label-{suffix}"
    email = f"iter34-live-{suffix}@example.com"
    password = temporary_password("Iter34Live")
    now = "2026-08-30T00:00:00+00:00"
    base_line_id = f"iter34-live-base-{suffix}"
    added_line_id = f"iter34-live-added-{suffix}"

    db.users.insert_one({
        "id": user_id,
        "name": "Iter34 Live Label",
        "email": email,
        "password_hash": hash_password(password),
        "role": "label",
        "status": "active",
        "email_verified_at": now,
        "token_version": 0,
        "created_at": now,
        "updated_at": now,
    })
    db.labels.insert_one({
        "id": label_id,
        "user_id": user_id,
        "label_name": f"Iter34 Live {suffix}",
        "account_status": "active",
        "created_at": now,
        "updated_at": now,
    })
    db.royalty_lines.insert_one({
        "id": base_line_id,
        "label_id": label_id,
        "period": "2026-06",
        "status": "available",
        "legacy_settled": False,
        "quantity": 100,
        "label_idr": 1000,
        "track_title_raw": "Live Song",
        "artist_name_raw": "Live Artist",
        "platform": "Spotify",
        "country": "ID",
    })

    try:
        token = _login(email, password)

        first = requests.get(
            f"{API}/label/analytics",
            headers=_headers(token),
            params={"window": "latest"},
            timeout=30,
        )
        assert first.status_code == 200, first.text
        first_body = first.json()
        assert first_body["latest_report"]["streams"] == 100
        assert first_body["latest_report"]["revenue_idr"] == 1000

        # Simulate newly received line in latest period and ensure endpoint reflects it.
        db.royalty_lines.insert_one({
            "id": added_line_id,
            "label_id": label_id,
            "period": "2026-06",
            "status": "available",
            "legacy_settled": False,
            "quantity": 50,
            "label_idr": 500,
            "track_title_raw": "Live Song 2",
            "artist_name_raw": "Live Artist 2",
            "platform": "Apple Music",
            "country": "US",
        })

        second = requests.get(
            f"{API}/label/analytics",
            headers=_headers(token),
            params={"window": "latest"},
            timeout=30,
        )
        assert second.status_code == 200, second.text
        second_body = second.json()
        assert second_body["latest_report"]["streams"] == 150
        assert second_body["latest_report"]["revenue_idr"] == 1500

        # Convert one modern line to withdrawn; analytics should still include it.
        db.royalty_lines.update_one({"id": added_line_id}, {"$set": {"status": "withdrawn"}})
        third = requests.get(
            f"{API}/label/analytics",
            headers=_headers(token),
            params={"window": "latest"},
            timeout=30,
        )
        assert third.status_code == 200, third.text
        third_body = third.json()
        assert third_body["latest_report"]["streams"] == 150
        assert third_body["latest_report"]["revenue_idr"] == 1500
    finally:
        db.royalty_lines.delete_many({"id": {"$in": [base_line_id, added_line_id]}})
        db.labels.delete_one({"id": label_id})
        db.users.delete_one({"id": user_id})
