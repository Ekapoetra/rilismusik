"""Phase 60 — guarded royalty import replacement with paid/active withdrawal effects."""
import os
import time
import uuid

import pymongo
import requests

from tests.support_config import SUPERADMIN


BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


def _db():
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


def _token():
    response = requests.post(f"{API}/auth/login", json=SUPERADMIN, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]


def _wait(token, job_id, timeout=90):
    deadline = time.time() + timeout
    headers = {"Authorization": f"Bearer {token}"}
    while time.time() < deadline:
        response = requests.get(
            f"{API}/royalty/admin/imports/replacement/jobs/{job_id}", headers=headers, timeout=20,
        )
        response.raise_for_status()
        job = response.json()
        if job["status"] in ("done", "error"):
            return job
        time.sleep(0.2)
    raise AssertionError(f"replacement job timeout: {job_id}")


def test_replacement_preserves_paid_history_adjusts_balance_and_active_request():
    db = _db()
    token = _token()
    headers = {"Authorization": f"Bearer {token}"}
    suffix = uuid.uuid4().hex[:8]
    old_id = f"ph60-old-{suffix}"
    new_id = f"ph60-new-{suffix}"
    label_id = f"ph60-label-{suffix}"
    paid_id = f"ph60-paid-{suffix}"
    request_id = f"ph60-request-{suffix}"
    preview_id = commit_id = None
    old_import = {
        "id": old_id, "filename": "old.csv", "status": "dana_received",
        "total_lines": 2, "total_revenue_eur": 30.0, "total_label_idr": 300_000,
        "period_start": "2026-01", "period_end": "2026-02", "period": "multi",
        "exchange_rate_eur_idr": 10_000, "r2_key": None,
        "published_at": "2026-03-01T00:00:00+00:00", "dana_received_at": "2026-03-02T00:00:00+00:00",
        "created_at": "2026-03-01T00:00:00+00:00", "updated_at": "2026-03-02T00:00:00+00:00",
    }
    replacement = {
        "id": new_id, "filename": "replacement.csv", "status": "replacement_preview",
        "replacement_stage": True, "replacement_of_import_id": old_id,
        "total_lines": 2, "total_revenue_eur": 37.0, "total_label_idr": 370_000,
        "period_start": "2026-01", "period_end": "2026-02", "period": "multi",
        "exchange_rate_eur_idr": 10_000, "r2_key": None,
        "created_at": "2026-03-03T00:00:00+00:00", "updated_at": "2026-03-03T00:00:00+00:00",
    }
    db.royalty_imports.insert_many([old_import, replacement])
    db.labels.insert_one({
        "id": label_id, "label_name": f"PH60 {suffix}", "last_withdrawn_period": "2026-01",
        "royalty_percentage_default": 100, "balance_pending_idr": 0,
        "balance_available_idr": 0, "balance_withdraw_requested_idr": 200_000,
    })
    db.withdraw_requests.insert_many([
        {"id": paid_id, "label_id": label_id, "status": "paid", "legacy_import": True,
         "period_from": "2026-01", "period_to": "2026-01", "amount_idr": 100_000},
        {"id": request_id, "label_id": label_id, "status": "requested", "legacy_import": False,
         "period_from": "2026-02", "period_to": "2026-12", "amount_idr": 200_000,
         "lines_count": 1},
    ])
    db.balance_transactions.insert_many([
        {"id": f"ph60-old-tx-{suffix}", "label_id": label_id, "type": "royalty_available",
         "amount_idr": 200_000, "reference_type": "royalty_import", "reference_id": old_id},
        {"id": f"ph60-request-tx-{suffix}", "label_id": label_id, "type": "withdraw_request",
         "amount_idr": -200_000, "reference_type": "withdraw", "reference_id": request_id},
    ])
    db.royalty_lines.insert_many([
        {"id": f"ph60-old-historical-{suffix}", "import_id": old_id, "label_id": label_id,
         "period": "2026-01", "status": "withdrawn", "legacy_settled": True,
         "match_status": "matched", "revenue_eur": 10, "label_idr": 100_000},
        {"id": f"ph60-old-active-{suffix}", "import_id": old_id, "label_id": label_id,
         "period": "2026-02", "status": "available", "legacy_settled": False,
         "match_status": "matched", "revenue_eur": 20, "label_idr": 200_000},
        {"id": f"ph60-new-historical-{suffix}", "import_id": new_id, "label_id": label_id,
         "period": "2026-01", "status": "draft", "legacy_settled": False,
         "match_status": "replacement_staged", "replacement_original_match_status": "matched",
         "replacement_stage": True, "revenue_eur": 12, "label_idr": 120_000},
        {"id": f"ph60-new-active-{suffix}", "import_id": new_id, "label_id": label_id,
         "period": "2026-02", "status": "draft", "legacy_settled": False,
         "match_status": "replacement_staged", "replacement_original_match_status": "matched",
         "replacement_stage": True, "revenue_eur": 25, "label_idr": 250_000},
    ])
    try:
        started = requests.post(
            f"{API}/royalty/admin/imports/{old_id}/replacement/{new_id}/preview",
            headers=headers, timeout=20,
        )
        assert started.status_code == 200, started.text
        preview_id = started.json()["job_id"]
        preview = _wait(token, preview_id)
        assert preview["status"] == "done", preview.get("error_message")
        assert preview["summary"]["affected_labels"] == 1
        assert preview["summary"]["active_balance_delta_idr"] == 50_000
        assert preview["summary"]["historical_adjustment_idr"] == 20_000
        rows = requests.get(
            f"{API}/royalty/admin/imports/replacement/jobs/{preview_id}/rows",
            headers=headers, timeout=20,
        ).json()["items"]
        assert rows[0]["active_withdraw"]["old_amount_idr"] == 200_000
        assert rows[0]["active_withdraw"]["new_amount_idr"] == 270_000

        committed = requests.post(
            f"{API}/royalty/admin/imports/{old_id}/replacement/{new_id}/commit",
            headers=headers,
            json={"preview_job_id": preview_id, "confirmation": "GANTI DATA"},
            timeout=20,
        )
        assert committed.status_code == 200, committed.text
        commit_id = committed.json()["job_id"]
        commit = _wait(token, commit_id)
        assert commit["status"] == "done", commit.get("error_message")
        assert commit["result"]["old_lines_deleted"] == 2
        assert commit["result"]["new_lines_activated"] == 2
        assert commit["result"]["historical_adjustments_created"] == 1
        assert commit["result"]["active_withdraws_recalculated"] == 1
        assert db.royalty_imports.find_one({"id": old_id}) is None
        assert db.royalty_lines.count_documents({"import_id": old_id}) == 0
        new_import = db.royalty_imports.find_one({"id": new_id})
        assert new_import["status"] == "dana_received"
        assert new_import["replaced_import_id"] == old_id
        new_historical = db.royalty_lines.find_one({"id": f"ph60-new-historical-{suffix}"})
        new_active = db.royalty_lines.find_one({"id": f"ph60-new-active-{suffix}"})
        assert new_historical["status"] == "withdrawn" and new_historical["legacy_settled"] is True
        assert new_active["status"] == "available" and new_active["legacy_settled"] is False
        adjustment = db.royalty_lines.find_one({"id": f"replacement-adjustment:{new_id}:{label_id}"})
        assert adjustment["label_idr"] == 20_000 and adjustment["status"] == "available"
        assert db.withdraw_requests.find_one({"id": paid_id})["amount_idr"] == 100_000
        active_request = db.withdraw_requests.find_one({"id": request_id})
        assert active_request["amount_idr"] == 270_000
        assert active_request["replacement_revisions"][-1]["old_amount_idr"] == 200_000
        label = db.labels.find_one({"id": label_id})
        assert label["balance_available_idr"] == 0
        assert label["balance_withdraw_requested_idr"] == 270_000
        repeated = requests.post(
            f"{API}/royalty/admin/imports/{old_id}/replacement/{new_id}/commit",
            headers=headers,
            json={"preview_job_id": preview_id, "confirmation": "GANTI DATA"},
            timeout=20,
        )
        assert repeated.status_code == 200 and repeated.json()["already_running"] is True
    finally:
        ids = [item for item in (preview_id, commit_id) if item]
        db.royalty_import_replacement_rows.delete_many({"job_id": {"$in": ids}})
        db.royalty_import_replacements.delete_many({"replacement_import_id": new_id})
        db.migrate_jobs.delete_many({"id": {"$in": ids}})
        db.balance_transactions.delete_many({"label_id": label_id})
        db.withdraw_requests.delete_many({"label_id": label_id})
        db.royalty_lines.delete_many({"import_id": {"$in": [old_id, new_id]}})
        db.royalty_imports.delete_many({"id": {"$in": [old_id, new_id]}})
        db.labels.delete_one({"id": label_id})