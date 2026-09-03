"""Iteration 54 — scoped phase64 24migo balance-audit verification."""
import os
import time

import pymongo
import pytest
import requests

from tests.support_config import SUPERADMIN
from royalty_utils import calculate_line


BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
PHASE64_LABEL_ID = "phase64-24migo"
PHASE64_WEB_WITHDRAW_ID = "phase64-web-paid"


def _db():
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


def _login():
    response = requests.post(f"{API}/auth/login", json=SUPERADMIN, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _wait_job(token, job_id, timeout=120):
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
        time.sleep(0.3)
    raise AssertionError(f"balance audit timeout: {job_id}")


@pytest.fixture(scope="module")
def super_token():
    return _login()


@pytest.fixture(scope="module", autouse=True)
def phase64_fixture():
    db = _db()
    now = "2026-09-03T12:00:00+00:00"
    june_import = "phase64-june"
    july_import = "phase64-july"
    db.labels.delete_many({"id": PHASE64_LABEL_ID})
    db.withdraw_requests.delete_many({"id": {"$regex": "^phase64-"}})
    db.royalty_lines.delete_many({"id": {"$regex": "^phase64-"}})
    db.royalty_imports.delete_many({"id": {"$regex": "^phase64-"}})
    db.labels.insert_one({
        "id": PHASE64_LABEL_ID, "label_name": "24migo",
        "royalty_percentage_default": 35, "last_withdrawn_period": "2026-05",
        "balance_pending_idr": 0, "balance_available_idr": 3_311_210,
        "balance_withdraw_requested_idr": 0, "account_status": "active",
        "created_at": now, "updated_at": now,
    })
    db.withdraw_requests.insert_one({
        "id": PHASE64_WEB_WITHDRAW_ID, "label_id": PHASE64_LABEL_ID,
        "status": "paid", "legacy_import": False, "period_from": "2026-01",
        "period_to": "2026-05", "amount_idr": 1,
        "request_date": "2026-06-01T00:00:00+00:00",
        "paid_date": "2026-06-03T00:00:00+00:00", "created_at": now,
    })
    db.royalty_imports.insert_many([
        {"id": june_import, "filename": "JUNI 2026.csv", "period": "2026-06",
         "status": "dana_received", "exchange_rate_eur_idr": 19_000},
        {"id": july_import, "filename": "JULI 2026.csv", "period": "2026-07",
         "status": "dana_received", "exchange_rate_eur_idr": 18_500},
    ])
    june_values = [
        126.2777370736842105263157895,
        *([0.000072] * 14),
        325.7657857904647894736842105,
    ]
    july_values = [*([0.000078] * 110), 326.111420]
    lines = []
    for index, revenue in enumerate(june_values):
        current = calculate_line(revenue, 0, 50, 19_000)
        settled = index > 0
        lines.append({
            "id": f"phase64-june-line-{index}", "import_id": june_import,
            "label_id": PHASE64_LABEL_ID, "period": "2026-06",
            "status": "withdrawn" if settled else "available",
            "legacy_settled": settled,
            "legacy_settled_period_end": "2026-06" if settled else None,
            "revenue_eur": revenue, "exchange_rate": 19_000,
            "label_percentage_applied": 50, "label_eur": current["label_eur"],
            "label_idr": current["label_idr"], "distributor_idr": current["distributor_idr"],
            "created_at": now,
        })
    for index, revenue in enumerate(july_values):
        current = calculate_line(revenue, 0, 35, 18_500)
        lines.append({
            "id": f"phase64-july-line-{index}", "import_id": july_import,
            "label_id": PHASE64_LABEL_ID, "period": "2026-07",
            "status": "available", "legacy_settled": False,
            "revenue_eur": revenue, "exchange_rate": 18_500,
            "label_percentage_applied": 35, "label_eur": current["label_eur"],
            "label_idr": current["label_idr"], "distributor_idr": current["distributor_idr"],
            "created_at": now,
        })
    db.royalty_lines.insert_many(lines)
    assert sum(
        row["label_idr"] for row in lines if row["status"] == "available"
    ) == 3_311_210
    assert sum(
        calculate_line(row["revenue_eur"], 0, 35, row["exchange_rate"])["label_idr"]
        for row in lines
    ) == 5_117_660
    yield
    job_ids = [row["id"] for row in db.migrate_jobs.find(
        {"$or": [
            {"scope_label_ids": {"$in": [PHASE64_LABEL_ID]}},
            {"label_id": PHASE64_LABEL_ID},
        ]}, {"_id": 0, "id": 1},
    )]
    db.balance_audit_rows.delete_many({"job_id": {"$in": job_ids}})
    db.balance_transactions.delete_many({"reference_id": {"$in": job_ids}})
    db.migrate_jobs.delete_many({"id": {"$in": job_ids}})
    db.withdraw_requests.delete_many({"id": {"$regex": "^phase64-"}})
    db.royalty_lines.delete_many({"id": {"$regex": "^phase64-"}})
    db.royalty_imports.delete_many({"id": {"$regex": "^phase64-"}})
    db.labels.delete_many({"id": PHASE64_LABEL_ID})


# balance-audit scoped preview baseline expectations for phase64 fixture
def test_phase64_preview_baseline_matches_expected_story_numbers(super_token):
    db = _db()
    label = db.labels.find_one({"id": PHASE64_LABEL_ID})
    assert label

    started = requests.post(
        f"{API}/admin/balance-audit/preview",
        headers=_headers(super_token),
        json={"label_ids": [PHASE64_LABEL_ID]},
        timeout=25,
    )
    assert started.status_code == 200, started.text
    preview_id = started.json()["job_id"]
    preview = _wait_job(super_token, preview_id)
    assert preview["status"] == "done", preview.get("error_message")

    rows_response = requests.get(
        f"{API}/admin/balance-audit/jobs/{preview_id}/rows",
        headers=_headers(super_token),
        params={"limit": 20},
        timeout=20,
    )
    assert rows_response.status_code == 200, rows_response.text
    rows = rows_response.json()["items"]
    row = next(item for item in rows if item["label_id"] == PHASE64_LABEL_ID)

    # Expected fixture baseline per phase64 story
    assert row["effective_withdraw_cutoff"] == "2026-05"
    assert row["eligible_period_from"] == "2026-06"
    assert row["eligible_period_to"] == "2026-07"
    assert row["wrongly_settled_lines"] == 15
    assert row["calculation_mismatch_lines"] == 16
    assert row["expected_available_idr"] == 5_117_660
    assert row["current_available_idr"] == 3_311_210

    db.balance_audit_rows.delete_many({"job_id": preview_id})
    db.migrate_jobs.delete_many({"id": preview_id})


# balance-audit scoped commit should restore/recalculate and keep web paid withdrawal untouched
def test_phase64_scoped_commit_then_repreview_is_clean(super_token):
    db = _db()
    label = db.labels.find_one({"id": PHASE64_LABEL_ID})
    assert label

    web_withdraw_before = db.withdraw_requests.find_one(
        {"id": PHASE64_WEB_WITHDRAW_ID},
        {"_id": 0, "id": 1, "status": 1, "legacy_import": 1, "period_to": 1, "amount_idr": 1},
    )

    line_guard_before = {
        "restored": db.royalty_lines.count_documents({
            "label_id": PHASE64_LABEL_ID,
            "restored_by_balance_reconciliation": True,
        }),
        "reconciled": db.royalty_lines.count_documents({
            "label_id": PHASE64_LABEL_ID,
            "status_reconciled_from_import": True,
        }),
    }

    started = requests.post(
        f"{API}/admin/balance-audit/preview",
        headers=_headers(super_token),
        json={"label_ids": [PHASE64_LABEL_ID]},
        timeout=25,
    )
    assert started.status_code == 200, started.text
    preview_id = started.json()["job_id"]
    preview = _wait_job(super_token, preview_id)
    assert preview["status"] == "done", preview.get("error_message")

    line_guard_after_preview = {
        "restored": db.royalty_lines.count_documents({
            "label_id": PHASE64_LABEL_ID,
            "restored_by_balance_reconciliation": True,
        }),
        "reconciled": db.royalty_lines.count_documents({
            "label_id": PHASE64_LABEL_ID,
            "status_reconciled_from_import": True,
        }),
    }
    assert line_guard_after_preview == line_guard_before

    committed = requests.post(
        f"{API}/admin/balance-audit/commit",
        headers=_headers(super_token),
        json={"preview_job_id": preview_id},
        timeout=25,
    )
    assert committed.status_code == 200, committed.text
    commit_id = committed.json()["job_id"]
    commit = _wait_job(super_token, commit_id, timeout=180)
    assert commit["status"] in ("done", "done_with_errors"), commit.get("error_message")

    updated_label = db.labels.find_one({"id": PHASE64_LABEL_ID}, {"_id": 0, "balance_available_idr": 1})
    assert updated_label["balance_available_idr"] == 5_117_660

    verified = requests.post(
        f"{API}/admin/balance-audit/preview",
        headers=_headers(super_token),
        json={"label_ids": [PHASE64_LABEL_ID]},
        timeout=25,
    )
    assert verified.status_code == 200, verified.text
    verify_id = verified.json()["job_id"]
    verify_job = _wait_job(super_token, verify_id)
    assert verify_job["status"] == "done", verify_job.get("error_message")
    assert verify_job["summary"]["drift_labels"] == 0
    assert verify_job["summary"]["wrongly_settled_lines"] == 0
    assert verify_job["summary"]["calculation_mismatch_lines"] == 0

    web_withdraw_after = db.withdraw_requests.find_one(
        {"id": PHASE64_WEB_WITHDRAW_ID},
        {"_id": 0, "id": 1, "status": 1, "legacy_import": 1, "period_to": 1, "amount_idr": 1},
    )
    assert web_withdraw_after == web_withdraw_before

    db.balance_audit_rows.delete_many({"job_id": {"$in": [preview_id, commit_id, verify_id]}})
    db.migrate_jobs.delete_many({"id": {"$in": [preview_id, commit_id, verify_id]}})
    db.balance_transactions.delete_many({"reference_id": {"$in": [commit_id]}})
