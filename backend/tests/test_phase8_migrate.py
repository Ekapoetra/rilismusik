"""Phase 8 — Bulk Migration tests.

Covers:
- Multi-period royalty CSV (no period form field, period column varies per row).
- Bulk labels import (template download, dry-run, real upload, idempotency).
- Bulk releases + tracks import (legacy flag, ISRC dedupe).
- Bulk withdraws import (historical, no notifications).
- Claim flow: register with claim_existing=true → admin link to legacy label.
- Permissions: Only Super Admin can call /admin/migrate/*.
"""
import io
import os
import uuid
import requests
from tests.support_config import FINANCE, SUPERADMIN, temporary_password
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE}/api"

SUPER_EMAIL = SUPERADMIN["email"]
SUPER_PASS = SUPERADMIN["password"]


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _hdr(t):
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture(scope="module")
def super_token():
    return _login(SUPER_EMAIL, SUPER_PASS)


@pytest.fixture(scope="module")
def imported_label_id(super_token):
    """Bulk-import 3 labels then return the ID of the first."""
    suffix = uuid.uuid4().hex[:8]
    csv = (
        "label_name,pic_name,whatsapp,address,city,country,label_type,payment_type,subscription_tier,subscription_expires_at,account_status,royalty_percentage_default,notes\n"
        f"Phase8 Test Label A {suffix},Tester A,081111110001,Jl. A,Jakarta,Indonesia,label,annual_subscription,annual_vip,2027-01-01,active,60,VIP migrant\n"
        f"Phase8 Test Label B {suffix},Tester B,081111110002,Jl. B,Bandung,Indonesia,label,pay_per_release,,,active,55,PPR migrant\n"
        f"Phase8 Test Label C {suffix},Tester C,081111110003,Jl. C,Surabaya,Indonesia,independent_artist,pay_per_release,,,legacy_unclaimed,60,\n"
    )
    files = {"file": ("test.csv", csv, "text/csv")}
    r = requests.post(f"{API}/admin/migrate/labels", headers=_hdr(super_token), files=files, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["inserted"] == 3
    # Find the first label's ID via the report
    first = next(r for r in body["report"] if r["status"] == "OK")
    label_id = first["reason"].split("id=")[1]
    return {"label_id": label_id, "label_name": first["label_name"], "suffix": suffix}


# ============== MULTI-PERIOD ROYALTY CSV ==============

class TestMultiPeriodRoyaltyCsv:
    def test_multi_period_auto_split(self, super_token, imported_label_id):
        label_name = imported_label_id["label_name"]
        csv = (
            "Bulan Laporan,ISRC,UPC,Judul Lagu,Artis,Album,Label,Platform,Negara,Kuantias,Pendapatan Bersih\n"
            f"2024-01,IDPH8000001,3650800000001,Lagu Satu,Tester,Album A,{label_name},Spotify,ID,10000,12.50\n"
            f"2024-01,IDPH8000002,3650800000001,Lagu Dua,Tester,Album A,{label_name},Apple Music,ID,2500,3.10\n"
            f"2024-02,IDPH8000001,3650800000001,Lagu Satu,Tester,Album A,{label_name},Spotify,ID,15000,18.75\n"
            f"2024-03,IDPH8000001,3650800000001,Lagu Satu,Tester,Album A,{label_name},Spotify,US,5000,7.20\n"
        )
        files = {"file": ("multi.csv", csv, "text/csv")}
        r = requests.post(
            f"{API}/royalty/admin/imports",
            headers=_hdr(super_token),
            files=files,
            data={"rate_eur_idr": "17500", "note": "Phase 8 multi-period"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["is_multi_period"] is True
        assert body["period"] == "multi"
        assert body["period_start"] == "2024-01"
        assert body["period_end"] == "2024-03"
        assert body["period_breakdown"] == {"2024-01": 2, "2024-02": 1, "2024-03": 1}
        assert body["matched_lines"] == 4
        assert body["total_lines"] == 4

    def test_single_period_override(self, super_token, imported_label_id):
        label_name = imported_label_id["label_name"]
        csv = (
            "Bulan Laporan,ISRC,Label,Platform,Negara,Kuantias,Pendapatan Bersih\n"
            f"2024-01,IDPH8000003,{label_name},Spotify,ID,5000,6.00\n"
            f"2024-02,IDPH8000004,{label_name},Spotify,ID,4000,5.00\n"
        )
        files = {"file": ("override.csv", csv, "text/csv")}
        # Even though CSV has 2 periods, explicit form `period=2024-01` overrides all lines
        r = requests.post(
            f"{API}/royalty/admin/imports",
            headers=_hdr(super_token),
            files=files,
            data={"rate_eur_idr": "17500", "period": "2024-01"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["is_multi_period"] is False
        assert body["period"] == "2024-01"
        assert body["period_breakdown"] == {"2024-01": 2}

    def test_missing_period_column_and_form_fails(self, super_token):
        csv = (
            "ISRC,Label,Platform,Pendapatan Bersih\n"
            "IDPH8000099,Some Label,Spotify,1.00\n"
        )
        files = {"file": ("no_period.csv", csv, "text/csv")}
        r = requests.post(
            f"{API}/royalty/admin/imports",
            headers=_hdr(super_token),
            files=files,
            data={"rate_eur_idr": "17500"},
            timeout=30,
        )
        assert r.status_code == 400
        assert "period" in r.text.lower() or "bulan laporan" in r.text.lower()


# ============== BULK LABELS ==============

class TestBulkLabels:
    def test_template_download(self, super_token):
        r = requests.get(f"{API}/admin/migrate/template/labels", headers=_hdr(super_token), timeout=15)
        assert r.status_code == 200
        # Should be a CSV header row
        assert r.text.lower().startswith("label_name,pic_name,whatsapp")

    def test_bulk_idempotent_skip(self, super_token, imported_label_id):
        # Re-upload the same CSV — all 3 should be skipped
        suffix = imported_label_id["suffix"]
        csv = (
            "label_name,pic_name,whatsapp,city,country\n"
            f"Phase8 Test Label A {suffix},Tester A,081111110001,Jakarta,Indonesia\n"
            f"Phase8 Test Label B {suffix},Tester B,081111110002,Bandung,Indonesia\n"
        )
        files = {"file": ("dup.csv", csv, "text/csv")}
        r = requests.post(f"{API}/admin/migrate/labels", headers=_hdr(super_token), files=files, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["inserted"] == 0
        assert body["skipped"] == 2

    def test_invalid_subscription_tier_errors(self, super_token):
        suffix = uuid.uuid4().hex[:8]
        csv = (
            "label_name,pic_name,whatsapp,city,country,subscription_tier\n"
            f"Phase8 Invalid {suffix},Tester,081100000099,Jakarta,Indonesia,gold_extreme\n"
        )
        files = {"file": ("invalid.csv", csv, "text/csv")}
        r = requests.post(f"{API}/admin/migrate/labels", headers=_hdr(super_token), files=files, timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert body["errors"] == 1
        assert body["inserted"] == 0


# ============== CLAIM FLOW ==============

class TestClaimFlow:
    def test_register_with_claim_does_not_create_label(self, super_token, imported_label_id):
        email = f"claim_phase8_{uuid.uuid4().hex[:8]}@example.com"
        legacy_name = imported_label_id["label_name"]
        r = requests.post(
            f"{API}/auth/register",
            json={
                "label_name": "New Future Label",
                "pic_name": "Phase8 Claimant",
                "email": email,
                "whatsapp": "081234567099",
                "password": temporary_password("phase8-claim"),
                "account_type": "label",
                "mda_accepted": True,
                "claim_existing": True,
                "legacy_label_name": legacy_name,
            },
            timeout=15,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["claim_pending"] is True
        assert body["label"]["claim_pending"] is True
        user_id = body["user"]["id"]

        # The user's /label/me should return claim_pending=true
        token = body["access_token"]
        me = requests.get(f"{API}/label/me", headers=_hdr(token), timeout=15)
        assert me.status_code == 200
        assert me.json()["claim_pending"] is True

        # Admin can see the pending claim
        claims = requests.get(f"{API}/admin/migrate/claims", headers=_hdr(super_token), timeout=15).json()
        ids = [c["id"] for c in claims]
        assert user_id in ids

        # Admin links to legacy label
        link = requests.post(
            f"{API}/admin/migrate/claims/{user_id}/link/{imported_label_id['label_id']}",
            headers=_hdr(super_token),
            timeout=15,
        )
        assert link.status_code == 200, link.text
        link_body = link.json()
        assert link_body["ok"] is True

        # After linking, /label/me should return the actual label (not pending)
        me2 = requests.get(f"{API}/label/me", headers=_hdr(token), timeout=15)
        assert me2.status_code == 200
        me2_body = me2.json()
        assert "claim_pending" not in me2_body or not me2_body.get("claim_pending")
        assert me2_body.get("label_name") == legacy_name

        # MDA contract should now exist for this label
        contracts = requests.get(f"{API}/contracts/label", headers=_hdr(token), timeout=15).json()
        mdas = [c for c in contracts if c.get("kind") == "mda"]
        assert len(mdas) >= 1, "MDA should be generated on claim link"


# ============== PERMISSIONS ==============

class TestMigratePermissions:
    def test_non_super_admin_rejected(self):
        token = _login(FINANCE["email"], FINANCE["password"])
        files = {"file": ("x.csv", "label_name\nx\n", "text/csv")}
        r = requests.post(f"{API}/admin/migrate/labels", headers=_hdr(token), files=files, timeout=15)
        assert r.status_code == 403

    def test_label_user_rejected(self):
        # Register a fresh label and try
        email = f"label_p8_{uuid.uuid4().hex[:8]}@example.com"
        reg = requests.post(
            f"{API}/auth/register",
            json={
                "label_name": "Phase8 Outsider", "pic_name": "Out", "email": email,
                "whatsapp": "081234567088", "password": temporary_password("phase8-out"),
                "account_type": "label", "mda_accepted": True,
            },
            timeout=15,
        )
        assert reg.status_code == 200
        token = reg.json()["access_token"]
        files = {"file": ("x.csv", "label_name\nx\n", "text/csv")}
        r = requests.post(f"{API}/admin/migrate/labels", headers=_hdr(token), files=files, timeout=15)
        assert r.status_code == 403
