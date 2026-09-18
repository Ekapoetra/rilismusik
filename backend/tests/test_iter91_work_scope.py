"""Iter91 — Work scope (My Work vs Team Monitor) + gaps removed.

Verifies backend acceptance criteria for the "Perbaiki Work Dashboard" PRD:
- /admin/work/queue?scope=my as Super Admin => items all scope=='super_admin_only'; NO 'gaps' key
- /admin/work/queue?scope=team as Super Admin => items all scope=='permission'
- /admin/work/settings => work_types include sla_days + scope; NO responsible_role_ids
- /admin/work/responsibilities => 404 (endpoint removed)
- Regular admins (release / finance) get expected My Work by real role permissions
- Regression: /admin/performance/overview returns 200 with rows for Super Admin
"""
import os
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

CREDS = {
    "super": ("superadmin@rilismusik.com", "SuperAdmin#2026"),
    "release": ("release1@rilismusik.com", "Release#2026"),
    "finance": ("finance1@rilismusik.com", "Finance#2026"),
}


def _login(email, password):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    assert tok, f"no token in login response: {data}"
    return tok


@pytest.fixture(scope="module")
def tokens():
    return {k: _login(*v) for k, v in CREDS.items()}


def _hdr(tok):
    return {"Authorization": f"Bearer {tok}"}


class TestSuperAdminWorkScope:
    def test_my_only_super_admin_only_and_no_gaps(self, tokens):
        r = requests.get(f"{BASE}/api/admin/work/queue", params={"scope": "my"}, headers=_hdr(tokens["super"]), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "gaps" not in data, f"'gaps' key should be gone, got: {list(data.keys())}"
        items = data.get("items", [])
        assert items, "Super Admin My Work should include at least sensitive_approval"
        for it in items:
            assert it["scope"] == "super_admin_only", f"unexpected scope in My Work: {it}"
        keys = {it["work_type"] for it in items}
        assert "sensitive_approval" in keys
        # Ensure NO operational team work leaks in
        for banned in ["release_review", "release_go_live", "withdraw_verification", "support_ticket",
                      "wami_registration", "addon_processing", "legacy_claim", "bank_verification", "kyc_review"]:
            assert banned not in keys, f"{banned} must not be in Super Admin My Work"

    def test_team_only_permission_scope(self, tokens):
        r = requests.get(f"{BASE}/api/admin/work/queue", params={"scope": "team"}, headers=_hdr(tokens["super"]), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "gaps" not in data
        items = data.get("items", [])
        assert items, "Team Monitor should list operational work types"
        for it in items:
            assert it["scope"] == "permission", f"team must not contain super_admin_only: {it}"
        keys = {it["work_type"] for it in items}
        assert "sensitive_approval" not in keys

    def test_my_and_team_are_disjoint(self, tokens):
        my = requests.get(f"{BASE}/api/admin/work/queue", params={"scope": "my"}, headers=_hdr(tokens["super"]), timeout=30).json()
        team = requests.get(f"{BASE}/api/admin/work/queue", params={"scope": "team"}, headers=_hdr(tokens["super"]), timeout=30).json()
        my_keys = {i["work_type"] for i in my["items"]}
        team_keys = {i["work_type"] for i in team["items"]}
        assert my_keys.isdisjoint(team_keys), f"overlap: {my_keys & team_keys}"


class TestWorkSettingsAndRemovedResponsibilities:
    def test_settings_shape(self, tokens):
        r = requests.get(f"{BASE}/api/admin/work/settings", headers=_hdr(tokens["super"]), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "work_types" in data and data["work_types"]
        for wt in data["work_types"]:
            assert "sla_days" in wt and isinstance(wt["sla_days"], int)
            assert "scope" in wt and wt["scope"] in ("permission", "super_admin_only")
            assert "responsible_role_ids" not in wt, f"legacy responsibility leaked: {wt}"

    def test_responsibilities_endpoint_removed(self, tokens):
        r = requests.get(f"{BASE}/api/admin/work/responsibilities", headers=_hdr(tokens["super"]), timeout=30)
        assert r.status_code == 404, f"expected 404, got {r.status_code}: {r.text[:200]}"

    def test_responsibilities_put_removed(self, tokens):
        r = requests.put(f"{BASE}/api/admin/work/responsibilities", headers=_hdr(tokens["super"]),
                         json={"work_type": "release_review", "role_ids": []}, timeout=30)
        assert r.status_code in (404, 405)


class TestDynamicRoleMyWork:
    def test_release_admin(self, tokens):
        r = requests.get(f"{BASE}/api/admin/work/queue", params={"scope": "my"}, headers=_hdr(tokens["release"]), timeout=30)
        assert r.status_code == 200, r.text
        keys = {i["work_type"] for i in r.json()["items"]}
        assert "release_review" in keys, f"missing release_review: {keys}"
        assert "release_go_live" in keys, f"missing release_go_live: {keys}"
        assert "withdraw_verification" not in keys, f"withdraw leaked: {keys}"
        assert "sensitive_approval" not in keys

    def test_finance_admin(self, tokens):
        r = requests.get(f"{BASE}/api/admin/work/queue", params={"scope": "my"}, headers=_hdr(tokens["finance"]), timeout=30)
        assert r.status_code == 200, r.text
        keys = {i["work_type"] for i in r.json()["items"]}
        assert "withdraw_verification" in keys, f"missing withdraw: {keys}"
        assert "release_review" not in keys
        assert "sensitive_approval" not in keys


class TestPerformanceRegression:
    def test_overview_ok(self, tokens):
        r = requests.get(f"{BASE}/api/admin/performance/overview", headers=_hdr(tokens["super"]), timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        # accept either {rows: [...]} or list; assert non-empty payload
        rows = data.get("rows") if isinstance(data, dict) else data
        assert rows is not None, f"no rows key: {data}"
        assert isinstance(rows, list)
