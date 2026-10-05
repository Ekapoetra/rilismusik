"""Private recurring queue ticks replace the legacy in-process scheduler."""
import hashlib
import os
import time
from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError
from vercel.queue import send
from background_runtime import run_background, recover_pending_dispatches

# Every API request passes through seed_schedule. The tick chain renews itself
# every 60 s through the queue, so one instance only needs to re-check the
# shared schedule document occasionally instead of writing it on every request.
SEED_CHECK_INTERVAL_SECONDS = 30
_next_seed_check = 0.0


async def seed_schedule(host: str):
    global _next_seed_check
    if os.environ.get("VERCEL_ENV") != "production" or host not in {
        "rilismusik.com", "www.rilismusik.com", "rilismusik.vercel.app",
    }:
        return
    from routes.deps import db_bg
    deployment = os.environ.get("VERCEL_DEPLOYMENT_ID")
    if not deployment:
        return
    now = time.time()
    if now < _next_seed_check:
        return
    # Reserve the slot before awaiting so concurrent requests skip the check.
    _next_seed_check = now + SEED_CHECK_INTERVAL_SECONDS
    active = await db_bg.serverless_schedule.find_one({"_id": "active"}, {"deployment": 1, "tick_until": 1}) or {}
    if active.get("deployment") == deployment and float(active.get("tick_until") or 0) >= now:
        return
    if active.get("deployment") != deployment:
        await db_bg.serverless_schedule.update_one({"_id": "active"}, {"$set": {"deployment": deployment}}, upsert=True)
    claimed = await db_bg.serverless_schedule.update_one({
        "_id": "active", "$or": [{"tick_until": {"$lt": now}}, {"tick_until": {"$exists": False}}],
    }, {"$set": {"tick_until": now + 180}})
    if claimed.matched_count:
        await send("rilismusik-schedule", {"deployment": deployment}, delay=1,
                   idempotency_key=f"tick:{deployment}:{int(now // 60)}")


async def process_tick(payload: dict):
    from routes.deps import db_bg
    active = await db_bg.serverless_schedule.find_one({"_id": "active"}) or {}
    deployment = os.environ.get("VERCEL_DEPLOYMENT_ID")
    if payload.get("deployment") != deployment or active.get("deployment") != deployment:
        return  # An old deployment must not keep scheduling after a cutover.
    from routes import cron_jobs as cron
    from routes.background_job_notifications import notify_completed_background_jobs
    from routes.label_balance_snapshot import start_label_balance_snapshot_refresh
    from routes.contentid_assets import contentid_maintenance_once
    from routes.direct_uploads import cleanup_expired_direct_uploads
    from routes.royalty_report_export import cleanup_expired_report_exports
    from routes.staff import finalize_yesterday_attendance
    await recover_pending_dispatches()
    now = datetime.now(timezone.utc)
    epoch = int(now.timestamp())
    tasks = [
        (cron.reconcile_pending_xendit_payments, 120, {}),
        (notify_completed_background_jobs, 300, {}),
        (contentid_maintenance_once, 900, {}),
        (cleanup_expired_direct_uploads, 900, {}),
        (cleanup_expired_report_exports, 900, {}),
        (cron.check_subscription_expiry_job, 3600, {}),
        (start_label_balance_snapshot_refresh, 3600, {"reason": "hourly_scheduler"}),
        (cron.send_payment_reminders_job, 10800, {}),
    ]
    # Daily/monthly jobs run only inside their existing UTC schedule windows.
    if now.hour == 2 and now.minute < 5:
        tasks += [(cron.check_contract_expiry_job, 86400, {}),
                  (cron.believe_followup_reminder_job, 86400, {})]
        if now.day == 3:
            from routes.monthly_royalty_email import send_monthly_summaries
            tasks.append((send_monthly_summaries, 86400, {}))
    if now.hour == 1 and now.minute < 5:
        tasks.append((cron.detect_releases_due_live_job, 86400, {}))
    if now.hour == 17 and 30 <= now.minute < 35:
        tasks.append((finalize_yesterday_attendance, 86400, {}))
    for function, interval, kwargs in tasks:
        identity = f"{function.__module__}:{function.__name__}:{epoch // interval}"
        task_id = hashlib.sha256(identity.encode()).hexdigest()[:32]
        await run_background(function, _dispatch_id=task_id, **kwargs)
    await send("rilismusik-schedule", {"deployment": deployment}, delay=60,
               idempotency_key=f"tick:{deployment}:{epoch // 60 + 1}")
    await db_bg.serverless_schedule.update_one({"_id": "active", "deployment": deployment},
        {"$set": {"tick_until": time.time() + 180, "last_tick_epoch": time.time()}})
