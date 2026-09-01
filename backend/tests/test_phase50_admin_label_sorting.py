"""Phase 50 — Label Management sorting and last-withdraw period contract."""
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


def test_label_list_defaults_to_balance_desc_and_supports_alpha_sorting():
    db = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    suffix = uuid.uuid4().hex[:10]
    docs = [
        {"id": f"phase50-alpha-{suffix}", "label_name": f"Phase50 Alpha {suffix}", "email": f"bravo-{suffix}@example.com", "balance_available_idr": 5000, "last_withdrawn_period": "2026-07", "created_at": "2026-09-01T00:00:00+00:00"},
        {"id": f"phase50-beta-{suffix}", "label_name": f"Phase50 beta {suffix}", "email": f"alpha-{suffix}@example.com", "balance_available_idr": 5000, "last_withdrawn_period": None, "created_at": "2026-09-01T00:00:00+00:00"},
        {"id": f"phase50-zulu-{suffix}", "label_name": f"Phase50 Zulu {suffix}", "email": f"zulu-{suffix}@example.com", "balance_available_idr": 1000, "last_withdrawn_period": "2026-02", "created_at": "2026-09-01T00:00:00+00:00"},
    ]
    db.labels.insert_many(docs)
    db.royalty_lines.insert_many([
        {"id": f"phase50-line-alpha-{suffix}", "label_id": docs[0]["id"], "period": "2026-08", "status": "available", "legacy_settled": False, "label_idr": 5000},
        {"id": f"phase50-line-beta-{suffix}", "label_id": docs[1]["id"], "period": "2026-08", "status": "available", "legacy_settled": False, "label_idr": 5000},
        {"id": f"phase50-line-zulu-{suffix}", "label_id": docs[2]["id"], "period": "2026-08", "status": "available", "legacy_settled": False, "label_idr": 1000},
    ])
    ids = {doc["id"] for doc in docs}
    try:
        login = requests.post(f"{API}/auth/login", json=FINANCE, timeout=30)
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        default_response = requests.get(f"{API}/admin/labels", params={"q": "Phase50"}, headers=headers, timeout=30)
        assert default_response.status_code == 200, default_response.text
        default_items = [item for item in default_response.json() if item["id"] in ids]
        assert [item["id"] for item in default_items] == [docs[0]["id"], docs[1]["id"], docs[2]["id"]]
        assert default_items[0]["last_withdrawn_period"] == "2026-07"
        assert default_items[1]["last_withdrawn_period"] is None

        label_desc = requests.get(f"{API}/admin/labels", params={"q": "Phase50", "sort_by": "label", "sort_dir": "desc"}, headers=headers, timeout=30)
        assert label_desc.status_code == 200, label_desc.text
        assert [item["id"] for item in label_desc.json() if item["id"] in ids] == [docs[2]["id"], docs[1]["id"], docs[0]["id"]]

        email_asc = requests.get(f"{API}/admin/labels", params={"q": "Phase50", "sort_by": "email", "sort_dir": "asc"}, headers=headers, timeout=30)
        assert email_asc.status_code == 200, email_asc.text
        assert [item["id"] for item in email_asc.json() if item["id"] in ids] == [docs[1]["id"], docs[0]["id"], docs[2]["id"]]

        balance_asc = requests.get(f"{API}/admin/labels", params={"q": "Phase50", "sort_by": "balance", "sort_dir": "asc"}, headers=headers, timeout=30)
        assert balance_asc.status_code == 200, balance_asc.text
        assert [item["id"] for item in balance_asc.json() if item["id"] in ids] == [docs[2]["id"], docs[0]["id"], docs[1]["id"]]
    finally:
        db.royalty_lines.delete_many({"label_id": {"$in": list(ids)}})
        db.labels.delete_many({"id": {"$in": list(ids)}})