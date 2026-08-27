"""Iteration 32 — label rate import API regression coverage (preview/commit/job)."""
import csv
import io
import os
import time
import uuid
import asyncio

import pymongo
import pytest
import requests
from dotenv import load_dotenv
from openpyxl import Workbook

load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/frontend/.env", override=True)

from routes.label_rate_import import _run_rate_sync_job

from tests.support_config import FINANCE, RELEASE_ADMIN, SUPERADMIN


BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
_SHARED_LOOP = asyncio.new_event_loop()


def _run_async(coro):
    previous_loop = None
    try:
        previous_loop = asyncio.get_event_loop()
    except RuntimeError:
        previous_loop = None
    asyncio.set_event_loop(_SHARED_LOOP)
    try:
        return _SHARED_LOOP.run_until_complete(coro)
    finally:
        if previous_loop and previous_loop is not _SHARED_LOOP:
            asyncio.set_event_loop(previous_loop)
        else:
            asyncio.set_event_loop(None)


def _db():
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


def _login(account):
    response = requests.post(f"{API}/auth/login", json=account, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _csv_bytes(rows, *, delimiter=",", headers=None):
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=delimiter)
    writer.writerow(headers or ["No.", "Nama Label", "Rate"])
    writer.writerows(rows)
    return buffer.getvalue().encode()


def _xlsx_bytes(rows, *, headers=None):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers or ["No.", "Nama Label", "Rate"])
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    workbook.close()
    return buffer.getvalue()


def _preview(token, filename, content, *, expected=200):
    response = requests.post(
        f"{API}/admin/labels/rate-import/preview",
        headers=_headers(token),
        files={"file": (filename, content)},
        timeout=60,
    )
    assert response.status_code == expected, response.text
    return response


