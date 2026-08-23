"""Test-only configuration without version-controlled credentials."""
import os
import secrets
from pathlib import Path

from dotenv import dotenv_values, load_dotenv


_BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_BACKEND_ROOT / ".env")
_VALUES = dotenv_values(_BACKEND_ROOT / ".env.test")
_FRONTEND_VALUES = dotenv_values(_BACKEND_ROOT.parent / "frontend" / ".env")
PREVIEW_BASE = (os.environ.get("REACT_APP_BACKEND_URL") or _FRONTEND_VALUES.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
if not PREVIEW_BASE:
    raise RuntimeError("REACT_APP_BACKEND_URL is required for API tests")
os.environ.setdefault("REACT_APP_BACKEND_URL", PREVIEW_BASE)


def require_test_env(name: str) -> str:
    value = os.environ.get(name) or _VALUES.get(name)
    if not value:
        raise RuntimeError(f"Test environment variable {name} is required")
    return str(value)


def temporary_password(prefix: str = "Test") -> str:
    safe_prefix = "".join(char for char in prefix if char.isalnum())[:10] or "Test"
    return f"{safe_prefix}Aa1!{secrets.token_urlsafe(12)}"


def temporary_token(prefix: str = "test") -> str:
    return f"{prefix}-{secrets.token_urlsafe(24)}"


SUPERADMIN = {
    "email": require_test_env("TEST_SUPERADMIN_EMAIL"),
    "password": require_test_env("TEST_SUPERADMIN_PASSWORD"),
}

FINANCE = {
    "email": require_test_env("TEST_FINANCE_EMAIL"),
    "password": require_test_env("TEST_FINANCE_PASSWORD"),
}

SUPPORT = {
    "email": require_test_env("TEST_SUPPORT_EMAIL"),
    "password": require_test_env("TEST_SUPPORT_PASSWORD"),
}

RELEASE_ADMIN = {
    "email": require_test_env("TEST_RELEASE_EMAIL"),
    "password": require_test_env("TEST_RELEASE_PASSWORD"),
}
MARKETING = {
    "email": require_test_env("TEST_MARKETING_EMAIL"),
    "password": require_test_env("TEST_MARKETING_PASSWORD"),
}

CONTENT = {
    "email": require_test_env("TEST_CONTENT_EMAIL"),
    "password": require_test_env("TEST_CONTENT_PASSWORD"),
}

DEMO_PASSWORD = require_test_env("TEST_DEMO_PASSWORD")
DEMO_VIP = {
    "email": require_test_env("TEST_DEMO_VIP_EMAIL"),
    "password": require_test_env("TEST_DEMO_VIP_PASSWORD"),
}
DEMO_PPR = {
    "email": require_test_env("TEST_DEMO_PPR_EMAIL"),
    "password": require_test_env("TEST_DEMO_PPR_PASSWORD"),
}