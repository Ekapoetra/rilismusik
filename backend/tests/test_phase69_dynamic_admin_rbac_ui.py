"""Phase 69 — dynamic admin RBAC, active-session enforcement, and UI navigation config."""
import copy
import uuid

import requests

from tests.support_config import SUPERADMIN, temporary_password
from tests.test_phase43_release_approval_invoice import API, _db, _headers, _login


def test_custom_role_admin_user_and_navigation_permissions_are_dynamic():
    db = _db(); suffix = uuid.uuid4().hex[:10]
    super_token = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    super_headers = _headers(super_token)
    email = f"phase69-admin-{suffix}@example.com"; password = temporary_password("Admin69")
    role_id = None; user_id = None
    original_ui = requests.get(f"{API}/admin/ui-settings", headers=super_headers, timeout=30).json()
    try:
        catalog = requests.get(f"{API}/admin/access/catalog", headers=super_headers, timeout=30)
        assert catalog.status_code == 200, catalog.text
        keys = set(catalog.json()["all_permissions"])
        assert {"labels.view", "releases.view", "ui.settings.manage", "access.users.manage"}.issubset(keys)

        roles = requests.get(f"{API}/admin/access/roles", headers=super_headers, timeout=30)
        assert roles.status_code == 200, roles.text
        assert any(role["key"] == "admin_ui" and role["builtin"] for role in roles.json())

        created_role = requests.post(f"{API}/admin/access/roles", headers=super_headers, json={
            "name": f"Auditor Label {suffix}", "description": "Role custom Phase 69",
            "permissions": ["labels.view"],
        }, timeout=30)
        assert created_role.status_code == 200, created_role.text
        role_id = created_role.json()["id"]

        created_user = requests.post(f"{API}/admin/admin-users", headers=super_headers, json={
            "name": "Admin Kustom Phase 69", "email": email, "password": password,
            "admin_role_id": role_id,
        }, timeout=30)
        assert created_user.status_code == 200, created_user.text
        user_id = created_user.json()["id"]
        assert created_user.json()["role"] == "admin_custom"

        login = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
        assert login.status_code == 200, login.text
        custom_token = login.json()["access_token"]; custom_headers = _headers(custom_token)
        auth_user = login.json()["user"]
        assert auth_user["is_admin"] is True
        assert auth_user["role_name"] == f"Auditor Label {suffix}"
        assert auth_user["permissions"] == ["labels.view"]

        nav = requests.get(f"{API}/admin/navigation", headers=custom_headers, timeout=30)
        assert nav.status_code == 200, nav.text
        assert {item["key"] for item in nav.json()["items"]} == {"labels"}
        assert requests.get(f"{API}/admin/labels", headers=custom_headers, timeout=30).status_code == 200
        denied_edit = requests.patch(f"{API}/admin/labels/phase69-missing", headers=custom_headers, json={"account_status": "suspended"}, timeout=30)
        assert denied_edit.status_code == 403
        denied = requests.get(f"{API}/admin/releases", headers=custom_headers, timeout=30)
        assert denied.status_code == 403 and denied.json()["detail"]["code"] == "PERMISSION_DENIED"
        assert requests.get(f"{API}/admin/ui-settings", headers=custom_headers, timeout=30).status_code == 403

        expanded = requests.patch(f"{API}/admin/access/roles/{role_id}", headers=super_headers, json={
            "name": f"Auditor Label & Rilisan {suffix}",
            "permissions": ["labels.view", "labels.manage", "releases.view", "ui.settings.view"],
        }, timeout=30)
        assert expanded.status_code == 200, expanded.text
        assert requests.get(f"{API}/admin/releases", headers=custom_headers, timeout=30).status_code == 200
        assert requests.patch(f"{API}/admin/labels/phase69-missing", headers=custom_headers, json={"account_status": "suspended"}, timeout=30).status_code == 404
        assert requests.get(f"{API}/admin/ui-settings", headers=custom_headers, timeout=30).status_code == 200

        updated_user = requests.patch(f"{API}/admin/admin-users/{user_id}", headers=super_headers, json={"name": "Admin UI Rilisan Phase 69"}, timeout=30)
        assert updated_user.status_code == 200, updated_user.text
        assert updated_user.json()["name"] == "Admin UI Rilisan Phase 69"

        settings = copy.deepcopy(original_ui)
        settings["default_locale"] = "en"
        settings["items"] = sorted(settings["items"], key=lambda item: item.get("order", 0), reverse=True)
        for item in settings["items"]:
            item.pop("permission", None); item.pop("icon", None)
            if item["key"] == "releases":
                item["labels"] = {"id": "Operasional Rilisan", "en": "Release Operations"}
                item["parent_key"] = "labels"
        saved_ui = requests.put(f"{API}/admin/ui-settings", headers=super_headers, json={"default_locale": settings["default_locale"], "items": settings["items"]}, timeout=30)
        assert saved_ui.status_code == 200, saved_ui.text
        custom_nav = requests.get(f"{API}/admin/navigation", headers=custom_headers, timeout=30).json()
        release_nav = next(item for item in custom_nav["items"] if item["key"] == "releases")
        assert release_nav["parent_key"] == "labels"
        assert release_nav["labels"]["en"] == "Release Operations"

        invalid_items = copy.deepcopy(settings["items"])
        invalid_items[0]["route"] = "https://example.com"
        invalid = requests.put(f"{API}/admin/ui-settings", headers=super_headers, json={"default_locale": "id", "items": invalid_items}, timeout=30)
        assert invalid.status_code == 400

        narrowed = requests.patch(f"{API}/admin/access/roles/{role_id}", headers=super_headers, json={"permissions": ["releases.view"]}, timeout=30)
        assert narrowed.status_code == 200
        assert requests.get(f"{API}/admin/labels", headers=custom_headers, timeout=30).status_code == 403
        assert requests.get(f"{API}/admin/releases", headers=custom_headers, timeout=30).status_code == 200

        disabled = requests.patch(f"{API}/admin/access/roles/{role_id}", headers=super_headers, json={"active": False}, timeout=30)
        assert disabled.status_code == 200
        assert requests.get(f"{API}/admin/releases", headers=custom_headers, timeout=30).status_code == 403
        assert requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30).status_code == 403
    finally:
        restore_items = []
        for item in original_ui.get("items", []):
            restored = {key: value for key, value in item.items() if key not in {"permission", "icon"}}
            restore_items.append(restored)
        requests.put(f"{API}/admin/ui-settings", headers=super_headers, json={"default_locale": original_ui.get("default_locale", "id"), "items": restore_items}, timeout=30)
        if user_id:
            requests.delete(f"{API}/admin/admin-users/{user_id}", headers=super_headers, timeout=30)
        if role_id:
            requests.delete(f"{API}/admin/access/roles/{role_id}", headers=super_headers, timeout=30)
        db.users.delete_many({"email": email})
        if role_id:
            db.admin_roles.delete_many({"id": role_id})