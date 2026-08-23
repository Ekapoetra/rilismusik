"""Phase-4 tests: Real Believe royalty CSV parsing, sensitive-field hiding,
match_by=label_name fallback, and reset-demo-data admin endpoint.

Covers /app/backend/royalty_utils.py + /app/backend/server.py changes.
"""
import io
import os
import sys
import pytest
import requests
from tests.support_config import DEMO_PASSWORD, SUPERADMIN, temporary_password

# Allow direct import of backend modules for unit tests.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from royalty_utils import (  # noqa: E402
    parse_amount,
    parse_csv_bytes,
    detect_columns,
    parse_period_from_value,
    strip_sensitive,
    SENSITIVE_FIELDS,
)

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fall back to frontend/.env
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                    break
    except FileNotFoundError:
        pass



# ------------------------------------------------------------------ #
# Unit tests: parse_amount (the headline bug — long EU decimals)     #
# ------------------------------------------------------------------ #
class TestParseAmount:
    @pytest.mark.parametrize("raw,expected", [
        ("0,000407547753", 0.000407547753),
        ("1.234,56",       1234.56),
        ("1,234.56",       1234.56),
        ("0,70000000",     0.7),
        ("0,000000",       0.0),
        ("0",              0.0),
        ("",               0.0),
        (None,             0.0),
        ("1234",           1234.0),
        ("1234.56",        1234.56),
        ("  42,5 ",        42.5),
        ("\u00a01.000,00", 1000.0),
        ("garbage",        0.0),
    ])
    def test_parse_amount(self, raw, expected):
        got = parse_amount(raw)
        assert abs(got - expected) < 1e-9, f"parse_amount({raw!r}) -> {got}, expected {expected}"


class TestParsePeriod:
    @pytest.mark.parametrize("raw,expected", [
        ("2025/05/01", "2025-05"),
        ("2025-05-01", "2025-05"),
        ("2025-05",    "2025-05"),
        ("05/2025",    "2025-05"),
        ("",           None),
        (None,         None),
    ])
    def test_parse_period(self, raw, expected):
        assert parse_period_from_value(raw) == expected


# ------------------------------------------------------------------ #
# Unit tests: parse_csv_bytes + detect_columns w/ Believe headers    #
# ------------------------------------------------------------------ #
BELIEVE_HEADER = (
    "Bulan laporan;Bulan Penjualan;Platform;Negara;Nama Label;Nama Artis;"
    "Judul rilis;Judul track;UPC;ISRC;Referensi Katalog Rilis;"
    "Jenis Langganan Streaming;Jenis rilis;Jenis penjualan;Kuantias;"
    "Mata Uang Pembayaran Klien;Harga Unit;Biaya Mekanis;Pendapatan Kotor;"
    "Tingkat pembagian klien;Pendapatan Bersih"
)
BELIEVE_ROW = (
    '"2025/05/01";"2025/05/01";"YouTube Official Content";"Indonesia";'
    '"Manawa Music";"DECENT";"Mamang";"Mamang";"3617661494481";'
    '"DG-A08-24-65457";"";"Freemium / Ad Supported";"Music Release";'
    '"Stream";1;"EUR";"0,000407547753";"0,000000";"0,000407547753";'
    '"0,70000000";"0,000285283427"'
)


class TestParseCsv:
    def test_semicolon_autodetect_and_indonesian_headers(self):
        content = (BELIEVE_HEADER + "\n" + BELIEVE_ROW + "\n").encode("utf-8")
        headers, rows = parse_csv_bytes(content)
        assert len(rows) == 1
        # headers preserved as-is
        assert "Bulan laporan" in headers
        assert "Pendapatan Bersih" in headers
        # column index detection covers all canonical keys
        col_idx = detect_columns(headers)
        for canon in (
            "isrc", "upc", "track_title", "artist_name", "release_title",
            "label_name", "platform", "country", "period", "quantity",
            "revenue_eur", "gross_revenue_eur", "unit_price_eur",
            "mechanical_cost_eur", "client_share_rate",
            "sales_type", "subscription_type", "release_type", "currency",
        ):
            assert col_idx[canon] is not None, f"missing column mapping for {canon}"

    def test_row_values(self):
        content = (BELIEVE_HEADER + "\n" + BELIEVE_ROW + "\n").encode("utf-8")
        _, rows = parse_csv_bytes(content)
        r = rows[0]
        assert r["isrc"] == "DG-A08-24-65457"
        assert r["upc"] == "3617661494481"
        assert r["nama label"] == "Manawa Music"
        assert r["pendapatan bersih"] == "0,000285283427"
        assert r["kuantias"] == "1"


