"""PRD-01 iter73: Sensitive Action request→approval for Blacklist + Package."""
import os
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://lanjut-core.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

CREDS = {
    "super": ("superadmin@rilismusik.com", "SuperAdmin#2026"),
    "finance": ("finance1@rilismusik.com", "Finance#2026"),
    "support": ("support1@rilismusik.com", "Support#2026"),
    "release": ("release1@rilismusik.com", "Release#2026"),
}


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text[:200]}"
    return r.json()["access_token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def tokens():
    return {k: _login(*v) for k, v in CREDS.items()}


@pytest.fixture(scope="module")
def ppr_label(tokens):
    """Pick a PPR (pay_per_release), non-blacklisted label."""
    r = requests.get(f"{API}/admin/labels?limit=200", headers=_h(tokens["super"]), timeout=30)
    assert r.status_code == 200
    payload = r.json()
    items = payload.get("items") if isinstance(payload, dict) else payload
    for lbl in items or []:
        if lbl.get("account_status") != "blacklisted" and (lbl.get("payment_type") or "pay_per_release") == "pay_per_release":
            return lbl
    pytest.skip("No PPR non-blacklisted label available")


def _cleanup_pending(tokens, label_id, action_type):
    lst = requests.get(f"{API}/admin/sensitive-requests?status=pending&label_id={label_id}&action_type={action_type}",
                       headers=_h(tokens["super"]), timeout=20)
    if lst.status_code == 200:
        for req in lst.json() or []:
            requests.post(f"{API}/admin/sensitive-requests/{req['id']}/decision",
                          headers=_h(tokens["super"]),
                          json={"action": "reject", "note": "cleanup"}, timeout=20)


# ------------------- Package request flow -------------------
class TestPackageRequestFlow:
    def test_finance_direct_package_forbidden(self, tokens, ppr_label):
        r = requests.patch(f"{API}/admin/labels/{ppr_label['id']}/package",
                           headers=_h(tokens["finance"]),
                           json={"package": "annual_vip", "expires_on": "2027-01-01",
                                 "reason": "test", "expected_revision": 0, "confirm": True},
                           timeout=20)
        assert r.status_code == 403, f"got {r.status_code}: {r.text[:200]}"

    def test_finance_patch_label_subscription_forbidden(self, tokens, ppr_label):
        r = requests.patch(f"{API}/admin/labels/{ppr_label['id']}",
                           headers=_h(tokens["finance"]),
                           json={"payment_type": "annual_subscription", "subscription_tier": "annual_vip"},
                           timeout=20)
        assert r.status_code == 403, f"got {r.status_code}: {r.text[:200]}"

    def test_finance_creates_pending_package_request(self, tokens, ppr_label):
        _cleanup_pending(tokens, ppr_label["id"], "package")
        r = requests.post(f"{API}/admin/labels/{ppr_label['id']}/package-request",
                          headers=_h(tokens["finance"]),
                          json={"package": "annual_vip", "expires_on": "2027-01-01",
                                "reason": "iter73 pytest", "expected_revision": int(ppr_label.get("package_revision") or 0)},
                          timeout=20)
        assert r.status_code == 200, r.text
        doc = r.json()
        assert doc["status"] == "pending"
        assert doc["action_type"] == "package"
        pytest.pkg_req_id = doc["id"]
        # live unchanged
        detail = requests.get(f"{API}/admin/labels/{ppr_label['id']}",
                              headers=_h(tokens["super"]), timeout=20).json()
        lbl = detail.get("label") or detail
        assert (lbl.get("payment_type") or "pay_per_release") == "pay_per_release"

    def test_duplicate_package_pending_409(self, tokens, ppr_label):
        r = requests.post(f"{API}/admin/labels/{ppr_label['id']}/package-request",
                          headers=_h(tokens["finance"]),
                          json={"package": "annual_normal", "expires_on": "2027-01-01",
                                "reason": "dup", "expected_revision": 0},
                          timeout=20)
        assert r.status_code == 409, f"got {r.status_code}"

    def test_finance_cannot_approve_package(self, tokens):
        r = requests.post(f"{API}/admin/sensitive-requests/{pytest.pkg_req_id}/decision",
                          headers=_h(tokens["finance"]),
                          json={"action": "approve"}, timeout=20)
        assert r.status_code == 403

    def test_super_admin_approves_package_applies(self, tokens, ppr_label):
        r = requests.post(f"{API}/admin/sensitive-requests/{pytest.pkg_req_id}/decision",
                          headers=_h(tokens["super"]),
                          json={"action": "approve"}, timeout=20)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "approved"
        detail = requests.get(f"{API}/admin/labels/{ppr_label['id']}",
                              headers=_h(tokens["super"]), timeout=20).json()
        lbl = detail.get("label") or detail
        assert lbl.get("payment_type") == "annual_subscription"
        assert lbl.get("subscription_tier") == "annual_vip"

    def test_super_admin_restore_package(self, tokens, ppr_label):
        # Restore to pay_per_release
        detail = requests.get(f"{API}/admin/labels/{ppr_label['id']}",
                              headers=_h(tokens["super"]), timeout=20).json()
        lbl = detail.get("label") or detail
        rev = int(lbl.get("package_revision") or 0)
        r = requests.patch(f"{API}/admin/labels/{ppr_label['id']}/package",
                           headers=_h(tokens["super"]),
                           json={"package": "pay_per_release", "reason": "iter73 restore",
                                 "expected_revision": rev, "confirm": True},
                           timeout=20)
        assert r.status_code == 200, r.text
        detail = requests.get(f"{API}/admin/labels/{ppr_label['id']}",
                              headers=_h(tokens["super"]), timeout=20).json()
        lbl = detail.get("label") or detail
        assert lbl.get("payment_type") == "pay_per_release"


# ------------------- Blacklist request flow -------------------
class TestBlacklistRequestFlow:
    def test_support_direct_blacklist_forbidden(self, tokens, ppr_label):
        r = requests.post(f"{API}/admin/labels/{ppr_label['id']}/blacklist",
                          headers=_h(tokens["support"]),
                          json={"reason": "test"}, timeout=20)
        assert r.status_code == 403, r.text[:200]

    def test_support_creates_pending_blacklist_request(self, tokens, ppr_label):
        _cleanup_pending(tokens, ppr_label["id"], "blacklist")
        r = requests.post(f"{API}/admin/labels/{ppr_label['id']}/blacklist-request",
                          headers=_h(tokens["support"]),
                          json={"action": "blacklist", "reason": "iter73 pytest"}, timeout=20)
        assert r.status_code == 200, r.text
        doc = r.json()
        assert doc["status"] == "pending"
        assert doc["action_type"] == "blacklist"
        pytest.bl_req_id = doc["id"]
        # live unchanged
        detail = requests.get(f"{API}/admin/labels/{ppr_label['id']}",
                              headers=_h(tokens["super"]), timeout=20).json()
        lbl = detail.get("label") or detail
        assert lbl.get("account_status") != "blacklisted"

    def test_duplicate_blacklist_pending_409(self, tokens, ppr_label):
        r = requests.post(f"{API}/admin/labels/{ppr_label['id']}/blacklist-request",
                          headers=_h(tokens["support"]),
                          json={"action": "blacklist", "reason": "dup"}, timeout=20)
        assert r.status_code == 409

    def test_support_cannot_approve_blacklist(self, tokens):
        r = requests.post(f"{API}/admin/sensitive-requests/{pytest.bl_req_id}/decision",
                          headers=_h(tokens["support"]),
                          json={"action": "approve"}, timeout=20)
        assert r.status_code == 403

    def test_reject_blacklist_leaves_label_unchanged(self, tokens, ppr_label):
        r = requests.post(f"{API}/admin/sensitive-requests/{pytest.bl_req_id}/decision",
                          headers=_h(tokens["super"]),
                          json={"action": "reject", "note": "iter73 reject"}, timeout=20)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "rejected"
        detail = requests.get(f"{API}/admin/labels/{ppr_label['id']}",
                              headers=_h(tokens["super"]), timeout=20).json()
        lbl = detail.get("label") or detail
        assert lbl.get("account_status") != "blacklisted"

    def test_approve_blacklist_and_restore(self, tokens, ppr_label):
        # Create a fresh request, approve, verify blacklisted, then unblacklist to restore
        r = requests.post(f"{API}/admin/labels/{ppr_label['id']}/blacklist-request",
                          headers=_h(tokens["support"]),
                          json={"action": "blacklist", "reason": "iter73 approve"}, timeout=20)
        assert r.status_code == 200, r.text
        req_id = r.json()["id"]
        r = requests.post(f"{API}/admin/sensitive-requests/{req_id}/decision",
                          headers=_h(tokens["super"]),
                          json={"action": "approve"}, timeout=20)
        assert r.status_code == 200, r.text
        detail = requests.get(f"{API}/admin/labels/{ppr_label['id']}",
                              headers=_h(tokens["super"]), timeout=20).json()
        lbl = detail.get("label") or detail
        assert lbl.get("account_status") == "blacklisted"
        # RESTORE
        r = requests.post(f"{API}/admin/labels/{ppr_label['id']}/unblacklist",
                         headers=_h(tokens["super"]), timeout=20)
        assert r.status_code == 200, r.text
        detail = requests.get(f"{API}/admin/labels/{ppr_label['id']}",
                              headers=_h(tokens["super"]), timeout=20).json()
        lbl = detail.get("label") or detail
        assert lbl.get("account_status") == "active"

    def test_blacklist_state_validation(self, tokens, ppr_label):
        # already active -> unblacklist request must 400
        r = requests.post(f"{API}/admin/labels/{ppr_label['id']}/blacklist-request",
                          headers=_h(tokens["support"]),
                          json={"action": "unblacklist", "reason": "should fail"}, timeout=20)
        assert r.status_code == 400, r.text[:200]


# ------------------- Scoped queue visibility -------------------
class TestScopedQueue:
    def test_finance_sees_only_package(self, tokens):
        r = requests.get(f"{API}/admin/sensitive-requests",
                         headers=_h(tokens["finance"]), timeout=20)
        assert r.status_code == 200
        items = r.json()
        types = {i.get("action_type") for i in items}
        assert types.issubset({"package"}), f"finance saw {types}"

    def test_support_sees_only_blacklist(self, tokens):
        r = requests.get(f"{API}/admin/sensitive-requests",
                         headers=_h(tokens["support"]), timeout=20)
        assert r.status_code == 200
        items = r.json()
        types = {i.get("action_type") for i in items}
        assert types.issubset({"blacklist"}), f"support saw {types}"

    def test_release_no_view_perm_403(self, tokens):
        r = requests.get(f"{API}/admin/sensitive-requests",
                         headers=_h(tokens["release"]), timeout=20)
        assert r.status_code == 403


# ------------------- Super Admin direct actions -------------------
class TestSuperAdminDirect:
    def test_super_admin_direct_blacklist_and_unblacklist(self, tokens, ppr_label):
        r = requests.post(f"{API}/admin/labels/{ppr_label['id']}/blacklist",
                          headers=_h(tokens["super"]),
                          json={"reason": "iter73 super direct"}, timeout=20)
        assert r.status_code == 200, r.text
        detail = requests.get(f"{API}/admin/labels/{ppr_label['id']}",
                              headers=_h(tokens["super"]), timeout=20).json()
        lbl = detail.get("label") or detail
        assert lbl.get("account_status") == "blacklisted"
        r = requests.post(f"{API}/admin/labels/{ppr_label['id']}/unblacklist",
                          headers=_h(tokens["super"]), timeout=20)
        assert r.status_code == 200
        detail = requests.get(f"{API}/admin/labels/{ppr_label['id']}",
                              headers=_h(tokens["super"]), timeout=20).json()
        lbl = detail.get("label") or detail
        assert lbl.get("account_status") == "active"


# ------------------- RBAC validate warnings -------------------
class TestValidateWarnings:
    def test_redundant_package(self, tokens):
        r = requests.post(f"{API}/admin/access/validate",
                          headers=_h(tokens["super"]),
                          json={"permissions": ["labels.view", "labels.package", "labels.package.request"], "active": True},
                          timeout=20)
        assert r.status_code == 200, r.text
        codes = {w.get("code") for w in r.json().get("warnings", [])}
        assert "redundant_request" in codes, f"warnings: {r.json().get('warnings')}"

    def test_missing_prereq_blacklist(self, tokens):
        r = requests.post(f"{API}/admin/access/validate",
                          headers=_h(tokens["super"]),
                          json={"permissions": ["labels.blacklist"], "active": True},
                          timeout=20)
        assert r.status_code == 200
        warnings = r.json().get("warnings", [])
        # must find missing_prerequisite for labels.view under labels.blacklist
        found = any(w.get("code") == "missing_prerequisite" and w.get("permission") == "labels.blacklist" for w in warnings)
        assert found, f"warnings: {warnings}"


# ------------------- Regression Rate/Fee -------------------
class TestRateFeeRegression:
    def test_finance_rate_request_still_works(self, tokens):
        r = requests.get(f"{API}/admin/labels?limit=1", headers=_h(tokens["super"]), timeout=20).json()
        items = r.get("items") if isinstance(r, dict) else r
        assert items
        lbl = items[0]
        # cleanup
        lst = requests.get(f"{API}/admin/rate-changes?status=pending&label_id={lbl['id']}",
                           headers=_h(tokens["super"]), timeout=20).json()
        for p in lst or []:
            requests.post(f"{API}/admin/rate-changes/{p['id']}/decision",
                          headers=_h(tokens["super"]),
                          json={"action": "reject", "note": "cleanup"}, timeout=20)
        current = float(lbl.get("royalty_percentage_default", 60))
        proposed = current + 1 if current < 90 else current - 1
        r = requests.post(f"{API}/admin/labels/{lbl['id']}/rate-change/request",
                         headers=_h(tokens["finance"]),
                         json={"proposed_value": proposed, "reason": "iter73 regression"}, timeout=20)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "pending"
        # cleanup - reject
        rid = r.json()["id"]
        r = requests.post(f"{API}/admin/rate-changes/{rid}/decision",
                          headers=_h(tokens["super"]),
                          json={"action": "reject", "note": "iter73 cleanup"}, timeout=20)
        assert r.status_code == 200


# ------------------- Module regression -------------------
class TestModuleRegression:
    @pytest.mark.parametrize("role,endpoint,expected", [
        ("finance", "/admin/labels?limit=1", 200),
        ("finance", "/admin/payments?limit=1", 200),
        ("finance", "/withdraw/admin?limit=1", 200),
        ("support", "/tickets/admin?limit=1", 200),
        ("release", "/admin/releases?limit=1", 200),
    ])
    def test_module_access(self, tokens, role, endpoint, expected):
        r = requests.get(f"{API}{endpoint}", headers=_h(tokens[role]), timeout=20)
        assert r.status_code == expected, f"{role} {endpoint} -> {r.status_code}"
