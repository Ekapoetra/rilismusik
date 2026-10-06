"""Offline checks for the browser return URL sent to Xendit Payment Sessions."""
import os
import unittest
from unittest.mock import patch

import test_vercel_preview  # Configures offline environment before real imports.
from fastapi import HTTPException
import payment_service


PAYMENT = {"id": "pay-1", "reference_id": "ref-1", "amount": 50_000, "type": "custom_service",
           "description": "Cover Art", "return_path": "/label/invoices"}


def return_url(base, payment=PAYMENT):
    with patch.dict(os.environ, {"XENDIT_RETURN_URL_BASE": base}):
        payload = payment_service.build_session_payload(payment)
    assert payload["success_return_url"] == payload["cancel_return_url"]
    return payload["success_return_url"]


class XenditReturnUrlTests(unittest.TestCase):
    def test_valid_origin_is_used_as_is(self):
        self.assertEqual(return_url("https://rilismusik.com"), "https://rilismusik.com/label/invoices?payment_id=pay-1")

    def test_common_env_typos_still_produce_https_url(self):
        for value in ("rilismusik.com", "https://rilismusik.com/", '"https://rilismusik.com"',
                      "  'rilismusik.com'  ", "http://rilismusik.com"):
            with self.subTest(value=value):
                self.assertEqual(return_url(value), "https://rilismusik.com/label/invoices?payment_id=pay-1")

    def test_return_path_without_leading_slash_is_fixed(self):
        url = return_url("https://www.rilismusik.com", {**PAYMENT, "return_path": "label/wami"})
        self.assertEqual(url, "https://www.rilismusik.com/label/wami?payment_id=pay-1")

    def test_unusable_value_reports_clear_configuration_error(self):
        for value in ("localhost", "-", "https://rilis musik.com", "https://rilismusik.com/?x=1", "ftp://rilismusik.com"):
            with self.subTest(value=value), self.assertRaises(HTTPException) as raised:
                return_url(value)
            self.assertEqual(raised.exception.status_code, 503)
            self.assertIn("XENDIT_RETURN_URL_BASE", raised.exception.detail)

    def test_missing_value_keeps_existing_message(self):
        with self.assertRaises(HTTPException) as raised:
            return_url("   ")
        self.assertEqual(raised.exception.detail, "Konfigurasi Xendit belum lengkap")


if __name__ == "__main__":
    unittest.main()
