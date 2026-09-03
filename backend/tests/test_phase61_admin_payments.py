"""Phase 61 — admin payments localization, actionable workflow, and notifications."""
import asyncio
import os
import uuid
from datetime import datetime, timezone

import pymongo
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient

from tests.support_config import (
    CONTENT,
    FINANCE,
    MARKETING,
    RELEASE_ADMIN,
    SUPERADMIN,
    SUPPORT,
)


# Module under test: /api/auth + /api/admin/dashboard + /api/admin/payments + /api/payments/admin/{id}/action
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


def _db():
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


def _token(credentials: dict) -> str:
    response = requests.post(f"{API}/auth/login", json=credentials, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _get_phase61_payment(rows: list[dict], slug: str) -> dict:
    target = next((row for row in rows if slug in (row.get("id") or "") or slug in (row.get("reference_id") or "")), None)
    assert target is not None, f"Fixture {slug} tidak ditemukan"
    return target


def test_superadmin_login_sets_secure_http_only_cookies():
    response = requests.post(f"{API}/auth/login", json=SUPERADMIN, timeout=30)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["user"]["role"] == "super_admin"
    set_cookie = response.headers.get("set-cookie", "")
    lowered = set_cookie.lower()
    assert "httponly" in lowered
    assert "secure" in lowered


def test_dashboard_and_actionable_filter_match_phase61_fixture_baseline():
    token = _token(SUPERADMIN)
    dash = requests.get(f"{API}/admin/dashboard", headers=_headers(token), timeout=30)
    assert dash.status_code == 200, dash.text
    dash_body = dash.json()
    assert "actionable_payments" in dash_body
    assert isinstance(dash_body["actionable_payments"], int)
    assert dash_body["actionable_payments"] == 2

    rows = requests.get(
        f"{API}/admin/payments",
        headers=_headers(token),
        params={"needs_action": "true"},
        timeout=30,
    )
    assert rows.status_code == 200, rows.text
    items = rows.json()
    ids = {row["id"] for row in items}
    assert "phase61-ui-ppr" in ids
    assert "phase61-ui-custom" in ids
    assert "phase61-ui-sub" not in ids
    assert "phase61-ui-pending" not in ids
    for row in items:
        assert row["status"] == "paid"
        assert row["type"] in {"pay_per_release", "custom_service", "wami_addon"}


def test_admin_payments_enrichment_and_no_mongo_objectid():
    token = _token(SUPERADMIN)
    response = requests.get(f"{API}/admin/payments", headers=_headers(token), timeout=30)
    assert response.status_code == 200, response.text
    rows = response.json()
    fixtures = {
        "phase61-ui-ppr": _get_phase61_payment(rows, "phase61-ui-ppr"),
        "phase61-ui-custom": _get_phase61_payment(rows, "phase61-ui-custom"),
        "phase61-ui-sub": _get_phase61_payment(rows, "phase61-ui-sub"),
        "phase61-ui-pending": _get_phase61_payment(rows, "phase61-ui-pending"),
    }
    for row in fixtures.values():
        assert "_id" not in row
        assert row.get("label_name")
        assert "label_email" in row
        assert "payment_method" in row
        assert "admin_action_status" in row
        assert "admin_action_path" in row

    assert fixtures["phase61-ui-ppr"]["admin_action_path"] == "/admin/releases/phase61-ui-release"
    assert fixtures["phase61-ui-ppr"]["admin_action_type"] == "release"
    assert fixtures["phase61-ui-sub"]["admin_action_required"] is False
    assert fixtures["phase61-ui-sub"]["admin_action_status"] == "automatic"


def test_custom_action_phase61_fixture_in_progress_then_completed_and_hidden_from_actionable():
    db = _db()
    token = _token(SUPERADMIN)
    response = requests.get(f"{API}/admin/payments", headers=_headers(token), timeout=30)
    rows = response.json()
    payment = _get_phase61_payment(rows, "phase61-ui-custom")
    payment_id = payment["id"]
    order_id = payment.get("service_order_id")
    assert order_id
    original_order = db.service_orders.find_one({"id": order_id}) or {}
    original_status = original_order.get("status")
    original_payment = db.payments.find_one({"id": payment_id}) or {}
    original_action_status = original_payment.get("admin_action_status")
    try:
        start = requests.post(
            f"{API}/payments/admin/{payment_id}/action",
            headers=_headers(token),
            json={"action": "in_progress"},
            timeout=30,
        )
        assert start.status_code == 200, start.text
        assert start.json()["service_status"] == "in_progress"

        finish = requests.post(
            f"{API}/payments/admin/{payment_id}/action",
            headers=_headers(token),
            json={"action": "completed"},
            timeout=30,
        )
        assert finish.status_code == 200, finish.text
        finish_body = finish.json()
        assert finish_body["service_status"] == "completed"
        assert finish_body["admin_action_required"] is False

        service = db.service_orders.find_one({"id": order_id}, {"_id": 0})
        assert service["status"] == "completed"

        filtered = requests.get(
            f"{API}/admin/payments",
            headers=_headers(token),
            params={"needs_action": "true"},
            timeout=30,
        )
        assert filtered.status_code == 200
        filtered_ids = {row["id"] for row in filtered.json()}
        assert payment_id not in filtered_ids
    finally:
        if original_status:
            db.service_orders.update_one({"id": order_id}, {"$set": {"status": original_status}})
        if original_action_status is not None:
            db.payments.update_one({"id": payment_id}, {"$set": {"admin_action_status": original_action_status}})
        else:
            db.payments.update_one({"id": payment_id}, {"$unset": {"admin_action_status": ""}})


def test_custom_action_role_permissions_and_rejections_for_invalid_target_types():
    db = _db()
    now = datetime.now(timezone.utc).isoformat()
    suffix = uuid.uuid4().hex[:8]
    label_id = f"phase61-role-label-{suffix}"
    service_id = f"phase61-role-service-{suffix}"
    custom_payment_id = f"phase61-role-custom-{suffix}"
    non_custom_id = f"phase61-role-sub-{suffix}"
    unpaid_custom_id = f"phase61-role-custom-unpaid-{suffix}"

    db.labels.insert_one({"id": label_id, "label_name": f"Phase61 Role {suffix}", "created_at": now, "updated_at": now})
    db.service_orders.insert_one({"id": service_id, "label_id": label_id, "name": "Role Service", "status": "paid", "created_at": now, "updated_at": now})
    db.payments.insert_many([
        {
            "id": custom_payment_id,
            "label_id": label_id,
            "service_order_id": service_id,
            "type": "custom_service",
            "description": "Role test custom",
            "amount": 50000,
            "currency": "IDR",
            "status": "paid",
            "reference_id": custom_payment_id,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": non_custom_id,
            "label_id": label_id,
            "type": "annual_subscription",
            "description": "Role test subscription",
            "amount": 350000,
            "currency": "IDR",
            "status": "paid",
            "reference_id": non_custom_id,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": unpaid_custom_id,
            "label_id": label_id,
            "service_order_id": service_id,
            "type": "custom_service",
            "description": "Role test custom unpaid",
            "amount": 50000,
            "currency": "IDR",
            "status": "pending",
            "reference_id": unpaid_custom_id,
            "created_at": now,
            "updated_at": now,
        },
    ])

    finance = _token(FINANCE)
    support = _token(SUPPORT)
    release_admin = _token(RELEASE_ADMIN)
    marketing = _token(MARKETING)
    content = _token(CONTENT)
    super_admin = _token(SUPERADMIN)

    try:
        ok_finance = requests.post(
            f"{API}/payments/admin/{custom_payment_id}/action",
            headers=_headers(finance),
            json={"action": "in_progress"},
            timeout=30,
        )
        assert ok_finance.status_code == 200, ok_finance.text

        ok_support = requests.post(
            f"{API}/payments/admin/{custom_payment_id}/action",
            headers=_headers(support),
            json={"action": "completed"},
            timeout=30,
        )
        assert ok_support.status_code == 200, ok_support.text

        denied_release = requests.post(
            f"{API}/payments/admin/{custom_payment_id}/action",
            headers=_headers(release_admin),
            json={"action": "in_progress"},
            timeout=30,
        )
        assert denied_release.status_code == 403

        denied_marketing = requests.post(
            f"{API}/payments/admin/{custom_payment_id}/action",
            headers=_headers(marketing),
            json={"action": "in_progress"},
            timeout=30,
        )
        assert denied_marketing.status_code == 403

        denied_content = requests.post(
            f"{API}/payments/admin/{custom_payment_id}/action",
            headers=_headers(content),
            json={"action": "in_progress"},
            timeout=30,
        )
        assert denied_content.status_code == 403

        reject_non_custom = requests.post(
            f"{API}/payments/admin/{non_custom_id}/action",
            headers=_headers(super_admin),
            json={"action": "in_progress"},
            timeout=30,
        )
        assert reject_non_custom.status_code == 400

        reject_unpaid_custom = requests.post(
            f"{API}/payments/admin/{unpaid_custom_id}/action",
            headers=_headers(super_admin),
            json={"action": "in_progress"},
            timeout=30,
        )
        assert reject_unpaid_custom.status_code == 400
    finally:
        db.payments.delete_many({"id": {"$in": [custom_payment_id, non_custom_id, unpaid_custom_id]}})
        db.service_orders.delete_many({"id": service_id})
        db.labels.delete_many({"id": label_id})


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_paid_notification_dispatch_is_idempotent_and_persists_provider_method(monkeypatch):
    import payment_service as service

    db = _db()
    motor_client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    monkeypatch.setattr(service, "db", motor_client[os.environ["DB_NAME"]])

    suffix = uuid.uuid4().hex[:10]
    user_id = f"phase61-user-{suffix}"
    label_id = f"phase61-label-{suffix}"
    order_id = f"phase61-service-{suffix}"
    payment_id = f"phase61-pay-{suffix}"
    now = datetime.now(timezone.utc).isoformat()
    label_email = f"phase61-{suffix}@example.com"

    sent = []

    async def fake_label_receipt(*, to: str, **_kwargs):
        sent.append(("label", to))
        return f"msg-label-{len(sent)}"

    async def fake_admin_receipt(*, to: str, **_kwargs):
        sent.append(("admin", to))
        return f"msg-admin-{len(sent)}"

    monkeypatch.setattr(service, "send_payment_receipt_email", fake_label_receipt)
    monkeypatch.setattr(service, "send_admin_paid_payment_email", fake_admin_receipt)

    db.users.insert_one({
        "id": user_id,
        "name": "Phase61 Label User",
        "email": label_email,
        "role": "label",
        "status": "active",
        "email_verified_at": now,
        "token_version": 0,
        "created_at": now,
        "updated_at": now,
    })
    db.labels.insert_one({
        "id": label_id,
        "user_id": user_id,
        "label_name": f"Phase61 Label {suffix}",
        "created_at": now,
        "updated_at": now,
    })
    db.service_orders.insert_one({
        "id": order_id,
        "label_id": label_id,
        "name": "Phase61 Notif Service",
        "status": "unpaid",
        "created_at": now,
        "updated_at": now,
    })
    payment_doc = {
        "id": payment_id,
        "label_id": label_id,
        "service_order_id": order_id,
        "type": "custom_service",
        "description": "Phase61 custom service",
        "amount": 123456,
        "currency": "IDR",
        "status": "pending",
        "provider": "xendit",
        "provider_status": "ACTIVE",
        "reference_id": f"rm-{payment_id}",
        "fulfillment_status": "pending",
        "return_path": "/label/invoices",
        "created_at": now,
        "updated_at": now,
    }
    db.payments.insert_one(dict(payment_doc))

    admin_email_count = db.users.count_documents({
        "role": {"$in": ["super_admin", "admin_finance", "admin_support"]},
        "status": {"$nin": ["disabled", "suspended"]},
        "email": {"$exists": True, "$ne": ""},
    })

    remote_payload = {
        "reference_id": payment_doc["reference_id"],
        "amount": payment_doc["amount"],
        "currency": "IDR",
        "status": "COMPLETED",
        "payment_request_id": f"pr-{suffix}",
        "payment_id": f"py-{suffix}",
        "payment_method": {"channel_code": "VIRTUAL_ACCOUNT"},
    }

    async def scenario():
        first = await service.reconcile_payment(dict(payment_doc), dict(remote_payload))
        assert first["status"] == "paid"
        assert first["fulfillment_status"] == "fulfilled"
        assert first["payment_method"] == "VIRTUAL_ACCOUNT"
        second = await service.reconcile_payment(dict(first), dict(remote_payload))
        assert second["status"] == "paid"
        assert second["payment_method"] == "VIRTUAL_ACCOUNT"
        third = await service.fulfill_payment(dict(second))
        assert third["status"] == "paid"

    try:
        asyncio.run(scenario())
        expected_inapp = 1 + int(admin_email_count)
        expected_email = 1 + int(admin_email_count)
        inapp = db.notifications.count_documents({"event_key": {"$regex": f"^payment-paid:{payment_id}:inapp:"}})
        email_docs = db.payment_notification_deliveries.count_documents({"event_key": {"$regex": f"^payment-paid:{payment_id}:email:"}})
        assert inapp == expected_inapp
        assert email_docs == expected_email
        assert len(sent) == expected_email
    finally:
        motor_client.close()
        db.payment_notification_deliveries.delete_many({"event_key": {"$regex": f"^payment-paid:{payment_id}:"}})
        db.notifications.delete_many({"event_key": {"$regex": f"^payment-paid:{payment_id}:"}})
        db.payments.delete_many({"id": payment_id})
        db.service_orders.delete_many({"id": order_id})
        db.labels.delete_many({"id": label_id})
        db.users.delete_many({"id": user_id})