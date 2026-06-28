"""Phase 16.1 — Defensive wrapper tests for /api/royalty/admin/imports/{id}/publish

New scenarios:
  - frozen / non-standard status → HTTP 400 with descriptive message naming
    the invalid status + listing the valid statuses.
  - import doc with NO status field (legacy migration) → defaults to
    pending_review and proceeds normally (NOT 500).
  - Auth: anon=401, release1=403, super=200, finance=200.
  - Idempotency under rapid double-click is verified by the parent suite,
    so here we only re-check the descriptive 400 path.

These tests insert raw docs into MongoDB directly (no CSV upload) — we only
need to verify the endpoint's defensive branches, not the publish pipeline.
"""
import os
import sys
import time
import pytest
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break

SUPERADMIN = {"email": "superadmin@rilismusik.com", "password": "SuperAdmin#2026"}
FINANCE    = {"email": "finance1@rilismusik.com",    "password": "Finance#2026"}
RELEASE    = {"email": "release1@rilismusik.com",    "password": "Release#2026"}

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME   = os.environ.get("DB_NAME",   "rilismusik_db")


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password}, timeout=20)
    if r.status_code != 200:
        pytest.skip(f"login failed {email}: {r.status_code}")
    return r.json()["access_token"]


def _H(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def super_tok():
    return _login(**SUPERADMIN)


@pytest.fixture(scope="module")
def finance_tok():
    return _login(**FINANCE)


@pytest.fixture(scope="module")
def release_tok():
    return _login(**RELEASE)


@pytest.fixture(scope="module")
def mongo_db():
    from pymongo import MongoClient
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


def _seed_minimal_import(mongo_db, status_field=None, import_id_prefix="TEST_PH161"):
    """Insert a minimal royalty_imports doc with NO royalty_lines so /publish
    short-circuits on the status check (which is what we want to verify)."""
    from uuid import uuid4
    import_id = f"{import_id_prefix}_{uuid4().hex[:8]}"
    doc = {
        "id": import_id,
        "period": "2024-01",
        "period_start": "2024-01",
        "period_end": "2024-01",
        "is_multi_period": False,
        "source": "believe",
        "filename": "TEST_phase16_1.csv",
        "exchange_rate_eur_idr": 17500,
        "fee_percent": 5.0,
        "total_lines": 0,
        "processed_lines": 0,
        "matched_lines": 0,
        "unmatched_lines": 0,
        "total_revenue_eur": 0.0,
        "total_label_idr": 0,
        "uploaded_by": "test",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    if status_field is not None:
        doc["status"] = status_field
    # else: omit status entirely (legacy doc scenario)
    mongo_db.royalty_imports.insert_one(doc)
    return import_id


@pytest.fixture(scope="module", autouse=True)
def _cleanup(mongo_db):
    yield
    mongo_db.royalty_imports.delete_many({"id": {"$regex": "^TEST_PH161_"}})


# --------------------------------------------------------------------
# 1) Auth gates (re-verified in 16.1 context)
# --------------------------------------------------------------------
class TestAuthGates161:
    def test_anon_publish_401(self, mongo_db):
        iid = _seed_minimal_import(mongo_db, status_field="pending_review")
        r = requests.post(f"{BASE_URL}/api/royalty/admin/imports/{iid}/publish",
                          json={}, timeout=15)
        assert r.status_code in (401, 403)

    def test_release_admin_publish_403(self, release_tok, mongo_db):
        iid = _seed_minimal_import(mongo_db, status_field="pending_review")
        r = requests.post(f"{BASE_URL}/api/royalty/admin/imports/{iid}/publish",
                          headers=_H(release_tok), json={}, timeout=15)
        assert r.status_code == 403, f"got {r.status_code} {r.text[:200]}"

    def test_finance_admin_publish_200(self, finance_tok, mongo_db):
        iid = _seed_minimal_import(mongo_db, status_field="pending_review")
        r = requests.post(f"{BASE_URL}/api/royalty/admin/imports/{iid}/publish",
                          headers=_H(finance_tok), json={}, timeout=15)
        assert r.status_code == 200, f"finance got {r.status_code} {r.text[:200]}"
        body = r.json()
        assert body.get("status") in ("publishing", "published")

    def test_super_admin_publish_200(self, super_tok, mongo_db):
        iid = _seed_minimal_import(mongo_db, status_field="pending_review")
        r = requests.post(f"{BASE_URL}/api/royalty/admin/imports/{iid}/publish",
                          headers=_H(super_tok), json={}, timeout=15)
        assert r.status_code == 200
        assert r.json().get("status") in ("publishing", "published")


# --------------------------------------------------------------------
# 2) Frozen / non-standard status → 400 with descriptive detail
# --------------------------------------------------------------------
class TestFrozenStatus:
    def test_frozen_status_returns_400_with_description(self, super_tok, mongo_db):
        iid = _seed_minimal_import(mongo_db, status_field="frozen")
        r = requests.post(f"{BASE_URL}/api/royalty/admin/imports/{iid}/publish",
                          headers=_H(super_tok), json={}, timeout=15)
        assert r.status_code == 400, f"expected 400 frozen, got {r.status_code}: {r.text[:300]}"
        # Detail must name the invalid status & list valid ones
        text = r.text.lower()
        assert "frozen" in text, f"detail must mention 'frozen': {r.text[:300]}"
        assert "pending_review" in text and "publish_error" in text, (
            f"detail must list valid statuses: {r.text[:300]}"
        )

    def test_published_status_returns_400(self, super_tok, mongo_db):
        iid = _seed_minimal_import(mongo_db, status_field="published")
        r = requests.post(f"{BASE_URL}/api/royalty/admin/imports/{iid}/publish",
                          headers=_H(super_tok), json={}, timeout=15)
        assert r.status_code == 400, f"published → expected 400, got {r.status_code}"
        assert "published" in r.text.lower()


# --------------------------------------------------------------------
# 3) Legacy doc with NO status field → defensive default → 200
# --------------------------------------------------------------------
class TestMissingStatusField:
    def test_doc_without_status_field_defaults_to_pending_review(
            self, super_tok, mongo_db):
        """Insert an import doc with NO 'status' key at all (legacy migration
        scenario). The defensive wrapper should treat it as pending_review and
        succeed (return 200), NOT 500."""
        iid = _seed_minimal_import(mongo_db, status_field=None)
        # Sanity-check the seed actually lacks 'status'
        seeded = mongo_db.royalty_imports.find_one({"id": iid})
        assert "status" not in seeded, "seed setup broken: status key present"

        r = requests.post(f"{BASE_URL}/api/royalty/admin/imports/{iid}/publish",
                          headers=_H(super_tok), json={}, timeout=15)
        assert r.status_code == 200, (
            f"legacy doc (no status) should not 500. got {r.status_code}: {r.text[:300]}"
        )
        body = r.json()
        # Endpoint should have flipped status to 'publishing' (or background
        # already finished into 'published').
        assert body.get("status") in ("publishing", "published"), (
            f"unexpected status: {body.get('status')}"
        )

        # Poll briefly to confirm bg task completes (0 lines → trivial)
        deadline = time.time() + 15
        last_status = None
        while time.time() < deadline:
            g = requests.get(f"{BASE_URL}/api/royalty/admin/imports/{iid}",
                             headers=_H(super_tok), timeout=15)
            assert g.status_code == 200
            last_status = g.json()["import"]["status"]
            if last_status in ("published", "publish_error"):
                break
            time.sleep(1)
        assert last_status == "published", (
            f"legacy doc bg publish did not complete: {last_status}"
        )


# --------------------------------------------------------------------
# 4) 404 path still works (sanity)
# --------------------------------------------------------------------
class TestNotFound:
    def test_publish_unknown_id_returns_404(self, super_tok):
        r = requests.post(
            f"{BASE_URL}/api/royalty/admin/imports/NONEXISTENT_xyz/publish",
            headers=_H(super_tok), json={}, timeout=15,
        )
        assert r.status_code == 404, f"expected 404, got {r.status_code}"
        assert "ditemukan" in r.text.lower() or "not found" in r.text.lower()


# --------------------------------------------------------------------
# 5) Publish_error status is allowed (defensive retry path)
# --------------------------------------------------------------------
class TestPublishErrorRetry:
    def test_publish_error_status_can_be_republished(self, super_tok, mongo_db):
        iid = _seed_minimal_import(mongo_db, status_field="publish_error")
        r = requests.post(f"{BASE_URL}/api/royalty/admin/imports/{iid}/publish",
                          headers=_H(super_tok), json={}, timeout=15)
        assert r.status_code == 200, (
            f"publish_error should be retryable, got {r.status_code}: {r.text[:300]}"
        )
        assert r.json().get("status") in ("publishing", "published")
