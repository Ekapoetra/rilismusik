"""
Phase 13 — DESTRUCTIVE: Reset Semua Data (POST /api/admin/admin/danger/reset-all-data)

⚠️  This test wipes the production DB. Run in PREVIEW only.
Tested:
  1) 401 without auth
  2) 403 with non-super-admin token (admin_finance)
  3) 400 with wrong confirm string
  4) Setup test data (register label, create release draft, upload CSV royalty, upload R2 image)
  5) 200 with super_admin + confirm=RESET-ALL-DATA + delete_r2_files=true → report has non-zero deletions
  6) Post-reset assertions:
       - GET /api/admin/labels  → empty
       - GET /api/royalty/admin/imports → empty
       - Created test-label login → 401 (deleted)
       - Super admin login still works
       - GET /api/cms/landing still returns valid CMS data
  7) Idempotent re-run → 200 with mostly zeros
"""
import os
import time
import io
import pytest
import requests
from tests.support_config import FINANCE, SUPERADMIN, temporary_password

def _read_frontend_env_url():
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip()
    except Exception:
        return ""
    return ""

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _read_frontend_env_url()).rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"

SUPER_EMAIL = SUPERADMIN["email"]
SUPER_PASS = SUPERADMIN["password"]

# A sub-admin for the 403 test (admin_finance has no super_admin role)
FINANCE_EMAIL = FINANCE["email"]
FINANCE_PASS = FINANCE["password"]

ENDPOINT = f"{BASE_URL}/api/admin/admin/danger/reset-all-data"


def _login(email: str, password: str) -> str | None:
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    if r.status_code != 200:
        return None
    return r.json().get("access_token") or r.json().get("token")


@pytest.fixture(scope="module")
def super_token():
    tok = _login(SUPER_EMAIL, SUPER_PASS)
    if not tok:
        pytest.skip("Super admin login failed — cannot run destructive test")
    return tok


@pytest.fixture(scope="module")
def finance_token():
    tok = _login(FINANCE_EMAIL, FINANCE_PASS)
    if not tok:
        pytest.skip("admin_finance login failed — sub-admin seed missing")
    return tok


def _hdr(tok: str):
    return {"Authorization": f"Bearer {tok}"}


# ---------------------------------------------------------------------------
# Phase A: RBAC + validation (BEFORE we mutate anything)
# ---------------------------------------------------------------------------
class TestRBAC:
    def test_a1_no_auth_returns_401(self):
        r = requests.post(ENDPOINT, data={"confirm": "RESET-ALL-DATA"}, timeout=30)
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code} body={r.text[:200]}"

    def test_a2_non_super_admin_returns_403(self, finance_token):
        r = requests.post(
            ENDPOINT,
            data={"confirm": "RESET-ALL-DATA", "delete_r2_files": "false"},
            headers=_hdr(finance_token),
            timeout=30,
        )
        assert r.status_code == 403, f"expected 403, got {r.status_code} body={r.text[:300]}"

    def test_a3_wrong_confirm_returns_400(self, super_token):
        r = requests.post(
            ENDPOINT,
            data={"confirm": "WRONG", "delete_r2_files": "false"},
            headers=_hdr(super_token),
            timeout=30,
        )
        assert r.status_code == 400
        body = r.json()
        assert "RESET-ALL-DATA" in str(body.get("detail", "")), body


# ---------------------------------------------------------------------------
# Phase B: seed test data, then DESTROY, then verify clean slate
# ---------------------------------------------------------------------------
TEST_LABEL_EMAIL = f"TEST_reset_{int(time.time())}@example.com"
TEST_LABEL_PASS = temporary_password("phase13-reset")

state = {}  # shared across tests in this module


