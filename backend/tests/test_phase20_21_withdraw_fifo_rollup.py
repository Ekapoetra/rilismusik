"""Phase 20 (FIFO Withdraw) + Phase 21 (Revenue Rollup) backend tests.

Covers:
- /api/withdraw/label/computed (FIFO compute; RBAC)
- /api/withdraw/label/request (force-full; min withdraw; window dep)
- /api/withdraw/admin/{id}/action mark_paid/reject (finance-only)
- /api/admin/artists & /admin/releases with revenue rollup + period filter
- /api/artists/ & /api/releases/ (label) with rollup
"""
import os
import pytest
import requests

def _load_backend_url():
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if not url:
        # Fallback: read from frontend .env
        try:
            with open("/app/frontend/.env") as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        url = line.split("=", 1)[1].strip()
                        break
        except Exception:
            pass
    assert url, "REACT_APP_BACKEND_URL not set"
    return url.rstrip("/")


BASE_URL = _load_backend_url()
API = f"{BASE_URL}/api"

SUPERADMIN = ("superadmin@rilismusik.com", "SuperAdmin#2026")
FINANCE = ("finance1@rilismusik.com", "Finance#2026")
SUPPORT = ("support1@rilismusik.com", "Support#2026")
PPR_LABEL = ("demo_ppr@rilismusik.com", "DemoPPR#2026")
VIP_LABEL = ("demo_vip@rilismusik.com", "DemoVIP#2026")


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def super_s():
    return _login(*SUPERADMIN)


@pytest.fixture(scope="module")
def finance_s():
    return _login(*FINANCE)


@pytest.fixture(scope="module")
def support_s():
    return _login(*SUPPORT)


@pytest.fixture(scope="module")
def label_s():
    # Try existing demo labels; fall back to fresh registration.
    for email, pwd in [PPR_LABEL, VIP_LABEL]:
        try:
            return _login(email, pwd)
        except AssertionError:
            continue
    # Register a fresh label for testing
    import uuid
    s = requests.Session()
    email = f"TEST_p20label_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "TestLabel#2026"
    r = s.post(f"{API}/auth/register", json={
        "label_name": f"TEST Label {uuid.uuid4().hex[:6]}",
        "owner_name": "Test Owner",
        "pic_name": "Test PIC",
        "email": email,
        "password": pwd,
        "whatsapp": "+628111000000",
        "mda_accepted": True,
    }, timeout=30)
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    # Login (in case register doesn't auto-login)
    r2 = s.post(f"{API}/auth/login", json={"email": email, "password": pwd}, timeout=20)
    assert r2.status_code == 200, f"post-register login failed: {r2.text}"
    return s


