"""Phase 14 — Direct-to-R2 large-file upload flow.

Tests the new /api/royalty/admin/imports/initiate + /finalize endpoints,
the actual PUT to R2 against a presigned URL, CORS preflight, and
backward-compat with the existing multipart small-file flow.
"""
import os
import time
import pytest
import requests
from tests.support_config import FINANCE as FINANCE_CRED, RELEASE_ADMIN, SUPERADMIN

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
SUPER = (SUPERADMIN["email"], SUPERADMIN["password"])
FINANCE = (FINANCE_CRED["email"], FINANCE_CRED["password"])
RELEASE = (RELEASE_ADMIN["email"], RELEASE_ADMIN["password"])
FRONTEND_ORIGIN = "https://lanjut-core.preview.emergentagent.com"


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def super_tok():
    return _login(*SUPER)


@pytest.fixture(scope="module")
def finance_tok():
    return _login(*FINANCE)


@pytest.fixture(scope="module")
def release_tok():
    return _login(*RELEASE)


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


SMALL_CSV = (
    "ISRC,UPC,Judul Track,Nama Artis,Nama Label,Platform,Negara,Kuantitas,Pendapatan Bersih,Bulan Laporan\n"
    "USTEST0000001,1234567890123,TEST_Phase14_Track,TEST_Phase14_Artist,TEST_Phase14_Label_Direct,Spotify,ID,1000,0.50,2024-01\n"
    "USTEST0000002,1234567890124,TEST_Phase14_Track2,TEST_Phase14_Artist,TEST_Phase14_Label_Direct,YouTube,US,2000,1.20,2024-01\n"
)


# -------- AUTH / VALIDATION on /initiate --------
class TestInitiateAuth:
    def test_initiate_no_auth_401(self):
        r = requests.post(f"{BASE_URL}/api/royalty/admin/imports/initiate", json={
            "filename": "x.csv", "rate_eur_idr": 17500, "period": "2024-01"
        }, timeout=15)
        assert r.status_code == 401, f"expected 401, got {r.status_code}"

    def test_initiate_release_role_403(self, release_tok):
        r = requests.post(f"{BASE_URL}/api/royalty/admin/imports/initiate",
                          headers=H(release_tok),
                          json={"filename": "x.csv", "rate_eur_idr": 17500, "period": "2024-01"},
                          timeout=15)
        assert r.status_code == 403
        body = r.json()
        assert "Finance" in (body.get("detail") or "") or "Super Admin" in (body.get("detail") or "")

    def test_initiate_bad_rate_422(self, super_tok):
        r = requests.post(f"{BASE_URL}/api/royalty/admin/imports/initiate",
                          headers=H(super_tok),
                          json={"filename": "x.csv", "rate_eur_idr": 0, "period": "2024-01"},
                          timeout=15)
        assert r.status_code == 422, f"expected 422 for rate<=0, got {r.status_code}"

    def test_initiate_bad_period_400(self, super_tok):
        r = requests.post(f"{BASE_URL}/api/royalty/admin/imports/initiate",
                          headers=H(super_tok),
                          json={"filename": "x.csv", "rate_eur_idr": 17500, "period": "bad-period"},
                          timeout=15)
        assert r.status_code == 400, f"expected 400 for bad period, got {r.status_code}"