class TestSeedThenReset:
    def test_b1_seed_label_account(self):
        """Register a fresh label → must succeed and create a labels row."""
        r = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "label_name": "TEST Reset Label",
                "pic_name": "Tester",
                "email": TEST_LABEL_EMAIL,
                "whatsapp": "+628111111111",
                "password": TEST_LABEL_PASS,
                "account_type": "label",
                "mda_accepted": True,
            },
            timeout=60,
        )
        assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text[:300]}"

    def test_b2_seed_release_draft(self):
        tok = _login(TEST_LABEL_EMAIL, TEST_LABEL_PASS)
        assert tok, "test label login failed right after register"
        state["label_token"] = tok
        r = requests.post(
            f"{BASE_URL}/api/releases/draft",
            json={
                "release_title": "TEST Reset Release",
                "release_type": "single",
                "artist_name": "Tester Artist",
                "release_date": "2026-12-01",
                "genre": "Pop",
                "language": "Indonesian",
                "platforms": ["spotify"],
                "tracks": [],
            },
            headers=_hdr(tok),
            timeout=30,
        )
        # release draft endpoint may return 200 or 201 — both fine
        assert r.status_code in (200, 201), f"release draft failed: {r.status_code} {r.text[:300]}"

    def test_b3_seed_royalty_csv(self, super_token):
        csv_bytes = (
            b"ISRC,Track Title,Artist,Label,Platform,Country,Bulan Laporan,Quantity,Pendapatan Bersih\n"
            b"IDA0X2200001,TEST Track,Tester Artist,TEST Reset Label,Spotify,ID,2026-01,123,0.50\n"
            b"IDA0X2200002,TEST Track 2,Tester Artist,TEST Reset Label,YouTube,ID,2026-01,200,0.75\n"
        )
        files = {"file": ("test_reset.csv", csv_bytes, "text/csv")}
        data = {"rate_eur_idr": "17000", "note": "TEST reset seed"}
        r = requests.post(
            f"{BASE_URL}/api/royalty/admin/imports",
            files=files,
            data=data,
            headers=_hdr(super_token),
            timeout=60,
        )
        assert r.status_code in (200, 201), f"royalty import failed: {r.status_code} {r.text[:400]}"

    def test_b4_seed_r2_file(self, super_token):
        """Upload a small file to R2 via CMS landing-image upload (no Pillow check)."""
        # 1x1 PNG bytes
        png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0"
            b"\x00\x00\x00\x03\x00\x01\x5c\xcd\xff\x69\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        files = {"file": ("seed.png", png, "image/png")}
        r = requests.post(
            f"{BASE_URL}/api/cms/landing/upload-image",
            files=files,
            headers=_hdr(super_token),
            timeout=60,
        )
        # If R2 not configured the endpoint may 500/400. We tolerate non-200 here but log it.
        if r.status_code not in (200, 201):
            print(f"[warn] R2 seed upload returned {r.status_code}: {r.text[:200]}")
        state["r2_seeded"] = r.status_code in (200, 201)

    # ---------- DESTROY ----------
    @staticmethod
    def _run_reset(super_token, delete_r2: str):
        """Phase 29.1: reset is now an async background job — poll until done."""
        r = requests.post(
            ENDPOINT,
            data={"confirm": "RESET-ALL-DATA", "delete_r2_files": delete_r2},
            headers=_hdr(super_token),
            timeout=60,
        )
        assert r.status_code == 200, f"reset failed: {r.status_code} {r.text[:500]}"
        body = r.json()
        assert body.get("ok") is True
        job_id = body.get("job_id")
        assert job_id, f"expected job_id in response, got {body}"
        deadline = time.time() + 300
        while time.time() < deadline:
            jr = requests.get(f"{BASE_URL}/api/admin/migrate/jobs/{job_id}", headers=_hdr(super_token), timeout=30)
            assert jr.status_code == 200, jr.text[:200]
            job = jr.json()
            if job.get("status") == "done":
                return job.get("result") or {}
            if job.get("status") == "error":
                raise AssertionError(f"reset job errored: {job.get('error_message')}")
            time.sleep(2)
        raise AssertionError("reset job did not finish within 300s")

    def test_c1_reset_success(self, super_token):
        rep = self._run_reset(super_token, "true")
        state["first_report"] = rep
        print("[reset report]", rep)

        # Must show non-zero deletions for the rows we created.
        # NOTE: collection counts use estimated_document_count (metadata-based,
        # can lag a checkpoint) — assert on the reliably-counted fields only.
        assert rep.get("users_deleted_non_admin", 0) >= 1, f"expected >=1 user deleted, got {rep}"
        assert "labels" in rep and "royalty_lines" in rep, f"report missing collection keys: {rep}"
        # Reseed must succeed
        assert rep.get("reseed") == "ok", f"reseed failed: {rep}"
        # R2 deletion: only assert if we successfully seeded
        if state.get("r2_seeded"):
            assert rep.get("r2_objects_deleted", 0) >= 1, f"expected R2 objects deleted, got {rep}"

    # ---------- VERIFY CLEAN STATE ----------
    def test_c2_labels_empty(self, super_token):
        r = requests.get(f"{BASE_URL}/api/admin/labels", headers=_hdr(super_token), timeout=30)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        assert len(items) == 0, f"labels should be empty post-reset, got {len(items)} items"

    def test_c3_royalty_imports_empty(self, super_token):
        r = requests.get(f"{BASE_URL}/api/royalty/admin/imports", headers=_hdr(super_token), timeout=30)
        assert r.status_code == 200
        items = r.json()
        # Either an array or {items: [...]}
        if isinstance(items, dict):
            items = items.get("items") or items.get("imports") or []
        assert len(items) == 0, f"royalty imports should be empty, got {items}"

    def test_c4_test_label_cannot_login(self):
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_LABEL_EMAIL, "password": TEST_LABEL_PASS},
            timeout=30,
        )
        assert r.status_code in (401, 403, 404), f"deleted user should not login, got {r.status_code} {r.text[:200]}"

    def test_c5_super_admin_login_still_works(self):
        tok = _login(SUPER_EMAIL, SUPER_PASS)
        assert tok, "Super admin login broken after reset — CRITICAL"

    def test_c6_cms_landing_still_works(self):
        r = requests.get(f"{BASE_URL}/api/cms/landing", timeout=30)
        assert r.status_code == 200, f"CMS landing broken: {r.status_code} {r.text[:200]}"
        data = r.json()
        assert isinstance(data, dict)
        # CMS landing should still have at least some keys preserved (legal_entity, pricing, etc.)
        assert len(data.keys()) >= 1, f"CMS appears wiped: {data}"

    # ---------- IDEMPOTENT ----------
    def test_d1_reset_idempotent(self, super_token):
        rep = self._run_reset(super_token, "false")
        # All non-admin user delete counts should be 0 now
        assert rep.get("users_deleted_non_admin", 0) == 0, f"expected 0 users on re-run, got {rep}"
        assert rep.get("labels", 0) == 0
        assert rep.get("royalty_imports", 0) == 0
        assert rep.get("reseed") == "ok"