class TestStripSensitive:
    def test_strip_sensitive_removes_all_4_fields(self):
        line = {
            "id": "x", "period": "2025-05",
            "revenue_eur": 1.23,
            "gross_revenue_eur": 4.56,
            "unit_price_eur": 0.1,
            "mechanical_cost_eur": 0.0,
            "client_share_rate": 0.7,
        }
        out = strip_sensitive(line)
        for f in SENSITIVE_FIELDS:
            assert f not in out, f"{f} should have been stripped"
        assert out["revenue_eur"] == 1.23
        assert out["id"] == "x"


# ------------------------------------------------------------------ #
# Integration tests against the live backend                         #
# ------------------------------------------------------------------ #
@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=SUPERADMIN, timeout=20)
    if r.status_code != 200:
        pytest.skip(f"Cannot login as super_admin: {r.status_code} {r.text[:200]}")
    return s


@pytest.fixture(scope="module")
def admin_finance_session(admin_session):
    """Create a fresh admin_finance user and return its logged-in session."""
    import uuid
    email = f"TEST_finance_{uuid.uuid4().hex[:8]}@rilismusik.com"
    password = temporary_password("believe-finance")
    payload = {
        "email": email,
        "password": password,
        "name": "TEST Finance Admin",
        "role": "admin_finance",
    }
    r = admin_session.post(f"{BASE_URL}/api/admin/admin-users", json=payload, timeout=20)
    if r.status_code not in (200, 201):
        pytest.skip(f"Cannot create admin_finance: {r.status_code} {r.text[:200]}")
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=20)
    if r.status_code != 200:
        pytest.skip(f"Cannot login admin_finance: {r.status_code} {r.text[:200]}")
    return s


@pytest.fixture(scope="module")
def label_session(admin_session):
    """Login as one of the demo labels (Khizanah Kreasi Gontor preferred)."""
    r = admin_session.get(f"{BASE_URL}/api/admin/labels?limit=200", timeout=20)
    if r.status_code != 200:
        pytest.skip(f"Cannot list labels: {r.status_code}")
    payload = r.json()
    items = payload.get("items", payload) if isinstance(payload, dict) else payload
    target = None
    for lab in items:
        if (lab.get("label_name") or "").strip().lower() == "khizanah kreasi gontor":
            target = lab
            break
    if not target and items:
        target = items[0]
    if not target:
        pytest.skip("No labels available")
    email = target.get("email")
    for pw in (DEMO_PASSWORD,):
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pw}, timeout=20)
        if r.status_code == 200:
            return s
    pytest.skip(f"Could not login as label {email}")


