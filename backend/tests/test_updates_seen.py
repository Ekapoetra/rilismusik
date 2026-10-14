"""v1.1 Updates popup — per-account seen state persists server-side."""
import os
import unittest
from pathlib import Path
import sys
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.update({
    "MONGO_URL": "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=100",
    "DB_NAME": "updates_seen_test",
    "JWT_SECRET": "test-only-unused-jwt-secret",
    "UPLOAD_DIR": "/tmp/rilismusik-test-uploads",
    "RILISMUSIK_DEPLOYMENT_MODE": "preview",
    "FRONTEND_URL": "https://preview.example.invalid",
    "CORS_ORIGINS": "https://preview.example.invalid",
    "SMTP_HOST": "smtp.example.invalid",
    "SMTP_PORT": "465",
    "SMTP_USER": "",
    "SMTP_PASSWORD": "",
    "SENDER_EMAIL": "test@example.invalid",
    "SENDER_NAME": "Preview test",
    "R2_ENDPOINT_URL": "",
    "R2_ACCESS_KEY_ID": "",
    "R2_SECRET_ACCESS_KEY": "",
    "R2_BUCKET": "",
})

from fastapi.testclient import TestClient
import server
from server import app
from routes.deps import get_current_user
import routes.labels as labels_mod
from test_token_foundation import _FakeCollection, _db

LABEL_USER = {"id": "u-1", "role": "label", "email": "l@t", "name": "Lab"}
ADMIN = {"id": "a-1", "role": "super_admin", "email": "a@t"}


class UpdatesSeenTests(unittest.TestCase):
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
        self.users = _FakeCollection()
        self.users.docs = [dict(LABEL_USER)]
        patch.object(labels_mod, "db", _db(users=self.users)).start()

    def tearDown(self):
        patch.stopall()
        app.dependency_overrides.clear()

    def _as(self, user):
        app.dependency_overrides[get_current_user] = lambda: user

    def test_mark_seen_persists_version(self):
        self._as(LABEL_USER)
        r = self.client.post("/api/label/updates/seen", json={"version": "1.1"})
        self.assertEqual(r.status_code, 200)
        doc = self.users.docs[0]
        self.assertEqual(doc["updates_seen_version"], "1.1")
        self.assertTrue(doc.get("updates_seen_at"))

    def test_newer_version_overwrites(self):
        self._as(LABEL_USER)
        self.client.post("/api/label/updates/seen", json={"version": "1.1"})
        self.client.post("/api/label/updates/seen", json={"version": "1.2"})
        self.assertEqual(self.users.docs[0]["updates_seen_version"], "1.2")

    def test_empty_version_rejected(self):
        self._as(LABEL_USER)
        r = self.client.post("/api/label/updates/seen", json={"version": "  "})
        self.assertEqual(r.status_code, 400)

    def test_admin_rejected(self):
        self._as(ADMIN)
        r = self.client.post("/api/label/updates/seen", json={"version": "1.1"})
        self.assertEqual(r.status_code, 403)

    def test_unauthenticated_rejected(self):
        r = self.client.post("/api/label/updates/seen", json={"version": "1.1"})
        self.assertEqual(r.status_code, 401)

    def test_unverified_label_not_kyc_gated(self):
        # /api/label/updates is KYC-free — the popup must still acknowledge for
        # members whose verification is pending.
        self._as({**LABEL_USER, "id": "u-new"})
        self.users.docs.append({"id": "u-new", "role": "label", "email": "n@t"})
        r = self.client.post("/api/label/updates/seen", json={"version": "1.1"})
        self.assertEqual(r.status_code, 200)


if __name__ == "__main__":
    unittest.main()
