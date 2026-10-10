"""System115 — versioned system settings: draft/discard/restore/publish,
optimistic concurrency, audit redaction, content publish applying onto
landing_settings, procedures cache refresh."""
import os
import unittest
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.update({
    "MONGO_URL": "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=100",
    "DB_NAME": "system_settings_test",
    "JWT_SECRET": "test-only-unused-jwt-secret",
    "UPLOAD_DIR": "/tmp/rilismusik-test-uploads",
})

from fastapi.testclient import TestClient
import server
from server import app
from routes.deps import get_current_user
import routes.system_settings as sys_mod
import routes.cms as cms_mod
import procedures_config


def _match(doc, key, cond):
    value = doc.get(key)
    if not isinstance(cond, dict):
        return value == cond
    if "$ne" in cond and value == cond["$ne"]:
        return False
    if "$in" in cond and value not in cond["$in"]:
        return False
    return True


def _query(doc, q):
    return all(_match(doc, k, c) for k, c in (q or {}).items())


class _Cursor:
    def __init__(self, rows):
        self._rows = list(rows)

    def sort(self, key, direction=-1):
        self._rows.sort(key=lambda r: r.get(key) or "", reverse=direction < 0)
        return self

    async def to_list(self, limit):
        return self._rows if limit is None else self._rows[:limit]


class _FakeCollection:
    def __init__(self):
        self.docs = []

    def find(self, query=None, projection=None):
        return _Cursor([d for d in self.docs if _query(d, query)])

    async def find_one(self, query, projection=None, sort=None):
        rows = [d for d in self.docs if _query(d, query)]
        return rows[0] if rows else None

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def update_one(self, query, update, upsert=False, **kw):
        doc = await self.find_one(query)
        if not doc:
            if not upsert:
                return SimpleNamespace(modified_count=0, upserted_id=None)
            doc = {k: v for k, v in (query or {}).items() if not k.startswith("$")}
            doc.update(update.get("$set", {}))
            doc.update(update.get("$setOnInsert", {}))
            for key, value in (update.get("$inc") or {}).items():
                doc[key] = (doc.get(key) or 0) + value
            self.docs.append(doc)
            return SimpleNamespace(modified_count=0, upserted_id="new")
        doc.update(update.get("$set", {}))
        for key, value in (update.get("$inc") or {}).items():
            doc[key] = (doc.get(key) or 0) + value
        return SimpleNamespace(modified_count=1, upserted_id=None)

    async def delete_one(self, query):
        before = len(self.docs)
        self.docs = [d for d in self.docs if not _query(d, query)]
        return SimpleNamespace(deleted_count=before - len(self.docs))

    async def count_documents(self, query):
        return sum(1 for d in self.docs if _query(d, query))


SUPER = {"id": "adm-1", "role": "super_admin", "name": "Super", "email": "s@t"}
STAFF = {"id": "adm-2", "role": "admin_content", "name": "Staff", "email": "x@t",
         "permissions": ["cms.view", "cms.manage"], "admin_role_active": True}
LABEL = {"id": "u-1", "role": "label", "name": "Label", "email": "l@t"}


def _db(**colls):
    return SimpleNamespace(**colls)