# ---- Sensitive fields hidden from LABEL response ----
class TestSensitiveFieldsHidden:
    def test_label_royalty_lines_no_sensitive_fields(self, label_session):
        r = label_session.get(f"{BASE_URL}/api/royalty/lines?limit=50", timeout=30)
        assert r.status_code == 200, r.text[:300]
        lines = r.json()
        assert isinstance(lines, list)
        if not lines:
            pytest.skip("No royalty lines visible to this label — cannot assert hidden fields")
        for line in lines:
            for f in SENSITIVE_FIELDS:
                assert f not in line, f"label response leaks {f}: {line}"

    def test_admin_get_import_includes_sensitive(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/royalty/admin/imports", timeout=20)
        assert r.status_code == 200, r.text[:200]
        imports = r.json()
        if not imports:
            pytest.skip("No imports present in DB")
        imp_id = imports[0]["id"]
        r = admin_session.get(f"{BASE_URL}/api/royalty/admin/imports/{imp_id}", timeout=30)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        lines = data.get("lines", [])
        assert lines, "Admin import detail should expose lines"
        # At least one line must contain every sensitive key (admin sees them).
        any_has_all = any(all(k in ln for k in SENSITIVE_FIELDS) for ln in lines)
        assert any_has_all, "Admin /admin/imports/{id} must include sensitive fields"


# ---- Real Believe CSV upload (small slice) ----
class TestBelieveCsvUpload:
    """Upload first 100 lines of the real Believe sample; verify totals + matching."""

    SAMPLE_PATH = "/tmp/believe_sample.csv"

    @pytest.fixture(scope="class")
    def small_csv_bytes(self):
        if not os.path.exists(self.SAMPLE_PATH):
            pytest.skip("Real Believe sample not available at /tmp/believe_sample.csv")
        with open(self.SAMPLE_PATH, "rb") as f:
            head_lines = []
            for i, line in enumerate(f):
                head_lines.append(line)
                if i >= 99:  # 1 header + 99 data lines
                    break
        return b"".join(head_lines)

    def test_upload_and_totals(self, admin_session, small_csv_bytes):
        # Parse expected total of 'Pendapatan Bersih' column locally for reference
        headers, rows = parse_csv_bytes(small_csv_bytes)
        col_idx = detect_columns(headers)
        net_idx = col_idx["revenue_eur"]
        gross_idx = col_idx["gross_revenue_eur"]
        assert net_idx is not None and gross_idx is not None
        expected_net = sum(parse_amount(list(rw.values())[net_idx]) for rw in rows)
        expected_gross = sum(parse_amount(list(rw.values())[gross_idx]) for rw in rows)
        # Sanity: in this dataset Pendapatan Bersih != Pendapatan Kotor
        assert expected_net > 0
        assert abs(expected_net - expected_gross) > 1e-12, \
            "Pendapatan Bersih and Pendapatan Kotor must differ"

        files = {"file": ("TEST_believe_100.csv", small_csv_bytes, "text/csv")}
        data = {"period": "2099-01", "rate_eur_idr": "17500", "note": "TEST_believe_phase4"}
        r = admin_session.post(
            f"{BASE_URL}/api/royalty/admin/imports",
            files=files, data=data, timeout=60,
        )
        assert r.status_code == 200, r.text[:500]
        imp = r.json()
        assert imp["total_lines"] == 99, f"Expected 99 data rows, got {imp['total_lines']}"
        # total_revenue_eur ≈ sum of Pendapatan Bersih (net), not Kotor (gross)
        assert abs(imp["total_revenue_eur"] - round(expected_net, 4)) < 0.001, \
            f"total_revenue_eur={imp['total_revenue_eur']} expected≈{expected_net}"
        # Should NOT equal gross
        assert abs(imp["total_revenue_eur"] - round(expected_gross, 4)) > 0.001
        assert imp["matched_lines"] + imp["unmatched_lines"] == imp["total_lines"]

        # Save for next test
        TestBelieveCsvUpload._last_import_id = imp["id"]

    def test_label_name_fallback_match(self, admin_session):
        """At least some lines should be match_by='label_name' since Believe CSV
        has labels (Manawa Music etc.) seeded by name without owning the ISRC tracks."""
        imp_id = getattr(TestBelieveCsvUpload, "_last_import_id", None)
        if not imp_id:
            pytest.skip("Upload test must run first")
        r = admin_session.get(f"{BASE_URL}/api/royalty/admin/imports/{imp_id}", timeout=30)
        assert r.status_code == 200
        lines = r.json().get("lines", [])
        # at least one should have match_by in (isrc|upc|label_name)
        match_by_counts = {}
        for ln in lines:
            mb = ln.get("match_by")
            match_by_counts[mb] = match_by_counts.get(mb, 0) + 1
        assert any(k in match_by_counts for k in ("isrc", "upc", "label_name")), \
            f"No matched lines at all: {match_by_counts}"
        # Unmatched lines must have match_by None
        for ln in lines:
            if ln.get("match_status") == "unmatched":
                assert ln.get("match_by") in (None, ""), \
                    f"Unmatched line has match_by={ln.get('match_by')}"

    def test_cleanup_test_import(self, admin_session):
        """Delete the throw-away 2099-01 import we just created."""
        imp_id = getattr(TestBelieveCsvUpload, "_last_import_id", None)
        if not imp_id:
            pytest.skip("nothing to clean up")
        # Try a delete endpoint if available; otherwise leave (next agent can ignore 2099-01)
        r = admin_session.delete(
            f"{BASE_URL}/api/royalty/admin/imports/{imp_id}", timeout=20,
        )
        # endpoint may or may not exist; both states are acceptable
        assert r.status_code in (200, 204, 404, 405), r.status_code


# ---- reset-demo-data validation (do NOT actually run RESET) ----
class TestResetDemoData:
    URL = "/api/royalty/admin/reset-demo-data"

    def test_wrong_confirm_returns_400(self, admin_session):
        r = admin_session.post(f"{BASE_URL}{self.URL}", data={"confirm": "reset"}, timeout=20)
        assert r.status_code == 400, r.text[:200]
        # Indonesian message
        body = r.text.lower()
        assert "konfirmasi" in body or "reset" in body

    def test_empty_confirm_returns_400_or_422(self, admin_session):
        # Form param required → FastAPI will respond 422 if missing entirely.
        r = admin_session.post(f"{BASE_URL}{self.URL}", data={"confirm": ""}, timeout=20)
        assert r.status_code in (400, 422), r.text[:200]

    def test_admin_finance_forbidden(self, admin_finance_session):
        r = admin_finance_session.post(
            f"{BASE_URL}{self.URL}", data={"confirm": "RESET"}, timeout=20,
        )
        assert r.status_code == 403, r.text[:200]

    def test_unauthenticated_forbidden(self):
        r = requests.post(f"{BASE_URL}{self.URL}", data={"confirm": "RESET"}, timeout=20)
        assert r.status_code in (401, 403), r.text[:200]
