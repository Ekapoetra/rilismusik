"""Smoke-check the real API imports and preview behavior without a live DB."""
import asyncio
import os
import unittest
from pathlib import Path
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.update({
    "RILISMUSIK_DEPLOYMENT_MODE": "preview",
    "MONGO_URL": "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=100",
    "DB_NAME": "migration_preview_test",
    "FRONTEND_URL": "https://preview.example.invalid",
    "UPLOAD_DIR": "/app/backend/uploads",
    "JWT_SECRET": "test-only-unused-jwt-secret",
    "SMTP_HOST": "smtp.example.invalid",
    "SMTP_PORT": "465",
    "SMTP_USER": "",
    "SMTP_PASSWORD": "",
    "SENDER_EMAIL": "test@example.invalid",
    "SENDER_NAME": "Preview test",
    "R2_ENDPOINT_URL": "", "R2_ACCESS_KEY_ID": "",
    "R2_SECRET_ACCESS_KEY": "", "R2_BUCKET": "",
})

from fastapi.testclient import TestClient
from vercel_app import app
import server
from routes.deps import UPLOAD_DIR, require_super_admin


class PreviewSmokeTests(unittest.TestCase):
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

    def test_startup_works_without_a_database_or_workers(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.bootstrap_mock.assert_not_called()

    def test_emergent_upload_path_is_replaced(self):
        self.assertNotEqual(str(UPLOAD_DIR), "/app/backend/uploads")
        self.assertTrue(UPLOAD_DIR.is_dir())

    def test_job_and_payment_writes_are_rejected(self):
        for path in ("/api/admin/royalty/import", "/api/payments/create", "/api/auth/register"):
            with self.subTest(path=path):
                self.assertEqual(self.client.post(path, json={}).status_code, 503)

    def test_scheduler_and_migration_endpoints_are_rejected(self):
        for path in ("/api/admin/cron/monthly-royalty-summary/status", "/api/admin/migrate/ensure-indexes"):
            self.assertEqual(self.client.get(path).status_code, 503)

    def test_logout_and_refresh_reach_authentication_routes(self):
        self.assertEqual(self.client.post("/api/auth/logout").status_code, 200)
        self.assertEqual(self.client.post("/api/auth/refresh").status_code, 401)

    def test_database_check_requires_authentication(self):
        self.assertEqual(self.client.get("/api/admin/deployment-check").status_code, 401)

    def test_cache_miss_reads_revenue_without_scheduling_a_preview_rebuild(self):
        from routes import revenue_rollup
        expected = {"artist-1": {"revenue_idr": 42000, "lines": 3}}
        with patch.object(revenue_rollup, "_rollup_from_cache", new=AsyncMock(return_value={})), \
             patch.object(revenue_rollup, "_rollup_live", new=AsyncMock(return_value=expected)) as live, \
             patch("asyncio.create_task") as create_task:
            result = asyncio.run(revenue_rollup.rollup_revenue_by_id(
                field="artist_id", ids=["artist-1"], period_from="2026-01", period_to="2026-06",
            ))
        self.assertEqual(result, expected)
        live.assert_awaited_once_with(
            field="artist_id", ids=["artist-1"], period_from="2026-01", period_to="2026-06",
        )
        create_task.assert_not_called()

    def test_database_check_includes_royalty_source_and_analytics_counts(self):
        import vercel_app
        counts = {"users": 287, "labels": 1798, "releases": 18092, "royalty_lines": 0, "monthly_analytics": 0}
        database = MagicMock()
        database.name = "migration_preview_test"
        database.command = AsyncMock(return_value={"ok": 1})
        collections = {
            name: MagicMock(estimated_document_count=AsyncMock(return_value=count))
            for name, count in counts.items()
        }
        database.__getitem__.side_effect = collections.__getitem__
        async def admin():
            return {"role": "super_admin"}
        app.dependency_overrides[require_super_admin] = admin
        try:
            with patch.object(vercel_app, "db", new=database):
                response = self.client.get("/api/admin/deployment-check")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["collections"], counts)
            database.command.assert_awaited_once_with("ping")
            for collection in collections.values():
                collection.estimated_document_count.assert_awaited_once_with()
        finally:
            app.dependency_overrides.pop(require_super_admin, None)

    def test_database_failure_does_not_expose_connection_details(self):
        import vercel_app
        async def admin():
            return {"role": "super_admin"}
        app.dependency_overrides[require_super_admin] = admin
        try:
            with patch.object(vercel_app.db, "command", new=AsyncMock(side_effect=RuntimeError("private URI"))):
                response = self.client.get("/api/admin/deployment-check")
                self.assertEqual(response.status_code, 503)
                self.assertNotIn("private URI", response.text)
        finally:
            app.dependency_overrides.pop(require_super_admin, None)


if __name__ == "__main__":
    unittest.main()