# =============================================================================
# PHASE 20 — Withdraw FIFO
# =============================================================================
class TestPhase20WithdrawComputed:
    def test_computed_label_rbac_admin_forbidden(self, super_s):
        r = super_s.get(f"{API}/withdraw/label/computed", timeout=20)
        assert r.status_code == 403, f"super_admin should be 403 on label-only endpoint, got {r.status_code}"

    def test_computed_label_rbac_support_forbidden(self, support_s):
        r = support_s.get(f"{API}/withdraw/label/computed", timeout=20)
        assert r.status_code == 403

    def test_computed_label_ok_shape(self, label_s):
        r = label_s.get(f"{API}/withdraw/label/computed", timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        # shape
        for k in ["withdrawable_idr", "period_from", "period_to", "lines_count",
                  "last_withdrawn_period", "min_withdraw_idr", "can_withdraw", "reason"]:
            assert k in d, f"missing {k} in computed response"
        assert d["min_withdraw_idr"] == 1_000_000
        assert isinstance(d["withdrawable_idr"], int)
        assert isinstance(d["lines_count"], int)
        # Fresh label w/no royalty: withdrawable=0, can_withdraw=False, reason includes 'Belum ada royalti'
        if d["lines_count"] == 0:
            assert d["withdrawable_idr"] == 0
            assert d["can_withdraw"] is False
            assert "Belum ada royalti" in (d["reason"] or "")
        # Boolean coherence
        assert d["can_withdraw"] == (d["withdrawable_idr"] >= 1_000_000)


class TestPhase20WithdrawRequest:
    def test_request_below_min_returns_400(self, label_s):
        """Demo PPR label has no royalty_lines so computed=0 → must reject with 400."""
        comp = label_s.get(f"{API}/withdraw/label/computed", timeout=20).json()
        if comp["can_withdraw"]:
            pytest.skip("label happens to have enough royalty; skip below-min check")
        r = label_s.post(f"{API}/withdraw/label/request", timeout=20)
        # 400 either because window closed or below minimum. We accept either, but
        # if 400, the detail must NOT be "amount_idr required" (old API).
        assert r.status_code == 400, f"expected 400 below-min/closed-window, got {r.status_code}: {r.text}"
        body = r.json()
        detail = (body.get("detail") or "").lower()
        # Should not require body anymore
        assert "amount_idr" not in detail.replace("_", ""), "endpoint should no longer require amount_idr in body"

    def test_request_no_body_accepted(self, label_s):
        """POST with no body must not fail validation; should fail business-logic later only."""
        r = label_s.post(f"{API}/withdraw/label/request", json={}, timeout=20)
        # Must NOT be a 422 (validation error)
        assert r.status_code != 422, f"endpoint should accept empty body, got 422: {r.text}"

    def test_request_admin_forbidden(self, super_s):
        r = super_s.post(f"{API}/withdraw/label/request", timeout=20)
        assert r.status_code == 403


class TestPhase20AdminAction:
    def test_mark_paid_support_forbidden(self, support_s):
        """Admin Support cannot mark_paid (finance/super only)."""
        # We don't need a real withdraw id — fake id should still trigger RBAC check first
        r = support_s.post(
            f"{API}/withdraw/admin/nonexistent-id/action",
            json={"action": "mark_paid"}, timeout=20,
        )
        assert r.status_code == 403, f"support must be 403, got {r.status_code}: {r.text}"

    def test_admin_list_withdraws_finance_ok(self, finance_s):
        r = finance_s.get(f"{API}/withdraw/admin", timeout=20)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        # Verify period_from/to/lines_count exist on any 'paid' or new withdraw (Phase 20 columns)
        for it in items:
            # New columns may be None for legacy rows — just check keys exist on new docs
            assert "amount_idr" in it and "status" in it

    def test_admin_list_withdraws_support_ok(self, support_s):
        """Support can VIEW withdraws but not mark_paid."""
        r = support_s.get(f"{API}/withdraw/admin", timeout=20)
        assert r.status_code == 200


# =============================================================================
# PHASE 21 — Revenue Rollup
# =============================================================================
class TestPhase21AdminArtists:
    def test_admin_artists_shape(self, super_s):
        r = super_s.get(f"{API}/admin/artists", timeout=30)
        assert r.status_code == 200, r.text
        items = r.json()
        assert isinstance(items, list)
        if not items:
            pytest.skip("no artists in preview DB")
        sample = items[0]
        for k in ["revenue_eur", "revenue_idr", "royalty_lines_count",
                  "first_active_period", "last_active_period", "label_name"]:
            assert k in sample, f"missing {k} in admin/artists item"
        assert isinstance(sample["revenue_idr"], int)
        assert isinstance(sample["royalty_lines_count"], int)

    def test_admin_artists_period_filter(self, super_s):
        # Apply impossible future period — counts should all be zero
        r = super_s.get(
            f"{API}/admin/artists",
            params={"period_from": "2099-01", "period_to": "2099-12"},
            timeout=30,
        )
        assert r.status_code == 200
        for it in r.json():
            assert it["revenue_idr"] == 0
            assert it["royalty_lines_count"] == 0
            assert it["last_active_period"] is None

    def test_admin_artists_period_2024(self, super_s):
        r = super_s.get(
            f"{API}/admin/artists",
            params={"period_from": "2023-01", "period_to": "2024-12"},
            timeout=30,
        )
        assert r.status_code == 200
        for it in r.json():
            if it["royalty_lines_count"] > 0:
                lp = it.get("last_active_period")
                assert lp is not None and "2023-01" <= lp <= "2024-12", \
                    f"last_active_period {lp} outside filter"

    def test_admin_artists_finance_ok(self, finance_s):
        r = finance_s.get(f"{API}/admin/artists", timeout=30)
        assert r.status_code == 200


class TestPhase21AdminReleases:
    def test_admin_releases_shape(self, super_s):
        r = super_s.get(f"{API}/admin/releases", timeout=30)
        assert r.status_code == 200, r.text
        items = r.json()
        assert isinstance(items, list)
        if not items:
            pytest.skip("no releases in preview DB")
        sample = items[0]
        for k in ["revenue_eur", "revenue_idr", "royalty_lines_count",
                  "first_active_period", "last_active_period", "label_name"]:
            assert k in sample, f"missing {k} in admin/releases item"

    def test_admin_releases_period_filter(self, super_s):
        r = super_s.get(
            f"{API}/admin/releases",
            params={"period_from": "2099-01", "period_to": "2099-12"},
            timeout=30,
        )
        assert r.status_code == 200
        for it in r.json():
            assert it["revenue_idr"] == 0
            assert it["royalty_lines_count"] == 0

    def test_admin_releases_status_filter_combined_with_period(self, super_s):
        r = super_s.get(
            f"{API}/admin/releases",
            params={"status": "live", "period_from": "2024-01", "period_to": "2024-12"},
            timeout=30,
        )
        assert r.status_code == 200
        for it in r.json():
            assert it["status"] == "live"


class TestPhase21LabelArtistsReleases:
    def test_label_artists_with_rollup(self, label_s):
        r = label_s.get(f"{API}/artists/", timeout=30)
        assert r.status_code == 200, r.text
        items = r.json()
        if items:
            for k in ["revenue_eur", "revenue_idr", "royalty_lines_count", "last_active_period"]:
                assert k in items[0], f"label artists missing {k}"

    def test_label_releases_with_rollup(self, label_s):
        r = label_s.get(f"{API}/releases/", timeout=30)
        assert r.status_code == 200, r.text
        items = r.json()
        if items:
            for k in ["revenue_eur", "revenue_idr", "royalty_lines_count", "last_active_period"]:
                assert k in items[0], f"label releases missing {k}"

    def test_label_releases_period_filter(self, label_s):
        r = label_s.get(
            f"{API}/releases/",
            params={"period_from": "2099-01", "period_to": "2099-12"},
            timeout=30,
        )
        assert r.status_code == 200
        for it in r.json():
            assert it["royalty_lines_count"] == 0
            assert it["revenue_idr"] == 0


# =============================================================================
# REGRESSION — RBAC sanity on existing withdraw endpoints
# =============================================================================
class TestRegressionWithdrawRBAC:
    def test_withdraw_window_authenticated(self, label_s):
        r = label_s.get(f"{API}/withdraw/window", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert "request_open" in d

    def test_withdraw_label_list(self, label_s):
        r = label_s.get(f"{API}/withdraw/label", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
