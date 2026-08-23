"""Phase 23.1 — CSV `Bulan Laporan` column priority.

User explicitly requested: the `Bulan Laporan` column is the ONLY period
source. The form field and `Bulan Penjualan` must never be fallbacks.

Why this matters: multi-period Believe CSVs (one upload containing rows from
multiple months) require each row's true period to be preserved for analytics,
FIFO withdraw, and rollups to compute correctly. The previous behaviour
(form-period wins) was overwriting actual CSV data.
"""
import io
import os
import csv as _csv
import time
import uuid
import requests
from tests.support_config import SUPERADMIN
import pytest
import pymongo

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


def _make_multi_period_csv(rows):
    """Build a Believe-format CSV with explicit `Bulan Laporan` column."""
    buf = io.StringIO()
    writer = _csv.writer(buf, quoting=_csv.QUOTE_ALL)
    writer.writerow([
        "Bulan Laporan", "Platform", "Negara", "ISRC", "UPC", "Judul Lagu",
        "Artis", "Judul Rilisan", "Label", "Kuantitas", "Pendapatan Bersih",
    ])
    for r in rows:
        writer.writerow([
            r["bulan_laporan"], r.get("platform", "Spotify"), r.get("country", "ID"),
            r.get("isrc", ""), r.get("upc", ""), r.get("track_title", "Test Track"),
            r.get("artist", "Test Artist"), r.get("release_title", "Test Release"),
            r.get("label_name", ""), r.get("qty", "1"), r.get("revenue_eur", "1.50"),
        ])
    return buf.getvalue().encode("utf-8")


@pytest.fixture(scope="module")
def super_token():
    return _login(*SUPER)


def _wait_until_done(import_id, super_token, max_wait_sec=60):
    """Poll the import until status leaves 'processing'.
    The detail endpoint returns {import: {...}, lines: [...], per_label: [...]}.
    """
    for _ in range(max_wait_sec * 2):
        r = requests.get(f"{API}/royalty/admin/imports/{import_id}", headers=_hdr(super_token), timeout=15)
        if r.status_code == 200:
            payload = r.json()
            imp = payload.get("import", payload)
            if imp.get("status") not in ("processing", "publishing"):
                return imp
        time.sleep(0.5)
    raise AssertionError(f"Import {import_id} did not finish in {max_wait_sec}s")


def test_csv_bulan_laporan_overrides_form_period(super_token):
    """Upload CSV with rows in periods 2024-01, 2024-02, 2024-03 while form
    period is set to 2025-12. Expect each row to keep its CSV period intact.
    """
    db = _db()
    # Use direct upload (multipart) — keeps the test simple, no R2 presigning.
    csv_bytes = _make_multi_period_csv([
        {"bulan_laporan": "2024-01", "isrc": f"TEST{uuid.uuid4().hex[:8].upper()}",
         "label_name": "PHASE231_TEST_LABEL"},
        {"bulan_laporan": "2024-02", "isrc": f"TEST{uuid.uuid4().hex[:8].upper()}",
         "label_name": "PHASE231_TEST_LABEL"},
        {"bulan_laporan": "2024-03", "isrc": f"TEST{uuid.uuid4().hex[:8].upper()}",
         "label_name": "PHASE231_TEST_LABEL"},
    ])
    files = {"file": ("test_multi_period.csv", csv_bytes, "text/csv")}
    data = {"period": "2025-12", "rate_eur_idr": "17500", "fee_percent": "5"}
    r = requests.post(
        f"{API}/royalty/admin/imports",
        headers=_hdr(super_token), files=files, data=data, timeout=60,
    )
    assert r.status_code in (200, 201, 202), f"upload failed: {r.status_code} {r.text}"
    import_id = r.json()["id"]
    try:
        imp = _wait_until_done(import_id, super_token, max_wait_sec=60)
        assert imp["status"] in ("pending_review", "published"), f"unexpected status: {imp.get('status')}"
        # is_multi_period should be True (3 different periods)
        assert imp.get("is_multi_period") is True, f"expected multi-period, got {imp}"
        # period_breakdown should reflect CSV's Bulan Laporan, not form
        breakdown = imp.get("period_breakdown") or {}
        assert set(breakdown.keys()) == {"2024-01", "2024-02", "2024-03"}, (
            f"period_breakdown should match CSV Bulan Laporan, got {breakdown}"
        )
        # display period stored as "multi" for multi-period imports
        assert imp.get("period") == "multi", f"display period should be 'multi', got {imp.get('period')}"
        assert imp.get("period_start") == "2024-01"
        assert imp.get("period_end") == "2024-03"
        # Verify actual royalty_lines docs — each should carry its CSV period
        lines = list(db.royalty_lines.find({"import_id": import_id}))
        periods_in_lines = sorted({ln["period"] for ln in lines})
        assert periods_in_lines == ["2024-01", "2024-02", "2024-03"], (
            f"royalty_lines must store CSV period, got {periods_in_lines}"
        )
        # Ensure NONE of the lines were tagged with the form's period
        assert all(ln["period"] != "2025-12" for ln in lines), (
            "no royalty_line should have been tagged with the form's period"
        )
    finally:
        # Cleanup via the async delete + brief wait
        requests.delete(f"{API}/royalty/admin/imports/{import_id}", headers=_hdr(super_token), timeout=30)
        time.sleep(3)
        # Final cleanup of any leftover test label
        db.labels.delete_many({"label_name": "PHASE231_TEST_LABEL"})


def test_missing_bulan_laporan_is_rejected_even_with_form_period(super_token):
    # Build a CSV WITHOUT the `Bulan Laporan` column
    buf = io.StringIO()
    writer = _csv.writer(buf, quoting=_csv.QUOTE_ALL)
    writer.writerow(["Platform", "Negara", "ISRC", "Judul Lagu", "Artis", "Label", "Kuantitas", "Pendapatan Bersih"])
    iso = f"TEST{uuid.uuid4().hex[:8].upper()}"
    writer.writerow(["Spotify", "ID", iso, "Legacy Track", "Legacy Artist", "PHASE231_LEGACY", "1", "2.00"])
    csv_bytes = buf.getvalue().encode("utf-8")

    files = {"file": ("legacy_no_bulan.csv", csv_bytes, "text/csv")}
    data = {"period": "2023-07", "rate_eur_idr": "17000", "fee_percent": "5"}
    r = requests.post(
        f"{API}/royalty/admin/imports",
        headers=_hdr(super_token), files=files, data=data, timeout=60,
    )
    assert r.status_code == 400, r.text
    assert "Bulan laporan" in r.text
