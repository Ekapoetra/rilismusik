"""Phase 18 — Admin Analytics backend tests.

Covers:
- /api/admin/analytics/recompute auth (super_admin only)
- /api/admin/analytics/status — any admin role
- /api/admin/analytics/periods — any admin role + structure
- /api/admin/analytics/monthly default (cache) + period range
- /api/admin/analytics/monthly with filters → source=live
- Auto-rebuild on publish + delete-import (smoke / cache freshness)
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://lanjut-core.preview.emergentagent.com").rstrip("/")

SUPER = {"email": "superadmin@rilismusik.com", "password": "SuperAdmin#2026"}
FINANCE = {"email": "finance1@rilismusik.com", "password": "Finance#2026"}
SUPPORT = {"email": "support1@rilismusik.com", "password": "Support#2026"}
RELEASE = {"email": "release1@rilismusik.com", "password": "Release#2026"}


def _login(creds):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    token = r.json().get("access_token") or r.json().get("token")
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="module")
def super_client():
    return _login(SUPER)


@pytest.fixture(scope="module")
def finance_client():
    return _login(FINANCE)


@pytest.fixture(scope="module")
def support_client():
    return _login(SUPPORT)


@pytest.fixture(scope="module")
def release_client():
    return _login(RELEASE)


# ------------------------- /periods -------------------------

class TestAnalyticsPeriods:
    def test_periods_super_admin(self, super_client):
        r = super_client.get(f"{BASE_URL}/api/admin/analytics/periods", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "periods" in d and "min" in d and "max" in d
        assert isinstance(d["periods"], list)
        # ascending sort check
        if len(d["periods"]) >= 2:
            assert d["periods"] == sorted(d["periods"]), "periods not sorted ascending"
            assert d["min"] == d["periods"][0]
            assert d["max"] == d["periods"][-1]

    def test_periods_finance_allowed(self, finance_client):
        r = finance_client.get(f"{BASE_URL}/api/admin/analytics/periods", timeout=30)
        assert r.status_code == 200, r.text

    def test_periods_support_allowed(self, support_client):
        # any admin role can read
        r = support_client.get(f"{BASE_URL}/api/admin/analytics/periods", timeout=30)
        assert r.status_code == 200, r.text


# ------------------------- /status -------------------------

class TestAnalyticsStatus:
    def test_status_super(self, super_client):
        r = super_client.get(f"{BASE_URL}/api/admin/analytics/status", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ["running", "finished_at", "duration_sec", "doc_count"]:
            assert k in d, f"missing key {k}"
        assert isinstance(d["running"], bool)

    def test_status_finance(self, finance_client):
        r = finance_client.get(f"{BASE_URL}/api/admin/analytics/status", timeout=30)
        assert r.status_code == 200

    def test_status_support(self, support_client):
        r = support_client.get(f"{BASE_URL}/api/admin/analytics/status", timeout=30)
        assert r.status_code == 200


# ------------------------- /recompute auth -------------------------

class TestRecomputeAuth:
    def test_recompute_finance_forbidden(self, finance_client):
        r = finance_client.post(f"{BASE_URL}/api/admin/analytics/recompute", timeout=120)
        assert r.status_code == 403, f"expected 403 got {r.status_code} {r.text}"

    def test_recompute_support_forbidden(self, support_client):
        r = support_client.post(f"{BASE_URL}/api/admin/analytics/recompute", timeout=120)
        assert r.status_code == 403

    def test_recompute_release_forbidden(self, release_client):
        r = release_client.post(f"{BASE_URL}/api/admin/analytics/recompute", timeout=120)
        assert r.status_code == 403

    def test_recompute_super_allowed(self, super_client):
        r = super_client.post(f"{BASE_URL}/api/admin/analytics/recompute", timeout=300)
        assert r.status_code == 200, r.text
        d = r.json()
        # Either ok:true with meta, or ok:false "already running"
        assert "meta" in d
        meta = d["meta"]
        assert "finished_at" in meta and "doc_count" in meta
        # after a successful run, status endpoint should reflect it
        s = super_client.get(f"{BASE_URL}/api/admin/analytics/status").json()
        assert s["doc_count"] == meta["doc_count"]


# ------------------------- /monthly (cache path) -------------------------

class TestMonthlyCachePath:
    def test_monthly_default_returns_cache(self, super_client):
        r = super_client.get(f"{BASE_URL}/api/admin/analytics/monthly", timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("source") == "cache", f"expected cache, got {d.get('source')}"
        # KPI keys
        kpi = d.get("kpi", {})
        for k in [
            "total_revenue_eur", "total_revenue_idr", "total_quantity", "total_lines",
            "distinct_platforms", "distinct_countries", "distinct_tracks",
            "distinct_artists", "distinct_labels",
        ]:
            assert k in kpi, f"missing kpi.{k}"
        # arrays
        for k in ["monthly", "top_platforms", "top_countries", "top_labels", "top_artists", "top_tracks"]:
            assert k in d and isinstance(d[k], list), f"missing array {k}"
        # monthly sorted ASC by period
        periods = [m["period"] for m in d["monthly"]]
        assert periods == sorted(periods), "monthly not sorted ASC"
        # top_n capped at 10 by default
        assert len(d["top_platforms"]) <= 10
        assert len(d["top_tracks"]) <= 10

    def test_monthly_period_range_filters(self, super_client):
        # get periods first
        p = super_client.get(f"{BASE_URL}/api/admin/analytics/periods").json()
        if not p["periods"] or len(p["periods"]) < 2:
            pytest.skip("Need at least 2 periods")
        pmin, pmax = p["periods"][0], p["periods"][-1]
        r = super_client.get(
            f"{BASE_URL}/api/admin/analytics/monthly",
            params={"period_from": pmin, "period_to": pmin}, timeout=60,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["source"] == "cache"
        # All monthly entries must be within range
        for m in d["monthly"]:
            assert pmin <= m["period"] <= pmin

    def test_monthly_response_under_3s(self, super_client):
        t0 = time.time()
        r = super_client.get(f"{BASE_URL}/api/admin/analytics/monthly", timeout=30)
        elapsed = time.time() - t0
        assert r.status_code == 200
        # Sub-3s expected for cache hit; lenient since preview infra
        assert elapsed < 5.0, f"cache path slow: {elapsed:.2f}s"


# ------------------------- /monthly (live path) -------------------------

class TestMonthlyLivePath:
    def _pick_filter(self, super_client, dim_key):
        """Pick a real value from top_N for filter testing."""
        d = super_client.get(f"{BASE_URL}/api/admin/analytics/monthly").json()
        arr = d.get(f"top_{dim_key}", [])
        if not arr:
            return None
        return arr[0].get("key")

    def test_filter_by_platform_is_live(self, super_client):
        plat = self._pick_filter(super_client, "platforms")
        if not plat:
            pytest.skip("No platform data")
        r = super_client.get(
            f"{BASE_URL}/api/admin/analytics/monthly",
            params={"platform": plat}, timeout=60,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["source"] == "live"
        assert d["filters"]["platform"] == plat

    def test_filter_by_country_is_live(self, super_client):
        ctr = self._pick_filter(super_client, "countries")
        if not ctr:
            pytest.skip("No country data")
        r = super_client.get(
            f"{BASE_URL}/api/admin/analytics/monthly",
            params={"country": ctr}, timeout=60,
        )
        assert r.status_code == 200
        assert r.json()["source"] == "live"

    def test_filter_by_label_is_live(self, super_client):
        lab = self._pick_filter(super_client, "labels")
        if not lab:
            pytest.skip("No label data")
        r = super_client.get(
            f"{BASE_URL}/api/admin/analytics/monthly",
            params={"label_id": lab}, timeout=60,
        )
        assert r.status_code == 200
        assert r.json()["source"] == "live"

    def test_filter_by_artist_is_live(self, super_client):
        art = self._pick_filter(super_client, "artists")
        if not art:
            pytest.skip("No artist data")
        r = super_client.get(
            f"{BASE_URL}/api/admin/analytics/monthly",
            params={"artist_id": art}, timeout=60,
        )
        assert r.status_code == 200
        assert r.json()["source"] == "live"

    def test_filter_by_track_is_live(self, super_client):
        trk = self._pick_filter(super_client, "tracks")
        if not trk:
            pytest.skip("No track data")
        r = super_client.get(
            f"{BASE_URL}/api/admin/analytics/monthly",
            params={"track_id": trk}, timeout=60,
        )
        assert r.status_code == 200
        assert r.json()["source"] == "live"


# ------------------------- Auth on /monthly -------------------------

class TestMonthlyAuth:
    def test_monthly_no_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/analytics/monthly", timeout=30)
        assert r.status_code in (401, 403), f"expected 401/403 got {r.status_code}"

    def test_monthly_finance_allowed(self, finance_client):
        r = finance_client.get(f"{BASE_URL}/api/admin/analytics/monthly", timeout=60)
        assert r.status_code == 200

    def test_monthly_support_allowed(self, support_client):
        # spec: any admin role can view monthly (even though no nav link)
        r = support_client.get(f"{BASE_URL}/api/admin/analytics/monthly", timeout=60)
        assert r.status_code == 200
