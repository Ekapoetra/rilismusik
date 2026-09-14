"""Iter76 - Add-on Orders (admin + label + backfill + work queue)"""
import os
import pytest
import requests

def _load_env():
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass
    return os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

BASE = _load_env()
ADMIN = {"email": "superadmin@rilismusik.com", "password": "SuperAdmin#2026"}
LABEL = {"email": "demo_vip@rilismusik.com", "password": "DemoVIP#2026"}
DEMO_RELEASE_ID = "2110e419-46a3-4911-9a2b-dd5aed48b88d"


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    data = r.json()
    token = data.get("token") or data.get("access_token")
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def label():
    return _login(LABEL)


def test_admin_list(admin):
    r = admin.get(f"{BASE}/api/admin/addon-orders", timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "items" in d and "counts" in d and "flow" in d and "labels" in d
    assert d["flow"] == ["pending", "in_progress", "delivered", "completed"]
    assert isinstance(d["items"], list) and len(d["items"]) >= 3
    # Each item should have status_label + label/release info
    for it in d["items"]:
        assert "status" in it and "status_label" in it
    # filter
    r2 = admin.get(f"{BASE}/api/admin/addon-orders?status=pending", timeout=30)
    assert r2.status_code == 200
    for it in r2.json()["items"]:
        assert it["status"] == "pending"


def test_backfill_idempotent(admin):
    r1 = admin.post(f"{BASE}/api/admin/addon-orders/backfill", timeout=60)
    assert r1.status_code == 200, r1.text
    d1 = r1.json()
    assert "scanned_payments" in d1 and "orders_created" in d1
    r2 = admin.post(f"{BASE}/api/admin/addon-orders/backfill", timeout=60)
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["orders_created"] == 0, f"backfill not idempotent: {d2}"


def test_label_sees_only_own(label):
    r = label.get(f"{BASE}/api/label/addon-orders", timeout=30)
    if r.status_code == 403 and "KYC" in r.text:
        pytest.skip(f"Label endpoint gated by KYC (demo_vip missing bank): {r.text}")
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert len(items) >= 3
    label_ids = {it["label_id"] for it in items}
    assert len(label_ids) == 1
    # release filter
    r2 = label.get(f"{BASE}/api/label/addon-orders?release_id={DEMO_RELEASE_ID}", timeout=30)
    assert r2.status_code == 200
    for it in r2.json()["items"]:
        assert it["release_id"] == DEMO_RELEASE_ID


def test_status_lifecycle_and_delivery(admin, label):
    # find a pending order for demo label
    r = admin.get(f"{BASE}/api/admin/addon-orders?status=pending", timeout=30)
    pendings = [o for o in r.json()["items"] if "demo_vip" in (o.get("label_name") or "").lower() or "Demo Label VIP" in (o.get("label_name") or "")]
    if not pendings:
        pendings = [o for o in r.json()["items"] if o.get("status") == "pending"]
    assert pendings, "No pending demo order"
    order_id = pendings[0]["id"]

    # backward move should fail: try delivered->pending on an in_progress one
    r_ip = admin.get(f"{BASE}/api/admin/addon-orders?status=in_progress", timeout=30)
    ip_items = r_ip.json()["items"]
    if ip_items:
        back = admin.patch(f"{BASE}/api/admin/addon-orders/{ip_items[0]['id']}/status",
                           json={"status": "pending"}, timeout=30)
        assert back.status_code == 409, f"expected 409, got {back.status_code} {back.text}"

    # forward: pending -> in_progress
    r1 = admin.patch(f"{BASE}/api/admin/addon-orders/{order_id}/status",
                     json={"status": "in_progress"}, timeout=30)
    assert r1.status_code == 200, r1.text
    assert r1.json()["status"] == "in_progress"

    # invalid delivery URL
    bad = admin.patch(f"{BASE}/api/admin/addon-orders/{order_id}/delivery",
                      json={"delivery_url": "ftp://bad.example"}, timeout=30)
    assert bad.status_code == 400, bad.text

    # good delivery URL auto-advances to delivered
    good = admin.patch(f"{BASE}/api/admin/addon-orders/{order_id}/delivery",
                       json={"delivery_url": "https://example.com/result.mp4",
                             "delivery_note": "Test hasil"}, timeout=30)
    assert good.status_code == 200, good.text
    body = good.json()
    assert body["status"] == "delivered"
    assert body["delivery_url"] == "https://example.com/result.mp4"

    # advance to completed
    r2 = admin.patch(f"{BASE}/api/admin/addon-orders/{order_id}/status",
                     json={"status": "completed"}, timeout=30)
    assert r2.status_code == 200
    assert r2.json()["status"] == "completed"

    # terminal: further changes rejected
    r3 = admin.patch(f"{BASE}/api/admin/addon-orders/{order_id}/status",
                     json={"status": "in_progress"}, timeout=30)
    assert r3.status_code == 409

    # delivery on completed (terminal but not cancelled) - endpoint only rejects cancelled;
    # this is allowed per code. Verify.
    # Label should see the delivery url
    lr = label.get(f"{BASE}/api/label/addon-orders?release_id={DEMO_RELEASE_ID}", timeout=30)
    if lr.status_code == 200:
        urls = [it.get("delivery_url") for it in lr.json()["items"]]
        assert any(u == "https://example.com/result.mp4" for u in urls)
    else:
        print(f"[label endpoint blocked: {lr.status_code} {lr.text[:120]}]")


def test_work_queue_addon_processing(admin):
    r = admin.get(f"{BASE}/api/admin/work/queue?scope=team", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    # look for addon_processing entry
    items = data.get("items") or data.get("queue") or data
    if isinstance(items, dict):
        items = items.get("items", [])
    found = None
    for it in items:
        if it.get("work_type") == "addon_processing" or it.get("type") == "addon_processing":
            found = it
            break
    assert found is not None, f"addon_processing not in work queue: {data}"
    assert (found.get("open_count") or found.get("count") or 0) >= 1
