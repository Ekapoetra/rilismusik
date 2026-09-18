"""Iter89 — Post bridge-removal permission enforcement & delegation regression.

Coverage:
  - Regression: Admin Finance/Release/Support can still hit their permission-gated endpoints (200).
  - Cross-domain deny: 403 PERMISSION_DENIED for role-mismatched calls.
  - Delegation: labels.bank.verify — Super 200; Finance 403 by default; grant → 200; restore role afterward.
  - CMS PATCH permission gate: Finance 403, Content not 403.
Non-destructive: CMS PATCH body is empty dict; admin_finance permissions restored in teardown.
"""
import os
import copy
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"

SUPER = {"email": "superadmin@rilismusik.com", "password": "SuperAdmin#2026"}
FIN = {"email": "finance1@rilismusik.com", "password": "Finance#2026"}
REL = {"email": "release1@rilismusik.com", "password": "Release#2026"}
SUP = {"email": "support1@rilismusik.com", "password": "Support#2026"}
CON = {"email": "content1@rilismusik.com", "password": "Content#2026"}


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text[:200]}"
    j = r.json()
    return j.get("access_token") or j.get("token")


def _hdr(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def _assert_403_perm_denied(resp):
    assert resp.status_code == 403, f"expected 403 got {resp.status_code}: {resp.text[:300]}"
    try:
        body = resp.json()
    except Exception:
        pytest.fail(f"non-json 403 body: {resp.text[:200]}")
    detail = body.get("detail")
    if isinstance(detail, dict):
        assert detail.get("code") == "PERMISSION_DENIED", f"expected PERMISSION_DENIED, got {detail}"
    else:
        pytest.fail(f"detail is not a dict: {detail}")


@pytest.fixture(scope="module")
def super_tok():
    return _login(**SUPER)


@pytest.fixture(scope="module")
def fin_tok():
    return _login(**FIN)


@pytest.fixture(scope="module")
def rel_tok():
    return _login(**REL)


@pytest.fixture(scope="module")
def sup_tok():
    return _login(**SUP)


@pytest.fixture(scope="module")
def con_tok():
    return _login(**CON)


# ─── Regression: permission-based access still 200 ───────────────────────
def test_finance_withdraw_admin_list(fin_tok):
    r = requests.get(f"{API}/withdraw/admin", headers=_hdr(fin_tok), timeout=30)
    assert r.status_code == 200, r.text[:300]


def test_finance_refresh_revenue(fin_tok):
    r = requests.post(f"{API}/admin/dashboard/refresh-revenue", headers=_hdr(fin_tok), timeout=60)
    assert r.status_code == 200, r.text[:300]


def test_release_ready_to_live(rel_tok):
    r = requests.get(f"{API}/admin/releases/ready-to-live", headers=_hdr(rel_tok), timeout=30)
    assert r.status_code == 200, r.text[:300]


def test_support_kyc_list(sup_tok):
    r = requests.get(f"{API}/admin/kyc", headers=_hdr(sup_tok), timeout=30)
    assert r.status_code == 200, r.text[:300]


# ─── Cross-domain deny with PERMISSION_DENIED code ───────────────────────
def test_support_cannot_refresh_revenue(sup_tok):
    r = requests.post(f"{API}/admin/dashboard/refresh-revenue", headers=_hdr(sup_tok), timeout=30)
    _assert_403_perm_denied(r)


def test_release_cannot_view_withdraw(rel_tok):
    r = requests.get(f"{API}/withdraw/admin", headers=_hdr(rel_tok), timeout=30)
    _assert_403_perm_denied(r)


# ─── CMS content op permission gate ──────────────────────────────────────
def test_finance_cannot_patch_cms(fin_tok):
    r = requests.patch(f"{API}/cms/landing", headers=_hdr(fin_tok), json={}, timeout=30)
    _assert_403_perm_denied(r)


def test_content_can_patch_cms(con_tok):
    r = requests.patch(f"{API}/cms/landing", headers=_hdr(con_tok), json={}, timeout=30)
    assert r.status_code != 403, f"content admin unexpectedly 403: {r.text[:300]}"


# ─── Delegation: labels.bank.verify ──────────────────────────────────────
def test_bank_verification_delegation_flow(super_tok):
    # Super admin baseline: 200
    r_super = requests.get(f"{API}/admin/bank-verifications", headers=_hdr(super_tok), timeout=30)
    assert r_super.status_code == 200, r_super.text[:300]

    # Finance default: 403
    fin_tok = _login(**FIN)
    r_fin = requests.get(f"{API}/admin/bank-verifications", headers=_hdr(fin_tok), timeout=30)
    _assert_403_perm_denied(r_fin)

    # Fetch existing admin_finance role permissions
    r_role = requests.get(f"{API}/admin/access/roles", headers=_hdr(super_tok), timeout=30)
    assert r_role.status_code == 200, r_role.text[:300]
    roles = r_role.json()
    roles_list = roles if isinstance(roles, list) else roles.get("roles", [])
    fin_role = next((x for x in roles_list if (x.get("id") or x.get("key")) == "admin_finance"), None)
    assert fin_role, f"admin_finance role not found. Payload sample: {str(roles)[:400]}"
    original_perms = copy.deepcopy(fin_role.get("permissions") or [])
    assert "labels.bank.verify" not in original_perms, "precondition failed: finance already has labels.bank.verify"

    new_perms = list(original_perms) + ["labels.bank.verify"]

    try:
        # PATCH to add delegation
        r_patch = requests.patch(
            f"{API}/admin/access/roles/admin_finance",
            headers=_hdr(super_tok),
            json={"permissions": new_perms},
            timeout=30,
        )
        assert r_patch.status_code == 200, f"patch failed: {r_patch.status_code} {r_patch.text[:400]}"

        # Finance must re-login (session invalidated by token_version bump)
        fin_tok2 = _login(**FIN)
        r_fin2 = requests.get(f"{API}/admin/bank-verifications", headers=_hdr(fin_tok2), timeout=30)
        assert r_fin2.status_code == 200, f"finance still denied after delegation: {r_fin2.status_code} {r_fin2.text[:300]}"
    finally:
        # Restore original permissions
        r_restore = requests.patch(
            f"{API}/admin/access/roles/admin_finance",
            headers=_hdr(super_tok),
            json={"permissions": original_perms},
            timeout=30,
        )
        assert r_restore.status_code == 200, f"restore failed: {r_restore.status_code} {r_restore.text[:400]}"
        # Verify final state
        r_verify = requests.get(f"{API}/admin/access/roles", headers=_hdr(super_tok), timeout=30)
        rv = r_verify.json()
        rv_list = rv if isinstance(rv, list) else rv.get("roles", [])
        fin_after = next((x for x in rv_list if (x.get("id") or x.get("key")) == "admin_finance"), None)
        assert "labels.bank.verify" not in (fin_after.get("permissions") or []), "cleanup failed"
