"""
Phase 4 add-ons tests:
  - EUR redaction extension (revenue_eur, fee_eur, net_eur, label_eur, distributor_eur stripped for label/artist)
  - Contracts module CRUD + admin/label scope + extend/terminate + notifications
  - Blacklist + login block + unblock
  - In-app notifications (CRUD + cross-user isolation + hooks for tickets/release/withdraw/royalty)
"""
import io
import os
import time
import pytest
import requests
from datetime import datetime, timedelta, timezone
from tests.support_config import DEMO_PASSWORD, FINANCE as FINANCE_CRED, RELEASE_ADMIN as RELEASE_CRED, SUPPORT as SUPPORT_CRED, SUPERADMIN

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://lanjut-core.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

SUPER = (SUPERADMIN["email"], SUPERADMIN["password"])
FINANCE = (FINANCE_CRED["email"], FINANCE_CRED["password"])
SUPPORT = (SUPPORT_CRED["email"], SUPPORT_CRED["password"])
RELEASE_ADMIN = (RELEASE_CRED["email"], RELEASE_CRED["password"])


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    return r


def _token(email, password):
    r = _login(email, password)
    assert r.status_code == 200, f"Login {email} failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def _ensure_admin(super_token, email, password, role, name):
    """Create or reset sub-admin via super-admin API. Returns token."""
    r = _login(email, password)
    if r.status_code == 200:
        return r.json()["access_token"]
    # Create via admin-users
    cr = requests.post(f"{API}/admin/admin-users", headers=_h(super_token),
                       json={"email": email, "password": password, "name": name, "role": role}, timeout=30)
    if cr.status_code in (200, 201):
        r2 = _login(email, password)
        if r2.status_code == 200:
            return r2.json()["access_token"]
    # Fallback: find existing user of role and reset password
    listing = requests.get(f"{API}/admin/admin-users", headers=_h(super_token), timeout=30).json()
    for u in listing:
        if u.get("role") == role:
            rr = requests.patch(f"{API}/admin/admin-users/{u['id']}", headers=_h(super_token),
                                json={"password": password}, timeout=30)
            if rr.status_code in (200, 204):
                # Need to login with that user's existing email
                r3 = _login(u["email"], password)
                if r3.status_code == 200:
                    return r3.json()["access_token"]
    pytest.skip(f"Cannot provision {role} test user {email}")


@pytest.fixture(scope="session")
def super_token():
    return _token(*SUPER)


@pytest.fixture(scope="session")
def finance_token(super_token):
    return _ensure_admin(super_token, FINANCE[0], FINANCE[1], "admin_finance", "Finance Test")


@pytest.fixture(scope="session")
def support_token(super_token):
    return _ensure_admin(super_token, SUPPORT[0], SUPPORT[1], "admin_support", "Support Test")


