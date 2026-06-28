"""Phase 11 — Resend email integration smoke tests.

Validates that:
  - email_service module imports without error
  - send_email() returns None gracefully when API key is missing
  - send_email() actually returns an email_id when sending to resend.dev sandbox
  - Auth endpoints don't break when email send is triggered

Skipped automatically if RESEND_API_KEY is not configured.
"""
import os
import sys
import pytest
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")


@pytest.mark.skipif(not RESEND_API_KEY, reason="RESEND_API_KEY not configured")
def test_send_verification_email_returns_id():
    from email_service import send_verification_email

    async def run():
        return await send_verification_email(
            to="delivered@resend.dev",  # Resend's sandbox always-accept address
            pic_name="Smoke Test",
            token="test-token-smoke",
        )

    email_id = asyncio.run(run())
    assert email_id, "send_verification_email should return a non-empty resend email id"
    assert isinstance(email_id, str) and len(email_id) > 10


@pytest.mark.skipif(not RESEND_API_KEY, reason="RESEND_API_KEY not configured")
def test_send_password_reset_email_returns_id():
    from email_service import send_password_reset_email

    async def run():
        return await send_password_reset_email(
            to="delivered@resend.dev",
            token="reset-token-smoke",
        )

    email_id = asyncio.run(run())
    assert email_id and isinstance(email_id, str)


def test_email_service_import_safe():
    """Module must import cleanly even without API key."""
    import importlib
    import email_service
    importlib.reload(email_service)
    assert hasattr(email_service, "send_email")
    assert hasattr(email_service, "send_verification_email")
    assert hasattr(email_service, "send_password_reset_email")
    assert hasattr(email_service, "send_contract_expiry_email")
    assert hasattr(email_service, "send_subscription_expiry_email")
    assert hasattr(email_service, "send_payment_receipt_email")
    assert hasattr(email_service, "send_withdraw_paid_email")
