"""Phase 38/33 regression: balance audit RBAC and preview row payload invariants."""
import os
import time
import uuid

import pymongo
import requests

from tests.support_config import FINANCE, SUPPORT


BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


def _db():
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


def _login(creds: dict) -> str:
    response = requests.post(f"{API}/auth/login", json=creds, timeout=30)
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
        time.sleep(0.3)
    raise AssertionError(f"balance-audit job timeout: {job_id}")


# Finance role should be allowed while non-finance admin should be rejected.
def test_balance_audit_preview_rbac_enforced():
    finance_token = _login(FINANCE)
    db = _db()
    ok = requests.post(
        f"{API}/admin/balance-audit/preview",
        headers=_headers(finance_token),
        json={"label_ids": []},
        timeout=20,
    )
    assert ok.status_code == 200, ok.text
    preview_job_id = ok.json()["job_id"]
    preview_job = _wait_job(finance_token, preview_job_id)
    assert preview_job["status"] == "done"
    assert preview_job["summary"]["total_labels"] == 0

    support_token = _login(SUPPORT)
    forbidden = requests.post(
        f"{API}/admin/balance-audit/preview",
        headers=_headers(support_token),
        json={"label_ids": []},
        timeout=20,
    )
    assert forbidden.status_code == 403, forbidden.text
    db.balance_audit_rows.delete_many({"job_id": preview_job_id})
    db.migrate_jobs.delete_many({"id": preview_job_id})


# Preview rows must be ObjectId-free and compute expected balances from royalty lines after cutoff.
def test_balance_audit_preview_poetra_cutoff_payload_invariants():
    token = _login(FINANCE)
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    label_id = f"ITER33_POETRA_{suffix}"

    db.labels.insert_one({
        "id": label_id,
        "label_name": f"ITER33 Poetra {suffix}",
        "last_withdrawn_period": "2026-06",
        "balance_pending_idr": -9_168_938,
        "balance_available_idr": 9_167_085,
        "balance_withdraw_requested_idr": 0,
    })
    db.royalty_lines.insert_many([
        {
            "id": f"ITER33_LINE_P_{suffix}",
            "label_id": label_id,
            "period": "2026-05",
            "status": "pending",
            "label_idr": 5_000_000,
            "legacy_settled": False,
        },
        {
            "id": f"ITER33_LINE_A_{suffix}",
            "label_id": label_id,
            "period": "2026-06",
            "status": "available",
            "label_idr": 4_000_000,
            "legacy_settled": False,
        },
    ])

    preview_job_id = None
    try:
        started = requests.post(
            f"{API}/admin/balance-audit/preview",
            headers=_headers(token),
            json={"label_ids": [label_id]},
            timeout=20,
        )
        assert started.status_code == 200, started.text
        preview_job_id = started.json()["job_id"]

        job = _wait_job(token, preview_job_id)
        assert job["status"] == "done", job.get("error_message")
        summary = job.get("summary") or {}
        assert summary.get("total_labels") == 1
        assert summary.get("drift_labels") == 1
        assert summary.get("negative_balance_labels") == 1
        assert summary.get("stale_cutoff_lines") == 2

        rows_response = requests.get(
            f"{API}/admin/balance-audit/jobs/{preview_job_id}/rows",
            headers=_headers(token),
            params={"limit": 100},
            timeout=20,
        )
        assert rows_response.status_code == 200, rows_response.text
        payload = rows_response.json()
        assert payload["total"] == 1
        assert len(payload["items"]) == 1
        row = payload["items"][0]

        assert "_id" not in row
        assert row["label_id"] == label_id
        assert row["last_withdrawn_period"] == "2026-06"
        assert row["latest_report_period"] == "2026-06"
        assert row["eligible_period_from"] is None
        assert row["eligible_period_to"] is None
        assert row["expected_pending_idr"] == 0
        assert row["expected_available_idr"] == 0
        assert row["current_pending_idr"] == -9_168_938
        assert row["current_available_idr"] == 9_167_085
        assert row["audit_status"] == "drift"
    finally:
        if preview_job_id:
            db.balance_audit_rows.delete_many({"job_id": preview_job_id})
            db.migrate_jobs.delete_many({"id": preview_job_id})
        db.royalty_lines.delete_many({"label_id": label_id})
        db.labels.delete_many({"id": label_id})
