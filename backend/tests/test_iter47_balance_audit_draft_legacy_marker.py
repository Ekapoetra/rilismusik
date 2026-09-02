"""Iteration 47 — balance-audit regression for post-cutoff draft/pending/available legacy markers."""
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


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _wait_job(token: str, job_id: str, timeout: int = 90) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = requests.get(
            f"{API}/admin/balance-audit/jobs/{job_id}",
            headers=_headers(token),
            timeout=20,
        )
        response.raise_for_status()
        job = response.json()
        if job.get("status") in ("done", "done_with_errors", "error"):
            return job
        time.sleep(0.2)
    raise AssertionError(f"balance-audit job timeout: {job_id}")


# Feature: preview/commit must include draft legacy markers after cutoff and preserve non-withdrawn statuses.
def test_balance_audit_handles_post_cutoff_draft_legacy_markers_end_to_end():
    db = _db()
    token = _login()
    suffix = uuid.uuid4().hex[:8]
    label_id = f"iter47-draft-{suffix}"
    preview_id = commit_id = verify_id = None

    db.labels.insert_one({
        "id": label_id,
        "label_name": f"ITER47 Draft {suffix}",
        "last_withdrawn_period": "2026-01",
        "royalty_percentage_default": 50,
        "balance_pending_idr": 0,
        "balance_available_idr": 0,
        "balance_withdraw_requested_idr": 0,
    })
    db.withdraw_requests.insert_one({
        "id": f"iter47-paid-{suffix}",
        "label_id": label_id,
        "status": "paid",
        "period_from": "2025-01",
        "period_to": "2026-01",
        "amount_idr": 50_000,
    })
    db.royalty_lines.insert_many([
        {
            "id": f"iter47-draft-line-{suffix}",
            "label_id": label_id,
            "period": "2026-05",
            "status": "draft",
            "legacy_settled": True,
            "legacy_settled_period_end": "2026-05",
            "revenue_eur": 10,
            "exchange_rate": 10_000,
            "label_eur": 6,
            "label_idr": 60_000,
            "distributor_idr": 40_000,
            "label_percentage_applied": 60,
        },
        {
            "id": f"iter47-pending-line-{suffix}",
            "label_id": label_id,
            "period": "2026-06",
            "status": "pending",
            "legacy_settled": True,
            "legacy_settled_period_end": "2026-06",
            "revenue_eur": 4,
            "exchange_rate": 10_000,
            "label_eur": 2.4,
            "label_idr": 24_000,
            "distributor_idr": 16_000,
            "label_percentage_applied": 60,
        },
        {
            "id": f"iter47-available-line-{suffix}",
            "label_id": label_id,
            "period": "2026-07",
            "status": "available",
            "legacy_settled": True,
            "legacy_settled_period_end": "2026-07",
            "revenue_eur": 20,
            "exchange_rate": 10_000,
            "label_eur": 12,
            "label_idr": 120_000,
            "distributor_idr": 80_000,
            "label_percentage_applied": 60,
        },
        {
            "id": f"iter47-historical-{suffix}",
            "label_id": label_id,
            "period": "2026-01",
            "status": "withdrawn",
            "legacy_settled": True,
            "label_idr": 50_000,
        },
    ])

    try:
        started = requests.post(
            f"{API}/admin/balance-audit/preview",
            headers=_headers(token),
            json={"label_ids": [label_id]},
            timeout=20,
        )
        assert started.status_code == 200, started.text
        preview_id = started.json()["job_id"]
        preview = _wait_job(token, preview_id)
        assert preview["status"] == "done", preview.get("error_message")
        assert preview["summary"]["wrongly_settled_lines"] == 3
        assert preview["summary"]["orphan_withdrawn_lines"] == 0
        assert preview["summary"]["orphan_legacy_settled_lines"] == 3

        rows_response = requests.get(
            f"{API}/admin/balance-audit/jobs/{preview_id}/rows",
            headers=_headers(token),
            params={"limit": 100},
            timeout=20,
        )
        assert rows_response.status_code == 200, rows_response.text
        row = rows_response.json()["items"][0]
        assert row["label_id"] == label_id
        assert row["wrongly_settled_lines"] == 3
        assert row["orphan_legacy_settled_lines"] == 3
        assert row["expected_pending_idr"] == 84_000
        assert row["expected_available_idr"] == 120_000

        committed = requests.post(
            f"{API}/admin/balance-audit/commit",
            headers=_headers(token),
            json={"preview_job_id": preview_id},
            timeout=20,
        )
        assert committed.status_code == 200, committed.text
        commit_id = committed.json()["job_id"]
        commit = _wait_job(token, commit_id)
        assert commit["status"] == "done", commit.get("error_message")
        assert commit["result"]["orphan_lines_restored"] == 3

        draft_line = db.royalty_lines.find_one({"id": f"iter47-draft-line-{suffix}"})
        pending_line = db.royalty_lines.find_one({"id": f"iter47-pending-line-{suffix}"})
        available_line = db.royalty_lines.find_one({"id": f"iter47-available-line-{suffix}"})
        historical_line = db.royalty_lines.find_one({"id": f"iter47-historical-{suffix}"})

        assert draft_line["status"] == "draft"
        assert pending_line["status"] == "pending"
        assert available_line["status"] == "available"

        assert draft_line["legacy_settled"] is False
        assert pending_line["legacy_settled"] is False
        assert available_line["legacy_settled"] is False

        assert draft_line["label_percentage_applied"] == 50
        assert pending_line["label_percentage_applied"] == 50
        assert available_line["label_percentage_applied"] == 50

        assert draft_line["label_idr"] == 50_000
        assert pending_line["label_idr"] == 20_000
        assert available_line["label_idr"] == 100_000

        assert historical_line["status"] == "withdrawn"
        assert historical_line["legacy_settled"] is True

        verified = requests.post(
            f"{API}/admin/balance-audit/preview",
            headers=_headers(token),
            json={"label_ids": [label_id]},
            timeout=20,
        )
        assert verified.status_code == 200, verified.text
        verify_id = verified.json()["job_id"]
        verify = _wait_job(token, verify_id)
        assert verify["summary"]["wrongly_settled_lines"] == 0
        assert verify["summary"]["orphan_legacy_settled_lines"] == 0
    finally:
        job_ids = [item for item in (preview_id, commit_id, verify_id) if item]
        db.balance_audit_rows.delete_many({"job_id": {"$in": job_ids}})
        db.migrate_jobs.delete_many({"id": {"$in": job_ids}})
        db.balance_transactions.delete_many({"reference_id": {"$in": job_ids}})
        db.withdraw_requests.delete_many({"label_id": label_id})
        db.royalty_lines.delete_many({"label_id": label_id})
        db.labels.delete_many({"id": label_id})