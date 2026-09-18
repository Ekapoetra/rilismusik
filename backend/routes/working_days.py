"""Indonesian working-days calculation (excludes weekends + national holidays &
cuti bersama). Used by the Believe follow-up task threshold. Holiday list is per
SKB 3 Menteri 2026; extend the map for future years."""
from datetime import datetime, timezone, timedelta, date

# National holidays + cuti bersama (SKB 3 Menteri 2026). Both are non-working days.
_HOLIDAYS = {
    2026: {
        # National holidays
        "2026-01-01", "2026-01-16", "2026-02-17", "2026-03-19", "2026-03-21",
        "2026-03-22", "2026-04-03", "2026-04-05", "2026-05-01", "2026-05-14",
        "2026-05-27", "2026-05-31", "2026-06-01", "2026-06-16", "2026-08-17",
        "2026-08-25", "2026-12-25",
        # Cuti bersama
        "2026-02-16", "2026-03-18", "2026-03-20", "2026-03-23", "2026-03-24",
        "2026-05-15", "2026-05-28", "2026-12-24",
    },
}


def _wib_today() -> date:
    return (datetime.now(timezone.utc) + timedelta(hours=7)).date()


def is_working_day(d: date) -> bool:
    if d.weekday() >= 5:  # Sat/Sun
        return False
    return d.isoformat() not in _HOLIDAYS.get(d.year, set())


def _parse_date(value) -> date | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (dt + timedelta(hours=7)).date()  # to WIB calendar date


def working_days_elapsed(start_iso) -> int:
    """Count working days strictly AFTER the start date up to today (WIB)."""
    start = _parse_date(start_iso)
    if not start:
        return 0
    today = _wib_today()
    count = 0
    d = start + timedelta(days=1)
    while d <= today:
        if is_working_day(d):
            count += 1
        d += timedelta(days=1)
    return count
