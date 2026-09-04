"""Iter 60 — targeted tests for /api/notifications/admin/log."""

import os
import uuid

import pymongo
import requests
from dotenv import load_dotenv

from tests.support_config import SUPERADMIN, SUPPORT, temporary_password


load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/frontend/.env", override=True)

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _login(email: str, password: str) -> dict:
    response = requests.post(
        f"{API}/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    assert response.status_code == 200, response.text
    token = response.json().get("access_token")
    assert isinstance(token, str) and token
    return {"Authorization": f"Bearer {token}"}


def _get_notifications(headers: dict, **params):
    return requests.get(f"{API}/notifications/admin/log", headers=headers, params=params, timeout=30)


# modules/features: mine scope payload shape, pagination, unread_count, and type list
def test_admin_log_mine_returns_projected_items_pagination_and_counts():
    support_headers = _login(SUPPORT["email"], SUPPORT["password"])

    response = _get_notifications(support_headers, scope="mine", page=1, limit=5, read_status="all")
    assert response.status_code == 200, response.text

    data = response.json()
    assert isinstance(data.get("items"), list)
    assert isinstance(data.get("total"), int)
    assert data.get("page") == 1
    assert data.get("limit") == 5
    assert isinstance(data.get("pages"), int)
    assert isinstance(data.get("unread_count"), int)
    assert isinstance(data.get("types"), list)
    assert data.get("scope") == "mine"

    for item in data["items"]:
        assert "_id" not in item
        assert isinstance(item.get("id"), str)
        assert item.get("is_mine") is True
        assert isinstance(item.get("recipient"), dict)
        assert item["recipient"].get("id") == item.get("user_id")
        assert "_id" not in item["recipient"]


# modules/features: super-admin all scope visibility and per-item recipient/is_mine fields
def test_super_admin_scope_all_returns_cross_admin_feed_with_recipient_and_is_mine():
    super_headers = _login(SUPERADMIN["email"], SUPERADMIN["password"])

    response = _get_notifications(super_headers, scope="all", page=1, limit=25, read_status="all")
    assert response.status_code == 200, response.text

    data = response.json()
    assert data.get("scope") == "all"
    assert isinstance(data.get("items"), list)
    assert isinstance(data.get("types"), list)
    assert isinstance(data.get("unread_count"), int)

    for item in data["items"]:
        assert "_id" not in item
        assert "recipient" in item
        assert isinstance(item.get("is_mine"), bool)
        if item.get("recipient") is not None:
            assert "_id" not in item["recipient"]


# modules/features: non-super admin forbidden from all scope
def test_non_super_admin_gets_403_for_scope_all():
    support_headers = _login(SUPPORT["email"], SUPPORT["password"])
    response = _get_notifications(support_headers, scope="all", page=1, limit=10)
    assert response.status_code == 403


# modules/features: auth + admin permission guard
def test_non_admin_user_cannot_access_admin_notification_log():
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    email = f"iter60-label-{suffix}@example.com"
    password = temporary_password("Iter60Label")
    user_id = f"iter60-label-user-{suffix}"
    label_id = f"iter60-label-{suffix}"
    try:
        db.users.insert_one({
            "id": user_id,
            "name": "Iter60 Label",
            "email": email,
            "password_hash": db.users.find_one({"email": "demo_ppr@rilismusik.com"}, {"password_hash": 1})["password_hash"],
            "role": "label",
            "status": "active",
            "email_verified": True,
            "created_at": "2026-01-01T00:00:00+00:00",
        })
        db.labels.insert_one({"id": label_id, "user_id": user_id, "label_name": f"Iter60 Label {suffix}"})

        # login with cloned valid hash from seeded label account then verify admin endpoint denied
        login = requests.post(f"{API}/auth/login", json={"email": email, "password": "DemoPPR#2026"}, timeout=30)
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        response = _get_notifications(headers, scope="mine")
        assert response.status_code == 403
    finally:
        db.labels.delete_many({"id": label_id})
        db.users.delete_many({"id": user_id})


# modules/features: permission notifications.view required (custom admin without permission gets 403)
def test_custom_admin_without_notifications_view_gets_permission_denied():
    db = _db()
    super_headers = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    suffix = uuid.uuid4().hex[:8]
    email = f"iter60-no-notif-{suffix}@example.com"
    password = temporary_password("Iter60NoNotif")
    role_id = None
    user_id = None

    try:
        role_resp = requests.post(
            f"{API}/admin/access/roles",
            headers=super_headers,
            json={"name": f"Iter60 NoNotif {suffix}", "permissions": ["labels.view"]},
            timeout=30,
        )
        assert role_resp.status_code == 200, role_resp.text
        role_id = role_resp.json()["id"]

        user_resp = requests.post(
            f"{API}/admin/admin-users",
            headers=super_headers,
            json={"name": "Iter60 NoNotif", "email": email, "password": password, "admin_role_id": role_id},
            timeout=30,
        )
        assert user_resp.status_code == 200, user_resp.text
        user_id = user_resp.json()["id"]

        headers = _login(email, password)
        denied = _get_notifications(headers, scope="mine")
        assert denied.status_code == 403
        detail = denied.json().get("detail")
        assert isinstance(detail, dict)
        assert detail.get("code") == "PERMISSION_DENIED"
        assert detail.get("permission") == "notifications.view"
    finally:
        if user_id:
            requests.delete(f"{API}/admin/admin-users/{user_id}", headers=super_headers, timeout=30)
        if role_id:
            requests.delete(f"{API}/admin/access/roles/{role_id}", headers=super_headers, timeout=30)
        db.users.delete_many({"email": email})
        if role_id:
            db.admin_roles.delete_many({"id": role_id})


# modules/features: q/read_status/ntype/date range filters + invalid query validation
def test_admin_log_filters_and_validation_queries():
    super_headers = _login(SUPERADMIN["email"], SUPERADMIN["password"])

    baseline = _get_notifications(super_headers, scope="all", page=1, limit=20, read_status="all")
    assert baseline.status_code == 200, baseline.text
    baseline_data = baseline.json()
    assert isinstance(baseline_data.get("items"), list)

    if baseline_data["items"]:
        sample = baseline_data["items"][0]
        sample_type = sample.get("type")
        sample_title_token = (sample.get("title") or "")[:8].strip()
        created_at = sample.get("created_at", "")
        sample_date = created_at[:10] if isinstance(created_at, str) and len(created_at) >= 10 else None

        if sample_type:
            by_type = _get_notifications(super_headers, scope="all", ntype=sample_type, page=1, limit=20)
            assert by_type.status_code == 200, by_type.text
            for item in by_type.json().get("items", []):
                assert item.get("type") == sample_type

        if sample_title_token:
            by_search = _get_notifications(super_headers, scope="all", q=sample_title_token, page=1, limit=20)
            assert by_search.status_code == 200, by_search.text

        if sample_date:
            by_date = _get_notifications(
                super_headers,
                scope="all",
                date_from=sample_date,
                date_to=sample_date,
                page=1,
                limit=20,
            )
            assert by_date.status_code == 200, by_date.text

    read_only = _get_notifications(super_headers, scope="all", read_status="read", page=1, limit=20)
    unread_only = _get_notifications(super_headers, scope="all", read_status="unread", page=1, limit=20)
    assert read_only.status_code == 200, read_only.text
    assert unread_only.status_code == 200, unread_only.text
    for item in read_only.json().get("items", []):
        assert item.get("read_at") is not None
    for item in unread_only.json().get("items", []):
        assert item.get("read_at") is None

    invalid_scope = _get_notifications(super_headers, scope="team")
    invalid_read = _get_notifications(super_headers, scope="mine", read_status="pending")
    invalid_limit = _get_notifications(super_headers, scope="mine", limit=0)
    invalid_page = _get_notifications(super_headers, scope="mine", page=0)
    invalid_date = _get_notifications(super_headers, scope="mine", date_from="2026-13-01")
    for response in (invalid_scope, invalid_read, invalid_limit, invalid_page, invalid_date):
        assert response.status_code == 422
