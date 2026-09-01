"""Phase 54 — nonblocking Label Management backed by materialized balances."""
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


def _wait_refresh(headers, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = requests.get(f"{API}/admin/labels/balance-refresh/status", headers=headers, timeout=10)
        assert response.status_code == 200, response.text
        data = response.json()
        if data.get("status") in {"done", "error"}:
            return data
        time.sleep(0.4)
    raise AssertionError("Balance snapshot refresh timeout")


def test_label_list_returns_fast_then_background_refresh_updates_materialized_balance():
    db = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    suffix = uuid.uuid4().hex[:10]
    label_id = f"phase54-label-{suffix}"
    label_name = f"Phase54 Snapshot {suffix}"
    db.labels.insert_one({
        "id": label_id, "label_name": label_name, "email": f"phase54-{suffix}@example.com",
        "balance_available_idr": 59_557_995, "last_withdrawn_period": "2026-03",
        "created_at": "2026-09-01T00:00:00+00:00",
    })
    db.royalty_lines.insert_many([
        {"id": f"phase54-live-{suffix}", "label_id": label_id, "period": "2026-04", "status": "available", "legacy_settled": False, "label_idr": 13_149_228},
        {"id": f"phase54-cutoff-{suffix}", "label_id": label_id, "period": "2026-03", "status": "available", "legacy_settled": False, "label_idr": 40_000_000},
    ])
    try:
        login = requests.post(f"{API}/auth/login", json=FINANCE, timeout=30)
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        start = time.perf_counter()
        before = requests.get(f"{API}/admin/labels", params={"q": label_name}, headers=headers, timeout=10)
        elapsed = time.perf_counter() - start
        assert before.status_code == 200, before.text
        assert elapsed < 3.0
        assert before.json()[0]["balance_available_idr"] == 59_557_995

        queued = requests.post(f"{API}/admin/labels/balance-refresh", params={"force": "true"}, headers=headers, timeout=10)
        assert queued.status_code == 200, queued.text
        status = _wait_refresh(headers)
        assert status["status"] == "done", status.get("error_message")

        start = time.perf_counter()
        after = requests.get(f"{API}/admin/labels", params={"q": label_name}, headers=headers, timeout=10)
        elapsed_after = time.perf_counter() - start
        assert after.status_code == 200, after.text
        assert elapsed_after < 3.0
        assert after.json()[0]["balance_available_idr"] == 13_149_228
    finally:
        db.royalty_lines.delete_many({"label_id": label_id})
        db.labels.delete_one({"id": label_id})