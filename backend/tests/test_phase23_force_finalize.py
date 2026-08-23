"""Phase 23 — Force-finalize stuck royalty imports.

Validates:
  - POST /api/royalty/admin/imports/{id}/force-finalize transitions a stuck
    `processing` import to `pending_review` by recomputing stats from the
    actual `royalty_lines` collection.
  - When 0 rows exist, the endpoint marks the import as `error`.
  - RBAC: super_admin + admin_finance allowed; admin_release/support/content
    must return 403.
  - Watchdog manual trigger endpoint runs without error and recovers a stuck
    import the same way.

Setup: seed a fake royalty_imports doc with status='processing' + an old
updated_at, plus N synthetic royalty_lines tied to that import_id. Then call
the force-finalize endpoint and assert the resulting doc shape.
"""
import os
import time
import uuid
import requests
from tests.support_config import FINANCE as FINANCE_CRED, RELEASE_ADMIN, SUPPORT as SUPPORT_CRED, SUPERADMIN
import pytest
import pymongo

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://lanjut-core.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"
SUPER = (SUPERADMIN["email"], SUPERADMIN["password"])
FINANCE = (FINANCE_CRED["email"], FINANCE_CRED["password"])
SUPPORT = (SUPPORT_CRED["email"], SUPPORT_CRED["password"])
RELEASE = (RELEASE_ADMIN["email"], RELEASE_ADMIN["password"])


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


@pytest.fixture
def stuck_import_with_lines():
    """Insert a stuck `processing` royalty_imports doc + 20 royalty_lines.
    Returns the import_id. Cleans up after the test.
    """
    db = _db()
    import_id = f"phase23-stuck-{uuid.uuid4().hex[:10]}"
    label_id = f"phase23-lab-{uuid.uuid4().hex[:8]}"

    # Stuck import: status=processing, updated_at long ago
    db.royalty_imports.insert_one({
        "id": import_id,
        "filename": "phase23_test.csv",
        "status": "processing",
        "exchange_rate_eur_idr": 17500,
        "fee_percent": 5.0,
        "total_lines": 0,
        "processed_lines": 0,
        "progress_pct": 99,
        "matched_lines": 0,
        "unmatched_lines": 0,
        "period_breakdown": {},
        "is_multi_period": False,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "uploaded_by": "system",
    })

    # Helper label so matched rows have a real FK
    db.labels.insert_one({
        "id": label_id,
        "label_name": f"Phase23 Test {import_id[-6:]}",
        "balance_pending_idr": 0,
        "balance_available_idr": 0,
    })

    # Seed 20 royalty_lines spanning 2 periods (10 matched, 5 unmatched)
    lines = []
    for k in range(15):
        lines.append({
            "id": f"line-{import_id}-{k}",
            "import_id": import_id,
            "period": "2025-01" if k < 10 else "2025-02",
            "label_id": label_id,
            "match_status": "matched",
            "status": "draft",
            "revenue_eur": 2.5,
            "label_idr": 25000,
            "isrc": f"ISRC{k:08d}",
        })
    for k in range(5):
        lines.append({
            "id": f"line-{import_id}-um-{k}",
            "import_id": import_id,
            "period": "2025-02",
            "label_id": None,
            "match_status": "unmatched",
            "status": "draft",
            "revenue_eur": 1.0,
            "label_idr": 0,
            "isrc": f"UMISRC{k:06d}",
        })
    db.royalty_lines.insert_many(lines)

    yield import_id, label_id

    # Teardown
    db.royalty_lines.delete_many({"import_id": import_id})
    db.royalty_imports.delete_one({"id": import_id})
    db.labels.delete_one({"id": label_id})


def test_force_finalize_recomputes_from_lines(super_token, stuck_import_with_lines):
    import_id, label_id = stuck_import_with_lines
    r = requests.post(f"{API}/royalty/admin/imports/{import_id}/force-finalize",
                      headers=_hdr(super_token), timeout=30)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ok"] is True
    assert j["status"] == "pending_review"
    assert j["total_lines"] == 20
    assert j["matched_lines"] == 15
    assert j["unmatched_lines"] == 5
    # 15 matched × 2.5 EUR + 5 unmatched × 1 EUR = 42.5 EUR
    assert abs(j["total_revenue_eur"] - 42.5) < 0.01
    assert j["total_label_idr"] == 15 * 25000  # only matched count toward label_idr in our seed
    assert sorted(j["period_breakdown"].keys()) == ["2025-01", "2025-02"]
    assert j["is_multi_period"] is True
    assert j["period_start"] == "2025-01"
    assert j["period_end"] == "2025-02"

    # Verify Mongo state matches
    db = _db()
    imp = db.royalty_imports.find_one({"id": import_id})
    assert imp["status"] == "pending_review"
    assert imp["progress_pct"] == 100
    assert imp["period"] == "multi"


