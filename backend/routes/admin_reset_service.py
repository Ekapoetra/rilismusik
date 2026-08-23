"""Background full-data reset service."""
import asyncio
from pathlib import Path
from typing import Any, Dict

from models import now_iso
from .dashboard_cache import reset as reset_dashboard_cache
from .deps import ADMIN_ROLES, SUPER_ADMIN, UPLOAD_DIR, db_bg, logger, log_activity


BUSINESS_COLLECTIONS = [
    "labels", "releases", "tracks", "artists", "bank_accounts",
    "royalty_imports", "royalty_lines", "royalty_percentage_history",
    "balance_transactions", "withdraw_requests", "contracts",
    "support_tickets", "ticket_comments", "payments", "wami_orders",
    "notifications", "activity_logs", "login_attempts",
    "email_verification_tokens", "password_reset_tokens",
]
CACHE_COLLECTIONS = ["monthly_analytics", "metrics_cache", "rollup_health"]


async def _progress(job_id: str, phase: str) -> None:
    await db_bg.migrate_jobs.update_one(
        {"id": job_id},
        {"$set": {"status": "running", "phase": phase, "updated_at": now_iso()}},
    )


async def _drop_collections(job_id: str, report: Dict[str, Any]) -> None:
    for collection in BUSINESS_COLLECTIONS + CACHE_COLLECTIONS:
        await _progress(job_id, f"dropping_{collection}")
        try:
            report[collection] = await db_bg[collection].estimated_document_count()
        except Exception:
            report[collection] = 0
        await db_bg.drop_collection(collection)


def _delete_local_uploads(upload_dir: Path) -> int:
    deleted = 0
    if not upload_dir.exists():
        return deleted
    for path in upload_dir.rglob("*"):
        if path.is_file():
            path.unlink(missing_ok=True)
            deleted += 1
    return deleted


def _wipe_r2_bucket_sync() -> int:
    import storage_service
    if not storage_service.is_configured():
        return 0
    client = storage_service._client()
    bucket = storage_service.R2_BUCKET
    deleted = 0
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket):
        objects = page.get("Contents") or []
        if objects:
            client.delete_objects(Bucket=bucket, Delete={"Objects": [{"Key": item["Key"]} for item in objects]})
            deleted += len(objects)
    return deleted


async def _optional_r2_cleanup(job_id: str, report: dict, enabled: bool) -> None:
    if not enabled:
        return
    await _progress(job_id, "wiping_r2")
    try:
        report["r2_objects_deleted"] = await asyncio.to_thread(_wipe_r2_bucket_sync)
    except Exception as exc:
        logger.exception("R2 cleanup during reset failed: %s", exc)
        report["r2_cleanup_error"] = str(exc)


async def _reseed(job_id: str, report: dict) -> None:
    from .seed import seed_indexes_and_admins
    await _progress(job_id, "reseeding")
    try:
        await seed_indexes_and_admins()
        report["reseed"] = "ok"
    except Exception as exc:
        logger.exception("Reseed after reset failed: %s", exc)
        report["reseed_error"] = str(exc)


async def run_full_reset(
    *, job_id: str, delete_r2_files: bool, user_id: str, user_email: str,
) -> None:
    report: Dict[str, Any] = {}
    try:
        await _progress(job_id, "wiping_users")
        users = await db_bg.users.delete_many({"role": {"$nin": list(ADMIN_ROLES) + [SUPER_ADMIN]}})
        report["users_deleted_non_admin"] = users.deleted_count
        await _drop_collections(job_id, report)
        await db_bg.migrate_jobs.delete_many({"id": {"$ne": job_id}})
        reset_dashboard_cache()
        try:
            report["local_files_deleted"] = _delete_local_uploads(UPLOAD_DIR)
        except Exception as exc:
            report["local_files_error"] = str(exc)
        await _optional_r2_cleanup(job_id, report, delete_r2_files)
        await _reseed(job_id, report)
        await log_activity(user_id, "danger_reset_all_data", "system", "global", after=report)
        logger.warning("[DANGER] Full data reset by super_admin %s: %s", user_email, report)
        await db_bg.migrate_jobs.update_one({"id": job_id}, {"$set": {
            "status": "done", "phase": "done", "result": report,
            "finished_at": now_iso(), "updated_at": now_iso(),
        }})
    except Exception as exc:
        logger.exception("[DANGER] Full data reset FAILED: %s", exc)
        try:
            await db_bg.migrate_jobs.update_one({"id": job_id}, {"$set": {
                "status": "error", "error_message": f"{type(exc).__name__}: {str(exc)[:300]}",
                "result": report, "updated_at": now_iso(),
            }})
        except Exception as update_exc:
            logger.exception("[DANGER] Could not record reset failure: %s", update_exc)