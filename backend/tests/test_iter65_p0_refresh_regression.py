"""Iter 65 — P0 refresh regression checks for admin nav/chat unread/reset endpoint + auth sanity."""

import os

import pymongo
import requests
from dotenv import load_dotenv

from tests.support_config import SUPERADMIN, SUPPORT


load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/frontend/.env", override=True)

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _login(email: str, password: str):
    response = requests.post(
        f"{API}/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    assert response.status_code == 200, response.text
    token = response.json().get("access_token")
    assert isinstance(token, str) and token
    return response, {"Authorization": f"Bearer {token}"}


# modules/features: auth cookie contract + secure hash format
def test_auth_login_sets_http_only_cookie_and_bcrypt_hash_uses_2b_prefix():
    login_response, _ = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    set_cookie = login_response.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie
    assert "access_token=" in set_cookie and "refresh_token=" in set_cookie

    user = _db().users.find_one({"email": SUPERADMIN["email"]}, {"_id": 0, "password_hash": 1})
    assert isinstance((user or {}).get("password_hash"), str)
    assert user["password_hash"].startswith("$2b$")


# modules/features: access catalog must not include removed label_rates nav item
def test_admin_access_catalog_excludes_label_rates_and_has_navigation_payload():
    _, headers = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    response = requests.get(f"{API}/admin/access/catalog", headers=headers, timeout=30)
    assert response.status_code == 200, response.text

    body = response.json()
    assert isinstance(body.get("modules"), list)
    assert isinstance(body.get("all_permissions"), list)
    assert isinstance(body.get("navigation"), list)
    keys = [item.get("key") for item in body["navigation"]]
    assert "label_rates" not in keys


# modules/features: runtime admin navigation must not include removed label_rates nav item
def test_admin_navigation_excludes_label_rates_for_super_admin():
    _, headers = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    response = requests.get(f"{API}/admin/navigation", headers=headers, timeout=30)
    assert response.status_code == 200, response.text

    body = response.json()
    assert isinstance(body.get("items"), list)
    keys = [item.get("key") for item in body["items"]]
    assert "label_rates" not in keys


# modules/features: unread endpoint response includes latest incoming fields and typed payload
def test_chat_unread_includes_latest_incoming_fields_and_integer_unread_count():
    _, headers = _login(SUPPORT["email"], SUPPORT["password"])
    response = requests.get(f"{API}/chat/unread", headers=headers, timeout=30)
    assert response.status_code == 200, response.text

    body = response.json()
    assert "unread" in body and isinstance(body["unread"], int)
    assert "latest_incoming_id" in body
    assert "latest_incoming_at" in body
    assert body["latest_incoming_id"] is None or isinstance(body["latest_incoming_id"], str)
    assert body["latest_incoming_at"] is None or isinstance(body["latest_incoming_at"], str)


# modules/features: removed dangerous reset endpoint should be absent/inaccessible
def test_removed_reset_all_data_endpoint_is_not_available():
    _, headers = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    response = requests.post(
        f"{API}/admin/admin/danger/reset-all-data",
        headers=headers,
        timeout=30,
    )
    assert response.status_code in (404, 405)
