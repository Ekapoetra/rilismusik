"""V13 label account: reviewed identity changes and history."""
import unittest
from unittest.mock import AsyncMock, patch

import test_vercel_preview  # Configures offline environment before real router imports.
from fastapi import HTTPException
from mongomock_motor import AsyncMongoMockClient
from routes import label_account
from routes.label_account import ProfileChangeIn, ProfileChangeReviewIn


class LabelAccountTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = AsyncMongoMockClient(tz_aware=True).test
        self.label = {"id": "l1", "user_id": "u1", "label_name": "Senja", "pic_name": "Eka", "kyc_status": "verified"}
        await self.db.labels.insert_one(dict(self.label))
        await self.db.users.insert_one({"id": "u1", "email": "eka@senja.id"})
        self.user = {"id": "u1", "role": "label", "name": "Eka"}
        self.admin = {"id": "a1", "role": "super_admin", "name": "Admin"}
        self.patches = [patch.object(label_account, "db", self.db),
                        patch.object(label_account, "get_label_by_user", self.current_label),
                        patch.object(label_account, "log_activity", AsyncMock()), patch.object(label_account, "notify", AsyncMock()),
                        patch.object(label_account, "notify_many", AsyncMock()), patch.object(label_account, "admin_user_ids", AsyncMock(return_value=[]))]
        for item in self.patches:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in self.patches])

    async def current_label(self, user):
        return await self.db.labels.find_one({"id": "l1"}, {"_id": 0})

    async def test_name_change_waits_for_review_then_applies(self):
        result = await label_account.submit_profile_change(ProfileChangeIn(label_name="Senja Baru", pic_name="Eka"), self.user)
        request = result["request"]
        self.assertEqual((request["status"], request["after"]), ("pending", {"label_name": "Senja Baru"}))
        self.assertEqual((await self.db.labels.find_one({"id": "l1"}))["label_name"], "Senja")
        with self.assertRaises(HTTPException):
            await label_account.submit_profile_change(ProfileChangeIn(pic_name="Lain"), self.user)
        await label_account.review_profile_change(request["id"], ProfileChangeReviewIn(action="approve"), self.admin)
        self.assertEqual((await self.db.labels.find_one({"id": "l1"}))["label_name"], "Senja Baru")

    async def test_correction_needs_note_and_resubmit_replaces_it(self):
        request = (await label_account.submit_profile_change(ProfileChangeIn(pic_name="Eka Putra"), self.user))["request"]
        with self.assertRaises(HTTPException):
            await label_account.review_profile_change(request["id"], ProfileChangeReviewIn(action="correct"), self.admin)
        await label_account.review_profile_change(request["id"], ProfileChangeReviewIn(action="correct", note="Sesuaikan KTP"), self.admin)
        again = (await label_account.submit_profile_change(ProfileChangeIn(pic_name="Eka P."), self.user))["request"]
        self.assertEqual(again["status"], "pending")
        self.assertEqual((await self.db.label_profile_changes.find_one({"id": request["id"]}))["status"], "superseded")

    async def test_history_lists_release_events(self):
        await self.db.releases.insert_one({"id": "r1", "label_id": "l1", "release_title": "Ruang", "created_at": "2026-10-01T00:00:00+00:00",
                                           "updated_at": "2026-10-03", "status_history": [{"to": "submitted", "changed_by": "u1", "changed_at": "2026-10-02T00:00:00+00:00"},
                                                                                         {"to": "need_revision", "changed_by": "a1", "changed_at": "2026-10-03T00:00:00+00:00"}]})
        items = (await label_account.label_history(self.user))["items"]
        self.assertEqual([(i["name"], i["actor"]) for i in items[:3]], [("Perbaikan diminta", "Rilis Musik"), ("Pengajuan dikirim", "Anda"), ("Draft dibuat", "Anda")])


if __name__ == "__main__":
    unittest.main()
