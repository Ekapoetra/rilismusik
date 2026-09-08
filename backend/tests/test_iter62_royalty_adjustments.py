"""Iter 62 — royalty admin adjustment + withdrawal integration regression."""

import os
import uuid
from datetime import datetime, timedelta, timezone

import pymongo
import pytest
import requests
from dotenv import load_dotenv

from auth_utils import hash_password
from tests.support_config import FINANCE, RELEASE_ADMIN, SUPERADMIN, SUPPORT, temporary_password


load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/frontend/.env", override=True)

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def _login(account: dict) -> str:
    response = requests.post(f"{API}/auth/login", json=account, timeout=30)
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture()
def sandbox():
    """royalty-adjustment + withdraw modules: isolated QA fixture/cleanup helper."""
    db = _db()
    created = {
        "label_ids": [],
        "user_ids": [],
        "user_emails": [],
        "contract_ids": [],
        "bank_ids": [],
        "kyc_ids": [],
        "line_ids": [],
        "withdraw_ids": [],
        "preview_ids": [],
        "role_ids": [],
        "admin_user_ids": [],
        "admin_user_emails": [],
    }

    def create_verified_label(*, tag: str, line_specs: list[dict] | None = None):
        suffix = uuid.uuid4().hex[:8]
        now = datetime.now(timezone.utc).isoformat()
        user_id = f"iter62-user-{tag}-{suffix}"
        label_id = f"iter62-label-{tag}-{suffix}"
        label_name = f"Iter62 {tag} {suffix}"
        email = f"iter62-{tag}-{suffix}@example.com"
        password = temporary_password("Iter62Label")
        bank_id = f"iter62-bank-{tag}-{suffix}"
        contract_id = f"iter62-contract-{tag}-{suffix}"
        kyc_id = f"iter62-kyc-{tag}-{suffix}"

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
            "address": "Jl. Test QA 62",
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
            "account_number": f"12345{suffix}",
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

        line_ids = []
        for index, spec in enumerate(line_specs or []):
            line_id = f"iter62-line-{tag}-{suffix}-{index}"
            line_ids.append(line_id)
            db.royalty_lines.insert_one({
                "id": line_id,
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
        created["line_ids"].extend(line_ids)
        return {
            "label_id": label_id,
            "label_name": label_name,
            "user_email": email,
            "user_password": password,
            "line_ids": line_ids,
        }

    yield {"db": db, "created": created, "create_verified_label": create_verified_label}

    financial_refs = [item["id"] for item in db.balance_transactions.find(
        {"label_id": {"$in": created["label_ids"]}}, {"_id": 0, "id": 1},
    )]
    withdrawal_refs = [item["id"] for item in db.withdraw_requests.find(
        {"label_id": {"$in": created["label_ids"]}}, {"_id": 0, "id": 1},
    )]
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
    db.activity_logs.delete_many({"$or": [
        {"reference_id": {"$in": financial_refs + withdrawal_refs + created["label_ids"] + created["admin_user_ids"] + created["role_ids"]}},
        {"user_id": {"$in": created["admin_user_ids"] + created["user_ids"]}},
    ]})
    if created["admin_user_ids"]:
        db.users.delete_many({"id": {"$in": created["admin_user_ids"]}})
    if created["admin_user_emails"]:
        db.users.delete_many({"email": {"$in": created["admin_user_emails"]}})
    if created["role_ids"]:
        db.admin_roles.delete_many({"id": {"$in": created["role_ids"]}})


def _preview(headers: dict, label_id: str, payload: dict, expected: int = 200):
    response = requests.post(
        f"{API}/royalty/admin/adjustments/labels/{label_id}/preview",
        headers=headers,
        json=payload,
        timeout=30,
    )
    assert response.status_code == expected, response.text
    return response


def _commit(headers: dict, label_id: str, preview_id: str, expected: int = 200):
    response = requests.post(
        f"{API}/royalty/admin/adjustments/labels/{label_id}",
        headers=headers,
        json={"preview_id": preview_id},
        timeout=30,
    )
    assert response.status_code == expected, response.text
    return response


# auth + permission coverage for the new adjustment router
def test_adjustment_permissions_and_custom_royalty_manage_role(sandbox):
    db = sandbox["db"]
    created = sandbox["created"]

    unauth = requests.get(f"{API}/royalty/admin/adjustments/labels", timeout=30)
    assert unauth.status_code == 401

    support_headers = _headers(_login(SUPPORT))
    release_headers = _headers(_login(RELEASE_ADMIN))
    finance_headers = _headers(_login(FINANCE))
    assert requests.get(f"{API}/royalty/admin/adjustments/labels", headers=support_headers, timeout=30).status_code == 403
    assert requests.get(f"{API}/royalty/admin/adjustments/labels", headers=release_headers, timeout=30).status_code == 403
    assert requests.get(f"{API}/royalty/admin/adjustments/labels", headers=finance_headers, timeout=30).status_code == 200

    super_headers = _headers(_login(SUPERADMIN))
    suffix = uuid.uuid4().hex[:8]
    role_resp = requests.post(
        f"{API}/admin/access/roles",
        headers=super_headers,
        json={"name": f"Iter62 Royalty Manage {suffix}", "permissions": ["royalty.manage"]},
        timeout=30,
    )
    assert role_resp.status_code == 200, role_resp.text
    role_id = role_resp.json()["id"]
    created["role_ids"].append(role_id)

    admin_email = f"iter62-admin-{suffix}@example.com"
    admin_password = temporary_password("Iter62Admin")
    user_resp = requests.post(
        f"{API}/admin/admin-users",
        headers=super_headers,
        json={"name": "Iter62 Royalty Admin", "email": admin_email, "password": admin_password, "admin_role_id": role_id},
        timeout=30,
    )
    assert user_resp.status_code == 200, user_resp.text
    created["admin_user_ids"].append(user_resp.json()["id"])
    created["admin_user_emails"].append(admin_email)

    custom_headers = _headers(_login({"email": admin_email, "password": admin_password}))
    assert requests.get(f"{API}/royalty/admin/adjustments/labels", headers=custom_headers, timeout=30).status_code == 200
    assert requests.get(f"{API}/admin/labels", headers=custom_headers, timeout=30).status_code == 403
    nav = requests.get(f"{API}/admin/navigation", headers=custom_headers, timeout=30)
    assert nav.status_code == 200, nav.text
    nav_keys = {item.get("key") for item in nav.json().get("items", [])}
    assert "royalty_adjustments" in nav_keys


# source split and boundary behavior for legacy vs current royalty
def test_source_summary_boundary_and_exclusion_rules(sandbox):
    finance_headers = _headers(_login(FINANCE))
    label = sandbox["create_verified_label"](
        tag="summary",
        line_specs=[
            {"period": "2026-05", "label_idr": 200_000, "status": "available", "legacy_settled": True},
            {"period": "2026-06", "label_idr": 900_000, "status": "available", "legacy_settled": False},
            {"period": "2026-07", "label_idr": 300_000, "status": "available", "legacy_settled": False},
            {"period": "2026-07", "label_idr": 111_000, "status": "withdrawn", "legacy_settled": False},
        ],
    )

    split = requests.get(
        f"{API}/royalty/admin/adjustments/labels/{label['label_id']}/summary",
        headers=finance_headers,
        params={"legacy_period_to": "2026-06"},
        timeout=30,
    )
    assert split.status_code == 200, split.text
    body = split.json()
    assert body["legacy_period_to"] == "2026-06"
    assert body["believe_legacy_idr"] == 900_000
    assert body["new_royalty_idr"] == 300_000
    assert body["admin_adjustment_idr"] == 0
    assert body["balance_available_idr"] == 1_200_000

    unclassified = requests.get(
        f"{API}/royalty/admin/adjustments/labels/{label['label_id']}/summary",
        headers=finance_headers,
        timeout=30,
    )
    assert unclassified.status_code == 200, unclassified.text
    free = unclassified.json()
    assert free["legacy_period_to"] is None
    assert free["believe_legacy_idr"] is None
    assert free["new_royalty_idr"] is None
    assert free["unclassified_csv_idr"] == 1_200_000


# preview/commit idempotency and adjustment-only withdrawal redaction
def test_preview_commit_idempotency_and_adjustment_only_withdraw_flow(sandbox):
    db = sandbox["db"]
    finance_headers = _headers(_login(FINANCE))
    label = sandbox["create_verified_label"](tag="adjust-only", line_specs=[])
    label_headers = _headers(_login({"email": label["user_email"], "password": label["user_password"]}))

    before_lines = db.royalty_lines.count_documents({"label_id": label["label_id"]})
    payload = {
        "amount_idr": 1_000_001,
        "currency": "IDR",
        "adjustment_type": "LEGACY_RECONCILIATION",
        "reason": "QA reconcile legacy deficit",
        "reference": "QA-ITER62-ADJ-ONLY",
        "legacy_period_to": "2026-06",
        "reference_amount_idr": 1_000_001,
    }
    preview = _preview(finance_headers, label["label_id"], payload).json()
    assert preview["balance_before_idr"] == 0
    assert preview["balance_after_idr"] == 1_000_001
    assert db.balance_transactions.count_documents({"label_id": label["label_id"], "type": "royalty_admin_adjustment"}) == 0

    first = _commit(finance_headers, label["label_id"], preview["preview_id"]).json()
    assert first["replayed"] is False
    assert first["balance_available_idr"] == 1_000_001
    tx = db.balance_transactions.find_one({"_id": f"AJ-{preview['preview_id']}"}, {"_id": 0})
    assert tx["id"] == f"AJ-{preview['preview_id']}"
    assert tx["source"] == "ADMIN_ADJUSTMENT"
    assert tx["type"] == "royalty_admin_adjustment"
    assert tx["amount_idr"] == 1_000_001
    assert tx["status"] == "active"
    assert tx["reason"] == payload["reason"]
    assert tx["reference"] == payload["reference"]
    assert tx["legacy_period_to"] == "2026-06"
    assert db.royalty_lines.count_documents({"label_id": label["label_id"]}) == before_lines

    replay = _commit(finance_headers, label["label_id"], preview["preview_id"]).json()
    assert replay["replayed"] is True
    assert db.balance_transactions.count_documents({"_id": f"AJ-{preview['preview_id']}"}) == 1

    computed = requests.get(f"{API}/withdraw/label/computed", headers=label_headers, timeout=30)
    assert computed.status_code == 200, computed.text
    computed_json = computed.json()
    assert computed_json["withdrawable_idr"] == 1_000_001
    assert computed_json["can_withdraw"] is True
    assert "adjustment_ids" not in computed_json
    assert "adjustment_amount_idr" not in computed_json

    wd_create = requests.post(f"{API}/withdraw/label/request", headers=label_headers, timeout=30)
    assert wd_create.status_code == 200, wd_create.text
    wd = wd_create.json()
    assert wd["amount_idr"] == 1_000_001
    assert wd["period_from"] is None and wd["period_to"] is None
    assert "adjustment_ids" not in wd and "adjustment_amount_idr" not in wd and "royalty_amount_idr" not in wd

    stored = db.withdraw_requests.find_one({"id": wd["id"]}, {"_id": 0})
    assert stored["adjustment_only"] is True
    assert stored["adjustment_amount_idr"] == 1_000_001
    assert stored["royalty_amount_idr"] == 0

    reject = requests.post(
        f"{API}/withdraw/admin/{wd['id']}/action",
        headers=finance_headers,
        json={"action": "reject", "note": "iter62 reject for void check"},
        timeout=30,
    )
    assert reject.status_code == 200, reject.text

    recomputed = requests.get(f"{API}/withdraw/label/computed", headers=label_headers, timeout=30)
    assert recomputed.status_code == 200, recomputed.text
    assert recomputed.json()["withdrawable_idr"] == 1_000_001


# strict threshold behavior: exactly 1,000,000 denied, +1 accepted
def test_threshold_strictly_greater_than_one_million(sandbox):
    finance_headers = _headers(_login(FINANCE))
    label = sandbox["create_verified_label"](
        tag="threshold",
        line_specs=[{"period": "2026-07", "label_idr": 1_000_000, "status": "available", "legacy_settled": False}],
    )
    label_headers = _headers(_login({"email": label["user_email"], "password": label["user_password"]}))

    before = requests.get(f"{API}/withdraw/label/computed", headers=label_headers, timeout=30)
    assert before.status_code == 200, before.text
    assert before.json()["withdrawable_idr"] == 1_000_000
    assert before.json()["can_withdraw"] is False

    payload = {
        "amount_idr": 1,
        "currency": "IDR",
        "adjustment_type": "LEGACY_RECONCILIATION",
        "reason": "Top up one rupiah threshold",
        "reference": "ITER62-THRESHOLD-1",
        "legacy_period_to": "2026-06",
        "reference_amount_idr": 1_000_001,
    }
    preview = _preview(finance_headers, label["label_id"], payload).json()
    _commit(finance_headers, label["label_id"], preview["preview_id"])  # assert inside helper

    after = requests.get(f"{API}/withdraw/label/computed", headers=label_headers, timeout=30)
    assert after.status_code == 200, after.text
    assert after.json()["withdrawable_idr"] == 1_000_001
    assert after.json()["can_withdraw"] is True


# schema validation and anti-tamper checks for preview/commit payloads
def test_preview_validation_and_tampered_commit_rejections(sandbox):
    finance_headers = _headers(_login(FINANCE))
    label = sandbox["create_verified_label"](tag="validations", line_specs=[])

    valid = {
        "amount_idr": 100,
        "currency": "IDR",
        "adjustment_type": "LEGACY_RECONCILIATION",
        "reason": "Valid reason for preview",
        "reference": "VAL-ITER62",
        "legacy_period_to": "2026-06",
        "reference_amount_idr": 100,
    }
    invalid_payloads = [
        {**valid, "amount_idr": 0},
        {**valid, "amount_idr": -1},
        {**valid, "amount_idr": 1.5},
        {**valid, "amount_idr": True},
        {**valid, "amount_idr": "100"},
        {**valid, "currency": "USD"},
        {**valid, "reason": "    "},
        {**valid, "reference": "  "},
        {**valid, "legacy_period_to": "2026/06"},
    ]
    for payload in invalid_payloads:
        response = requests.post(
            f"{API}/royalty/admin/adjustments/labels/{label['label_id']}/preview",
            headers=finance_headers,
            json=payload,
            timeout=30,
        )
        assert response.status_code == 422, response.text

    preview = _preview(finance_headers, label["label_id"], valid).json()
    tampered = requests.post(
        f"{API}/royalty/admin/adjustments/labels/{label['label_id']}",
        headers=finance_headers,
        json={"preview_id": preview["preview_id"], "amount_idr": 200},
        timeout=30,
    )
    assert tampered.status_code == 422, tampered.text


# stale/expired/cross-admin and wrong-label protections for commit
def test_stale_expired_cross_admin_and_wrong_label_guards(sandbox):
    db = sandbox["db"]
    finance_headers = _headers(_login(FINANCE))
    super_headers = _headers(_login(SUPERADMIN))
    label = sandbox["create_verified_label"](tag="guards", line_specs=[])
    other = sandbox["create_verified_label"](tag="guards2", line_specs=[])

    payload = {
        "amount_idr": 500_000,
        "currency": "IDR",
        "adjustment_type": "LEGACY_RECONCILIATION",
        "reason": "First preview for stale guard",
        "reference": "ITER62-GUARD-A",
        "legacy_period_to": "2026-06",
    }
    preview_a = _preview(finance_headers, label["label_id"], payload).json()
    preview_b = _preview(finance_headers, label["label_id"], {**payload, "reference": "ITER62-GUARD-B"}).json()
    _commit(finance_headers, label["label_id"], preview_a["preview_id"])  # first commit

    stale = requests.post(
        f"{API}/royalty/admin/adjustments/labels/{label['label_id']}",
        headers=finance_headers,
        json={"preview_id": preview_b["preview_id"]},
        timeout=30,
    )
    assert stale.status_code == 409, stale.text

    preview_c = _preview(finance_headers, label["label_id"], {**payload, "reference": "ITER62-GUARD-C"}).json()
    cross_admin = requests.post(
        f"{API}/royalty/admin/adjustments/labels/{label['label_id']}",
        headers=super_headers,
        json={"preview_id": preview_c["preview_id"]},
        timeout=30,
    )
    assert cross_admin.status_code == 403, cross_admin.text

    wrong_label = requests.post(
        f"{API}/royalty/admin/adjustments/labels/{other['label_id']}",
        headers=finance_headers,
        json={"preview_id": preview_c["preview_id"]},
        timeout=30,
    )
    assert wrong_label.status_code == 404, wrong_label.text

    db.royalty_adjustment_previews.update_one(
        {"_id": preview_c["preview_id"]},
        {"$set": {"expires_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()}},
    )
    expired = requests.post(
        f"{API}/royalty/admin/adjustments/labels/{label['label_id']}",
        headers=finance_headers,
        json={"preview_id": preview_c["preview_id"]},
        timeout=30,
    )
    assert expired.status_code == 409, expired.text


# lock behavior: active withdraw blocks preview/void; reject restores and allows void
def test_active_withdraw_blocks_adjustment_actions_until_rejected(sandbox):
    finance_headers = _headers(_login(FINANCE))
    label = sandbox["create_verified_label"](
        tag="void",
        line_specs=[{"period": "2026-07", "label_idr": 1_500_000, "status": "available", "legacy_settled": False}],
    )
    label_headers = _headers(_login({"email": label["user_email"], "password": label["user_password"]}))

    payload = {
        "amount_idr": 100_000,
        "currency": "IDR",
        "adjustment_type": "LEGACY_RECONCILIATION",
        "reason": "Void scenario setup",
        "reference": "ITER62-VOID-SETUP",
        "legacy_period_to": "2026-06",
    }
    preview = _preview(finance_headers, label["label_id"], payload).json()
    created = _commit(finance_headers, label["label_id"], preview["preview_id"]).json()
    adjustment_id = created["adjustment"]["id"]

    wd_create = requests.post(f"{API}/withdraw/label/request", headers=label_headers, timeout=30)
    assert wd_create.status_code == 200, wd_create.text
    wd_id = wd_create.json()["id"]

    blocked_preview = requests.post(
        f"{API}/royalty/admin/adjustments/labels/{label['label_id']}/preview",
        headers=finance_headers,
        json={
            "amount_idr": 10_000,
            "currency": "IDR",
            "adjustment_type": "LEGACY_RECONCILIATION",
            "reason": "Should block while active withdraw",
            "reference": "ITER62-BLOCKED",
            "legacy_period_to": "2026-06",
        },
        timeout=30,
    )
    assert blocked_preview.status_code == 409, blocked_preview.text

    blocked_void = requests.post(
        f"{API}/royalty/admin/adjustments/labels/{label['label_id']}/{adjustment_id}/void",
        headers=finance_headers,
        json={"reason": "Need to void while active"},
        timeout=30,
    )
    assert blocked_void.status_code == 409, blocked_void.text

    reject = requests.post(
        f"{API}/withdraw/admin/{wd_id}/action",
        headers=finance_headers,
        json={"action": "reject", "note": "iter62 unlock"},
        timeout=30,
    )
    assert reject.status_code == 200, reject.text

    voided = requests.post(
        f"{API}/royalty/admin/adjustments/labels/{label['label_id']}/{adjustment_id}/void",
        headers=finance_headers,
        json={"reason": "Correction after rejection"},
        timeout=30,
    )
    assert voided.status_code == 200, voided.text
    assert voided.json()["adjustment"]["status"] == "voided"
    assert voided.json()["balance_available_idr"] == 1_500_000

    repeat_void = requests.post(
        f"{API}/royalty/admin/adjustments/labels/{label['label_id']}/{adjustment_id}/void",
        headers=finance_headers,
        json={"reason": "Repeated request"},
        timeout=30,
    )
    assert repeat_void.status_code == 200, repeat_void.text
    assert repeat_void.json()["replayed"] is True
    assert repeat_void.json()["adjustment"]["status"] == "voided"


# no hard-delete mutation route exists for adjustments (audit immutability)
def test_adjustment_patch_delete_not_allowed(sandbox):
    finance_headers = _headers(_login(FINANCE))
    label = sandbox["create_verified_label"](tag="methods", line_specs=[])

    patch_resp = requests.patch(
        f"{API}/royalty/admin/adjustments/labels/{label['label_id']}",
        headers=finance_headers,
        json={"status": "voided"},
        timeout=30,
    )
    delete_resp = requests.delete(
        f"{API}/royalty/admin/adjustments/labels/{label['label_id']}",
        headers=finance_headers,
        timeout=30,
    )
    assert patch_resp.status_code in (405, 404)
    assert delete_resp.status_code in (405, 404)