# -------- HAPPY PATH --------
class TestInitiateFinalizeFlow:
    @pytest.fixture(scope="class")
    def init_response(self, super_tok):
        payload = {
            "filename": "TEST_phase14_direct.csv",
            "rate_eur_idr": 17500,
            "period": "2024-01",
            "note": "TEST_phase14 direct-to-R2",
            "file_size_bytes": len(SMALL_CSV.encode("utf-8")),
        }
        r = requests.post(f"{BASE_URL}/api/royalty/admin/imports/initiate",
                          headers=H(super_tok), json=payload, timeout=20)
        assert r.status_code == 200, f"initiate failed: {r.status_code} {r.text}"
        data = r.json()
        for k in ("import_id", "presigned_put_url", "r2_key", "content_type", "expires_in"):
            assert k in data, f"missing {k} in response"
        assert data["content_type"] == "text/csv"
        assert data["expires_in"] == 7200
        assert data["r2_key"].startswith("csv/")
        assert data["r2_key"].endswith(".csv")
        return data

    def test_put_to_r2_succeeds(self, init_response):
        url = init_response["presigned_put_url"]
        r = requests.put(url, data=SMALL_CSV.encode("utf-8"),
                         headers={"Content-Type": init_response["content_type"]}, timeout=60)
        assert r.status_code in (200, 201), f"PUT to R2 failed: {r.status_code} {r.text[:300]}"

    def test_finalize_then_background_processes(self, super_tok, init_response):
        # PUT must succeed first (relies on test ordering inside class)
        import_id = init_response["import_id"]
        r = requests.post(f"{BASE_URL}/api/royalty/admin/imports/{import_id}/finalize",
                          headers=H(super_tok), timeout=30)
        assert r.status_code == 200, f"finalize failed: {r.status_code} {r.text}"
        body = r.json()
        assert body["id"] == import_id
        assert body["status"] == "processing"
        assert body["file_size_bytes"] == len(SMALL_CSV.encode("utf-8"))

        # Wait for background to flip to pending_review
        deadline = time.time() + 20
        final = None
        while time.time() < deadline:
            time.sleep(2)
            g = requests.get(f"{BASE_URL}/api/royalty/admin/imports/{import_id}",
                             headers=H(super_tok), timeout=15)
            assert g.status_code == 200
            final = g.json()["import"]
            if final["status"] in ("pending_review", "error"):
                break
        assert final is not None
        assert final["status"] == "pending_review", f"status stuck at {final['status']}: {final.get('error_message')}"
        # New label was auto-created (TEST_Phase14_Label_Direct didn't exist)
        assert final["auto_created_labels"] >= 1
        assert final["auto_created_tracks"] >= 1
        assert final["total_lines"] == 2


# -------- ERROR / EDGE CASES --------
class TestFinalizeErrors:
    def test_finalize_unknown_id_404(self, super_tok):
        r = requests.post(f"{BASE_URL}/api/royalty/admin/imports/nonexistent-id-xyz/finalize",
                          headers=H(super_tok), timeout=15)
        assert r.status_code == 404

    def test_finalize_without_put_returns_400(self, super_tok):
        # Initiate but never PUT — finalize should 400 with R2-not-found message
        init = requests.post(f"{BASE_URL}/api/royalty/admin/imports/initiate",
                             headers=H(super_tok),
                             json={"filename": "TEST_neverput.csv", "rate_eur_idr": 17500, "period": "2024-02"},
                             timeout=15).json()
        r = requests.post(f"{BASE_URL}/api/royalty/admin/imports/{init['import_id']}/finalize",
                          headers=H(super_tok), timeout=15)
        assert r.status_code == 400
        assert "belum berhasil di-upload" in (r.json().get("detail") or "").lower() or "r2" in (r.json().get("detail") or "").lower()


# -------- CORS preflight --------
class TestR2Cors:
    def test_options_preflight_on_presigned_put(self, super_tok):
        # Mint a fresh presigned URL
        init = requests.post(f"{BASE_URL}/api/royalty/admin/imports/initiate",
                             headers=H(super_tok),
                             json={"filename": "TEST_cors.csv", "rate_eur_idr": 17500, "period": "2024-03"},
                             timeout=15).json()
        url = init["presigned_put_url"]
        r = requests.options(url, headers={
            "Origin": FRONTEND_ORIGIN,
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "content-type",
        }, timeout=15)
        # R2 returns either 200 or 204 on preflight
        assert r.status_code in (200, 204), f"OPTIONS got {r.status_code}: {r.text[:200]}"
        allow_origin = r.headers.get("Access-Control-Allow-Origin", "")
        # Either '*' or contains our origin
        assert allow_origin == "*" or FRONTEND_ORIGIN in allow_origin, f"missing CORS allow-origin: {dict(r.headers)}"


# -------- Backward compat: small-file multipart still works --------
class TestSmallFileMultipart:
    def test_small_multipart_still_sync(self, super_tok):
        files = {"file": ("TEST_small_backcompat.csv", SMALL_CSV, "text/csv")}
        data = {"period": "2024-04", "rate_eur_idr": "17500", "note": "TEST_phase14_backcompat"}
        r = requests.post(f"{BASE_URL}/api/royalty/admin/imports",
                          headers=H(super_tok), files=files, data=data, timeout=30)
        assert r.status_code == 200, f"multipart failed: {r.status_code} {r.text}"
        body = r.json()
        # Small file → sync path → goes straight to pending_review
        assert body["status"] == "pending_review"
        assert body["total_lines"] == 2
