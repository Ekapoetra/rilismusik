"""Iter 63 — financial acceptance coverage for approve/paid and atomicity safeguards."""

import asyncio
import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import pymongo
import pytest
import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

from auth_utils import hash_password
from tests.support_config import FINANCE, temporary_password


load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/frontend/.env", override=True)

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _login(account: dict) -> str:
    response = requests.post(f"{API}/auth/login", json=account, timeout=30)
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _headers(token: str):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def fresh_async_db(monkeypatch):
    """Each in-process test owns its Motor client; never reuse a closed test loop."""
    import importlib
    modules = [importlib.import_module(name) for name in (
        "routes.deps", "routes.admin_permission_service", "routes.balance_utils",
        "routes.royalty_adjustment_balance", "routes.royalty_adjustment_service",
        "routes.royalty_adjustment_mutations", "routes.financial_lock", "routes.withdraw",
    )]
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    database = client[os.environ["DB_NAME"]]
    for module in modules:
        for attribute in ("db", "db_bg"):
            if hasattr(module, attribute):
                monkeypatch.setattr(module, attribute, database)
    from auth_utils import make_get_current_user
    from routes import deps
    monkeypatch.setattr(deps, "_base_get_current_user", make_get_current_user(database))
    yield database
    client.close()


@pytest.fixture
def inprocess_paid_api(monkeypatch, fresh_async_db):
    """Real authenticated payment-status route and Mongo, sender mocked in SAME process."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from routes.withdraw import withdraw_r
    app = FastAPI()
    app.include_router(withdraw_r, prefix="/api")
    real_post = requests.post
    with TestClient(app) as client:
        def dispatch(url, **kwargs):
            if url.startswith(f"{API}/withdraw/admin/") and url.endswith("/action"):
                kwargs.pop("timeout", None)
                return client.post(url.removeprefix(BASE), **kwargs)
            return real_post(url, **kwargs)
        monkeypatch.setattr(requests, "post", dispatch)
        yield


def _adjustment_payload(amount: int, *, reference: str, boundary: str = "2026-06", ref_amount: int | None = None):
    return {
        "amount_idr": amount,
        "currency": "IDR",
        "adjustment_type": "LEGACY_RECONCILIATION",
        "reason": "Iter63 financial acceptance coverage",
        "reference": reference,
        "legacy_period_to": boundary,
        "reference_amount_idr": ref_amount,
    }


@pytest.fixture()
def qa_fixture():
    """royalty_adjustment + withdraw modules: isolated REAL Mongo fixture with narrow cleanup."""
    db = _db()
    created = {
        "label_ids": [],
        "user_ids": [],
        "user_emails": [],
        "contract_ids": [],
        "bank_ids": [],
        "kyc_ids": [],
    }

    def create_verified_label(*, tag: str, line_specs: list[dict] | None = None):
        suffix = uuid.uuid4().hex[:8]
        now = datetime.now(timezone.utc).isoformat()
        user_id = f"iter63-user-{tag}-{suffix}"
        label_id = f"iter63-label-{tag}-{suffix}"
        label_name = f"Iter63 {tag} {suffix}"
        email = f"iter63-{tag}-{suffix}@example.com"
        password = temporary_password("Iter63Label")
        bank_id = f"iter63-bank-{tag}-{suffix}"
        contract_id = f"iter63-contract-{tag}-{suffix}"
        kyc_id = f"iter63-kyc-{tag}-{suffix}"

        db.users.insert_one({
            "id": user_id,
            "name": label_name,
            "email": email,
            "password_hash": hash_password(password),
            "role": "label",
            "status": "active",
            "token_version": 0,
            "email_verified_at": now,
            "created_at": now,
            "updated_at": now,
        })
        db.labels.insert_one({
            "id": label_id,
            "user_id": user_id,
            "label_name": label_name,
            "pic_name": f"PIC {tag}",
            "whatsapp": "+6281234567890",
            "address": "Jl. Test Iter63",
            "city": "Jakarta",
            "logo_storage_key": f"label-logo/{label_id}/logo.png",
            "account_status": "active",
            "kyc_status": "verified",
            "kyc_document_id": kyc_id,
            "kyc_verified_at": now,
            "bank_verified": True,
            "last_withdrawn_period": None,
            "balance_pending_idr": 0,
            "balance_available_idr": 0,
            "balance_withdraw_requested_idr": 0,
            "created_at": now,
            "updated_at": now,
        })
        db.bank_accounts.insert_one({
            "id": bank_id,
            "label_id": label_id,
            "bank_name": "Bank QA",
            "account_number": f"98765{suffix}",
            "account_holder_name": label_name,
            "verified_status": "verified",
            "verified_at": now,
            "created_at": now,
            "updated_at": now,
        })
        db.contracts.insert_one({
            "id": contract_id,
            "label_id": label_id,
            "status": "active",
            "file_url": "/api/files/contract/test.pdf",
            "filename": "test.pdf",
            "start_date": "2025-01-01",
            "end_date": "2030-01-01",
            "created_at": now,
            "updated_at": now,
        })
        db.kyc_documents.insert_one({
            "id": kyc_id,
            "label_id": label_id,
            "status": "verified",
            "is_current": True,
            "storage_key": f"kyc-private/{label_id}/ktp.pdf",
            "sha256": suffix,
            "uploaded_at": now,
            "verified_at": now,
        })
        for index, spec in enumerate(line_specs or []):
            db.royalty_lines.insert_one({
                "id": f"iter63-line-{tag}-{suffix}-{index}",
                "label_id": label_id,
                "period": spec["period"],
                "status": spec.get("status", "available"),
                "legacy_settled": bool(spec.get("legacy_settled", False)),
                "label_idr": int(spec["label_idr"]),
                "created_at": now,
                "updated_at": now,
            })

        created["label_ids"].append(label_id)
        created["user_ids"].append(user_id)
        created["user_emails"].append(email)
        created["contract_ids"].append(contract_id)
        created["bank_ids"].append(bank_id)
        created["kyc_ids"].append(kyc_id)
        return {
            "label_id": label_id,
            "label_name": label_name,
            "user_email": email,
            "user_password": password,
        }

    yield {"db": db, "create_verified_label": create_verified_label}

    refs = [row["id"] for row in db.balance_transactions.find({"label_id": {"$in": created["label_ids"]}}, {"_id": 0, "id": 1})]
    refs += [row["id"] for row in db.withdraw_requests.find({"label_id": {"$in": created["label_ids"]}}, {"_id": 0, "id": 1})]
    db.activity_logs.delete_many({"$or": [{"reference_id": {"$in": refs + created["label_ids"]}}, {"user_id": {"$in": created["user_ids"]}}]})
    db.notifications.delete_many({"user_id": {"$in": created["user_ids"]}})
    db.financial_operation_locks.delete_many({"_id": {"$in": created["label_ids"]}})
    db.withdraw_requests.delete_many({"label_id": {"$in": created["label_ids"]}})
    db.royalty_adjustment_previews.delete_many({"label_id": {"$in": created["label_ids"]}})
    db.balance_transactions.delete_many({"label_id": {"$in": created["label_ids"]}})
    db.royalty_lines.delete_many({"label_id": {"$in": created["label_ids"]}})
    db.contracts.delete_many({"id": {"$in": created["contract_ids"]}})
    db.bank_accounts.delete_many({"id": {"$in": created["bank_ids"]}})
    db.kyc_documents.delete_many({"id": {"$in": created["kyc_ids"]}})
    db.labels.delete_many({"id": {"$in": created["label_ids"]}})
    db.users.delete_many({"id": {"$in": created["user_ids"]}})
    db.users.delete_many({"email": {"$in": created["user_emails"]}})


def _preview(headers: dict, label_id: str, payload: dict):
    response = requests.post(
        f"{API}/royalty/admin/adjustments/labels/{label_id}/preview",
        headers=headers,
        json=payload,
        timeout=30,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _commit(headers: dict, label_id: str, preview_id: str):
    return requests.post(
        f"{API}/royalty/admin/adjustments/labels/{label_id}",
        headers=headers,
        json={"preview_id": preview_id},
        timeout=30,
    )


def test_request_approve_paid_flow_full_amount_and_paid_guards(qa_fixture, monkeypatch, inprocess_paid_api):
    # Modules/features: withdraw mark_paid flow + adjustment history/post-payment invariants.
    import routes.withdraw as withdraw_module

    emails = []

    async def fake_send_withdraw_paid_email(**kwargs):
        emails.append(kwargs)
        return "MOCKED-withdraw-paid"

    monkeypatch.setattr(withdraw_module, "send_withdraw_paid_email", fake_send_withdraw_paid_email)

    label = qa_fixture["create_verified_label"](
        tag="paid-main",
        line_specs=[{"period": "2026-06", "label_idr": 13_800_000, "status": "available", "legacy_settled": False}],
    )
    finance_headers = _headers(_login(FINANCE))
    label_headers = _headers(_login({"email": label["user_email"], "password": label["user_password"]}))

    preview = _preview(finance_headers, label["label_id"], _adjustment_payload(1_450_000, reference="ITER63-MAIN", ref_amount=15_250_000))
    created = _commit(finance_headers, label["label_id"], preview["preview_id"])
    assert created.status_code == 200, created.text

    computed_before = requests.get(f"{API}/withdraw/label/computed", headers=label_headers, timeout=30)
    assert computed_before.status_code == 200, computed_before.text
    assert computed_before.json()["withdrawable_idr"] == 15_250_000
    assert computed_before.json()["can_withdraw"] is True

    malicious_request = requests.post(f"{API}/withdraw/label/request", headers=label_headers, json={"amount_idr": 1}, timeout=30)
    assert malicious_request.status_code == 200, malicious_request.text
    wd = malicious_request.json()
    assert wd["amount_idr"] == 15_250_000

    approved = requests.post(f"{API}/withdraw/admin/{wd['id']}/action", headers=finance_headers, json={"action": "approve", "note": "iter63 approve"}, timeout=30)
    assert approved.status_code == 200, approved.text

    paid = requests.post(
        f"{API}/withdraw/admin/{wd['id']}/action",
        headers=finance_headers,
        json={"action": "mark_paid", "payment_reference": "ITER63-PAID", "amount_idr": 123},
        timeout=30,
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["status"] == "paid"
    assert paid.json()["amount_idr"] == 15_250_000
    assert len(emails) == 1  # Sender is patched in the process executing mark_paid.

    tx_count = qa_fixture["db"].balance_transactions.count_documents({"type": "withdraw_paid", "reference_id": wd["id"]})
    assert tx_count == 1

    duplicate_paid = requests.post(
        f"{API}/withdraw/admin/{wd['id']}/action",
        headers=finance_headers,
        json={"action": "mark_paid", "payment_reference": "ITER63-PAID-2"},
        timeout=30,
    )
    assert duplicate_paid.status_code == 400
    assert qa_fixture["db"].balance_transactions.count_documents({"type": "withdraw_paid", "reference_id": wd["id"]}) == 1

    computed_after = requests.get(f"{API}/withdraw/label/computed", headers=label_headers, timeout=30)
    assert computed_after.status_code == 200, computed_after.text
    assert computed_after.json()["withdrawable_idr"] == 0
    assert computed_after.json()["can_withdraw"] is False

    history = requests.get(f"{API}/royalty/admin/adjustments/labels/{label['label_id']}", headers=finance_headers, timeout=30)
    assert history.status_code == 200, history.text
    item = history.json()["items"][0]
    assert item["withdrawal_status"] == "paid"
    assert item["can_void"] is False

    void_after_paid = requests.post(
        f"{API}/royalty/admin/adjustments/labels/{label['label_id']}/{item['id']}/void",
        headers=finance_headers,
        json={"reason": "should fail after paid"},
        timeout=30,
    )
    assert void_after_paid.status_code == 409


def test_adjustment_only_paid_keeps_cutoff_none_and_spends_only_once(qa_fixture, monkeypatch, inprocess_paid_api):
    # Modules/features: adjustment-only withdraw + post-paid new funds + unspent adjustment IDs.
    import routes.withdraw as withdraw_module

    async def fake_send_withdraw_paid_email(**kwargs):
        return "MOCKED-withdraw-paid"

    monkeypatch.setattr(withdraw_module, "send_withdraw_paid_email", fake_send_withdraw_paid_email)

    label = qa_fixture["create_verified_label"](tag="adjust-only", line_specs=[])
    db = qa_fixture["db"]
    finance_headers = _headers(_login(FINANCE))
    label_headers = _headers(_login({"email": label["user_email"], "password": label["user_password"]}))

    preview = _preview(finance_headers, label["label_id"], _adjustment_payload(1_000_001, reference="ITER63-ADJ-ONLY"))
    assert _commit(finance_headers, label["label_id"], preview["preview_id"]).status_code == 200

    req = requests.post(f"{API}/withdraw/label/request", headers=label_headers, timeout=30)
    assert req.status_code == 200, req.text
    wd = req.json()
    assert wd["period_from"] is None and wd["period_to"] is None

    assert requests.post(f"{API}/withdraw/admin/{wd['id']}/action", headers=finance_headers, json={"action": "approve"}, timeout=30).status_code == 200
    assert requests.post(
        f"{API}/withdraw/admin/{wd['id']}/action",
        headers=finance_headers,
        json={"action": "mark_paid", "payment_reference": "ITER63-ONLY"},
        timeout=30,
    ).status_code == 200

    stored_label = db.labels.find_one({"id": label["label_id"]}, {"_id": 0, "last_withdrawn_period": 1})
    assert stored_label["last_withdrawn_period"] is None

    db.royalty_lines.insert_one({
        "id": f"iter63-future-{uuid.uuid4().hex[:8]}",
        "label_id": label["label_id"],
        "period": "2026-10",
        "status": "available",
        "legacy_settled": False,
        "label_idr": 300_000,
    })
    after_csv = requests.get(f"{API}/withdraw/label/computed", headers=label_headers, timeout=30).json()
    assert after_csv["withdrawable_idr"] == 300_000
    assert after_csv["can_withdraw"] is False

    preview2 = _preview(finance_headers, label["label_id"], _adjustment_payload(800_001, reference="ITER63-ADJ-SECOND", boundary="2026-09"))
    commit2 = _commit(finance_headers, label["label_id"], preview2["preview_id"])
    assert commit2.status_code == 200, commit2.text
    second_adjustment_id = commit2.json()["adjustment"]["id"]

    req2 = requests.post(f"{API}/withdraw/label/request", headers=label_headers, timeout=30)
    assert req2.status_code == 200, req2.text
    wd2 = db.withdraw_requests.find_one({"id": req2.json()["id"]}, {"_id": 0})
    assert wd2["amount_idr"] == 1_100_001
    assert wd2["adjustment_amount_idr"] == 800_001
    assert wd2["royalty_amount_idr"] == 300_000
    assert wd2["adjustment_ids"] == [second_adjustment_id]


def test_mixed_withdraw_cutoff_uses_latest_csv_period_not_legacy_boundary(qa_fixture, monkeypatch, inprocess_paid_api):
    # Modules/features: paid mixed withdrawal cutoff behavior.
    import routes.withdraw as withdraw_module

    async def fake_send_withdraw_paid_email(**kwargs):
        return "MOCKED-withdraw-paid"

    monkeypatch.setattr(withdraw_module, "send_withdraw_paid_email", fake_send_withdraw_paid_email)

    label = qa_fixture["create_verified_label"](
        tag="mixed-cutoff",
        line_specs=[
            {"period": "2026-06", "label_idr": 13_800_000, "status": "available", "legacy_settled": False},
            {"period": "2026-08", "label_idr": 200_000, "status": "available", "legacy_settled": False},
        ],
    )
    finance_headers = _headers(_login(FINANCE))
    label_headers = _headers(_login({"email": label["user_email"], "password": label["user_password"]}))

    preview = _preview(finance_headers, label["label_id"], _adjustment_payload(1_250_000, reference="ITER63-MIXED", boundary="2026-06", ref_amount=15_250_000))
    assert _commit(finance_headers, label["label_id"], preview["preview_id"]).status_code == 200
    wd = requests.post(f"{API}/withdraw/label/request", headers=label_headers, timeout=30)
    assert wd.status_code == 200, wd.text
    wd_id = wd.json()["id"]
    assert requests.post(f"{API}/withdraw/admin/{wd_id}/action", headers=finance_headers, json={"action": "approve"}, timeout=30).status_code == 200
    assert requests.post(
        f"{API}/withdraw/admin/{wd_id}/action",
        headers=finance_headers,
        json={"action": "mark_paid", "payment_reference": "ITER63-MIXED"},
        timeout=30,
    ).status_code == 200

    stored_label = qa_fixture["db"].labels.find_one({"id": label["label_id"]}, {"_id": 0, "last_withdrawn_period": 1})
    assert stored_label["last_withdrawn_period"] == "2026-08"


@pytest.mark.anyio
async def test_atomicity_insert_failure_keeps_balance_unchanged_and_no_lock_leak(qa_fixture, monkeypatch, fresh_async_db):
    # Modules/features: adjustment commit atomicity when journal insert fails.
    import routes.royalty_adjustment_mutations as mutations

    label = qa_fixture["create_verified_label"](
        tag="atomic-fail",
        line_specs=[{"period": "2026-07", "label_idr": 600_000, "status": "available", "legacy_settled": False}],
    )
    finance_token = _login(FINANCE)
    finance_headers = _headers(finance_token)
    finance_user = qa_fixture["db"].users.find_one({"email": FINANCE["email"]}, {"_id": 0, "id": 1, "name": 1})

    summary_before = requests.get(f"{API}/royalty/admin/adjustments/labels/{label['label_id']}/summary", headers=finance_headers, timeout=30)
    assert summary_before.status_code == 200, summary_before.text
    before_amount = summary_before.json()["balance_available_idr"]
    preview = _preview(finance_headers, label["label_id"], _adjustment_payload(500_000, reference="ITER63-ATOMIC-FAIL"))

    class FailingBalanceTransactions:
        def __init__(self, real_collection):
            self._real = real_collection

        def __getattr__(self, name):
            return getattr(self._real, name)

        async def find_one(self, *args, **kwargs):
            return await self._real.find_one(*args, **kwargs)

        async def insert_one(self, *args, **kwargs):
            raise RuntimeError("forced insert failure")

    async def failing_insert_one(*args, **kwargs):
        raise RuntimeError("forced insert failure")

    _ = failing_insert_one  # keep explicit callable for debugging hooks
    monkeypatch.setattr(mutations.db, "balance_transactions", FailingBalanceTransactions(mutations.db.balance_transactions))
    with pytest.raises(RuntimeError, match="forced insert failure"):
        await mutations.commit_adjustment(label["label_id"], preview["preview_id"], finance_user)

    summary_after = requests.get(f"{API}/royalty/admin/adjustments/labels/{label['label_id']}/summary", headers=finance_headers, timeout=30)
    assert summary_after.status_code == 200
    assert summary_after.json()["balance_available_idr"] == before_amount
    assert qa_fixture["db"].balance_transactions.count_documents({"id": f"AJ-{preview['preview_id']}"}) == 0
    assert qa_fixture["db"].financial_operation_locks.find_one({"_id": label["label_id"]}) is None


@pytest.mark.anyio
async def test_atomicity_insert_success_refresh_failure_durable_with_replay(qa_fixture, monkeypatch, fresh_async_db):
    # Modules/features: commit durability when post-insert cache refresh fails.
    import routes.royalty_adjustment_mutations as mutations

    label = qa_fixture["create_verified_label"](tag="atomic-durable", line_specs=[])
    finance_headers = _headers(_login(FINANCE))
    finance_user = qa_fixture["db"].users.find_one({"email": FINANCE["email"]}, {"_id": 0, "id": 1, "name": 1})

    preview = _preview(finance_headers, label["label_id"], _adjustment_payload(700_000, reference="ITER63-DURABLE"))
    original_refresh = mutations.refresh_balance_cache

    async def failing_refresh(_label_id: str):
        raise RuntimeError("forced refresh failure")

    monkeypatch.setattr(mutations, "refresh_balance_cache", failing_refresh)
    with pytest.raises(RuntimeError, match="forced refresh failure"):
        await mutations.commit_adjustment(label["label_id"], preview["preview_id"], finance_user)

    inserted = qa_fixture["db"].balance_transactions.count_documents({"id": f"AJ-{preview['preview_id']}"})
    assert inserted == 1
    monkeypatch.setattr(mutations, "refresh_balance_cache", original_refresh)

    replay = _commit(finance_headers, label["label_id"], preview["preview_id"])
    assert replay.status_code == 200, replay.text
    assert replay.json()["replayed"] is True
    assert qa_fixture["db"].balance_transactions.count_documents({"id": f"AJ-{preview['preview_id']}"}) == 1


def test_concurrent_same_preview_and_concurrent_withdraw_double_booking_guard(qa_fixture):
    # Modules/features: concurrent same-preview commit and concurrent withdraw request race guards.
    label = qa_fixture["create_verified_label"](
        tag="concurrent",
        line_specs=[{"period": "2026-09", "label_idr": 1_200_000, "status": "available", "legacy_settled": False}],
    )
    finance_headers = _headers(_login(FINANCE))
    label_headers = _headers(_login({"email": label["user_email"], "password": label["user_password"]}))

    preview = _preview(finance_headers, label["label_id"], _adjustment_payload(500_000, reference="ITER63-CONCURRENT"))
    preview_id = preview["preview_id"]

    def commit_once():
        return _commit(finance_headers, label["label_id"], preview_id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: commit_once(), range(2)))
    statuses = [resp.status_code for resp in responses]
    assert 200 in statuses
    assert all(code in (200, 409) for code in statuses)
    assert qa_fixture["db"].balance_transactions.count_documents({"id": f"AJ-{preview_id}"}) == 1

    def request_withdraw_once():
        return requests.post(f"{API}/withdraw/label/request", headers=label_headers, timeout=30)

    with ThreadPoolExecutor(max_workers=2) as pool:
        wd_responses = list(pool.map(lambda _: request_withdraw_once(), range(2)))
    wd_statuses = sorted([resp.status_code for resp in wd_responses])
    assert wd_statuses == [200, 409]
    assert qa_fixture["db"].withdraw_requests.count_documents({"label_id": label["label_id"], "status": "requested"}) == 1


def test_stale_preview_conflict_then_refresh_preview_succeeds(qa_fixture):
    # Modules/features: stale-preview 409 then refreshed preview success.
    label = qa_fixture["create_verified_label"](tag="stale", line_specs=[])
    finance_headers = _headers(_login(FINANCE))

    a = _preview(finance_headers, label["label_id"], _adjustment_payload(400_000, reference="ITER63-STALE-A"))
    b = _preview(finance_headers, label["label_id"], _adjustment_payload(450_000, reference="ITER63-STALE-B"))

    assert _commit(finance_headers, label["label_id"], a["preview_id"]).status_code == 200
    stale = _commit(finance_headers, label["label_id"], b["preview_id"])
    assert stale.status_code == 409

    fresh = _preview(finance_headers, label["label_id"], _adjustment_payload(450_000, reference="ITER63-STALE-C"))
    fresh_commit = _commit(finance_headers, label["label_id"], fresh["preview_id"])
    assert fresh_commit.status_code == 200


def test_paid_withdraw_guard_query_semantics_ignore_adjustment_only_missing_period():
    # Modules/features: paid-withdraw missing-period guard semantics (adjustment_only excluded).

    label_id = f"iter63-guard-{uuid.uuid4().hex[:8]}"
    db = _db()
    db.labels.insert_one({"id": label_id, "label_name": "Iter63 Guard"})
    db.withdraw_requests.insert_many([
        {"id": f"iter63-wd-a-{uuid.uuid4().hex[:8]}", "label_id": label_id, "status": "paid", "adjustment_only": True, "period_to": None},
        {"id": f"iter63-wd-b-{uuid.uuid4().hex[:8]}", "label_id": label_id, "status": "paid", "adjustment_only": False, "period_to": None},
    ])
    try:
        missing_non_adjustment_only = db.withdraw_requests.count_documents({
            "label_id": label_id,
            "status": "paid",
            "adjustment_only": {"$ne": True},
            "$or": [{"period_to": None}, {"period_to": {"$exists": False}}],
        })
        assert missing_non_adjustment_only == 1
    finally:
        db.withdraw_requests.delete_many({"label_id": label_id})
        db.labels.delete_one({"id": label_id})


def test_finalize_row_expected_available_includes_manual_adjustment():
    # Modules/features: balance_audit._finalize_row expected_available includes manual funds.
    from routes.balance_audit import _finalize_row

    row = {
        "expected_pending_idr": 0,
        "expected_available_source_idr": 300_000,
        "expected_requested_idr": 100_000,
        "admin_adjustment_idr": 800_000,
        "current_pending_idr": 0,
        "current_available_idr": 0,
        "current_requested_idr": 0,
        "stale_cutoff_lines": 0,
        "wrongly_settled_lines": 0,
        "cutoff_needs_sync": False,
        "calculation_mismatch_lines": 0,
        "has_active_withdraw": False,
        "restore_blocked": False,
    }
    result = _finalize_row(row)
    assert result["expected_available_idr"] == 1_000_000


