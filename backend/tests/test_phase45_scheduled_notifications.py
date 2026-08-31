"""Phase 45 — monthly royalty email idempotency and background job alerts."""
import asyncio
import uuid
from dotenv import load_dotenv


load_dotenv("/app/backend/.env", override=True)
LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(LOOP)


def test_monthly_email_is_sent_once_per_label_period(monkeypatch):
    from routes import monthly_royalty_email as module

    async def scenario():
        db = module.db
        suffix = uuid.uuid4().hex[:10]
        user_id = f"phase45-user-{suffix}"
        label_id = f"phase45-label-{suffix}"
        period = "2026-07"
        sent = []

        async def fake_send(**kwargs):
            sent.append(kwargs)
            return "phase45-message-id"

        monkeypatch.setattr(module, "send_monthly_royalty_summary_email", fake_send)
        await db.users.insert_one({"id": user_id, "email": f"phase45-{suffix}@example.com", "status": "active"})
        await db.labels.insert_one({"id": label_id, "user_id": user_id, "label_name": "Phase 45 Label"})
        await db.royalty_lines.insert_many([
            {"id": f"phase45-line-a-{suffix}", "label_id": label_id, "period": period, "track_title_raw": "Track A", "quantity": 120, "label_idr": 15000},
            {"id": f"phase45-line-b-{suffix}", "label_id": label_id, "period": period, "track_title_raw": "Track B", "quantity": 80, "label_idr": 10000},
        ])
        try:
            first = await module.send_one_monthly_summary(label_id, period)
            second = await module.send_one_monthly_summary(label_id, period)
            assert first == "sent"
            assert second == "already-sent"
            assert len(sent) == 1
            assert sent[0]["total_idr"] == 25000
            assert sent[0]["streams"] == 200
            delivery = await db.monthly_email_deliveries.find_one({"label_id": label_id, "period": period}, {"_id": 0})
            assert delivery["status"] == "sent"
            assert delivery["attempts"] == 1
        finally:
            await db.monthly_email_deliveries.delete_many({"label_id": label_id})
            await db.royalty_lines.delete_many({"label_id": label_id})
            await db.labels.delete_one({"id": label_id})
            await db.users.delete_one({"id": user_id})

    LOOP.run_until_complete(scenario())


def test_completed_background_job_notifies_actor_once():
    from routes import background_job_notifications as module

    async def scenario():
        db = module.db
        suffix = uuid.uuid4().hex[:10]
        user_id = f"phase45-admin-{suffix}"
        job_id = f"phase45-job-{suffix}"
        await db.users.insert_one({"id": user_id, "email": f"phase45-admin-{suffix}@example.com", "status": "active", "role": "admin_finance"})
        await db.migrate_jobs.insert_one({
            "id": job_id, "kind": "label_rate_sync", "status": "done",
            "created_by": user_id, "created_at": "2026-09-01T00:00:00+00:00", "updated_at": "2026-09-01T00:01:00+00:00",
        })
        try:
            first = await module.notify_completed_background_jobs(job_id)
            second = await module.notify_completed_background_jobs(job_id)
            assert first["jobs"] == 1
            assert second["jobs"] == 0
            notifications = await db.notifications.find({"user_id": user_id, "meta.job_id": job_id}, {"_id": 0}).to_list(10)
            assert len(notifications) == 1
            assert notifications[0]["type"] == "background_job_completed"
            job = await db.migrate_jobs.find_one({"id": job_id}, {"_id": 0})
            assert job.get("completion_notified_at")
        finally:
            await db.notifications.delete_many({"user_id": user_id, "meta.job_id": job_id})
            await db.migrate_jobs.delete_one({"id": job_id})
            await db.users.delete_one({"id": user_id})

    LOOP.run_until_complete(scenario())