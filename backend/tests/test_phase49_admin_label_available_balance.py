"""Phase 49 — Label Management available-balance column contract."""
import os
import uuid

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
        {"id": positive_id, "label_name": f"Phase49 Positive {suffix}", "balance_available_idr": 1_234_567, "created_at": "2026-09-01T00:00:00+00:00"},
        {"id": negative_id, "label_name": f"Phase49 Negative {suffix}", "balance_available_idr": -500, "created_at": "2026-09-01T00:00:00+00:00"},
    ])
    try:
        login = requests.post(f"{API}/auth/login", json=FINANCE, timeout=30)
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        response = requests.get(f"{API}/admin/labels", params={"q": f"Phase49"}, headers=headers, timeout=30)
        assert response.status_code == 200, response.text
        by_id = {item["id"]: item for item in response.json()}
        assert by_id[positive_id]["balance_available_idr"] == 1_234_567
        assert by_id[negative_id]["balance_available_idr"] == 0
    finally:
        db.labels.delete_many({"id": {"$in": [positive_id, negative_id]}})