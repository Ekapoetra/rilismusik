"""Royalty CSV parsing, matching, and calculation helpers.

Supports BOTH:
- Real Believe CSV (Indonesian headers, semicolon delimited, European decimals)
- Generic distributor CSV (English headers, comma delimited)

Believe real-format example (21 columns):
  Bulan laporan;Bulan Penjualan;Platform;Negara;Nama Label;Nama Artis;
  Judul rilis;Judul track;UPC;ISRC;Referensi Katalog Rilis;
  Jenis Langganan Streaming;Jenis rilis;Jenis penjualan;Kuantias;
  Mata Uang Pembayaran Klien;Harga Unit;Biaya Mekanis;Pendapatan Kotor;
  Tingkat pembagian klien;Pendapatan Bersih

Sensitive fields (hidden from label/artist responses):
  Harga Unit, Biaya Mekanis, Pendapatan Kotor, Tingkat pembagian klien
"""
import csv
import io
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple


# Canonical key -> list of normalized aliases (lowercased, stripped).
HEADER_ALIASES: Dict[str, List[str]] = {
    "isrc": ["isrc", "isrc code", "isrc_code"],
    "upc": ["upc", "ean", "upc_code", "upc/ean"],
    "track_title": [
        "track title", "track_title", "title", "song", "song title", "track",
        "judul track", "judul lagu",
    ],
    "artist_name": [
        "artist", "artist name", "artist_name", "primary artist", "performer",
        "nama artis", "artist utama",
    ],
    "release_title": [
        "release title", "release_title", "album", "album title", "release",
        "judul rilis",
    ],
    "label_name": [
        "label", "label name", "nama label",
    ],
    "platform": [
        "platform", "service", "dsp", "store", "shop",
    ],
    "country": [
        "country", "territory", "country code", "iso country",
        "negara",
    ],
    "period": [
        "period", "sales month", "sale_month", "reporting period", "month",
        "bulan penjualan", "bulan laporan",
    ],
    "quantity": [
        "quantity", "units", "streams", "stream count", "play count", "qty",
        # Believe Indonesian header MISSPELLED in the real export.
        "kuantias", "kuantitas",
    ],
    # Net Revenue (the value label sees). On Believe = "Pendapatan Bersih".
    "revenue_eur": [
        "revenue", "net revenue", "net amount", "amount", "royalty amount",
        "amount eur", "amount (eur)", "revenue eur", "net amount eur",
        "amount_eur", "royalty (eur)", "net_amount", "net_eur",
        "net revenue eur", "net revenue (eur)", "revenue (eur)",
        "net revenue in eur", "earnings", "earnings eur", "earnings (eur)",
        "pendapatan bersih",
    ],
    # ===== Admin-only (hidden from label/artist API responses) =====
    "gross_revenue_eur": [
        "gross revenue", "pendapatan kotor", "gross", "gross amount",
    ],
    "unit_price_eur": [
        "unit price", "harga unit", "price per unit",
    ],
    "mechanical_cost_eur": [
        "mechanical cost", "biaya mekanis", "mechanical",
    ],
    "client_share_rate": [
        "client share rate", "tingkat pembagian klien", "share rate",
        "client share", "tingkat pembagian",
    ],
    # ===== Metadata (optional) =====
    "sales_type": ["sales type", "jenis penjualan", "transaction type"],
    "subscription_type": [
        "subscription type", "streaming subscription type",
        "jenis langganan streaming",
    ],
    "release_type": ["release type", "jenis rilis"],
    "currency": ["currency", "mata uang", "mata uang pembayaran klien"],
    "catalog_ref": ["catalog reference", "referensi katalog rilis"],
}

# Fields that must NEVER be sent in label / artist API responses.
SENSITIVE_FIELDS = (
    "gross_revenue_eur",
    "unit_price_eur",
    "mechanical_cost_eur",
    "client_share_rate",
)

# Internal EUR fields — labels work in Rupiah only. Stored for admin audit
# but stripped from label/artist responses (alongside SENSITIVE_FIELDS).
INTERNAL_EUR_FIELDS = (
    "revenue_eur",
    "fee_eur",
    "net_eur",
    "label_eur",
    "distributor_eur",
)

