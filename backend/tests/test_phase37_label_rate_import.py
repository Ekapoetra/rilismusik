"""Bulk XLSX/CSV label-rate synchronization regression coverage."""
import csv
import io
import os
import time
import uuid

import pymongo
import pytest
import requests
from openpyxl import Workbook

from tests.support_config import RELEASE_ADMIN, SUPERADMIN


BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


def _db():
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


def _login(account):
    response = requests.post(f"{API}/auth/login", json=account, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _csv_bytes(rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["No.", "Nama Label", "Rate"])
    writer.writerows(rows)
    return buffer.getvalue().encode()


def _xlsx_bytes(rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["No.", "Nama Label", "Rate"])
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    workbook.close()
    return buffer.getvalue()


def _preview(token, filename, content):
    response = requests.post(
        f"{API}/admin/labels/rate-import/preview",
        headers=_headers(token),
        files={"file": (filename, content)},
        timeout=60,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _wait_job(token, job_id, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = requests.get(
            f"{API}/admin/labels/rate-import/jobs/{job_id}",
            headers=_headers(token), timeout=20,
        )
        response.raise_for_status()
        job = response.json()
        if job["status"] in ("done", "done_with_errors", "error"):
            return job
        time.sleep(0.2)
    raise AssertionError(f"label rate job {job_id} tidak selesai")


@pytest.fixture(scope="module")
def super_token():
    return _login(SUPERADMIN)


@pytest.fixture(scope="module")
def release_token():
    return _login(RELEASE_ADMIN)


def test_preview_xlsx_csv_match_categories_and_commit_recalculation(super_token, release_token):
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    prefix = f"PH37 {suffix}"
    ids = {name: f"ph37-{name.lower()}-{suffix}" for name in ("Alpha", "Beta1", "Beta2", "Gamma", "Zeta")}
    labels = [
        {"id": ids["Alpha"], "label_name": f"PT. {prefix} Alpha Records", "royalty_percentage_default": 60, "balance_pending_idr": 60_000, "balance_available_idr": 0},
        {"id": ids["Beta1"], "label_name": f"{prefix} Beta-Music", "royalty_percentage_default": 50, "balance_pending_idr": 0, "balance_available_idr": 0},
        {"id": ids["Beta2"], "label_name": f"{prefix} Beta Music", "royalty_percentage_default": 45, "balance_pending_idr": 0, "balance_available_idr": 0},
        {"id": ids["Gamma"], "label_name": f"{prefix} Gamma", "royalty_percentage_default": 50, "balance_pending_idr": 0, "balance_available_idr": 0},
        {"id": ids["Zeta"], "label_name": f"{prefix} Zeta", "royalty_percentage_default": 30, "balance_pending_idr": 0, "balance_available_idr": 0},
    ]
    db.labels.insert_many(labels)
    import_id = f"ph37-import-{suffix}"
    db.royalty_imports.insert_one({"id": import_id, "status": "published", "period": "2026-06"})
    db.royalty_lines.insert_one({
        "id": f"ph37-line-{suffix}", "import_id": import_id, "label_id": ids["Alpha"],
        "status": "pending", "legacy_settled": False, "match_status": "matched",
        "period": "2026-06", "revenue_eur": 10, "exchange_rate": 10_000,
        "revenue_idr": 100_000, "label_idr": 60_000, "distributor_idr": 40_000,
        "label_percentage_applied": 60,
    })
    withdraw_id = f"ph37-withdraw-{suffix}"
    db.withdraw_requests.insert_one({"id": withdraw_id, "label_id": ids["Gamma"], "status": "requested", "legacy_import": False})
    rows = [
        [1, f"{prefix} Alpha Records", 70],
        [2, f"PT {prefix} Alpha Records", 70],
        [3, f"{prefix} Beta Music", 55],
        [4, f"{prefix} Missing", 40],
        [5, f"{prefix} Gamma", 65],
        [6, "", 20],
        [7, f"{prefix} Zeta", 30],
        [8, f"{prefix} Conflict", 40],
        [9, f"{prefix} Conflict", 50],
    ]
    batch_ids = []
    job_id = None
    try:
        unauthorized = requests.post(
            f"{API}/admin/labels/rate-import/preview",
            headers=_headers(release_token), files={"file": ("rates.csv", _csv_bytes(rows))}, timeout=30,
        )
        assert unauthorized.status_code == 403

        xlsx_preview = _preview(super_token, "rates.xlsx", _xlsx_bytes(rows[:1]))
        batch_ids.append(xlsx_preview["batch_id"])
        assert xlsx_preview["summary"]["will_update"] == 1
        assert xlsx_preview["rows"][0]["status"] == "matched"

        preview = _preview(super_token, "rates.csv", _csv_bytes(rows))
        batch_ids.append(preview["batch_id"])
        summary = preview["summary"]
        assert summary["total_rows"] == 9
        assert summary["will_update"] == 1
        assert summary["unchanged"] == 1
        assert summary["unmatched"] == 1
        assert summary["ambiguous"] == 1
        assert summary["invalid"] == 1
        assert summary["duplicate_redundant"] == 1
        assert summary["duplicate_conflict"] == 2
        assert summary["blocked_withdraw"] == 1
        assert db.labels.find_one({"id": ids["Alpha"]})["royalty_percentage_default"] == 60

        committed = requests.post(
            f"{API}/admin/labels/rate-import/commit",
            headers=_headers(super_token),
            json={"batch_id": preview["batch_id"], "reason": "Phase 37 test"},
            timeout=30,
        )
        assert committed.status_code == 200, committed.text
        job_id = committed.json()["job_id"]
        job = _wait_job(super_token, job_id)
        assert job["status"] == "done", job.get("error_message")
        assert job["result"]["labels_updated"] == 1
        assert job["result"]["labels_recalculated"] == 1
        assert job["result"]["lines_recalculated"] == 1

        alpha = db.labels.find_one({"id": ids["Alpha"]})
        line = db.royalty_lines.find_one({"id": f"ph37-line-{suffix}"})
        assert alpha["royalty_percentage_default"] == 70
        assert alpha["balance_pending_idr"] == 70_000
        assert line["label_percentage_applied"] == 70
        assert line["label_idr"] == 70_000
        assert db.royalty_percentage_history.count_documents({"batch_id": preview["batch_id"], "label_id": ids["Alpha"]}) == 1

        repeated = requests.post(
            f"{API}/admin/labels/rate-import/commit",
            headers=_headers(super_token), json={"batch_id": preview["batch_id"]}, timeout=30,
        )
        assert repeated.status_code == 200
        assert repeated.json()["job_id"] == job_id
        assert repeated.json()["already_started"] is True
        assert db.labels.find_one({"id": ids["Alpha"]})["balance_pending_idr"] == 70_000
    finally:
        db.label_rate_imports.delete_many({"id": {"$in": batch_ids}})
        if job_id:
            db.migrate_jobs.delete_one({"id": job_id})
        db.balance_transactions.delete_many({"reference_id": job_id})
        db.royalty_percentage_history.delete_many({"label_id": {"$in": list(ids.values())}})
        db.withdraw_requests.delete_one({"id": withdraw_id})
        db.royalty_lines.delete_many({"import_id": import_id})
        db.royalty_imports.delete_one({"id": import_id})
        db.labels.delete_many({"id": {"$in": list(ids.values())}})


def test_commit_rechecks_active_withdraw_created_after_preview(super_token):
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    label_id = f"ph37-race-{suffix}"
    label_name = f"PH37 Race {suffix}"
    db.labels.insert_one({
        "id": label_id, "label_name": label_name, "royalty_percentage_default": 60,
        "balance_pending_idr": 0, "balance_available_idr": 0,
    })
    preview = _preview(super_token, "race.csv", _csv_bytes([[1, label_name, 75]]))
    withdraw_id = f"ph37-race-withdraw-{suffix}"
    db.withdraw_requests.insert_one({"id": withdraw_id, "label_id": label_id, "status": "approved", "legacy_import": False})
    job_id = None
    try:
        committed = requests.post(
            f"{API}/admin/labels/rate-import/commit",
            headers=_headers(super_token), json={"batch_id": preview["batch_id"]}, timeout=30,
        )
        assert committed.status_code == 200
        job_id = committed.json()["job_id"]
        job = _wait_job(super_token, job_id)
        assert job["status"] == "done"
        assert job["result"]["labels_skipped_active_withdraw"] == 1
        assert db.labels.find_one({"id": label_id})["royalty_percentage_default"] == 60
        assert db.royalty_percentage_history.count_documents({"batch_id": preview["batch_id"]}) == 0
    finally:
        db.label_rate_imports.delete_one({"id": preview["batch_id"]})
        db.migrate_jobs.delete_many({"id": job_id})
        db.withdraw_requests.delete_one({"id": withdraw_id})
        db.labels.delete_one({"id": label_id})