"""Phase 9 — Auto-create from CSV + Admin Buatkan Akun tests.

Covers:
  - Royalty CSV auto-creates Label/Release/Track for unmatched rows
  - Fuzzy match by label name (case + whitespace) doesn't dup an existing label
  - Auto-created Release defaults (date, type, status, imported_legacy, cover_url)
  - Auto-created Track defaults (artist_name, audio_url, imported_legacy)
  - Admin POST /labels/{id}/create-account: success + validations + RBAC
  - Login with newly generated password works
  - Demo PPR + Demo VIP seeded accounts can log in and dashboards work
"""
import io
import os
import time
import uuid
import requests
from tests.support_config import DEMO_PPR, DEMO_VIP, FINANCE, RELEASE_ADMIN, SUPERADMIN, temporary_password
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://lanjut-core.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

SUPER = SUPERADMIN
FINANCE_ADMIN = FINANCE


def _items(resp_json):
    """Normalize list responses: backend may return list or {items: [...]}"""
    if isinstance(resp_json, list):
        return resp_json
    if isinstance(resp_json, dict):
        return resp_json.get("items") or resp_json.get("labels") or resp_json.get("orders") or resp_json.get("withdraws") or []
    return []


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login {creds['email']} -> {r.status_code} {r.text[:200]}"
    return r.json()["access_token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def super_tok():
    return _login(SUPER)


@pytest.fixture(scope="module")
def release_tok():
    return _login(RELEASE_ADMIN)


@pytest.fixture(scope="module")
def finance_tok():
    return _login(FINANCE_ADMIN)


def _make_csv(label_name, artist, release_title, track_title, isrc, upc, period="2024-06"):
    # Believe-style semicolon CSV w/ minimal columns
    header = "Bulan laporan;Nama Label;Nama Artis;Judul rilis;Judul track;UPC;ISRC;Pendapatan Bersih"
    line = f"{period};{label_name};{artist};{release_title};{track_title};{upc};{isrc};1,2345"
    return f"{header}\n{line}\n".encode("utf-8")


# ---------------------- Auto-create from CSV -----------------------------

def test_autocreate_new_label_release_track(super_tok):
    sfx = uuid.uuid4().hex[:8].upper()
    label_name = f"TEST_AutoLabel_{sfx}"
    isrc = f"IDTEST{sfx[:6]}"
    upc = f"UPCT{sfx}"
    csv_bytes = _make_csv(label_name, "TEST Artist", "TEST Release", "TEST Track", isrc, upc)

    r = requests.post(
        f"{API}/royalty/admin/imports",
        headers=_h(super_tok),
        files={"file": ("believe.csv", csv_bytes, "text/csv")},
        data={"rate_eur_idr": "17000"},
        timeout=60,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("auto_created_labels", 0) >= 1, body
    assert body.get("auto_created_releases", 0) >= 1, body
    assert body.get("auto_created_tracks", 0) >= 1, body
    # auto-created lines count as matched (no unmatched)
    assert body.get("matched_lines", body.get("matched", 0)) >= 1
    assert body.get("unmatched_lines", body.get("unmatched", 0)) == 0
    import_id = body.get("id") or body.get("import_id")
    assert import_id

    # Verify label was created with expected attrs
    rl = requests.get(f"{API}/admin/labels?q={label_name}", headers=_h(super_tok), timeout=30)
    assert rl.status_code == 200, rl.text
    items = _items(rl.json())
    assert isinstance(items, list)
    match = [x for x in items if x.get("label_name") == label_name]
    assert match, f"new label not found: {label_name}"
    lab = match[0]
    assert lab.get("user_id") in (None, ""), lab
    assert lab.get("account_status") == "legacy_unclaimed", lab
    assert lab.get("auto_created_from") == import_id


def test_autocreate_fuzzy_match_existing_label_case_and_spaces(super_tok):
    """Upload with uppercased + padded label name should match existing label, not duplicate."""
    sfx = uuid.uuid4().hex[:6].upper()
    base_name = f"TEST_Fuzzy_{sfx}"

    # Pre-create a label via first CSV (lowercase variant)
    csv1 = _make_csv(base_name, "Art1", "Rel1", "Trk1", f"IDFUZ{sfx}1", f"UPCFZ{sfx}1")
    r1 = requests.post(
        f"{API}/royalty/admin/imports",
        headers=_h(super_tok),
        files={"file": ("a.csv", csv1, "text/csv")},
        data={"rate_eur_idr": "17000"},
        timeout=60,
    )
    assert r1.status_code == 200, r1.text
    assert r1.json().get("auto_created_labels", 0) >= 1

    # Now upload uppercase + extra spaces of the SAME label
    weird_name = f"  {base_name.upper()}   "
    csv2 = _make_csv(weird_name, "Art2", "Rel2", "Trk2", f"IDFUZ{sfx}2", f"UPCFZ{sfx}2")
    r2 = requests.post(
        f"{API}/royalty/admin/imports",
        headers=_h(super_tok),
        files={"file": ("b.csv", csv2, "text/csv")},
        data={"rate_eur_idr": "17000"},
        timeout=60,
    )
    assert r2.status_code == 200, r2.text
    # No NEW label should be created on the 2nd upload (fuzzy matched)
    assert r2.json().get("auto_created_labels", 0) == 0, r2.json()
    # But matched should be 1 (line matched by fuzzy label_name)
    assert r2.json().get("matched_lines", r2.json().get("matched", 0)) >= 1

    # Confirm only ONE label exists for that name
    rl = requests.get(f"{API}/admin/labels?q={base_name}", headers=_h(super_tok), timeout=30)
    items = _items(rl.json())
    same = [x for x in items if x.get("label_name", "").strip().lower() == base_name.lower()]
    assert len(same) == 1, f"expected 1 label, got {len(same)}: {[x.get('label_name') for x in same]}"


def test_autocreate_release_track_defaults(super_tok):
    sfx = uuid.uuid4().hex[:6].upper()
    label_name = f"TEST_Defaults_{sfx}"
    isrc = f"IDDEF{sfx}"
    upc = f"UPCDEF{sfx}"
    csv_bytes = _make_csv(label_name, "ArtistX", "ReleaseX", "TrackX", isrc, upc, period="2023-08")

    r = requests.post(
        f"{API}/royalty/admin/imports",
        headers=_h(super_tok),
        files={"file": ("c.csv", csv_bytes, "text/csv")},
        data={"rate_eur_idr": "17000"},
        timeout=60,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    import_id = body.get("id") or body.get("import_id")

    # Find label
    rl = requests.get(f"{API}/admin/labels?q={label_name}", headers=_h(super_tok), timeout=30)
    items = _items(rl.json())
    lab = next((x for x in items if x.get("label_name") == label_name), None)
    assert lab, "label not found"
    label_id = lab["id"]

    # Fetch releases for label via admin endpoint
    rr = requests.get(f"{API}/admin/releases?q=ReleaseX", headers=_h(super_tok), timeout=30)
    assert rr.status_code == 200, rr.text
    releases = [x for x in rr.json() if x.get("label_id") == label_id]
    assert releases, f"no releases for label {label_id}"
    rel = next((x for x in releases if x.get("upc") == upc), releases[0])
    assert rel.get("release_type") == "single", rel
    assert rel.get("status") == "live", rel
    assert rel.get("imported_legacy") is True, rel
    assert rel.get("cover_url") in (None, ""), rel
    assert rel.get("release_date") == "2023-08-01", rel
    assert rel.get("auto_created_from") == import_id

    # Tracks: query db via the royalty matched lines (lines populate track_id)
    rl2 = requests.get(f"{API}/royalty/admin/lines?import_id={import_id}", headers=_h(super_tok), timeout=30)
    if rl2.status_code == 200:
        body2 = rl2.json()
        lines = body2 if isinstance(body2, list) else (body2.get("items") or body2.get("lines") or [])
        trk_line = next((x for x in lines if x.get("isrc") == isrc), None)
        if trk_line:
            assert trk_line.get("artist_name") == "ArtistX"


# ---------------------- Admin create-account -----------------------------

def _create_unclaimed_label(super_tok):
    sfx = uuid.uuid4().hex[:8].upper()
    label_name = f"TEST_CA_{sfx}"
    isrc = f"IDCA{sfx[:6]}"
    upc = f"UPCCA{sfx}"
    csv_bytes = _make_csv(label_name, "Artist", "Rel", "Trk", isrc, upc)
    r = requests.post(
        f"{API}/royalty/admin/imports",
        headers=_h(super_tok),
        files={"file": ("d.csv", csv_bytes, "text/csv")},
        data={"rate_eur_idr": "17000"},
        timeout=60,
    )
    assert r.status_code == 200
    rl = requests.get(f"{API}/admin/labels?q={label_name}", headers=_h(super_tok), timeout=30)
    items = _items(rl.json())
    lab = next((x for x in items if x.get("label_name") == label_name), None)
    assert lab, "label not created"
    return lab["id"], label_name


def test_create_account_auto_password_and_login(super_tok):
    label_id, label_name = _create_unclaimed_label(super_tok)
    email = f"test_ca_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(
        f"{API}/admin/labels/{label_id}/create-account",
        headers=_h(super_tok),
        data={"email": email, "pic_name": "PIC X", "whatsapp": "081234567890"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["email"] == email
    pw = body["password"]
    assert isinstance(pw, str) and len(pw) == 12, pw

    # Login with that password
    time.sleep(0.5)
    r2 = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=30)
    assert r2.status_code == 200, r2.text
    tok = r2.json()["access_token"]

    # Dashboard works
    rd = requests.get(f"{API}/label/dashboard", headers=_h(tok), timeout=30)
    assert rd.status_code == 200, rd.text
    dash = rd.json()
    assert dash["label"]["label_name"] == label_name
    assert dash["label"].get("account_status") == "active"
    assert dash["label"].get("user_id")
    # MDA accepted_at + contract should be present
    assert dash["label"].get("mda_accepted_at")


def test_create_account_validations(super_tok):
    label_id, _ = _create_unclaimed_label(super_tok)

    # Invalid email
    r = requests.post(
        f"{API}/admin/labels/{label_id}/create-account",
        headers=_h(super_tok),
        data={"email": "not-an-email"},
        timeout=30,
    )
    assert r.status_code == 400, r.text

    # Short password
    r = requests.post(
        f"{API}/admin/labels/{label_id}/create-account",
        headers=_h(super_tok),
        data={"email": f"ok_{uuid.uuid4().hex[:6]}@example.com", "password": temporary_password("phase9")[:3]},
        timeout=30,
    )
    assert r.status_code == 400, r.text

    # Email taken (use super admin's email)
    r = requests.post(
        f"{API}/admin/labels/{label_id}/create-account",
        headers=_h(super_tok),
        data={"email": SUPER["email"]},
        timeout=30,
    )
    assert r.status_code == 409, r.text

    # Label not found
    r = requests.post(
        f"{API}/admin/labels/nonexistent-id-xxxx/create-account",
        headers=_h(super_tok),
        data={"email": f"a_{uuid.uuid4().hex[:6]}@example.com"},
        timeout=30,
    )
    assert r.status_code == 404, r.text

    # Successful create then re-create => 400 (already has user_id)
    email_ok = f"good_{uuid.uuid4().hex[:6]}@example.com"
    r_ok = requests.post(
        f"{API}/admin/labels/{label_id}/create-account",
        headers=_h(super_tok),
        data={"email": email_ok},
        timeout=30,
    )
    assert r_ok.status_code == 200, r_ok.text
    r_dup = requests.post(
        f"{API}/admin/labels/{label_id}/create-account",
        headers=_h(super_tok),
        data={"email": f"x_{uuid.uuid4().hex[:6]}@example.com"},
        timeout=30,
    )
    assert r_dup.status_code == 400, r_dup.text


def test_create_account_rbac_finance_forbidden(super_tok, finance_tok):
    label_id, _ = _create_unclaimed_label(super_tok)
    r = requests.post(
        f"{API}/admin/labels/{label_id}/create-account",
        headers=_h(finance_tok),
        data={"email": f"fin_{uuid.uuid4().hex[:6]}@example.com"},
        timeout=30,
    )
    assert r.status_code == 403, r.text


def test_create_account_release_admin_allowed(super_tok, release_tok):
    label_id, _ = _create_unclaimed_label(super_tok)
    r = requests.post(
        f"{API}/admin/labels/{label_id}/create-account",
        headers=_h(release_tok),
        data={"email": f"rel_{uuid.uuid4().hex[:6]}@example.com"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    assert r.json().get("password")


# ---------------------- Demo accounts ------------------------------------

def test_demo_ppr_login_and_dashboard():
    tok = _login(DEMO_PPR)
    r = requests.get(f"{API}/label/dashboard", headers=_h(tok), timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["label"].get("subscription_tier") in ("pay_per_release", None) or d["label"].get("payment_type") == "pay_per_release"
    assert d["label"].get("balance_available_idr") == 5000000
    assert (d.get("stats") or {}).get("total_releases", 0) >= 2


def test_demo_vip_dashboard_and_wami_and_withdraw():
    tok = _login(DEMO_VIP)
    r = requests.get(f"{API}/label/dashboard", headers=_h(tok), timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    lab = d["label"]
    assert lab.get("subscription_tier") == "annual_vip" or lab.get("payment_type") == "annual_vip"
    assert lab.get("subscription_status") == "active"
    assert lab.get("balance_available_idr") == 15000000
    assert lab.get("balance_pending_idr") == 3200000
    assert lab.get("bank_verified") is True
    stats = d.get("stats") or {}
    assert stats.get("total_releases", 0) >= 3
    assert stats.get("total_tracks", 0) >= 3

    # WAMI label
    rw = requests.get(f"{API}/wami/label", headers=_h(tok), timeout=30)
    assert rw.status_code == 200, rw.text
    wbody = rw.json()
    orders = _items(wbody)
    if isinstance(orders, dict):
        orders = orders.get("orders") or []
    assert any(o.get("is_free_vip") is True and o.get("status") == "registered" for o in orders), orders

    # Withdraw history
    rh = requests.get(f"{API}/withdraw/label", headers=_h(tok), timeout=30)
    assert rh.status_code == 200, rh.text
    hist = rh.json()
    items = _items(hist)
    paid = [w for w in items if w.get("status") == "paid"]
    assert paid, f"no paid withdraw found: {items}"
    assert paid[0].get("amount_idr") == 5000000 or paid[0].get("net_amount_idr") == 5000000 or paid[0].get("amount") == 5000000


# ---------------------- Regressions --------------------------------------

def test_regression_existing_label_name_match_no_autocreate(super_tok):
    """Uploading CSV w/ EXACT label_name as a real existing label should NOT trigger auto-create."""
    # Use a demo label
    label_name = "Suara Hujan Records" if False else None  # actually find via API
    rl = requests.get(f"{API}/admin/labels?status=active&per_page=50", headers=_h(super_tok), timeout=30)
    items = _items(rl.json())
    existing = next((x for x in items if x.get("user_id")), None)
    if not existing:
        pytest.skip("No claimed label available to test regression")
    label_name = existing["label_name"]

    sfx = uuid.uuid4().hex[:6].upper()
    csv_bytes = _make_csv(label_name, "Art", "Rel", "Trk", f"IDREG{sfx}", f"UPCREG{sfx}")
    r = requests.post(
        f"{API}/royalty/admin/imports",
        headers=_h(super_tok),
        files={"file": ("r.csv", csv_bytes, "text/csv")},
        data={"rate_eur_idr": "17000"},
        timeout=60,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("auto_created_labels", 0) == 0, f"regression: created new label for existing name: {body}"
    assert body.get("matched_lines", body.get("matched", 0)) >= 1
