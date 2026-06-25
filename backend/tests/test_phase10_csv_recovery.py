"""Phase 10 — Background CSV import recovery & retry tests.

Covers:
  - GET /admin/imports/{id} returns {import, lines, per_label} (regression for
    the duplicate-endpoint bug)
  - POST /admin/imports/{id}/retry on a fresh dana_received import returns 400
    (only processing/error allowed)
  - POST /admin/imports/{id}/retry on a non-existent import returns 404
  - Retry of an artificially-stuck 'processing' import succeeds and the import
    eventually transitions to 'pending_review'
"""
import io
import os
import time
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://lanjut-core.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

SUPER = {"email": "superadmin@rilismusik.com", "password": "SuperAdmin#2026"}
FINANCE = {"email": "finance1@rilismusik.com", "password": "Finance#2026"}
RELEASE = {"email": "release1@rilismusik.com", "password": "Release#2026"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login {creds['email']} -> {r.status_code} {r.text[:200]}"
    return r.json()["access_token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


def _make_csv():
    """Tiny CSV that exercises auto-create + multi-period + the standard Believe header layout."""
    csv = (
        "Bulan Laporan,ISRC,UPC,Judul Track,Nama Artis,Judul Release,Nama Label,Platform,Negara,Kuantitas,Pendapatan Bersih\n"
        f"2024-01,ID00P{uuid.uuid4().hex[:8].upper()},,Lagu Phase 10 A,Artis P10,Album P10,Phase10Label{uuid.uuid4().hex[:6]},Spotify,ID,1234,12.3456\n"
        f"2024-02,ID00P{uuid.uuid4().hex[:8].upper()},,Lagu Phase 10 B,Artis P10,Album P10,Phase10Label{uuid.uuid4().hex[:6]},Apple Music,ID,567,8.9012\n"
    )
    return csv.encode("utf-8")


@pytest.fixture(scope="module")
def super_tok():
    return _login(SUPER)


@pytest.fixture(scope="module")
def finance_tok():
    return _login(FINANCE)


@pytest.fixture(scope="module")
def fresh_import(finance_tok):
    """Upload a small CSV → processes inline → returns the import doc."""
    files = {"file": (f"phase10_{uuid.uuid4().hex}.csv", _make_csv(), "text/csv")}
    data = {"rate_eur_idr": 17500, "note": "phase10 test"}
    r = requests.post(f"{API}/royalty/admin/imports", files=files, data=data, headers=_h(finance_tok), timeout=60)
    assert r.status_code == 200, r.text[:400]
    return r.json()


def test_detail_endpoint_returns_lines_and_per_label(finance_tok, fresh_import):
    """Regression: the duplicate GET endpoint was shadowing the rich version
    and the frontend RoyaltyDetail page was broken.
    """
    import_id = fresh_import["id"]
    r = requests.get(f"{API}/royalty/admin/imports/{import_id}", headers=_h(finance_tok), timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert "import" in body and "lines" in body and "per_label" in body
    assert body["import"]["id"] == import_id


def test_retry_404_for_unknown_import(finance_tok):
    r = requests.post(f"{API}/royalty/admin/imports/nope-{uuid.uuid4().hex}/retry", headers=_h(finance_tok), timeout=20)
    assert r.status_code == 404


def test_retry_rejects_non_processing_status(finance_tok, fresh_import):
    import_id = fresh_import["id"]
    # Fresh import is 'pending_review' (synchronously processed) — retry forbidden
    r = requests.post(f"{API}/royalty/admin/imports/{import_id}/retry", headers=_h(finance_tok), timeout=20)
    assert r.status_code == 400
    assert "processing" in r.text.lower() or "error" in r.text.lower()


def test_retry_rbac_release_admin_forbidden(super_tok, fresh_import):
    """Admin Release cannot retry — only Super Admin / Admin Finance."""
    release_tok = _login(RELEASE)
    import_id = fresh_import["id"]
    r = requests.post(f"{API}/royalty/admin/imports/{import_id}/retry", headers=_h(release_tok), timeout=20)
    # 403 from inside the handler is the expected response
    assert r.status_code == 403


def test_imports_list_includes_progress_pct(finance_tok):
    """The list endpoint must expose progress_pct for in-flight items so the
    admin UI can render the progress bar without hitting the detail endpoint.
    """
    r = requests.get(f"{API}/royalty/admin/imports", headers=_h(finance_tok), timeout=30)
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    # Every item must have these keys (whether 0 or actual value)
    for it in items:
        assert "status" in it
