"""Phase 55 — guarded recovery for withdrawn royalty lines beyond paid cutoff."""
import os
import time
import uuid
from datetime import datetime, timezone

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
            f"{API}/admin/balance-audit/jobs/{job_id}",
            headers=_headers(token),
            timeout=20,
        )
        response.raise_for_status()
        job = response.json()
        if job["status"] in ("done", "done_with_errors", "error"):
            return job
        time.sleep(0.2)
    raise AssertionError(f"balance audit timeout: {job_id}")


def test_global_audit_restores_only_guarded_post_cutoff_orphans():
    db = _db()
    token = _login()
    suffix = uuid.uuid4().hex[:8]
    safe_id = f"ph55-safe-{suffix}"
    blocked_id = f"ph55-blocked-{suffix}"
    preview_id = commit_id = verify_id = None
    db.labels.insert_many([
        {
            "id": safe_id,
            "label_name": f"PH55 Safe {suffix}",
            "last_withdrawn_period": "2026-01",
            "royalty_percentage_default": 50,
            "balance_pending_idr": -25_000,
            "balance_available_idr": 50_000,
            "balance_withdraw_requested_idr": 0,
        },
        {
            "id": blocked_id,
            "label_name": f"PH55 Blocked {suffix}",
            "last_withdrawn_period": "2026-01",
            "royalty_percentage_default": 50,
            "balance_pending_idr": 0,
            "balance_available_idr": 0,
            "balance_withdraw_requested_idr": 0,
        },
    ])
    db.withdraw_requests.insert_many([
        {
            "id": f"ph55-paid-safe-{suffix}",
            "label_id": safe_id,
            "status": "paid",
            "period_from": "2025-01",
            "period_to": "2026-01",
            "amount_idr": 100_000,
        },
        {
            "id": f"ph55-paid-blocked-{suffix}",
            "label_id": blocked_id,
            "status": "paid",
            "amount_idr": 100_000,
        },
    ])
    db.royalty_lines.insert_many([
        {
            "id": f"ph55-safe-active-{suffix}",
            "label_id": safe_id,
            "period": "2026-02",
            "status": "available",
            "legacy_settled": False,
            "revenue_eur": 10,
            "exchange_rate": 10_000,
            "label_eur": 5,
            "label_idr": 50_000,
            "distributor_idr": 50_000,
            "label_percentage_applied": 50,
        },
        {
            "id": f"ph55-safe-orphan-{suffix}",
            "label_id": safe_id,
            "period": "2026-06",
            "status": "withdrawn",
            "legacy_settled": True,
            "legacy_settled_period_end": "2026-06",
            "revenue_eur": 20,
            "exchange_rate": 10_000,
            "label_eur": 12,
            "label_idr": 120_000,
            "distributor_idr": 80_000,
            "label_percentage_applied": 60,
        },
        {
            "id": f"ph55-safe-historical-{suffix}",
            "label_id": safe_id,
            "period": "2026-01",
            "status": "withdrawn",
            "legacy_settled": True,
            "label_idr": 100_000,
        },
        {
            "id": f"ph55-safe-legacy-marker-{suffix}",
            "label_id": safe_id,
            "period": "2026-05",
            "status": "available",
            "legacy_settled": True,
            "legacy_settled_period_end": "2026-05",
            "revenue_eur": 30,
            "exchange_rate": 10_000,
            "label_eur": 18,
            "label_idr": 180_000,
            "distributor_idr": 120_000,
            "label_percentage_applied": 60,
        },
        {
            "id": f"ph55-safe-pending-marker-{suffix}",
            "label_id": safe_id,
            "period": "2026-07",
            "status": "pending",
            "legacy_settled": True,
            "legacy_settled_period_end": "2026-07",
            "revenue_eur": 4,
            "exchange_rate": 10_000,
            "label_eur": 2.4,
            "label_idr": 24_000,
            "distributor_idr": 16_000,
            "label_percentage_applied": 60,
        },
        {
            "id": f"ph55-blocked-orphan-{suffix}",
            "label_id": blocked_id,
            "period": "2026-06",
            "status": "withdrawn",
            "legacy_settled": True,
            "revenue_eur": 20,
            "exchange_rate": 10_000,
            "label_idr": 120_000,
            "label_percentage_applied": 60,
        },
    ])
    try:
        started = requests.post(
            f"{API}/admin/balance-audit/preview",
            headers=_headers(token),
            json={"label_ids": [safe_id, blocked_id]},
            timeout=20,
        )
        assert started.status_code == 200, started.text
        preview_id = started.json()["job_id"]
        preview = _wait_job(token, preview_id)
        assert preview["status"] == "done", preview.get("error_message")
        assert preview["summary"]["orphan_withdrawn_lines"] == 2
        assert preview["summary"]["orphan_legacy_settled_lines"] == 2
        assert preview["summary"]["wrongly_settled_lines"] == 4
        assert preview["summary"]["blocked_withdraw_history"] == 1

        rows_response = requests.get(
            f"{API}/admin/balance-audit/jobs/{preview_id}/rows",
            headers=_headers(token),
            params={"limit": 100},
            timeout=20,
        )
        rows = {row["label_id"]: row for row in rows_response.json()["items"]}
        assert rows[safe_id]["effective_withdraw_cutoff"] == "2026-01"
        assert rows[safe_id]["orphan_withdrawn_lines"] == 1
        assert rows[safe_id]["orphan_withdrawn_idr"] == 120_000
        assert rows[safe_id]["orphan_legacy_settled_lines"] == 2
        assert rows[safe_id]["orphan_legacy_settled_idr"] == 204_000
        assert rows[safe_id]["wrongly_settled_lines"] == 3
        assert rows[safe_id]["expected_pending_idr"] == 24_000
        assert rows[safe_id]["expected_available_idr"] == 350_000
        assert rows[safe_id]["audit_status"] == "drift"
        assert rows[blocked_id]["audit_status"] == "blocked_withdraw_history"

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
        assert commit["result"]["labels_skipped_withdraw_history"] == 0

        restored = db.royalty_lines.find_one({"id": f"ph55-safe-orphan-{suffix}"})
        assert restored["status"] == "available"
        assert restored["legacy_settled"] is False
        assert restored["label_percentage_applied"] == 50
        assert restored["label_idr"] == 100_000
        assert restored["restored_by_balance_reconciliation"] is True
        restored_marker = db.royalty_lines.find_one({"id": f"ph55-safe-legacy-marker-{suffix}"})
        assert restored_marker["status"] == "available"
        assert restored_marker["legacy_settled"] is False
        assert restored_marker["label_percentage_applied"] == 50
        assert restored_marker["label_idr"] == 150_000
        restored_pending = db.royalty_lines.find_one({"id": f"ph55-safe-pending-marker-{suffix}"})
        assert restored_pending["status"] == "pending"
        assert restored_pending["legacy_settled"] is False
        assert restored_pending["label_percentage_applied"] == 50
        assert restored_pending["label_idr"] == 20_000
        assert db.royalty_lines.find_one({"id": f"ph55-safe-historical-{suffix}"})["status"] == "withdrawn"
        assert db.royalty_lines.find_one({"id": f"ph55-blocked-orphan-{suffix}"})["status"] == "withdrawn"

        safe = db.labels.find_one({"id": safe_id})
        assert safe["balance_pending_idr"] == 20_000
        assert safe["balance_available_idr"] == 300_000

        verified = requests.post(
            f"{API}/admin/balance-audit/preview",
            headers=_headers(token),
            json={"label_ids": [safe_id]},
            timeout=20,
        )
        verify_id = verified.json()["job_id"]
        verify = _wait_job(token, verify_id)
        assert verify["summary"]["orphan_withdrawn_lines"] == 0
        assert verify["summary"]["orphan_legacy_settled_lines"] == 0
        assert verify["summary"]["wrongly_settled_lines"] == 0
        assert verify["summary"]["drift_labels"] == 0
    finally:
        job_ids = [item for item in (preview_id, commit_id, verify_id) if item]
        db.balance_audit_rows.delete_many({"job_id": {"$in": job_ids}})
        db.migrate_jobs.delete_many({"id": {"$in": job_ids}})
        db.balance_transactions.delete_many({"reference_id": {"$in": job_ids}})
        db.withdraw_requests.delete_many({"label_id": {"$in": [safe_id, blocked_id]}})
        db.royalty_lines.delete_many({"label_id": {"$in": [safe_id, blocked_id]}})
        db.labels.delete_many({"id": {"$in": [safe_id, blocked_id]}})