@pytest.fixture(scope="session")
def demo_labels(super_token):
    """Return list of demo label dicts (with id, label_name, user_id, email)."""
    r = requests.get(f"{API}/admin/labels?limit=200", headers=_h(super_token), timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    items = data if isinstance(data, list) else (data.get("items") or [])
    wanted = ["Khizanah Kreasi Gontor", "Mustafa Kamal", "Manawa Music", "WANWE RECORDS"]
    out = {}
    for it in items:
        ln = it.get("label_name") or ""
        for w in wanted:
            if ln.strip().lower() == w.lower():
                out[w] = it
    return out


def _label_token(label_dict):
    email = label_dict.get("email") or label_dict.get("user_email")
    assert email, f"label dict missing email: {label_dict}"
    for pw in (DEMO_PASSWORD,):
        r = _login(email, pw)
        if r.status_code == 200:
            return r.json()["access_token"], email
    pytest.skip(f"Cannot log in to label {email}")


# ---------------------------------------------------------------------------
# 1) Currency Redaction
# ---------------------------------------------------------------------------
class TestCurrencyRedaction:
    EUR_KEYS = ("revenue_eur", "fee_eur", "net_eur", "label_eur", "distributor_eur",
                "gross_revenue_eur", "unit_price_eur", "mechanical_cost_eur", "client_share_rate")

    def test_label_lines_no_eur(self, demo_labels):
        lab = demo_labels.get("Khizanah Kreasi Gontor")
        assert lab, "Khizanah demo label not found"
        tok, _ = _label_token(lab)
        r = requests.get(f"{API}/royalty/lines?limit=10", headers=_h(tok), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        items = data if isinstance(data, list) else (data.get("items") or [])
        assert items, "No royalty lines"
        for line in items[:5]:
            for k in self.EUR_KEYS:
                assert k not in line, f"LABEL response leaked {k}: {line.keys()}"
            # IDR must still be present
            assert any(k in line for k in ("revenue_idr", "net_idr", "label_idr")), f"No IDR keys: {line.keys()}"

    def test_admin_lines_keep_eur(self, super_token):
        r = requests.get(f"{API}/royalty/lines?limit=10", headers=_h(super_token), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        items = data if isinstance(data, list) else (data.get("items") or [])
        assert items
        # At least one of EUR or sensitive should be present in admin view
        found = False
        for line in items[:10]:
            if any(k in line for k in self.EUR_KEYS):
                found = True
                break
        assert found, "Admin view should retain at least one EUR/sensitive field"


# ---------------------------------------------------------------------------
# 2) Contracts module
# ---------------------------------------------------------------------------
class TestContracts:
    created_ids = []

    def _upload_pdf(self, super_token, name="test.pdf", mime="application/pdf"):
        files = {"file": (name, io.BytesIO(b"%PDF-1.4\n%fake\n"), mime)}
        r = requests.post(f"{API}/contracts/admin/upload-pdf",
                          headers={"Authorization": f"Bearer {super_token}"},
                          files=files, timeout=30)
        return r

    def test_upload_pdf_rejects_non_pdf(self, super_token):
        files = {"file": ("img.jpg", io.BytesIO(b"\xff\xd8\xff"), "image/jpeg")}
        r = requests.post(f"{API}/contracts/admin/upload-pdf",
                          headers={"Authorization": f"Bearer {super_token}"},
                          files=files, timeout=30)
        assert r.status_code == 400, r.text

    def test_upload_pdf_accepts(self, super_token):
        r = self._upload_pdf(super_token)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "url" in body and "filename" in body
        TestContracts._pdf = body

    def test_create_invalid_label(self, super_token):
        payload = {
            "label_id": "nonexistent-id",
            "file_url": "/api/files/contract/xxx.pdf",
            "filename": "x.pdf",
            "start_date": "2025-01-01",
            "end_date": "2026-01-01",
        }
        r = requests.post(f"{API}/contracts/admin", headers=_h(super_token), json=payload, timeout=30)
        assert r.status_code == 404, r.text

    def test_create_invalid_dates(self, super_token, demo_labels):
        lab = demo_labels.get("Khizanah Kreasi Gontor")
        payload = {
            "label_id": lab["id"],
            "file_url": "/api/files/contract/xxx.pdf",
            "filename": "x.pdf",
            "start_date": "2025-06-01",
            "end_date": "2025-06-01",  # equal -> invalid
        }
        r = requests.post(f"{API}/contracts/admin", headers=_h(super_token), json=payload, timeout=30)
        assert r.status_code == 400, r.text

    def _make_contract(self, super_token, label_id, start, end):
        payload = {
            "label_id": label_id,
            "file_url": getattr(TestContracts, "_pdf", {}).get("url", "/api/files/contract/x.pdf"),
            "filename": "contract.pdf",
            "start_date": start,
            "end_date": end,
            "notes": "TEST_CONTRACT",
        }
        r = requests.post(f"{API}/contracts/admin", headers=_h(super_token), json=payload, timeout=30)
        return r

    def test_effective_status_all_states(self, super_token, demo_labels):
        lab = demo_labels.get("Khizanah Kreasi Gontor")
        today = datetime.now(timezone.utc).date()
        # active: end_date > 30 days from now
        r1 = self._make_contract(super_token, lab["id"],
                                 (today - timedelta(days=10)).isoformat(),
                                 (today + timedelta(days=200)).isoformat())
        assert r1.status_code == 200, r1.text
        assert r1.json()["effective_status"] == "active"
        TestContracts.created_ids.append(r1.json()["id"])

        # expiring_soon: end_date within 1-30 days
        r2 = self._make_contract(super_token, lab["id"],
                                 (today - timedelta(days=200)).isoformat(),
                                 (today + timedelta(days=10)).isoformat())
        assert r2.status_code == 200
        assert r2.json()["effective_status"] == "expiring_soon"
        TestContracts.created_ids.append(r2.json()["id"])

        # expired: end_date in past
        r3 = self._make_contract(super_token, lab["id"],
                                 (today - timedelta(days=400)).isoformat(),
                                 (today - timedelta(days=10)).isoformat())
        assert r3.status_code == 200
        assert r3.json()["effective_status"] == "expired"
        TestContracts.created_ids.append(r3.json()["id"])

        # terminated: create active then terminate
        r4 = self._make_contract(super_token, lab["id"],
                                 (today - timedelta(days=5)).isoformat(),
                                 (today + timedelta(days=300)).isoformat())
        assert r4.status_code == 200
        cid = r4.json()["id"]
        TestContracts.created_ids.append(cid)
        tr = requests.post(f"{API}/contracts/admin/{cid}/terminate", headers=_h(super_token),
                           json={"reason": "TEST_TERMINATE_REASON"}, timeout=30)
        assert tr.status_code == 200, tr.text
        assert tr.json()["effective_status"] == "terminated"

    def test_admin_list_filter(self, super_token):
        r = requests.get(f"{API}/contracts/admin?status=active", headers=_h(super_token), timeout=30)
        assert r.status_code == 200
        items = r.json()
        for c in items:
            assert c["effective_status"] == "active"

    def test_admin_detail_404(self, super_token):
        r = requests.get(f"{API}/contracts/admin/nonexistent-cid", headers=_h(super_token), timeout=30)
        assert r.status_code == 404

    def test_extend_moves_to_active(self, super_token, demo_labels):
        lab = demo_labels.get("Khizanah Kreasi Gontor")
        today = datetime.now(timezone.utc).date()
        # create expired
        r = self._make_contract(super_token, lab["id"],
                                (today - timedelta(days=400)).isoformat(),
                                (today - timedelta(days=10)).isoformat())
        assert r.status_code == 200
        cid = r.json()["id"]
        TestContracts.created_ids.append(cid)
        assert r.json()["effective_status"] == "expired"

        # extend to active
        new_end = (today + timedelta(days=365)).isoformat()
        er = requests.post(f"{API}/contracts/admin/{cid}/extend", headers=_h(super_token),
                           json={"new_end_date": new_end}, timeout=30)
        assert er.status_code == 200, er.text
        assert er.json()["effective_status"] == "active"

        # invalid extend (before start_date)
        bad = (today - timedelta(days=500)).isoformat()
        er2 = requests.post(f"{API}/contracts/admin/{cid}/extend", headers=_h(super_token),
                            json={"new_end_date": bad}, timeout=30)
        assert er2.status_code == 400

    def test_label_scope_isolation(self, super_token, demo_labels):
        khizanah = demo_labels.get("Khizanah Kreasi Gontor")
        manawa = demo_labels.get("Manawa Music")
        kt, _ = _label_token(khizanah)
        mt, _ = _label_token(manawa)
        kr = requests.get(f"{API}/contracts/label", headers=_h(kt), timeout=30)
        mr = requests.get(f"{API}/contracts/label", headers=_h(mt), timeout=30)
        assert kr.status_code == 200 and mr.status_code == 200
        for c in kr.json():
            assert c["label_id"] == khizanah["id"], "Khizanah saw foreign contract"
        for c in mr.json():
            assert c["label_id"] == manawa["id"], "Manawa saw foreign contract"

    def test_contract_creates_notification(self, super_token, demo_labels):
        lab = demo_labels.get("Mustafa Kamal")
        ltok, _ = _label_token(lab)
        # baseline unread
        before = requests.get(f"{API}/notifications/me", headers=_h(ltok), timeout=30).json()["unread_count"]
        today = datetime.now(timezone.utc).date()
        r = self._make_contract(super_token, lab["id"],
                                (today - timedelta(days=1)).isoformat(),
                                (today + timedelta(days=400)).isoformat())
        assert r.status_code == 200
        cid = r.json()["id"]
        TestContracts.created_ids.append(cid)
        time.sleep(0.5)
        notif = requests.get(f"{API}/notifications/me", headers=_h(ltok), timeout=30).json()
        assert notif["unread_count"] >= before + 1, f"unread_count did not increase: {before} → {notif['unread_count']}"
        types = [n["type"] for n in notif["items"]]
        assert "contract_created" in types

        # extend
        er = requests.post(f"{API}/contracts/admin/{cid}/extend", headers=_h(super_token),
                           json={"new_end_date": (today + timedelta(days=500)).isoformat()}, timeout=30)
        assert er.status_code == 200
        time.sleep(0.5)
        notif2 = requests.get(f"{API}/notifications/me", headers=_h(ltok), timeout=30).json()
        types2 = [n["type"] for n in notif2["items"]]
        assert "contract_extended" in types2

        # terminate
        tr = requests.post(f"{API}/contracts/admin/{cid}/terminate", headers=_h(super_token),
                           json={"reason": "TEST_PHASE4"}, timeout=30)
        assert tr.status_code == 200
        time.sleep(0.5)
        notif3 = requests.get(f"{API}/notifications/me", headers=_h(ltok), timeout=30).json()
        types3 = [n["type"] for n in notif3["items"]]
        assert "contract_terminated" in types3


# ---------------------------------------------------------------------------
# 3) Blacklist
# ---------------------------------------------------------------------------
class TestBlacklist:
    def test_finance_cannot_blacklist(self, finance_token, demo_labels):
        lab = demo_labels.get("WANWE RECORDS")
        if not lab:
            pytest.skip("WANWE RECORDS not seeded")
        r = requests.post(f"{API}/admin/labels/{lab['id']}/blacklist", headers=_h(finance_token),
                          json={"reason": "TEST_should_fail"}, timeout=30)
        assert r.status_code == 403, r.text

    def test_blacklist_blocks_login_then_unblock(self, super_token, demo_labels):
        lab = demo_labels.get("WANWE RECORDS")
        if not lab:
            pytest.skip("WANWE RECORDS not seeded")
        email = lab.get("email")
        # blacklist
        reason = "TEST_PHASE4_BLACKLIST_REASON"
        r = requests.post(f"{API}/admin/labels/{lab['id']}/blacklist", headers=_h(super_token),
                          json={"reason": reason}, timeout=30)
        assert r.status_code == 200, r.text

        # login attempt
        lr = _login(email, DEMO_PASSWORD)
        assert lr.status_code == 403, f"Expected 403 got {lr.status_code} {lr.text}"
        body = lr.json()
        detail = body.get("detail", "")
        assert detail.startswith("Akun di-blacklist. Alasan:"), f"Unexpected detail: {detail}"
        assert reason in detail

        # unblock
        ur = requests.post(f"{API}/admin/labels/{lab['id']}/unblacklist", headers=_h(super_token), timeout=30)
        assert ur.status_code == 200

        # login OK
        lr2 = _login(email, DEMO_PASSWORD)
        assert lr2.status_code == 200, lr2.text


# ---------------------------------------------------------------------------
# 4) Notifications CRUD + isolation
# ---------------------------------------------------------------------------
class TestNotifications:
    def test_me_returns_shape(self, super_token):
        r = requests.get(f"{API}/notifications/me", headers=_h(super_token), timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data and "unread_count" in data
        assert isinstance(data["items"], list)
        assert isinstance(data["unread_count"], int)

    def test_cross_user_mark_read_404(self, super_token, demo_labels, finance_token):
        # Create a contract notification for a label
        lab = demo_labels.get("Mustafa Kamal") or demo_labels.get("Khizanah Kreasi Gontor")
        if not lab:
            pytest.skip("No label available")
        today = datetime.now(timezone.utc).date()
        payload = {
            "label_id": lab["id"],
            "file_url": "/api/files/contract/x.pdf",
            "filename": "iso.pdf",
            "start_date": (today - timedelta(days=1)).isoformat(),
            "end_date": (today + timedelta(days=200)).isoformat(),
            "notes": "TEST_ISO",
        }
        cr = requests.post(f"{API}/contracts/admin", headers=_h(super_token), json=payload, timeout=30)
        assert cr.status_code == 200
        time.sleep(0.5)
        ltok, _ = _label_token(lab)
        my = requests.get(f"{API}/notifications/me", headers=_h(ltok), timeout=30).json()
        assert my["items"], "Label should have at least one notification"
        target_nid = my["items"][0]["id"]
        # finance_token tries to mark label's notification
        r = requests.post(f"{API}/notifications/mark-read/{target_nid}", headers=_h(finance_token), timeout=30)
        assert r.status_code == 404

    def test_mark_read_and_mark_all_read(self, super_token, demo_labels):
        lab = demo_labels.get("Khizanah Kreasi Gontor")
        ltok, _ = _label_token(lab)
        my = requests.get(f"{API}/notifications/me", headers=_h(ltok), timeout=30).json()
        if not my["items"]:
            pytest.skip("No notifications to mark read")
        nid = my["items"][0]["id"]
        r = requests.post(f"{API}/notifications/mark-read/{nid}", headers=_h(ltok), timeout=30)
        assert r.status_code == 200

        ra = requests.post(f"{API}/notifications/mark-all-read", headers=_h(ltok), timeout=30)
        assert ra.status_code == 200
        after = requests.get(f"{API}/notifications/me", headers=_h(ltok), timeout=30).json()
        assert after["unread_count"] == 0

    def _get_release_id(self, ltok):
        r = requests.get(f"{API}/releases", headers=_h(ltok), timeout=30)
        if r.status_code != 200:
            return None
        data = r.json()
        items = data if isinstance(data, list) else (data.get("items") or [])
        return items[0]["id"] if items else None

    def _ensure_release(self, ltok):
        rid = self._get_release_id(ltok)
        if rid:
            return rid
        # Create a draft release
        from datetime import date, timedelta as _td
        future = (date.today() + _td(days=30)).isoformat()
        payload = {
            "release_title": "TEST_PHASE4_DRAFT",
            "release_type": "single",
            "artist_name": "TEST Artist",
            "release_date": future,
            "year": date.today().year,
            "genre": "Pop",
            "language": "Indonesian",
            "explicit": False,
        }
        r = requests.post(f"{API}/releases/draft", headers=_h(ltok), json=payload, timeout=30)
        if r.status_code in (200, 201):
            return r.json().get("id") or r.json().get("release_id")
        return None

    def _create_ticket(self, ltok, subject):
        rid = self._ensure_release(ltok)
        if not rid:
            pytest.skip("No releases available and cannot create draft")
        payload = {
            "release_id": rid,
            "subject": subject,
            "category": "other",
            "priority": "low",
            "description": "TEST ping ping ping",
        }
        return requests.post(f"{API}/tickets/label/create", headers=_h(ltok), json=payload, timeout=30)

    def test_ticket_comment_notifies_label(self, super_token, demo_labels):
        lab = demo_labels.get("Khizanah Kreasi Gontor")
        ltok, _ = _label_token(lab)
        cr = self._create_ticket(ltok, "TEST_NOTIF")
        assert cr.status_code in (200, 201), cr.text
        tid = cr.json()["id"]
        # admin comments
        ac = requests.post(f"{API}/tickets/{tid}/comment", headers=_h(super_token),
                           json={"body": "TEST admin reply"}, timeout=30)
        assert ac.status_code in (200, 201), ac.text
        time.sleep(0.5)
        notif = requests.get(f"{API}/notifications/me", headers=_h(ltok), timeout=30).json()
        types = [n["type"] for n in notif["items"]]
        assert "ticket_update" in types

    def test_ticket_status_change_notifies_label(self, super_token, demo_labels):
        lab = demo_labels.get("Khizanah Kreasi Gontor")
        ltok, _ = _label_token(lab)
        cr = self._create_ticket(ltok, "TEST_STATUS")
        assert cr.status_code in (200, 201), cr.text
        tid = cr.json()["id"]
        sc = requests.post(f"{API}/tickets/admin/{tid}/status", headers=_h(super_token),
                           json={"status": "in_progress"}, timeout=30)
        assert sc.status_code in (200, 201), sc.text
        time.sleep(0.5)
        notif = requests.get(f"{API}/notifications/me", headers=_h(ltok), timeout=30).json()
        types = [n["type"] for n in notif["items"]]
        assert "ticket_update" in types

    def test_label_comment_notifies_admin(self, super_token, support_token, demo_labels):
        lab = demo_labels.get("Khizanah Kreasi Gontor")
        ltok, _ = _label_token(lab)
        cr = self._create_ticket(ltok, "TEST_LABEL_COMMENT")
        assert cr.status_code in (200, 201), cr.text
        tid = cr.json()["id"]
        # baseline support unread
        before = requests.get(f"{API}/notifications/me", headers=_h(support_token), timeout=30).json()["unread_count"]
        # label comments
        lc = requests.post(f"{API}/tickets/{tid}/comment", headers=_h(ltok),
                           json={"body": "TEST label reply"}, timeout=30)
        assert lc.status_code in (200, 201), lc.text
        time.sleep(0.5)
        after = requests.get(f"{API}/notifications/me", headers=_h(support_token), timeout=30).json()
        assert after["unread_count"] >= before + 1, f"Support unread did not grow: {before}->{after['unread_count']}"
        types = [n["type"] for n in after["items"]]
        assert "ticket_update" in types
