"""RILIS MUSIK — backend API.

This file is the slim entry-point. All business routes live in
/app/backend/routes/. Each domain is its own module that exports
a router object (e.g. `routes.auth.auth`, `routes.labels.label_r`).
"""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import logging
from urllib.parse import urlsplit, urlunsplit
from fastapi import FastAPI, APIRouter
from fastapi.responses import FileResponse, RedirectResponse
from starlette.middleware.cors import CORSMiddleware

# Configure root logger BEFORE importing the route modules so they
# inherit the formatting.
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("rilismusik")

from models import now_iso
from routes.deps import UPLOAD_DIR, client
from routes.auth import auth
from routes.labels import label_r
from routes.releases import release_r
from routes.artists import artist_r
from routes.payments import pay_r
from routes.wami import wami_r
from routes.cms import cms_r
from routes.admin import admin_r
from routes.label_rate_import import rate_import_r, resume_label_rate_jobs
from routes.balance_audit import balance_audit_r, resume_balance_audit_jobs
from routes.label_analytics import label_analytics_r
from routes.admin_analytics import analytics_r, recompute_monthly_analytics
from routes.royalty import royalty_r, resume_interrupted_imports
from routes.withdraw import withdraw_r
from routes.tickets import ticket_r
from routes.notifications import notif_r
from routes.contracts import contract_r
from routes.migrate import migrate_r
from routes.cron_jobs import cron_r, start_scheduler, stop_scheduler
from routes.seed import seed_indexes_and_admins
import storage_service


app = FastAPI(title="RILIS MUSIK API", version="0.1.0")


def expand_origin_variants(origins: list[str]) -> list[str]:
    """Allow both apex and www aliases for a configured custom domain."""
    expanded: list[str] = []
    for raw_origin in origins:
        origin = raw_origin.strip().rstrip("/")
        if not origin:
            continue
        if origin not in expanded:
            expanded.append(origin)
        parsed = urlsplit(origin)
        host = parsed.hostname or ""
        base_host = host[4:] if host.startswith("www.") else host
        if base_host.count(".") != 1:
            continue
        alternate_host = base_host if host.startswith("www.") else f"www.{base_host}"
        port = f":{parsed.port}" if parsed.port else ""
        alternate = urlunsplit((parsed.scheme, f"{alternate_host}{port}", "", "", ""))
        if alternate not in expanded:
            expanded.append(alternate)
    return expanded


