"""Phase 27 — Ensure indexes endpoint + index presence check.

Validates that `POST /api/admin/migrate/ensure-indexes` (super_admin only)
runs the seed_indexes_and_admins() function and that the critical new
indexes are present afterward.
"""
import os
import requests
from tests.support_config import FINANCE as FINANCE_CRED, SUPERADMIN
import pytest
import pymongo

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://lanjut-core.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"
SUPER = (SUPERADMIN["email"], SUPERADMIN["password"])
FINANCE = (FINANCE_CRED["email"], FINANCE_CRED["password"])


def _db():
    client = pymongo.MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    return client[os.environ.get("DB_NAME", "rilismusik_db")]


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def _hdr(t):
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture(scope="module")
def super_token():
    return _login(*SUPER)


def test_ensure_indexes_endpoint_returns_ok(super_token):
    r = requests.post(
        f"{API}/admin/migrate/ensure-indexes",
        headers=_hdr(super_token),
        timeout=60,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert "duration_sec" in body


def test_ensure_indexes_rbac_super_admin_only():
    finance_t = _login(*FINANCE)
    r = requests.post(
        f"{API}/admin/migrate/ensure-indexes",
        headers=_hdr(finance_t),
        timeout=30,
    )
    assert r.status_code == 403


def test_critical_indexes_present_after_ensure(super_token):
    """After running ensure-indexes, the Phase 27 compound + secondary indexes
    must be present on royalty_lines."""
    # Trigger to be safe
    requests.post(f"{API}/admin/migrate/ensure-indexes",
                  headers=_hdr(super_token), timeout=60)
    db = _db()
    idx = list(db.royalty_lines.list_indexes())
    idx_keys = [list(i["key"].items()) for i in idx]
    # Compound (label_id, period, status)
    assert [("label_id", 1), ("period", 1), ("status", 1)] in idx_keys
    # Compound (label_id, artist_name_raw)
    assert [("label_id", 1), ("artist_name_raw", 1)] in idx_keys
    # row_period solo
    assert [("row_period", 1)] in idx_keys
    # artist_name_raw solo
    assert [("artist_name_raw", 1)] in idx_keys
    # release_id solo
    assert [("release_id", 1)] in idx_keys


def test_migrate_jobs_indexes_present(super_token):
    """migrate_jobs collection should have id + status + kind indexes."""
    requests.post(f"{API}/admin/migrate/ensure-indexes",
                  headers=_hdr(super_token), timeout=60)
    db = _db()
    idx = list(db.migrate_jobs.list_indexes())
    idx_keys = [list(i["key"].items()) for i in idx]
    assert [("id", 1)] in idx_keys
    assert [("status", 1), ("submitted_at", -1)] in idx_keys
    assert [("kind", 1)] in idx_keys
