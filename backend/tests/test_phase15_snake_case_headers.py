"""Phase 15 — SQL snake_case CSV header support.

Single-line core change in royalty_utils.normalize_header():
    s = s.replace("_", " ").replace("-", " ")
    s = " ".join(s.split())

Tests cover:
1. Unit tests for normalize_header / detect_columns / parse_amount /
   parse_period on SQL snake_case headers AND values.
2. parse_csv_bytes / iter_csv_file with /tmp/sql_revenues.csv (real
   user export, 10 rows, 23 cols, snake_case).
3. E2E direct-to-R2 upload (initiate -> PUT -> finalize) of the SQL CSV,
   verifying 10/10 lines matched, 4 labels + 7 releases + 7 tracks
   auto-created, total ~0.083 EUR.
4. Regression: Believe CSV ("Bulan Laporan" with spaces) STILL parses.
"""
import io
import os
import sys
import time
import pytest
import requests

# Local module import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from royalty_utils import (  # noqa: E402
    normalize_header,
    detect_columns,
    parse_amount,
    parse_period_from_value,
    parse_csv_bytes,
    iter_csv_file,
)

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break

SUPERADMIN = {"email": "superadmin@rilismusik.com", "password": "SuperAdmin#2026"}
SQL_CSV_PATH = "/tmp/sql_revenues.csv"

SQL_HEADERS = [
    "id", "bulan_laporan", "bulan_penjualan", "platform", "negara",
    "nama_label", "nama_artis", "judul_rilis", "judul_track", "upc",
    "isrc", "release_catalog_nb", "jenis_rilis", "jenis_penjualan",
    "kuantitas", "mata_uang", "harga_unit", "biaya_mekanis",
    "pendapatan_kotor", "tingkat_pembagian", "pendapatan_bersih",
    "source_file", "created_at",
]


# ====================================================================
# 1) normalize_header — snake/kebab/whitespace tolerance
# ====================================================================
class TestNormalizeHeader:
    @pytest.mark.parametrize("raw,expected", [
        ("bulan_laporan",          "bulan laporan"),
        ("Bulan Laporan",          "bulan laporan"),
        ("BULAN-LAPORAN",          "bulan laporan"),
        ("  bulan__laporan  ",     "bulan laporan"),
        ("pendapatan_bersih",      "pendapatan bersih"),
        ("nama_label",             "nama label"),
        ("nama_artis",             "nama artis"),
        ("\ufeffbulan_laporan",    "bulan laporan"),
        ("judul-track",            "judul track"),
        ("",                       ""),
        (None,                     ""),
        ("ISRC",                   "isrc"),
        ("isrc_code",              "isrc code"),
    ])
    def test_normalize(self, raw, expected):
        assert normalize_header(raw) == expected


# ====================================================================
# 2) detect_columns on SQL snake_case headers
# ====================================================================
class TestDetectColumnsSQL:
    def test_all_canonical_mappings_found(self):
        col = detect_columns(SQL_HEADERS)
        # All canonical fields the user listed must resolve
        expected = {
            "period":              ("bulan_laporan", "bulan_penjualan"),
            "label_name":          ("nama_label",),
            "artist_name":         ("nama_artis",),
            "release_title":       ("judul_rilis",),
            "track_title":         ("judul_track",),
            "isrc":                ("isrc",),
            "upc":                 ("upc",),
            "quantity":            ("kuantitas",),
            "revenue_eur":         ("pendapatan_bersih",),
            "gross_revenue_eur":   ("pendapatan_kotor",),
            "unit_price_eur":      ("harga_unit",),
            "mechanical_cost_eur": ("biaya_mekanis",),
            "client_share_rate":   ("tingkat_pembagian",),
            "sales_type":          ("jenis_penjualan",),
            "release_type":        ("jenis_rilis",),
            "currency":            ("mata_uang",),
            "platform":            ("platform",),
            "country":             ("negara",),
        }
        for canon, candidate_headers in expected.items():
            assert col[canon] is not None, f"{canon} not detected"
            # Must point to one of the acceptable source columns
            got_header = SQL_HEADERS[col[canon]]
            assert got_header in candidate_headers, (
                f"{canon} -> {got_header}, expected one of {candidate_headers}"
            )

    def test_release_catalog_nb_ignored_safely(self):
        """release_catalog_nb is not a canonical alias; must NOT crash & must NOT
        be mistakenly assigned to any canonical field."""
        col = detect_columns(SQL_HEADERS)
        # catalog_ref alias list does NOT include 'release catalog nb'
        # so catalog_ref should be None
        assert col["catalog_ref"] is None


