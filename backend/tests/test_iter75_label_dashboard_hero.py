"""Iter75 — Label dashboard pipeline + CMS label_dashboard_hero key.

Verifies:
- GET /api/label/dashboard returns top-level `pipeline` with expected keys and integer values
- Existing `stats` and `label` fields remain intact
- PATCH /api/cms/landing persists label_dashboard_hero for super admin
- Public GET /api/cms/landing returns the key and other landing keys remain intact
"""
import os
import pytest
import requests
from dotenv import dotenv_values

_env = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or _env.get("REACT_APP_BACKEND_URL")).rstrip("/")

SUPERADMIN = ("superadmin@rilismusik.com", "SuperAdmin#2026")
LABEL = ("demo_vip@rilismusik.com", "DemoVIP#2026")


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def label_session():
    return _login(*LABEL)


@pytest.fixture(scope="module")
def admin_session():
    return _login(*SUPERADMIN)


# --- Label dashboard: pipeline field ---
class TestLabelDashboardPipeline:
    def test_dashboard_returns_pipeline(self, label_session):
        r = label_session.get(f"{BASE}/api/label/dashboard", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "pipeline" in data, "missing top-level 'pipeline'"
        p = data["pipeline"]
        for k in ("draft", "review", "delivered", "live"):
            assert k in p, f"missing pipeline key {k}"
            assert isinstance(p[k], int), f"pipeline.{k} not int: {p[k]!r}"

    def test_dashboard_stats_and_label_intact(self, label_session):
        r = label_session.get(f"{BASE}/api/label/dashboard", timeout=30)
        data = r.json()
        assert "stats" in data and isinstance(data["stats"], dict)
        assert "label" in data and isinstance(data["label"], dict)
        # a few important existing stats keys
        for k in ("balance_available_idr", "balance_pending_idr", "total_releases", "last_month_revenue_idr"):
            assert k in data["stats"], f"stats.{k} missing (regression)"


# --- CMS landing label_dashboard_hero ---
class TestCMSLabelDashboardHero:
    def test_patch_and_get_hero(self, admin_session):
        payload = {
            "settings": {
                "label_dashboard_hero": {
                    "is_active": True,
                    "headline": "QA Headline",
                    "cta_text": "Ajukan Rilisan",
                    "cta_target": "/label/releases/upload",
                    "overlay_opacity": 60,
                }
            }
        }
        r = admin_session.patch(f"{BASE}/api/cms/landing", json=payload, timeout=30)
        assert r.status_code == 200, r.text

        # public GET
        r2 = requests.get(f"{BASE}/api/cms/landing", timeout=30)
        assert r2.status_code == 200
        data = r2.json()
        assert "label_dashboard_hero" in data
        hero = data["label_dashboard_hero"]
        assert hero.get("is_active") is True
        assert hero.get("headline") == "QA Headline"
        assert hero.get("cta_target") == "/label/releases/upload"
        assert hero.get("overlay_opacity") == 60

    def test_other_landing_keys_intact(self, admin_session):
        r = requests.get(f"{BASE}/api/cms/landing", timeout=30)
        assert r.status_code == 200
        data = r.json()
        # There should be more than just our key — regression check that existing keys remain.
        other_keys = [k for k in data.keys() if k != "label_dashboard_hero"]
        assert len(other_keys) > 0, f"only label_dashboard_hero present, other landing keys missing: {list(data.keys())}"

    def test_cleanup_deactivate_hero(self, admin_session):
        """Cleanup step per review request — leave is_active=False so real labels see default."""
        payload = {
            "settings": {
                "label_dashboard_hero": {
                    "is_active": False,
                    "headline": "",
                    "cta_text": "Ajukan Rilisan",
                    "cta_target": "/label/releases/upload",
                    "overlay_opacity": 60,
                }
            }
        }
        r = admin_session.patch(f"{BASE}/api/cms/landing", json=payload, timeout=30)
        assert r.status_code == 200
        r2 = requests.get(f"{BASE}/api/cms/landing", timeout=30)
        assert r2.json()["label_dashboard_hero"]["is_active"] is False
