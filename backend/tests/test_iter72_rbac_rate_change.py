"""PRD-01 RBAC + Rate/Fee Sensitive Action tests (iteration 72)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://lanjut-core.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

CREDS = {
    "super": ("superadmin@rilismusik.com", "SuperAdmin#2026"),
    "finance": ("finance1@rilismusik.com", "Finance#2026"),
    "support": ("support1@rilismusik.com", "Support#2026"),
    "release": ("release1@rilismusik.com", "Release#2026"),
}


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    tok = r.json().get("access_token")
    assert tok
    return tok


def _headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def tokens():
    return {k: _login(*v) for k, v in CREDS.items()}


@pytest.fixture(scope="module")
def sample_label(tokens):
    # Prefer a label with 0 royalty lines to avoid heavy recalculation
    r = requests.get(f"{API}/admin/labels?limit=100", headers=_headers(tokens["super"]), timeout=20)
    assert r.status_code == 200, r.text
    payload = r.json()
    items = payload.get("items") if isinstance(payload, dict) else payload
    assert items, "No labels available"
    # pick first
    return items[0]


# ----------------------- Sensitive workflow -----------------------
class TestRateChangeWorkflow:
    def test_finance_direct_forbidden(self, tokens, sample_label):
        r = requests.post(
            f"{API}/admin/labels/{sample_label['id']}/rate-change/direct",
            headers=_headers(tokens["finance"]),
            json={"proposed_value": 55, "reason": "test"},
            timeout=20,
        )
        assert r.status_code == 403, f"expected 403, got {r.status_code} {r.text}"

    def test_finance_patch_label_royalty_forbidden(self, tokens, sample_label):
        r = requests.patch(
            f"{API}/admin/labels/{sample_label['id']}",
            headers=_headers(tokens["finance"]),
            json={"royalty_percentage_default": 55},
            timeout=20,
        )
        assert r.status_code == 403, f"expected 403, got {r.status_code} {r.text}"

    def test_finance_creates_pending_request_and_live_unchanged(self, tokens, sample_label):
        # cleanup any prior pending
        lst = requests.get(f"{API}/admin/rate-changes?status=pending&label_id={sample_label['id']}",
                           headers=_headers(tokens["super"]), timeout=20).json()
        for pending in lst or []:
            requests.post(f"{API}/admin/rate-changes/{pending['id']}/decision",
                          headers=_headers(tokens["super"]),
                          json={"action": "reject", "note": "cleanup"}, timeout=20)

        current = float(sample_label.get("royalty_percentage_default", 60))
        proposed = current + 1 if current < 90 else current - 1
        r = requests.post(
            f"{API}/admin/labels/{sample_label['id']}/rate-change/request",
            headers=_headers(tokens["finance"]),
            json={"proposed_value": proposed, "reason": "iter72 pytest"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        doc = r.json()
        assert doc["status"] == "pending"
        pytest.rc_request_id = doc["id"]
        pytest.rc_current = current
        pytest.rc_proposed = proposed

        # live unchanged
        detail = requests.get(f"{API}/admin/labels/{sample_label['id']}",
                              headers=_headers(tokens["super"]), timeout=20).json()
        lbl = detail.get("label") or detail
        assert float(lbl["royalty_percentage_default"]) == current

    def test_duplicate_pending_guard(self, tokens, sample_label):
        proposed = pytest.rc_proposed + 1
        r = requests.post(
            f"{API}/admin/labels/{sample_label['id']}/rate-change/request",
            headers=_headers(tokens["finance"]),
            json={"proposed_value": proposed, "reason": "dup"},
            timeout=20,
        )
        assert r.status_code == 409, f"expected 409, got {r.status_code}"

    def test_finance_cannot_approve(self, tokens):
        r = requests.post(
            f"{API}/admin/rate-changes/{pytest.rc_request_id}/decision",
            headers=_headers(tokens["finance"]),
            json={"action": "approve"},
            timeout=20,
        )
        assert r.status_code == 403

    def test_super_admin_approves_applies_value(self, tokens, sample_label):
        r = requests.post(
            f"{API}/admin/rate-changes/{pytest.rc_request_id}/decision",
            headers=_headers(tokens["super"]),
            json={"action": "approve"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "approved"
        detail = requests.get(f"{API}/admin/labels/{sample_label['id']}",
                              headers=_headers(tokens["super"]), timeout=20).json()
        lbl = detail.get("label") or detail
        assert float(lbl["royalty_percentage_default"]) == float(pytest.rc_proposed)

    def test_super_admin_direct_restore(self, tokens, sample_label):
        # RESTORE original value via direct change
        r = requests.post(
            f"{API}/admin/labels/{sample_label['id']}/rate-change/direct",
            headers=_headers(tokens["super"]),
            json={"proposed_value": pytest.rc_current, "reason": "iter72 restore"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        detail = requests.get(f"{API}/admin/labels/{sample_label['id']}",
                              headers=_headers(tokens["super"]), timeout=20).json()
        lbl = detail.get("label") or detail
        assert float(lbl["royalty_percentage_default"]) == float(pytest.rc_current)


# ----------------------- Validate / Preview -----------------------
class TestValidateAndPreview:
    def test_validate_redundant(self, tokens):
        r = requests.post(f"{API}/admin/access/validate",
                          headers=_headers(tokens["super"]),
                          json={"permissions": ["labels.rate", "labels.rate.request"], "active": True},
                          timeout=20)
        assert r.status_code == 200, r.text
        warnings = r.json().get("warnings", [])
        codes = {w.get("code") for w in warnings}
        assert "redundant_request" in codes, f"warnings: {warnings}"

    def test_validate_missing_prerequisite(self, tokens):
        r = requests.post(f"{API}/admin/access/validate",
                          headers=_headers(tokens["super"]),
                          json={"permissions": ["labels.manage"], "active": True},
                          timeout=20)
        assert r.status_code == 200
        codes = {w.get("code") for w in r.json().get("warnings", [])}
        assert "missing_prerequisite" in codes

    def test_preview_labels_view_readonly(self, tokens):
        r = requests.post(f"{API}/admin/access/preview",
                          headers=_headers(tokens["super"]),
                          json={"permissions": ["labels.view"], "active": True},
                          timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        modules = data.get("modules") or []
        labels_mod = next((m for m in modules if m.get("key") == "labels"), None)
        assert labels_mod is not None
        assert labels_mod.get("accessible") is True
        assert labels_mod.get("read_only") is True

    def test_preview_inactive_all_unavailable(self, tokens):
        r = requests.post(f"{API}/admin/access/preview",
                          headers=_headers(tokens["super"]),
                          json={"permissions": ["labels.view"], "active": False},
                          timeout=20)
        assert r.status_code == 200
        modules = r.json().get("modules") or []
        for m in modules:
            for a in m.get("actions", []):
                assert a.get("state") == "unavailable", f"{m['key']}.{a.get('key')} = {a.get('state')}"


# ----------------------- Role CRUD -----------------------
class TestRoleCRUD:
    def test_full_lifecycle_and_builtin_protection(self, tokens):
        s = _headers(tokens["super"])
        # Get builtin role list
        roles = requests.get(f"{API}/admin/access/roles", headers=s, timeout=20).json()
        builtin = next((r for r in roles if r.get("builtin")), None)
        assert builtin
        super_role = next((r for r in roles if r.get("key") == "super_admin"), None)
        assert super_role

        # Cannot deactivate super admin
        r = requests.patch(f"{API}/admin/access/roles/{super_role['id']}", headers=s,
                           json={"active": False}, timeout=20)
        assert r.status_code == 400

        # Cannot delete builtin
        r = requests.delete(f"{API}/admin/access/roles/{builtin['id']}", headers=s, timeout=20)
        assert r.status_code == 400

        # Create custom
        r = requests.post(f"{API}/admin/access/roles", headers=s,
                          json={"name": "TEST_iter72_role", "description": "t",
                                "permissions": ["labels.view"]}, timeout=20)
        assert r.status_code == 200, r.text
        rid = r.json()["id"]

        # Update
        r = requests.patch(f"{API}/admin/access/roles/{rid}", headers=s,
                           json={"name": "TEST_iter72_role_v2",
                                 "permissions": ["labels.view", "payments.view"]}, timeout=20)
        assert r.status_code == 200
        assert set(r.json()["permissions"]) == {"labels.view", "payments.view"}

        # Delete
        r = requests.delete(f"{API}/admin/access/roles/{rid}", headers=s, timeout=20)
        assert r.status_code == 200


# ----------------------- Regression: Admin module access -----------------------
class TestModuleRegression:
    @pytest.mark.parametrize("role,endpoint,expected", [
        ("finance", "/admin/labels?limit=1", 200),
        ("finance", "/admin/payments?limit=1", 200),
        ("finance", "/withdraw/admin?limit=1", 200),
        ("support", "/tickets/admin?limit=1", 200),
        ("release", "/admin/releases?limit=1", 200),
    ])
    def test_module_access(self, tokens, role, endpoint, expected):
        r = requests.get(f"{API}{endpoint}", headers=_headers(tokens[role]), timeout=20)
        assert r.status_code == expected, f"{role} {endpoint} -> {r.status_code} {r.text[:200]}"
