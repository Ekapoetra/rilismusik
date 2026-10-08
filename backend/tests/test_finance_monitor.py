"""Financial Monitoring reports agree with the withdrawal balance sources."""
import unittest
from unittest.mock import patch

import test_vercel_preview  # Configures offline environment before real router imports.
from mongomock_motor import AsyncMongoMockClient
from routes import finance_monitor, royalty_adjustment_balance


class FinanceMonitorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = AsyncMongoMockClient(tz_aware=True).test
        self.patches = [patch.object(finance_monitor, "db_bg", self.db), patch.object(finance_monitor, "db", self.db),
                        patch.object(royalty_adjustment_balance, "db_bg", self.db)]
        for item in self.patches:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in self.patches])
        finance_monitor._cache.clear()
        await self.db.labels.insert_many([
            {"id": "a1", "user_id": "u1", "label_name": "Alpha", "last_withdrawn_period": "2024-01", "bank_verified": True},
            {"id": "a2", "user_id": "u1", "label_name": "Alpha Two", "bank_verified": True},
            {"id": "b1", "user_id": "u2", "label_name": "Beta", "bank_verified": False},
            {"id": "z1", "user_id": "u3", "label_name": "Empty"},
        ])
        await self.db.royalty_lines.insert_many([
            {"label_id": "a1", "period": "2024-01", "status": "available", "label_idr": 999_000},  # before cutoff
            {"label_id": "a1", "period": "2024-06", "status": "available", "label_idr": 700_000},
            {"label_id": "a1", "period": "2099-01", "status": "available", "label_idr": 500_000},
            {"label_id": "a2", "period": "2099-01", "status": "pending", "label_idr": 80_000},
            {"label_id": "b1", "period": "2099-01", "status": "available", "label_idr": 300_000},
            {"label_id": "b1", "period": "2099-02", "status": "available", "label_idr": 1, "legacy_settled": True},
        ])
        await self.db.withdraw_requests.insert_many([
            {"label_id": "a1", "status": "requested", "amount_idr": 200_000},
            {"label_id": "b1", "status": "paid", "amount_idr": 50_000, "paid_at": "2026-01-02T00:00:00+00:00"},
        ])
        await self.db.monthly_analytics.insert_many([
            {"dim": "total", "period": "2026-08", "revenue_idr": 900}, {"dim": "total", "period": "2026-07", "revenue_idr": 800},
            {"dim": "label", "key": "a1", "period": "2026-08", "revenue_idr": 150}, {"dim": "label", "key": "a1", "period": "2026-07", "revenue_idr": 100},
            {"dim": "label", "key": "b1", "period": "2026-08", "revenue_idr": 40},
        ])

    async def test_funds_group_accounts_and_age_lots(self):
        result = await finance_monitor._build_funds()
        rows = {row["id"]: row for row in result["rows"]}
        self.assertNotIn("u3", rows)
        alpha = rows["u1"]
        self.assertEqual(alpha["label_count"], 2)
        self.assertEqual(alpha["available_idr"], 1_000_000)  # 700k + 500k - 200k reserved
        self.assertEqual(alpha["processing_idr"], 200_000)
        self.assertEqual(alpha["unpaid_idr"], 1_200_000)
        self.assertEqual(alpha["pending_idr"], 80_000)
        self.assertEqual(alpha["age"]["d365_plus"], 500_000)  # oldest lot reserved first
        self.assertEqual(alpha["condition"], "has_request")
        self.assertEqual(alpha["last_income"], {"period": "2026-08", "amount_idr": 150})
        beta = rows["u2"]
        self.assertEqual(beta["available_idr"], 300_000)
        self.assertEqual(beta["paid_idr"], 50_000)
        self.assertEqual(beta["condition"], "accumulating")
        self.assertFalse(beta["bank_verified"])
        self.assertEqual(result["totals"]["unpaid_idr"], 1_500_000)

    async def test_minimum_follows_production_rule(self):
        row = {"anomalies": [], "processing_idr": 0, "available_idr": 1_000_000}
        self.assertEqual(finance_monitor._condition(row), "accumulating")
        row["available_idr"] = 1_000_001
        self.assertEqual(finance_monitor._condition(row), "minimum_reached")

    async def test_catalogue_compares_consecutive_complete_periods(self):
        result = await finance_monitor._build_catalogue()
        self.assertEqual((result["period"], result["previous_period"], result["comparable"]), ("2026-08", "2026-07", True))
        rows = {row["label_id"]: row for row in result["rows"]}
        self.assertEqual(rows["a1"]["change_pct"], 50.0)
        self.assertIsNone(rows["b1"]["change_pct"])  # no base month, no percentage

    async def test_cash_keeps_receipts_payouts_and_observations_apart(self):
        await self.db.royalty_imports.insert_many([
            {"id": "i1", "status": "dana_received", "total_revenue_eur": 10, "exchange_rate_eur_idr": 17000, "total_label_idr": 120_000, "created_at": "1"},
            {"id": "i2", "status": "published", "total_revenue_eur": 5, "exchange_rate_eur_idr": 17000, "total_label_idr": 60_000, "created_at": "2"},
            {"id": "i3", "status": "processing", "total_label_idr": 1, "created_at": "3"},
        ])
        result = await finance_monitor._build_cash()
        self.assertEqual(result["totals"]["received_idr"], 170_000)
        self.assertEqual(result["totals"]["pending_label_idr"], 60_000)
        self.assertEqual(result["totals"]["paid_idr"], 50_000)
        self.assertIsNone(result["totals"]["latest_cash_idr"])
        self.assertEqual(result["conclusion"], "not_determinable")
        self.assertEqual(len(result["receipts"]), 2)


if __name__ == "__main__":
    unittest.main()
