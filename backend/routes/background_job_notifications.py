"""Emit in-app notifications when long-running admin jobs reach terminal states."""
from .deps import db, notify_many, admin_user_ids, logger
from models import now_iso


TERMINAL_JOB_STATUSES = ["done", "error", "failed", "completed"]
TERMINAL_IMPORT_STATUSES = ["pending_review", "published", "received", "error"]


def _job_label(job: dict) -> str:
    names = {
        "label_rate_sync": "Sinkronisasi rate label",
        "balance_audit_preview": "Audit saldo label",
        "balance_audit_commit": "Rekonsiliasi saldo label",
        "reset_all_data": "Reset data",
        "legacy_withdrawals_import": "Impor riwayat penarikan",
        "analytics_rebuild": "Pembangunan ulang analytics",
    }
    return names.get(job.get("kind"), str(job.get("kind") or "Background job").replace("_", " ").title())


async def _recipients(document: dict) -> list[str]:
    actor = document.get("created_by") or document.get("requested_by") or document.get("uploaded_by") or document.get("user_id")
    if actor:
        exists = await db.users.find_one({"id": actor, "status": {"$nin": ["disabled", "suspended"]}}, {"_id": 0, "id": 1})
        if exists:
            return [actor]
    return await admin_user_ids(("super_admin", "admin_finance"))


async def notify_completed_background_jobs(only_id: str | None = None) -> dict:
    counters = {"jobs": 0, "imports": 0}
    job_filter = {"status": {"$in": TERMINAL_JOB_STATUSES}, "completion_notified_at": {"$exists": False}}
    import_filter = {"status": {"$in": TERMINAL_IMPORT_STATUSES}}
    if only_id:
        job_filter["id"] = only_id
        import_filter["id"] = only_id
    jobs = await db.migrate_jobs.find(
        job_filter, {"_id": 0},
    ).sort("updated_at", 1).limit(200).to_list(200)
    for job in jobs:
        status = job.get("status")
        success = status in {"done", "completed"}
        recipients = await _recipients(job)
        await notify_many(
            recipients, "background_job_completed" if success else "background_job_failed",
            f"{_job_label(job)} {'selesai' if success else 'gagal'}",
            "Proses background telah selesai. Buka halaman terkait untuk melihat hasil." if success else str(job.get("error_message") or job.get("error") or "Proses gagal. Periksa detail job."),
            "/admin/migrate", {"job_id": job.get("id"), "kind": job.get("kind"), "status": status},
        )
        await db.migrate_jobs.update_one({"id": job["id"], "completion_notified_at": {"$exists": False}}, {"$set": {"completion_notified_at": now_iso(), "updated_at": now_iso()}})
        counters["jobs"] += 1
    imports = await db.royalty_imports.find(
        import_filter, {"_id": 0, "id": 1, "filename": 1, "status": 1, "uploaded_by": 1, "completion_notified_statuses": 1},
    ).sort("updated_at", 1).limit(200).to_list(200)
    for item in imports:
        status = item.get("status")
        if status in (item.get("completion_notified_statuses") or []):
            continue
        recipients = await _recipients(item)
        await notify_many(
            recipients, "royalty_import_status", f"Impor royalti: {status.replace('_', ' ')}",
            f"{item.get('filename') or item.get('id')} kini berstatus {status.replace('_', ' ')}.",
            "/admin/royalty", {"import_id": item.get("id"), "status": status},
        )
        await db.royalty_imports.update_one({"id": item["id"]}, {"$addToSet": {"completion_notified_statuses": status}, "$set": {"updated_at": now_iso()}})
        counters["imports"] += 1
    return counters