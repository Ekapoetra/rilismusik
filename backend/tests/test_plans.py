"""V13 package changes: upgrades start now, lower packages wait for the current end."""
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import test_vercel_preview  # Configures offline environment before real router imports.
from mongomock_motor import AsyncMongoMockClient
import payment_service
from routes import cron_jobs, entitlements

NOW = datetime.now(timezone.utc)


def iso(days):
    return (NOW + timedelta(days=days)).isoformat()


class PlanTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = AsyncMongoMockClient(tz_aware=True).test
        self.patches = [patch.object(payment_service, "db", self.db), patch.object(cron_jobs, "db", self.db),
                        patch.object(cron_jobs, "notify", AsyncMock())]
        for item in self.patches:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in self.patches])
        await self.db.labels.insert_one({"id": "l1", "user_id": "u1", "payment_type": "annual_subscription",
                                         "subscription_status": "active", "subscription_tier": "annual_vip",
                                         "subscription_expires_at": iso(100)})

    async def label(self):
        return await self.db.labels.find_one({"id": "l1"}, {"_id": 0})

    async def test_downgrade_is_scheduled_at_current_end(self):
        await payment_service._fulfill_subscription({"id": "p1", "label_id": "l1", "tier": "annual_normal"})
        label = await self.label()
        self.assertEqual(label["subscription_tier"], "annual_vip")
        change = label["scheduled_plan_change"]
        self.assertEqual((change["tier"], change["source"]), ("annual_normal", "payment"))
        self.assertEqual(entitlements.resolve_label_entitlements(label)["package"], "annual_vip")
        self.assertEqual(entitlements.pending_plan_change(label)["tier"], "annual_normal")

    async def test_upgrade_starts_now_and_adds_remaining_time(self):
        await self.db.labels.update_one({"id": "l1"}, {"$set": {"subscription_tier": "annual_normal"}})
        await payment_service._fulfill_subscription({"id": "p2", "label_id": "l1", "tier": "annual_vip"})
        label = await self.label()
        self.assertEqual(label["subscription_tier"], "annual_vip")
        self.assertGreater(datetime.fromisoformat(label["subscription_expires_at"]), NOW + timedelta(days=464))
        self.assertNotIn("scheduled_plan_change", label)

    async def test_scheduled_package_takes_over_when_current_ends(self):
        await self.db.labels.update_one({"id": "l1"}, {"$set": {"subscription_expires_at": iso(-1), "scheduled_plan_change": {
            "tier": "annual_normal", "starts_at": iso(-1), "ends_at": iso(364), "source": "payment"}}})
        label = await self.label()
        self.assertEqual(entitlements.resolve_label_entitlements(label)["package"], "annual_normal")
        await cron_jobs.check_subscription_expiry_job()
        label = await self.label()
        self.assertEqual((label["subscription_tier"], label["subscription_status"]), ("annual_normal", "active"))
        self.assertNotIn("scheduled_plan_change", label)

    async def test_scheduled_basic_lets_package_expire(self):
        await self.db.labels.update_one({"id": "l1"}, {"$set": {"subscription_expires_at": iso(-1), "scheduled_plan_change": {
            "tier": "pay_per_release", "starts_at": iso(-1), "source": "basic"}}})
        self.assertEqual(entitlements.resolve_label_entitlements(await self.label())["package"], "pay_per_release")
        await cron_jobs.check_subscription_expiry_job()
        label = await self.label()
        self.assertEqual(label["subscription_status"], "expired")
        self.assertNotIn("scheduled_plan_change", label)


if __name__ == "__main__":
    unittest.main()