def test_stale_recalculation_is_closed_but_recent_job_still_blocks_commit():
    db = _db()
    token = _login()
    suffix = uuid.uuid4().hex[:8]
    label_id = f"ph55-stale-{suffix}"
    stale_id = f"ph55-stale-job-{suffix}"
    recent_id = f"ph55-recent-job-{suffix}"
    preview_id = commit_id = None
    db.labels.insert_one({
        "id": label_id,
        "label_name": f"PH55 Stale Guard {suffix}",
        "balance_pending_idr": -1,
        "balance_available_idr": 0,
        "balance_withdraw_requested_idr": 0,
    })
    db.migrate_jobs.insert_one({
        "id": stale_id,
        "kind": "recalculate_all_unwithdrawn",
        "status": "processing",
        "updated_at": "2026-01-01T00:00:00+00:00",
    })
    try:
        started = requests.post(
            f"{API}/admin/balance-audit/preview",
            headers=_headers(token),
            json={"label_ids": [label_id]},
            timeout=20,
        )
        preview_id = started.json()["job_id"]
        assert _wait_job(token, preview_id)["status"] == "done"

        committed = requests.post(
            f"{API}/admin/balance-audit/commit",
            headers=_headers(token),
            json={"preview_job_id": preview_id},
            timeout=20,
        )
        assert committed.status_code == 200, committed.text
        commit_id = committed.json()["job_id"]
        assert _wait_job(token, commit_id)["status"] == "done"
        stale = db.migrate_jobs.find_one({"id": stale_id})
        assert stale["status"] == "error"
        assert stale["stale_job_closed"] is True

        db.migrate_jobs.insert_one({
            "id": recent_id,
            "kind": "recalculate_all_unwithdrawn",
            "status": "processing",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        db.migrate_jobs.update_one(
            {"id": preview_id},
            {"$unset": {"commit_job_id": ""}},
        )
        blocked = requests.post(
            f"{API}/admin/balance-audit/commit",
            headers=_headers(token),
            json={"preview_job_id": preview_id},
            timeout=20,
        )
        assert blocked.status_code == 409, blocked.text
        assert "hitung ulang persentase" in blocked.json()["detail"]
        assert db.migrate_jobs.find_one({"id": recent_id})["status"] == "processing"
    finally:
        job_ids = [item for item in (preview_id, commit_id, stale_id, recent_id) if item]
        db.balance_audit_rows.delete_many({"job_id": {"$in": job_ids}})
        db.migrate_jobs.delete_many({"id": {"$in": job_ids}})
        db.balance_transactions.delete_many({"reference_id": {"$in": job_ids}})
        db.labels.delete_one({"id": label_id})