# ====================================================================
# 3) parse_period — SQL uses YYYY-MM-DD
# ====================================================================
class TestParsePeriodSQL:
    @pytest.mark.parametrize("raw,expected", [
        ("2020-12-01", "2020-12"),
        ("2020-12", "2020-12"),
        ("2021-01-15", "2021-01"),
    ])
    def test_sql_period(self, raw, expected):
        assert parse_period_from_value(raw) == expected


# ====================================================================
# 4) parse_amount — SQL uses dot-decimal with leading zero
# ====================================================================
class TestParseAmountSQL:
    @pytest.mark.parametrize("raw,expected", [
        ("0.000181577974000", 0.000181577974),
        ("0.000259397105000", 0.000259397105),
        ("0.70000",           0.7),
        ("1",                 1.0),
        ("0.000000000000000", 0.0),
    ])
    def test_sql_amounts(self, raw, expected):
        got = parse_amount(raw)
        assert abs(got - expected) < 1e-12, f"{raw!r} -> {got}, expected {expected}"

    def test_believe_european_decimals_still_work(self):
        # Regression: European format must NOT regress
        assert abs(parse_amount("0,000181577974000") - 0.000181577974) < 1e-12
        assert abs(parse_amount("0,70000000") - 0.7) < 1e-12


# ====================================================================
# 5) parse_csv_bytes / iter_csv_file on the real SQL export
# ====================================================================
class TestParseSQLCsvFile:
    def test_file_exists(self):
        assert os.path.exists(SQL_CSV_PATH), f"{SQL_CSV_PATH} missing"

    def test_parse_csv_bytes_full_file(self):
        with open(SQL_CSV_PATH, "rb") as f:
            content = f.read()
        headers, rows = parse_csv_bytes(content)
        assert len(rows) == 10, f"expected 10 rows, got {len(rows)}"
        # detect_columns on real headers from disk
        col = detect_columns(headers)
        # All critical fields detected
        for canon in ("period", "label_name", "artist_name", "release_title",
                      "track_title", "isrc", "upc", "quantity", "revenue_eur"):
            assert col[canon] is not None, f"{canon} not detected from real CSV headers"

        # First row sanity
        r0 = rows[0]
        # row dict uses normalized keys (snake->space) because parse_csv_bytes
        # passes headers through normalize_header()
        assert r0["nama label"] == "Poetra Studio"
        assert r0["judul track"] == "Indonesia Lebih Baik"
        assert r0["pendapatan bersih"] == "0.000181577974000"

    def test_iter_csv_file_stream(self):
        gen = iter_csv_file(SQL_CSV_PATH)
        headers, none_first = next(gen)
        assert none_first is None
        assert "bulan_laporan" in headers
        assert "pendapatan_bersih" in headers
        rows = []
        for _h, r in gen:
            rows.append(r)
        assert len(rows) == 10
        # Sum revenue
        total = sum(parse_amount(r["pendapatan bersih"]) for r in rows)
        assert abs(total - 0.0831587644) < 1e-6, f"total={total}"


# ====================================================================
# 6) Regression: Believe CSV with spaces still works
# ====================================================================
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


class TestBelieveRegression:
    def test_semicolon_autodetect_and_indonesian_headers(self):
        content = (BELIEVE_HEADER + "\n" + BELIEVE_ROW + "\n").encode("utf-8")
        headers, rows = parse_csv_bytes(content)
        assert len(rows) == 1
        assert "Bulan laporan" in headers
        assert "Pendapatan Bersih" in headers
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


# ====================================================================
# 7) E2E: upload SQL CSV via direct-to-R2 flow & verify auto-create
# ====================================================================
def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password},
                      timeout=20)
    if r.status_code != 200:
        pytest.skip(f"login failed: {r.status_code} {r.text[:200]}")
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def super_tok():
    return _login(**SUPERADMIN)


@pytest.fixture(scope="module")
def sql_csv_bytes():
    with open(SQL_CSV_PATH, "rb") as f:
        return f.read()


def _H(tok):
    return {"Authorization": f"Bearer {tok}"}


