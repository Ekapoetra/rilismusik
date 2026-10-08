"""Token wallet and Standard/Express/MAX release modes."""
import asyncio
import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch

import test_vercel_preview  # Configures offline environment before real router imports.
from fastapi import HTTPException
from mongomock_motor import AsyncMongoMockClient
from routes import tokens


SETTINGS = {**tokens.DEFAULT_SETTINGS}


class ModeDateTests(unittest.TestCase):
    def at(self, iso):  # WIB wall time
        return datetime.fromisoformat(iso + "+07:00").astimezone(timezone.utc)

    def test_working_days_skip_weekends(self):
        monday = self.at("2026-10-05T09:00:00")
        self.assertEqual(tokens.earliest_release_date("standard", SETTINGS, monday), date(2026, 10, 14))
        self.assertEqual(tokens.earliest_release_date("express", SETTINGS, monday), date(2026, 10, 12))
        self.assertEqual(tokens.earliest_release_date("max", SETTINGS, monday), date(2026, 10, 8))

    def test_max_friday_rule(self):
        self.assertEqual(tokens.earliest_release_date("max", SETTINGS, self.at("2026-10-09T11:59:00")), date(2026, 10, 11))
        self.assertIsNone(tokens.earliest_release_date("max", SETTINGS, self.at("2026-10-09T12:00:00")))
        self.assertEqual(tokens.earliest_release_date("express", SETTINGS, self.at("2026-10-09T15:00:00")), date(2026, 10, 16))

    def test_costs_per_track(self):
        self.assertEqual(tokens.mode_token_cost("standard", 4, SETTINGS), 0)
        self.assertEqual(tokens.mode_token_cost("express", 4, SETTINGS), 8)
        self.assertEqual(tokens.mode_token_cost("max", 1, SETTINGS), 3)


class WalletTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = AsyncMongoMockClient(tz_aware=True).test
        await self.db.token_wallets.create_index("account_id", unique=True)
        await self.db.token_ledger.create_index("key", unique=True)
        self.patch = patch.object(tokens, "db", self.db)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.label = {"id": "l1", "user_id": "u1"}

    async def credit(self, amount, key="purchase:p1"):
        return await tokens.apply_tokens(account_id="u1", label_id="l1", tokens=amount, kind="purchase", key=key)

    async def test_purchase_fulfillment_is_idempotent(self):
        await self.db.labels.insert_one(dict(self.label))
        payment = {"id": "p1", "label_id": "l1", "token_quantity": 5, "description": "5 token"}
        await tokens.fulfill_token_pack(payment)
        await tokens.fulfill_token_pack(payment)
        self.assertEqual(await tokens.wallet_balance("u1"), 5)
        self.assertEqual(await self.db.token_ledger.count_documents({"kind": "purchase"}), 1)

    async def test_debit_never_overdraws(self):
        await self.credit(3)
        with self.assertRaises(HTTPException) as raised:
            await tokens.apply_tokens(account_id="u1", label_id="l1", tokens=-4, kind="release_reserve", key="r:1")
        self.assertEqual(raised.exception.status_code, 402)
        self.assertEqual(await tokens.wallet_balance("u1"), 3)
        with self.assertRaises(HTTPException):
            await tokens.apply_tokens(account_id="nobody", label_id=None, tokens=-1, kind="release_reserve", key="r:2")

    async def test_concurrent_debits_cannot_both_spend(self):
        await self.credit(3)
        results = await asyncio.gather(*[tokens.apply_tokens(account_id="u1", label_id="l1", tokens=-2, kind="release_reserve", key=f"r:{i}") for i in range(2)], return_exceptions=True)
        self.assertEqual(sum(1 for item in results if item is True), 1)
        self.assertEqual(await tokens.wallet_balance("u1"), 1)

    async def test_resubmit_charges_difference_and_reject_refunds(self):
        await self.credit(10)
        release = {"id": "rel1", "label_id": "l1"}
        fields = await tokens.reserve_release_tokens(release, self.label, "express", 2, SETTINGS, "u1")
        self.assertEqual((fields["token_reserved"], fields["token_status"]), (4, "reserved"))
        self.assertEqual(await tokens.wallet_balance("u1"), 6)
        release.update(fields)
        fields = await tokens.reserve_release_tokens(release, self.label, "max", 2, SETTINGS, "u1")  # after revision
        self.assertEqual(await tokens.wallet_balance("u1"), 4)
        release.update(fields)
        refund = await tokens.refund_release_tokens(release, "admin", "Rilisan ditolak")
        self.assertEqual(refund["token_status"], "refunded")
        self.assertEqual(await tokens.wallet_balance("u1"), 10)
        release.update(refund)
        self.assertIsNone(await tokens.refund_release_tokens(release, "admin", "again"))

    async def test_switching_back_to_standard_returns_tokens(self):
        await self.credit(6)
        release = {"id": "rel2", "label_id": "l1"}
        release.update(await tokens.reserve_release_tokens(release, self.label, "max", 2, SETTINGS, "u1"))
        fields = await tokens.reserve_release_tokens(release, self.label, "standard", 2, SETTINGS, "u1")
        self.assertIsNone(fields["token_status"])
        self.assertEqual(await tokens.wallet_balance("u1"), 6)

    async def test_token_covered_release_skips_invoice(self):
        self.assertTrue(tokens.token_covers_release({"billing_flow": "token", "token_status": "reserved"}))
        self.assertFalse(tokens.token_covers_release({"billing_flow": "token", "token_status": "refunded"}))
        self.assertFalse(tokens.token_covers_release({"billing_flow": "pay_per_release"}))


if __name__ == "__main__":
    unittest.main()
