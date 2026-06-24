"""Royalty CSV parsing, matching, and calculation helpers."""
import csv
import io
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple


# Common header variations from Believe / generic distributors
HEADER_ALIASES = {
    "isrc": ["isrc", "isrc code", "isrc_code"],
    "upc": ["upc", "ean", "upc_code", "upc/ean"],
    "track_title": ["track title", "track_title", "title", "song", "song title", "track"],
    "artist_name": ["artist", "artist name", "artist_name", "primary artist", "performer"],
    "release_title": ["release title", "release_title", "album", "album title", "release"],
    "platform": ["platform", "service", "dsp", "store", "shop"],
    "country": ["country", "territory", "country code", "iso country"],
    "period": ["period", "sales month", "sale_month", "reporting period", "month"],
    "quantity": ["quantity", "units", "streams", "stream count", "play count", "qty"],
    "revenue_eur": [
        "revenue", "net revenue", "net amount", "amount", "royalty amount",
        "amount eur", "amount (eur)", "revenue eur", "net amount eur",
        "amount_eur", "royalty (eur)", "net_amount", "net_eur",
        "net revenue eur", "net revenue (eur)", "revenue (eur)",
        "net revenue in eur", "earnings", "earnings eur", "earnings (eur)",
    ],
}


def normalize_header(h: str) -> str:
    return (h or "").strip().lower().replace("\ufeff", "")


def detect_columns(headers: List[str]) -> Dict[str, Optional[int]]:
    """Map our canonical names to column indices in the CSV header."""
    headers_norm = [normalize_header(h) for h in headers]
    out: Dict[str, Optional[int]] = {k: None for k in HEADER_ALIASES}
    for canon, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            if alias in headers_norm:
                out[canon] = headers_norm.index(alias)
                break
    return out


def parse_amount(value: str) -> float:
    if value is None:
        return 0.0
    s = str(value).strip().replace("\u00a0", "")
    if not s:
        return 0.0
    # Handle European decimal format (1.234,56) and US (1,234.56)
    s = s.replace(" ", "")
    if s.count(",") and s.count("."):
        # Both — assume last separator is decimal
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif s.count(",") and not s.count("."):
        # only commas — if 2 decimals after comma → decimal, else thousands
        parts = s.split(",")
        if len(parts[-1]) == 2:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    try:
        return float(s)
    except Exception:
        return 0.0


def parse_csv_bytes(content: bytes) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Return (headers, rows-as-dicts) parsed from CSV bytes.
    Detects delimiter (`,` or `;`) and handles UTF-8 BOM.
    """
    text = content.decode("utf-8-sig", errors="replace")
    # detect delimiter using csv.Sniffer
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except Exception:
        class _D:  # fallback
            delimiter = ","
            quotechar = '"'
        dialect = _D()
    reader = csv.reader(io.StringIO(text), delimiter=dialect.delimiter, quotechar=getattr(dialect, "quotechar", '"'))
    headers: List[str] = []
    rows: List[Dict[str, Any]] = []
    for i, row in enumerate(reader):
        if i == 0:
            headers = row
            continue
        if not any((c or "").strip() for c in row):
            continue
        rows.append({normalize_header(h): (row[j] if j < len(row) else "") for j, h in enumerate(headers)})
    return headers, rows


def calculate_line(
    revenue_eur: float,
    fee_percent: float,
    label_percent: float,
    exchange_rate: float,
) -> Dict[str, float]:
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
    """Pick label percentage from history that was effective at/before given period (YYYY-MM)."""
    # history is list of {percentage, effective_month, changed_at}
    if not history:
        return default_pct
    applicable = [h for h in history if (h.get("effective_month") or "") <= period]
    if not applicable:
        return default_pct
    applicable.sort(key=lambda h: (h.get("effective_month") or "", h.get("changed_at") or ""), reverse=True)
    return float(applicable[0]["percentage"])
