"""Phase 57 — recover line statuses from the parent royalty import state."""
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


def _login():
    response = requests.post(f"{API}/auth/login", json=SUPERADMIN, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _wait_job(token, job_id, timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = requests.get(
            f"{API}/admin/balance-audit/jobs/{job_id}", headers=_headers(token), timeout=20,
        )
        response.raise_for_status()
        job = response.json()
        if job["status"] in ("done", "done_with_errors", "error"):
            return job
        time.sleep(0.2)
    raise AssertionError(f"balance audit timeout: {job_id}")


def test_received_import_draft_and_pending_lines_become_available():
    db = _db()
    token = _login()
    suffix = uuid.uuid4().hex[:8]
    label_id = f"ph57-label-{suffix}"
    received_id = f"ph57-received-{suffix}"
    published_id = f"ph57-published-{suffix}"
    draft_id = f"ph57-draft-{suffix}"
    preview_id = commit_id = verify_id = None
    db.labels.insert_one({
        "id": label_id,
        "label_name": f"PH57 Label {suffix}",
        "last_withdrawn_period": "2026-01",
        "royalty_percentage_default": 50,
        "balance_pending_idr": 0,
        "balance_available_idr": 0,
        "balance_withdraw_requested_idr": 0,
    })
    db.withdraw_requests.insert_one({
        "id": f"ph57-paid-{suffix}", "label_id": label_id, "status": "paid",
        "period_from": "2025-01", "period_to": "2026-01", "amount_idr": 1,
    })
    db.royalty_imports.insert_many([
        {"id": received_id, "filename": "received.csv", "status": "dana_received"},
        {"id": published_id, "filename": "published.csv", "status": "published"},
        {"id": draft_id, "filename": "draft.csv", "status": "draft"},
    ])

    def line(line_id, import_id, status, period, revenue, label_idr):
        return {
            "id": line_id,
            "import_id": import_id,
            "label_id": label_id,
            "period": period,
            "status": status,
            "legacy_settled": False,
            "revenue_eur": revenue,
            "exchange_rate": 10_000,
            "label_eur": revenue * 0.6,
            "label_idr": label_idr,
            "distributor_idr": round(revenue * 10_000) - label_idr,
            "label_percentage_applied": 60,
        }

    db.royalty_lines.insert_many([
        line(f"ph57-received-draft-{suffix}", received_id, "draft", "2026-05", 20, 120_000),
        line(f"ph57-received-pending-{suffix}", received_id, "pending", "2026-06", 10, 60_000),
        line(f"ph57-published-draft-{suffix}", published_id, "draft", "2026-07", 4, 24_000),
        line(f"ph57-legitimate-draft-{suffix}", draft_id, "draft", "2026-07", 5, 30_000),
    ])
    try:
        started = requests.post(
            f"{API}/admin/balance-audit/preview", headers=_headers(token),
            json={"label_ids": [label_id]}, timeout=20,
        )
        assert started.status_code == 200, started.text
        preview_id = started.json()["job_id"]
        preview = _wait_job(token, preview_id)
        assert preview["status"] == "done"
        assert preview["summary"]["import_status_mismatch_lines"] == 3
        assert preview["summary"]["wrongly_settled_lines"] == 3

        rows = requests.get(
            f"{API}/admin/balance-audit/jobs/{preview_id}/rows",
            headers=_headers(token), params={"limit": 20}, timeout=20,
        ).json()["items"]
        row = rows[0]
        assert row["draft_under_received_import_lines"] == 1
        assert row["pending_under_received_import_lines"] == 1
        assert row["draft_under_published_import_lines"] == 1
        assert row["expected_available_idr"] == 150_000
        assert row["expected_pending_idr"] == 20_000
        assert row["calculation_mismatch_lines"] == 3
        assert row["calculation_mismatch_current_idr"] == 204_000
        assert row["calculation_mismatch_projected_idr"] == 170_000

        diagnostic_response = requests.get(
            f"{API}/admin/balance-audit/labels/{label_id}/diagnostic",
            headers=_headers(token), timeout=30,
        )
        assert diagnostic_response.status_code == 200, diagnostic_response.text
        diagnostic = diagnostic_response.json()
        assert diagnostic["read_only"] is True
        assert diagnostic["totals"]["lines"] == 4
        assert diagnostic["categories"]["belum_mengikuti_laporan_diterima"]["lines"] == 2
        assert diagnostic["categories"]["belum_mengikuti_laporan_diterima"]["label_idr"] == 180_000
        assert diagnostic["categories"]["belum_mengikuti_laporan_terbit"]["lines"] == 1
        assert diagnostic["categories"]["draft_laporan_belum_terbit"]["lines"] == 1

        committed = requests.post(
            f"{API}/admin/balance-audit/commit", headers=_headers(token),
            json={"preview_job_id": preview_id}, timeout=20,
        )
        assert committed.status_code == 200, committed.text
        commit_id = committed.json()["job_id"]
        commit = _wait_job(token, commit_id)
        assert commit["status"] == "done", commit.get("error_message")
        assert commit["result"]["import_status_lines_synchronized"] == 3
        assert commit["result"]["import_status_lines_to_available"] == 2
        assert commit["result"]["import_status_lines_to_pending"] == 1

        received_draft = db.royalty_lines.find_one({"id": f"ph57-received-draft-{suffix}"})
        received_pending = db.royalty_lines.find_one({"id": f"ph57-received-pending-{suffix}"})
        published_draft = db.royalty_lines.find_one({"id": f"ph57-published-draft-{suffix}"})
        legitimate_draft = db.royalty_lines.find_one({"id": f"ph57-legitimate-draft-{suffix}"})
        assert received_draft["status"] == "available"
        assert received_pending["status"] == "available"
        assert published_draft["status"] == "pending"
        assert legitimate_draft["status"] == "draft"
        assert received_draft["label_idr"] == 100_000
        assert received_pending["label_idr"] == 50_000
        assert published_draft["label_idr"] == 20_000

        label = db.labels.find_one({"id": label_id})
        assert label["balance_available_idr"] == 150_000
        assert label["balance_pending_idr"] == 20_000

        verified = requests.post(
            f"{API}/admin/balance-audit/preview", headers=_headers(token),
            json={"label_ids": [label_id]}, timeout=20,
        )
        verify_id = verified.json()["job_id"]
        verify = _wait_job(token, verify_id)
        assert verify["summary"]["import_status_mismatch_lines"] == 0
        assert verify["summary"]["wrongly_settled_lines"] == 0
        assert verify["summary"]["drift_labels"] == 0
    finally:
        job_ids = [item for item in (preview_id, commit_id, verify_id) if item]
        db.balance_audit_rows.delete_many({"job_id": {"$in": job_ids}})
        db.migrate_jobs.delete_many({"id": {"$in": job_ids}})
        db.balance_transactions.delete_many({"reference_id": {"$in": job_ids}})
        db.withdraw_requests.delete_many({"label_id": label_id})
        db.royalty_lines.delete_many({"label_id": label_id})
        db.royalty_imports.delete_many({"id": {"$in": [received_id, published_id, draft_id]}})
        db.labels.delete_one({"id": label_id})