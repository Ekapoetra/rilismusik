"""Phase 33 safe API checks (no checkout/provider calls)."""
import os
import uuid
from datetime import datetime, timezone

import pymongo
import pytest
import requests
from dotenv import dotenv_values, load_dotenv

from auth_utils import hash_password


load_dotenv("/app/backend/.env", override=True)
FRONTEND_ENV = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or FRONTEND_ENV["REACT_APP_BACKEND_URL"]).rstrip("/")
API = f"{BASE}/api"


def _db():
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


def _token(email: str, password: str) -> str:
    response = requests.post(
        f"{API}/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _headers(token: str):
    return {"Authorization": f"Bearer {token}"}


# payments config + disabled endpoints + ownership/poll access
def test_config_disabled_endpoints_and_ownership_access_without_checkout():
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc).isoformat()

    users = [
        {
            "id": f"x33-u1-{suffix}",
            "email": f"x33a-{suffix}@example.com",
            "password": "X33Safe#2026A",
            "name": "X33 Label A",
        },
        {
            "id": f"x33-u2-{suffix}",
            "email": f"x33b-{suffix}@example.com",
            "password": "X33Safe#2026B",
            "name": "X33 Label B",
        },
    ]
    labels = [
        {"id": f"x33-l1-{suffix}", "user_id": users[0]["id"], "label_name": f"X33 Label A {suffix}"},
        {"id": f"x33-l2-{suffix}", "user_id": users[1]["id"], "label_name": f"X33 Label B {suffix}"},
    ]
    payment_id = f"x33-pay-{suffix}"

    try:
        for u in users:
            db.users.insert_one(
                {
                    "id": u["id"],
                    "name": u["name"],
                    "email": u["email"],
                    "password_hash": hash_password(u["password"]),
                    "role": "label",
                    "status": "active",
                    "email_verified_at": now,
                    "token_version": 0,
                    "created_at": now,
                    "updated_at": now,
                }
            )
        for l in labels:
            db.labels.insert_one(
                {
                    **l,
                    "account_status": "active",
                    "subscription_status": "inactive",
                    "created_at": now,
                    "updated_at": now,
                }
            )

        db.payments.insert_one(
            {
                "id": payment_id,
                "label_id": labels[0]["id"],
                "type": "annual_subscription",
                "tier": "annual_vip",
                "description": "X33 invoice",
                "amount": 500_000,
                "currency": "IDR",
                "status": "pending",
                "provider": "xendit",
                "provider_status": None,
                "reference_id": f"rm-{payment_id}",
                "xendit_session_id": None,
                "xendit_invoice_url": None,
                "fulfillment_status": "pending",
                "return_path": "/label/invoices",
                "created_at": now,
                "updated_at": now,
            }
        )

        token_a = _token(users[0]["email"], users[0]["password"])
        token_b = _token(users[1]["email"], users[1]["password"])
        token_finance = _token("finance1@rilismusik.com", "Finance#2026")
        token_super = _token("superadmin@rilismusik.com", "SuperAdmin#2026")

        config = requests.get(f"{API}/payments/config", headers=_headers(token_a), timeout=30)
        assert config.status_code == 200
        body = config.json()
        assert body == {
            "provider": "xendit",
            "mode": "production_polling",
            "configured": True,
            "webhook_required": False,
        }
        serialized = str(body).lower()
        assert "secret" not in serialized
        assert "token" not in serialized

        status_owner = requests.get(f"{API}/payments/{payment_id}/status", headers=_headers(token_a), timeout=30)
        assert status_owner.status_code == 200
        assert status_owner.json()["payment_id"] == payment_id
        assert status_owner.json()["status"] == "pending"

        status_other = requests.get(f"{API}/payments/{payment_id}/status", headers=_headers(token_b), timeout=30)
        assert status_other.status_code == 404

        status_finance = requests.get(f"{API}/payments/{payment_id}/status", headers=_headers(token_finance), timeout=30)
        assert status_finance.status_code == 200
        assert status_finance.json()["payment_id"] == payment_id

        status_super = requests.get(f"{API}/payments/{payment_id}/status", headers=_headers(token_super), timeout=30)
        assert status_super.status_code == 200

        mock_pay = requests.post(f"{API}/payments/{payment_id}/mock-pay", headers=_headers(token_a), timeout=30)
        assert mock_pay.status_code == 404

        webhook = requests.post(f"{API}/payments/webhook/xendit", json={}, timeout=30)
        assert webhook.status_code == 410
    finally:
        db.payments.delete_many({"id": payment_id})
        db.labels.delete_many({"id": {"$in": [labels[0]["id"], labels[1]["id"]]}})
        db.users.delete_many({"id": {"$in": [users[0]["id"], users[1]["id"]]}})


