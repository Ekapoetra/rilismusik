"""D13 - Maintenance windows (Super Admin CRUD + member-facing /active)."""
import asyncio
import os
import unittest
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.update({
    "MONGO_URL": "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=100",
    "DB_NAME": "maintenance_test",
    "JWT_SECRET": "test-only-unused-jwt-secret",
    "UPLOAD_DIR": "/tmp/rilismusik-test-uploads",
})

from fastapi.testclient import TestClient
import server
from server import app
from routes.deps import get_current_user
import routes.maintenance_windows as mw


class _Cursor:
    def __init__(self, rows):
        self._rows = list(rows)

    def sort(self, key, direction=-1):
        self._rows.sort(key=lambda r: r.get(key) or "", reverse=direction < 0)
        return self

    async def to_list(self, limit):
        return self._rows[:limit]


class _FakeCollection:
    def __init__(self):
        self.docs = []

    def find(self, query=None, projection=None):
        return _Cursor(self.docs)

    async def find_one(self, query, projection=None):
        return next((d for d in self.docs if all(d.get(k) == v for k, v in query.items())), None)

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def update_one(self, query, update):
        doc = await self.find_one(query)
        if not doc:
            return
        doc.update(update.get("$set", {}))
        for key, value in (update.get("$push") or {}).items():
            doc.setdefault(key, []).append(value)


SUPER = {"id": "super-1", "role": "super_admin", "name": "Super"}
LABEL = {"id": "label-1", "role": "label", "name": "Label"}

WINDOW = {
    "title": "Peningkatan sistem pembayaran",
    "kind": "scheduled", "mode": "info",
    "start_at": "2026-09-28T02:00:00+00:00", "end_at": "2026-09-28T04:00:00+00:00",
    "modules": ["payments"], "message": "Pembayaran ditutup sementara.",
    "notify": "24h", "note": None,
}


class MaintenanceWindowTests(unittest.TestCase):
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

    def setUp(self):
        self.coll = _FakeCollection()
        self._db = patch.object(mw, "db", SimpleNamespace(maintenance_windows=self.coll))
        self._db.start()
        self._log = patch.object(mw, "log_activity", new_callable=AsyncMock)
        self._log.start()
        app.dependency_overrides[get_current_user] = lambda: SUPER

    def tearDown(self):
        self._db.stop()
        self._log.stop()
        app.dependency_overrides.clear()

    # ---- pure helpers ----
    def test_effective_status_manual_overrides_time(self):
        w = dict(WINDOW, status="active")
        self.assertEqual(mw.effective_status(w), "active")
        w["status"] = "cancelled"
        self.assertEqual(mw.effective_status(w), "cancelled")

    def test_effective_status_derived_from_time(self):
        from datetime import datetime, timezone
        w = dict(WINDOW, status="scheduled")
        before = datetime(2026, 9, 27, tzinfo=timezone.utc)
        during = datetime(2026, 9, 28, 3, tzinfo=timezone.utc)
        after = datetime(2026, 9, 29, tzinfo=timezone.utc)
        self.assertEqual(mw.effective_status(w, before), "scheduled")
        self.assertEqual(mw.effective_status(w, during), "active")
        self.assertEqual(mw.effective_status(w, after), "completed")

    def test_visibility_respects_notify_lead(self):
        from datetime import datetime, timezone
        w = dict(WINDOW, status="scheduled")
        early = datetime(2026, 9, 26, tzinfo=timezone.utc)
        inside_lead = datetime(2026, 9, 27, 3, tzinfo=timezone.utc)
        self.assertFalse(mw._visible(w, early))     # >24h sebelum mulai
        self.assertTrue(mw._visible(w, inside_lead))  # dalam 24h
        w["notify"] = "none"
        self.assertFalse(mw._visible(w, inside_lead))

    # ---- endpoints ----
    def test_create_list_and_label_visibility(self):
        body = dict(WINDOW)
        body["start_at"] = "2099-01-01T00:00:00+00:00"
        body["end_at"] = "2099-01-01T02:00:00+00:00"
        r = self.client.post("/api/admin/maintenance", json=body)
        self.assertEqual(r.status_code, 200, r.text)
        wid = r.json()["id"]
        self.assertTrue(wid.startswith("MW-"))

        r = self.client.get("/api/admin/maintenance")
        self.assertEqual(len(r.json()["windows"]), 1)
        self.assertEqual(r.json()["windows"][0]["effective_status"], "scheduled")

        # belum dalam masa pengumuman -> label tidak melihat apa pun
        r = self.client.get("/api/maintenance/active")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["windows"], [])

        # paksa aktif -> banner tampil untuk member (peran apapun yang login)
        r = self.client.post(f"/api/admin/maintenance/{wid}/status", json={"status": "active"})
        self.assertEqual(r.status_code, 200, r.text)
        app.dependency_overrides[get_current_user] = lambda: LABEL
        r = self.client.get("/api/maintenance/active")
        wins = r.json()["windows"]
        self.assertEqual(len(wins), 1)
        self.assertEqual(wins[0]["status"], "active")
        self.assertEqual(wins[0]["message"], "Pembayaran ditutup sementara.")

    def test_validation_and_auth(self):
        bad = dict(WINDOW, start_at="2026-09-28T04:00:00+00:00", end_at="2026-09-28T02:00:00+00:00")
        r = self.client.post("/api/admin/maintenance", json=bad)
        self.assertEqual(r.status_code, 400)

        app.dependency_overrides[get_current_user] = lambda: LABEL
        r = self.client.post("/api/admin/maintenance", json=WINDOW)
        self.assertEqual(r.status_code, 403)
        app.dependency_overrides[get_current_user] = lambda: SUPER

    def test_patch_and_audit(self):
        r = self.client.post("/api/admin/maintenance", json=WINDOW)
        wid = r.json()["id"]
        r = self.client.patch(f"/api/admin/maintenance/{wid}", json={"message": "Pesan baru."})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["message"], "Pesan baru.")
        self.assertTrue(any(h["action"] == "updated" for h in r.json()["history"]))
        self._log.mock.assert_called()


if __name__ == "__main__":
    unittest.main()
