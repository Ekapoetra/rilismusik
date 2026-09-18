"""Iter90 — RBAC audit + quick-grant flow tests.

Covers:
- GET /api/admin/access/role-audit shape and diff computation
- PATCH /api/admin/access/roles/{admin_finance} produces new audit entry with added=labels.bank.verify
- No-op update does not create a visible entry
- Quick-grant flow: create custom role, PATCH with union of perms, verify granted, cleanup
"""
import os
import time
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"

SUPER = {"email": "superadmin@rilismusik.com", "password": "SuperAdmin#2026"}


@pytest.fixture(scope="module")
def super_token():
    r = requests.post(f"{BASE}/auth/login", json=SUPER, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def hdr(super_token):
    return {"Authorization": f"Bearer {super_token}"}


def _find_admin_finance(hdr):
    r = requests.get(f"{BASE}/admin/access/roles", headers=hdr, timeout=30)
    assert r.status_code == 200
    for role in r.json():
        if role.get("key") == "admin_finance":
            return role
    pytest.fail("admin_finance role not found")


class TestRoleAudit:
    def test_role_audit_shape(self, hdr):
        r = requests.get(f"{BASE}/admin/access/role-audit", headers=hdr, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "entries" in data and "count" in data
        assert isinstance(data["entries"], list)
        assert data["count"] == len(data["entries"])
        for e in data["entries"][:3]:
            assert "at" in e and "actor_name" in e and "role_name" in e
            assert e["action"] in ("create_admin_role", "update_admin_role", "delete_admin_role")
            assert isinstance(e["added"], list) and isinstance(e["removed"], list)

    def test_patch_admin_finance_creates_audit_entry_with_diff(self, hdr):
        role = _find_admin_finance(hdr)
        original_perms = list(role["permissions"])
        assert "labels.bank.verify" not in original_perms, "Precondition: labels.bank.verify should not already be in admin_finance"
        role_id = role["id"]
        try:
            new_perms = original_perms + ["labels.bank.verify"]
            r = requests.patch(f"{BASE}/admin/access/roles/{role_id}", headers=hdr,
                               json={"permissions": new_perms}, timeout=30)
            assert r.status_code == 200, r.text
            assert "labels.bank.verify" in r.json()["permissions"]

            time.sleep(0.5)
            r2 = requests.get(f"{BASE}/admin/access/role-audit", headers=hdr,
                              params={"role_id": role_id, "limit": 10}, timeout=30)
            assert r2.status_code == 200
            entries = r2.json()["entries"]
            assert entries, "expected an audit entry after PATCH"
            newest = entries[0]
            assert newest["role_name"] == "Admin Finance"
            added_keys = [a["key"] for a in newest["added"]]
            assert "labels.bank.verify" in added_keys, f"expected added labels.bank.verify, got {added_keys}"

            # No-op update should not create a new entry
            count_before = r2.json()["count"]
            r3 = requests.patch(f"{BASE}/admin/access/roles/{role_id}", headers=hdr,
                                json={"permissions": new_perms}, timeout=30)
            assert r3.status_code == 200
            time.sleep(0.5)
            r4 = requests.get(f"{BASE}/admin/access/role-audit", headers=hdr,
                              params={"role_id": role_id, "limit": 10}, timeout=30)
            assert r4.json()["count"] == count_before, "no-op update should not add a visible entry"
        finally:
            # Restore
            requests.patch(f"{BASE}/admin/access/roles/{role_id}", headers=hdr,
                           json={"permissions": original_perms}, timeout=30)
            after = _find_admin_finance(hdr)
            assert "labels.bank.verify" not in after["permissions"]
            assert set(after["permissions"]) == set(original_perms)


class TestQuickGrant:
    def test_quick_grant_flow(self, hdr):
        role_id = None
        try:
            create = requests.post(f"{BASE}/admin/access/roles", headers=hdr,
                                   json={"name": "TEST_QuickGrant_Iter90",
                                         "description": "temp",
                                         "permissions": ["dashboard.view"]}, timeout=30)
            assert create.status_code == 200, create.text
            role = create.json()
            role_id = role["id"]
            assert role["permissions"] == ["dashboard.view"]

            merged = list(set(role["permissions"] + ["analytics.view"]))
            patch = requests.patch(f"{BASE}/admin/access/roles/{role_id}", headers=hdr,
                                   json={"permissions": merged}, timeout=30)
            assert patch.status_code == 200, patch.text
            perms = patch.json()["permissions"]
            assert "analytics.view" in perms and "dashboard.view" in perms

            # Verify via GET
            listed = requests.get(f"{BASE}/admin/access/roles", headers=hdr, timeout=30).json()
            found = next((r for r in listed if r["id"] == role_id), None)
            assert found and "analytics.view" in found["permissions"]
        finally:
            if role_id:
                d = requests.delete(f"{BASE}/admin/access/roles/{role_id}", headers=hdr, timeout=30)
                assert d.status_code == 200
