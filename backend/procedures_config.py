"""System115 'procedures' area — published operational knobs (sync accessor).

The published document lives in the `system_settings` collection (area
"procedures"); `routes/system_settings.py` refreshes this cache on publish
and at startup. Code paths that cannot await (entitlements, withdraw
validation) read through `procedure()`. Before the first publish — or when
the cache has not been loaded yet — the defaults below apply, which are
identical to the previously hard-coded values.
"""

DEFAULTS = {
    "subscription_reminder_days": [30, 7, 3, 1],
    "contract_reminder_days": [30, 7, 1],
    "payment_pending_reminder_hours": [72, 24],
    "withdraw_min_idr": 1_000_000,
    "daily_release_limit": 7,
}

_CACHE = dict(DEFAULTS)
# Monotonic time of the last DB load. Each worker / serverless instance keeps
# its own cache, so it is refreshed on a short TTL (see server.py) — a publish
# on one instance otherwise never reaches the others until they restart.
_LOADED_AT = None
REFRESH_SECONDS = 60


def procedure(key):
    return _CACHE.get(key, DEFAULTS.get(key))


def is_stale(now=None):
    import time
    now = time.monotonic() if now is None else now
    return _LOADED_AT is None or now - _LOADED_AT >= REFRESH_SECONDS


def touch():
    """Back off after a failed refresh — retry after the TTL, not per request."""
    import time
    global _LOADED_AT
    _LOADED_AT = time.monotonic()


def set_published(values):
    import time
    global _LOADED_AT
    merged = dict(DEFAULTS)
    merged.update({k: v for k, v in (values or {}).items() if k in DEFAULTS})
    _CACHE.clear()
    _CACHE.update(merged)
    _LOADED_AT = time.monotonic()