def test_force_finalize_marks_error_when_no_lines(super_token):
    """A stuck import with 0 actual rows in MongoDB should be marked as error."""
    db = _db()
    import_id = f"phase23-empty-{uuid.uuid4().hex[:10]}"
    db.royalty_imports.insert_one({
        "id": import_id,
        "filename": "empty.csv",
        "status": "processing",
        "exchange_rate_eur_idr": 17500,
        "fee_percent": 5.0,
        "total_lines": 0,
        "processed_lines": 0,
        "progress_pct": 99,
        "is_multi_period": False,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    })
    try:
        r = requests.post(f"{API}/royalty/admin/imports/{import_id}/force-finalize",
                          headers=_hdr(super_token), timeout=30)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["ok"] is False
        assert j["status"] == "error"
        # Verify Mongo state
        imp = db.royalty_imports.find_one({"id": import_id})
        assert imp["status"] == "error"
        assert "0 royalty_lines" in (imp.get("error_message") or "") or "tidak ada" in (imp.get("error_message") or "").lower()
    finally:
        db.royalty_imports.delete_one({"id": import_id})


def test_force_finalize_rejected_for_already_finished(super_token):
    """Force-finalize must refuse statuses other than processing/error."""
    db = _db()
    import_id = f"phase23-done-{uuid.uuid4().hex[:10]}"
    db.royalty_imports.insert_one({
        "id": import_id,
        "filename": "done.csv",
        "status": "published",  # already done
        "exchange_rate_eur_idr": 17500,
        "fee_percent": 5.0,
        "total_lines": 100,
        "processed_lines": 100,
        "progress_pct": 100,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    })
    try:
        r = requests.post(f"{API}/royalty/admin/imports/{import_id}/force-finalize",
                          headers=_hdr(super_token), timeout=30)
        assert r.status_code == 400
        assert "processing" in r.text.lower()
    finally:
        db.royalty_imports.delete_one({"id": import_id})


def test_force_finalize_rbac_finance_allowed(stuck_import_with_lines):
    """Admin Finance is allowed to force-finalize."""
    import_id, _ = stuck_import_with_lines
    finance_t = _login(*FINANCE)
    r = requests.post(f"{API}/royalty/admin/imports/{import_id}/force-finalize",
                      headers=_hdr(finance_t), timeout=30)
    assert r.status_code == 200, r.text


def test_force_finalize_rbac_support_denied(stuck_import_with_lines):
    """Admin Support / Release / Content must get 403."""
    import_id, _ = stuck_import_with_lines
    for creds in (SUPPORT, RELEASE):
        t = _login(*creds)
        r = requests.post(f"{API}/royalty/admin/imports/{import_id}/force-finalize",
                          headers=_hdr(t), timeout=30)
        assert r.status_code == 403, f"{creds[0]} got {r.status_code} instead of 403"


def test_watchdog_manual_trigger_returns_ok(super_token):
    """The manual cron-trigger endpoint runs the watchdog without error."""
    r = requests.post(f"{API}/admin/cron/stuck-imports-check",
                      headers=_hdr(super_token), timeout=60)
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True


def test_watchdog_manual_trigger_rbac(super_token):
    """Support cannot run the watchdog manually."""
    t = _login(*SUPPORT)
    r = requests.post(f"{API}/admin/cron/stuck-imports-check",
                      headers=_hdr(t), timeout=30)
    assert r.status_code == 403


def test_watchdog_recovers_stuck_import(super_token):
    """End-to-end: seed a stuck import with old updated_at, manually trigger
    watchdog, expect status flipped to pending_review."""
    db = _db()
    import_id = f"phase23-watch-{uuid.uuid4().hex[:10]}"
    label_id = f"phase23-watch-lab-{uuid.uuid4().hex[:8]}"
    db.royalty_imports.insert_one({
        "id": import_id,
        "filename": "watch.csv",
        "status": "processing",
        "exchange_rate_eur_idr": 17500,
        "fee_percent": 5.0,
        "total_lines": 0,
        "processed_lines": 0,
        "progress_pct": 99,
        "is_multi_period": False,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",  # very old → guaranteed stuck
    })
    db.labels.insert_one({"id": label_id, "label_name": f"Watchdog Lab {import_id[-6:]}"})
    db.royalty_lines.insert_many([{
        "id": f"line-{import_id}-{k}",
        "import_id": import_id,
        "period": "2025-03",
        "label_id": label_id,
        "match_status": "matched",
        "status": "draft",
        "revenue_eur": 1.0,
        "label_idr": 10000,
    } for k in range(7)])
    try:
        r = requests.post(f"{API}/admin/cron/stuck-imports-check",
                          headers=_hdr(super_token), timeout=60)
        assert r.status_code == 200, r.text
        # Give async job a brief moment (it's awaited in-line but just be safe)
        time.sleep(0.5)
        imp = db.royalty_imports.find_one({"id": import_id})
        assert imp["status"] == "pending_review", f"Got {imp['status']}"
        assert imp.get("watchdog_recovered") is True
        assert imp["total_lines"] == 7
    finally:
        db.royalty_lines.delete_many({"import_id": import_id})
        db.royalty_imports.delete_one({"id": import_id})
        db.labels.delete_one({"id": label_id})
