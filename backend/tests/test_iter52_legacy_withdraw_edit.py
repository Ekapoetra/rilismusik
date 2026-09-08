"""Iter 52 — legacy withdrawal period edit API regression coverage."""
import os
import time
import uuid

import pymongo
import pytest
import requests
from dotenv import load_dotenv

from auth_utils import hash_password
from tests.support_config import FINANCE, SUPERADMIN, SUPPORT, temporary_password


load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/frontend/.env", override=True)
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _token(email: str, password: str) -> str:
    response = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def _wait_job(token: str, job_id: str, timeout: int = 60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = requests.get(f"{API}/admin/migrate/jobs/{job_id}", headers=_headers(token), timeout=30)
        assert response.status_code == 200, response.text
        body = response.json()
        if body.get("status") in {"done", "error"}:
            return body
        time.sleep(0.5)
    raise AssertionError(f"legacy-edit job timeout: {job_id}")


@pytest.fixture
def seeded_legacy_edit_case():
    """withdraw/legacy-edit module: deterministic fixture for preview + commit assertions"""
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    now = "2026-10-01T00:00:00+00:00"
    label_user_id = f"iter52-user-{suffix}"
    label_id = f"iter52-label-{suffix}"
    label_email = f"iter52-{suffix}@example.com"
    label_password = temporary_password("iter52")
    target_wd_id = f"iter52-legacy-target-{suffix}"
    web_paid_wd_id = f"iter52-web-paid-{suffix}"
    imp_id = f"iter52-import-{suffix}"

    db.users.insert_one({
        "id": label_user_id,
        "name": "Iter52 Label",
        "email": label_email,
        "password_hash": hash_password(label_password),
        "role": "label",
        "status": "active",
        "token_version": 0,
        "email_verified_at": now,
        "created_at": now,
        "updated_at": now,
    })
    db.labels.insert_one({
        "id": label_id,
        "user_id": label_user_id,
        "label_name": f"Iter52 Label {suffix}",
        "account_status": "active",
        "last_withdrawn_period": "2026-03",
        "balance_pending_idr": 0,
        "balance_available_idr": 9000,
        "balance_withdraw_requested_idr": 0,
        "created_at": now,
        "updated_at": now,
    })
    db.royalty_imports.insert_one({
        "id": imp_id,
        "status": "dana_received",
        "created_at": now,
        "updated_at": now,
    })
    db.royalty_lines.insert_many([
        {
            "id": f"iter52-line-mar-{suffix}",
            "label_id": label_id,
            "import_id": imp_id,
            "period": "2026-03",
            "status": "withdrawn",
            "legacy_settled": True,
            "legacy_settled_period_end": "2026-03",
            "label_idr": 3000,
        },
        {
            "id": f"iter52-line-apr-{suffix}",
            "label_id": label_id,
            "import_id": imp_id,
            "period": "2026-04",
            "status": "available",
            "legacy_settled": False,
            "label_idr": 9000,
        },
    ])
    db.withdraw_requests.insert_many([
        {
            "id": target_wd_id,
            "label_id": label_id,
            "amount_idr": 3000,
            "status": "paid",
            "legacy_import": True,
            "manual_legacy": True,
            "period_from": "2026-01",
            "period_to": "2026-03",
            "request_date": "2026-04-01",
            "paid_date": "2026-04-15",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": web_paid_wd_id,
            "label_id": label_id,
            "amount_idr": 2000,
            "status": "paid",
            "legacy_import": False,
            "period_from": "2025-12",
            "period_to": "2026-01",
            "created_at": now,
            "updated_at": now,
        },
    ])

    payload = {
        "label_id": label_id,
        "target_wd_id": target_wd_id,
        "web_paid_wd_id": web_paid_wd_id,
        "imp_id": imp_id,
        "label_email": label_email,
        "label_password": label_password,
        "finance_token": _token(FINANCE["email"], FINANCE["password"]),
        "support_token": _token(SUPPORT["email"], SUPPORT["password"]),
        "superadmin_token": _token(SUPERADMIN["email"], SUPERADMIN["password"]),
    }
    try:
        yield payload
    finally:
        db.migrate_jobs.delete_many({"label_id": label_id})
        db.legacy_withdraw_edit_previews.delete_many({"label_id": label_id})
        db.balance_transactions.delete_many({"label_id": label_id})
        db.activity_logs.delete_many({"$or": [{"resource_id": {"$regex": f"{suffix}"}}, {"user_id": label_user_id}]})
        db.withdraw_requests.delete_many({"label_id": label_id})
        db.royalty_lines.delete_many({"label_id": label_id})
        db.royalty_imports.delete_many({"id": imp_id})
        db.labels.delete_one({"id": label_id})
        db.users.delete_one({"id": label_user_id})


def test_admin_list_marks_legacy_editable_only_for_paid_legacy_with_period_to(seeded_legacy_edit_case):
    case = seeded_legacy_edit_case
    db = _db()
    # Add a legacy paid row without period_to to assert legacy_editable=False
    db.withdraw_requests.insert_one({
        "id": f"iter52-legacy-no-period-{uuid.uuid4().hex[:6]}",
        "label_id": case["label_id"],
        "amount_idr": 1000,
        "status": "paid",
        "legacy_import": True,
        "period_from": "2026-01",
        "period_to": None,
        "created_at": "2026-10-01T00:00:00+00:00",
        "updated_at": "2026-10-01T00:00:00+00:00",
    })
    response = requests.get(f"{API}/withdraw/admin", headers=_headers(case["finance_token"]), timeout=30)
    assert response.status_code == 200, response.text
    rows = {row["id"]: row for row in response.json() if row.get("label_id") == case["label_id"]}
    assert rows[case["target_wd_id"]]["legacy_editable"] is True
    assert rows[case["web_paid_wd_id"]]["legacy_editable"] is False
    assert all(row.get("_id") is None for row in rows.values())


def test_preview_role_gate_and_web_withdraw_rejected(seeded_legacy_edit_case):
    case = seeded_legacy_edit_case
    support_resp = requests.post(
        f"{API}/withdraw/admin/{case['target_wd_id']}/legacy-edit/preview",
        json={"period_to": "2026-02"},
        headers=_headers(case["support_token"]),
        timeout=30,
    )
    assert support_resp.status_code == 403

    web_resp = requests.post(
        f"{API}/withdraw/admin/{case['web_paid_wd_id']}/legacy-edit/preview",
        json={"period_to": "2026-02"},
        headers=_headers(case["finance_token"]),
        timeout=30,
    )
    assert web_resp.status_code == 400


def test_preview_decrease_returns_expected_math_and_does_not_mutate_rows(seeded_legacy_edit_case):
    case = seeded_legacy_edit_case
    db = _db()
    preview_resp = requests.post(
        f"{API}/withdraw/admin/{case['target_wd_id']}/legacy-edit/preview",
        json={"period_to": "2026-02"},
        headers=_headers(case["superadmin_token"]),
        timeout=30,
    )
    assert preview_resp.status_code == 200, preview_resp.text
    data = preview_resp.json()
    assert data["old_period_to"] == "2026-03"
    assert data["new_period_to"] == "2026-02"
    assert data["old_cutoff"] == "2026-03"
    assert data["new_cutoff"] == "2026-02"
    assert data["direction"] == "decrease"
    assert data["lines_to_restore"] == 1
    assert data["balance_before"]["available_idr"] == 9000
    assert data["balance_after"]["available_idr"] == 12000

    # Preview must not write royalty line statuses.
    line = db.royalty_lines.find_one({"id": {"$regex": "iter52-line-mar-"}}, {"_id": 0})
    assert line["status"] == "withdrawn"
    assert line["legacy_settled"] is True


def test_commit_decrease_then_increase_restores_and_re_settles_without_touching_web_withdraw(seeded_legacy_edit_case):
    case = seeded_legacy_edit_case
    db = _db()
    first_preview = requests.post(
        f"{API}/withdraw/admin/{case['target_wd_id']}/legacy-edit/preview",
        json={"period_to": "2026-02"},
        headers=_headers(case["finance_token"]),
        timeout=30,
    )
    assert first_preview.status_code == 200, first_preview.text
    first_commit = requests.post(
        f"{API}/withdraw/admin/{case['target_wd_id']}/legacy-edit",
        json={"preview_id": first_preview.json()["preview_id"]},
        headers=_headers(case["finance_token"]),
        timeout=30,
    )
    assert first_commit.status_code == 200, first_commit.text
    first_job = _wait_job(_token(SUPERADMIN["email"], SUPERADMIN["password"]), first_commit.json()["job_id"])
    assert first_job["status"] == "done", first_job.get("error_message")

    target = db.withdraw_requests.find_one({"id": case["target_wd_id"]}, {"_id": 0})
    web_paid = db.withdraw_requests.find_one({"id": case["web_paid_wd_id"]}, {"_id": 0})
    label = db.labels.find_one({"id": case["label_id"]}, {"_id": 0})
    mar_line = db.royalty_lines.find_one({"id": {"$regex": "iter52-line-mar-"}}, {"_id": 0})
    assert target["period_to"] == "2026-02"
    assert web_paid["period_to"] == "2026-01"
    assert label["last_withdrawn_period"] == "2026-02"
    assert label["balance_available_idr"] == 12000
    assert mar_line["status"] == "available"
    assert mar_line["legacy_settled"] is False

    second_preview = requests.post(
        f"{API}/withdraw/admin/{case['target_wd_id']}/legacy-edit/preview",
        json={"period_to": "2026-03"},
        headers=_headers(case["finance_token"]),
        timeout=30,
    )
    assert second_preview.status_code == 200, second_preview.text
    second_commit = requests.post(
        f"{API}/withdraw/admin/{case['target_wd_id']}/legacy-edit",
        json={"preview_id": second_preview.json()["preview_id"]},
        headers=_headers(case["finance_token"]),
        timeout=30,
    )
    assert second_commit.status_code == 200, second_commit.text
    second_job = _wait_job(_token(SUPERADMIN["email"], SUPERADMIN["password"]), second_commit.json()["job_id"])
    assert second_job["status"] == "done", second_job.get("error_message")

    target_after = db.withdraw_requests.find_one({"id": case["target_wd_id"]}, {"_id": 0})
    label_after = db.labels.find_one({"id": case["label_id"]}, {"_id": 0})
    mar_line_after = db.royalty_lines.find_one({"id": {"$regex": "iter52-line-mar-"}}, {"_id": 0})
    assert target_after["period_to"] == "2026-03"
    assert label_after["last_withdrawn_period"] == "2026-03"
    assert label_after["balance_available_idr"] == 9000
    assert mar_line_after["status"] == "withdrawn"
    assert mar_line_after["legacy_settled"] is True


def test_preview_blocked_by_active_web_withdraw_and_paid_history_without_period_to(seeded_legacy_edit_case):
    case = seeded_legacy_edit_case
    db = _db()
    active_id = f"iter52-active-{uuid.uuid4().hex[:6]}"
    db.withdraw_requests.insert_one({
        "id": active_id,
        "label_id": case["label_id"],
        "amount_idr": 500,
        "status": "requested",
        "legacy_import": False,
        "created_at": "2026-10-01T00:00:00+00:00",
        "updated_at": "2026-10-01T00:00:00+00:00",
    })
    blocked_active = requests.post(
        f"{API}/withdraw/admin/{case['target_wd_id']}/legacy-edit/preview",
        json={"period_to": "2026-02"},
        headers=_headers(case["finance_token"]),
        timeout=30,
    )
    assert blocked_active.status_code == 409
    db.withdraw_requests.delete_one({"id": active_id})

    missing_period_id = f"iter52-missing-period-{uuid.uuid4().hex[:6]}"
    db.withdraw_requests.insert_one({
        "id": missing_period_id,
        "label_id": case["label_id"],
        "amount_idr": 700,
        "status": "paid",
        "legacy_import": False,
        "period_from": "2025-11",
        "period_to": None,
        "created_at": "2026-10-01T00:00:00+00:00",
        "updated_at": "2026-10-01T00:00:00+00:00",
    })
    blocked_missing_period = requests.post(
        f"{API}/withdraw/admin/{case['target_wd_id']}/legacy-edit/preview",
        json={"period_to": "2026-02"},
        headers=_headers(case["finance_token"]),
        timeout=30,
    )
    assert blocked_missing_period.status_code == 409


def test_preview_validation_and_single_use_preview_and_stale_preview_rejected(seeded_legacy_edit_case):
    case = seeded_legacy_edit_case
    db = _db()
    invalid_month = requests.post(
        f"{API}/withdraw/admin/{case['target_wd_id']}/legacy-edit/preview",
        json={"period_to": "2026/02"},
        headers=_headers(case["finance_token"]),
        timeout=30,
    )
    assert invalid_month.status_code == 422

    before_period_from = requests.post(
        f"{API}/withdraw/admin/{case['target_wd_id']}/legacy-edit/preview",
        json={"period_to": "2025-12"},
        headers=_headers(case["finance_token"]),
        timeout=30,
    )
    assert before_period_from.status_code == 400

    after_latest = requests.post(
        f"{API}/withdraw/admin/{case['target_wd_id']}/legacy-edit/preview",
        json={"period_to": "2026-09"},
        headers=_headers(case["finance_token"]),
        timeout=30,
    )
    assert after_latest.status_code == 400

    single_use_preview = requests.post(
        f"{API}/withdraw/admin/{case['target_wd_id']}/legacy-edit/preview",
        json={"period_to": "2026-02"},
        headers=_headers(case["finance_token"]),
        timeout=30,
    )
    assert single_use_preview.status_code == 200, single_use_preview.text
    preview_id = single_use_preview.json()["preview_id"]
    first_commit = requests.post(
        f"{API}/withdraw/admin/{case['target_wd_id']}/legacy-edit",
        json={"preview_id": preview_id},
        headers=_headers(case["finance_token"]),
        timeout=30,
    )
    assert first_commit.status_code == 200, first_commit.text
    first_job = _wait_job(_token(SUPERADMIN["email"], SUPERADMIN["password"]), first_commit.json()["job_id"])
    assert first_job["status"] == "done", first_job.get("error_message")

    reuse_commit = requests.post(
        f"{API}/withdraw/admin/{case['target_wd_id']}/legacy-edit",
        json={"preview_id": preview_id},
        headers=_headers(case["finance_token"]),
        timeout=30,
    )
    assert reuse_commit.status_code == 404

    stale_preview = requests.post(
        f"{API}/withdraw/admin/{case['target_wd_id']}/legacy-edit/preview",
        json={"period_to": "2026-03"},
        headers=_headers(case["finance_token"]),
        timeout=30,
    )
    assert stale_preview.status_code == 200, stale_preview.text
    stale_preview_id = stale_preview.json()["preview_id"]
    db.withdraw_requests.update_one({"id": case["target_wd_id"]}, {"$set": {"period_to": "2026-04"}})
    stale_commit = requests.post(
        f"{API}/withdraw/admin/{case['target_wd_id']}/legacy-edit",
        json={"preview_id": stale_preview_id},
        headers=_headers(case["finance_token"]),
        timeout=30,
    )
    assert stale_commit.status_code == 409
