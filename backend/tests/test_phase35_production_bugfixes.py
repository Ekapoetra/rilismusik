"""Regression coverage for three production bugs reported after Phase 34."""
import csv
import io
import os
import time
import uuid
from pathlib import Path

import pymongo
import pytest
import requests

from royalty_utils import detect_columns, parse_period_from_value
from tests.support_config import SUPERADMIN


BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


def _db():
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


def _login():
    response = requests.post(
        f"{API}/auth/login",
        json={"email": SUPERADMIN["email"], "password": SUPERADMIN["password"]},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _wait_job(token, job_id, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = requests.get(f"{API}/admin/migrate/jobs/{job_id}", headers=_headers(token), timeout=20)
        response.raise_for_status()
        job = response.json()
        if job["status"] in ("done", "error"):
            return job
        time.sleep(0.25)
    raise AssertionError(f"job {job_id} tidak selesai dalam {timeout}s")


@pytest.fixture(scope="module")
def super_token():
    return _login()


def test_period_column_is_strictly_bulan_laporan():
    columns = detect_columns(["Bulan laporan", "Bulan Penjualan", "Pendapatan Bersih"])
    assert columns["period"] == 0
    assert detect_columns(["Bulan Penjualan", "Pendapatan Bersih"])["period"] is None
    assert parse_period_from_value("01/06/2026") == "2026-06"
    assert parse_period_from_value("2026-13-01") is None
    assert parse_period_from_value("2026-99-sampah") is None


def test_upload_uses_bulan_laporan_and_rejects_invalid_rows(super_token):
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    label_name = f"PH35 PERIOD {suffix}"
    rows = [
        ["01/06/2025", "01/01/2024", "Spotify", label_name, f"IDPH35{suffix}1", "1,50"],
        ["01/07/2025", "01/02/2024", "Spotify", label_name, f"IDPH35{suffix}2", "2,50"],
        ["", "01/03/2024", "Spotify", label_name, f"IDPH35{suffix}3", "9,00"],
    ]
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(["Bulan laporan", "Bulan Penjualan", "Platform", "Nama Label", "ISRC", "Pendapatan Bersih"])
    writer.writerows(rows)
    response = requests.post(
        f"{API}/royalty/admin/imports",
        headers=_headers(super_token),
        files={"file": ("phase35.csv", buffer.getvalue().encode(), "text/csv")},
        data={"period": "2030-12", "rate_eur_idr": "17000"},
        timeout=30,
    )
    assert response.status_code == 200, response.text
    result = response.json()
    import_id = result["id"]
    try:
        assert result["period_breakdown"] == {"2025-06": 1, "2025-07": 1}
        assert result["invalid_period_rows"] == 1
        assert result["total_lines"] == 2
        assert result["total_revenue_eur"] == 4.0
        lines = list(db.royalty_lines.find({"import_id": import_id}, {"_id": 0, "period": 1, "row_period": 1}))
        assert {line["period"] for line in lines} == {"2025-06", "2025-07"}
        assert all(line["period"] == line["row_period"] for line in lines)
    finally:
        db.royalty_lines.delete_many({"import_id": import_id})
        db.royalty_imports.delete_one({"id": import_id})
        db.labels.delete_many({"auto_created_from": import_id})
        db.releases.delete_many({"auto_created_from": import_id})
        db.tracks.delete_many({"auto_created_from": import_id})
        db.artists.delete_many({"auto_created_from": import_id})


def test_upload_rejects_bulan_penjualan_without_bulan_laporan(super_token):
    csv_bytes = b"Bulan Penjualan;Nama Label;Pendapatan Bersih\n01/06/2026;PH35;1,00\n"
    response = requests.post(
        f"{API}/royalty/admin/imports",
        headers=_headers(super_token),
        files={"file": ("wrong-period.csv", csv_bytes, "text/csv")},
        data={"period": "2026-06", "rate_eur_idr": "17000"},
        timeout=30,
    )
    assert response.status_code == 400
    assert "Bulan laporan" in response.text


def test_mark_dana_received_runs_background_and_is_idempotent(super_token):
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    import_id = f"ph35-receive-{suffix}"
    label_id = f"ph35-label-{suffix}"
    amount = 12_500
    db.labels.insert_one({
        "id": label_id,
        "label_name": f"PH35 Receive {suffix}",
        "balance_pending_idr": amount * 3,
        "balance_available_idr": 5_000,
    })
    db.royalty_imports.insert_one({
        "id": import_id,
        "status": "published",
        "period": "2025-06",
        "period_start": "2025-06",
        "period_end": "2025-06",
        "is_multi_period": False,
        "dana_received_at": None,
        "uploaded_by": "phase35-test",
    })
    db.royalty_lines.insert_many([{
        "id": f"{import_id}-{index}",
        "import_id": import_id,
        "label_id": label_id,
        "status": "pending",
        "label_idr": amount,
        "match_status": "matched",
    } for index in range(3)])
    try:
        started = time.monotonic()
        response = requests.post(
            f"{API}/royalty/admin/imports/{import_id}/mark-dana-received",
            headers=_headers(super_token),
            timeout=15,
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "receiving"
        assert time.monotonic() - started < 5

        deadline = time.time() + 20
        while time.time() < deadline:
            current = db.royalty_imports.find_one({"id": import_id})
            if current.get("status") in ("dana_received", "receive_error"):
                break
            time.sleep(0.2)
        assert current["status"] == "dana_received", current.get("error_message")
        label = db.labels.find_one({"id": label_id})
        assert label["balance_pending_idr"] == 0
        assert label["balance_available_idr"] == 5_000 + amount * 3
        assert db.royalty_lines.count_documents({"import_id": import_id, "status": "available"}) == 3
        assert db.balance_transactions.count_documents({
            "reference_id": import_id, "type": "royalty_available",
        }) == 1

        repeated = requests.post(
            f"{API}/royalty/admin/imports/{import_id}/mark-dana-received",
            headers=_headers(super_token),
            timeout=15,
        )
        assert repeated.status_code == 400
    finally:
        db.royalty_lines.delete_many({"import_id": import_id})
        db.royalty_imports.delete_one({"id": import_id})
        db.balance_transactions.delete_many({"reference_id": import_id})
        db.labels.delete_one({"id": label_id})


def test_legacy_withdraw_preview_and_commit_are_background_jobs(super_token):
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    label_id = f"ph35-withdraw-{suffix}"
    label_name = f"PH35 Withdraw {suffix}"
    db.labels.insert_one({
        "id": label_id,
        "label_name": label_name,
        "last_withdrawn_period": None,
        "balance_pending_idr": 10_000,
        "balance_available_idr": 0,
        "royalty_percentage_default": 60,
    })
    db.royalty_lines.insert_one({
        "id": f"ph35-line-{suffix}",
        "label_id": label_id,
        "period": "2025-01",
        "status": "pending",
        "label_idr": 10_000,
        "revenue_eur": 1,
        "exchange_rate": 16_666,
        "match_status": "matched",
    })
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["trx_id", "nama_label", "period_start", "period_end"])
    writer.writerow([f"PH35-{suffix}", label_name, "2025-01", "2025-01"])
    csv_bytes = buffer.getvalue().encode()
    job_ids = []
    try:
        for dry_run in (True, False):
            started = time.monotonic()
            response = requests.post(
                f"{API}/admin/migrate/withdraws-legacy-period",
                headers=_headers(super_token),
                files={"file": ("withdraws.csv", csv_bytes, "text/csv")},
                data={"dry_run": str(dry_run).lower()},
                timeout=15,
            )
            assert response.status_code == 200, response.text
            queued = response.json()
            assert queued["status"] == "queued"
            assert queued["job_id"]
            job_ids.append(queued["job_id"])
            assert time.monotonic() - started < 15
            job = _wait_job(super_token, queued["job_id"])
            assert job["status"] == "done", job.get("error_message")
            if dry_run:
                assert job["result"]["dry_run"] is True
                assert job["result"]["matched_labels"] == 1
            else:
                assert job["preview_result"]["matched_labels"] == 1
                assert job["result"]["royalty_lines_flipped"] == 1

        assert db.labels.find_one({"id": label_id})["last_withdrawn_period"] == "2025-01"
        assert db.royalty_lines.find_one({"id": f"ph35-line-{suffix}"})["status"] == "withdrawn"
    finally:
        db.migrate_jobs.delete_many({"id": {"$in": job_ids}})
        db.withdraw_requests.delete_many({"label_id": label_id})
        db.royalty_lines.delete_many({"label_id": label_id})
        db.labels.delete_one({"id": label_id})


def test_existing_import_period_can_be_repaired_from_retained_csv(super_token):
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    import_id = f"ph35-repair-{suffix}"
    csv_path = Path("/app/backend/uploads/csv") / f"{import_id}.csv"
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(["Bulan laporan", "Bulan Penjualan", "Nama Label", "Pendapatan Bersih"])
    writer.writerow(["01/05/2025", "01/12/2024", "PH35 Repair", "1,00"])
    writer.writerow(["01/06/2025", "01/01/2025", "PH35 Repair", "2,00"])
    csv_path.write_text(buffer.getvalue(), encoding="utf-8")
    db.royalty_imports.insert_one({
        "id": import_id,
        "filename": csv_path.name,
        "status": "published",
        "period": "multi",
        "period_start": "2024-12",
        "period_end": "2025-01",
        "period_breakdown": {"2024-12": 1, "2025-01": 1},
        "uploaded_by": "phase35-test",
    })
    db.royalty_lines.insert_many([
        {
            "id": f"{import_id}-1", "import_id": import_id, "period": "2024-12",
            "row_period": "2024-12", "status": "pending", "match_status": "matched",
            "label_idr": 10_000, "revenue_eur": 1,
        },
        {
            "id": f"{import_id}-2", "import_id": import_id, "period": "2025-01",
            "row_period": "2025-01", "status": "pending", "match_status": "matched",
            "label_idr": 20_000, "revenue_eur": 2,
        },
    ])
    job_id = None
    try:
        response = requests.post(
            f"{API}/royalty/admin/imports/{import_id}/repair-reporting-period",
            headers=_headers(super_token), timeout=15,
        )
        assert response.status_code == 200, response.text
        job_id = response.json()["job_id"]
        job = _wait_job(super_token, job_id, timeout=60)
        assert job["status"] == "done", job.get("error_message")
        assert job["result"]["period_breakdown"] == {"2025-05": 1, "2025-06": 1}
        lines = list(db.royalty_lines.find({"import_id": import_id}).sort("_id", 1))
        assert [line["period"] for line in lines] == ["2025-05", "2025-06"]
        assert all(line["period"] == line["row_period"] for line in lines)
        repaired_import = db.royalty_imports.find_one({"id": import_id})
        assert repaired_import["status"] == "published"
        assert repaired_import["period_start"] == "2025-05"
        assert repaired_import["period_end"] == "2025-06"
        assert repaired_import["period_repair_status"] == "done"
    finally:
        csv_path.unlink(missing_ok=True)
        db.migrate_jobs.delete_many({"id": job_id})
        db.royalty_lines.delete_many({"import_id": import_id})
        db.royalty_imports.delete_one({"id": import_id})