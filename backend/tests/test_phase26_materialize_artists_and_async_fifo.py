"""Phase 26 — Materialize artists + async withdraw FIFO.

Two unrelated features bundled in this phase:

1. POST /api/admin/migrate/materialize-artists
   Scans royalty_lines for unique (label_id, artist_name) combos and creates
   artist documents (since CSV ingestion never auto-creates them). Backfills
   artist_id on lines + tracks.

2. POST /api/admin/migrate/withdraws-legacy-period
   Already existed (Phase 22) but commit phase used to run synchronously and
   timed out at 120s on production datasets. Phase 26 makes commit return
   HTTP 200 with `commit.queued=true` + `job_id`. Heavy writes run in
   background; status polled via GET /api/admin/migrate/jobs/{job_id}.
"""
import os
import time
import uuid
import requests
import pytest
import pymongo

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://lanjut-core.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"
SUPER = ("superadmin@rilismusik.com", "SuperAdmin#2026")
FINANCE = ("finance1@rilismusik.com", "Finance#2026")


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


# ---------------------------------------------------------------------------
# Materialize artists tests
# ---------------------------------------------------------------------------

@pytest.fixture
def seeded_lines_without_artists():
    """Seed 2 labels, 5 artist names spread across lines. None of them have
    an artist_id set. Plus one line with `artist_name_raw="Unknown"` which
    must be skipped by the materializer.
    """
    db = _db()
    label_a = f"phase26-laba-{uuid.uuid4().hex[:8]}"
    label_b = f"phase26-labb-{uuid.uuid4().hex[:8]}"
    db.labels.insert_many([
        {"id": label_a, "label_name": "Phase26 Label A"},
        {"id": label_b, "label_name": "Phase26 Label B"},
    ])

    artists_a = ["Phase26 Singer One", "Phase26 Singer Two", "Phase26 Singer Three"]
    artists_b = ["Phase26 Singer One", "Phase26 Band X"]  # "Singer One" appears in both labels
    lines = []
    for art in artists_a:
        for k in range(3):
            lines.append({
                "id": f"line-A-{art[-1]}-{k}",
                "import_id": "phase26-imp", "label_id": label_a,
                "artist_id": None, "artist_name_raw": art,
                "match_status": "matched", "status": "draft",
                "period": "2024-01", "row_period": "2024-01",
                "revenue_eur": 1.5, "label_idr": 15000, "quantity": 1,
            })
    for art in artists_b:
        for k in range(2):
            lines.append({
                "id": f"line-B-{art[-1]}-{k}",
                "import_id": "phase26-imp", "label_id": label_b,
                "artist_id": None, "artist_name_raw": art,
                "match_status": "matched", "status": "draft",
                "period": "2024-02", "row_period": "2024-02",
                "revenue_eur": 2.0, "label_idr": 20000, "quantity": 1,
            })
    # Sentinel that must be excluded
    lines.append({
        "id": "line-A-unknown", "import_id": "phase26-imp", "label_id": label_a,
        "artist_id": None, "artist_name_raw": "Unknown",
        "match_status": "matched", "status": "draft",
        "period": "2024-01", "row_period": "2024-01",
        "revenue_eur": 1.0, "label_idr": 10000, "quantity": 1,
    })
    db.royalty_lines.insert_many(lines)

    yield {"label_a": label_a, "label_b": label_b,
           "artists_a": artists_a, "artists_b": artists_b}
    db.royalty_lines.delete_many({"import_id": "phase26-imp"})
    db.labels.delete_many({"id": {"$in": [label_a, label_b]}})
    db.artists.delete_many({"label_id": {"$in": [label_a, label_b]}})


def _wait_for_job(super_token, job_id, max_wait=30):
    """Poll a migrate job until status leaves processing/queued, then return
    the final job doc. Phase 27: Materialize Artists is now async."""
    for _ in range(max_wait * 2):
        r = requests.get(f"{API}/admin/migrate/jobs/{job_id}",
                         headers=_hdr(super_token), timeout=15)
        if r.status_code == 200:
            job = r.json()
            if job["status"] in ("done", "error"):
                return job
        time.sleep(0.5)
    raise AssertionError(f"job {job_id} did not finish within {max_wait}s")