# Hybrid file serving: try R2 (presigned redirect) first, fall back to local disk
# for legacy files uploaded before the R2 migration.
@app.get("/api/files/{path:path}")
async def serve_file(path: str):
    from fastapi import HTTPException
    # 1) Try R2
    if storage_service.is_configured():
        try:
            meta = await storage_service.head_object(key=path)
            if meta:
                ttl = 3600 * 24 * 7 if path.startswith(("cover/", "landing/")) else 3600
                url = await storage_service.generate_presigned_url(key=path, ttl=ttl)
                return RedirectResponse(url=url, status_code=302)
        except Exception as e:
            logger.warning("[FILES] R2 lookup failed for %s: %s", path, e)
    # 2) Fallback: serve from local disk (legacy / dev)
    local_path = (UPLOAD_DIR / path).resolve()
    if not str(local_path).startswith(str(UPLOAD_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Invalid file path")
    if local_path.exists():
        return FileResponse(str(local_path))
    raise HTTPException(status_code=404, detail="File not found")


api = APIRouter(prefix="/api")

# Register routers
api.include_router(auth)
api.include_router(label_r)
api.include_router(release_r)
api.include_router(artist_r)
api.include_router(pay_r)
api.include_router(wami_r)
api.include_router(cms_r)
api.include_router(admin_r)
api.include_router(rate_import_r)
api.include_router(balance_audit_r)
api.include_router(label_analytics_r)
api.include_router(analytics_r)
api.include_router(royalty_r)
api.include_router(withdraw_r)
api.include_router(ticket_r)
api.include_router(contract_r)
api.include_router(migrate_r)
api.include_router(notif_r)
api.include_router(cron_r)


@api.get("/")
async def api_root():
    return {"name": "RILIS MUSIK API", "version": "0.1.0"}


@api.get("/health")
async def health():
    return {"ok": True, "time": now_iso()}


@app.get("/health")
async def root_health():
    """K8s readiness probe hits `/health` (no `/api` prefix). Returns 200
    immediately so the pod becomes Ready while heavy startup work (index
    builds, R2 CORS, import resume) finishes in the background."""
    return {"ok": True, "time": now_iso()}


app.include_router(api)

# ---- CORS ----
# Credentialed auth cookies require an explicit origin. If a legacy environment
# still contains CORS_ORIGINS='*', safely narrow it to FRONTEND_URL.
cors_raw = os.environ.get("CORS_ORIGINS", "").strip()
frontend_url = os.environ.get("FRONTEND_URL", "").strip().rstrip("/")
if cors_raw == "*":
    if not frontend_url:
        raise RuntimeError("FRONTEND_URL wajib diisi saat CORS_ORIGINS='*'")
    cors_origins = [frontend_url]
elif cors_raw:
    cors_origins = [o.strip().rstrip("/") for o in cors_raw.split(",") if o.strip() and o.strip() != "*"]
    if not cors_origins:
        if not frontend_url:
            raise RuntimeError("CORS_ORIGINS atau FRONTEND_URL wajib diisi")
        cors_origins = [frontend_url]
else:
    if not frontend_url:
        raise RuntimeError("FRONTEND_URL wajib diisi")
    cors_origins = [frontend_url]
cors_origins = expand_origin_variants(cors_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    """Defer ALL heavy bootstrap work to a background task so the K8s
    readiness probe gets `200 OK` from /health immediately. On production
    with 3M+ row collections, index creation alone routinely exceeds the
    Kubernetes readiness timeout (60-300s) and triggers a restart loop.
    """
    import asyncio
    asyncio.create_task(_bootstrap_async())
    logger.info("RILIS MUSIK API server up — deferring heavy bootstrap to background")


async def _bootstrap_async():
    """Background bootstrap: indexes, admin seeding, R2 CORS, scheduler,
    resume interrupted imports. Each step is wrapped to ensure one failure
    never breaks the others."""
    try:
        await seed_indexes_and_admins()
        logger.info("seed_indexes_and_admins() finished")
    except Exception as e:  # noqa: BLE001
        logger.exception("seed_indexes_and_admins failed (retry via /api/admin/migrate/ensure-indexes): %s", e)

    try:
        start_scheduler()
        logger.info("scheduler started")
    except Exception as e:  # noqa: BLE001
        logger.exception("start_scheduler failed: %s", e)

    try:
        # Reuse the credential-safe explicit backend origins. storage_service
        # merges them with existing bucket rules so preview/production cannot
        # overwrite each other's R2 CORS aliases.
        frontend_origins = cors_origins
        if frontend_origins:
            await storage_service.ensure_cors(frontend_origins)
            logger.info("R2 ensure_cors finished with origins=%s", frontend_origins)
        else:
            logger.info("R2 ensure_cors skipped — no allowed origins configured")
    except Exception as e:  # noqa: BLE001
        logger.exception("R2 ensure_cors failed: %s", e)

    # Resume any royalty CSV imports that were left in 'processing' state by a
    # previous container shutdown/hot-reload — must run AFTER db is ready.
    import asyncio
    asyncio.create_task(resume_interrupted_imports())
    asyncio.create_task(resume_label_rate_jobs())
    asyncio.create_task(resume_balance_audit_jobs())
    logger.info("RILIS MUSIK API bootstrap finished")


@app.on_event("shutdown")
async def on_shutdown():
    stop_scheduler()
    client.close()
