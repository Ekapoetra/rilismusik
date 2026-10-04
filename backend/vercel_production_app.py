"""Production FastAPI entrypoint on Vercel; business writes remain authorized
by the existing route dependencies, while long jobs use private Queues functions.
"""
import logging
import os
import time
from pathlib import Path
from tempfile import gettempdir

os.environ["RILISMUSIK_SERVERLESS_RUNTIME"] = "1"
os.environ["RILISMUSIK_DEPLOYMENT_MODE"] = "vercel-production"
os.environ["UPLOAD_DIR"] = str(Path(gettempdir()) / "rilismusik" / "uploads")

from fastapi import Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from server import app
from routes.deps import db, require_super_admin


@app.middleware("http")
async def production_timing(request: Request, call_next):
    started = time.perf_counter()
    from serverless_schedule import seed_schedule
    host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or "").split(",")[0].strip().lower()
    try:
        await seed_schedule(host)
    except Exception:
        logging.getLogger("rilismusik").exception("serverless schedule dispatch failed")
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    elapsed = (time.perf_counter() - started) * 1000
    response.headers["Server-Timing"] = f"app;dur={elapsed:.1f}"
    route = request.scope.get("route")
    logging.getLogger("rilismusik.performance").info(
        "api_timing route=%s status=%s duration_ms=%.1f",
        getattr(route, "path", "unmatched"), response.status_code, elapsed,
    )
    return response


@app.get("/api/admin/deployment-check")
async def deployment_check(user: dict = Depends(require_super_admin)):
    try:
        await db.command("ping")
        counts = {name: await db[name].estimated_document_count()
                  for name in ("users", "labels", "releases", "royalty_lines", "monthly_analytics")}
    except Exception:
        raise HTTPException(503, "Koneksi database belum berhasil.") from None
    return {"ok": True, "deployment_mode": "vercel-production", "database": db.name,
            "collections": counts, "background_jobs": "vercel-queues"}


@app.get("/api/runtime-health")
async def runtime_health(request: Request):
    """Public readiness reveals no account data or configuration secrets."""
    import hashlib
    from background_runtime import run_background, record_runtime_probe
    from routes.deps import db_bg
    import storage_service
    deployment = os.environ.get("VERCEL_DEPLOYMENT_ID", "local")
    try:
        await db.command("ping")
        if not storage_service.is_configured():
            raise RuntimeError("storage unavailable")
        task_id = hashlib.sha256(f"health:{deployment}".encode()).hexdigest()[:32]
        await run_background(record_runtime_probe, deployment=deployment, _dispatch_id=task_id)
        probe = await db_bg.serverless_probes.find_one({"_id": deployment}) or {}
        result = {"ok": probe.get("status") == "done", "database": "ready",
                "background_jobs": "ready" if probe.get("status") == "done" else "checking",
                "deployment_mode": "vercel-production"}
        if 'text/html' in request.headers.get('accept', ''):
            status = 'READY' if result['ok'] else 'CHECKING'
            return HTMLResponse(f'<!doctype html><html lang="en"><title>Rilis Musik Runtime Health</title>'
                f'<h1>Rilis Musik: {status}</h1><p>Database: ready</p>'
                f'<p>Background jobs: {result["background_jobs"]}</p></html>')
        return result
    except Exception as error:
        logging.getLogger("rilismusik").error("runtime readiness failed: %s", type(error).__name__)
        raise HTTPException(503, "Pemeriksaan sistem belum berhasil") from None