class SystemSettingsTests(unittest.TestCase):
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
        self.landing = _FakeCollection()
        self.landing.docs = [
            {"key": "hero", "value": {"title": "Judul Lama"}},
            {"key": "general", "value": {"brand_name": "RILIS"}},
        ]
        self.settings = _FakeCollection()
        self.audit = _FakeCollection()
        fake = _db(landing_settings=self.landing, system_settings=self.settings,
                   system_audit=self.audit, activity_logs=_FakeCollection())
        patch.object(sys_mod, "db", fake).start()
        patch.object(cms_mod, "db", fake).start()
        patch.object(cms_mod, "log_activity", new_callable=AsyncMock).start()
        procedures_config.set_published({})  # reset cache to defaults

    def tearDown(self):
        patch.stopall()
        app.dependency_overrides.clear()
        procedures_config.set_published({})

    def _as(self, user):
        app.dependency_overrides[get_current_user] = lambda: user

    def _detail(self, area="content"):
        r = self.client.get(f"/api/admin/system/{area}")
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    # ---------- ACL ----------
    def test_super_only(self):
        self._as(LABEL)
        self.assertEqual(self.client.get("/api/admin/system/areas").status_code, 403)
        self.assertEqual(self.client.get("/api/admin/system/content").status_code, 403)
        self._as(STAFF)
        # staff (non-super) also blocked — prototype guard is super-only
        self.assertEqual(self.client.get("/api/admin/system/content").status_code, 403)
        self._as(SUPER)
        r = self.client.get("/api/admin/system/areas")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual({a["area"] for a in r.json()["areas"]}, {"content", "procedures"})

    def test_unknown_area_404(self):
        self._as(SUPER)
        self.assertEqual(self.client.get("/api/admin/system/navigation").status_code, 404)

    # ---------- content draft → publish ----------
    def test_content_draft_publish_cycle(self):
        self._as(SUPER)
        d = self._detail()
        self.assertEqual(d["published"]["hero"], {"title": "Judul Lama"})
        self.assertIsNone(d["draft"])

        draft_map = {"hero": {"title": "Judul Baru"}, "general": {"brand_name": "RILIS"},
                     "seo": {"desc": "baru"}}
        r = self.client.post("/api/admin/system/content/draft",
                             json={"value": draft_map, "version": 0, "draft_version": 0})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["draft"], draft_map)
        # published untouched while drafting
        self.assertEqual(self._detail()["published"]["hero"], {"title": "Judul Lama"})

        r = self.client.post("/api/admin/system/content/publish",
                             json={"note": "ubah hero", "version": 0, "draft_version": 1})
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual(body["version"], 1)
        self.assertIsNone(body["draft"])
        self.assertEqual(body["published"]["hero"], {"title": "Judul Baru"})
        # public store updated: upsert seo, keep general, hero replaced
        by_key = {x["key"]: x["value"] for x in self.landing.docs}
        self.assertEqual(by_key["hero"], {"title": "Judul Baru"})
        self.assertEqual(by_key["seo"], {"desc": "baru"})
        # history holds the previous published map
        self.assertEqual(body["history"][0]["value"]["hero"], {"title": "Judul Lama"})
        self.assertTrue(any(e["kind"] == "publish" for e in self.audit.docs))

    def test_concurrency_conflict(self):
        self._as(SUPER)
        self.client.post("/api/admin/system/content/draft",
                         json={"value": {"hero": {"title": "A"}}, "version": 0, "draft_version": 0})
        # stale version token
        r = self.client.post("/api/admin/system/content/draft",
                             json={"value": {"hero": {"title": "B"}}, "version": 9, "draft_version": 9})
        self.assertEqual(r.status_code, 409)

    def test_publish_requires_draft_and_note(self):
        self._as(SUPER)
        self.assertEqual(self.client.post("/api/admin/system/content/publish",
                                          json={"note": "catatan", "version": 0, "draft_version": 0}).status_code, 409)
        self.assertEqual(self.client.post("/api/admin/system/content/publish",
                                          json={"note": "", "version": 0, "draft_version": 0}).status_code, 422)

    def test_publish_no_changes_409(self):
        self._as(SUPER)
        same = {"hero": {"title": "Judul Lama"}, "general": {"brand_name": "RILIS"}}
        self.client.post("/api/admin/system/content/draft",
                         json={"value": same, "version": 0, "draft_version": 0})
        r = self.client.post("/api/admin/system/content/publish",
                             json={"note": "sama", "version": 0, "draft_version": 1})
        self.assertEqual(r.status_code, 409)

    def test_discard_and_restore(self):
        self._as(SUPER)
        self.client.post("/api/admin/system/content/draft",
                         json={"value": {"hero": {"title": "Baru"}, "general": {"brand_name": "RILIS"}},
                               "version": 0, "draft_version": 0})
        d = self.client.post("/api/admin/system/content/discard",
                             json={"version": 0, "draft_version": 1})
        self.assertIsNone(d.json()["draft"])
        # publish once to create a history entry
        self.client.post("/api/admin/system/content/draft",
                         json={"value": {"hero": {"title": "V1"}, "general": {"brand_name": "RILIS"}},
                               "version": 0, "draft_version": 2})
        pub = self.client.post("/api/admin/system/content/publish",
                               json={"note": "naik", "version": 0, "draft_version": 3})
        self.assertEqual(pub.status_code, 200, pub.text)
        hid = pub.json()["history"][0]["id"]
        r = self.client.post("/api/admin/system/content/restore",
                             json={"history_id": hid, "version": 1, "draft_version": 4})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["draft"]["hero"], {"title": "Judul Lama"})

    # ---------- procedures ----------
    def test_procedures_publish_updates_cache(self):
        self._as(SUPER)
        d = self._detail("procedures")
        self.assertEqual(d["published"]["daily_release_limit"], 7)  # default merged
        value = {**d["published"], "daily_release_limit": 3, "withdraw_min_idr": 2_000_000}
        self.client.post("/api/admin/system/procedures/draft",
                         json={"value": value, "version": 0, "draft_version": 0})
        r = self.client.post("/api/admin/system/procedures/publish",
                             json={"note": "ketatkan", "version": 0, "draft_version": 1})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(procedures_config.procedure("daily_release_limit"), 3)
        self.assertEqual(procedures_config.procedure("withdraw_min_idr"), 2_000_000)

    def test_procedures_validation(self):
        self._as(SUPER)
        r = self.client.post("/api/admin/system/procedures/draft",
                             json={"value": {"bogus_key": 1}, "version": 0, "draft_version": 0})
        self.assertEqual(r.status_code, 400)
        r = self.client.post("/api/admin/system/procedures/draft",
                             json={"value": {"daily_release_limit": 0}, "version": 0, "draft_version": 0})
        self.assertEqual(r.status_code, 400)
        r = self.client.post("/api/admin/system/procedures/draft",
                             json={"value": {"subscription_reminder_days": [7, 7]}, "version": 0, "draft_version": 0})
        self.assertEqual(r.status_code, 400)

    # ---------- legacy PATCH stays versioned ----------
    def test_direct_patch_landing_records_history(self):
        self._as(STAFF)  # existing right preserved: cms.manage publishes directly
        r = self.client.patch("/api/cms/landing", json={"settings": {"hero": {"title": "Langsung"}}})
        self.assertEqual(r.status_code, 200, r.text)
        doc = self.settings.docs[0]
        self.assertEqual(doc["version"], 1)
        self.assertEqual(doc["history"][0]["value"]["hero"], {"title": "Judul Lama"})
        self.assertTrue(any(e["kind"] == "direct-publish" for e in self.audit.docs))

    # ---------- audit redaction ----------
    def test_audit_redacts_sensitive(self):
        self._as(SUPER)
        self.client.post("/api/admin/system/content/draft",
                         json={"value": {"hero": {"title": "X"}, "signature_url": "https://x/sig.png",
                                         "general": {"brand_name": "RILIS"}},
                               "version": 0, "draft_version": 0})
        entry = self.audit.docs[0]
        flat = str(entry["diff"])
        self.assertIn("[Data dilindungi]", flat)
        self.assertNotIn("sig.png", flat)


if __name__ == "__main__":
    unittest.main()
