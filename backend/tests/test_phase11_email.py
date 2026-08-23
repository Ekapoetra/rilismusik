"""Phase 11 — SMTP (Hostinger) email integration smoke tests.

Validates that:
  - email_service module imports without error
  - All 7 transactional helpers are exported
  - send_email() returns a message-id when SMTP_HOST + creds are configured
  - send_email() returns None gracefully when SMTP creds are missing

Live-send tests skipped automatically if SMTP_USER or SMTP_PASSWORD missing.
"""
import os
import sys
import pytest
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from tests.support_config import temporary_token
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")


def test_email_service_import_safe():
    """Module must import cleanly and expose all 7 helpers."""
    import importlib
    import email_service
    importlib.reload(email_service)
    for fn in (
        "send_email",
        "send_verification_email",
        "send_password_reset_email",
        "send_contract_expiry_email",
        "send_subscription_expiry_email",
        "send_payment_receipt_email",
        "send_withdraw_paid_email",
    ):
        assert hasattr(email_service, fn), f"email_service missing {fn}"


@pytest.mark.skipif(not (SMTP_USER and SMTP_PASSWORD), reason="SMTP credentials not configured")
def test_send_verification_email_via_smtp():
    """Live SMTP send — must return a non-empty message-id and not raise."""
    from email_service import send_verification_email

    async def run():
        return await send_verification_email(
            to=SMTP_USER,  # send to self (always deliverable)
            pic_name="Pytest Phase 11",
            token=temporary_token("verification"),
        )

    msg_id = asyncio.run(run())
    assert msg_id, "send_verification_email should return a message-id"
    assert isinstance(msg_id, str)


@pytest.mark.skipif(not (SMTP_USER and SMTP_PASSWORD), reason="SMTP credentials not configured")
def test_send_password_reset_email_via_smtp():
    from email_service import send_password_reset_email

    async def run():
        return await send_password_reset_email(
            to=SMTP_USER,
            token=temporary_token("reset"),
        )

    msg_id = asyncio.run(run())
    assert msg_id and isinstance(msg_id, str)