# product CRUD + service/subscription invoice creation without xendit session
def test_custom_product_and_invoice_creation_are_local_and_objectid_hidden():
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc).isoformat()

    user_id = f"x33-u3-{suffix}"
    label_id = f"x33-l3-{suffix}"
    email = f"x33c-{suffix}@example.com"
    password = "X33Safe#2026C"
    product_id = None

    try:
        db.users.insert_one(
            {
                "id": user_id,
                "name": "X33 Label C",
                "email": email,
                "password_hash": hash_password(password),
                "role": "label",
                "status": "active",
                "email_verified_at": now,
                "token_version": 0,
                "created_at": now,
                "updated_at": now,
            }
        )
        db.labels.insert_one(
            {
                "id": label_id,
                "user_id": user_id,
                "label_name": f"X33 Label C {suffix}",
                "account_status": "active",
                "subscription_status": "inactive",
                "created_at": now,
                "updated_at": now,
            }
        )

        token_finance = _token("finance1@rilismusik.com", "Finance#2026")
        token_label = _token(email, password)

        create_product = requests.post(
            f"{API}/payments/admin/products",
            headers=_headers(token_finance),
            json={
                "name": f"X33 Service {suffix}",
                "description": "safe local invoice",
                "amount": 22222,
                "active": True,
            },
            timeout=30,
        )
        assert create_product.status_code == 200, create_product.text
        created = create_product.json()
        product_id = created["id"]
        assert "_id" not in created
        assert created["amount"] == 22222

        updated = requests.patch(
            f"{API}/payments/admin/products/{product_id}",
            headers=_headers(token_finance),
            json={"amount": 33333, "active": True},
            timeout=30,
        )
        assert updated.status_code == 200
        assert updated.json()["amount"] == 33333
        assert "_id" not in updated.json()

        listed = requests.get(f"{API}/payments/products", headers=_headers(token_label), timeout=30)
        assert listed.status_code == 200
        listed_body = listed.json()
        row = next((r for r in listed_body if r["id"] == product_id), None)
        assert row is not None
        assert row["amount"] == 33333
        assert "_id" not in row

        service_invoice = requests.post(
            f"{API}/payments/service/{product_id}",
            json={},
            headers=_headers(token_label),
            timeout=30,
        )
        assert service_invoice.status_code == 200, service_invoice.text
        service_body = service_invoice.json()
        assert service_body["status"] == "pending"
        assert service_body["type"] == "custom_service"
        assert service_body.get("xendit_session_id") is None
        assert "_id" not in service_body

        subscription = requests.post(
            f"{API}/payments/subscription",
            headers=_headers(token_label),
            json={"tier": "annual_normal"},
            timeout=30,
        )
        assert subscription.status_code == 200
        sub_body = subscription.json()
        assert sub_body["status"] == "pending"
        assert sub_body["type"] == "annual_subscription"
        assert sub_body.get("xendit_session_id") is None
        assert "_id" not in sub_body
    finally:
        if product_id:
            db.payment_products.delete_many({"id": product_id})
        db.service_orders.delete_many({"label_id": label_id})
        db.payments.delete_many({"label_id": label_id})
        db.labels.delete_many({"id": label_id})
        db.users.delete_many({"id": user_id})
