"""Phase 24 — Materialized rollups for Artists/Releases/Labels.

Validates the Phase 24 fast-path where `rollup_revenue_by_id` reads from the
`monthly_analytics` cache (sub-second) instead of doing a live aggregate over
`royalty_lines` (slow on 1M+ rows).

Setup pattern: seed both the source (`royalty_lines`) and the cache
(`monthly_analytics`) with controlled data, then call the helper and assert
the result comes from the cache (verified by tweaking the cache values to
known sentinels that differ from the source).
"""
import os
import time
import uuid
import requests
from tests.support_config import SUPERADMIN
import pytest
import pymongo
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load backend/.env so direct in-process imports (revenue_rollup → deps) can
# read MONGO_URL/DB_NAME like the running server does.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://lanjut-core.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"
SUPER = (SUPERADMIN["email"], SUPERADMIN["password"])


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


def test_rollup_helper_cache_and_fallback(super_token):
    """Combined test (single asyncio.run) to avoid the motor client being
    bound to a closed event loop between consecutive in-process tests.

    Scenario A — cache hit: seed monthly_analytics with a sentinel; verify
    that value is returned (and NOT the differing royalty_lines value).
    Scenario B — cache miss: zero docs in monthly_analytics for a new dim
    key; verify the helper falls back to live royalty_lines aggregation.
    """
    db = _db()
    artist_id = f"phase24-artist-{uuid.uuid4().hex[:10]}"
    release_id = f"phase24-rel-{uuid.uuid4().hex[:10]}"

    # Scenario A — cache populated with sentinel
    db.monthly_analytics.insert_one({
        "dim": "artist", "key": artist_id, "period": "2024-06",
        "revenue_eur": 999.99, "revenue_idr": 9_999_999,
        "quantity": 42, "lines_count": 7,
        "artist_name": "Phase24 Cache Artist",
    })
    # Live source has different value — would leak through if fallback fires
    db.royalty_lines.insert_one({
        "id": f"phase24-line-{uuid.uuid4().hex[:8]}",
        "artist_id": artist_id, "label_id": "irrelevant", "period": "2024-06",
        "match_status": "matched", "status": "draft",
        "revenue_eur": 1.0, "label_idr": 1, "quantity": 1, "row_period": "2024-06",
    })

    # Scenario B — NO cache, only live (release dim, fresh key)
    db.royalty_lines.insert_many([{
        "id": f"line-{release_id}-{k}",
        "release_id": release_id, "label_id": "x", "period": "2024-03",
        "match_status": "matched", "status": "draft",
        "revenue_eur": 5.0, "label_idr": 50000, "quantity": 1, "row_period": "2024-03",
    } for k in range(3)])

    try:
        import sys
        sys.path.insert(0, "/app/backend")
        from routes.revenue_rollup import rollup_revenue_by_id

        async def _run_both():
            cache_result = await rollup_revenue_by_id(
                field="artist_id", ids=[artist_id],
                period_from="2024-01", period_to="2024-12",
            )
            live_result = await rollup_revenue_by_id(
                field="release_id", ids=[release_id],
                period_from="2024-01", period_to="2024-12",
            )
            return cache_result, live_result

        cache_result, live_result = asyncio.run(_run_both())

        # Scenario A assertions
        assert artist_id in cache_result, f"cache hit missing: {cache_result}"
        assert cache_result[artist_id]["revenue_eur"] == 999.99
        assert cache_result[artist_id]["revenue_idr"] == 9_999_999
        assert cache_result[artist_id]["lines"] == 7

        # Scenario B assertions — live fallback returned aggregated values
        assert release_id in live_result, f"live fallback missing: {live_result}"
        assert live_result[release_id]["revenue_eur"] == 15.0  # 3 × 5.0
        assert live_result[release_id]["revenue_idr"] == 150000
        assert live_result[release_id]["lines"] == 3
    finally:
        db.monthly_analytics.delete_many({"key": {"$in": [artist_id, release_id]}})
        db.royalty_lines.delete_many({"artist_id": artist_id})
        db.royalty_lines.delete_many({"release_id": release_id})


def test_rebuild_endpoint_includes_release_dim(super_token):
    """After Phase 24 the rebuild must emit `dim='release'` docs too.
    Seed a release with royalty_lines, trigger rebuild, verify."""
    db = _db()
    label_id = f"phase24-lab-{uuid.uuid4().hex[:8]}"
    release_id = f"phase24-rebuild-rel-{uuid.uuid4().hex[:8]}"

    db.labels.insert_one({"id": label_id, "label_name": "Phase24 Label"})
    db.releases.insert_one({
        "id": release_id, "release_title": "Phase24 Album", "artist_name": "Phase24 Artist",
        "upc": "PH24UPC001", "label_id": label_id,
    })
    db.royalty_lines.insert_many([{
        "id": f"line-rebuild-{release_id}-{k}",
        "release_id": release_id, "label_id": label_id, "period": "2024-07",
        "match_status": "matched", "status": "draft",
        "revenue_eur": 2.0, "label_idr": 20000, "quantity": 1, "row_period": "2024-07",
    } for k in range(5)])

    try:
        # Trigger rebuild
        r = requests.post(f"{API}/admin/analytics/recompute", headers=_hdr(super_token), timeout=120)
        assert r.status_code == 200, r.text
        # Verify release dim docs exist with hydrated title
        rel_doc = db.monthly_analytics.find_one({"dim": "release", "key": release_id})
        assert rel_doc is not None, "rebuild did not produce release-dim docs"
        assert rel_doc["release_title"] == "Phase24 Album"
        assert rel_doc["revenue_eur"] == 10.0  # 5 lines × 2.0
        assert rel_doc["lines_count"] == 5
        # Status endpoint should now include release in per_dim_counts
        s = requests.get(f"{API}/admin/analytics/status", headers=_hdr(super_token), timeout=15)
        assert s.status_code == 200
        per_dim = s.json().get("per_dim_counts", {})
        assert "release" in per_dim, f"per_dim_counts missing 'release': {per_dim}"
        assert per_dim["release"] >= 1
    finally:
        db.monthly_analytics.delete_many({"$or": [
            {"key": release_id}, {"key": label_id},
        ]})
        db.royalty_lines.delete_many({"release_id": release_id})
        db.releases.delete_one({"id": release_id})
        db.labels.delete_one({"id": label_id})


def test_rollup_health_doc_persisted(super_token):
    """After a successful rebuild, rollup_health doc must be present so the
    status endpoint can surface metadata even after pod restart."""
    db = _db()
    # Trigger rebuild (idempotent)
    r = requests.post(f"{API}/admin/analytics/recompute", headers=_hdr(super_token), timeout=120)
    assert r.status_code == 200
    # Verify the persisted doc
    health = db.rollup_health.find_one({"id": "monthly_analytics"})
    assert health is not None, "rollup_health doc was not persisted"
    assert health.get("finished_at") is not None
    assert health.get("doc_count", 0) >= 0
    assert isinstance(health.get("per_dim_counts"), dict)


def test_status_endpoint_returns_per_dim_counts(super_token):
    """Status endpoint should include per_dim_counts dict."""
    s = requests.get(f"{API}/admin/analytics/status", headers=_hdr(super_token), timeout=15)
    assert s.status_code == 200
    body = s.json()
    assert "per_dim_counts" in body
    assert isinstance(body["per_dim_counts"], dict)
