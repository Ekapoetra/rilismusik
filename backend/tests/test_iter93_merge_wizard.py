"""Phase 6 Merge Wizard + Public Request + Admin Batch backend tests."""
import os
import pytest
import requests
from pathlib import Path

_env = {}
for line in Path("/app/frontend/.env").read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        _env[k.strip()] = v.strip()
BASE = _env["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"


def _login(email, pwd):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": pwd})
    return r


def _hdr(email, pwd):
    r = _login(email, pwd)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def super_hdr():
    return _hdr("superadmin@rilismusik.com", "SuperAdmin#2026")


@pytest.fixture(scope="module")
def finance_hdr():
    return _hdr("finance1@rilismusik.com", "Finance#2026")


# ---------- Merge candidates + validate + commit ----------

class TestMergeWizard:
    def test_candidates_lists_three_mgqa(self, super_hdr):
        r = requests.get(f"{BASE}/admin/multi-label/candidates", headers=super_hdr)
        assert r.status_code == 200, r.text
        emails = {c["email"] for c in r.json().get("candidates", [])}
        assert {"mgqa-a@example.com", "mgqa-b@example.com", "mgqa-c@example.com"} <= emails

    def test_validate_and_commit_merge(self, super_hdr):
        # Fetch candidate label_ids
        r = requests.get(f"{BASE}/admin/multi-label/candidates", headers=super_hdr)
        cands = r.json()["candidates"]
        by_email = {c["email"]: c for c in cands}
        label_ids = [by_email[e]["label_id"] for e in ("mgqa-a@example.com", "mgqa-b@example.com", "mgqa-c@example.com")]
        primary_user_id = by_email["mgqa-a@example.com"]["user_id"]
        bank_id = "mgqa-label-a-bank"

        body = {
            "label_ids": label_ids,
            "primary_user_id": primary_user_id,
            "responsible_name": "PIC A",
            "responsible_email": "mgqa-a@example.com",
            "responsible_whatsapp": "+62811000000",
            "payout_bank_account_id": bank_id,
            "confirm": True,
        }

        vr = requests.post(f"{BASE}/admin/multi-label/merge/validate", headers=super_hdr, json=body)
        assert vr.status_code == 200, vr.text
        vdata = vr.json()
        # Combined balance excludes legacy 9,999,999
        agg = (vdata.get("preview") or {}).get("combined_balance_idr")
        assert agg == 9000000, vdata

        cr = requests.post(f"{BASE}/admin/multi-label/merge/commit", headers=super_hdr, json=body)
        assert cr.status_code == 200, cr.text
        cdata = cr.json()
        assert cdata.get("ok") is True

        # Idempotency
        cr2 = requests.post(f"{BASE}/admin/multi-label/merge/commit", headers=super_hdr, json=body)
        assert cr2.status_code == 200, cr2.text
        assert cr2.json().get("idempotent") is True, cr2.json()

    def test_accounts_reflects_merge(self, super_hdr):
        r = requests.get(f"{BASE}/admin/multi-label/accounts", headers=super_hdr)
        assert r.status_code == 200, r.text
        accounts = r.json().get("accounts", [])
        match = [a for a in accounts if a.get("primary_email") == "mgqa-a@example.com"]
        assert match, f"no merged account found: {accounts}"
        acc = match[0]
        assert acc.get("label_count") == 3
        assert acc.get("aggregate_balance_idr") == 9000000, acc
        # BCA bank
        bank = acc.get("payout_bank") or {}
        assert "BCA" in (bank.get("bank_name") or "") or "Central Asia" in (bank.get("bank_name") or ""), bank
        # per-label cutoffs preserved
        cuts = {lbl.get("id"): lbl.get("last_withdrawn_period") for lbl in acc.get("labels", [])}
        # if labels list doesn't include last_withdrawn_period, fetch separately - but at least keys should be a-b-c
        assert set(cuts.keys()) == {"mgqa-label-a", "mgqa-label-b", "mgqa-label-c"}, cuts

    def test_old_accounts_blocked_login(self):
        for e, p in [("mgqa-b@example.com", "MergeB#2026"), ("mgqa-c@example.com", "MergeC#2026")]:
            r = _login(e, p)
            assert r.status_code == 403, f"{e}: {r.status_code} {r.text}"
            assert "gabung" in r.text.lower() or "merge" in r.text.lower()

    def test_primary_still_logs_in_multi_label(self):
        r = _login("mgqa-a@example.com", "MergeA#2026")
        assert r.status_code == 200, r.text

    def test_finance_forbidden_on_commit(self, finance_hdr):
        r = requests.post(f"{BASE}/admin/multi-label/merge/commit", headers=finance_hdr, json={
            "label_ids": ["x", "y"], "primary_user_id": "y",
            "responsible_name": "n", "responsible_email": "e@e.com", "responsible_whatsapp": "+62",
            "payout_bank_account_id": "b", "confirm": True,
        })
        assert r.status_code == 403, f"{r.status_code} {r.text}"

    def test_validate_rejects_already_merged_label(self, super_hdr):
        # Get 2 labels from merged account
        r = requests.get(f"{BASE}/admin/multi-label/accounts", headers=super_hdr)
        merged = [a for a in r.json()["accounts"] if a.get("primary_email") == "mgqa-a@example.com"]
        assert merged, "expected merged account"
        acc = merged[0]
        two_ids = [l["id"] for l in acc["labels"]][:2]
        body = {
            "label_ids": two_ids,
            "primary_user_id": "some-other-user",
            "responsible_name": "n", "responsible_email": "e@e.com", "responsible_whatsapp": "+62",
            "payout_bank_account_id": "x",
        }
        vr = requests.post(f"{BASE}/admin/multi-label/merge/validate", headers=super_hdr, json=body)
        # Endpoint returns 200 with ok:false + errors
        assert vr.status_code == 200, vr.text
        data = vr.json()
        assert data.get("ok") is False and data.get("errors"), data


# ---------- Public Multi Label request ----------

class TestPublicRequest:
    def test_public_submit_no_auth(self):
        payload = {"name": "QA Requester", "email": "qa-request@example.com", "whatsapp": "+628123456789",
                   "label_info": "Test Label QA", "message": "please"}
        r = requests.post(f"{BASE}/multi-label/request", json=payload)
        assert r.status_code in (200, 201), r.text

    def test_admin_sees_request(self, super_hdr):
        r = requests.get(f"{BASE}/admin/multi-label/requests", headers=super_hdr)
        assert r.status_code == 200, r.text
        reqs = r.json().get("requests", [])
        assert any(x.get("email") == "qa-request@example.com" for x in reqs), reqs


# ---------- Admin batch view ----------

class TestAdminBatches:
    def test_batches_endpoint(self, super_hdr):
        r = requests.get(f"{BASE}/withdraw/admin/batches", headers=super_hdr)
        assert r.status_code == 200, r.text
        # Body should be a list or dict with 'batches'
        body = r.json()
        assert isinstance(body, (list, dict))
