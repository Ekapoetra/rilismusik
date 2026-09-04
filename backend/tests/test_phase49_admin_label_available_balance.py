"""Phase 49 — Label Management available-balance column contract."""
import os
import uuid
import time

import pymongo
import requests
from dotenv import load_dotenv

from tests.support_config import FINANCE


load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/frontend/.env", override=True)
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"


def test_admin_label_list_exposes_nonnegative_reconciled_available_balance():
    db = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    suffix = uuid.uuid4().hex[:10]
    positive_id = f"phase49-positive-{suffix}"
    negative_id = f"phase49-negative-{suffix}"
    db.labels.insert_many([
        {"id": positive_id, "label_name": f"Phase49 Positive {suffix}", "logo_storage_key": f"label-logo/{positive_id}/logo.png", "balance_available_idr": 59_557_995, "last_withdrawn_period": "2026-03", "created_at": "2026-09-01T00:00:00+00:00"},
        {"id": negative_id, "label_name": f"Phase49 Negative {suffix}", "balance_available_idr": -500, "created_at": "2026-09-01T00:00:00+00:00"},
    ])
    db.royalty_lines.insert_many([
        {"id": f"phase49-available-{suffix}", "label_id": positive_id, "period": "2026-04", "status": "available", "legacy_settled": False, "label_idr": 13_149_228},
        {"id": f"phase49-before-cutoff-{suffix}", "label_id": positive_id, "period": "2026-03", "status": "available", "legacy_settled": False, "label_idr": 20_000_000},
        {"id": f"phase49-withdrawn-{suffix}", "label_id": positive_id, "period": "2026-05", "status": "withdrawn", "legacy_settled": False, "label_idr": 40_000_000},
        {"id": f"phase49-legacy-{suffix}", "label_id": positive_id, "period": "2026-05", "status": "available", "legacy_settled": True, "label_idr": 30_000_000},
    ])
    try:
        login = requests.post(f"{API}/auth/login", json=FINANCE, timeout=30)
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        assert requests.post(f"{API}/admin/labels/balance-refresh", params={"force": "true"}, headers=headers, timeout=10).status_code == 200
        deadline = time.time() + 60
        while time.time() < deadline:
            refresh = requests.get(f"{API}/admin/labels/balance-refresh/status", headers=headers, timeout=10).json()
            if refresh.get("status") in {"done", "error"}:
                break
            time.sleep(0.3)
        assert refresh["status"] == "done", refresh
        response = requests.get(f"{API}/admin/labels", params={"q": f"Phase49"}, headers=headers, timeout=30)
        assert response.status_code == 200, response.text
        by_id = {item["id"]: item for item in response.json()}
        assert by_id[positive_id]["stored_balance_available_idr"] == 13_149_228
        assert by_id[positive_id]["balance_available_idr"] == 13_149_228
        assert by_id[positive_id]["logo_url"] == f"/api/files/label-logo/{positive_id}/logo.png"
        assert by_id[negative_id]["balance_available_idr"] == 0
        assert by_id[negative_id]["logo_url"] is None
        detail = requests.get(f"{API}/admin/labels/{positive_id}", headers=headers, timeout=30)
        assert detail.status_code == 200, detail.text
        assert detail.json()["financial_summary"]["available_idr"] == by_id[positive_id]["balance_available_idr"]
        db.withdraw_requests.insert_one({
            "id": f"phase49-active-withdraw-{suffix}", "label_id": positive_id,
            "status": "requested", "legacy_import": False, "amount_idr": 1_000_000,
        })
        assert requests.post(f"{API}/admin/labels/balance-refresh", params={"force": "true"}, headers=headers, timeout=10).status_code == 200
        deadline = time.time() + 60
        while time.time() < deadline:
            refresh = requests.get(f"{API}/admin/labels/balance-refresh/status", headers=headers, timeout=10).json()
            if refresh.get("status") in {"done", "error"}:
                break
            time.sleep(0.3)
        assert refresh["status"] == "done", refresh
        reserved_list = requests.get(f"{API}/admin/labels", params={"q": f"Phase49 Positive {suffix}"}, headers=headers, timeout=30)
        reserved_detail = requests.get(f"{API}/admin/labels/{positive_id}", headers=headers, timeout=30)
        assert reserved_list.status_code == reserved_detail.status_code == 200
        assert reserved_list.json()[0]["balance_available_idr"] == 12_149_228
        assert reserved_detail.json()["financial_summary"]["available_idr"] == 12_149_228
    finally:
        db.withdraw_requests.delete_many({"label_id": {"$in": [positive_id, negative_id]}})
        db.royalty_lines.delete_many({"label_id": {"$in": [positive_id, negative_id]}})
        db.labels.delete_many({"id": {"$in": [positive_id, negative_id]}})