def _wait_job(token, job_id, timeout=75):
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = requests.get(
            f"{API}/admin/labels/rate-import/jobs/{job_id}",
            headers=_headers(token),
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") in ("done", "done_with_errors", "error"):
            return payload
        time.sleep(0.3)
    raise AssertionError(f"job {job_id} did not finish in time")


@pytest.fixture(scope="module")
def super_token():
    return _login(SUPERADMIN)


@pytest.fixture(scope="module")
def finance_token():
    return _login(FINANCE)


@pytest.fixture(scope="module")
def release_token():
    return _login(RELEASE_ADMIN)


# Modules/features: role-gated preview endpoint + file parsing support.
def test_role_access_and_semicolon_csv_preview(finance_token, release_token):
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    label_id = f"ITER32-role-{suffix}"
    label_name = f"PT. ITER32 {suffix} Label-One"
    db.labels.insert_one({
        "id": label_id,
        "label_name": label_name,
        "royalty_percentage_default": 61,
        "balance_pending_idr": 0,
        "balance_available_idr": 0,
    })
    batch_ids = []
    try:
        denied = _preview(
            release_token,
            "rates.csv",
            _csv_bytes([[1, label_name, 77]]),
            expected=403,
        )
        assert "Admin Finance" in denied.text or "403" in denied.text

        ok = _preview(
            finance_token,
            "rates-semicolon.csv",
            _csv_bytes([[99, f"iter32 {suffix} label_one", 77]], delimiter=";"),
            expected=200,
        ).json()
        batch_ids.append(ok["batch_id"])
        assert ok["summary"]["will_update"] == 1
        assert ok["rows"][0]["status"] == "matched"
        assert ok["rows"][0]["label_id"] == label_id
        assert db.labels.find_one({"id": label_id})["royalty_percentage_default"] == 61
    finally:
        db.label_rate_imports.delete_many({"id": {"$in": batch_ids}})
        db.labels.delete_one({"id": label_id})


# Modules/features: strict preview validation for format/headers/limits.
def test_preview_rejects_unsupported_missing_headers_empty_and_too_many_rows(super_token):
    unsupported = _preview(super_token, "rates.txt", b"x", expected=400)
    assert "xlsx" in unsupported.text.lower() or "csv" in unsupported.text.lower()

    missing = _preview(
        super_token,
        "missing.csv",
        _csv_bytes([[1, "Label", 60]], headers=["No.", "Label", "Persen"]),
        expected=400,
    )
    assert "nama label" in missing.text.lower()

    empty = _preview(super_token, "empty.csv", b"", expected=400)
    assert "kosong" in empty.text.lower()

    too_many_rows = [[i, f"ITER32 LIMIT {i}", 60] for i in range(1, 5002)]
    too_many = _preview(super_token, "too-many.csv", _csv_bytes(too_many_rows), expected=400)
    assert "5000" in too_many.text


# Modules/features: invalid/duplicate classification in preview summary.
def test_preview_classifies_invalid_and_duplicate_rows(super_token):
    rows = [
        [1, "", 20],
        [2, "ITER32 DUP", ""],
        [3, "ITER32 DUP", "abc"],
        [4, "ITER32 CONFLICT", 10],
        [5, "ITER32 CONFLICT", 15],
    ]
    db = _db()
    batch_id = None
    try:
        response = _preview(super_token, "invalids.xlsx", _xlsx_bytes(rows), expected=200).json()
        batch_id = response["batch_id"]
        assert response["summary"]["invalid"] == 3
        assert response["summary"]["duplicate_conflict"] == 2
        assert response["summary"]["will_update"] == 0
    finally:
        if batch_id:
            db.label_rate_imports.delete_one({"id": batch_id})


# Modules/features: preview must not mutate rates, lines, balances, history, transactions.
def test_preview_has_no_side_effects(super_token):
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    label_id = f"ITER32-noside-{suffix}"
    label_name = f"ITER32 NO SIDE {suffix}"
    import_id = f"ITER32-import-{suffix}"
    line_id = f"ITER32-line-{suffix}"
    db.labels.insert_one({
        "id": label_id,
        "label_name": label_name,
        "royalty_percentage_default": 60,
        "balance_pending_idr": 12000,
        "balance_available_idr": 3000,
    })
    db.royalty_imports.insert_one({"id": import_id, "status": "published", "period": "2026-07"})
    db.royalty_lines.insert_one({
        "id": line_id,
        "import_id": import_id,
        "label_id": label_id,
        "status": "pending",
        "legacy_settled": False,
        "revenue_eur": 10,
        "exchange_rate": 10000,
        "label_idr": 60000,
        "distributor_idr": 40000,
        "label_percentage_applied": 60,
    })
    batch_id = None
    try:
        before = {
            "rate": db.labels.find_one({"id": label_id})["royalty_percentage_default"],
            "pending": db.labels.find_one({"id": label_id})["balance_pending_idr"],
            "available": db.labels.find_one({"id": label_id})["balance_available_idr"],
            "line_label_idr": db.royalty_lines.find_one({"id": line_id})["label_idr"],
            "history": db.royalty_percentage_history.count_documents({"label_id": label_id}),
            "tx": db.balance_transactions.count_documents({"label_id": label_id}),
        }
        preview = _preview(super_token, "preview-only.csv", _csv_bytes([[1, label_name, 70]]), expected=200).json()
        batch_id = preview["batch_id"]
        assert preview["summary"]["will_update"] == 1

        after = {
            "rate": db.labels.find_one({"id": label_id})["royalty_percentage_default"],
            "pending": db.labels.find_one({"id": label_id})["balance_pending_idr"],
            "available": db.labels.find_one({"id": label_id})["balance_available_idr"],
            "line_label_idr": db.royalty_lines.find_one({"id": line_id})["label_idr"],
            "history": db.royalty_percentage_history.count_documents({"label_id": label_id}),
            "tx": db.balance_transactions.count_documents({"label_id": label_id}),
        }
        assert after == before
    finally:
        if batch_id:
            db.label_rate_imports.delete_one({"id": batch_id})
        db.royalty_lines.delete_one({"id": line_id})
        db.royalty_imports.delete_one({"id": import_id})
        db.balance_transactions.delete_many({"label_id": label_id})
        db.royalty_percentage_history.delete_many({"label_id": label_id})
        db.labels.delete_one({"id": label_id})


# Modules/features: owner check + super_admin override + idempotent commit + job payload.
def test_commit_ownership_override_idempotent_and_job_shape(super_token, finance_token):
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    label_id = f"ITER32-owner-{suffix}"
    label_name = f"ITER32 OWNER {suffix}"
    db.labels.insert_one({
        "id": label_id,
        "label_name": label_name,
        "royalty_percentage_default": 55,
        "balance_pending_idr": 0,
        "balance_available_idr": 0,
    })
    super_batch = None
    finance_batch = None
    finance_job = None
    try:
        super_preview = _preview(super_token, "owner-super.csv", _csv_bytes([[1, label_name, 59]]), expected=200).json()
        super_batch = super_preview["batch_id"]
        denied = requests.post(
            f"{API}/admin/labels/rate-import/commit",
            headers=_headers(finance_token),
            json={"batch_id": super_batch},
            timeout=30,
        )
        assert denied.status_code == 403, denied.text

        finance_preview = _preview(finance_token, "owner-finance.csv", _csv_bytes([[1, label_name, 64]]), expected=200).json()
        finance_batch = finance_preview["batch_id"]
        committed = requests.post(
            f"{API}/admin/labels/rate-import/commit",
            headers=_headers(super_token),
            json={"batch_id": finance_batch, "reason": "ITER32 override"},
            timeout=30,
        )
        assert committed.status_code == 200, committed.text
        finance_job = committed.json()["job_id"]

        repeated = requests.post(
            f"{API}/admin/labels/rate-import/commit",
            headers=_headers(super_token),
            json={"batch_id": finance_batch},
            timeout=30,
        )
        assert repeated.status_code == 200
        assert repeated.json()["job_id"] == finance_job
        assert repeated.json()["already_started"] is True

        job = _wait_job(super_token, finance_job)
        assert "_id" not in job
        assert job["status"] in ("done", "done_with_errors")
        assert db.labels.find_one({"id": label_id})["royalty_percentage_default"] == 64
    finally:
        db.label_rate_imports.delete_many({"id": {"$in": [value for value in [super_batch, finance_batch] if value]}})
        if finance_job:
            db.migrate_jobs.delete_one({"id": finance_job})
            db.balance_transactions.delete_many({"reference_id": finance_job})
        db.royalty_percentage_history.delete_many({"label_id": label_id})
        db.labels.delete_one({"id": label_id})


# Modules/features: stale changes after preview must not be overwritten on commit.
def test_commit_skips_stale_rate_change_after_preview(super_token):
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    label_id = f"ITER32-stale-{suffix}"
    label_name = f"ITER32 STALE {suffix}"
    db.labels.insert_one({
        "id": label_id,
        "label_name": label_name,
        "royalty_percentage_default": 40,
        "balance_pending_idr": 0,
        "balance_available_idr": 0,
    })
    batch_id = None
    job_id = None
    try:
        preview = _preview(super_token, "stale.csv", _csv_bytes([[1, label_name, 70]]), expected=200).json()
        batch_id = preview["batch_id"]
        db.labels.update_one({"id": label_id}, {"$set": {"royalty_percentage_default": 45}})

        committed = requests.post(
            f"{API}/admin/labels/rate-import/commit",
            headers=_headers(super_token),
            json={"batch_id": batch_id},
            timeout=30,
        )
        assert committed.status_code == 200, committed.text
        job_id = committed.json()["job_id"]
        job = _wait_job(super_token, job_id)

        assert job["status"] in ("done", "done_with_errors")
        assert int(job["result"].get("labels_skipped_changed_after_preview", 0)) == 1
        assert db.labels.find_one({"id": label_id})["royalty_percentage_default"] == 45

        refreshed = db.label_rate_imports.find_one({"id": batch_id}, {"_id": 0, "rows": 1})
        target = next(row for row in refreshed["rows"] if row.get("label_id") == label_id)
        assert target.get("apply_status") == "stale_conflict"
    finally:
        if batch_id:
            db.label_rate_imports.delete_one({"id": batch_id})
        if job_id:
            db.migrate_jobs.delete_one({"id": job_id})
            db.balance_transactions.delete_many({"reference_id": job_id})
        db.royalty_percentage_history.delete_many({"label_id": label_id})
        db.labels.delete_one({"id": label_id})


# Modules/features: queued label_rate_sync jobs resume and complete after restart/hot-reload.
def test_resume_queued_label_rate_sync_job(super_token):
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    label_id = f"ITER32-resume-{suffix}"
    label_name = f"ITER32 RESUME {suffix}"
    batch_id = f"ITER32-batch-{suffix}"
    job_id = f"ITER32-job-{suffix}"
    db.labels.insert_one({
        "id": label_id,
        "label_name": label_name,
        "royalty_percentage_default": 60,
        "balance_pending_idr": 0,
        "balance_available_idr": 0,
    })
    db.label_rate_imports.insert_one({
        "id": batch_id,
        "filename": "iter32_resume.csv",
        "status": "queued",
        "summary": {"will_update": 1},
        "rows": [{
            "row_number": 2,
            "input_label_name": label_name,
            "normalized_name": f"iter32 resume {suffix}",
            "input_rate": 72.0,
            "label_id": label_id,
            "matched_label_name": label_name,
            "current_rate": 60.0,
            "candidate_labels": [],
            "status": "matched",
            "reason": "resume test",
        }],
        "submitted_by": "iter32-user",
        "created_at": "2026-01-01T00:00:00+00:00",
        "expires_at": "2099-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "job_id": job_id,
    })
    db.migrate_jobs.insert_one({
        "id": job_id,
        "kind": "label_rate_sync",
        "status": "queued",
        "batch_id": batch_id,
        "submitted_by": "iter32-user",
        "submitted_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "progress_labels_done": 0,
        "progress_labels_total": 1,
    })
    try:
        _run_async(_run_rate_sync_job(batch_id=batch_id, job_id=job_id, user_id="iter32-user", reason="ITER32 resume"))
        finished = _wait_job(super_token, job_id, timeout=60)
        assert finished["status"] in ("done", "done_with_errors")
        assert db.labels.find_one({"id": label_id})["royalty_percentage_default"] == 72
    finally:
        db.label_rate_imports.delete_one({"id": batch_id})
        db.migrate_jobs.delete_one({"id": job_id})
        db.balance_transactions.delete_many({"reference_id": job_id})
        db.royalty_percentage_history.delete_many({"label_id": label_id})
        db.labels.delete_one({"id": label_id})


# Modules/features: resume path skips rows already marked done (idempotent, no duplicate effects).
def test_resume_processing_job_skips_already_done_rows(super_token):
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    label_id = f"ITER32-resume-done-{suffix}"
    label_name = f"ITER32 RESUME DONE {suffix}"
    batch_id = f"ITER32-batch-done-{suffix}"
    job_id = f"ITER32-job-done-{suffix}"
    db.labels.insert_one({
        "id": label_id,
        "label_name": label_name,
        "royalty_percentage_default": 70,
        "balance_pending_idr": 0,
        "balance_available_idr": 0,
    })
    db.label_rate_imports.insert_one({
        "id": batch_id,
        "filename": "iter32_resume_done.csv",
        "status": "processing",
        "summary": {"will_update": 1},
        "rows": [{
            "row_number": 2,
            "input_label_name": label_name,
            "normalized_name": f"iter32 resume done {suffix}",
            "input_rate": 70.0,
            "label_id": label_id,
            "matched_label_name": label_name,
            "current_rate": 60.0,
            "candidate_labels": [],
            "status": "matched",
            "apply_status": "done",
            "reason": "already done row",
        }],
        "submitted_by": "iter32-user",
        "created_at": "2026-01-01T00:00:00+00:00",
        "expires_at": "2099-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "job_id": job_id,
    })
    db.migrate_jobs.insert_one({
        "id": job_id,
        "kind": "label_rate_sync",
        "status": "processing",
        "batch_id": batch_id,
        "submitted_by": "iter32-user",
        "submitted_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "progress_labels_done": 0,
        "progress_labels_total": 1,
    })
    before_tx = db.balance_transactions.count_documents({"reference_id": job_id})
    try:
        _run_async(_run_rate_sync_job(batch_id=batch_id, job_id=job_id, user_id="iter32-user", reason="ITER32 resume done"))
        finished = _wait_job(super_token, job_id, timeout=60)
        assert finished["status"] in ("done", "done_with_errors")
        assert int((finished.get("result") or {}).get("labels_updated", 0)) == 0
        assert db.balance_transactions.count_documents({"reference_id": job_id}) == before_tx
        assert db.labels.find_one({"id": label_id})["royalty_percentage_default"] == 70
    finally:
        db.label_rate_imports.delete_one({"id": batch_id})
        db.migrate_jobs.delete_one({"id": job_id})
        db.balance_transactions.delete_many({"reference_id": job_id})
        db.royalty_percentage_history.delete_many({"label_id": label_id})
        db.labels.delete_one({"id": label_id})
