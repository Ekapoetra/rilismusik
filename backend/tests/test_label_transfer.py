"""Offline regressions for label rename / merge / release move / sale."""
import asyncio
import unittest
from unittest.mock import AsyncMock, patch

import test_vercel_preview  # Configures offline environment before real router imports.
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from routes import (
    balance_utils, deps, financial_lock, label_transfer_service as service, label_transfers,
    royalty, royalty_adjustment_balance, withdraw,
)
from routes.label_transfer_service import LabelTransferDecisionIn, LabelTransferIn

OWNER = {"id": "owner", "role": "label", "name": "Pemilik"}
BUYER = {"id": "buyer", "role": "label", "name": "Pembeli"}
SUPER = {"id": "super", "role": "super_admin", "is_admin": True, "admin_role_active": True, "permissions": [], "name": "Super"}
SUPER_2 = {**SUPER, "id": "super-2", "name": "Super Dua"}
SUPPORT = {"id": "support", "role": "admin_custom", "admin_role_id": "r-support", "is_admin": True, "admin_role_active": True,
           "permissions": ["labels.view", "labels.manage"], "name": "Support"}
APPROVER = {"id": "approver", "role": "admin_custom", "admin_role_id": "r-approver", "is_admin": True, "admin_role_active": True,
            "permissions": ["labels.view", "labels.manage", "labels.transfer.approve"], "name": "Approver"}


def line(line_id, label_id, period, status, amount, release_id="r1", track_id="t1", **extra):
    return {"id": line_id, "label_id": label_id, "period": period, "status": status, "label_idr": amount,
            "release_id": release_id, "track_id": track_id, "legacy_settled": False, "match_status": "matched", **extra}


class LabelTransferTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = AsyncMongoMockClient().test
        targets = [(service, "db"), (service, "db_bg"), (label_transfers, "db"), (deps, "db"), (financial_lock, "db"),
                   (balance_utils, "db_bg"), (royalty_adjustment_balance, "db_bg")]
        self.patches = [patch.object(module, name, self.db) for module, name in targets]
        self.patches.append(patch.object(service, "_refresh_analytics", new_callable=AsyncMock))
        for item in self.patches:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in self.patches])
        await self.db.users.insert_many([
            {"id": "owner", "role": "label", "active_label_id": "pel"}, {"id": "buyer", "role": "label"},
            {"id": "super", "role": "super_admin"}, {"id": "super-2", "role": "super_admin"},
        ])
        await self.db.labels.insert_many([
            {"id": "pel", "user_id": "owner", "label_name": "Pelpendo", "last_withdrawn_period": "2026-03"},
            {"id": "elf", "user_id": "owner", "label_name": "Elfnon", "last_withdrawn_period": "2026-05"},
            {"id": "buy", "user_id": "buyer", "label_name": "Pembeli Records", "last_withdrawn_period": None},
            {"id": "ghost", "user_id": None, "label_name": "Label Lama", "legacy_import": True},
        ])
        await self.db.releases.insert_many([
            {"id": "r1", "label_id": "pel", "release_title": "Satu", "upc": "111"},
            {"id": "r2", "label_id": "pel", "release_title": "Dua", "upc": "222"},
            {"id": "re", "label_id": "elf", "release_title": "Elf", "upc": "999"},
        ])
        await self.db.tracks.insert_many([
            {"id": "t1", "release_id": "r1", "label_id": "pel", "isrc": "IDA000000001", "artist_id": "a1"},
            {"id": "t2", "release_id": "r2", "label_id": "pel", "isrc": "IDA000000002", "artist_id": "a2"},
        ])
        await self.db.artists.insert_many([
            {"id": "a1", "label_id": "pel", "name": "Artis Satu"}, {"id": "a2", "label_id": "pel", "name": "Artis Dua", "user_id": "artist-login"},
        ])
        await self.db.royalty_lines.insert_many([
            line("old", "pel", "2026-02", "withdrawn", 5_000),       # paid history stays
            line("conflict", "pel", "2026-04", "available", 1_000),  # target already settled 2026-05
            line("new", "pel", "2026-06", "available", 2_000, release_id="r2", track_id="t2"),
            line("pending", "pel", "2026-07", "pending", 500),
            line("elf-own", "elf", "2026-06", "available", 400, release_id="re", track_id="te"),
        ])
        await self.db.balance_transactions.insert_one({
            "id": "AJ-1", "label_id": "pel", "type": royalty_adjustment_balance.ADJUSTMENT_TYPE,
            "source": "ADMIN_ADJUSTMENT", "status": "active", "amount_idr": 300,
        })

    async def balance(self, label_id):
        snapshot = await balance_utils.compute_label_balance_snapshot(label_id=label_id)
        return snapshot["balance_available_idr"], snapshot["balance_pending_idr"]

    async def create(self, actor, kind="admin", **body):
        payload = LabelTransferIn(reason="Pindah sesuai Believe", **body)
        doc = await service.build_transfer_request(payload, actor=actor, actor_kind=kind)
        await self.db.label_transfers.insert_one(dict(doc))
        return doc

    async def approve_and_apply(self, doc, actor=SUPER):
        await self.db.label_transfers.update_one({"id": doc["id"]}, {"$set": {"status": "approved", "decided_by": actor["id"]}})
        return await service.apply_transfer(doc["id"], actor)

    async def test_rename_keeps_label_and_answers_to_old_name(self):
        doc = await self.create(SUPER, mode="rename", source_label_id="pel", new_name="Elfnon Baru")
        result = await self.approve_and_apply(doc)
        self.assertEqual(result["status"], "completed")
        label = await self.db.labels.find_one({"id": "pel"})
        self.assertEqual(label["label_name"], "Elfnon Baru")
        self.assertEqual([alias["name"] for alias in label["label_name_aliases"]], ["Pelpendo"])
        index = royalty._label_name_index({item["id"]: item async for item in self.db.labels.find({}, {"_id": 0})})
        self.assertEqual(index["pelpendo"]["id"], "pel")
        self.assertEqual(index["elfnon baru"]["id"], "pel")
        self.assertEqual(await self.balance("pel"), (3_300, 500))

    async def test_rename_refuses_names_in_use(self):
        with self.assertRaises(HTTPException) as ctx:
            await self.create(SUPER, mode="rename", source_label_id="pel", new_name="  elfnon ")
        self.assertEqual(ctx.exception.status_code, 409)
        with self.assertRaises(HTTPException) as ctx:
            await self.create(SUPER, mode="rename", source_label_id="pel", new_name="Label Lama")
        self.assertIn("belum diklaim", ctx.exception.detail)

    async def test_merge_moves_unwithdrawn_balance_without_losing_or_doubling(self):
        before = [await self.balance("pel"), await self.balance("elf")]
        self.assertEqual(before, [(3_300, 500), (400, 0)])
        doc = await self.create(OWNER, kind="label", mode="merge", source_label_id="pel", target_label_id="elf")
        result = await self.approve_and_apply(doc)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(await self.balance("pel"), (0, 0))
        # 400 own + 2,000 moved + 1,000 settled-period credit + 300 adjustment; pending follows too.
        self.assertEqual(await self.balance("elf"), (3_700, 500))
        moved = {item["id"]: item["label_id"] async for item in self.db.royalty_lines.find({})}
        self.assertEqual(moved, {"old": "pel", "conflict": "elf", "new": "elf", "pending": "elf", "elf-own": "elf"})
        self.assertEqual(await self.db.releases.count_documents({"label_id": "elf"}), 3)
        self.assertEqual(await self.db.artists.count_documents({"label_id": "elf"}), 2)
        source = await self.db.labels.find_one({"id": "pel"})
        target = await self.db.labels.find_one({"id": "elf"})
        self.assertEqual(source["merged_into_label_id"], "elf")
        self.assertNotIn("transfer_in_progress_id", source)
        self.assertEqual(target["label_name_aliases"][0]["name"], "Pelpendo")
        self.assertEqual((await self.db.users.find_one({"id": "owner"}))["active_label_id"], "elf")
        index = royalty._label_name_index({item["id"]: item async for item in self.db.labels.find({}, {"_id": 0})})
        self.assertEqual(index["pelpendo"]["id"], "elf")

    async def test_interrupted_merge_resumes_without_double_counting(self):
        doc = await self.create(SUPER, mode="merge", source_label_id="pel", target_label_id="elf")
        original = service._journal
        calls = {"n": 0}

        async def flaky(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("koneksi putus")
            return await original(*args, **kwargs)

        with patch.object(service, "_journal", flaky):
            with self.assertRaises(HTTPException):
                await self.approve_and_apply(doc)
        stored = await self.db.label_transfers.find_one({"id": doc["id"]})
        self.assertEqual(stored["status"], "failed")
        # Lines moved but the credit is missing: money is hidden, never doubled.
        self.assertLessEqual(sum([(await self.balance("pel"))[0], (await self.balance("elf"))[0]]), 3_700)
        self.assertTrue((await self.db.labels.find_one({"id": "pel"})).get("transfer_in_progress_id"))
        result = await service.apply_transfer(doc["id"], SUPER)
        self.assertEqual(result["status"], "completed")
        self.assertEqual([await self.balance("pel"), await self.balance("elf")], [(0, 0), (3_700, 500)])

    async def test_unsafe_states_are_refused(self):
        await self.db.royalty_lines.insert_one(line("draft", "pel", "2026-05", "draft", 50))
        doc = await self.create(SUPER, mode="merge", source_label_id="pel", target_label_id="elf")
        with self.assertRaises(HTTPException) as ctx:
            await service.build_plan(doc)
        self.assertEqual(ctx.exception.status_code, 409)
        await self.db.royalty_lines.delete_one({"id": "draft"})
        await self.db.withdraw_requests.insert_one({"id": "w1", "label_id": "elf", "status": "requested"})
        with self.assertRaises(HTTPException) as ctx:
            await service.build_plan(doc)
        self.assertIn("withdraw", ctx.exception.detail)

    async def test_failed_planning_moves_nothing_and_reopens_withdrawals(self):
        doc = await self.create(SUPER, mode="merge", source_label_id="pel", target_label_id="elf")
        await self.db.withdraw_requests.insert_one({"id": "w1", "label_id": "pel", "status": "requested"})
        with self.assertRaises(HTTPException):
            await self.approve_and_apply(doc)
        stored = await self.db.label_transfers.find_one({"id": doc["id"]})
        self.assertEqual((stored["status"], stored.get("plan")), ("approved", None))
        self.assertIsNone((await self.db.labels.find_one({"id": "pel"})).get("transfer_in_progress_id"))

    async def test_selected_releases_move_only_their_royalties(self):
        doc = await self.create(OWNER, kind="label", mode="releases", source_label_id="pel", target_label_id="elf", release_ids=["r2"])
        await self.approve_and_apply(doc)
        self.assertEqual((await self.db.releases.find_one({"id": "r2"}))["label_id"], "elf")
        self.assertEqual((await self.db.releases.find_one({"id": "r1"}))["label_id"], "pel")
        self.assertEqual(await self.balance("pel"), (1_300, 500))
        self.assertEqual(await self.balance("elf"), (2_400, 0))
        self.assertIsNone((await self.db.labels.find_one({"id": "pel"})).get("merged_into_label_id"))

    async def test_same_account_modes_require_same_owner(self):
        with self.assertRaises(HTTPException) as ctx:
            await self.create(OWNER, kind="label", mode="merge", source_label_id="pel", target_label_id="buy")
        self.assertEqual(ctx.exception.status_code, 400)
        with self.assertRaises(HTTPException) as ctx:
            await self.create(BUYER, kind="label", mode="rename", source_label_id="pel", new_name="Curian")
        self.assertEqual(ctx.exception.status_code, 403)

    async def test_sale_is_admin_only_and_needs_another_super_admin(self):
        with self.assertRaises(HTTPException) as ctx:
            await self.create(OWNER, kind="label", mode="sale", source_label_id="pel", target_label_id="buy",
                              effective_period="2026-07", reference="AJB-1")
        self.assertEqual(ctx.exception.status_code, 403)
        with self.assertRaises(HTTPException):
            await self.create(SUPER, mode="sale", source_label_id="pel", target_label_id="buy", effective_period="2026-07")
        doc = await self.create(SUPER, mode="sale", source_label_id="pel", target_label_id="buy",
                                effective_period="2026-07", reference="AJB-1", carry_balance=False)
        self.assertFalse(service.can_apply_directly(SUPER, "sale"))
        self.assertFalse(service.can_decide(SUPER, doc))
        self.assertFalse(service.can_decide(APPROVER, doc))
        self.assertTrue(service.can_decide(SUPER_2, doc))
        await self.approve_and_apply(doc, SUPER_2)
        # Earnings before the sale stay with the seller; 2026-07 onwards go to the buyer.
        self.assertEqual(await self.balance("pel"), (3_300, 0))
        self.assertEqual(await self.balance("buy"), (0, 500))
        self.assertEqual(await self.db.artists.count_documents({"label_id": "buy"}), 1)  # artist login stays
        self.assertIsNone((await self.db.tracks.find_one({"id": "t2"}))["artist_id"])  # seller's artist detached
        self.assertEqual((await self.db.tracks.find_one({"id": "t1"}))["artist_id"], "a1")
        routes = service.sale_routes([await self.db.label_transfers.find_one({"id": doc["id"]}, {"_id": 0})])
        self.assertEqual(service.owner_for_period(routes, "isrc", "ida000000001", "2026-06"), "pel")
        self.assertIsNone(service.owner_for_period(routes, "isrc", "IDA000000001", "2026-07"))
        self.assertEqual(service.owner_for_period(routes, "upc", "222", "2026-01"), "pel")

    async def test_sale_request_alerts_both_owners_before_anything_moves(self):
        doc = await self.create(SUPPORT, mode="sale", source_label_id="pel", target_label_id="buy",
                                effective_period="2026-07", reference="AJB-1")
        await service.notify_submitted(doc)
        alerted = sorted([item["user_id"] async for item in self.db.notifications.find({"type": "label_transfer_sale_pending"})])
        self.assertEqual(alerted, ["buyer", "owner"])
        approvers = sorted([item["user_id"] async for item in self.db.notifications.find({"type": "label_transfer_request"})])
        self.assertEqual(approvers, ["super", "super-2"])
        self.assertEqual((await self.db.releases.find_one({"id": "r1"}))["label_id"], "pel")

    async def test_decision_rules_for_requests(self):
        doc = await self.create(SUPPORT, mode="merge", source_label_id="pel", target_label_id="elf")
        self.assertFalse(service.can_decide(SUPPORT, doc))
        self.assertTrue(service.can_decide(APPROVER, doc))
        own = {**doc, "requested_by": "approver"}
        self.assertFalse(service.can_decide(APPROVER, own))
        self.assertTrue(service.can_decide(SUPER, {**doc, "requested_by": "super"}))
        with self.assertRaises(HTTPException) as ctx:
            await self.create(SUPER, mode="rename", source_label_id="elf", new_name="Elfnon Dua")
        self.assertEqual(ctx.exception.status_code, 409)  # one open transfer per label

    async def test_withdrawal_is_closed_while_transfer_runs(self):
        await self.db.labels.update_one({"id": "pel"}, {"$set": {"transfer_in_progress_id": "x"}})
        label = await self.db.labels.find_one({"id": "pel"}, {"_id": 0})
        with patch.object(withdraw, "withdraw_window_state", return_value={"request_open": True, "message": ""}):
            with self.assertRaises(HTTPException) as ctx:
                await withdraw._create_label_withdrawal(label, OWNER)
        self.assertEqual(ctx.exception.status_code, 409)


class LabelTransferHttpTests(unittest.TestCase):
    def setUp(self):
        self.db = AsyncMongoMockClient().test
        db_patch = patch.object(label_transfers, "db", self.db)
        db_patch.start()
        self.addCleanup(db_patch.stop)
        app = FastAPI()
        app.include_router(label_transfers.label_transfer_r, prefix="/api")
        self.user = SUPPORT
        app.dependency_overrides[deps.get_current_user] = lambda: self.user
        self.client = TestClient(app)

    def test_admin_decision_requires_believe_confirmation(self):
        doc = {"id": "t1", "mode": "merge", "requested_by": "support", "status": "pending", "source_label_id": "pel"}
        asyncio.run(self.db.label_transfers.insert_one(doc))
        self.user = APPROVER
        response = self.client.post("/api/admin/label-transfers/t1/decision", json={"action": "approve"})
        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("Believe", response.json()["detail"])

    def test_admin_without_manage_cannot_create(self):
        self.user = {**SUPPORT, "permissions": ["labels.view"]}
        response = self.client.post("/api/admin/label-transfers", json={
            "mode": "rename", "source_label_id": "pel", "new_name": "Baru", "reason": "Ganti nama"})
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
