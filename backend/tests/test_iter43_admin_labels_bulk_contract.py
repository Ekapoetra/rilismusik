"""Iter 43 — admin labels bulk computed-balance contract and response hygiene."""
import os
import time
import uuid

import pymongo
import requests
from dotenv import load_dotenv

from tests.support_config import FINANCE


load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/frontend/.env", override=True)
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"


def test_admin_labels_default_balance_sort_uses_computed_values_and_no_objectid_leakage():
    db = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    suffix = uuid.uuid4().hex[:10]
    label_low_computed = {
        "id": f"iter43-low-{suffix}",
        "label_name": f"Iter43 Low Computed {suffix}",
        "email": f"iter43-low-{suffix}@example.com",
        "balance_available_idr": 99_000_000,
        "created_at": "2026-09-01T00:00:00+00:00",
    }
    label_high_computed = {
        "id": f"iter43-high-{suffix}",
        "label_name": f"Iter43 High Computed {suffix}",
        "email": f"iter43-high-{suffix}@example.com",
        "balance_available_idr": 1_000,
        "created_at": "2026-09-01T00:00:00+00:00",
    }
    db.labels.insert_many([label_low_computed, label_high_computed])
    db.royalty_lines.insert_one({
        "id": f"iter43-line-high-{suffix}",
        "label_id": label_high_computed["id"],
        "period": "2026-08",
        "status": "available",
        "legacy_settled": False,
        "label_idr": 5_000_000,
    })

    try:
        login = requests.post(f"{API}/auth/login", json=FINANCE, timeout=30)
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        start = time.perf_counter()
        response = requests.get(
            f"{API}/admin/labels",
            params={"q": f"Iter43", "sort_by": "balance", "sort_dir": "desc"},
            headers=headers,
            timeout=30,
        )
        elapsed = time.perf_counter() - start
        assert response.status_code == 200, response.text
        assert elapsed < 3.0

        items = response.json()
        by_id = {item["id"]: item for item in items}
        assert by_id[label_low_computed["id"]]["stored_balance_available_idr"] == 99_000_000
        assert by_id[label_low_computed["id"]]["balance_available_idr"] == 0
        assert by_id[label_high_computed["id"]]["balance_available_idr"] == 5_000_000
        ordered_ids = [item["id"] for item in items if item["id"] in {label_low_computed["id"], label_high_computed["id"]}]
        assert ordered_ids == [label_high_computed["id"], label_low_computed["id"]]

        assert all("_id" not in item for item in items)

        detail = requests.get(f"{API}/admin/labels/{label_high_computed['id']}", headers=headers, timeout=30)
        assert detail.status_code == 200, detail.text
        assert detail.json()["financial_summary"]["available_idr"] == by_id[label_high_computed["id"]]["balance_available_idr"]
    finally:
        db.withdraw_requests.delete_many({"label_id": {"$in": [label_low_computed["id"], label_high_computed["id"]]}})
        db.royalty_lines.delete_many({"label_id": {"$in": [label_low_computed["id"], label_high_computed["id"]]}})
        db.labels.delete_many({"id": {"$in": [label_low_computed["id"], label_high_computed["id"]]}})
