"""Iter50 — royalty import replacement guardrails, permissions, and staging visibility."""
import os
import time
import uuid

import pymongo
import requests

from tests.support_config import FINANCE, SUPERADMIN


BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


def _db():
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


def _token(credentials: dict) -> str:
    response = requests.post(f"{API}/auth/login", json=credentials, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]


def _wait_job(token: str, job_id: str, timeout: int = 90):
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


# module: replacement initiate constraints and isolated staging record
def test_initiate_replacement_rejects_pending_review_import():
    db = _db()
    token = _token(SUPERADMIN)
    headers = {"Authorization": f"Bearer {token}"}
    suffix = uuid.uuid4().hex[:8]
    old_id = f"iter50-old-pending-{suffix}"
    db.royalty_imports.insert_one({
        "id": old_id,
        "filename": "old_pending.csv",
        "status": "pending_review",
        "total_lines": 0,
        "total_revenue_eur": 0.0,
        "total_label_idr": 0,
        "exchange_rate_eur_idr": 17500,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    })
    try:
        response = requests.post(
            f"{API}/royalty/admin/imports/{old_id}/replacement/initiate",
            headers=headers,
            json={
                "filename": "replacement.csv",
                "size_bytes": 128,
                "rate_eur_idr": 17500,
                "note": "guard",
            },
            timeout=20,
        )
        assert response.status_code == 409
    finally:
        db.royalty_imports.delete_many({"id": {"$regex": f"iter50-old-pending-{suffix}"}})


