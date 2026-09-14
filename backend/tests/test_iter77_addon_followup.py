"""Iter77 - Add-on follow-up: RBAC addon.view/manage, action-center, catalog move, file delivery."""
import io
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


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login {r.status_code} {r.text}"
    tok = r.json().get("token") or r.json().get("access_token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def label():
    return _login(LABEL)


# --- RBAC ---
def test_navigation_has_addon_manage(admin):
    r = admin.get(f"{BASE}/api/admin/navigation", timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    perms = d.get("permissions") or []
    assert "addon.manage" in perms, f"addon.manage missing: {perms}"
    assert "addon.view" in perms
    # nav item addon_orders permission = addon.view
    items = d.get("items") or d.get("navigation") or []
    addon_item = next((i for i in items if i.get("key") == "addon_orders"), None)
    assert addon_item, f"addon_orders nav item missing: {items}"
    assert addon_item.get("permission") == "addon.view", addon_item


def test_access_catalog_has_addon_module(admin):
    r = admin.get(f"{BASE}/api/admin/access/catalog", timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    modules = d.get("modules") or d
    if isinstance(modules, dict):
        modules = modules.get("modules", modules)
    addon_mod = None
    for m in modules if isinstance(modules, list) else []:
        if m.get("key") == "addon" or m.get("id") == "addon":
            addon_mod = m
            break
    assert addon_mod, f"addon module not in access catalog: {modules}"
    action_keys = [a.get("key") if isinstance(a, dict) else a for a in (addon_mod.get("actions") or [])]
    # actions may be tuples/strings — flatten
    flat = []
    for a in addon_mod.get("actions") or []:
        if isinstance(a, dict):
            flat.append(a.get("key") or a.get("permission"))
        elif isinstance(a, (list, tuple)):
            flat.append(a[0])
        else:
            flat.append(a)
    assert "addon.view" in flat and "addon.manage" in flat, flat
    # Should NOT be an "approval" workflow — no approve/request keys under addon
    approval = [k for k in flat if k and (".approve" in k or ".request" in k)]
    assert not approval, f"addon should be direct, found approval keys: {approval}"


# --- Action center ---
def test_action_center_has_addon_orders(admin):
    r = admin.get(f"{BASE}/api/admin/action-center", timeout=30)
    assert r.status_code == 200, r.text
    items = r.json().get("items") or []
    entry = next((i for i in items if i.get("key") == "addon_orders"), None)
    assert entry, f"addon_orders missing in action-center: {items}"
    assert entry.get("link") == "/admin/addon-orders"
    assert entry.get("permission") == "addon.view"
    assert entry.get("count", 0) >= 3, entry


# --- Catalog CRUD via addon.manage ---
def test_admin_products_list_and_create_file(admin):
    r = admin.get(f"{BASE}/api/payments/admin/products", timeout=30)
    assert r.status_code == 200, r.text
    payload = {"name": "TEST_addon_iter77", "description": "test", "amount": 12345, "delivery_type": "file"}
    c = admin.post(f"{BASE}/api/payments/admin/products", json=payload, timeout=30)
    assert c.status_code in (200, 201), c.text
    prod = c.json()
    assert prod.get("delivery_type") == "file"
    pid = prod["id"]

    # invalid delivery_type via PATCH => 400
    bad = admin.patch(f"{BASE}/api/payments/admin/products/{pid}", json={"delivery_type": "bogus"}, timeout=30)
    assert bad.status_code == 400, bad.text

    # valid patch to link
    ok = admin.patch(f"{BASE}/api/payments/admin/products/{pid}", json={"delivery_type": "link", "active": False}, timeout=30)
    assert ok.status_code == 200, ok.text
    assert ok.json().get("delivery_type") == "link"

    # delete
    d = admin.delete(f"{BASE}/api/payments/admin/products/{pid}", timeout=30)
    assert d.status_code in (200, 204), d.text


# --- File delivery endpoint ---
def test_delivery_file_flow(admin):
    # find visualizer (file) pending order for demo_vip
    r = admin.get(f"{BASE}/api/admin/addon-orders", timeout=30)
    assert r.status_code == 200
    items = r.json()["items"]
    file_orders = [o for o in items if o.get("delivery_type") == "file" and o.get("status") in ("pending", "in_progress")]
    if not file_orders:
        pytest.skip(f"No open file-delivery order to test (items: {len(items)})")
    order = file_orders[0]
    oid = order["id"]

    # bad extension
    bad = admin.post(
        f"{BASE}/api/admin/addon-orders/{oid}/delivery-file",
        files={"file": ("bad.exe", io.BytesIO(b"x"), "application/octet-stream")}, timeout=30)
    assert bad.status_code == 400, bad.text

    # good upload
    good = admin.post(
        f"{BASE}/api/admin/addon-orders/{oid}/delivery-file",
        files={"file": ("result.mp4", io.BytesIO(b"\x00\x00fake"), "video/mp4")}, timeout=60)
    assert good.status_code == 200, good.text
    body = good.json()
    assert body["status"] == "delivered"
    assert body["delivery_url"].startswith("/api/files/")
    assert body.get("delivery_filename") == "result.mp4"


def test_delivery_file_rejects_cancelled(admin):
    # Create a synthetic scenario: find any order, cancel it, then try upload
    r = admin.get(f"{BASE}/api/admin/addon-orders?status=pending", timeout=30)
    items = r.json()["items"]
    if not items:
        pytest.skip("No pending to cancel")
    oid = items[0]["id"]
    cx = admin.patch(f"{BASE}/api/admin/addon-orders/{oid}/status", json={"status": "cancelled"}, timeout=30)
    assert cx.status_code == 200
    up = admin.post(
        f"{BASE}/api/admin/addon-orders/{oid}/delivery-file",
        files={"file": ("a.mp4", io.BytesIO(b"x"), "video/mp4")}, timeout=30)
    assert up.status_code == 409, up.text


# --- Label visibility ---
def test_label_addon_orders(label):
    r = label.get(f"{BASE}/api/label/addon-orders", timeout=30)
    if r.status_code == 403:
        pytest.skip(f"label gated: {r.text[:120]}")
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert len(items) >= 1