# Percentage / fee fields — must NEVER be exposed to label/artist. The royalty
# IDR amount shown to them is FINAL; they should not see the label-share split.
# NOTE: `fee_percent_applied` (5% distributor fee) is INTENTIONALLY shown for
# transparency per user requirement (2026-06-24): "fee 5% tetap diperlihatkan
# tidak masalah". Only the label-share percentage is hidden.
INTERNAL_PERCENT_FIELDS = (
    "label_percentage_applied",
    "distributor_idr",
    "exchange_rate",
)


def normalize_header(h: str) -> str:
    return (h or "").strip().lower().replace("\ufeff", "")


def detect_columns(headers: List[str]) -> Dict[str, Optional[int]]:
    """Map each canonical key to the index of the matching column in `headers`."""
    headers_norm = [normalize_header(h) for h in headers]
    out: Dict[str, Optional[int]] = {k: None for k in HEADER_ALIASES}
    for canon, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            if alias in headers_norm:
                out[canon] = headers_norm.index(alias)
                break
    return out


def parse_amount(value: Any) -> float:
    """Parse numeric value tolerating both US (1,234.56) and EU (1.234,56 / 0,00012345) formats."""
    if value is None:
        return 0.0
    s = str(value).strip().replace("\u00a0", "").replace(" ", "")
    if not s:
        return 0.0
    has_comma = "," in s
    has_dot = "." in s
    if has_comma and has_dot:
        # last separator is the decimal one
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")  # EU 1.234,56
        else:
            s = s.replace(",", "")                    # US 1,234.56
    elif has_comma:
        # Comma-only — Believe uses comma as decimal (e.g., 0,000407547753).
        # If there's exactly one comma and the integer side is short, treat as decimal.
        parts = s.split(",")
        if len(parts) == 2:
            s = parts[0].replace(".", "") + "." + parts[1]  # decimal
        else:
            s = s.replace(",", "")                          # 1,234,567 -> 1234567
    # dot-only or no separator: leave as-is
    try:
        return float(s)
    except Exception:
        return 0.0


def parse_period_from_value(value: Any) -> Optional[str]:
    """Convert various date strings to YYYY-MM. Accepts:
       - 2025/05/01, 2025-05-01, 2025-05, 2025/05, 05/2025, May 2025."""
    if not value:
        return None
    s = str(value).strip()
    for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%Y/%m", "%Y-%m", "%d/%m/%Y", "%m/%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m")
        except ValueError:
            continue
    # fallback: take first 7 chars if it looks like YYYY?MM
    if len(s) >= 7 and s[:4].isdigit():
        return f"{s[:4]}-{s[5:7]}"
    return None


