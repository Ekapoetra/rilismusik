"""
Iter78 backend tests: release_go_live work type + not_live ticket category + label live_today.
"""
import os
import pytest
import requests
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
SUPER = {"email": "superadmin@rilismusik.com", "password": "SuperAdmin#2026"}
LABEL = {"email": "demo_vip@rilismusik.com", "password": "DemoVIP#2026"}

RELEASE_GO_LIVE_ID = "2110e419-46a3-4911-9a2b-dd5aed48b88d"
RELEASE_LIVE_TODAY_ID = "758c0421-2811-4952-a3a8-c2c884c1dcf2"


def _login(sess: requests.Session, creds):
    r = sess.post(f"{BASE_URL}/api/auth/login", json=creds)
    assert r.status_code == 200, f"login failed {r.status_code}: {r.text}"
    tok = r.json().get("access_token") or r.json().get("token")
    if tok:
        sess.headers.update({"Authorization": f"Bearer {tok}"})
    return r.json()


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    _login(s, SUPER)
    return s


@pytest.fixture(scope="module")
def label():
    s = requests.Session()
    _login(s, LABEL)
    return s


# ---- Feature A: work queue + action center ----
class TestWorkQueue:
    def test_work_queue_has_release_go_live(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/work/queue?scope=team")
        assert r.status_code == 200, r.text
        data = r.json()
        items = data.get("items") or []
        found = next((it for it in items if it.get("work_type") == "release_go_live"), None)
        assert found is not None, f"release_go_live not in queue"
        # open_count may be 0 if seed release was already marked live in prior run
        assert found.get("open_count", -1) >= 0
        assert found.get("permission") == "releases.review"
        assert "Admin Rilisan" in (found.get("responsible_roles") or [])

    def test_action_center_release_go_live(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/action-center")
        assert r.status_code == 200, r.text
        payload = r.json()
        items = payload.get("items") if isinstance(payload, dict) else payload
        keys = {it.get("key"): it for it in items} if isinstance(items, list) else {}
        # If seed already consumed, action-center may exclude count=0 items; skip check
        if "release_go_live" not in keys:
            pytest.skip("release_go_live seed already consumed; action-center only shows count>0")
        it = keys["release_go_live"]
        assert it.get("count", 0) >= 1
        assert "/admin/releases" in (it.get("link") or "")
        assert "delivered" in (it.get("link") or "")


# ---- Feature B: cron ----
class TestCron:
    def test_cron_release_live_check(self, admin):
        r = admin.post(f"{BASE_URL}/api/admin/cron/release-live-check")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        # due may be 0 if seed already fulfilled
        assert body.get("due", -1) >= 0
        assert "notified" in body


# ---- Feature C: mark_live fulfillment ----
class TestMarkLive:
    def test_mark_live_reduces_queue(self, admin):
        # 1. Get initial open count
        r0 = admin.get(f"{BASE_URL}/api/admin/work/queue?scope=team")
        items0 = r0.json().get("items") or []
        oc0 = 0
        for it in items0:
            if it.get("work_type") == "release_go_live":
                oc0 = it.get("open_count") or 0
                break

        # 2. Fetch release detail to get track IDs
        rd = admin.get(f"{BASE_URL}/api/releases/{RELEASE_GO_LIVE_ID}")
        assert rd.status_code == 200, rd.text
        rel = rd.json()
        tracks = rel.get("tracks") or []
        assert tracks, "no tracks on release"
        today_wib = (datetime.now(timezone.utc) + timedelta(hours=7)).date().isoformat()
        # Only mark_live if not already live
        if rel.get("status") == "live":
            pytest.skip("release already live from a previous test run")
        track_isrcs = {t["id"]: f"IDQA1250000{i+1}" for i, t in enumerate(tracks)}
        payload = {"action": "mark_live", "upc": "QATEST0000001",
                   "track_isrcs": track_isrcs, "release_date": today_wib}
        r = admin.post(f"{BASE_URL}/api/releases/{RELEASE_GO_LIVE_ID}/admin/action", json=payload)
        assert r.status_code == 200, r.text

        # 3. Verify release status
        rd2 = admin.get(f"{BASE_URL}/api/releases/{RELEASE_GO_LIVE_ID}")
        assert rd2.json().get("status") == "live"

        # 4. Verify queue count decreased (allow brief cache — retry up to 5s)
        import time
        oc1 = oc0
        for _ in range(6):
            r1 = admin.get(f"{BASE_URL}/api/admin/work/queue?scope=team")
            items1 = r1.json().get("items") or []
            oc1 = 0
            for it in items1:
                if it.get("work_type") == "release_go_live":
                    oc1 = it.get("open_count") or 0
                    break
            if oc1 == oc0 - 1:
                break
            time.sleep(1)
        assert oc1 == oc0 - 1, f"expected {oc0-1}, got {oc1}"


# ---- Feature D: not_live ticket ----
class TestNotLiveTicket:
    def test_categories_include_not_live(self, label):
        r = label.get(f"{BASE_URL}/api/tickets/categories")
        assert r.status_code == 200, r.text
        data = r.json()
        cats = data if isinstance(data, list) else data.get("categories") or []
        values = [c.get("value") if isinstance(c, dict) else c for c in cats]
        assert "not_live" in values, f"not_live not in categories: {values}"

    def test_create_not_live_ticket(self, label):
        payload = {"category": "not_live",
                   "release_id": RELEASE_LIVE_TODAY_ID,
                   "message": "TEST_not_live automated test ticket"}
        r = label.post(f"{BASE_URL}/api/tickets/label/create", json=payload)
        assert r.status_code in (200, 201), r.text
        data = r.json()
        ticket_id = data.get("id") or data.get("ticket_id") or (data.get("ticket") or {}).get("id")
        assert ticket_id, f"no ticket id: {data}"
        assert (data.get("category") or (data.get("ticket") or {}).get("category")) == "not_live"

    def test_admin_sees_not_live_ticket(self, admin):
        # action-center tickets count
        r = admin.get(f"{BASE_URL}/api/admin/action-center")
        items = r.json().get("items") or []
        by_key = {it.get("key"): it for it in items}
        assert "tickets" in by_key
        assert by_key["tickets"].get("count", 0) >= 1

        # work queue support_ticket
        r2 = admin.get(f"{BASE_URL}/api/admin/work/queue?scope=team")
        items2 = r2.json().get("items") or []
        st = next((i for i in items2 if i.get("work_type") == "support_ticket"), None)
        assert st and (st.get("open_count") or 0) >= 1

        # admin ticket list contains a not_live ticket
        r3 = admin.get(f"{BASE_URL}/api/tickets/admin")
        assert r3.status_code == 200, r3.text
        body = r3.json()
        tickets = body if isinstance(body, list) else body.get("items") or body.get("tickets") or []
        cats = [t.get("category") for t in tickets]
        assert "not_live" in cats, f"categories: {set(cats)}"


# ---- Regression ----
class TestLabelDashboard:
    def test_label_dashboard_live_today(self, label):
        r = label.get(f"{BASE_URL}/api/label/dashboard")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "live_today" in data, f"live_today missing: keys={list(data)[:20]}"
        ids = [x.get("id") for x in (data.get("live_today") or [])]
        assert RELEASE_LIVE_TODAY_ID in ids, f"expected {RELEASE_LIVE_TODAY_ID} in {ids}"