def test_materialize_dry_run_does_not_mutate(super_token, seeded_lines_without_artists):
    db = _db()
    ctx = seeded_lines_without_artists
    # Phase 27: endpoint returns job_id, work runs in background.
    r = requests.post(
        f"{API}/admin/migrate/materialize-artists",
        headers=_hdr(super_token),
        data={"dry_run": "true"},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("job_id"), f"missing job_id in {body}"
    job = _wait_for_job(super_token, body["job_id"])
    assert job["status"] == "done", f"job errored: {job.get('error_message')}"
    j = job["result"]
    assert j["dry_run"] is True
    # The endpoint scans ALL royalty_lines, so other test fixtures' lines may
    # also be counted. Assert >= our seeded 5 unique combos.
    assert j["combos_in_lines"] >= 5
    assert j["artists_to_create"] >= 5
    preview_keys = {(a["label_id"], a["artist_name"]) for a in j.get("top_preview", [])}
    expected_combos = {(ctx["label_a"], n) for n in ctx["artists_a"]} | {(ctx["label_b"], n) for n in ctx["artists_b"]}
    assert expected_combos.issubset(preview_keys), f"missing combos: {expected_combos - preview_keys}"
    # Mongo state unchanged for OUR seeded labels
    n_art = db.artists.count_documents({"label_id": {"$in": [ctx["label_a"], ctx["label_b"]]}})
    assert n_art == 0
    n_lines_with_artist = db.royalty_lines.count_documents({
        "import_id": "phase26-imp", "artist_id": {"$ne": None}
    })
    assert n_lines_with_artist == 0


def test_materialize_commit_creates_artists_and_backfills(super_token, seeded_lines_without_artists):
    db = _db()
    ctx = seeded_lines_without_artists
    r = requests.post(
        f"{API}/admin/migrate/materialize-artists",
        headers=_hdr(super_token),
        data={"dry_run": "false"},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    job = _wait_for_job(super_token, body["job_id"])
    assert job["status"] == "done", f"job errored: {job.get('error_message')}"
    j = job["result"]
    assert j["dry_run"] is False
    assert j["commit"]["applied"] is True
    # Other test fixtures may also leak lines into the scan; assert AT LEAST
    # our 5 artists were created.
    assert j["commit"]["artists_created"] >= 5

    # Verify each artist exists with correct label_id
    arts_a = list(db.artists.find({"label_id": ctx["label_a"]}))
    arts_b = list(db.artists.find({"label_id": ctx["label_b"]}))
    assert len(arts_a) == 3
    assert len(arts_b) == 2
    a_names = sorted([a["artist_name"] for a in arts_a])
    assert a_names == sorted(ctx["artists_a"])

    # Verify lines now have artist_id set (and Unknown is still null)
    seeded_lines_with_artist = db.royalty_lines.count_documents({
        "import_id": "phase26-imp", "artist_id": {"$ne": None}
    })
    assert seeded_lines_with_artist == 13  # 9 + 4

    n_unknown = db.royalty_lines.count_documents({
        "import_id": "phase26-imp", "artist_name_raw": "Unknown",
    })
    n_unknown_with_artist = db.royalty_lines.count_documents({
        "import_id": "phase26-imp", "artist_name_raw": "Unknown",
        "artist_id": {"$ne": None},
    })
    assert n_unknown == 1
    assert n_unknown_with_artist == 0, "Unknown rows must remain artist_id=null"


def test_materialize_idempotent(super_token, seeded_lines_without_artists):
    """Re-running commit must result in 0 new artists, 0 lines updated."""
    # First commit
    r1 = requests.post(f"{API}/admin/migrate/materialize-artists",
                       headers=_hdr(super_token), data={"dry_run": "false"}, timeout=15)
    _wait_for_job(super_token, r1.json()["job_id"])
    # Second commit
    r2 = requests.post(f"{API}/admin/migrate/materialize-artists",
                       headers=_hdr(super_token), data={"dry_run": "false"}, timeout=15)
    job = _wait_for_job(super_token, r2.json()["job_id"])
    j = job["result"]
    assert j["artists_to_create"] == 0
    assert j["commit"]["artists_created"] == 0
    assert j["commit"]["lines_updated"] == 0


def test_materialize_rbac_super_admin_only(seeded_lines_without_artists):
    finance_t = _login(*FINANCE)
    r = requests.post(
        f"{API}/admin/migrate/materialize-artists",
        headers=_hdr(finance_t),
        data={"dry_run": "true"},
        timeout=30,
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Withdraw FIFO async commit tests
# ---------------------------------------------------------------------------

def _make_withdraw_csv(rows):
    import csv as _csv
    import io as _io
    buf = _io.StringIO()
    writer = _csv.writer(buf, quoting=_csv.QUOTE_ALL)
    writer.writerow(["nama_label", "period_start", "period_end", "amount", "exchange_rate", "trx_id", "status"])
    for r in rows:
        writer.writerow([r.get("nama_label", ""), r.get("period_start", ""), r.get("period_end", ""),
                         r.get("amount", "0"), r.get("exchange_rate", "17000"),
                         r.get("trx_id", ""), r.get("status", "paid")])
    return buf.getvalue().encode("utf-8")


def test_withdraw_fifo_commit_returns_job_id_and_runs_in_background(super_token):
    db = _db()
    label_id = f"phase26-wfifo-{uuid.uuid4().hex[:8]}"
    db.labels.insert_one({
        "id": label_id, "label_name": "Phase26 Withdraw Lab",
        "balance_pending_idr": 50000, "balance_available_idr": 100000,
    })
    db.royalty_lines.insert_many([{
        "id": f"wfifo-{label_id}-{k}",
        "import_id": "phase26-wfifo-imp", "label_id": label_id,
        "match_status": "matched", "status": "pending" if k < 3 else "available",
        "period": "2023-01", "row_period": "2023-01",
        "label_idr": 10000, "revenue_eur": 1.0, "quantity": 1,
    } for k in range(5)])

    csv_bytes = _make_withdraw_csv([
        {"nama_label": "Phase26 Withdraw Lab", "period_end": "2023-12",
         "amount": "50", "trx_id": "PH26TRX001"}
    ])
    files = {"file": ("withdraws.csv", csv_bytes, "text/csv")}
    data = {"dry_run": "false", "create_history_docs": "true",
            "flip_royalty_lines": "true", "adjust_balances": "true"}
    try:
        r = requests.post(
            f"{API}/admin/migrate/withdraws-legacy-period",
            headers=_hdr(super_token), files=files, data=data, timeout=60,
        )
        assert r.status_code == 200, r.text
        j = r.json()
        # Phase 26: commit returns queued=true + job_id
        assert j["commit"]["applied"] is False
        assert j["commit"]["queued"] is True
        assert j["commit"]["job_id"]
        job_id = j["commit"]["job_id"]

        # Poll job status (up to 15s — the bg task is fast on small dataset)
        final_job = None
        for _ in range(30):
            jr = requests.get(f"{API}/admin/migrate/jobs/{job_id}",
                              headers=_hdr(super_token), timeout=15)
            assert jr.status_code == 200, jr.text
            job = jr.json()
            if job["status"] in ("done", "error"):
                final_job = job
                break
            time.sleep(0.5)
        assert final_job is not None, "BG job never finished"
        assert final_job["status"] == "done", f"job errored: {final_job.get('error_message')}"
        res = final_job["result"]
        assert res["applied"] is True
        assert res["labels_period_updated"] == 1
        # 5 royalty_lines covering period 2023-01 ≤ 2023-12 should all flip
        assert res["royalty_lines_flipped"] == 5
        assert res["history_docs_inserted"] == 1

        # Verify Mongo state
        lab = db.labels.find_one({"id": label_id})
        assert lab["last_withdrawn_period"] == "2023-12"
        # Pending sum was 3×10000=30000, available sum was 2×10000=20000
        assert lab["balance_pending_idr"] == 50000 - 30000
        assert lab["balance_available_idr"] == 100000 - 20000
        # All 5 lines now status='withdrawn'
        n_withdrawn = db.royalty_lines.count_documents({
            "import_id": "phase26-wfifo-imp", "status": "withdrawn"
        })
        assert n_withdrawn == 5
        # Withdraw history doc inserted with legacy_import flag
        hist = db.withdraw_requests.find_one(
            {"label_id": label_id, "legacy_trx_id": "PH26TRX001"}
        )
        assert hist is not None
        assert hist["legacy_import"] is True
    finally:
        db.royalty_lines.delete_many({"import_id": "phase26-wfifo-imp"})
        db.labels.delete_one({"id": label_id})
        db.withdraw_requests.delete_many({"label_id": label_id})
        db.migrate_jobs.delete_many({"submitted_by": {"$exists": True}})


def test_withdraw_fifo_dry_run_still_synchronous(super_token):
    """Dry-run must NOT spawn a job — returns full preview synchronously."""
    db = _db()
    label_id = f"phase26-dry-{uuid.uuid4().hex[:8]}"
    db.labels.insert_one({"id": label_id, "label_name": "Phase26 Dry Lab"})
    csv_bytes = _make_withdraw_csv([
        {"nama_label": "Phase26 Dry Lab", "period_end": "2024-06", "trx_id": "DRYTRX"}
    ])
    files = {"file": ("dry.csv", csv_bytes, "text/csv")}
    try:
        r = requests.post(
            f"{API}/admin/migrate/withdraws-legacy-period",
            headers=_hdr(super_token), files=files,
            data={"dry_run": "true"}, timeout=30,
        )
        assert r.status_code == 200
        j = r.json()
        assert j["dry_run"] is True
        assert j["commit"]["applied"] is False
        assert j["commit"].get("queued") is not True
        assert j.get("job_id") is None
    finally:
        db.labels.delete_one({"id": label_id})


def test_get_job_404_when_unknown(super_token):
    r = requests.get(f"{API}/admin/migrate/jobs/nope-nope-nope",
                     headers=_hdr(super_token), timeout=15)
    assert r.status_code == 404
