"""Iter 59 — targeted dynamic admin RBAC + admin UI/navigation regression checks."""

import copy
import os
import uuid

import pymongo
import pytest
import requests
from dotenv import load_dotenv

from tests.support_config import CONTENT, FINANCE, RELEASE_ADMIN, SUPERADMIN, SUPPORT, temporary_password


load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/frontend/.env", override=True)

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _login(email: str, password: str, expected: int = 200):
    session = requests.Session()
    response = session.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert response.status_code == expected, response.text
    return session, response


def _headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def _role_by_key(headers, key: str):
    roles = requests.get(f"{API}/admin/access/roles", headers=headers, timeout=30)
    assert roles.status_code == 200, roles.text
    role = next((item for item in roles.json() if item.get("key") == key), None)
    assert role, f"Role {key} not found"
    return role


# auth + role payload contract checks for built-in admins
def test_built_in_admin_login_and_auth_me_include_role_name_permissions_and_cookies():
    for account in (SUPERADMIN, RELEASE_ADMIN, FINANCE, SUPPORT):
        session, login = _login(account["email"], account["password"])
        set_cookie = login.headers.get("set-cookie", "")
        assert "HttpOnly" in set_cookie
        assert "access_token=" in set_cookie and "refresh_token=" in set_cookie
        body = login.json()
        assert body["user"].get("role_name")
        assert isinstance(body["user"].get("permissions"), list)
        me = session.get(f"{API}/auth/me", timeout=30)
        assert me.status_code == 200, me.text
        me_user = me.json()["user"]
        assert me_user.get("role_name")
        assert isinstance(me_user.get("permissions"), list)


# role CRUD + built-in constraints
def test_super_admin_can_edit_builtin_role_but_cannot_delete_builtin_and_admin_ui_has_required_permissions():
    _, login = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    token = login.json()["access_token"]
    headers = _headers(token)

    admin_ui = _role_by_key(headers, "admin_ui")
    assert "ui.settings.view" in (admin_ui.get("permissions") or [])
    assert "ui.settings.manage" in (admin_ui.get("permissions") or [])

    original_description = admin_ui.get("description")
    patched = requests.patch(
        f"{API}/admin/access/roles/{admin_ui['id']}",
        headers=headers,
        json={"description": "Builtin UI role edited in iter59 test"},
        timeout=30,
    )
    assert patched.status_code == 200, patched.text
    assert patched.json().get("description") == "Builtin UI role edited in iter59 test"

    denied_delete = requests.delete(f"{API}/admin/access/roles/{admin_ui['id']}", headers=headers, timeout=30)
    assert denied_delete.status_code == 400

    restore = requests.patch(
        f"{API}/admin/access/roles/{admin_ui['id']}",
        headers=headers,
        json={"description": original_description},
        timeout=30,
    )
    assert restore.status_code == 200, restore.text


# custom role user, permission hot-reload, and role-change session invalidation
def test_custom_role_assignment_reflects_on_active_token_and_role_change_revokes_session():
    _, super_login = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    super_headers = _headers(super_login.json()["access_token"])

    suffix = uuid.uuid4().hex[:8]
    role_id = None
    user_id = None
    email = f"iter59-custom-{suffix}@example.com"
    password = temporary_password("Iter59Admin")
    try:
        role_created = requests.post(
            f"{API}/admin/access/roles",
            headers=super_headers,
            json={"name": f"Iter59 Role {suffix}", "permissions": ["labels.view"]},
            timeout=30,
        )
        assert role_created.status_code == 200, role_created.text
        role_id = role_created.json()["id"]

        user_created = requests.post(
            f"{API}/admin/admin-users",
            headers=super_headers,
            json={"name": "Iter59 Admin", "email": email, "password": password, "admin_role_id": role_id},
            timeout=30,
        )
        assert user_created.status_code == 200, user_created.text
        user_id = user_created.json()["id"]
        assert user_created.json()["role"] == "admin_custom"
        assert user_created.json().get("admin_role_id") == role_id

        _, custom_login = _login(email, password)
        custom_token = custom_login.json()["access_token"]
        custom_headers = _headers(custom_token)
        assert custom_login.json()["user"].get("role") == "admin_custom"
        assert custom_login.json()["user"].get("admin_role_id") == role_id

        assert requests.get(f"{API}/admin/labels", headers=custom_headers, timeout=30).status_code == 200
        assert requests.get(f"{API}/admin/releases", headers=custom_headers, timeout=30).status_code == 403

        expand = requests.patch(
            f"{API}/admin/access/roles/{role_id}",
            headers=super_headers,
            json={"permissions": ["labels.view", "releases.view"]},
            timeout=30,
        )
        assert expand.status_code == 200, expand.text

        # Same already-issued token should reflect new role permissions.
        assert requests.get(f"{API}/admin/releases", headers=custom_headers, timeout=30).status_code == 200

        support_role = _role_by_key(super_headers, "admin_support")
        move_role = requests.patch(
            f"{API}/admin/admin-users/{user_id}",
            headers=super_headers,
            json={"admin_role_id": support_role["id"]},
            timeout=30,
        )
        assert move_role.status_code == 200, move_role.text

        old_session_resp = requests.get(f"{API}/admin/releases", headers=custom_headers, timeout=30)
        assert old_session_resp.status_code in (401, 403)

        _, relogin = _login(email, password)
        assert relogin.json()["user"].get("admin_role_id") == support_role["id"]
    finally:
        if user_id:
            requests.delete(f"{API}/admin/admin-users/{user_id}", headers=super_headers, timeout=30)
        if role_id:
            requests.delete(f"{API}/admin/access/roles/{role_id}", headers=super_headers, timeout=30)
        db = _db()
        db.users.delete_many({"email": email})
        if role_id:
            db.admin_roles.delete_many({"id": role_id})


