"""Vercel entrypoint for the migration preview, with legacy workers disabled.

Production cutover requires durable jobs and scheduled work to be migrated.
The ordinary server.py entrypoint retains its existing worker behavior.
"""
import os
from pathlib import Path
from tempfile import gettempdir

if os.environ.get("RILISMUSIK_DEPLOYMENT_MODE") != "preview":
    raise RuntimeError(
        "Deployment Vercel ini untuk pengujian migrasi. "
        "Isi RILISMUSIK_DEPLOYMENT_MODE=preview sebelum deploy."
    )

# Emergent's /app/backend/uploads is not a writable or durable Vercel volume.
# Durable covers/audio continue to be read from the existing R2 bucket.
os.environ["UPLOAD_DIR"] = str(Path(gettempdir()) / "rilismusik" / "uploads")
if not os.environ.get("FRONTEND_URL") and os.environ.get("VERCEL_URL"):
    os.environ["FRONTEND_URL"] = "https://" + os.environ["VERCEL_URL"]

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from server import app
from routes.deps import db, require_super_admin


_AUTH_WRITES = {
    "/api/auth/login", "/api/auth/logout", "/api/auth/refresh",
}


@app.middleware("http")
async def restrict_migration_preview(request: Request, call_next):
    path = request.url.path.rstrip("/")
    # Login/refresh still update sessions in the migrated database. Prevent
    # payments, emails, uploads and newly queued jobs during this preview.
    blocked_write = (
        request.method not in {"GET", "HEAD", "OPTIONS"}
        and path not in _AUTH_WRITES
    )
    blocked_maintenance = any(
        path == prefix or path.startswith(prefix + "/")
        for prefix in ("/api/cron", "/api/admin/cron", "/api/admin/migrate")
    )
    if blocked_write or blocked_maintenance:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Deployment ini untuk uji login dan pembacaan data. "
                "Pembayaran, perubahan data, unggahan, dan pekerjaan background "
                "belum diaktifkan pada deployment percobaan."
            },
        )
    return await call_next(request)


@app.get("/api/admin/deployment-check")
async def deployment_check(user: dict = Depends(require_super_admin)):
    """Confirm DB access after logging in, without exposing credentials."""
    try:
        await db.command("ping")
        counts = {
            name: await db[name].estimated_document_count()
            for name in ("users", "labels", "releases", "royalty_lines", "monthly_analytics")
        }
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Koneksi database gagal. Periksa MONGO_URL, DB_NAME dan akses jaringan Atlas.",
        ) from None
    return {
        "ok": True,
        "deployment_mode": "preview",
        "database": db.name,
        "collections": counts,
        "background_jobs": "disabled",
    }
