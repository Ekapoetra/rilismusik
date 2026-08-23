"""Phase 30 regression: repair-source initiate/finalize guard rails + R2 upload contract."""
import asyncio
import csv
import io
import os
import time
import uuid
from pathlib import Path

import pymongo
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

import storage_service
from tests.support_config import FINANCE, SUPERADMIN, SUPPORT

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


def _db():
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


def _login(user):
    response = requests.post(
        f"{API}/auth/login",
        json={"email": user["email"], "password": user["password"]},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _wait_job(token, job_id, timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = requests.get(f"{API}/admin/migrate/jobs/{job_id}", headers=_headers(token), timeout=20)
        response.raise_for_status()
        job = response.json()
        if job["status"] in ("done", "error"):
            return job
        time.sleep(0.5)
    raise AssertionError(f"job {job_id} tidak selesai dalam {timeout}s")


def _repair_csv_bytes():
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(["Bulan laporan", "Bulan Penjualan", "Nama Label", "Pendapatan Bersih"])
    writer.writerow(["01/04/2025", "01/01/2025", "ITER30", "1,00"])
    writer.writerow(["01/05/2025", "01/02/2025", "ITER30", "2,00"])
    return buffer.getvalue().encode("utf-8")


@pytest.fixture(scope="module")
def super_token():
    return _login(SUPERADMIN)


@pytest.fixture(scope="module")
def finance_token():
    return _login(FINANCE)


@pytest.fixture(scope="module")
def support_token():
    return _login(SUPPORT)


def _seed_import_with_lines(db, *, import_id: str):
    db.royalty_imports.insert_one({
        "id": import_id,
        "filename": f"missing-{import_id}.csv",
        "status": "dana_received",
        "period": "multi",
        "period_start": "2025-01",
        "period_end": "2025-02",
        "period_breakdown": {"2025-01": 1, "2025-02": 1},
        "uploaded_by": "iter30-test",
        "period_repair_status": "error",
        "period_repair_error": "CSV asli tidak tersedia",
    })
    db.royalty_lines.insert_many([
        {
            "id": f"{import_id}-1", "import_id": import_id, "period": "2025-01",
            "row_period": "2025-01", "status": "available", "match_status": "matched",
            "label_idr": 10000, "revenue_eur": 1,
        },
        {
            "id": f"{import_id}-2", "import_id": import_id, "period": "2025-02",
            "row_period": "2025-02", "status": "available", "match_status": "matched",
            "label_idr": 20000, "revenue_eur": 2,
        },
    ])


def _cleanup_import(db, import_id: str):
    upload_docs = list(db.royalty_import_repair_uploads.find({"import_id": import_id}, {"_id": 0, "object_key": 1}))
    for upload in upload_docs:
        try:
            asyncio.run(storage_service.delete_object(key=upload["object_key"]))
        except RuntimeError:
            pass
    db.royalty_import_repair_uploads.delete_many({"import_id": import_id})
    db.migrate_jobs.delete_many({"import_id": import_id})
    db.royalty_lines.delete_many({"import_id": import_id})
    db.royalty_imports.delete_one({"id": import_id})
    (Path("/app/backend/uploads/csv") / f"{import_id}.csv").unlink(missing_ok=True)
    (Path("/app/backend/uploads/csv") / f"{import_id}.csv.gz").unlink(missing_ok=True)


# Module: initiate/finalize guard rails and repair flow integrity
def test_repair_source_initiate_requires_admin_finance_or_super_admin(support_token):
    response = requests.post(
        f"{API}/royalty/admin/imports/nonexistent-id/repair-source/initiate",
        headers=_headers(support_token),
        json={"filename": "APRIL 2025.csv", "size_bytes": 100},
        timeout=20,
    )
    assert response.status_code == 403


def test_repair_source_initiate_rejects_missing_import(finance_token):
    response = requests.post(
        f"{API}/royalty/admin/imports/nonexistent-id/repair-source/initiate",
        headers=_headers(finance_token),
        json={"filename": "APRIL 2025.csv", "size_bytes": 100},
        timeout=20,
    )
    assert response.status_code == 404


def test_repair_source_initiate_rejects_wrong_extension(super_token):
    db = _db()
    import_id = f"iter30-ext-{uuid.uuid4().hex[:8]}"
    _seed_import_with_lines(db, import_id=import_id)
    try:
        response = requests.post(
            f"{API}/royalty/admin/imports/{import_id}/repair-source/initiate",
            headers=_headers(super_token),
            json={"filename": "APRIL-2025.txt", "size_bytes": 10},
            timeout=20,
        )
        assert response.status_code == 400
    finally:
        _cleanup_import(db, import_id)


def test_repair_source_initiate_rejects_zero_size(super_token):
    db = _db()
    import_id = f"iter30-size-{uuid.uuid4().hex[:8]}"
    _seed_import_with_lines(db, import_id=import_id)
    try:
        response = requests.post(
            f"{API}/royalty/admin/imports/{import_id}/repair-source/initiate",
            headers=_headers(super_token),
            json={"filename": "APRIL-2025.csv", "size_bytes": 0},
            timeout=20,
        )
        assert response.status_code == 422
    finally:
        _cleanup_import(db, import_id)


def test_direct_r2_put_rejects_wrong_content_type_and_finalize_rejects_size_mismatch(super_token):
    db = _db()
    import_id = f"iter30-ctype-{uuid.uuid4().hex[:8]}"
    _seed_import_with_lines(db, import_id=import_id)
    csv_bytes = _repair_csv_bytes()
    upload_id = None
    try:
        initiated = requests.post(
            f"{API}/royalty/admin/imports/{import_id}/repair-source/initiate",
            headers=_headers(super_token),
            json={"filename": "APRIL 2025.csv", "size_bytes": len(csv_bytes) + 1},
            timeout=20,
        )
        assert initiated.status_code == 200, initiated.text
        body = initiated.json()
        upload_id = body["upload_id"]
        assert body["content_type"] == "text/csv"

        wrong_put = requests.put(
            body["upload_url"],
            headers={"Content-Type": "application/octet-stream"},
            data=csv_bytes,
            timeout=30,
        )
        assert wrong_put.status_code >= 400

        finalize_before_valid_upload = requests.post(
            f"{API}/royalty/admin/imports/{import_id}/repair-source/finalize",
            headers=_headers(super_token),
            json={"upload_id": upload_id},
            timeout=20,
        )
        assert finalize_before_valid_upload.status_code == 400

        ok_put = requests.put(
            body["upload_url"],
            headers={"Content-Type": body["content_type"]},
            data=csv_bytes,
            timeout=30,
        )
        assert ok_put.status_code in (200, 201, 204), ok_put.text

        wrong_size_finalize = requests.post(
            f"{API}/royalty/admin/imports/{import_id}/repair-source/finalize",
            headers=_headers(super_token),
            json={"upload_id": upload_id},
            timeout=20,
        )
        assert wrong_size_finalize.status_code == 400
        assert "Ukuran file R2 tidak cocok" in wrong_size_finalize.text
    finally:
        _cleanup_import(db, import_id)


def test_finalize_rejects_cross_import_upload_id(super_token):
    db = _db()
    import_a = f"iter30-cross-a-{uuid.uuid4().hex[:8]}"
    import_b = f"iter30-cross-b-{uuid.uuid4().hex[:8]}"
    _seed_import_with_lines(db, import_id=import_a)
    _seed_import_with_lines(db, import_id=import_b)
    csv_bytes = _repair_csv_bytes()
    try:
        initiated = requests.post(
            f"{API}/royalty/admin/imports/{import_a}/repair-source/initiate",
            headers=_headers(super_token),
            json={"filename": "APRIL 2025.csv", "size_bytes": len(csv_bytes)},
            timeout=20,
        )
        assert initiated.status_code == 200, initiated.text
        body = initiated.json()

        uploaded = requests.put(
            body["upload_url"],
            headers={"Content-Type": body["content_type"]},
            data=csv_bytes,
            timeout=30,
        )
        assert uploaded.status_code in (200, 201, 204), uploaded.text

        cross_finalize = requests.post(
            f"{API}/royalty/admin/imports/{import_b}/repair-source/finalize",
            headers=_headers(super_token),
            json={"upload_id": body["upload_id"]},
            timeout=20,
        )
        assert cross_finalize.status_code == 404
    finally:
        _cleanup_import(db, import_a)
        _cleanup_import(db, import_b)


def test_finalize_marks_upload_finalized_queues_job_and_preserves_line_amounts_status(super_token):
    db = _db()
    import_id = f"iter30-finalize-{uuid.uuid4().hex[:8]}"
    _seed_import_with_lines(db, import_id=import_id)
    csv_bytes = _repair_csv_bytes()
    job_id = None
    upload_id = None
    try:
        before_lines = list(db.royalty_lines.find({"import_id": import_id}, {"_id": 0, "id": 1, "status": 1, "label_idr": 1, "revenue_eur": 1}).sort("id", 1))
        assert len(before_lines) == 2

        initiated = requests.post(
            f"{API}/royalty/admin/imports/{import_id}/repair-source/initiate",
            headers=_headers(super_token),
            json={"filename": "APRIL 2025.csv", "size_bytes": len(csv_bytes)},
            timeout=20,
        )
        assert initiated.status_code == 200, initiated.text
        body = initiated.json()
        upload_id = body["upload_id"]

        uploaded = requests.put(
            body["upload_url"],
            headers={"Content-Type": body["content_type"]},
            data=csv_bytes,
            timeout=30,
        )
        assert uploaded.status_code in (200, 201, 204), uploaded.text

        finalized = requests.post(
            f"{API}/royalty/admin/imports/{import_id}/repair-source/finalize",
            headers=_headers(super_token),
            json={"upload_id": upload_id},
            timeout=20,
        )
        assert finalized.status_code == 200, finalized.text
        response_data = finalized.json()
        assert response_data["source_attached"] is True
        job_id = response_data["job_id"]

        job = _wait_job(super_token, job_id, timeout=90)
        assert job["status"] == "done", job.get("error_message")

        upload_doc = db.royalty_import_repair_uploads.find_one({"id": upload_id}, {"_id": 0, "status": 1})
        assert upload_doc["status"] == "finalized"

        imp = db.royalty_imports.find_one({"id": import_id}, {"_id": 0, "repair_source": 1, "period_repair_status": 1, "status": 1})
        assert imp["status"] == "dana_received"
        assert imp["period_repair_status"] == "done"
        assert imp["repair_source"]["filename"] == "APRIL 2025.csv"

        after_lines = list(db.royalty_lines.find({"import_id": import_id}, {"_id": 0, "id": 1, "status": 1, "label_idr": 1, "revenue_eur": 1}).sort("id", 1))
        assert [line["status"] for line in after_lines] == [line["status"] for line in before_lines]
        assert [line["label_idr"] for line in after_lines] == [line["label_idr"] for line in before_lines]
        assert [line["revenue_eur"] for line in after_lines] == [line["revenue_eur"] for line in before_lines]

        reused_finalize = requests.post(
            f"{API}/royalty/admin/imports/{import_id}/repair-source/finalize",
            headers=_headers(super_token),
            json={"upload_id": upload_id},
            timeout=20,
        )
        assert reused_finalize.status_code == 404
    finally:
        _cleanup_import(db, import_id)