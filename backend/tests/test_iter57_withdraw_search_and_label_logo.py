"""Iteration 57 — withdraw search across periods + label logo response contract."""
import os
import uuid
from datetime import datetime, timezone

import pymongo
import pytest
import requests

from tests.support_config import DEMO_PPR, FINANCE


# Modules/features under test: /api/withdraw/admin search behavior, /api/admin/labels logo_url, /api/label/me + /api/label/dashboard logo_url
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _login(payload: dict) -> str:
    response = requests.post(f"{API}/auth/login", json=payload, timeout=30)
    if response.status_code != 200:
        pytest.skip(f"Login failed for {payload.get('email')}: {response.status_code} {response.text}")
    return response.json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_withdraw_admin_search_ignores_period_and_supports_unordered_multiword_with_status():
    db = _db()
    suffix = uuid.uuid4().hex[:10]
    label_id = f"iter57-label-{suffix}"
    now_iso = datetime.now(timezone.utc).isoformat()

    db.labels.insert_one({
        "id": label_id,
        "label_name": f"Demo Label PPR {suffix}",
        "email": f"iter57-{suffix}@example.com",
        "created_at": now_iso,
        "updated_at": now_iso,
    })
    wd_ids = {
        "requested_old": f"iter57-wd-old-{suffix}",
        "requested_new": f"iter57-wd-new-{suffix}",
        "paid": f"iter57-wd-paid-{suffix}",
    }
    db.withdraw_requests.insert_many([
        {
            "id": wd_ids["requested_old"],
            "label_id": label_id,
            "status": "requested",
            "amount_idr": 100_000,
            "request_date": "2024-03-02T00:00:00+07:00",
            "created_at": "2024-03-02T00:00:00+07:00",
            "updated_at": now_iso,
        },
        {
            "id": wd_ids["requested_new"],
            "label_id": label_id,
            "status": "requested",
            "amount_idr": 200_000,
            "request_date": "2026-09-03T00:00:00+07:00",
            "created_at": "2026-09-03T00:00:00+07:00",
            "updated_at": now_iso,
        },
        {
            "id": wd_ids["paid"],
            "label_id": label_id,
            "status": "paid",
            "amount_idr": 300_000,
            "request_date": "2025-06-01T00:00:00+07:00",
            "paid_date": "2025-06-10T00:00:00+07:00",
            "created_at": "2025-06-01T00:00:00+07:00",
            "updated_at": now_iso,
        },
    ])

    try:
        headers = _headers(_login(FINANCE))
        response = requests.get(
            f"{API}/withdraw/admin",
            params={"q": "PPR Demo", "status": "requested", "year": 2026, "month": 9},
            headers=headers,
            timeout=30,
        )
        assert response.status_code == 200, response.text
        by_id = {item["id"]: item for item in response.json()}

        assert wd_ids["requested_old"] in by_id
        assert by_id[wd_ids["requested_old"]]["label_name"].startswith("Demo Label PPR")
        assert wd_ids["requested_new"] in by_id
        assert wd_ids["paid"] not in by_id
    finally:
        db.withdraw_requests.delete_many({"id": {"$in": list(wd_ids.values())}})
        db.labels.delete_many({"id": label_id})


def test_withdraw_admin_without_q_keeps_period_filter_and_requires_complete_year_month_pair():
    db = _db()
    suffix = uuid.uuid4().hex[:10]
    label_id = f"iter57-period-label-{suffix}"
    now_iso = datetime.now(timezone.utc).isoformat()
    db.labels.insert_one({
        "id": label_id,
        "label_name": f"Iter57 Period Label {suffix}",
        "email": f"iter57-period-{suffix}@example.com",
        "created_at": now_iso,
        "updated_at": now_iso,
    })
    wd_ids = {
        "sep": f"iter57-period-sep-{suffix}",
        "aug": f"iter57-period-aug-{suffix}",
    }
    db.withdraw_requests.insert_many([
        {
            "id": wd_ids["sep"],
            "label_id": label_id,
            "status": "paid",
            "amount_idr": 90_000,
            "request_date": "2026-08-29T00:00:00+07:00",
            "paid_date": "2026-09-10T00:00:00+07:00",
            "created_at": "2026-08-29T00:00:00+07:00",
            "updated_at": now_iso,
        },
        {
            "id": wd_ids["aug"],
            "label_id": label_id,
            "status": "paid",
            "amount_idr": 80_000,
            "request_date": "2026-08-20T00:00:00+07:00",
            "paid_date": "2026-08-25T00:00:00+07:00",
            "created_at": "2026-08-20T00:00:00+07:00",
            "updated_at": now_iso,
        },
    ])

    try:
        headers = _headers(_login(FINANCE))
        scoped = requests.get(
            f"{API}/withdraw/admin",
            params={"status": "paid", "year": 2026, "month": 9},
            headers=headers,
            timeout=30,
        )
        assert scoped.status_code == 200, scoped.text
        scoped_ids = {item["id"] for item in scoped.json()}
        assert wd_ids["sep"] in scoped_ids
        assert wd_ids["aug"] not in scoped_ids

        incomplete_pair = requests.get(
            f"{API}/withdraw/admin",
            params={"year": 2026},
            headers=headers,
            timeout=30,
        )
        assert incomplete_pair.status_code == 400
        assert incomplete_pair.json()["detail"] == "Tahun dan bulan harus dipilih bersama"
    finally:
        db.withdraw_requests.delete_many({"id": {"$in": list(wd_ids.values())}})
        db.labels.delete_many({"id": label_id})


def test_admin_labels_and_label_endpoints_include_logo_url_contract():
    db = _db()
    suffix = uuid.uuid4().hex[:10]
    with_logo_id = f"iter57-logo-with-{suffix}"
    without_logo_id = f"iter57-logo-without-{suffix}"
    now_iso = datetime.now(timezone.utc).isoformat()

    db.labels.insert_many([
        {
            "id": with_logo_id,
            "label_name": f"Iter57 Logo With {suffix}",
            "email": f"iter57-logo-with-{suffix}@example.com",
            "logo_storage_key": f"label-logo/{with_logo_id}/logo.png",
            "created_at": now_iso,
            "updated_at": now_iso,
        },
        {
            "id": without_logo_id,
            "label_name": f"Iter57 Logo Without {suffix}",
            "email": f"iter57-logo-without-{suffix}@example.com",
            "created_at": now_iso,
            "updated_at": now_iso,
        },
    ])

    try:
        finance_headers = _headers(_login(FINANCE))
        labels_response = requests.get(
            f"{API}/admin/labels",
            params={"q": suffix},
            headers=finance_headers,
            timeout=30,
        )
        assert labels_response.status_code == 200, labels_response.text
        by_id = {item["id"]: item for item in labels_response.json()}

        assert by_id[with_logo_id]["logo_url"] == f"/api/files/label-logo/{with_logo_id}/logo.png"
        assert by_id[without_logo_id]["logo_url"] is None

        label_headers = _headers(_login(DEMO_PPR))
        profile = requests.get(f"{API}/label/me", headers=label_headers, timeout=30)
        dashboard = requests.get(f"{API}/label/dashboard", headers=label_headers, timeout=30)
        assert profile.status_code == 200, profile.text
        assert dashboard.status_code == 200, dashboard.text
        assert "logo_url" in profile.json()
        assert "logo_url" in dashboard.json()["label"]
    finally:
        db.labels.delete_many({"id": {"$in": [with_logo_id, without_logo_id]}})
