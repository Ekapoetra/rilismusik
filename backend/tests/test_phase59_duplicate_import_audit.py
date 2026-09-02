"""Phase 59 — read-only duplicate royalty import audit."""
import os
import time
import uuid

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


def _wait(token, job_id, timeout=90):
    deadline = time.time() + timeout
    headers = {"Authorization": f"Bearer {token}"}
    while time.time() < deadline:
        response = requests.get(
            f"{API}/royalty/admin/duplicate-audit/jobs/{job_id}", headers=headers, timeout=20,
        )
        response.raise_for_status()
        job = response.json()
        if job["status"] in ("done", "error"):
            return job
        time.sleep(0.2)
    raise AssertionError(f"duplicate audit timeout: {job_id}")


def test_duplicate_audit_is_read_only_and_reports_period_and_label_impact():
    db = _db()
    token = _login()
    suffix = uuid.uuid4().hex[:8]
    canonical_id = f"ph59-canonical-{suffix}"
    duplicate_id = f"ph59-duplicate-{suffix}"
    unique_id = f"ph59-unique-{suffix}"
    label_a = f"ph59-label-a-{suffix}"
    label_b = f"ph59-label-b-{suffix}"
    job_id = None
    shared = {
        "status": "dana_received",
        "total_lines": 3,
        "matched_lines": 3,
        "total_revenue_eur": 15.5,
        "period": "multi",
        "period_start": "2026-03",
        "period_end": "2026-05",
        "period_breakdown": {"2026-03": 2, "2026-05": 1},
    }
    db.royalty_imports.insert_many([
        {"id": canonical_id, "filename": "MEI 2026.csv", "exchange_rate_eur_idr": 18_000,
         "created_at": "2026-08-23T00:00:00+00:00", "total_label_idr": 139_500, **shared},
        {"id": duplicate_id, "filename": "Mei 2022.csv", "exchange_rate_eur_idr": 15_500,
         "created_at": "2026-08-06T00:00:00+00:00", "total_label_idr": 120_125, **shared},
        {"id": unique_id, "filename": "JUNI 2026.csv", "exchange_rate_eur_idr": 19_000,
         "created_at": "2026-08-24T00:00:00+00:00", "total_label_idr": 9_500,
         **{**shared, "total_lines": 1, "total_revenue_eur": 1, "period_start": "2026-06",
            "period_end": "2026-06", "period_breakdown": {"2026-06": 1}}},
    ])
    db.labels.insert_many([
        {"id": label_a, "label_name": f"PH59 A {suffix}", "last_withdrawn_period": "2026-01"},
        {"id": label_b, "label_name": f"PH59 B {suffix}", "last_withdrawn_period": "2026-04"},
    ])
    db.withdraw_requests.insert_one({
        "id": f"ph59-paid-{suffix}", "label_id": label_b, "status": "paid",
        "period_from": "2026-01", "period_to": "2026-04", "amount_idr": 1,
    })
    source_rows = [
        ("2026-03", label_a, "available", False, 10.0),
        ("2026-03", label_a, "available", False, 0.5),
        ("2026-05", label_b, "withdrawn", True, 5.0),
    ]
    docs = []
    for import_id, rate in ((canonical_id, 18_000), (duplicate_id, 15_500)):
        for index, (period, label_id, status, legacy, revenue) in enumerate(source_rows):
            docs.append({
                "id": f"ph59-{import_id}-{index}", "import_id": import_id, "label_id": label_id,
                "period": period, "status": status, "legacy_settled": legacy,
                "match_status": "matched", "revenue_eur": revenue,
                "exchange_rate": rate, "label_idr": round(revenue * 0.5 * rate),
            })
    db.royalty_lines.insert_many(docs)
    before = list(db.royalty_lines.find({"import_id": duplicate_id}, {"_id": 0}).sort("id", 1))
    try:
        started = requests.post(
            f"{API}/royalty/admin/duplicate-audit/preview",
            headers={"Authorization": f"Bearer {token}"}, timeout=20,
        )
        assert started.status_code == 200, started.text
        job_id = started.json()["job_id"]
        job = _wait(token, job_id)
        assert job["status"] == "done", job.get("error_message")
        assert job["summary"]["duplicate_pairs"] >= 1
        assert job["summary"]["exact_content_pairs"] >= 1
        assert job["summary"]["duplicate_lines"] >= 3

        response = requests.get(
            f"{API}/royalty/admin/duplicate-audit/jobs/{job_id}/rows",
            headers={"Authorization": f"Bearer {token}"}, timeout=20,
        )
        assert response.status_code == 200, response.text
        row = next(
            item for item in response.json()["items"]
            if item["duplicate_import"]["id"] == duplicate_id
        )
        assert row["read_only"] is True
        assert row["canonical_import"]["id"] == canonical_id
        assert row["duplicate_import"]["id"] == duplicate_id
        assert row["comparison"]["exact_period_match"] is True
        assert len(row["comparison"]["periods"]) == 2
        assert row["impact"]["affected_labels"] == 2
        assert row["impact"]["labels_with_paid_withdrawal"] == 1
        assert row["impact"]["requires_paid_history_review"] is True
        assert row["impact"]["active_balance_idr"] == round(10.5 * 0.5 * 15_500)
        assert row["impact"]["historical_or_excluded_idr"] == round(5 * 0.5 * 15_500)
        after = list(db.royalty_lines.find({"import_id": duplicate_id}, {"_id": 0}).sort("id", 1))
        assert after == before
        assert db.royalty_imports.find_one({"id": duplicate_id})["status"] == "dana_received"
    finally:
        if job_id:
            db.migrate_jobs.delete_one({"id": job_id})
            db.royalty_duplicate_audit_rows.delete_many({"job_id": job_id})
        db.withdraw_requests.delete_many({"label_id": {"$in": [label_a, label_b]}})
        db.royalty_lines.delete_many({"import_id": {"$in": [canonical_id, duplicate_id, unique_id]}})
        db.royalty_imports.delete_many({"id": {"$in": [canonical_id, duplicate_id, unique_id]}})
        db.labels.delete_many({"id": {"$in": [label_a, label_b]}})