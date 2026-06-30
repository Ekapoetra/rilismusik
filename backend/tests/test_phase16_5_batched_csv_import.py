"""Phase 16.5 — CSV `royalty_lines` batched-insert throughput verification.

Goal: a CSV with 10,000 rows must finish ingestion under 30 seconds locally and
must produce exactly 10,000 `royalty_lines` documents tied to the import doc.
This indirectly verifies BATCH_SIZE=5000 + ordered=False + db_bg insert path
without needing the full 1M-row production CSV.

Also covers source-asserts that future agents don't accidentally regress:
  - BATCH_SIZE must be ≥ 5000
  - inserts must use `ordered=False`
  - writes must go through `db_bg` (not the CSOT-capped `db`)
"""
import io
import os
import time
import uuid
from pathlib import Path

import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://lanjut-core.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"
SUPER_EMAIL = "superadmin@rilismusik.com"
SUPER_PASS = "SuperAdmin#2026"


def _mongo_db():
    import pymongo
    client = pymongo.MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    return client[os.environ.get("DB_NAME", "rilismusik_db")]


def _login_super() -> str:
    r = requests.post(f"{API}/auth/login", json={"email": SUPER_EMAIL, "password": SUPER_PASS}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def _hdr(tok: str):
    return {"Authorization": f"Bearer {tok}"}


def _gen_csv(n_rows: int) -> bytes:
    """Generate a synthetic Believe-format CSV with `n_rows` rows."""
    headers = [
        "ISRC", "UPC", "Track title", "Artist", "Release title", "Label",
        "Platform", "Country", "Quantity", "Net revenue in EUR", "Reporting month",
    ]
    out = io.StringIO()
    out.write(",".join(headers) + "\n")
    for i in range(n_rows):
        row = [
            f"TEST{i:08d}",                  # ISRC
            f"{1000000 + i:013d}",           # UPC
            f"Track {i}",
            f"Artist {i % 50}",
            f"Release {i % 100}",
            f"TEST_LABEL_{i % 3}",
            "Spotify",
            "ID",
            "1000",
            "0.50",
            "2026-01",
        ]
        out.write(",".join(row) + "\n")
    return out.getvalue().encode("utf-8")


@pytest.fixture(scope="module")
def super_token():
    return _login_super()


def test_source_batch_size_at_least_5000():
    src = (Path(__file__).resolve().parents[1] / "routes" / "royalty.py").read_text()
    assert "BATCH_SIZE = 5000" in src, "BATCH_SIZE must be 5000 — smaller wastes round trips on 1M-row imports"


def test_source_inserts_use_ordered_false():
    src = (Path(__file__).resolve().parents[1] / "routes" / "royalty.py").read_text()
    # All five `insert_many` calls inside _process_csv_import_inline must be
    # ordered=False so a single bad row doesn't abort the whole batch and they
    # can run in parallel. (labels, releases, tracks, artists, royalty_lines)
    fn_start = src.index("async def _process_csv_import_inline(")
    rest = src[fn_start:]
    fn_end_rel = rest.index("\nasync def _process_csv_import_bg(")
    body = rest[:fn_end_rel]
    assert body.count("insert_many(") == 5, f"expected 5 insert_many calls inside _process_csv_import_inline, got {body.count('insert_many(')}"
    assert body.count("ordered=False") >= 5, "every insert_many must pass ordered=False"


def test_source_inserts_use_db_bg():
    src = (Path(__file__).resolve().parents[1] / "routes" / "royalty.py").read_text()
    fn_start = src.index("async def _process_csv_import_inline(")
    rest = src[fn_start:]
    fn_end_rel = rest.index("\nasync def _process_csv_import_bg(")
    body = rest[:fn_end_rel]
    # The five bulk inserts must use db_bg
    for coll in ("royalty_lines", "labels", "releases", "tracks", "artists"):
        assert f"db_bg.{coll}.insert_many(" in body, f"insert_many for {coll} must go through db_bg"
    # The big preflight cursor scans on labels/tracks/releases must also use db_bg
    assert "db_bg.tracks.find(" in body
    assert "db_bg.releases.find(" in body
    assert "db_bg.labels.find(" in body


def test_source_progress_throttled():
    src = (Path(__file__).resolve().parents[1] / "routes" / "royalty.py").read_text()
    assert "PROGRESS_EVERY_N_FLUSHES" in src, (
        "progress writes must be throttled to avoid 500+ updates on a 1M-row import"
    )


def test_seed_includes_isrc_upc_compound_indexes():
    """The hot CSV-matcher lookups require single-field indexes on
    `tracks.isrc` and `releases.upc`. Without these, a 100k-row collection scan
    runs every time someone uploads a CSV.

    The publish/per-label aggregates also need a compound on
    (import_id, match_status, status) — verified to keep the IXSCAN fast.
    """
    src = (Path(__file__).resolve().parents[1] / "routes" / "seed.py").read_text()
    assert 'tracks.create_index("isrc")' in src
    assert 'releases.create_index("upc")' in src
    assert '("import_id", 1), ("match_status", 1), ("status", 1)' in src


def test_10k_row_csv_import_under_30s(super_token):
    """End-to-end: upload a 10k-row synthetic CSV and verify it finishes
    ingestion under 30 seconds locally. On production this throughput projects
    to ~3-5 minutes for a 1M-row import (vs. previous ~10 minutes).
    """
    db = _mongo_db()
    n_rows = 10_000
    # Period must match YYYY-MM. Use a sentinel year so we don't collide with
    # real imports and cleanup is easy.
    period = "2099-12"
    csv_bytes = _gen_csv(n_rows)

    files = {"file": (f"bench_{period}.csv", csv_bytes, "text/csv")}
    data = {"period": period, "rate_eur_idr": "17500", "fee_percent": "15"}

    t0 = time.monotonic()
    r = requests.post(
        f"{API}/royalty/admin/imports",
        files=files, data=data, headers=_hdr(super_token), timeout=120,
    )
    elapsed = time.monotonic() - t0
    assert r.status_code == 200, r.text
    import_id = r.json()["id"]

    # Wait for background processing to finish if it didn't run synchronously
    for _ in range(60):
        imp = db.royalty_imports.find_one({"id": import_id})
        if imp and imp.get("status") in ("pending_review", "error"):
            break
        time.sleep(1)
    imp = db.royalty_imports.find_one({"id": import_id})
    assert imp["status"] == "pending_review", f"unexpected status {imp.get('status')}: {imp.get('error_message')}"

    total_elapsed = time.monotonic() - t0
    rows_inserted = db.royalty_lines.count_documents({"import_id": import_id})
    assert rows_inserted == n_rows, f"expected {n_rows} rows inserted, got {rows_inserted}"
    assert total_elapsed < 30, f"10k-row ingestion took {total_elapsed:.1f}s (must be <30s)"
    print(f"PERF: {n_rows} rows ingested in {total_elapsed:.1f}s → {n_rows/total_elapsed:.0f} rows/sec")

    # Cleanup
    requests.delete(f"{API}/royalty/admin/imports/{import_id}", headers=_hdr(super_token), timeout=30)
