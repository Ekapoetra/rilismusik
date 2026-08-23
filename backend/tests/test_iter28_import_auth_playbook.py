"""Iteration 28 — import-graph + auth playbook regression checks."""
import asyncio
import importlib
import os
import uuid
from pathlib import Path

import pymongo
import pytest
import requests
from dotenv import load_dotenv

from tests.support_config import SUPERADMIN, temporary_password


load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/frontend/.env", override=True)

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _login(email: str, password: str):
    return requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=30)


def test_import_graph_loads_without_circular_init_failure():
    assert BASE, "REACT_APP_BACKEND_URL is required"
    modules = [
        importlib.import_module("routes.admin"),
        importlib.import_module("routes.royalty_recalculation"),
        importlib.import_module("payment_service"),
    ]
    assert all(mod is not None for mod in modules)


def test_seeded_password_hash_uses_bcrypt_2b_prefix():
    doc = _db().users.find_one({"email": SUPERADMIN["email"]}, {"_id": 0, "password_hash": 1})
    assert doc and isinstance(doc.get("password_hash"), str)
    assert doc["password_hash"].startswith("$2b$")


def test_login_sets_httponly_secure_cookies():
    response = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    assert response.status_code == 200, response.text
    raw = response.headers.get("set-cookie", "")
    lowered = raw.lower()
    assert "access_token=" in raw
    assert "refresh_token=" in raw
    assert "httponly" in lowered
    assert "secure" in lowered


def test_cors_allows_credentials_for_explicit_origin():
    origin = BASE
    internal_backend = "http://127.0.0.1:8001"
    response = requests.options(
        f"{internal_backend}/api/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
        timeout=30,
    )
    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials", "").lower() == "true"


def test_bruteforce_lockout_after_five_failures():
    email = f"iter28-lock-{uuid.uuid4().hex[:10]}@example.com"
    password = temporary_password("Lock")
    register = requests.post(
        f"{BASE}/api/auth/register",
        json={
            "label_name": "Iter28 Lockout",
            "pic_name": "Iter Tester",
            "email": email,
            "whatsapp": "+628123000000",
            "password": password,
            "account_type": "label",
            "mda_accepted": True,
        },
        timeout=30,
    )
    assert register.status_code in (200, 201), register.text
    statuses = []
    wrong_password = temporary_password("wrong")
    for index in range(6):
        trial = requests.post(
            f"{BASE}/api/auth/login",
            json={"email": email, "password": wrong_password},
            headers={"X-Forwarded-For": f"10.28.0.{index + 1}"},
            timeout=30,
        )
        statuses.append(trial.status_code)
    assert 429 in statuses
    created = _db().users.find_one({"email": email}, {"_id": 0, "id": 1})
    if created:
        _db().labels.delete_many({"user_id": created["id"]})
    _db().users.delete_many({"email": email})


def test_seed_admin_updates_existing_admin_password_when_changed():
    from routes import seed as seed_module
    from auth_utils import verify_password

    original_email = os.environ.get("ADMIN_EMAIL")
    original_password = os.environ.get("ADMIN_PASSWORD")
    custom_email = f"iter28-admin-{temporary_password('x')[:6].lower()}@example.com"
    first_password = temporary_password("First")
    second_password = temporary_password("Second")

    async def scenario():
        os.environ["ADMIN_EMAIL"] = custom_email
        os.environ["ADMIN_PASSWORD"] = first_password
        await seed_module.seed_indexes_and_admins()
        before = _db().users.find_one({"email": custom_email}, {"_id": 0, "password_hash": 1})
        assert before and verify_password(first_password, before["password_hash"])

        os.environ["ADMIN_PASSWORD"] = second_password
        await seed_module.seed_indexes_and_admins()
        after = _db().users.find_one({"email": custom_email}, {"_id": 0, "password_hash": 1})
        assert after and verify_password(second_password, after["password_hash"])

    try:
        asyncio.run(scenario())
    finally:
        if original_email is None:
            os.environ.pop("ADMIN_EMAIL", None)
        else:
            os.environ["ADMIN_EMAIL"] = original_email
        if original_password is None:
            os.environ.pop("ADMIN_PASSWORD", None)
        else:
            os.environ["ADMIN_PASSWORD"] = original_password
        _db().users.delete_many({"email": custom_email})
