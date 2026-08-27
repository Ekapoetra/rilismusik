"""Financial-invariant coverage for FIFO balance audit and reconciliation."""
import csv
import io
import os
import time
import uuid

import pymongo
import pytest
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


def _wait_job(token, job_id, path="balance-audit", timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = requests.get(f"{API}/admin/{path}/jobs/{job_id}", headers=_headers(token), timeout=20)
        response.raise_for_status()
        job = response.json()
        if job["status"] in ("done", "done_with_errors", "error", "receive_error", "dana_received"):
            return job
        time.sleep(0.2)
    raise AssertionError(f"job {job_id} tidak selesai")


@pytest.fixture(scope="module")
def super_token():
    return _login()


def test_global_preview_and_commit_reconcile_cutoff_balances(super_token):
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    poetra_id = f"ph38-poetra-{suffix}"
    future_id = f"ph38-future-{suffix}"
    active_id = f"ph38-active-{suffix}"
    label_ids = [poetra_id, future_id, active_id]
    db.labels.insert_many([
        {
            "id": poetra_id, "label_name": f"Poetra Studio PH38 {suffix}",
            "last_withdrawn_period": "2026-06", "balance_pending_idr": -9_168_938,
            "balance_available_idr": 9_167_085, "balance_withdraw_requested_idr": 0,
        },
        {
            "id": future_id, "label_name": f"Future Label PH38 {suffix}",
            "last_withdrawn_period": "2026-06", "balance_pending_idr": 0,
            "balance_available_idr": 0, "balance_withdraw_requested_idr": 0,
        },
        {
            "id": active_id, "label_name": f"Active Label PH38 {suffix}",
            "last_withdrawn_period": "2026-06", "balance_pending_idr": 0,
            "balance_available_idr": 0, "balance_withdraw_requested_idr": 500_000,
        },
    ])
    lines = [
        {"id": f"ph38-poetra-p-{suffix}", "label_id": poetra_id, "period": "2026-05", "status": "pending", "label_idr": 5_000_000, "legacy_settled": False},
        {"id": f"ph38-poetra-a-{suffix}", "label_id": poetra_id, "period": "2026-06", "status": "available", "label_idr": 4_000_000, "legacy_settled": False},
        {"id": f"ph38-future-p-{suffix}", "label_id": future_id, "period": "2026-07", "status": "pending", "label_idr": 100_000, "legacy_settled": False},
        {"id": f"ph38-future-a-{suffix}", "label_id": future_id, "period": "2026-07", "status": "available", "label_idr": 200_000, "legacy_settled": False},
        {"id": f"ph38-active-a-{suffix}", "label_id": active_id, "period": "2026-07", "status": "available", "label_idr": 500_000, "legacy_settled": False},
    ]
    db.royalty_lines.insert_many(lines)
    withdraw_id = f"ph38-withdraw-{suffix}"
    db.withdraw_requests.insert_one({
        "id": withdraw_id, "label_id": active_id, "status": "approved",
        "amount_idr": 500_000, "legacy_import": False,
    })
    preview_job_id = None
    commit_job_id = None
    verify_job_id = None
    try:
        started = requests.post(
            f"{API}/admin/balance-audit/preview",
            headers=_headers(super_token), json={"label_ids": label_ids}, timeout=20,
        )
        assert started.status_code == 200, started.text
        preview_job_id = started.json()["job_id"]
        preview = _wait_job(super_token, preview_job_id)
        assert preview["status"] == "done", preview.get("error_message")
        assert preview["summary"]["total_labels"] == 3
        assert preview["summary"]["drift_labels"] == 2
        assert preview["summary"]["negative_balance_labels"] == 1
        assert preview["summary"]["stale_cutoff_lines"] == 2
        assert preview["summary"]["blocked_active_withdraw"] == 1

        rows_response = requests.get(
            f"{API}/admin/balance-audit/jobs/{preview_job_id}/rows",
            headers=_headers(super_token), params={"limit": 100}, timeout=20,
        )
        assert rows_response.status_code == 200
        rows = {row["label_id"]: row for row in rows_response.json()["items"]}
        poetra = rows[poetra_id]
        assert poetra["last_withdrawn_period"] == "2026-06"
        assert poetra["latest_report_period"] == "2026-06"
        assert poetra["eligible_period_from"] is None
        assert poetra["expected_pending_idr"] == 0
        assert poetra["expected_available_idr"] == 0
        assert poetra["current_pending_idr"] == -9_168_938
        assert poetra["current_available_idr"] == 9_167_085
        assert poetra["audit_status"] == "drift"
        assert rows[active_id]["audit_status"] == "blocked_active_withdraw"
        assert rows[active_id]["expected_available_idr"] == 0

        committed = requests.post(
            f"{API}/admin/balance-audit/commit",
            headers=_headers(super_token), json={"preview_job_id": preview_job_id}, timeout=20,
        )
        assert committed.status_code == 200, committed.text
        commit_job_id = committed.json()["job_id"]
        commit = _wait_job(super_token, commit_job_id)
        assert commit["status"] == "done", commit.get("error_message")
        assert commit["result"]["labels_reconciled"] == 2
        assert commit["result"]["stale_lines_settled"] == 2

        poetra_label = db.labels.find_one({"id": poetra_id})
        assert poetra_label["balance_pending_idr"] == 0
        assert poetra_label["balance_available_idr"] == 0
        assert poetra_label["balance_withdraw_requested_idr"] == 0
        assert poetra_label["balance_source"] == "royalty_lines_fifo"
        assert db.royalty_lines.count_documents({
            "label_id": poetra_id, "status": "withdrawn", "settled_by_balance_reconciliation": True,
        }) == 2
        future = db.labels.find_one({"id": future_id})
        assert future["balance_pending_idr"] == 100_000
        assert future["balance_available_idr"] == 200_000
        active = db.labels.find_one({"id": active_id})
        assert active["balance_available_idr"] == 0
        assert active["balance_withdraw_requested_idr"] == 500_000

        repeated = requests.post(
            f"{API}/admin/balance-audit/commit",
            headers=_headers(super_token), json={"preview_job_id": preview_job_id}, timeout=20,
        )
        assert repeated.status_code == 200
        assert repeated.json()["job_id"] == commit_job_id

        verified = requests.post(
            f"{API}/admin/balance-audit/preview",
            headers=_headers(super_token), json={"label_ids": label_ids}, timeout=20,
        )
        verify_job_id = verified.json()["job_id"]
        verify = _wait_job(super_token, verify_job_id)
        assert verify["summary"]["drift_labels"] == 0
        assert verify["summary"]["negative_balance_labels"] == 0
        assert verify["summary"]["stale_cutoff_lines"] == 0
    finally:
        job_ids = [item for item in (preview_job_id, commit_job_id, verify_job_id) if item]
        db.balance_audit_rows.delete_many({"job_id": {"$in": job_ids}})
        db.migrate_jobs.delete_many({"id": {"$in": job_ids}})
        db.balance_transactions.delete_many({"reference_id": commit_job_id})
        db.withdraw_requests.delete_one({"id": withdraw_id})
        db.royalty_lines.delete_many({"label_id": {"$in": label_ids}})
        db.labels.delete_many({"id": {"$in": label_ids}})


def test_mark_dana_never_recredits_period_at_or_before_withdraw_cutoff(super_token):
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    label_id = f"ph38-mark-{suffix}"
    import_id = f"ph38-mark-import-{suffix}"
    db.labels.insert_one({
        "id": label_id, "label_name": f"PH38 Mark {suffix}",
        "last_withdrawn_period": "2026-06", "balance_pending_idr": 0,
        "balance_available_idr": 0, "balance_withdraw_requested_idr": 0,
    })
    db.royalty_imports.insert_one({
        "id": import_id, "status": "published", "period": "2026-05",
        "period_start": "2026-05", "period_end": "2026-05", "is_multi_period": False,
        "dana_received_at": None, "uploaded_by": "phase38-test",
    })
    db.royalty_lines.insert_one({
        "id": f"ph38-mark-line-{suffix}", "import_id": import_id, "label_id": label_id,
        "period": "2026-05", "status": "pending", "label_idr": 700_000,
        "legacy_settled": False, "match_status": "matched",
    })
    try:
        response = requests.post(
            f"{API}/royalty/admin/imports/{import_id}/mark-dana-received",
            headers=_headers(super_token), timeout=20,
        )
        assert response.status_code == 200, response.text
        deadline = time.time() + 30
        while time.time() < deadline:
            current = db.royalty_imports.find_one({"id": import_id})
            if current.get("status") in ("dana_received", "receive_error"):
                break
            time.sleep(0.2)
        assert current["status"] == "dana_received", current.get("error_message")
        label = db.labels.find_one({"id": label_id})
        assert label["balance_pending_idr"] == 0
        assert label["balance_available_idr"] == 0
        line = db.royalty_lines.find_one({"import_id": import_id})
        assert line["status"] == "withdrawn"
        assert line["settled_by_period_cutoff"] is True
        assert db.balance_transactions.count_documents({"reference_id": import_id}) == 0
    finally:
        db.royalty_lines.delete_many({"import_id": import_id})
        db.royalty_imports.delete_one({"id": import_id})
        db.balance_transactions.delete_many({"reference_id": import_id})
        db.labels.delete_one({"id": label_id})


def test_rate_recalculation_ignores_lines_at_or_before_cutoff(super_token):
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    label_id = f"ph38-recalc-{suffix}"
    label_name = f"PH38 Recalc {suffix}"
    db.labels.insert_one({
        "id": label_id, "label_name": label_name, "last_withdrawn_period": "2026-06",
        "royalty_percentage_default": 60, "balance_pending_idr": 60_000,
        "balance_available_idr": 0, "balance_withdraw_requested_idr": 0,
    })
    db.royalty_lines.insert_many([
        {
            "id": f"ph38-recalc-old-{suffix}", "label_id": label_id, "period": "2026-06",
            "status": "pending", "legacy_settled": False, "revenue_eur": 10,
            "exchange_rate": 10_000, "label_idr": 60_000, "distributor_idr": 40_000,
            "label_percentage_applied": 60,
        },
        {
            "id": f"ph38-recalc-new-{suffix}", "label_id": label_id, "period": "2026-07",
            "status": "pending", "legacy_settled": False, "revenue_eur": 10,
            "exchange_rate": 10_000, "label_idr": 60_000, "distributor_idr": 40_000,
            "label_percentage_applied": 60,
        },
    ])
    preview_batch_id = None
    job_id = None
    try:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["Nama Label", "Rate"])
        writer.writerow([label_name, 70])
        preview = requests.post(
            f"{API}/admin/labels/rate-import/preview",
            headers=_headers(super_token),
            files={"file": ("phase38.csv", buffer.getvalue().encode())}, timeout=30,
        )
        assert preview.status_code == 200, preview.text
        preview_batch_id = preview.json()["batch_id"]
        committed = requests.post(
            f"{API}/admin/labels/rate-import/commit",
            headers=_headers(super_token), json={"batch_id": preview_batch_id}, timeout=30,
        )
        assert committed.status_code == 200, committed.text
        job_id = committed.json()["job_id"]
        job = _wait_job(super_token, job_id, path="labels/rate-import")
        assert job["status"] == "done", job.get("error_message")
        old_line = db.royalty_lines.find_one({"id": f"ph38-recalc-old-{suffix}"})
        new_line = db.royalty_lines.find_one({"id": f"ph38-recalc-new-{suffix}"})
        assert old_line["label_percentage_applied"] == 60
        assert old_line["label_idr"] == 60_000
        assert new_line["label_percentage_applied"] == 70
        assert new_line["label_idr"] == 70_000
        assert db.labels.find_one({"id": label_id})["balance_pending_idr"] == 70_000
    finally:
        db.label_rate_imports.delete_many({"id": preview_batch_id})
        db.migrate_jobs.delete_many({"id": job_id})
        db.balance_transactions.delete_many({"reference_id": job_id})
        db.royalty_percentage_history.delete_many({"label_id": label_id})
        db.royalty_lines.delete_many({"label_id": label_id})
        db.labels.delete_one({"id": label_id})