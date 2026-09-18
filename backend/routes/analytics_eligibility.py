"""Canonical eligibility predicate for Royalty Analytics.

Single source of truth so the materialized cache recompute, the live/filtered
admin aggregate, and the revenue rollups all count EXACTLY the same lines.
Business rules (confirmed with product owner):
  - match_status ∈ {matched, manually_matched}   → reliable label/track FK
  - line status ∈ {pending, available, withdrawn} → published onward (excludes draft)
  - replacement_stage ≠ true                      → excludes staged-replacement previews
Period is always the reporting month (`royalty_lines.period` ← CSV "Bulan laporan").
"""
from typing import Any, Dict, Optional

ANALYTICS_MATCH_STATUSES = ["matched", "manually_matched"]
# published lifecycle: draft(imported) → pending(published) → available(dana diterima) → withdrawn(paid)
ANALYTICS_LINE_STATUSES = ["pending", "available", "withdrawn"]


def analytics_eligible_filter(extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return the canonical `$match` filter. `extra` overrides/extends keys."""
    f: Dict[str, Any] = {
        "match_status": {"$in": ANALYTICS_MATCH_STATUSES},
        "status": {"$in": ANALYTICS_LINE_STATUSES},
        "replacement_stage": {"$ne": True},
        "period": {"$ne": None, "$exists": True},
    }
    if extra:
        f.update(extra)
    return f
