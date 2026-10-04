"""Validate the full-runtime launcher without touching live services."""
import contextlib
import io
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.start_production import configuration_errors, main


def complete_environment():
    return {
        "RILISMUSIK_DEPLOYMENT_MODE": "production", "MONGO_URL": "mongodb://localhost:27017",
        "DB_NAME": "rilismusik", "JWT_SECRET": "unit-test-only-secret",
        "FRONTEND_URL": "https://web.example.invalid", "SMTP_HOST": "smtp.example.invalid",
        "SMTP_PORT": "465", "SMTP_USER": "test", "SMTP_PASSWORD": "test-password",
        "SENDER_EMAIL": "test@example.invalid", "SENDER_NAME": "Rilis Musik",
        "R2_ENDPOINT_URL": "https://storage.example.invalid", "R2_ACCESS_KEY_ID": "test-key",
        "R2_SECRET_ACCESS_KEY": "test-storage-secret", "R2_BUCKET": "test-bucket",
        "XENDIT_SECRET_KEY": "test-payment-secret", "XENDIT_RETURN_URL_BASE": "https://web.example.invalid",
        "UPLOAD_DIR": "/data/uploads", "PORT": "8000", "XENDIT_ALLOW_MOCK_PAY": "false",
    }


class ProductionConfigurationTests(unittest.TestCase):
    def test_complete_configuration(self):
        self.assertEqual(configuration_errors(complete_environment()), [])

    def test_preview_or_function_cannot_run_full_launcher(self):
        env = complete_environment()
        env.update(RILISMUSIK_DEPLOYMENT_MODE="preview", VERCEL="1")
        self.assertEqual(len(configuration_errors(env)), 2)

    def test_invalid_values_do_not_leak_credentials(self):
        env = complete_environment()
        env.update(MONGO_URL="private-password", FRONTEND_URL="https://user:private-password@web.example.invalid")
        errors = configuration_errors(env)
        self.assertGreater(len(errors), 0)
        self.assertNotIn("private-password", str(errors))

    def test_bad_ports_and_mock_payment_fail(self):
        env = complete_environment()
        env.update(PORT="0", SMTP_PORT="not-a-port", XENDIT_ALLOW_MOCK_PAY="true")
        self.assertEqual(len(configuration_errors(env)), 3)

    def test_ephemeral_storage_is_rejected(self):
        for directory in ("/tmp/uploads", "relative/uploads"):
            with self.subTest(directory=directory):
                env = complete_environment()
                env["UPLOAD_DIR"] = directory
                self.assertTrue(configuration_errors(env))

    def test_webhook_requires_verification_token(self):
        env = complete_environment()
        env["XENDIT_WEBHOOK_ENABLED"] = "true"
        self.assertTrue(configuration_errors(env))
        env["XENDIT_WEBHOOK_VERIFICATION_TOKEN"] = "test-token"
        self.assertEqual(configuration_errors(env), [])

    def test_check_never_starts_server_or_claims_live_readiness(self):
        with patch.dict(os.environ, complete_environment(), clear=True), patch.object(sys, "argv", ["start", "--check"]), \
             patch("scripts.start_production.os.execvp") as start, contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(), 0)
        start.assert_not_called()
        self.assertIn("belum diuji", output.getvalue())


if __name__ == "__main__":
    unittest.main()