# disabled role should block active and new sessions
def test_disabling_custom_role_blocks_active_session_and_new_login():
    _, super_login = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    super_headers = _headers(super_login.json()["access_token"])

    suffix = uuid.uuid4().hex[:8]
    role_id = None
    user_id = None
    email = f"iter59-disabled-{suffix}@example.com"
    password = temporary_password("Iter59Disabled")
    try:
        role_created = requests.post(
            f"{API}/admin/access/roles",
            headers=super_headers,
            json={"name": f"Iter59 Disabled {suffix}", "permissions": ["releases.view"]},
            timeout=30,
        )
        assert role_created.status_code == 200, role_created.text
        role_id = role_created.json()["id"]

        user_created = requests.post(
            f"{API}/admin/admin-users",
            headers=super_headers,
            json={"name": "Iter59 Disabled", "email": email, "password": password, "admin_role_id": role_id},
            timeout=30,
        )
        assert user_created.status_code == 200, user_created.text
        user_id = user_created.json()["id"]

        _, custom_login = _login(email, password)
        custom_headers = _headers(custom_login.json()["access_token"])
        assert requests.get(f"{API}/admin/releases", headers=custom_headers, timeout=30).status_code == 200

        deactivate = requests.patch(
            f"{API}/admin/access/roles/{role_id}",
            headers=super_headers,
            json={"active": False},
            timeout=30,
        )
        assert deactivate.status_code == 200, deactivate.text

        active_session_denied = requests.get(f"{API}/admin/releases", headers=custom_headers, timeout=30)
        assert active_session_denied.status_code == 403

        relogin = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
        assert relogin.status_code == 403
    finally:
        if user_id:
            requests.delete(f"{API}/admin/admin-users/{user_id}", headers=super_headers, timeout=30)
        if role_id:
            requests.delete(f"{API}/admin/access/roles/{role_id}", headers=super_headers, timeout=30)
        db = _db()
        db.users.delete_many({"email": email})
        if role_id:
            db.admin_roles.delete_many({"id": role_id})


# navigation filtering + UI settings validation guards
def test_navigation_permission_filter_and_ui_settings_reject_invalid_configs():
    _, super_login = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    super_headers = _headers(super_login.json()["access_token"])

    base_settings = requests.get(f"{API}/admin/ui-settings", headers=super_headers, timeout=30)
    assert base_settings.status_code == 200, base_settings.text
    settings = base_settings.json()

    suffix = uuid.uuid4().hex[:8]
    role_id = None
    user_id = None
    email = f"iter59-nav-{suffix}@example.com"
    password = temporary_password("Iter59Nav")
    try:
        role_created = requests.post(
            f"{API}/admin/access/roles",
            headers=super_headers,
            json={"name": f"Iter59 Nav {suffix}", "permissions": ["releases.view"]},
            timeout=30,
        )
        assert role_created.status_code == 200, role_created.text
        role_id = role_created.json()["id"]

        user_created = requests.post(
            f"{API}/admin/admin-users",
            headers=super_headers,
            json={"name": "Iter59 Nav", "email": email, "password": password, "admin_role_id": role_id},
            timeout=30,
        )
        assert user_created.status_code == 200, user_created.text
        user_id = user_created.json()["id"]

        _, custom_login = _login(email, password)
        custom_headers = _headers(custom_login.json()["access_token"])
        nav = requests.get(f"{API}/admin/navigation", headers=custom_headers, timeout=30)
        assert nav.status_code == 200, nav.text
        nav_keys = {item["key"] for item in nav.json()["items"]}
        assert "releases" in nav_keys
        assert "labels" not in nav_keys

        changed_route = copy.deepcopy(settings)
        changed_route["items"][0]["route"] = "https://example.com/changed"
        invalid_route = requests.put(
            f"{API}/admin/ui-settings",
            headers=super_headers,
            json={"default_locale": changed_route["default_locale"], "items": changed_route["items"]},
            timeout=30,
        )
        assert invalid_route.status_code == 400

        duplicate = copy.deepcopy(settings)
        duplicate["items"][1]["key"] = duplicate["items"][0]["key"]
        invalid_duplicate = requests.put(
            f"{API}/admin/ui-settings",
            headers=super_headers,
            json={"default_locale": duplicate["default_locale"], "items": duplicate["items"]},
            timeout=30,
        )
        assert invalid_duplicate.status_code == 400

        self_parent = copy.deepcopy(settings)
        self_parent["items"][2]["parent_key"] = self_parent["items"][2]["key"]
        invalid_self_parent = requests.put(
            f"{API}/admin/ui-settings",
            headers=super_headers,
            json={"default_locale": self_parent["default_locale"], "items": self_parent["items"]},
            timeout=30,
        )
        assert invalid_self_parent.status_code == 400

        nested = copy.deepcopy(settings)
        keys = [item["key"] for item in nested["items"]]
        if len(keys) >= 3:
            nested["items"][1]["parent_key"] = keys[0]
            nested["items"][2]["parent_key"] = keys[1]
            invalid_nested = requests.put(
                f"{API}/admin/ui-settings",
                headers=super_headers,
                json={"default_locale": nested["default_locale"], "items": nested["items"]},
                timeout=30,
            )
            assert invalid_nested.status_code == 400
        else:
            pytest.skip("Not enough navigation items to validate nested level")
    finally:
        if user_id:
            requests.delete(f"{API}/admin/admin-users/{user_id}", headers=super_headers, timeout=30)
        if role_id:
            requests.delete(f"{API}/admin/access/roles/{role_id}", headers=super_headers, timeout=30)
        db = _db()
        db.users.delete_many({"email": email})
        if role_id:
            db.admin_roles.delete_many({"id": role_id})


