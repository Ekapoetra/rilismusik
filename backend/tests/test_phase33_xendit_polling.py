"""Phase 33 — production Xendit code paths without creating live transactions."""
import asyncio
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import pymongo
import pytest
import requests
from dotenv import dotenv_values, load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from auth_utils import hash_password
from tests.support_config import SUPERADMIN, temporary_password


load_dotenv("/app/backend/.env", override=True)
FRONTEND_ENV = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or FRONTEND_ENV["REACT_APP_BACKEND_URL"]).rstrip("/")
API = f"{BASE}/api"
SUPER = SUPERADMIN


def _db():
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


def _token(credentials):
    response = requests.post(f"{API}/auth/login", json=credentials, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_session_payload_and_mocked_provider_fulfillment(monkeypatch):
    """Provider HTTP is replaced in-process; this test cannot create a live Xendit session."""
    import payment_service as service

    db = _db()
    motor_client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    monkeypatch.setattr(service, "db", motor_client[os.environ["DB_NAME"]])
    suffix = uuid.uuid4().hex[:10]
    label_id = f"xendit-label-{suffix}"
    release_id = f"xendit-release-{suffix}"
    payment_id = f"xendit-payment-{suffix}"
    now = datetime.now(timezone.utc)
    payment = {
        "id": payment_id, "label_id": label_id, "release_id": release_id,
        "type": "pay_per_release", "description": "Distribusi Test",
        "amount": 35_000, "currency": "IDR", "status": "pending",
        "provider": "xendit", "provider_status": None,
        "reference_id": f"rm-{payment_id}", "xendit_session_id": None,
        "xendit_invoice_url": None, "fulfillment_status": "pending",
        "return_path": f"/label/releases/{release_id}",
        "created_at": now.isoformat(), "updated_at": now.isoformat(),
    }
    db.labels.insert_one({"id": label_id, "label_name": "Xendit Test", "balance_available_idr": 0})
    db.releases.insert_one({"id": release_id, "label_id": label_id, "status": "awaiting_payment", "payment_status": "pending"})
    db.payments.insert_one(dict(payment))

    async def fake_request(method, path, **kwargs):
        assert method == "POST"
        assert path == "/sessions"
        body = kwargs["json"]
        assert body["session_type"] == "PAY"
        assert body["mode"] == "PAYMENT_LINK"
        assert body["amount"] == 35_000
        assert body["currency"] == "IDR"
        assert body["country"] == "ID"
        assert body["success_return_url"].startswith("https://")
        assert "callback" not in " ".join(body.keys()).lower()
        return {
            "payment_session_id": f"ps-{suffix}", "payment_link_url": f"https://checkout.xendit.co/{suffix}",
            "reference_id": body["reference_id"], "amount": body["amount"], "currency": "IDR",
            "status": "ACTIVE", "expires_at": (now + timedelta(minutes=30)).isoformat(),
        }

    async def no_receipt(_payment):
        return None

    async def no_notify(*_args, **_kwargs):
        return None

    async def no_label_users(_label_id):
        return []

    monkeypatch.setattr(service, "_xendit_request", fake_request)
    monkeypatch.setattr(service, "_send_receipt", no_receipt)
    monkeypatch.setattr(service, "notify_many", no_notify)
    monkeypatch.setattr(service, "label_user_ids", no_label_users)

    async def scenario():
        created = await service.create_xendit_session(payment)
        assert created["xendit_session_id"] == f"ps-{suffix}"
        remote = {
            "payment_session_id": f"ps-{suffix}", "reference_id": payment["reference_id"],
            "amount": 35_000, "currency": "IDR", "status": "COMPLETED",
            "payment_request_id": f"pr-{suffix}", "payment_id": f"py-{suffix}",
        }
        paid = await service.reconcile_payment(created, remote)
        assert paid["status"] == "paid"
        assert paid["fulfillment_status"] == "fulfilled"
        again = await service.reconcile_payment(paid, remote)
        assert again["fulfillment_status"] == "fulfilled"

    try:
        asyncio.run(scenario())
        release = db.releases.find_one({"id": release_id})
        assert release["status"] == "under_review"
        assert release["payment_status"] == "paid"
        assert release["fulfilled_payment_ids"] == [payment_id]
        stored = db.payments.find_one({"id": payment_id})
        assert stored["payment_request_id"] == f"pr-{suffix}"
        assert stored["payment_id_provider"] == f"py-{suffix}"
    finally:
        motor_client.close()
        db.labels.delete_many({"id": label_id})
        db.releases.delete_many({"id": release_id})
        db.payments.delete_many({"id": payment_id})
        db.notifications.delete_many({"meta.payment_id": payment_id})


def test_custom_product_and_local_invoices_do_not_call_xendit():
    db = _db()
    suffix = uuid.uuid4().hex[:10]
    user_id = f"xendit-user-{suffix}"
    label_id = f"xendit-label-{suffix}"
    email = f"xendit-{suffix}@example.com"
    password = temporary_password("phase33")
    now = datetime.now(timezone.utc).isoformat()
    db.users.insert_one({
        "id": user_id, "name": "Xendit Label", "email": email,
        "password_hash": hash_password(password), "role": "label", "status": "active",
        "email_verified_at": now, "token_version": 0, "created_at": now, "updated_at": now,
    })
    db.labels.insert_one({
        "id": label_id, "user_id": user_id, "label_name": f"Xendit Label {suffix}",
        "account_status": "active", "subscription_status": "inactive",
        "created_at": now, "updated_at": now,
    })
    product_id = None
    try:
        super_token = _token(SUPER)
        response = requests.post(
            f"{API}/payments/admin/products",
            json={"name": f"Layanan Test {suffix}", "description": "Tidak memanggil provider", "amount": 12_345, "active": True},
            headers=_headers(super_token), timeout=30,
        )
        assert response.status_code == 200, response.text
        product_id = response.json()["id"]

        label_token = _token({"email": email, "password": password})
        config = requests.get(f"{API}/payments/config", headers=_headers(label_token), timeout=30)
        assert config.status_code == 200
        assert config.json() == {"provider": "xendit", "mode": "production_polling", "configured": True, "webhook_required": False}

        products = requests.get(f"{API}/payments/products", headers=_headers(label_token), timeout=30).json()
        assert any(row["id"] == product_id for row in products)

        service_invoice = requests.post(
            f"{API}/payments/service/{product_id}", json={}, headers=_headers(label_token), timeout=30,
        )
        assert service_invoice.status_code == 200, service_invoice.text
        assert service_invoice.json()["status"] == "pending"
        assert service_invoice.json().get("xendit_session_id") is None

        subscription = requests.post(
            f"{API}/payments/subscription", json={"tier": "annual_vip"},
            headers=_headers(label_token), timeout=30,
        )
        assert subscription.status_code == 200, subscription.text
        assert subscription.json()["status"] == "pending"
        assert subscription.json().get("xendit_session_id") is None

        mock = requests.post(
            f"{API}/payments/{subscription.json()['id']}/mock-pay",
            headers=_headers(label_token), timeout=30,
        )
        assert mock.status_code == 404

        webhook = requests.post(f"{API}/payments/webhook/xendit", json={}, timeout=30)
        assert webhook.status_code == 410
    finally:
        db.payment_products.delete_many({"id": product_id})
        db.service_orders.delete_many({"label_id": label_id})
        db.payments.delete_many({"label_id": label_id})
        db.labels.delete_many({"id": label_id})
        db.users.delete_many({"id": user_id})


def test_completed_amount_mismatch_is_rejected(monkeypatch):
    import payment_service as service
    payment = {
        "id": "local-test", "label_id": "label-test", "type": "custom_service",
        "amount": 10_000, "currency": "IDR", "reference_id": "rm-local-test",
    }
    remote = {"status": "COMPLETED", "amount": 9_000, "currency": "IDR", "reference_id": "rm-local-test"}
    with pytest.raises(Exception) as exc:
        asyncio.run(service.reconcile_payment(payment, remote))
    assert "Nominal" in str(exc.value)


def test_subscription_wami_and_custom_service_fulfillment_are_idempotent(monkeypatch):
    import payment_service as service

    db = _db()
    motor_client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    monkeypatch.setattr(service, "db", motor_client[os.environ["DB_NAME"]])
    suffix = uuid.uuid4().hex[:10]
    label_id = f"xendit-all-label-{suffix}"
    expiry = datetime.now(timezone.utc) + timedelta(days=30)
    sub_id = f"sub-{suffix}"
    wami_payment_id = f"wami-pay-{suffix}"
    custom_payment_id = f"custom-pay-{suffix}"
    wami_order_id = f"wami-order-{suffix}"
    service_order_id = f"service-order-{suffix}"

    async def no_receipt(_payment):
        return None

    async def no_notify(*_args, **_kwargs):
        return None

    async def no_label_users(_label_id):
        return []

    monkeypatch.setattr(service, "_send_receipt", no_receipt)
    monkeypatch.setattr(service, "notify_many", no_notify)
    monkeypatch.setattr(service, "label_user_ids", no_label_users)
    db.labels.insert_one({
        "id": label_id, "label_name": "All Products", "subscription_status": "active",
        "subscription_expires_at": expiry.isoformat(), "fulfilled_payment_ids": [],
    })
    db.wami_orders.insert_one({"id": wami_order_id, "label_id": label_id, "status": "unpaid"})
    db.service_orders.insert_one({"id": service_order_id, "label_id": label_id, "status": "unpaid"})
    payments = [
        {"id": sub_id, "type": "annual_subscription", "tier": "annual_vip", "amount": 500_000},
        {"id": wami_payment_id, "type": "wami_addon", "wami_order_id": wami_order_id, "amount": 100_000},
        {"id": custom_payment_id, "type": "custom_service", "service_order_id": service_order_id, "amount": 75_000},
    ]
    for payment in payments:
        payment.update({
            "label_id": label_id, "currency": "IDR", "status": "pending",
            "reference_id": f"rm-{payment['id']}", "fulfillment_status": "pending",
            "description": payment["type"], "return_path": "/label/invoices",
        })
    db.payments.insert_many(payments)

    async def scenario():
        for payment in payments:
            remote = {
                "reference_id": payment["reference_id"], "amount": payment["amount"],
                "currency": "IDR", "status": "COMPLETED",
            }
            paid = await service.reconcile_payment(dict(payment), remote)
            assert paid["fulfillment_status"] == "fulfilled"
            repeated = await service.reconcile_payment(paid, remote)
            assert repeated["fulfillment_status"] == "fulfilled"

    try:
        asyncio.run(scenario())
        label = db.labels.find_one({"id": label_id})
        expected_expiry = expiry + timedelta(days=365)
        actual_expiry = datetime.fromisoformat(label["subscription_expires_at"])
        assert abs((actual_expiry - expected_expiry).total_seconds()) < 2
        assert label["subscription_tier"] == "annual_vip"
        assert label["fulfilled_payment_ids"] == [sub_id]
        assert db.wami_orders.find_one({"id": wami_order_id})["status"] == "pending"
        assert db.wami_orders.find_one({"id": wami_order_id})["fulfilled_payment_ids"] == [wami_payment_id]
        assert db.service_orders.find_one({"id": service_order_id})["status"] == "paid"
        assert db.service_orders.find_one({"id": service_order_id})["fulfilled_payment_ids"] == [custom_payment_id]
    finally:
        motor_client.close()
        db.labels.delete_many({"id": label_id})
        db.wami_orders.delete_many({"id": wami_order_id})
        db.service_orders.delete_many({"id": service_order_id})
        db.payments.delete_many({"id": {"$in": [sub_id, wami_payment_id, custom_payment_id]}})