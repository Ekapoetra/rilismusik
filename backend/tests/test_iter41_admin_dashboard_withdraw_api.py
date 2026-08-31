"""Iter 41 — Admin dashboard withdrawn/unwithdrawn API + cache compatibility regression tests."""
import os
import uuid

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

from tests.support_config import SUPERADMIN


load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/frontend/.env", override=True)
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


def _login_superadmin_token() -> str:
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": SUPERADMIN["email"], "password": SUPERADMIN["password"]},
        timeout=30,
    )
    assert r.status_code == 200, f"superadmin login failed: {r.status_code} {r.text}"
    token = r.json().get("access_token")
    assert token and isinstance(token, str)
    return token


@pytest.mark.skipif(not BASE_URL, reason="REACT_APP_BACKEND_URL is required")
def test_admin_dashboard_returns_withdraw_breakdown_and_no_object_id_fields():
    # Module: /api/admin/dashboard service contract
    token = _login_superadmin_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Force refresh first so dashboard returns current breakdown fields.
    rr = requests.post(f"{BASE_URL}/api/admin/dashboard/refresh-revenue", headers=headers, timeout=120)
    assert rr.status_code == 200, f"refresh failed: {rr.status_code} {rr.text}"

    r = requests.get(f"{BASE_URL}/api/admin/dashboard", headers=headers, timeout=60)
    assert r.status_code == 200, f"dashboard failed: {r.status_code} {r.text}"
    data = r.json()

    assert "total_label_withdrawn_idr" in data
    assert "total_label_unwithdrawn_idr" in data
    assert isinstance(data["total_label_withdrawn_idr"], (int, float))
    assert isinstance(data["total_label_unwithdrawn_idr"], (int, float))
    assert data["total_label_withdrawn_idr"] + data["total_label_unwithdrawn_idr"] == data["total_revenue_idr"]

    assert "_id" not in data
    if isinstance(data.get("last_csv_import"), dict):
        assert "_id" not in data["last_csv_import"]


def test_legacy_metrics_cache_document_gets_upgraded_with_breakdown_after_refresh():
    # Module: metrics_cache persisted contract backward compatibility
    token = _login_superadmin_token()
    headers = {"Authorization": f"Bearer {token}"}

    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    assert mongo_url and db_name

    client = MongoClient(mongo_url)
    metrics = client[db_name].metrics_cache
    backup = metrics.find_one({"_id": "dashboard_revenue"})
    try:
        metrics.update_one(
            {"_id": "dashboard_revenue"},
            {
                "$set": {"total_eur": 12.34, "total_idr": 1234, "computed_at": 1000},
                "$unset": {"withdrawn_idr": "", "unwithdrawn_idr": ""},
            },
            upsert=True,
        )
        rr = requests.post(f"{BASE_URL}/api/admin/dashboard/refresh-revenue", headers=headers, timeout=120)
        assert rr.status_code == 200, f"refresh failed: {rr.status_code} {rr.text}"

        persisted = metrics.find_one({"_id": "dashboard_revenue"}, {"_id": 0})
        assert "withdrawn_idr" in persisted
        assert "unwithdrawn_idr" in persisted
    finally:
        if backup:
            metrics.replace_one({"_id": "dashboard_revenue"}, backup, upsert=True)
        else:
            metrics.delete_one({"_id": "dashboard_revenue"})
        client.close()


def test_withdrawn_logic_no_double_count_when_status_withdrawn_and_legacy_settled_true():
    # Module: dashboard_cache withdrawn aggregation condition via API refresh
    token = _login_superadmin_token()
    headers = {"Authorization": f"Bearer {token}"}

    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    assert mongo_url and db_name

    client = MongoClient(mongo_url)
    royalty_lines = client[db_name].royalty_lines

    d0 = requests.get(f"{BASE_URL}/api/admin/dashboard", headers=headers, timeout=60).json()
    w0 = d0["total_label_withdrawn_idr"]
    u0 = d0["total_label_unwithdrawn_idr"]
    t0 = d0["total_revenue_idr"]

    suffix = uuid.uuid4().hex[:10]
    line_id = f"iter41-double-count-{suffix}"
    royalty_lines.insert_one(
        {
            "id": line_id,
            "label_id": f"iter41-label-{suffix}",
            "status": "withdrawn",
            "legacy_settled": True,
            "label_idr": 777,
            "revenue_eur": 0,
        }
    )
    try:
        rr = requests.post(f"{BASE_URL}/api/admin/dashboard/refresh-revenue", headers=headers, timeout=120)
        assert rr.status_code == 200, f"refresh failed: {rr.status_code} {rr.text}"

        d1 = requests.get(f"{BASE_URL}/api/admin/dashboard", headers=headers, timeout=60).json()
        assert d1["total_label_withdrawn_idr"] - w0 == 777
        assert d1["total_revenue_idr"] - t0 == 777
        assert d1["total_label_unwithdrawn_idr"] - u0 == 0
        assert d1["total_label_withdrawn_idr"] + d1["total_label_unwithdrawn_idr"] == d1["total_revenue_idr"]
    finally:
        royalty_lines.delete_one({"id": line_id})
        requests.post(f"{BASE_URL}/api/admin/dashboard/refresh-revenue", headers=headers, timeout=120)
        client.close()
