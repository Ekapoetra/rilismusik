"""Phase 48 — server-side label search for manual legacy withdrawal picker."""
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


def test_admin_label_search_is_literal_case_insensitive_and_unfiltered_by_withdrawal():
    db = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    suffix = uuid.uuid4().hex[:10]
    label_id = f"phase48-label-{suffix}"
    label_name = f"Phase48 Studio (A+B) {suffix}"
    db.labels.insert_one({
        "id": label_id, "label_name": label_name, "account_status": "active",
        "last_withdrawn_period": "2026-06", "created_at": "2000-01-01T00:00:00+00:00",
    })
    try:
        login = requests.post(
            f"{API}/auth/login", json={"email": FINANCE["email"], "password": FINANCE["password"]}, timeout=30,
        )
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        response = requests.get(
            f"{API}/admin/labels", params={"q": f"phase48 studio (a+b) {suffix}"}, headers=headers, timeout=30,
        )
        assert response.status_code == 200, response.text
        matches = response.json()
        assert [item["id"] for item in matches] == [label_id]
        assert matches[0]["last_withdrawn_period"] == "2026-06"
    finally:
        db.labels.delete_one({"id": label_id})