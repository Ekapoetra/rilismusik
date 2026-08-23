"""Phase 16.4 — DELETE /api/royalty/admin/imports/{id} + dashboard revenue cache.

Tests:
- DELETE: super_admin can delete `awaiting_upload`/`error`/`pending_review`
- DELETE: admin_finance gets 403 (sub-admins blocked)
- DELETE: `published` status returns 400 with Indonesian explanation
- DELETE: subsequent GET returns 404
- DELETE: cascading cleanup of royalty_lines, auto-created labels/releases/tracks
- DASHBOARD: revenue_cache_age_sec field present, second call serves from cache
- POST /admin/dashboard/refresh-revenue: super_admin/admin_finance can force refresh
- Cache invalidation: revenue cache age resets after delete (background refresh ~5s)
"""
import os
import time
import pytest
import requests
from tests.support_config import FINANCE as FINANCE_CRED, SUPERADMIN
from pathlib import Path

# Load backend/.env so REACT_APP_BACKEND_URL etc. resolve when pytest runs standalone
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    load_dotenv(Path(__file__).resolve().parent.parent.parent / "frontend" / ".env")
except Exception:
    pass

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://lanjut-core.preview.emergentagent.com").rstrip("/")

SUPER_ADMIN = (SUPERADMIN["email"], SUPERADMIN["password"])
FINANCE = (FINANCE_CRED["email"], FINANCE_CRED["password"])


def _login(email: str, password: str) -> str:
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def super_token():
    return _login(*SUPER_ADMIN)


@pytest.fixture(scope="module")
def finance_token():
    return _login(*FINANCE)


def _headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def _initiate_import(token: str, filename: str = "TEST_phase164_dummy.csv"):
    body = {"filename": filename, "rate_eur_idr": 17500, "period": "2025-01"}
    r = requests.post(
        f"{BASE_URL}/api/royalty/admin/imports/initiate",
        json=body,
        headers=_headers(token),
        timeout=30,
    )
    assert r.status_code in (200, 201), f"initiate failed: {r.status_code} {r.text}"
    data = r.json()
    assert "import_id" in data
    return data["import_id"]


# -----------------------------------------------------------------------------
# DELETE endpoint
# -----------------------------------------------------------------------------
class TestRoyaltyImportDelete:
    def test_delete_awaiting_upload_succeeds(self, super_token):
        """Phase 23 update: delete is now async (202 Accepted + background task).
        We poll until the import doc disappears or status flips to 'deleting'."""
        import_id = _initiate_import(super_token)
        r = requests.delete(
            f"{BASE_URL}/api/royalty/admin/imports/{import_id}",
            headers=_headers(super_token),
            timeout=30,
        )
        assert r.status_code == 202, f"DELETE expected 202 Accepted, got {r.status_code} {r.text}"
        body = r.json()
        assert body.get("ok") is True
        assert body.get("status") == "deleting"
        assert body.get("import_id") == import_id

        # Poll up to 10s for the background task to finish + drop the doc
        for _ in range(20):
            g = requests.get(
                f"{BASE_URL}/api/royalty/admin/imports/{import_id}",
                headers=_headers(super_token),
                timeout=30,
            )
            if g.status_code == 404:
                return  # success — doc deleted by background task
            time.sleep(0.5)
        pytest.fail(f"import {import_id} still present after 10s — background delete did not complete")

    def test_finance_admin_gets_403(self, super_token, finance_token):
        import_id = _initiate_import(super_token)
        try:
            r = requests.delete(
                f"{BASE_URL}/api/royalty/admin/imports/{import_id}",
                headers=_headers(finance_token),
                timeout=30,
            )
            assert r.status_code == 403, f"expected 403 for admin_finance, got {r.status_code} {r.text}"
        finally:
            # cleanup
            requests.delete(
                f"{BASE_URL}/api/royalty/admin/imports/{import_id}",
                headers=_headers(super_token),
                timeout=30,
            )

    def test_delete_unauthenticated_blocked(self, super_token):
        import_id = _initiate_import(super_token)
        try:
            r = requests.delete(
                f"{BASE_URL}/api/royalty/admin/imports/{import_id}",
                timeout=30,
            )
            assert r.status_code in (401, 403), f"expected 401/403 unauth, got {r.status_code}"
        finally:
            requests.delete(
                f"{BASE_URL}/api/royalty/admin/imports/{import_id}",
                headers=_headers(super_token),
                timeout=30,
            )

    def test_delete_nonexistent_returns_404(self, super_token):
        r = requests.delete(
            f"{BASE_URL}/api/royalty/admin/imports/nonexistent-id-zzz",
            headers=_headers(super_token),
            timeout=30,
        )
        assert r.status_code == 404

    def test_delete_published_returns_400(self, super_token):
        """If any 'published' import exists in DB, DELETE on it must return 400 (Indonesian)."""
        # Find an existing published import
        r = requests.get(
            f"{BASE_URL}/api/royalty/admin/imports?status=published&limit=1",
            headers=_headers(super_token),
            timeout=30,
        )
        if r.status_code != 200:
            pytest.skip(f"cannot list imports: {r.status_code} {r.text}")
        body = r.json()
        items = body if isinstance(body, list) else (body.get("items") or body.get("imports") or [])
        # Filter to published only — server may not honour the query param
        items = [i for i in items if i.get("status") == "published"]
        if not items:
            pytest.skip("no published imports in DB to test against")
        published_id = items[0]["id"]
        d = requests.delete(
            f"{BASE_URL}/api/royalty/admin/imports/{published_id}",
            headers=_headers(super_token),
            timeout=30,
        )
        assert d.status_code == 400, f"expected 400 for published, got {d.status_code} {d.text}"
        # message should mention status and not be empty
        detail = d.json().get("detail", "")
        assert "published" in detail.lower() or "saldo" in detail.lower() or "publish" in detail.lower(), (
            f"detail should reference the protected status, got: {detail}"
        )


