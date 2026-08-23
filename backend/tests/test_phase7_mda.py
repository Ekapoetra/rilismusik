"""Phase 7 — Master Distribution Agreement (MDA) auto-generation tests.

Covers:
- POST /auth/register requires mda_accepted=true → 400 without it.
- Successful register creates a `contracts` document with kind='mda', end_date=None, status='active'.
- GET /cms/mda/preview returns a valid PDF (starts with %PDF-).
- Generated PDF starts with %PDF-1.x and is downloadable via /api/files/contract/<id>.pdf.
- Label sees own MDA via /contracts/label.
- Lifetime contract effective_status='active', days_left=None.
"""
import os
import time
import uuid
import requests
from tests.support_config import SUPERADMIN, temporary_password
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE}/api"


def _email():
    return f"test_mda_{uuid.uuid4().hex[:10]}@example.com"


def _register_payload(extra=None):
    payload = {
        "label_name": f"MDA Test {uuid.uuid4().hex[:6]}",
        "pic_name": "MDA Tester",
        "email": _email(),
        "whatsapp": "+6281234567890",
        "password": temporary_password("phase7-mda"),
        "account_type": "label",
        "mda_accepted": True,
    }
    if extra:
        payload.update(extra)
    return payload


class TestMdaRegistration:
    def test_register_without_mda_returns_400(self):
        payload = _register_payload({"mda_accepted": False})
        r = requests.post(f"{API}/auth/register", json=payload, timeout=30)
        assert r.status_code == 400
        assert "MDA" in r.text or "Distribution Agreement" in r.text

    def test_register_with_mda_creates_contract(self):
        payload = _register_payload()
        r = requests.post(f"{API}/auth/register", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        token = body["access_token"]
        label_id = body["label"]["id"]

        # Label should now see exactly 1 active MDA contract
        time.sleep(0.5)
        r2 = requests.get(
            f"{API}/contracts/label",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        assert r2.status_code == 200, r2.text
        items = r2.json()
        assert isinstance(items, list)
        mdas = [c for c in items if c.get("kind") == "mda"]
        assert len(mdas) >= 1, f"No MDA contract auto-generated for label {label_id}"
        mda = mdas[0]
        assert mda["status"] == "active"
        assert mda["effective_status"] == "active"
        assert mda["end_date"] is None
        assert mda["is_lifetime"] is True
        assert mda["days_left"] is None
        assert mda["accepted_by_name"] == payload["pic_name"]
        assert mda["title"] == "Master Distribution Agreement"
        assert mda["file_url"].startswith("/api/files/contract/")

    def test_mda_pdf_is_downloadable(self):
        # register a label, then download its MDA PDF
        payload = _register_payload()
        r = requests.post(f"{API}/auth/register", json=payload, timeout=30)
        assert r.status_code == 200
        token = r.json()["access_token"]
        time.sleep(0.4)
        contracts = requests.get(
            f"{API}/contracts/label",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        ).json()
        mda = next((c for c in contracts if c.get("kind") == "mda"), None)
        assert mda, "MDA not created"
        url = f"{BASE}{mda['file_url']}"
        pdf = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
        assert pdf.status_code == 200
        assert pdf.content[:5] == b"%PDF-", "Not a valid PDF"
        assert len(pdf.content) > 3000, "PDF suspiciously small"


class TestMdaPreview:
    def test_public_preview_returns_pdf(self):
        r = requests.get(f"{API}/cms/mda/preview", timeout=15)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:5] == b"%PDF-"
        assert len(r.content) > 3000

    def test_preview_does_not_create_db_contract(self):
        # Count contracts before & after — preview should NOT mutate DB
        # We rely on super_admin to count
        sa = requests.post(
            f"{API}/auth/login",
            json=SUPERADMIN,
            timeout=15,
        )
        assert sa.status_code == 200
        sa_token = sa.json()["access_token"]
        hdr = {"Authorization": f"Bearer {sa_token}"}
        before = requests.get(f"{API}/contracts/admin", headers=hdr, timeout=15).json()
        n_before = len(before) if isinstance(before, list) else len(before.get("items", []))
        requests.get(f"{API}/cms/mda/preview", timeout=15)
        after = requests.get(f"{API}/contracts/admin", headers=hdr, timeout=15).json()
        n_after = len(after) if isinstance(after, list) else len(after.get("items", []))
        assert n_after == n_before, "preview should NOT create a contract record"