def parse_csv_bytes(content: bytes) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Return (headers, rows-as-dicts) from CSV bytes.
    Auto-detects delimiter (`;`, `,`, `\\t`, `|`) and tolerates UTF-8 BOM / latin-1 fallback.

    NOTE: This loads the entire CSV into memory. For very large files (>10K rows),
    use `iter_csv_file()` instead which streams row-by-row from disk.
    """
    # Try utf-8 first then latin-1 fallback (Believe uses UTF-8 with BOM).
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1", errors="replace")

    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t|")
        delim = dialect.delimiter
        quote = dialect.quotechar or '"'
    except Exception:
        # heuristic: pick the most frequent delimiter in the first line
        first_line = sample.splitlines()[0] if sample else ""
        counts = {d: first_line.count(d) for d in (";", ",", "\t", "|")}
        delim = max(counts, key=counts.get) or ","
        quote = '"'

    reader = csv.reader(io.StringIO(text), delimiter=delim, quotechar=quote)
    headers: List[str] = []
    rows: List[Dict[str, Any]] = []
    for i, row in enumerate(reader):
        if i == 0:
            headers = row
            continue
        if not any((c or "").strip() for c in row):
            continue
        rows.append({
            normalize_header(h): (row[j] if j < len(row) else "")
            for j, h in enumerate(headers)
        })
    return headers, rows


def _open_csv_text(path: str):
    """Open a CSV file as a text stream with auto-detected encoding + gzip support.

    Returns (text_stream, sample_first_8KB).
    Supports plain .csv and .csv.gz (some Believe exports use gzip).
    """
    import gzip
    is_gz = path.endswith(".gz")
    # Read first 8 KB to sniff delimiter + decode
    if is_gz:
        with gzip.open(path, "rb") as f:
            raw_sample = f.read(8192)
    else:
        with open(path, "rb") as f:
            raw_sample = f.read(8192)
    try:
        sample_text = raw_sample.decode("utf-8-sig")
        encoding = "utf-8-sig"
    except UnicodeDecodeError:
        sample_text = raw_sample.decode("latin-1", errors="replace")
        encoding = "latin-1"
    # Open the real stream
    if is_gz:
        stream = gzip.open(path, "rt", encoding=encoding, errors="replace", newline="")
    else:
        stream = open(path, "rt", encoding=encoding, errors="replace", newline="")
    return stream, sample_text


def iter_csv_file(path: str):
    """Yield (headers, row_dict) one row at a time from a CSV file on disk.

    Memory-safe for files of any size (millions of rows). Supports .csv and .csv.gz.
    First yielded value is (headers, None) — caller should capture and discard.
    Subsequent yields are (headers, row_dict).
    """
    stream, sample = _open_csv_text(path)
    try:
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,\t|")
            delim = dialect.delimiter
            quote = dialect.quotechar or '"'
        except Exception:
            first_line = sample.splitlines()[0] if sample else ""
            counts = {d: first_line.count(d) for d in (";", ",", "\t", "|")}
            delim = max(counts, key=counts.get) or ","
            quote = '"'

        reader = csv.reader(stream, delimiter=delim, quotechar=quote)
        headers: List[str] = []
        for i, row in enumerate(reader):
            if i == 0:
                headers = row
                yield headers, None
                continue
            if not any((c or "").strip() for c in row):
                continue
            yield headers, {
                normalize_header(h): (row[j] if j < len(row) else "")
                for j, h in enumerate(headers)
            }
    finally:
        stream.close()


def calculate_line(
    revenue_eur: float,
    fee_percent: float,
    label_percent: float,
    exchange_rate: float,
) -> Dict[str, float]:
    """Apply distributor fee + label share + EUR→IDR conversion."""
    fee_eur = round(revenue_eur * (fee_percent / 100.0), 6)
    net_eur = round(revenue_eur - fee_eur, 6)
    label_eur = round(net_eur * (label_percent / 100.0), 6)
    distributor_eur = round(net_eur - label_eur, 6)
    label_idr = round(label_eur * exchange_rate)
    distributor_idr = round(distributor_eur * exchange_rate)
    revenue_idr = round(revenue_eur * exchange_rate)
    return {
        "fee_eur": fee_eur,
        "net_eur": net_eur,
        "label_eur": label_eur,
        "distributor_eur": distributor_eur,
        "label_idr": label_idr,
        "distributor_idr": distributor_idr,
        "revenue_idr": revenue_idr,
    }


def label_percentage_at(history: List[Dict[str, Any]], default_pct: float, period: str) -> float:
    """Pick the label royalty share effective at/before the given period (YYYY-MM)."""
    if not history:
        return default_pct
    applicable = [h for h in history if (h.get("effective_month") or "") <= period]
    if not applicable:
        return default_pct
    applicable.sort(
        key=lambda h: (h.get("effective_month") or "", h.get("changed_at") or ""),
        reverse=True,
    )
    return float(applicable[0]["percentage"])


def strip_sensitive(line: Dict[str, Any]) -> Dict[str, Any]:
    """Return a shallow copy of a royalty line with admin-only fields removed.
    Strips SENSITIVE_FIELDS + INTERNAL_EUR_FIELDS + INTERNAL_PERCENT_FIELDS —
    labels only see FINAL IDR amounts (no percentage breakdown, no EUR conversion).
    """
    hidden = SENSITIVE_FIELDS + INTERNAL_EUR_FIELDS + INTERNAL_PERCENT_FIELDS
    return {k: v for k, v in line.items() if k not in hidden}
