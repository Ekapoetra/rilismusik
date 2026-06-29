"""Phase 23.2 — Backfill royalty_lines.period from row_period.

Validates the `POST /api/admin/migrate/royalty/backfill-period-from-row`
endpoint that retroactively fixes the `period` field on royalty_lines docs
imported BEFORE Phase 23.1 (when the form's period overrode the CSV's
`Bulan Laporan` column).

Setup pattern: seed N royalty_lines with `period='2020-01'` (simulating an
old yearly import) but `row_period='2020-XX'` (the real CSV Bulan Laporan
that was preserved in the row). Then dry-run + commit + verify.
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
SUPPORT = ("support1@rilismusik.com", "Support#2026")


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
def seeded_legacy_yearly_import():
    """Seed a fake 'yearly' royalty_import doc with 24 lines spanning months
    2020-01 .. 2020-12 (2 rows per month). All rows have `period='2020-01'`
    (simulating the bad pre-Phase-23.1 behaviour) but their `row_period` field
    correctly carries the real Bulan Laporan value.
    """
    db = _db()
    import_id = f"phase232-yearly-{uuid.uuid4().hex[:10]}"
    label_id = f"phase232-lab-{uuid.uuid4().hex[:8]}"

    db.royalty_imports.insert_one({
        "id": import_id,
        "filename": "phase232_yearly_2020.csv",
        "status": "published",  # already published — common in production
        "exchange_rate_eur_idr": 17500,
        "fee_percent": 5.0,
        "total_lines": 24,
        "processed_lines": 24,
        "progress_pct": 100,
        "matched_lines": 24,
        "unmatched_lines": 0,
        "period": "2020-01",
        "period_start": "2020-01",
        "period_end": "2020-01",
        "is_multi_period": False,
        "period_breakdown": {"2020-01": 24},  # WRONG — should be 12 buckets after backfill
        "created_at": "2021-01-15T00:00:00+00:00",
        "updated_at": "2021-01-15T00:00:00+00:00",
        "uploaded_by": "system",
    })

    db.labels.insert_one({
        "id": label_id,
        "label_name": f"Phase232 Test {import_id[-6:]}",
        "balance_pending_idr": 0,
        "balance_available_idr": 0,
    })

    lines = []
    for month in range(1, 13):
        real_period = f"2020-{month:02d}"
        for k in range(2):
            lines.append({
                "id": f"line-{import_id}-{month:02d}-{k}",
                "import_id": import_id,
                # The BAD value — what backfill must fix
                "period": "2020-01",
                # The GOOD value preserved from CSV
                "row_period": real_period,
                "label_id": label_id,
                "match_status": "matched",
                "status": "draft",
                "revenue_eur": 1.5,
                "label_idr": 15000,
                "isrc": f"PH232M{month:02d}{k}",
            })
    db.royalty_lines.insert_many(lines)

    yield import_id, label_id

    # Cleanup
    db.royalty_lines.delete_many({"import_id": import_id})
    db.royalty_imports.delete_one({"id": import_id})
    db.labels.delete_one({"id": label_id})


def test_dry_run_does_not_mutate(super_token, seeded_legacy_yearly_import):
    import_id, _ = seeded_legacy_yearly_import
    db = _db()
    r = requests.post(
        f"{API}/admin/migrate/royalty/backfill-period-from-row",
        headers=_hdr(super_token),
        data={"dry_run": "true", "import_id": import_id},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["dry_run"] is True
    # Month 1 rows already have period == row_period == "2020-01" → not flagged.
    # Months 2-12 (11 months × 2 rows each) need fixing = 22.
    assert j["total_rows_to_fix"] == 22
    assert j["imports_affected"] == 1
    # Mongo state must be untouched
    lines = list(db.royalty_lines.find({"import_id": import_id}))
    assert all(ln["period"] == "2020-01" for ln in lines), "dry-run mutated data!"
    imp = db.royalty_imports.find_one({"id": import_id})
    assert imp["period_breakdown"] == {"2020-01": 24}, "dry-run mutated import doc!"
    # Summary should expose old vs new periods
    summary = j["summary"][0]
    assert summary["rows_to_fix"] == 22
    assert summary["old_periods_in_lines"] == ["2020-01"]
    assert set(summary["new_periods_will_be"]) == {f"2020-{m:02d}" for m in range(2, 13)}


def test_commit_rewrites_period_and_recomputes_import(super_token, seeded_legacy_yearly_import):
    import_id, _ = seeded_legacy_yearly_import
    db = _db()
    r = requests.post(
        f"{API}/admin/migrate/royalty/backfill-period-from-row",
        headers=_hdr(super_token),
        data={"dry_run": "false", "import_id": import_id},
        timeout=60,
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["dry_run"] is False
    assert j["commit"]["applied"] is True
    # 22 rows need fix (months 2-12 × 2), month 1 already matches
    assert j["commit"]["rows_updated"] == 22
    assert j["commit"]["imports_recomputed"] == 1

    # Verify line-level period was rewritten to match row_period
    lines = list(db.royalty_lines.find({"import_id": import_id}))
    for ln in lines:
        assert ln["period"] == ln["row_period"], f"line {ln['id']} period not fixed"
    # Verify import doc metadata was recomputed
    imp = db.royalty_imports.find_one({"id": import_id})
    assert imp["is_multi_period"] is True
    assert imp["period"] == "multi"
    assert imp["period_start"] == "2020-01"
    assert imp["period_end"] == "2020-12"
    assert set(imp["period_breakdown"].keys()) == {f"2020-{m:02d}" for m in range(1, 13)}
    assert all(v == 2 for v in imp["period_breakdown"].values())

    # Idempotency — re-running should find 0 rows to fix
    r2 = requests.post(
        f"{API}/admin/migrate/royalty/backfill-period-from-row",
        headers=_hdr(super_token),
        data={"dry_run": "false", "import_id": import_id},
        timeout=30,
    )
    assert r2.status_code == 200
    assert r2.json()["total_rows_to_fix"] == 0


def test_rbac_super_admin_only(seeded_legacy_yearly_import):
    """Only super_admin may run backfill — admin_finance / support / release get 403."""
    import_id, _ = seeded_legacy_yearly_import
    for creds in (FINANCE, SUPPORT):
        t = _login(*creds)
        r = requests.post(
            f"{API}/admin/migrate/royalty/backfill-period-from-row",
            headers=_hdr(t),
            data={"dry_run": "true", "import_id": import_id},
            timeout=30,
        )
        assert r.status_code == 403, f"{creds[0]} got {r.status_code} instead of 403"


def test_unknown_import_id_returns_404(super_token):
    r = requests.post(
        f"{API}/admin/migrate/royalty/backfill-period-from-row",
        headers=_hdr(super_token),
        data={"dry_run": "true", "import_id": "phase232-does-not-exist-xyz"},
        timeout=30,
    )
    assert r.status_code == 404


def test_full_database_backfill_only_touches_mismatched_rows(super_token):
    """Run a global backfill (no import_id) — must only touch rows where
    row_period != period. Rows that already match must be untouched.
    """
    db = _db()
    import_id_good = f"phase232-good-{uuid.uuid4().hex[:10]}"
    import_id_bad = f"phase232-bad-{uuid.uuid4().hex[:10]}"

    # GOOD import: period == row_period (matches expected post-Phase-23.1 state)
    db.royalty_imports.insert_one({
        "id": import_id_good, "filename": "good.csv", "status": "published",
        "exchange_rate_eur_idr": 17500, "fee_percent": 5.0,
        "total_lines": 5, "is_multi_period": False, "period": "2024-06",
        "created_at": "2024-07-01T00:00:00+00:00", "updated_at": "2024-07-01T00:00:00+00:00",
    })
    db.royalty_lines.insert_many([{
        "id": f"good-{import_id_good}-{k}",
        "import_id": import_id_good, "period": "2024-06", "row_period": "2024-06",
        "match_status": "matched", "status": "draft",
        "revenue_eur": 1.0, "label_idr": 10000,
    } for k in range(5)])

    # BAD import: period == "2023-01" but row_period == "2023-0X"
    db.royalty_imports.insert_one({
        "id": import_id_bad, "filename": "bad.csv", "status": "published",
        "exchange_rate_eur_idr": 17500, "fee_percent": 5.0,
        "total_lines": 3, "is_multi_period": False, "period": "2023-01",
        "period_breakdown": {"2023-01": 3},
        "created_at": "2024-02-01T00:00:00+00:00", "updated_at": "2024-02-01T00:00:00+00:00",
    })
    db.royalty_lines.insert_many([
        {"id": f"bad-{import_id_bad}-1", "import_id": import_id_bad,
         "period": "2023-01", "row_period": "2023-01", "match_status": "matched",
         "status": "draft", "revenue_eur": 1.0, "label_idr": 10000},  # actually correct — no-op
        {"id": f"bad-{import_id_bad}-2", "import_id": import_id_bad,
         "period": "2023-01", "row_period": "2023-02", "match_status": "matched",
         "status": "draft", "revenue_eur": 1.0, "label_idr": 10000},  # needs fix
        {"id": f"bad-{import_id_bad}-3", "import_id": import_id_bad,
         "period": "2023-01", "row_period": "2023-03", "match_status": "matched",
         "status": "draft", "revenue_eur": 1.0, "label_idr": 10000},  # needs fix
    ])

    try:
        # Dry-run global backfill — should find only the 2 bad rows from bad import
        r = requests.post(
            f"{API}/admin/migrate/royalty/backfill-period-from-row",
            headers=_hdr(super_token),
            data={"dry_run": "true"},  # no import_id → full DB
            timeout=60,
        )
        assert r.status_code == 200, r.text
        j = r.json()
        # `imports_affected` must INCLUDE bad import but NOT good import
        affected_ids = {s["import_id"] for s in j["summary"]}
        assert import_id_bad in affected_ids
        assert import_id_good not in affected_ids
        # Specifically, the bad import contributes 2 rows
        bad_summary = next(s for s in j["summary"] if s["import_id"] == import_id_bad)
        assert bad_summary["rows_to_fix"] == 2

        # Commit global backfill
        r2 = requests.post(
            f"{API}/admin/migrate/royalty/backfill-period-from-row",
            headers=_hdr(super_token),
            data={"dry_run": "false"},
            timeout=120,
        )
        assert r2.status_code == 200
        # The good import's lines must be untouched
        good_lines = list(db.royalty_lines.find({"import_id": import_id_good}))
        for ln in good_lines:
            assert ln["period"] == "2024-06"
        # The bad import's mismatched lines should now match row_period
        bad_lines = sorted(db.royalty_lines.find({"import_id": import_id_bad}), key=lambda x: x["id"])
        for ln in bad_lines:
            assert ln["period"] == ln["row_period"]
    finally:
        db.royalty_lines.delete_many({"import_id": {"$in": [import_id_good, import_id_bad]}})
        db.royalty_imports.delete_many({"id": {"$in": [import_id_good, import_id_bad]}})


def test_no_changes_needed_returns_zero(super_token):
    """If a database has zero rows where period != row_period, the endpoint
    should return a clean zero-counts response without errors."""
    db = _db()
    import_id = f"phase232-zero-{uuid.uuid4().hex[:10]}"
    db.royalty_imports.insert_one({
        "id": import_id, "filename": "zero.csv", "status": "published",
        "exchange_rate_eur_idr": 17500, "fee_percent": 5.0,
        "total_lines": 2, "is_multi_period": False, "period": "2024-08",
        "created_at": "2024-09-01T00:00:00+00:00", "updated_at": "2024-09-01T00:00:00+00:00",
    })
    db.royalty_lines.insert_many([{
        "id": f"zero-{import_id}-{k}", "import_id": import_id,
        "period": "2024-08", "row_period": "2024-08",
        "match_status": "matched", "status": "draft",
        "revenue_eur": 1.0, "label_idr": 10000,
    } for k in range(2)])
    try:
        r = requests.post(
            f"{API}/admin/migrate/royalty/backfill-period-from-row",
            headers=_hdr(super_token),
            data={"dry_run": "false", "import_id": import_id},
            timeout=30,
        )
        assert r.status_code == 200
        j = r.json()
        assert j["total_rows_to_fix"] == 0
        assert j["imports_affected"] == 0
    finally:
        db.royalty_lines.delete_many({"import_id": import_id})
        db.royalty_imports.delete_one({"id": import_id})
