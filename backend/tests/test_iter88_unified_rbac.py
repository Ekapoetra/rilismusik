"""Iter88 — Unified Admin Roles & Permissions (PRD) regression tests.

Verifies:
  - Super Admin implicit full access via /api/admin/navigation.
  - Admin Finance & Admin Release permission sets.
  - Granular gating on /api/withdraw/admin/{id}/action (403 PERMISSION_DENIED).
  - Session invalidation via role PATCH (token_version bump).
  - Role protection: cannot delete super_admin (400) or in-use dynamic role (409).
  - Work Queue permission-based (my/team) & PUT /responsibilities -> 410.
  - Config-review endpoints.
Non-destructive: only 403 path exercised on withdraw actions.
"""
import os
import uuid
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://lanjut-core.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

SUPER = {"email": "superadmin@rilismusik.com", "password": "SuperAdmin#2026"}
FIN = {"email": "finance1@rilismusik.com", "password": "Finance#2026"}
REL = {"email": "release1@rilismusik.com", "password": "Release#2026"}


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text[:300]}"
    return r.json().get("access_token") or r.json().get("token")


def _hdr(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def super_tok():
    return _login(SUPER["email"], SUPER["password"])


@pytest.fixture(scope="module")
def fin_tok():
    return _login(FIN["email"], FIN["password"])


@pytest.fixture(scope="module")
def rel_tok():
    return _login(REL["email"], REL["password"])


# ─── Navigation / permission surface ────────────────────────────────────────
def test_super_admin_navigation(super_tok):
    r = requests.get(f"{API}/admin/navigation", headers=_hdr(super_tok), timeout=30)
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    role = d.get("role")
    if isinstance(role, dict):
        role = role.get("id")
    assert role == "super_admin"
    perms = d.get("permissions") or []
    # Super admin should have many permissions (implicit full)
    assert len(perms) >= 30, f"super admin should have many perms, got {len(perms)}"
    for p in ("withdraw.approve", "withdraw.pay", "cms.manage", "releases.delete", "royalty.publish"):
        assert p in perms, f"super admin missing {p}"


def test_finance_navigation_permissions(fin_tok):
    r = requests.get(f"{API}/admin/navigation", headers=_hdr(fin_tok), timeout=30)
    assert r.status_code == 200
    d = r.json()
    perms = set(d.get("permissions") or [])
    for req in ("withdraw.manage", "withdraw.approve", "withdraw.pay", "royalty.publish"):
        assert req in perms, f"finance missing {req}: {sorted(perms)}"
    assert "cms.manage" not in perms, "finance should NOT have cms.manage (default-deny)"


def test_release_navigation_permissions(rel_tok):
    r = requests.get(f"{API}/admin/navigation", headers=_hdr(rel_tok), timeout=30)
    assert r.status_code == 200
    perms = set(r.json().get("permissions") or [])
    for req in ("releases.review", "releases.go_live", "releases.takedown", "releases.delete"):
        assert req in perms, f"release missing {req}"
    assert "withdraw.approve" not in perms


# ─── Role protection ────────────────────────────────────────────────────────
def test_delete_super_admin_role_forbidden(super_tok):
    r = requests.delete(f"{API}/admin/access/roles/super_admin", headers=_hdr(super_tok), timeout=30)
    assert r.status_code == 400, f"expected 400 got {r.status_code}: {r.text[:200]}"


def test_delete_in_use_role_conflict(super_tok):
    r = requests.delete(f"{API}/admin/access/roles/admin_finance", headers=_hdr(super_tok), timeout=30)
    assert r.status_code == 409, f"expected 409 got {r.status_code}: {r.text[:200]}"


# ─── Config review baseline ─────────────────────────────────────────────────
def test_config_review_baseline(super_tok):
    r = requests.get(f"{API}/admin/access/config-review", headers=_hdr(super_tok), timeout=30)
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    # Expect count=0 for clean baseline
    count = d.get("count", d.get("pending", 0))
    assert isinstance(count, int)
    # Also verify the complete endpoint works
    r2 = requests.post(f"{API}/admin/access/config-review/complete", headers=_hdr(super_tok), timeout=30)
    assert r2.status_code == 200, r2.text[:300]
    d2 = r2.json()
    assert "reviewed" in d2 or "count" in d2 or "ok" in d2


# ─── Work queue permission-based ─────────────────────────────────────────────
def test_work_queue_finance_scope_my(fin_tok):
    r = requests.get(f"{API}/admin/work/queue?scope=my", headers=_hdr(fin_tok), timeout=30)
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    items = d.get("items") or []
    allowed = {"withdraw_verification", "bank_verification", "addon_processing", "wami_registration"}
    forbidden = {"release_review", "kyc_review", "support_ticket"}
    types_seen = {it.get("type") for it in items}
    assert not (types_seen & forbidden), f"finance saw forbidden types: {types_seen & forbidden}"
    # allowed subset (finance may or may not have any pending, but no forbidden should appear)
    assert types_seen.issubset(allowed | {None}) or types_seen.issubset(allowed), (
        f"unexpected finance types: {types_seen}"
    )


def test_work_queue_team_super_manager(super_tok):
    r = requests.get(f"{API}/admin/work/queue?scope=team", headers=_hdr(super_tok), timeout=30)
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert d.get("is_manager") is True
    items = d.get("items") or []
    if items:
        for it in items[:5]:
            assert "responsible_roles" in it, f"item missing responsible_roles: {it}"


def test_work_responsibilities_retired(super_tok):
    r = requests.put(
        f"{API}/admin/work/responsibilities",
        headers=_hdr(super_tok),
        json={},
        timeout=30,
    )
    assert r.status_code == 410, f"expected 410 got {r.status_code}: {r.text[:200]}"


# ─── Granular withdraw gating + cleanup ─────────────────────────────────────
def test_granular_withdraw_gating_and_session_invalidation(super_tok):
    """Create temp role + user with view/manage only (no approve/pay). Verify 403 gating.
    Also verify token_version bump on role PATCH invalidates old finance token.
    """
    role_id = None
    admin_user_id = None
    temp_email = f"iter88-{uuid.uuid4().hex[:8]}@example.com"
    temp_pass = "Iter88Temp#2026Aa!"
    try:
        # 1) Create dynamic role
        role_payload = {
            "id": f"iter88_temp_{uuid.uuid4().hex[:6]}",
            "name": "Iter88 Temp Limited",
            "permissions": ["dashboard.view", "withdraw.view", "withdraw.manage"],
        }
        rr = requests.post(f"{API}/admin/access/roles", headers=_hdr(super_tok), json=role_payload, timeout=30)
        assert rr.status_code in (200, 201), f"create role failed: {rr.status_code} {rr.text[:300]}"
        role_body = rr.json()
        role_id = role_body.get("id") or role_body.get("role", {}).get("id") or role_payload["id"]

        # 2) Create temp admin user with that role
        ur_payload = {
            "email": temp_email,
            "password": temp_pass,
            "name": "Iter88 Temp",
            "role": role_id,
        }
        ur = requests.post(f"{API}/admin/admin-users", headers=_hdr(super_tok), json=ur_payload, timeout=30)
        if ur.status_code not in (200, 201):
            # Try alternate schema
            ur_payload2 = {**ur_payload, "role_id": role_id, "full_name": "Iter88 Temp"}
            ur = requests.post(f"{API}/admin/admin-users", headers=_hdr(super_tok), json=ur_payload2, timeout=30)
        assert ur.status_code in (200, 201), f"create admin-user failed: {ur.status_code} {ur.text[:300]}"
        body = ur.json()
        admin_user_id = body.get("id") or body.get("user", {}).get("id") or body.get("_id")
        assert admin_user_id, f"no user id in response: {body}"

        # 3) Login as temp user; check its navigation lacks withdraw.pay
        temp_tok = _login(temp_email, temp_pass)
        rn = requests.get(f"{API}/admin/navigation", headers=_hdr(temp_tok), timeout=30)
        assert rn.status_code == 200
        temp_perms = set(rn.json().get("permissions") or [])
        assert "withdraw.pay" not in temp_perms, f"temp role unexpectedly has withdraw.pay: {temp_perms}"
        assert "withdraw.approve" not in temp_perms
        assert "withdraw.manage" in temp_perms

        # 4) Try to find a withdraw id via super admin
        wr = requests.get(f"{API}/withdraw/admin", headers=_hdr(super_tok), timeout=30)
        wid = None
        if wr.status_code == 200:
            data = wr.json()
            items = data if isinstance(data, list) else (data.get("items") or data.get("results") or [])
            if items:
                wid = items[0].get("id") or items[0].get("_id")

        # 5) 403 gating checks
        if wid:
            for action, needed in (("mark_paid", "withdraw.pay"), ("approve", "withdraw.approve")):
                ar = requests.post(
                    f"{API}/withdraw/admin/{wid}/action",
                    headers=_hdr(temp_tok),
                    json={"action": action},
                    timeout=30,
                )
                assert ar.status_code == 403, f"{action}: expected 403 got {ar.status_code} {ar.text[:300]}"
                try:
                    detail = ar.json().get("detail") or {}
                    if isinstance(detail, dict):
                        assert detail.get("code") == "PERMISSION_DENIED", f"detail.code != PERMISSION_DENIED: {detail}"
                        assert detail.get("permission") == needed, f"detail.permission mismatch: {detail}"
                except ValueError:
                    pytest.fail(f"non-json 403 body: {ar.text[:200]}")
        else:
            print("[iter88] no withdraw id available; skipping granular 403 body check")

        # 6) Session invalidation: pre-patch finance token
        old_fin_tok = _login(FIN["email"], FIN["password"])
        # Get current finance permissions
        cur = requests.get(f"{API}/admin/access/roles/admin_finance", headers=_hdr(super_tok), timeout=30)
        cur_perms = None
        if cur.status_code == 200:
            body = cur.json()
            cur_perms = body.get("permissions") or (body.get("role") or {}).get("permissions")
        if not cur_perms:
            # fallback: list
            lst = requests.get(f"{API}/admin/access/roles", headers=_hdr(super_tok), timeout=30)
            if lst.status_code == 200:
                body = lst.json()
                roles = body if isinstance(body, list) else (body.get("roles") or [])
                for role in roles:
                    if role.get("id") == "admin_finance":
                        cur_perms = role.get("permissions")
                        break
        assert cur_perms, "cannot resolve current admin_finance permissions"

        # PATCH same permissions -> should still bump token_version
        pr = requests.patch(
            f"{API}/admin/access/roles/admin_finance",
            headers=_hdr(super_tok),
            json={"permissions": cur_perms},
            timeout=30,
        )
        assert pr.status_code in (200, 204), f"patch failed: {pr.status_code} {pr.text[:300]}"

        time.sleep(1)
        me = requests.get(f"{API}/auth/me", headers=_hdr(old_fin_tok), timeout=30)
        assert me.status_code == 401, f"pre-patch token should be invalidated; got {me.status_code}"
        # Fresh login works
        new_tok = _login(FIN["email"], FIN["password"])
        me2 = requests.get(f"{API}/auth/me", headers=_hdr(new_tok), timeout=30)
        assert me2.status_code == 200

    finally:
        # Cleanup: user first, then role
        if admin_user_id:
            dr = requests.delete(f"{API}/admin/admin-users/{admin_user_id}", headers=_hdr(super_tok), timeout=30)
            print(f"[cleanup] delete user {admin_user_id} -> {dr.status_code}")
        if role_id:
            dr2 = requests.delete(f"{API}/admin/access/roles/{role_id}", headers=_hdr(super_tok), timeout=30)
            print(f"[cleanup] delete role {role_id} -> {dr2.status_code}")
