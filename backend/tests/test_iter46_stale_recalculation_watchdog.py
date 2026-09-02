"""Iteration 46 — stale recalculation watchdog and cron guard regressions."""
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pymongo
import requests
from dotenv import load_dotenv

from tests.support_config import FINANCE, SUPERADMIN, SUPPORT


load_dotenv(Path(__file__).resolve().parents[1] / ".env")
from routes import cron_jobs


BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


def _db():
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


def _login(creds: dict) -> str:
    response = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# Feature: manual stale recalculation cron endpoint auth + atomic stale closure behavior.
def test_manual_stuck_recalculation_endpoint_closes_only_stale_jobs_and_enforces_roles():
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    stale_job_id = f"iter46-stale-{suffix}"
    recent_job_id = f"iter46-recent-{suffix}"
    stale_updated_at = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
    recent_updated_at = datetime.now(timezone.utc).isoformat()

    db.migrate_jobs.insert_many([
        {
            "id": stale_job_id,
            "kind": "recalculate_all_unwithdrawn",
            "status": "processing",
            "phase": "recalculating_labels",
            "updated_at": stale_updated_at,
        },
        {
            "id": recent_job_id,
            "kind": "recalculate_all_unwithdrawn",
            "status": "processing",
            "phase": "recalculating_labels",
            "updated_at": recent_updated_at,
        },
    ])

    try:
        support_token = _login(SUPPORT)
        forbidden = requests.post(
            f"{API}/admin/cron/stuck-recalculations-check",
            headers=_headers(support_token),
            timeout=20,
        )
        assert forbidden.status_code == 403, forbidden.text

        finance_token = _login(FINANCE)
        allowed = requests.post(
            f"{API}/admin/cron/stuck-recalculations-check",
            headers=_headers(finance_token),
            timeout=20,
        )
        assert allowed.status_code == 200, allowed.text
        payload = allowed.json()
        assert payload["ok"] is True
        assert stale_job_id in payload.get("job_ids", [])
        assert payload.get("closed") == 1

        stale_job = db.migrate_jobs.find_one({"id": stale_job_id})
        assert stale_job["status"] == "error"
        assert stale_job["phase"] == "error"
        assert stale_job["stale_job_closed"] is True
        assert stale_job.get("finished_at")
        assert stale_job.get("error_message")
        assert "Proses ditutup otomatis" in stale_job["error_message"]

        recent_job = db.migrate_jobs.find_one({"id": recent_job_id})
        assert recent_job["status"] == "processing"
        assert recent_job.get("stale_job_closed") is None
    finally:
        db.migrate_jobs.delete_many({"id": {"$in": [stale_job_id, recent_job_id]}})


# Feature: global recalc endpoint should close stale jobs first, then respect active recent job blocking.
def test_global_recalculate_endpoint_closes_stale_old_job_before_already_running_check():
    db = _db()
    token = _login(SUPERADMIN)
    suffix = uuid.uuid4().hex[:8]
    stale_job_id = f"iter46-recalc-stale-{suffix}"
    recent_job_id = f"iter46-recalc-recent-{suffix}"

    db.migrate_jobs.insert_many([
        {
            "id": stale_job_id,
            "kind": "recalculate_all_unwithdrawn",
            "status": "processing",
            "updated_at": (datetime.now(timezone.utc) - timedelta(hours=8)).isoformat(),
        },
        {
            "id": recent_job_id,
            "kind": "recalculate_all_unwithdrawn",
            "status": "processing",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    ])

    try:
        response = requests.post(
            f"{API}/royalty/admin/recalculate-unwithdrawn",
            headers=_headers(token),
            timeout=20,
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["already_running"] is True
        assert payload["job_id"] == recent_job_id

        stale_job = db.migrate_jobs.find_one({"id": stale_job_id})
        assert stale_job["status"] == "error"
        assert stale_job["stale_job_closed"] is True
        assert stale_job.get("finished_at")
    finally:
        db.migrate_jobs.delete_many({"id": {"$in": [stale_job_id, recent_job_id]}})


# Feature: scheduler should register stale recalculation watchdog every 15 minutes.
def test_scheduler_registers_stale_recalculation_watchdog_every_15_minutes(monkeypatch):
    captured_jobs = []

    class DummyScheduler:
        running = False

        def add_job(self, func, trigger, **kwargs):
            captured_jobs.append({
                "func_name": getattr(func, "__name__", ""),
                "trigger": trigger,
                **kwargs,
            })

        def start(self):
            return None

    monkeypatch.setattr(cron_jobs, "scheduler", DummyScheduler())
    cron_jobs.start_scheduler()

    target = [
        job for job in captured_jobs
        if job.get("id") == "stuck_recalculation_jobs_watchdog"
    ]
    assert len(target) == 1
    assert target[0]["trigger"] == "interval"
    assert target[0]["minutes"] == 15
    assert target[0]["replace_existing"] is True
