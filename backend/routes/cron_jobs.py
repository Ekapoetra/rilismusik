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
from email_service import send_contract_expiry_email, send_subscription_expiry_email, send_payment_reminder_email
from payment_service import poll_payment, xendit_configured
from .monthly_royalty_email import send_monthly_summaries
from .background_job_notifications import notify_completed_background_jobs
from .label_balance_snapshot import start_label_balance_snapshot_refresh
from .royalty_recalculation import close_stale_recalculation_jobs

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
                    user_doc = await db.users.find_one({"id": lab["user_id"]}, {"_id": 0, "email": 1})
                    if user_doc and user_doc.get("email"):
                        await send_subscription_expiry_email(
                            to=user_doc["email"],
                            label_name=lab.get("label_name") or "Label",
                            days_left=0,
                        )

        # 2) Send reminders for active subs expiring in T-30, T-7, T-3, T-1 days
        for days in (30, 7, 3, 1):
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


async def send_payment_reminders_job():
    """Remind labels about unpaid PPR / add-on (custom_service) invoices.

    Two one-off reminders per invoice: ~24h and ~72h after creation while still
    unpaid. Idempotent via `payment_reminders` markers stored on the payment doc.
    """
    try:
        now = datetime.now(timezone.utc)
        cursor = db.payments.find(
            {
                "status": {"$in": ["pending", "unpaid"]},
                "type": {"$in": ["pay_per_release", "custom_service"]},
            },
            {"_id": 0, "id": 1, "label_id": 1, "type": 1, "description": 1, "amount": 1,
             "release_id": 1, "created_at": 1, "payment_reminders": 1},
        )
        async for p in cursor:
            raw = p.get("created_at")
            if not raw:
                continue
            try:
                created = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
            except Exception:
                continue
            age_hours = (now - created).total_seconds() / 3600.0
            sent = set(p.get("payment_reminders") or [])
            marker = None
            if age_hours >= 72 and "72h" not in sent:
                marker, days_pending = "72h", 3
            elif age_hours >= 24 and "24h" not in sent:
                marker, days_pending = "24h", 1
            if not marker:
                continue
            label = await db.labels.find_one({"id": p["label_id"]}, {"_id": 0, "email": 1, "label_name": 1})
            if not (label and label.get("email")):
                # Still record the marker so we don't re-scan forever.
                await db.payments.update_one({"id": p["id"]}, {"$addToSet": {"payment_reminders": marker}})
                continue
            await send_payment_reminder_email(
                to=label["email"], label_name=label.get("label_name") or "Label",
                description=p.get("description") or "Tagihan RILIS MUSIK",
                amount_idr=int(p.get("amount") or 0), payment_id=p["id"],
                release_id=p.get("release_id"), days_pending=days_pending,
            )
            await db.payments.update_one({"id": p["id"]}, {"$addToSet": {"payment_reminders": marker}})
    except Exception as e:
        logger.exception("Payment reminder job failed: %s", e)



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


async def watchdog_stuck_recalculation_jobs():
    """Close abandoned rate/royalty recalculation jobs after four hours without progress."""
    try:
        result = await close_stale_recalculation_jobs()
        if result["closed"]:
            logger.warning("watchdog closed %d stale recalculation job(s)", result["closed"])
        return result
    except Exception as exc:
        logger.exception("watchdog_stuck_recalculation_jobs failed: %s", exc)
        return {"closed": 0, "job_ids": [], "error": type(exc).__name__}


async def reconcile_pending_xendit_payments():
    """Polling fallback for customers who close the Xendit checkout tab."""
    if not xendit_configured():
        return
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
    pending = await db.payments.find({
        "status": "pending",
        "xendit_session_id": {"$ne": None},
        "$or": [
            {"last_provider_poll_at": None},
            {"last_provider_poll_at": {"$lt": cutoff}},
        ],
    }, {"_id": 0}).sort("created_at", 1).limit(100).to_list(100)
    for payment in pending:
        try:
            await poll_payment(payment, force=True)
        except Exception as exc:
            logger.warning(
                "[XENDIT POLL] payment=%s failed: %s",
                payment.get("id"), type(exc).__name__,
            )


@cron_r.post("/payment-reminders-check")
async def trigger_payment_reminders_check(user: dict = Depends(require_admin)):
    """Manually run the unpaid-invoice reminder sweep."""
    await send_payment_reminders_job()
    return {"ok": True, "job": "payment_reminders"}



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