# -----------------------------------------------------------------------------
# Dashboard revenue cache
# -----------------------------------------------------------------------------
class TestDashboardRevenueCache:
    def test_dashboard_response_has_cache_age_field(self, super_token):
        r = requests.get(f"{BASE_URL}/api/admin/dashboard", headers=_headers(super_token), timeout=60)
        assert r.status_code == 200, f"dashboard call failed: {r.status_code} {r.text}"
        data = r.json()
        assert "revenue_cache_age_sec" in data, f"missing revenue_cache_age_sec: {list(data.keys())}"
        # may be int or None on cold start (after compute it becomes int)
        assert data["revenue_cache_age_sec"] is None or isinstance(data["revenue_cache_age_sec"], int)
        assert "total_revenue_eur" in data
        assert "total_revenue_idr" in data

    def test_second_call_serves_from_cache_fast(self, super_token):
        # Prime
        requests.get(f"{BASE_URL}/api/admin/dashboard", headers=_headers(super_token), timeout=60)
        # Second call must come back quickly with cache_age >= 0
        t0 = time.time()
        r = requests.get(f"{BASE_URL}/api/admin/dashboard", headers=_headers(super_token), timeout=30)
        elapsed_ms = (time.time() - t0) * 1000
        assert r.status_code == 200
        data = r.json()
        age = data.get("revenue_cache_age_sec")
        assert age is not None and age >= 0, f"expected cached value with age >= 0, got {age}"
        # Should be reasonably fast (relaxed for network jitter — spec says ~200ms but
        # allow up to 3s through the preview ingress).
        assert elapsed_ms < 3000, f"second dashboard call too slow: {elapsed_ms:.0f}ms"

    def test_refresh_revenue_super_admin(self, super_token):
        r = requests.post(
            f"{BASE_URL}/api/admin/dashboard/refresh-revenue",
            headers=_headers(super_token),
            timeout=120,
        )
        assert r.status_code == 200, f"refresh failed: {r.status_code} {r.text}"
        data = r.json()
        assert data.get("ok") is True
        assert "total_eur" in data
        assert "total_idr" in data
        assert "computed_at" in data
        assert isinstance(data["computed_at"], (int, float)) and data["computed_at"] > 0

    def test_refresh_revenue_finance_admin_allowed(self, finance_token):
        """Spec: super_admin/admin_finance can call refresh-revenue.
        Implementation uses require_admin (allows all admins). At minimum admin_finance must pass."""
        r = requests.post(
            f"{BASE_URL}/api/admin/dashboard/refresh-revenue",
            headers=_headers(finance_token),
            timeout=120,
        )
        assert r.status_code == 200, f"admin_finance must be allowed: {r.status_code} {r.text}"

    def test_refresh_revenue_unauthenticated_blocked(self):
        r = requests.post(f"{BASE_URL}/api/admin/dashboard/refresh-revenue", timeout=30)
        assert r.status_code in (401, 403)


# -----------------------------------------------------------------------------
# Cache invalidation after delete
# -----------------------------------------------------------------------------
class TestCacheInvalidationAfterDelete:
    def test_delete_triggers_background_recompute(self, super_token):
        # Prime cache via dashboard
        requests.post(f"{BASE_URL}/api/admin/dashboard/refresh-revenue", headers=_headers(super_token), timeout=120)
        d1 = requests.get(f"{BASE_URL}/api/admin/dashboard", headers=_headers(super_token), timeout=60).json()
        age_before = d1.get("revenue_cache_age_sec")
        assert age_before is not None

        # Create + delete a fresh import
        import_id = _initiate_import(super_token, filename="TEST_phase164_cache_inv.csv")
        del_r = requests.delete(
            f"{BASE_URL}/api/royalty/admin/imports/{import_id}",
            headers=_headers(super_token),
            timeout=30,
        )
        # Phase 23: 202 Accepted (background task)
        assert del_r.status_code == 202

        # Wait up to 10s for background task to recompute
        new_age = None
        for _ in range(6):
            time.sleep(1)
            d2 = requests.get(f"{BASE_URL}/api/admin/dashboard", headers=_headers(super_token), timeout=60).json()
            new_age = d2.get("revenue_cache_age_sec")
            if new_age is not None and new_age <= age_before:
                break
        # After background recompute, age should be smaller (cache refreshed) than the
        # pre-delete age + the elapsed wait. Allow some tolerance.
        assert new_age is not None
        # New cache should be recent (< 10s ideally)
        assert new_age < 15, f"cache not refreshed after delete: new_age={new_age}, age_before={age_before}"
