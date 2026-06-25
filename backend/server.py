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
from fastapi import FastAPI, APIRouter
from fastapi.staticfiles import StaticFiles
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
from routes.royalty import royalty_r, resume_interrupted_imports
from routes.withdraw import withdraw_r
from routes.tickets import ticket_r
from routes.notifications import notif_r
from routes.contracts import contract_r
from routes.migrate import migrate_r
from routes.cron_jobs import cron_r, start_scheduler, stop_scheduler
from routes.seed import seed_indexes_and_admins


app = FastAPI(title="RILIS MUSIK API", version="0.1.0")

# Serve uploaded media (audio, cover, etc.) under /api/files
app.mount("/api/files", StaticFiles(directory=str(UPLOAD_DIR)), name="files")

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


app.include_router(api)

# ---- CORS ----
# Reads CORS_ORIGINS from env: either '*' (allow all) or a comma-separated list.
# Falls back to FRONTEND_URL + localhost for dev convenience.
cors_raw = os.environ.get("CORS_ORIGINS", "").strip()
if cors_raw == "*":
    cors_kwargs = {"allow_origins": ["*"], "allow_credentials": False}
elif cors_raw:
    cors_kwargs = {"allow_origins": [o.strip() for o in cors_raw.split(",") if o.strip()], "allow_credentials": True}
else:
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    cors_kwargs = {"allow_origins": [frontend_url, "http://localhost:3000"], "allow_credentials": True}

app.add_middleware(
    CORSMiddleware,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    **cors_kwargs,
)


@app.on_event("startup")
async def on_startup():
    await seed_indexes_and_admins()
    start_scheduler()
    # Resume any royalty CSV imports that were left in 'processing' state by a
    # previous container shutdown/hot-reload — must run AFTER db is ready.
    import asyncio
    asyncio.create_task(resume_interrupted_imports())
    logger.info("RILIS MUSIK API started — scheduler online")


@app.on_event("shutdown")
async def on_shutdown():
    stop_scheduler()
    client.close()
