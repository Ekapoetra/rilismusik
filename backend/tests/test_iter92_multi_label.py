"""Multi-Label (Rp1.5jt/tahun) Phase 2 & 3 backend tests."""
import os
import requests
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://lanjut-core.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"


def login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    tok = r.json().get("access_token")
    assert tok
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def ml_headers():
    return login("multilabel-qa@example.com", "MultiLabelQA#2026")


@pytest.fixture(scope="module")
def ppr_headers():
    return login("demo_ppr@rilismusik.com", "DemoPPR#2026")


@pytest.fixture(scope="module")
def super_headers():
    return login("superadmin@rilismusik.com", "SuperAdmin#2026")


@pytest.fixture(scope="module")
def finance_headers():
    return login("finance1@rilismusik.com", "Finance#2026")


# ---------- PHASE 2 ----------
class TestPhase2Account:
    def test_multi_label_account_aggregation(self, ml_headers):
        r = requests.get(f"{API}/label/account", headers=ml_headers, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("is_multi_label") is True, d
        assert d.get("label_count") == 2, d
        assert d.get("account_available_idr") == 5000000, d
        labels = d.get("labels") or []
        assert len(labels) == 2
        for lb in labels:
            assert "id" in lb and "label_name" in lb and "available_idr" in lb
        avs = sorted([lb["available_idr"] for lb in labels])
        assert avs == [2000000, 3000000], avs
        assert d.get("primary_label_id")
        assert d.get("active_label_id")

    def test_single_label_account_no_aggregation(self, ppr_headers):
        r = requests.get(f"{API}/label/account", headers=ppr_headers, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("is_multi_label") is False, d
        assert d.get("account_available_idr") is None, d


class TestPhase2ActiveLabel:
    def test_switch_label_b_then_back(self, ml_headers):
        r = requests.post(f"{API}/label/active-label", json={"label_id": "mlqa-label-b"},
                          headers=ml_headers, timeout=30)
        assert r.status_code == 200, r.text

        me = requests.get(f"{API}/label/me", headers=ml_headers, timeout=30)
        assert me.status_code == 200
        assert me.json().get("id") == "mlqa-label-b", me.json()

        # switch back
        r2 = requests.post(f"{API}/label/active-label", json={"label_id": "mlqa-label-a"},
                           headers=ml_headers, timeout=30)
        assert r2.status_code == 200
        me2 = requests.get(f"{API}/label/me", headers=ml_headers, timeout=30)
        assert me2.json().get("id") == "mlqa-label-a"

    def test_switch_forged_label_404(self, ml_headers):
        r = requests.post(f"{API}/label/active-label", json={"label_id": "not-mine-xyz"},
                          headers=ml_headers, timeout=30)
        assert r.status_code == 404, f"expected 404 got {r.status_code} {r.text}"


# ---------- PHASE 3 ----------
class TestPhase3WAMI:
    def test_free_wami_multi_label(self, ml_headers):
        r = requests.post(f"{API}/payments/wami", json={"track_id": "mlqa-track-a"},
                          headers=ml_headers, timeout=60)
        # If already used (idempotency), test flags as skip w/ context
        if r.status_code == 400 and "active" in r.text.lower():
            pytest.skip(f"WAMI already active for track (re-run requires cleanup): {r.text}")
        assert r.status_code in (200, 201), r.text
        payload = r.json()
        # response shape: {"order": {...}, "invoice": null, "free_vip": true}
        d = payload.get("order") or payload
        assert payload.get("free_vip") is True, payload
        assert payload.get("invoice") in (None, {}), payload
        assert d.get("amount_idr") == 0, d
        assert d.get("status") == "pending", d
        assert d.get("is_free_vip") is True, d
        assert d.get("benefit_source") == "multi_label", d

    def test_wami_paid_regression_single_label(self, ppr_headers):
        # find a track owned by demo_ppr
        rel = requests.get(f"{API}/releases", headers=ppr_headers, timeout=30)
        if rel.status_code != 200:
            pytest.skip(f"cannot list releases for demo_ppr: {rel.status_code}")
        releases = rel.json() if isinstance(rel.json(), list) else rel.json().get("items", [])
        track_id = None
        for rls in releases:
            for t in (rls.get("tracks") or []):
                if not t.get("wami_active") and not t.get("has_active_wami"):
                    track_id = t.get("id") or t.get("track_id")
                    if track_id:
                        break
            if track_id:
                break
        if not track_id:
            pytest.skip("no available track w/o WAMI for demo_ppr")
        r = requests.post(f"{API}/payments/wami", json={"track_id": track_id},
                          headers=ppr_headers, timeout=60)
        if r.status_code == 400 and "active" in r.text.lower():
            pytest.skip("track already has active wami")
        assert r.status_code in (200, 201), r.text
        d = r.json()
        assert d.get("amount_idr", 0) > 0, d
        assert d.get("is_free_vip") in (False, None), d
        # should have invoice url
        assert d.get("xendit_invoice_url") or d.get("invoice_url"), d


class TestPhase3Quota:
    def test_multi_label_quota_limit_7(self, ml_headers):
        r = requests.get(f"{API}/releases/submission-quota", headers=ml_headers, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("limit") == 7, d

    def test_single_label_quota_limit_7(self, ppr_headers):
        r = requests.get(f"{API}/releases/submission-quota", headers=ppr_headers, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("limit") == 7, d


# ---------- PHASE 1 regression ----------
class TestPhase1PackageRBAC:
    def _find_label_b(self, headers):
        # target mlqa-label-b (currently non-multi_label) via admin endpoint
        r = requests.get(f"{API}/admin/labels", headers=headers, timeout=30)
        if r.status_code != 200:
            return None
        items = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
        for lb in items:
            if (lb.get("id") or lb.get("_id")) == "mlqa-label-b":
                return lb
        return None

    def test_super_admin_can_patch_package(self, super_headers):
        lb = self._find_label_b(super_headers)
        if not lb:
            pytest.skip("mlqa-label-b not found")
        rev = int(lb.get("package_revision") or 0)
        current = lb.get("subscription_tier") or lb.get("package") or "free"
        body = {
            "package": "multi_label",
            "expires_on": "2027-01-01",
            "reason": "iter92 automated test — grant multi_label",
            "expected_revision": rev,
            "confirm": True,
        }
        r = requests.patch(f"{API}/admin/labels/mlqa-label-b/package",
                           json=body, headers=super_headers, timeout=30)
        assert r.status_code in (200, 204), f"{r.status_code} {r.text}"
        # revert
        lb2 = self._find_label_b(super_headers)
        rev2 = int(lb2.get("package_revision") or (rev + 1))
        requests.patch(f"{API}/admin/labels/mlqa-label-b/package",
                       json={"package": "pay_per_release",
                             "reason": "revert iter92 test",
                             "expected_revision": rev2,
                             "confirm": True},
                       headers=super_headers, timeout=30)

    def test_finance_admin_forbidden(self, finance_headers, super_headers):
        lb = self._find_label_b(super_headers)
        if not lb:
            pytest.skip("mlqa-label-b not found")
        rev = int(lb.get("package_revision") or 0)
        body = {
            "package": "multi_label",
            "expires_on": "2027-01-01",
            "reason": "iter92 finance forbidden test",
            "expected_revision": rev,
            "confirm": True,
        }
        r = requests.patch(f"{API}/admin/labels/mlqa-label-b/package",
                           json=body, headers=finance_headers, timeout=30)
        assert r.status_code == 403, f"expected 403 got {r.status_code} {r.text}"