@cron_r.post("/stuck-recalculations-check")
async def trigger_stuck_recalculations_check(user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Super Admin / Admin Finance")
    return {"ok": True, **(await watchdog_stuck_recalculation_jobs())}


@cron_r.post("/xendit-payments-check")
async def trigger_xendit_payments_check(user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Super Admin / Admin Finance")
    await reconcile_pending_xendit_payments()
    return {"ok": True, "job": "xendit_payment_polling"}


@cron_r.post("/monthly-royalty-summary")
async def trigger_monthly_royalty_summary(period: str | None = None, user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Super Admin / Admin Finance")
    return await send_monthly_summaries(period)


@cron_r.get("/monthly-royalty-summary/status")
async def monthly_royalty_summary_status(user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Super Admin / Admin Finance")
    return await db.monthly_email_deliveries.find({}, {"_id": 0}).sort("created_at", -1).limit(500).to_list(500)


@cron_r.post("/background-completion-check")
async def trigger_background_completion_check(user: dict = Depends(require_admin)):
    return await notify_completed_background_jobs()


async def detect_releases_due_live_job():
    """Daily (08:00 WIB): find releases delivered to Believe whose release date has
    arrived (WIB) and nudge release admins to finalize UPC/ISRC and set them Live.
    The Work Queue item itself is computed via reconciliation; this job forces a
    refresh and sends a once-per-day summary notification to responsible admins."""
    try:
        today_wib = (datetime.now(timezone.utc) + timedelta(hours=7)).date().isoformat()
        due = await db.releases.count_documents({"status": "delivered", "release_date": {"$ne": None, "$lte": today_wib}})
        # Force a Work Queue reconciliation so the task surfaces immediately.
        try:
            from .work_service import reconcile_work, get_responsibility
            await reconcile_work(force=True)
        except Exception as exc:
            logger.warning("release-live reconcile failed: %s", exc)
            get_responsibility = None
        if not due:
            return {"due": 0, "notified": 0}
        role_ids = []
        if get_responsibility:
            mapping = await get_responsibility()
            role_ids = mapping.get("release_go_live", [])
        recipients = await db.users.find(
            {"$or": [{"role": "super_admin"}, {"admin_role_id": {"$in": role_ids}}]},
            {"_id": 0, "id": 1},
        ).to_list(500)
        notified = 0
        for u in recipients:
            marker = f"release_live_due_{today_wib}_{u['id']}"
            if await db.notifications.find_one({"user_id": u["id"], "meta.marker": marker}):
                continue
            await notify(
                u["id"], "release_go_live",
                f"{due} rilisan siap ditayangkan",
                f"Ada {due} rilisan yang sudah dikirim ke Believe dan tanggal rilisnya sudah tiba. Lengkapi UPC/ISRC lalu ubah status menjadi Tayang.",
                "/admin/releases?status=delivered",
                {"marker": marker, "due": due},
            )
            notified += 1
        return {"due": due, "notified": notified}
    except Exception as e:
        logger.exception("detect_releases_due_live_job failed: %s", e)
        return {"due": 0, "notified": 0, "error": type(e).__name__}


@cron_r.post("/release-live-check")
async def trigger_release_live_check(user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_release"):
        raise HTTPException(status_code=403, detail="Hanya Super Admin / Admin Release")
    return {"ok": True, **(await detect_releases_due_live_job())}


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
        detect_releases_due_live_job, "cron", hour=1, minute=0,
        id="release_go_live_detect", replace_existing=True,
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=75),
    )
    scheduler.add_job(
        watchdog_stuck_royalty_imports, "interval", minutes=15,
        id="stuck_royalty_imports_watchdog", replace_existing=True,
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=60),
    )
    scheduler.add_job(
        watchdog_stuck_recalculation_jobs, "interval", minutes=15,
        id="stuck_recalculation_jobs_watchdog", replace_existing=True,
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=45),
    )
    scheduler.add_job(
        reconcile_pending_xendit_payments, "interval", minutes=2,
        id="xendit_payment_polling", replace_existing=True,
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=90),
    )
    scheduler.add_job(
        send_monthly_summaries, "cron", day=3, hour=2, minute=0,
        id="monthly_royalty_summary", replace_existing=True,
    )
    scheduler.add_job(
        notify_completed_background_jobs, "interval", minutes=5,
        id="background_job_completion_notifications", replace_existing=True,
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=120),
    )
    scheduler.add_job(
        start_label_balance_snapshot_refresh, "interval", hours=1,
        kwargs={"reason": "hourly_scheduler"},
        id="label_balance_snapshot_refresh", replace_existing=True,
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=20),
    )
    scheduler.add_job(
        send_payment_reminders_job, "interval", hours=3,
        id="payment_reminders", replace_existing=True,
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=100),
    )
    scheduler.start()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
