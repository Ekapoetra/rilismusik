"""Background scheduler + manual trigger endpoints.

- check_subscription_expiry_job: hourly cron, transitions expired subs and sends T-7/T-3/T-1 reminders.
- check_contract_expiry_job: daily cron at 02:00 UTC (~09:00 Jakarta), sends T-30/T-7/T-1 contract reminders.
- Two POST endpoints under /api/admin/cron/* allow super-admin / role-restricted manual triggers.
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .deps import db, db_bg, logger, require_admin, notify, label_user_ids
from models import now_iso
from email_service import send_contract_expiry_email, send_subscription_expiry_email

scheduler = AsyncIOScheduler(timezone="UTC")

cron_r = APIRouter(prefix="/admin/cron", tags=["admin-cron"])


async def check_subscription_expiry_job():
    """Hourly cron: transition expired subscriptions and send reminders at T-7, T-3, T-1 days."""
    try:
        now = datetime.now(timezone.utc)
        # 1) Transition expired subscriptions
        async for lab in db.labels.find(
            {"subscription_status": "active", "subscription_expires_at": {"$ne": None}},
            {"_id": 0, "id": 1, "label_name": 1, "user_id": 1, "subscription_expires_at": 1},
        ):
            raw = lab.get("subscription_expires_at")
            if not raw:
                continue
            try:
                expires = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
            except Exception:
                continue
            if expires <= now:
                await db.labels.update_one(
                    {"id": lab["id"]},
                    {"$set": {
                        "subscription_status": "expired",
                        "payment_type": "pay_per_release",
                        "updated_at": now_iso(),
                    }},
                )
                logger.info("Subscription expired for label %s", lab.get("label_name"))
                if lab.get("user_id"):
                    await notify(
                        lab["user_id"], "subscription_expired",
                        "Subscription Anda berakhir",
                        "Subscription tahunan Anda berakhir hari ini. Beralih ke Pay Per Release atau perpanjang sekarang.",
                        "/label/invoices", {"label_id": lab["id"]},
                    )

        # 2) Send reminders for active subs expiring in T-7, T-3, T-1 days
        for days in (7, 3, 1):
            target_low = now + timedelta(days=days - 1)
            target_high = now + timedelta(days=days)
            async for lab in db.labels.find(
                {
                    "subscription_status": "active",
                    "subscription_expires_at": {
                        "$gte": target_low.isoformat(),
                        "$lt": target_high.isoformat(),
                    },
                },
                {"_id": 0, "id": 1, "user_id": 1, "label_name": 1},
            ):
                if not lab.get("user_id"):
                    continue
                marker = f"sub_remind_{days}_{lab['id']}_{(now + timedelta(days=days)).date().isoformat()}"
                exists = await db.notifications.find_one({"user_id": lab["user_id"], "meta.marker": marker})
                if exists:
                    continue
                await notify(
                    lab["user_id"], "subscription_reminder",
                    f"Subscription berakhir dalam {days} hari",
                    "Perpanjang sekarang untuk tetap upload rilisan tanpa biaya per release.",
                    "/label/invoices",
                    {"days_left": days, "marker": marker, "label_id": lab["id"]},
                )
                # Send transactional email too (best-effort)
                user_doc = await db.users.find_one({"id": lab["user_id"]}, {"_id": 0, "email": 1})
                if user_doc and user_doc.get("email"):
                    await send_subscription_expiry_email(
                        to=user_doc["email"],
                        label_name=lab.get("label_name") or "Label",
                        days_left=days,
                    )
    except Exception as e:
        logger.exception("Subscription expiry job failed: %s", e)


async def check_contract_expiry_job():
    """Daily cron: notify labels whose contract is in T-30/T-7/T-1 days window."""
    try:
        today = datetime.now(timezone.utc).date()
        for days in (30, 7, 1):
            target = (today + timedelta(days=days)).isoformat()
            async for c in db.contracts.find(
                {"status": {"$ne": "terminated"}, "end_date": target},
                {"_id": 0, "id": 1, "label_id": 1, "label_name": 1, "end_date": 1},
            ):
                user_ids = await label_user_ids(c["label_id"])
                marker = f"contract_remind_{days}_{c['id']}_{today.isoformat()}"
                for uid in user_ids:
                    exists = await db.notifications.find_one({"user_id": uid, "meta.marker": marker})
                    if exists:
                        continue
                    await notify(
                        uid, "contract_reminder",
                        f"Kontrak berakhir dalam {days} hari",
                        f"Kontrak distribusi Anda berakhir {c['end_date']}. Hubungi admin untuk perpanjangan.",
                        "/label/contract",
                        {"days_left": days, "marker": marker, "contract_id": c["id"]},
                    )
                    # Send transactional email too (best-effort)
                    user_doc = await db.users.find_one({"id": uid}, {"_id": 0, "email": 1})
                    if user_doc and user_doc.get("email"):
                        await send_contract_expiry_email(
                            to=user_doc["email"],
                            label_name=c.get("label_name") or "Label",
                            days_left=days,
                            end_date=c["end_date"],
                        )
    except Exception as e:
        logger.exception("Contract expiry job failed: %s", e)


# Threshold for considering an import "stuck": no progress updates for this
# many minutes while status remains 'processing'. Tuned to be slow enough
# that genuine 1M-row imports finish first (~5 min worst case post-Phase 16.5)
# but quick enough that ops doesn't have to wait an hour.
STUCK_IMPORT_AFTER_MINUTES = 30


async def watchdog_stuck_royalty_imports():
    """Every 15 min: detect royalty_imports stuck in `processing` for >30 min
    with no progress updates, and auto-recover them by recomputing stats
    from the actual royalty_lines rows.

    - If actual_lines > 0  → set status='pending_review' (final-flip likely
                              hit a CSOT timeout; data is already there).
    - If actual_lines == 0 → set status='error' so admin can retry/upload.

    The recompute is idempotent and safe to re-run.
    """
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=STUCK_IMPORT_AFTER_MINUTES)).isoformat()
        # Lazy-import the helper to avoid a circular import (cron_jobs ← royalty).
        from .royalty import _recompute_import_stats_from_lines
        stuck = await db.royalty_imports.find(
            {"status": "processing", "updated_at": {"$lt": cutoff}},
            {"_id": 0, "id": 1, "filename": 1, "updated_at": 1},
        ).to_list(50)
        if not stuck:
            return
        logger.info("watchdog_stuck_royalty_imports: found %d stuck import(s)", len(stuck))
        for imp in stuck:
            import_id = imp["id"]
            try:
                stats = await _recompute_import_stats_from_lines(import_id)
                if stats["total_lines"] > 0:
                    update_doc = {
                        **stats,
                        "status": "pending_review",
                        "error_message": None,
                        "finished_at": now_iso(),
                        "updated_at": now_iso(),
                        "period": (stats["period_start"] if stats["period_start"] == stats["period_end"] else "multi"),
                        "watchdog_recovered": True,
                    }
                    await db_bg.royalty_imports.update_one({"id": import_id}, {"$set": update_doc})
                    logger.info(
                        "watchdog: import %s auto-finalized → pending_review (%d rows)",
                        import_id, stats["total_lines"],
                    )
                else:
                    await db_bg.royalty_imports.update_one(
                        {"id": import_id},
                        {"$set": {
                            "status": "error",
                            "error_message": (
                                f"Watchdog: import nyangkut >{STUCK_IMPORT_AFTER_MINUTES} menit tanpa "
                                "baris di MongoDB. Silakan retry atau upload ulang."
                            ),
                            "finished_at": now_iso(),
                            "updated_at": now_iso(),
                            "watchdog_failed": True,
                        }},
                    )
                    logger.warning("watchdog: import %s marked error (0 rows in DB)", import_id)
            except Exception as inner:
                logger.exception("watchdog: failed to recover import %s: %s", import_id, inner)
    except Exception as e:
        logger.exception("watchdog_stuck_royalty_imports job failed: %s", e)


@cron_r.post("/subscription-check")
async def trigger_subscription_check(user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Super Admin / Admin Finance")
    await check_subscription_expiry_job()
    return {"ok": True, "job": "subscription_expiry"}


@cron_r.post("/contract-check")
async def trigger_contract_check(user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_release"):
        raise HTTPException(status_code=403, detail="Hanya Super Admin / Admin Release")
    await check_contract_expiry_job()
    return {"ok": True, "job": "contract_expiry_reminder"}


@cron_r.post("/stuck-imports-check")
async def trigger_stuck_imports_check(user: dict = Depends(require_admin)):
    """Manually trigger the stuck-royalty-import watchdog. Useful when an admin
    notices an import sitting at 99% and doesn't want to wait for the next
    15-min tick."""
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Super Admin / Admin Finance")
    await watchdog_stuck_royalty_imports()
    return {"ok": True, "job": "watchdog_stuck_royalty_imports"}


def start_scheduler():
    """Register cron jobs and start the scheduler.

    Subscription expiry: hourly, with a 30-second first-run delay.
    Contract expiry reminder: daily at 02:00 UTC (~09:00 Jakarta).
    Stuck-import watchdog: every 15 minutes, first run after 60 seconds.
    """
    scheduler.add_job(
        check_subscription_expiry_job, "interval", hours=1,
        id="subscription_expiry", replace_existing=True,
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=30),
    )
    scheduler.add_job(
        check_contract_expiry_job, "cron", hour=2, minute=0,
        id="contract_expiry_reminder", replace_existing=True,
    )
    scheduler.add_job(
        watchdog_stuck_royalty_imports, "interval", minutes=15,
        id="stuck_royalty_imports_watchdog", replace_existing=True,
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=60),
    )
    scheduler.start()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