# module: replacement initiate creates staging import and presigned metadata without touching old import
def test_initiate_replacement_creates_staging_import_and_presigned_upload():
    db = _db()
    token = _token(SUPERADMIN)
    headers = {"Authorization": f"Bearer {token}"}
    suffix = uuid.uuid4().hex[:8]
    old_id = f"iter50-old-published-{suffix}"
    replacement_id = None
    db.royalty_imports.insert_one({
        "id": old_id,
        "filename": "old_published.csv",
        "status": "published",
        "total_lines": 2,
        "total_revenue_eur": 10.0,
        "total_label_idr": 100000,
        "period_start": "2026-01",
        "period_end": "2026-01",
        "exchange_rate_eur_idr": 17500,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "published_at": "2026-01-02T00:00:00+00:00",
    })
    try:
        response = requests.post(
            f"{API}/royalty/admin/imports/{old_id}/replacement/initiate",
            headers=headers,
            json={
                "filename": "replacement.csv",
                "size_bytes": 256,
                "rate_eur_idr": 18000,
                "note": "iter50 initiate",
            },
            timeout=20,
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        replacement_id = payload["replacement_import_id"]
        assert isinstance(payload.get("upload_url"), str) and payload["upload_url"].startswith("http")
        assert payload.get("content_type") == "text/csv"
        assert payload.get("expires_in") == 7200

        old_now = db.royalty_imports.find_one({"id": old_id})
        assert old_now["status"] == "published"

        staged = db.royalty_imports.find_one({"id": replacement_id})
        assert staged["status"] == "awaiting_upload"
        assert staged["replacement_stage"] is True
        assert staged["replacement_of_import_id"] == old_id
        assert staged["replacement_target_status"] == "published"
        assert staged["total_lines"] == 0
    finally:
        if replacement_id:
            db.royalty_imports.delete_one({"id": replacement_id})
        db.royalty_imports.delete_one({"id": old_id})


def _seed_preview_pair(db, suffix: str, *, old_status: str = "published"):
    old_id = f"iter50-old-prev-{suffix}"
    new_id = f"iter50-new-prev-{suffix}"
    label_id = f"iter50-label-{suffix}"
    db.labels.insert_one({
        "id": label_id,
        "label_name": f"ITER50 {suffix}",
        "last_withdrawn_period": None,
        "royalty_percentage_default": 100,
        "balance_pending_idr": 0,
        "balance_available_idr": 0,
        "balance_withdraw_requested_idr": 0,
    })
    db.royalty_imports.insert_many([
        {
            "id": old_id,
            "filename": "old.csv",
            "status": old_status,
            "total_lines": 1,
            "total_revenue_eur": 10.0,
            "total_label_idr": 100000,
            "period_start": "2026-01",
            "period_end": "2026-01",
            "exchange_rate_eur_idr": 10000,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "published_at": "2026-01-02T00:00:00+00:00",
        },
        {
            "id": new_id,
            "filename": "new.csv",
            "status": "replacement_preview",
            "replacement_stage": True,
            "replacement_of_import_id": old_id,
            "total_lines": 1,
            "total_revenue_eur": 12.0,
            "total_label_idr": 120000,
            "period_start": "2026-01",
            "period_end": "2026-01",
            "exchange_rate_eur_idr": 10000,
            "created_at": "2026-01-03T00:00:00+00:00",
            "updated_at": "2026-01-03T00:00:00+00:00",
        },
    ])
    db.royalty_lines.insert_many([
        {
            "id": f"iter50-old-line-{suffix}",
            "import_id": old_id,
            "label_id": label_id,
            "period": "2026-01",
            "status": "pending" if old_status == "published" else "available",
            "legacy_settled": False,
            "match_status": "matched",
            "revenue_eur": 10,
            "label_idr": 100000,
        },
        {
            "id": f"iter50-new-line-{suffix}",
            "import_id": new_id,
            "label_id": label_id,
            "period": "2026-01",
            "status": "draft",
            "legacy_settled": False,
            "match_status": "replacement_staged",
            "replacement_original_match_status": "matched",
            "replacement_stage": True,
            "revenue_eur": 12,
            "label_idr": 120000,
        },
    ])
    return old_id, new_id, label_id


# module: role guard (finance can preview, cannot commit) + ObjectId-safe responses
def test_finance_can_preview_but_cannot_commit_replacement():
    db = _db()
    finance_token = _token(FINANCE)
    super_token = _token(SUPERADMIN)
    finance_headers = {"Authorization": f"Bearer {finance_token}"}
    super_headers = {"Authorization": f"Bearer {super_token}"}
    suffix = uuid.uuid4().hex[:8]
    old_id, new_id, label_id = _seed_preview_pair(db, suffix, old_status="published")
    preview_id = None
    try:
        started = requests.post(
            f"{API}/royalty/admin/imports/{old_id}/replacement/{new_id}/preview",
            headers=finance_headers,
            timeout=20,
        )
        assert started.status_code == 200, started.text
        preview_id = started.json()["job_id"]
        preview = _wait_job(finance_token, preview_id)
        assert preview["status"] == "done", preview.get("error_message")
        assert "_id" not in preview

        rows = requests.get(
            f"{API}/royalty/admin/imports/replacement/jobs/{preview_id}/rows",
            headers=super_headers,
            timeout=20,
        )
        assert rows.status_code == 200
        items = rows.json()["items"]
        assert len(items) == 1
        assert "_id" not in items[0]

        denied = requests.post(
            f"{API}/royalty/admin/imports/{old_id}/replacement/{new_id}/commit",
            headers=finance_headers,
            json={"preview_job_id": preview_id, "confirmation": "GANTI DATA"},
            timeout=20,
        )
        assert denied.status_code == 403
    finally:
        ids = [preview_id] if preview_id else []
        db.royalty_import_replacement_rows.delete_many({"job_id": {"$in": ids}})
        db.migrate_jobs.delete_many({"id": {"$in": ids}})
        db.royalty_lines.delete_many({"import_id": {"$in": [old_id, new_id]}})
        db.royalty_imports.delete_many({"id": {"$in": [old_id, new_id]}})
        db.labels.delete_one({"id": label_id})


# module: commit requires unchanged signatures from preview
def test_commit_rejects_if_replacement_signature_changed_after_preview():
    db = _db()
    token = _token(SUPERADMIN)
    headers = {"Authorization": f"Bearer {token}"}
    suffix = uuid.uuid4().hex[:8]
    old_id, new_id, label_id = _seed_preview_pair(db, suffix, old_status="published")
    preview_id = None
    try:
        started = requests.post(
            f"{API}/royalty/admin/imports/{old_id}/replacement/{new_id}/preview",
            headers=headers,
            timeout=20,
        )
        assert started.status_code == 200, started.text
        preview_id = started.json()["job_id"]
        preview = _wait_job(token, preview_id)
        assert preview["status"] == "done", preview.get("error_message")

        db.royalty_imports.update_one(
            {"id": new_id},
            {"$set": {"total_label_idr": 121000, "updated_at": "2026-01-04T00:00:00+00:00"}},
        )
        commit = requests.post(
            f"{API}/royalty/admin/imports/{old_id}/replacement/{new_id}/commit",
            headers=headers,
            json={"preview_job_id": preview_id, "confirmation": "GANTI DATA"},
            timeout=20,
        )
        assert commit.status_code == 409
        assert "berubah setelah preview" in commit.text
    finally:
        ids = [preview_id] if preview_id else []
        db.royalty_import_replacement_rows.delete_many({"job_id": {"$in": ids}})
        db.migrate_jobs.delete_many({"id": {"$in": ids}})
        db.royalty_lines.delete_many({"import_id": {"$in": [old_id, new_id]}})
        db.royalty_imports.delete_many({"id": {"$in": [old_id, new_id]}})
        db.labels.delete_one({"id": label_id})


# module: staged replacement lines remain excluded from balances before commit
def test_staged_replacement_lines_excluded_from_admin_label_balance_snapshot():
    db = _db()
    token = _token(SUPERADMIN)
    headers = {"Authorization": f"Bearer {token}"}
    suffix = uuid.uuid4().hex[:8]
    label_id = f"iter50-balance-label-{suffix}"
    old_id = f"iter50-balance-old-{suffix}"
    new_id = f"iter50-balance-new-{suffix}"

    db.labels.insert_one({
        "id": label_id,
        "label_name": f"ITER50 BAL {suffix}",
        "last_withdrawn_period": None,
        "royalty_percentage_default": 100,
        "balance_pending_idr": 0,
        "balance_available_idr": 0,
        "balance_withdraw_requested_idr": 0,
    })
    db.royalty_imports.insert_many([
        {
            "id": old_id,
            "filename": "old.csv",
            "status": "published",
            "total_lines": 1,
            "total_revenue_eur": 0.0,
            "total_label_idr": 0,
            "period_start": "2026-01",
            "period_end": "2026-01",
            "exchange_rate_eur_idr": 10000,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "published_at": "2026-01-02T00:00:00+00:00",
        },
        {
            "id": new_id,
            "filename": "new.csv",
            "status": "replacement_preview",
            "replacement_stage": True,
            "replacement_of_import_id": old_id,
            "total_lines": 1,
            "total_revenue_eur": 99.0,
            "total_label_idr": 990000,
            "period_start": "2026-02",
            "period_end": "2026-02",
            "exchange_rate_eur_idr": 10000,
            "created_at": "2026-01-03T00:00:00+00:00",
            "updated_at": "2026-01-03T00:00:00+00:00",
        },
    ])
    db.royalty_lines.insert_one({
        "id": f"iter50-staged-line-{suffix}",
        "import_id": new_id,
        "label_id": label_id,
        "period": "2026-02",
        "status": "draft",
        "legacy_settled": False,
        "match_status": "replacement_staged",
        "replacement_original_match_status": "matched",
        "replacement_stage": True,
        "revenue_eur": 99,
        "label_idr": 990000,
    })
    try:
        response = requests.get(f"{API}/admin/labels/{label_id}", headers=headers, timeout=20)
        assert response.status_code == 200, response.text
        summary = response.json()["financial_summary"]
        assert summary["available_idr"] == 0
        assert summary["pending_idr"] == 0
        assert summary["total_royalty_idr"] == 0
    finally:
        db.royalty_lines.delete_many({"import_id": {"$in": [old_id, new_id]}})
        db.royalty_imports.delete_many({"id": {"$in": [old_id, new_id]}})
        db.labels.delete_one({"id": label_id})


# module: cancel guard when commit is in progress
def test_cancel_replacement_blocked_while_committing():
    db = _db()
    token = _token(FINANCE)
    headers = {"Authorization": f"Bearer {token}"}
    suffix = uuid.uuid4().hex[:8]
    old_id = f"iter50-old-cancel-{suffix}"
    new_id = f"iter50-new-cancel-{suffix}"
    db.royalty_imports.insert_many([
        {
            "id": old_id,
            "filename": "old.csv",
            "status": "published",
            "total_lines": 0,
            "total_revenue_eur": 0.0,
            "total_label_idr": 0,
            "exchange_rate_eur_idr": 10000,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "published_at": "2026-01-02T00:00:00+00:00",
        },
        {
            "id": new_id,
            "filename": "new.csv",
            "status": "replacement_committing",
            "replacement_stage": True,
            "replacement_of_import_id": old_id,
            "total_lines": 0,
            "total_revenue_eur": 0.0,
            "total_label_idr": 0,
            "exchange_rate_eur_idr": 10000,
            "created_at": "2026-01-03T00:00:00+00:00",
            "updated_at": "2026-01-03T00:00:00+00:00",
        },
    ])
    try:
        denied = requests.delete(
            f"{API}/royalty/admin/imports/{old_id}/replacement/{new_id}",
            headers=headers,
            timeout=20,
        )
        assert denied.status_code == 409
    finally:
        db.royalty_imports.delete_many({"id": {"$in": [old_id, new_id]}})
