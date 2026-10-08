"""The V13 UI preview branch must stay read-only against the shared database."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.pop("RILISMUSIK_DEPLOYMENT_MODE", None)
os.environ.update({
    "MONGO_URL": "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=100",
    "DB_NAME": "ui_preview_test",
    "FRONTEND_URL": "https://preview.example.invalid",
    "JWT_SECRET": "test-only-unused-jwt-secret",
    "SMTP_HOST": "smtp.example.invalid", "SMTP_PORT": "465", "SMTP_USER": "", "SMTP_PASSWORD": "",
    "SENDER_EMAIL": "test@example.invalid", "SENDER_NAME": "Preview test",
    "R2_ENDPOINT_URL": "", "R2_ACCESS_KEY_ID": "", "R2_SECRET_ACCESS_KEY": "", "R2_BUCKET": "",
})

from fastapi.testclient import TestClient
from vercel_ui_preview_app import app
import server


class UiPreviewReadOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bootstrap = patch.object(server, "_bootstrap_async", new_callable=AsyncMock)
        cls.bootstrap_mock = cls.bootstrap.start()
        cls.context = TestClient(app)
        cls.client = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)
        cls.bootstrap.stop()

    def test_entrypoint_forces_preview_mode_without_workers(self):
        self.assertEqual(os.environ["RILISMUSIK_DEPLOYMENT_MODE"], "preview")
        self.assertEqual(self.client.get("/api/health").status_code, 200)
        self.bootstrap_mock.assert_not_called()

    def test_writes_payments_and_jobs_are_rejected(self):
        for method, path in (("post", "/api/withdraw/label/request"), ("post", "/api/payments/create"),
                             ("patch", "/api/label/me"), ("delete", "/api/admin/releases/x"),
                             ("get", "/api/admin/cron/monthly-royalty-summary/status")):
            with self.subTest(path=path):
                self.assertEqual(getattr(self.client, method)(path).status_code, 503)

    def test_login_routes_stay_reachable(self):
        self.assertEqual(self.client.post("/api/auth/logout").status_code, 200)
        self.assertEqual(self.client.post("/api/auth/refresh").status_code, 401)


if __name__ == "__main__":
    unittest.main()
