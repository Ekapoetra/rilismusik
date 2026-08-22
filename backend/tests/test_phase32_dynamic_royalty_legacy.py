"""Phase 32 — no-fee dynamic royalty and legacy reporting-month cutoff."""
import csv
import io
import os
import sys
import time
import uuid
from pathlib import Path

import pymongo
import requests
from dotenv import dotenv_values, load_dotenv

sys.path.append(str(Path(__file__).resolve().parents[1]))
from auth_utils import hash_password


load_dotenv("/app/backend/.env")
FRONTEND_ENV = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or FRONTEND_ENV["REACT_APP_BACKEND_URL"]).rstrip("/")
API = f"{BASE}/api"
SUPER = {"email": "superadmin@rilismusik.com", "password": "SuperAdmin#2026"}


def _db():
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


def _token(credentials):
    response = requests.post(f"{API}/auth/login", json=credentials, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _wait_job(token, job_id, timeout=40):
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = requests.get(f"{API}/admin/migrate/jobs/{job_id}", headers=_headers(token), timeout=20)
        response.raise_for_status()
        job = response.json()
        if job["status"] == "done":
            return job
        if job["status"] == "error":
            raise AssertionError(job.get("error_message"))
        time.sleep(0.3)
    raise AssertionError(f"job {job_id} timeout")


def _wait_import(token, import_id, expected, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = requests.get(f"{API}/royalty/admin/imports/{import_id}", headers=_headers(token), timeout=20)
        response.raise_for_status()
        status = response.json()["import"]["status"]
        if status == expected:
            return response.json()
        if status in ("error", "publish_error"):
            raise AssertionError(response.text)
        time.sleep(0.3)
    raise AssertionError(f"import {import_id} did not reach {expected}")


def test_dynamic_percentage_and_legacy_cutoff_end_to_end():
    db = _db()
    suffix = uuid.uuid4().hex[:10]
    label_id = f"phase32-label-{suffix}"
    user_id = f"phase32-user-{suffix}"
    import_id = f"phase32-import-{suffix}"
    email = f"phase32-{suffix}@example.com"
    password = "Phase32#2026"
    label_name = f"Phase32 Label {suffix}"
    now = "2026-07-01T00:00:00+00:00"
    super_token = _token(SUPER)
    uploaded_import_id = None

    db.users.insert_one({
        "id": user_id, "name": "Phase 32 Label", "email": email,
        "password_hash": hash_password(password), "role": "label",
        "status": "active", "email_verified_at": now, "created_at": now,
        "updated_at": now, "token_version": 0,
    })
    db.labels.insert_one({
        "id": label_id, "user_id": user_id, "label_name": label_name,
        "royalty_percentage_default": 60.0, "last_withdrawn_period": None,
        "balance_pending_idr": 57_000, "balance_available_idr": 57_000,
        "balance_withdraw_requested_idr": 0, "account_status": "active",
        "bank_verified": True, "created_at": now, "updated_at": now,
    })
    db.royalty_imports.insert_one({
        "id": import_id, "status": "dana_received", "fee_percent": 5.0,
        "exchange_rate_eur_idr": 10_000, "total_label_idr": 228_000,
        "created_at": now, "updated_at": now,
    })
    lines = [
        ("pending", "2024-12"),
        ("available", "2025-01"),
        ("draft", "2024-11"),
        ("withdrawn", "2024-10"),
    ]
    db.royalty_lines.insert_many([{
        "id": f"phase32-line-{suffix}-{index}", "import_id": import_id,
        "label_id": label_id, "period": period, "status": status,
        "match_status": "matched", "revenue_eur": 10.0,
        "exchange_rate": 10_000.0, "fee_eur": 0.5, "net_eur": 9.5,
        "label_percentage_applied": 60.0, "fee_percent_applied": 5.0,
        "label_eur": 5.7, "distributor_eur": 3.8, "label_idr": 57_000,
        "distributor_idr": 38_000, "revenue_idr": 100_000,
        "quantity": 1, "platform": "Spotify", "country": "ID",
        "track_title_raw": f"Track {index}", "created_at": now,
    } for index, (status, period) in enumerate(lines)])

    try:
        response = requests.patch(
            f"{API}/admin/labels/{label_id}",
            json={"royalty_percentage_default": 95, "royalty_change_reason": "Phase 32 test"},
            headers=_headers(super_token), timeout=30,
        )
        assert response.status_code == 200, response.text
        job = _wait_job(super_token, response.json()["royalty_recalculation_job_id"])
        assert job["result"]["lines_recalculated"] == 3

        recalculated = list(db.royalty_lines.find({"label_id": label_id}, {"_id": 0}).sort("period", 1))
        by_status = {row["status"]: row for row in recalculated}
        assert by_status["pending"]["label_idr"] == 95_000
        assert by_status["available"]["label_idr"] == 95_000
        assert by_status["draft"]["label_idr"] == 95_000
        assert by_status["withdrawn"]["label_idr"] == 57_000
        assert by_status["available"]["fee_eur"] == 0
        assert by_status["available"]["fee_percent_applied"] == 0
        label = db.labels.find_one({"id": label_id})
        assert label["balance_pending_idr"] == 95_000
        assert label["balance_available_idr"] == 95_000
        assert db.royalty_imports.find_one({"id": import_id})["total_label_idr"] == 342_000

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["trx_id", "nama_label", "amount", "exchange_rate", "period_start", "period_end"])
        writer.writerow([f"LEG-{suffix}", label_name, "9999", "99999", "2020-01", "2024-12"])
        response = requests.post(
            f"{API}/admin/migrate/withdraws-legacy-period",
            files={"file": ("legacy.csv", buf.getvalue().encode(), "text/csv")},
            data={"dry_run": "false", "create_history_docs": "true", "flip_royalty_lines": "true", "adjust_balances": "true"},
            headers=_headers(super_token), timeout=30,
        )
        assert response.status_code == 200, response.text
        legacy_job = _wait_job(super_token, response.json()["job_id"])
        assert legacy_job["result"]["royalty_lines_flipped"] == 2

        label = db.labels.find_one({"id": label_id})
        assert label["last_withdrawn_period"] == "2024-12"
        assert label["legacy_withdraw_period_end"] == "2024-12"
        assert label["balance_pending_idr"] == 0
        assert label["balance_available_idr"] == 95_000
        settled = list(db.royalty_lines.find({"label_id": label_id, "legacy_settled": True}))
        assert {row["period"] for row in settled} == {"2024-11", "2024-12"}

        label_token = _token({"email": email, "password": password})
        months = requests.get(f"{API}/royalty/months", headers=_headers(label_token), timeout=30).json()
        assert months == ["2025-01"]
        summary = requests.get(f"{API}/royalty/summary", headers=_headers(label_token), timeout=30).json()
        assert summary["summary"]["total_idr"] == 95_000
        history = requests.get(f"{API}/withdraw/label", headers=_headers(label_token), timeout=30).json()
        assert history == []

        # A late royalty CSV row for an already-settled reporting month must
        # also be locked when the same legacy cutoff is synchronized again.
        late_line_id = f"phase32-line-late-{suffix}"
        db.royalty_lines.insert_one({
            "id": late_line_id, "import_id": import_id, "label_id": label_id,
            "period": "2024-12", "status": "draft", "match_status": "matched",
            "revenue_eur": 5.0, "exchange_rate": 10_000.0,
            "label_percentage_applied": 95.0, "fee_percent_applied": 0.0,
            "fee_eur": 0.0, "net_eur": 5.0, "label_eur": 4.75,
            "distributor_eur": 0.25, "label_idr": 47_500,
            "distributor_idr": 2_500, "revenue_idr": 50_000,
        })
        response = requests.post(
            f"{API}/admin/migrate/withdraws-legacy-period",
            files={"file": ("legacy.csv", buf.getvalue().encode(), "text/csv")},
            data={"dry_run": "false", "create_history_docs": "true", "flip_royalty_lines": "true", "adjust_balances": "true"},
            headers=_headers(super_token), timeout=30,
        )
        rerun_job = _wait_job(super_token, response.json()["job_id"])
        assert rerun_job["result"]["labels_period_updated"] == 0
        assert rerun_job["result"]["royalty_lines_flipped"] == 1
        late_line = db.royalty_lines.find_one({"id": late_line_id})
        assert late_line["status"] == "withdrawn"
        assert late_line["legacy_settled"] is True

        # A Believe CSV uploaded AFTER legacy synchronization is locked during
        # ingestion when its Bulan Laporan is at/before the cutoff.
        release_id = f"phase32-release-{suffix}"
        track_id = f"phase32-track-{suffix}"
        isrc = f"ID-P32-{suffix[:5]}"
        db.releases.insert_one({"id": release_id, "label_id": label_id, "release_title": "Phase 32", "status": "live"})
        db.tracks.insert_one({"id": track_id, "release_id": release_id, "label_id": label_id, "isrc": isrc, "track_title": "Late CSV"})
        royalty_csv = (
            "ISRC,UPC,Track Title,Artist,Album,Platform,Country,Period,Quantity,Net Revenue EUR\n"
            f"{isrc},,Late CSV,Tester,Phase 32,Spotify,ID,2024-12,10,10\n"
        ).encode()
        response = requests.post(
            f"{API}/royalty/admin/imports",
            files={"file": ("believe.csv", royalty_csv, "text/csv")},
            data={"period": "2024-12", "rate_eur_idr": "10000"},
            headers=_headers(super_token), timeout=30,
        )
        assert response.status_code == 200, response.text
        uploaded_import = response.json()
        uploaded_import_id = uploaded_import["id"]
        assert uploaded_import["fee_percent"] == 0
        assert uploaded_import["matched_lines"] == 1
        detail = requests.get(
            f"{API}/royalty/admin/imports/{uploaded_import['id']}", headers=_headers(super_token), timeout=30,
        ).json()
        assert detail["lines"][0]["status"] == "withdrawn"
        assert detail["lines"][0]["legacy_settled"] is True
        before_publish_balance = db.labels.find_one({"id": label_id})["balance_pending_idr"]
        response = requests.post(
            f"{API}/royalty/admin/imports/{uploaded_import['id']}/publish",
            json={}, headers=_headers(super_token), timeout=30,
        )
        assert response.status_code == 200, response.text
        _wait_import(super_token, uploaded_import["id"], "published")
        assert db.labels.find_one({"id": label_id})["balance_pending_idr"] == before_publish_balance
    finally:
        db.users.delete_many({"id": user_id})
        db.labels.delete_many({"id": label_id})
        db.royalty_imports.delete_many({"id": import_id})
        if uploaded_import_id:
            db.royalty_imports.delete_many({"id": uploaded_import_id})
        db.royalty_lines.delete_many({"label_id": label_id})
        db.royalty_percentage_history.delete_many({"label_id": label_id})
        db.withdraw_requests.delete_many({"label_id": label_id})
        db.balance_transactions.delete_many({"label_id": label_id})
        db.migrate_jobs.delete_many({"label_id": label_id})
        db.releases.delete_many({"label_id": label_id})
        db.tracks.delete_many({"label_id": label_id})