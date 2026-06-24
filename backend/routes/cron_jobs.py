"""Background scheduler + manual trigger endpoints.

- check_subscription_expiry_job: hourly cron, transitions expired subs and sends T-7/T-3/T-1 reminders.
- check_contract_expiry_job: daily cron at 02:00 UTC (~09:00 Jakarta), sends T-30/T-7/T-1 contract reminders.
- Two POST endpoints under /api/admin/cron/* allow super-admin / role-restricted manual triggers.
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .deps import db, logger, require_admin, notify, label_user_ids
from models import now_iso

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
    except Exception as e:
        logger.exception("Contract expiry job failed: %s", e)


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


def start_scheduler():
    """Register cron jobs and start the scheduler.

    Subscription expiry: hourly, with a 30-second first-run delay.
    Contract expiry reminder: daily at 02:00 UTC (~09:00 Jakarta).
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
    scheduler.start()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