# read vs manage permission guards + existing module RBAC smoke
def test_permission_guards_and_release_finance_support_kyc_cms_regression_smoke():
    _, super_login = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    super_headers = _headers(super_login.json()["access_token"])

    suffix = uuid.uuid4().hex[:8]
    role_id = None
    user_id = None
    email = f"iter59-readonly-{suffix}@example.com"
    password = temporary_password("Iter59Read")
    try:
        role_created = requests.post(
            f"{API}/admin/access/roles",
            headers=super_headers,
            json={"name": f"Iter59 ReadOnly {suffix}", "permissions": ["labels.view", "ui.settings.view"]},
            timeout=30,
        )
        assert role_created.status_code == 200, role_created.text
        role_id = role_created.json()["id"]

        user_created = requests.post(
            f"{API}/admin/admin-users",
            headers=super_headers,
            json={"name": "Iter59 Read", "email": email, "password": password, "admin_role_id": role_id},
            timeout=30,
        )
        assert user_created.status_code == 200, user_created.text
        user_id = user_created.json()["id"]

        _, custom_login = _login(email, password)
        custom_headers = _headers(custom_login.json()["access_token"])
        assert requests.get(f"{API}/admin/ui-settings", headers=custom_headers, timeout=30).status_code == 200

        current_settings = requests.get(f"{API}/admin/ui-settings", headers=super_headers, timeout=30)
        assert current_settings.status_code == 200, current_settings.text
        denied_patch = requests.put(
            f"{API}/admin/ui-settings",
            headers=custom_headers,
            json={"default_locale": current_settings.json()["default_locale"], "items": current_settings.json()["items"]},
            timeout=30,
        )
        assert denied_patch.status_code == 403

        assert requests.get(f"{API}/admin/labels", headers=custom_headers, timeout=30).status_code == 200
        denied_label_patch = requests.patch(
            f"{API}/admin/labels/non-existent-id",
            headers=custom_headers,
            json={"account_status": "suspended"},
            timeout=30,
        )
        assert denied_label_patch.status_code == 403

        _, release_login = _login(RELEASE_ADMIN["email"], RELEASE_ADMIN["password"])
        _, finance_login = _login(FINANCE["email"], FINANCE["password"])
        _, support_login = _login(SUPPORT["email"], SUPPORT["password"])
        _, content_login = _login(CONTENT["email"], CONTENT["password"])

        assert requests.get(f"{API}/admin/releases", headers=_headers(release_login.json()["access_token"]), timeout=30).status_code == 200
        assert requests.get(f"{API}/admin/payments", headers=_headers(finance_login.json()["access_token"]), timeout=30).status_code == 200
        assert requests.get(f"{API}/admin/kyc", headers=_headers(support_login.json()["access_token"]), timeout=30).status_code == 200
        assert requests.get(f"{API}/tickets/admin", headers=_headers(support_login.json()["access_token"]), timeout=30).status_code == 200
        assert requests.get(f"{API}/cms/landing", headers=_headers(content_login.json()["access_token"]), timeout=30).status_code == 200
    finally:
        if user_id:
            requests.delete(f"{API}/admin/admin-users/{user_id}", headers=super_headers, timeout=30)
        if role_id:
            requests.delete(f"{API}/admin/access/roles/{role_id}", headers=super_headers, timeout=30)
        db = _db()
        db.users.delete_many({"email": email})
        if role_id:
            db.admin_roles.delete_many({"id": role_id})