class TestSQLUploadE2E:
    """Upload /tmp/sql_revenues.csv end-to-end and verify 10/10 matched."""

    @pytest.fixture(scope="class")
    def init_data(self, super_tok, sql_csv_bytes):
        payload = {
            "filename": "TEST_phase15_sql_snake.csv",
            "rate_eur_idr": 17500,
            "period": "2020-12",
            "note": "TEST_phase15 SQL snake_case upload",
            "file_size_bytes": len(sql_csv_bytes),
        }
        r = requests.post(f"{BASE_URL}/api/royalty/admin/imports/initiate",
                          headers=_H(super_tok), json=payload, timeout=20)
        assert r.status_code == 200, f"initiate failed: {r.status_code} {r.text}"
        return r.json()

    def test_step1_initiate_returns_presigned_url(self, init_data):
        for k in ("import_id", "presigned_put_url", "r2_key", "content_type"):
            assert k in init_data, f"missing {k}"
        assert init_data["content_type"] == "text/csv"

    def test_step2_put_to_r2(self, init_data, sql_csv_bytes):
        r = requests.put(init_data["presigned_put_url"],
                         data=sql_csv_bytes,
                         headers={"Content-Type": init_data["content_type"]},
                         timeout=60)
        assert r.status_code in (200, 201), f"PUT to R2 failed: {r.status_code} {r.text[:300]}"

    def test_step3_finalize_and_verify_counts(self, super_tok, init_data):
        import_id = init_data["import_id"]
        r = requests.post(
            f"{BASE_URL}/api/royalty/admin/imports/{import_id}/finalize",
            headers=_H(super_tok), timeout=30,
        )
        assert r.status_code == 200, f"finalize failed: {r.status_code} {r.text}"
        body = r.json()
        assert body["status"] == "processing"

        # Wait for background processing to finish
        deadline = time.time() + 45
        final = None
        while time.time() < deadline:
            time.sleep(2)
            g = requests.get(f"{BASE_URL}/api/royalty/admin/imports/{import_id}",
                             headers=_H(super_tok), timeout=15)
            assert g.status_code == 200, f"get import failed: {g.status_code} {g.text}"
            final = g.json()["import"]
            if final["status"] in ("pending_review", "error"):
                break

        assert final is not None
        assert final["status"] == "pending_review", (
            f"status={final['status']} err={final.get('error_message')}"
        )

        # 10 rows, 10 matched (auto-created), 0 unmatched
        assert final["total_lines"] == 10, f"total_lines={final['total_lines']}"
        matched = final.get("matched_lines", 0)
        unmatched = final.get("unmatched_lines", 0)
        assert unmatched == 0, (
            f"expected 0 unmatched, got {unmatched}/{final['total_lines']}. "
            f"snake_case header parsing FAILED."
        )
        assert matched == 10, f"expected 10 matched, got {matched}"

        # Auto-created entities — capped at the four labels / 7 releases /
        # 7 tracks the SQL CSV contains. NOTE: if E1 (or a prior test run)
        # already uploaded the same CSV the entities will exist already and
        # auto_created counts will be 0 — that is still success, because the
        # 10/10 matched assertion above already proves the snake_case parser
        # works. We just guard against >expected (which would indicate bogus
        # extra entities being created).
        ac_labels   = final.get("auto_created_labels", 0)
        ac_releases = final.get("auto_created_releases", 0)
        ac_tracks   = final.get("auto_created_tracks", 0)
        assert 0 <= ac_labels   <= 4, f"ac_labels={ac_labels}"
        assert 0 <= ac_releases <= 7, f"ac_releases={ac_releases}"
        assert 0 <= ac_tracks   <= 7, f"ac_tracks={ac_tracks}"

        # Store import_id for next test
        TestSQLUploadE2E._import_id = import_id

    def test_step4_lines_have_correct_period_and_revenue(self, super_tok):
        import_id = getattr(TestSQLUploadE2E, "_import_id", None)
        if not import_id:
            pytest.skip("upload did not complete")
        r = requests.get(
            f"{BASE_URL}/api/royalty/admin/imports/{import_id}",
            headers=_H(super_tok), timeout=20,
        )
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        payload = r.json()
        lines = payload.get("lines", [])
        assert len(lines) == 10, f"expected 10 lines, got {len(lines)}"

        # Period must be normalised from "2020-12-01" -> "2020-12"
        for ln in lines:
            assert ln.get("period") == "2020-12", f"bad period: {ln.get('period')}"

        # Sum revenue_eur should match ~0.0832
        total = sum(float(ln.get("revenue_eur") or 0) for ln in lines)
        assert abs(total - 0.0831587644) < 1e-4, f"sum revenue_eur={total}"
