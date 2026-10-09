"""D10 - Staff signals: queue-vs-capacity metrics + read-only staff preview context."""
import os
import re
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.update({
    "MONGO_URL": "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=100",
    "DB_NAME": "staff_signal_test",
    "JWT_SECRET": "test-only-unused-jwt-secret",
    "UPLOAD_DIR": "/tmp/rilismusik-test-uploads",
})

from fastapi.testclient import TestClient
import server
from server import app
from routes.deps import get_current_user
import routes.work_service as work_route
import routes.admin as admin_route


def _match(doc, key, cond):
    value = doc.get(key)
    if not isinstance(cond, dict):
        return value == cond
    if "$ne" in cond and value == cond["$ne"]:
        return False
    if "$nin" in cond and value in cond["$nin"]:
        return False
    if "$in" in cond and value not in cond["$in"]:
        return False
    if "$exists" in cond and (key in doc) != bool(cond["$exists"]):
        return False
    if "$regex" in cond:
        flags = re.I if "i" in (cond.get("$options") or "") else 0
        if not re.search(cond["$regex"], value or "", flags):
            return False
    return True


def _query(doc, q):
    for key, cond in (q or {}).items():
        if key == "$or":
            if not any(_query(doc, branch) for branch in cond):
                return False
        elif key == "$and":
            if not all(_query(doc, branch) for branch in cond):
                return False
        elif not _match(doc, key, cond):
            return False
    return True


class _Cursor:
    def __init__(self, rows):
        self._rows = list(rows)

    def sort(self, key, direction=-1):
        self._rows.sort(key=lambda r: r.get(key) or "", reverse=direction < 0)
        return self

    def limit(self, n):
        self._rows = self._rows[:n]
        return self

    async def to_list(self, limit):
        return self._rows[:limit] if limit else self._rows

    def __aiter__(self):
        async def gen():
            for row in self._rows:
                yield row
        return gen()


class _FakeCollection:
    def __init__(self):
        self.docs = []

    def find(self, query=None, projection=None):
        return _Cursor([d for d in self.docs if _query(d, query)])

    async def find_one(self, query, projection=None):
        return next((d for d in self.docs if _query(d, query)), None)


SUPER = {"id": "super-1", "role": "super_admin", "name": "Super", "email": "super@test"}
STAFF = {"id": "st-1", "role": "admin_support", "admin_role_id": "role-support",
         "name": "Staff Satu", "email": "st@test", "status": "active"}
OLD = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()


def _db(**colls):
    return SimpleNamespace(**colls)


class StaffSignalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bootstrap = patch.object(server, "_bootstrap_async", new_callable=AsyncMock)
        cls.bootstrap.start()
        cls.context = TestClient(app)
        cls.client = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)
        cls.bootstrap.stop()

    def _db_patch(self):
        self.roles = _FakeCollection()
        self.roles.docs = [
            {"id": "role-support", "key": "admin_support", "name": "Support",
             "permissions": ["support.view"], "active": True},
        ]
        self.users = _FakeCollection()
        self.users.docs = [dict(STAFF)]
        self.work_items = _FakeCollection()
        self.work_items.docs = [
            {"id": "w1", "work_type": "kyc_review", "status": "open", "opened_at": OLD},
            {"id": "w2", "work_type": "support_ticket", "status": "open",
             "opened_at": datetime.now(timezone.utc).isoformat()},
        ]
        self.ui_settings = _FakeCollection()
        return _db(admin_roles=self.roles, users=self.users,
                   work_items=self.work_items, admin_ui_settings=self.ui_settings)

    def setUp(self):
        self._work_db = patch.object(work_route, "db", self._db_patch())
        self._work_db.start()
        patch.object(work_route, "work_read_synchronization", new_callable=AsyncMock,
                     return_value={"synchronizing": False}).start()

    def tearDown(self):
        patch.stopall()
        app.dependency_overrides.clear()

    # ---------- Queue staffing signal ----------
    def test_staff_count_and_needs_staff(self):
        app.dependency_overrides[get_current_user] = lambda: SUPER
        r = self.client.get("/api/admin/work/queue?scope=all")
        self.assertEqual(r.status_code, 200, r.text)
        d = r.json()
        mine = {i["work_type"]: i for i in d["items"]}        # super's My Work = non-delegated
        team = {i["work_type"]: i for i in d["team_items"]}   # delegated work
        # kyc_review has an open item but no staff holds kyc.review -> super's queue, needs_staff
        self.assertEqual(mine["kyc_review"]["staff_count"], 0)
        self.assertTrue(mine["kyc_review"]["needs_staff"])
        # support_ticket is covered by one active staff -> delegated (team), staffed
        self.assertEqual(team["support_ticket"]["staff_count"], 1)
        self.assertFalse(team["support_ticket"]["needs_staff"])

    def test_strained_when_overdue_and_single_staff(self):
        # single staff holds support.view; make the open ticket overdue
        self.work_items.docs[1]["opened_at"] = OLD
        app.dependency_overrides[get_current_user] = lambda: SUPER
        r = self.client.get("/api/admin/work/queue?scope=team")
        self.assertEqual(r.status_code, 200, r.text)
        items = {i["work_type"]: i for i in r.json()["items"]}
        self.assertEqual(items["support_ticket"]["staff_count"], 1)
        self.assertTrue(items["support_ticket"]["strained"])
        # a second active staff with the same permission relieves the strain flag
        self.users.docs.append({"id": "st-2", "role": "admin_support",
                                "admin_role_id": "role-support", "status": "active"})
        r = self.client.get("/api/admin/work/queue?scope=team")
        items = {i["work_type"]: i for i in r.json()["items"]}
        self.assertEqual(items["support_ticket"]["staff_count"], 2)
        self.assertFalse(items["support_ticket"]["strained"])

    def test_inactive_role_grants_no_coverage(self):
        self.roles.docs[0]["active"] = False
        app.dependency_overrides[get_current_user] = lambda: SUPER
        r = self.client.get("/api/admin/work/queue?scope=all")
        self.assertEqual(r.status_code, 200, r.text)
        d = r.json()
        # role inactive -> permission not delegated -> falls to super's My Work
        items = {i["work_type"]: i for i in d["items"] + d["team_items"]}
        self.assertEqual(items["support_ticket"]["staff_count"], 0)
        self.assertTrue(items["support_ticket"]["needs_staff"])

    # ---------- Preview context ----------
    def test_preview_context_returns_resolved_permissions(self):
        users = _FakeCollection(); users.docs = [dict(STAFF)]
        roles = _FakeCollection(); roles.docs = [
            {"id": "role-support", "key": "admin_support", "name": "Support",
             "permissions": ["support.view", "tickets.handle"], "active": True},
        ]
        patch.object(admin_route, "db", _db(users=users, admin_roles=roles)).start()
        patch.object(admin_route, "log_activity", new_callable=AsyncMock).start()
        app.dependency_overrides[get_current_user] = lambda: SUPER
        r = self.client.get("/api/admin/admin-users/st-1/preview-context")
        self.assertEqual(r.status_code, 200, r.text)
        d = r.json()
        self.assertEqual(d["permissions"], ["support.view", "tickets.handle"])
        self.assertEqual(d["role_name"], "Support")
        admin_route.log_activity.assert_awaited()

    def test_preview_requires_super(self):
        app.dependency_overrides[get_current_user] = lambda: dict(STAFF)
        r = self.client.get("/api/admin/admin-users/st-1/preview-context")
        self.assertEqual(r.status_code, 403)

    def test_preview_rejects_super_and_disabled(self):
        users = _FakeCollection()
        users.docs = [dict(SUPER), {**STAFF, "id": "st-9", "status": "disabled"}]
        patch.object(admin_route, "db", _db(users=users, admin_roles=_FakeCollection())).start()
        patch.object(admin_route, "log_activity", new_callable=AsyncMock).start()
        app.dependency_overrides[get_current_user] = lambda: SUPER
        self.assertEqual(self.client.get("/api/admin/admin-users/super-1/preview-context").status_code, 400)
        self.assertEqual(self.client.get("/api/admin/admin-users/st-9/preview-context").status_code, 400)
        self.assertEqual(self.client.get("/api/admin/admin-users/nobody/preview-context").status_code, 404)


if __name__ == "__main__":
    unittest.main()
