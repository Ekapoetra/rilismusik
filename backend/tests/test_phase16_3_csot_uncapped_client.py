"""Phase 16.3 — verify the CSOT-uncapped Mongo client (`db_bg`) is wired into
the royalty publish background task. Prevents future regressions where someone
swaps `db_bg` back to `db` and re-introduces the 10s read-timeout failure on
production Atlas (customer-apps-shard-00-01.fpzjgt.mongodb.net).

Reported by user 2026-06-29 after redeploy:
> Publish gagal: customer-apps-shard-00-01.fpzjgt.mongodb.net:27017:
> The read operation timed out (configured timeouts: timeoutMS: 10000.0ms,
> connectTimeoutMS: 20000.0ms)
"""
import os
from pathlib import Path

# Load backend .env so DB_NAME/MONGO_URL resolve under pytest
_env = Path(__file__).resolve().parents[1] / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def test_db_bg_client_has_no_csot_cap():
    """`client_bg` must have NO client-side operation timeout — long-running
    publish jobs on Atlas would otherwise be killed after ~10s.
    """
    from routes.deps import client_bg, db, db_bg
    opts = client_bg.options
    assert opts.timeout is None, f"client_bg.timeout must be None (got {opts.timeout!r}) — CSOT cap would kill 1M-row publish"
    assert opts.pool_options.socket_timeout is None, (
        f"client_bg socket_timeout must be None (got {opts.pool_options.socket_timeout!r})"
    )
    # Sanity: same DB name so reads see the same data
    assert db.name == db_bg.name


def test_publish_bg_uses_db_bg():
    """Static-source check: `_publish_bg` must NOT touch the foreground `db`
    client when iterating millions of `royalty_lines`. All aggregates, finds
    and update_manys inside the function body must reference `db_bg`.
    """
    src = (Path(__file__).resolve().parents[1] / "routes" / "royalty.py").read_text()
    # Slice the body of _publish_bg
    start = src.index("async def _publish_bg(")
    # find the next top-level `async def` / `def` / `@royalty_r.` after start
    rest = src[start + len("async def _publish_bg("):]
    # find end-of-function — the next "\n@" decorator or "\nasync def " / "\ndef "
    candidates = [rest.find("\n@"), rest.find("\nasync def "), rest.find("\ndef ")]
    end_rel = min(c for c in candidates if c > 0)
    body = rest[:end_rel]

    # The body MUST NOT contain `db.royalty_lines` (would hit CSOT)
    assert "db.royalty_lines" not in body, (
        "_publish_bg still uses foreground `db.royalty_lines` — must use `db_bg.royalty_lines` "
        "to avoid the production 10s CSOT timeout on Atlas."
    )
    # And it MUST reference db_bg.royalty_lines (sanity — confirms our fix landed)
    assert "db_bg.royalty_lines" in body, "_publish_bg must use db_bg.royalty_lines"


def test_admin_dashboard_uses_db_bg_for_revenue_aggregate():
    """`/api/admin/dashboard` aggregates revenue over the entire royalty_lines
    collection (millions of rows in production). It MUST route this single
    aggregate through `db_bg` to avoid 500s caused by CSOT timeout.

    Phase 16.4 update: the aggregate was refactored out of `admin_dashboard`
    into the `_recompute_revenue_cache()` helper (stale-while-revalidate
    cache). Either location is acceptable as long as the db_bg client is used.
    """
    routes_dir = Path(__file__).resolve().parents[1] / "routes"
    src = (routes_dir / "admin.py").read_text() + (routes_dir / "dashboard_cache.py").read_text()
    assert "db_bg.royalty_lines.aggregate" in src, (
        "admin.py must aggregate royalty_lines via db_bg (uncapped client) "
        "either inside admin_dashboard or in the dashboard revenue-cache helper."
    )


def test_admin_get_import_uses_db_bg_for_heavy_reads():
    """`/api/royalty/admin/imports/{id}` does a top-500 find + per-label
    aggregate over royalty_lines — both must use db_bg.
    """
    src = (Path(__file__).resolve().parents[1] / "routes" / "royalty.py").read_text()
    start = src.index("async def admin_get_import(")
    rest = src[start:]
    end_rel = min(c for c in [rest.find("\n@royalty_r."), rest.find("\nasync def admin_manually_match_line")] if c > 0)
    body = rest[:end_rel]
    assert "db_bg.royalty_lines.find" in body, "admin_get_import must read sample lines via db_bg"
    assert "db_bg.royalty_lines.aggregate" in body, "admin_get_import must run per-label aggregate via db_bg"


def test_mark_dana_received_uses_db_bg():
    """`/api/royalty/admin/imports/{id}/mark-dana-received` shifts millions of
    rows from pending→available and credits per-label balances. All heavy ops
    must use db_bg + chunked update_many.
    """
    src = (Path(__file__).resolve().parents[1] / "routes" / "royalty.py").read_text()
    start = src.index("async def admin_mark_dana_received(")
    rest = src[start:]
    end_rel = min(c for c in [rest.find("\n@royalty_r."), rest.find("\nasync def admin_reset_demo_royalty_data")] if c > 0)
    body = rest[:end_rel]
    assert "db_bg.royalty_lines.aggregate" in body
    assert "db_bg.royalty_lines.update_many" in body, "mark_dana_received must use chunked db_bg update_many"
    # And the old single huge update_many on `db` must be gone
    assert 'db.royalty_lines.update_many({"import_id": import_id, "status": "pending"}, {"$set": {"status": "available"}})' not in body
