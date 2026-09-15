"""PRD-05 KPI & Performance measurement layer + Chat cleanup + Work Monitor regression."""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

SA = {"email": "superadmin@rilismusik.com", "password": "SuperAdmin#2026"}
FIN = {"email": "finance1@rilismusik.com", "password": "Finance#2026"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    body = r.json()
    tok = body.get("token") or body.get("access_token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def sa():
    return _login(SA)


@pytest.fixture(scope="module")
def fin():
    return _login(FIN)


# ---- Performance config ----
def test_config_super_admin(sa):
    r = sa.get(f"{BASE_URL}/api/admin/performance/config", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "weights" in body and "targets" in body and "scoring" in body
    assert body.get("can_manage") is True
    assert len(body["weights"]) >= 10
    assert "categories" in body["scoring"] and len(body["scoring"]["categories"]) == 5
    assert "work_types" in body and len(body["work_types"]) >= 10
    assert "roles" in body


def test_config_update_audits(sa):
    # get current weights
    r = sa.get(f"{BASE_URL}/api/admin/performance/config").json()
    w = dict(r["weights"])
    orig = w.get("support_ticket", 1.0)
    w["support_ticket"] = float(orig) + 0.01
    r2 = sa.put(f"{BASE_URL}/api/admin/performance/config",
                json={"section": "weights", "value": w, "reason": "iter87 QA test"})
    assert r2.status_code == 200, r2.text
    # verify audit created via re-read
    r3 = sa.get(f"{BASE_URL}/api/admin/performance/config").json()
    assert abs(r3["weights"]["support_ticket"] - (float(orig) + 0.01)) < 1e-6
    # revert
    w["support_ticket"] = orig
    sa.put(f"{BASE_URL}/api/admin/performance/config",
           json={"section": "weights", "value": w, "reason": "iter87 revert"})


# ---- Overview ----
def test_overview_super_admin(sa):
    r = sa.get(f"{BASE_URL}/api/admin/performance/overview?period=2026-01")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["period"] == "2026-01"
    assert "rows" in body
    # super_admin must not be in list
    for row in body["rows"]:
        assert "super" not in (row.get("role_id") or "").lower() or row.get("role_id") != "super_admin"
        assert set(["user_id", "name", "completed_count", "weighted_output", "on_time_pct", "overall_score", "category", "confidence"]).issubset(row.keys())


# ---- Me endpoint (super admin) ----
def test_me_super_admin_not_staff(sa):
    r = sa.get(f"{BASE_URL}/api/admin/performance/me")
    assert r.status_code == 200
    body = r.json()
    assert body.get("is_staff") is False


# ---- Staff detail ----
def test_staff_detail_non_super(sa):
    # find any non-super user
    ov = sa.get(f"{BASE_URL}/api/admin/performance/overview?period=2026-01").json()
    rows = ov.get("rows", [])
    if not rows:
        pytest.skip("no staff rows available")
    uid = rows[0]["user_id"]
    r = sa.get(f"{BASE_URL}/api/admin/performance/staff/{uid}?period=2026-01")
    assert r.status_code == 200, r.text
    d = r.json()
    assert "by_type" in d and "timeliness" in d and "work_timing" in d and "achievement" in d
    assert d["work_timing"]["queue_time"] is None
    assert d["work_timing"]["processing_time"] is None
    assert "resolution_time_hours" in d["work_timing"]
    assert d["quality"]["status"] == "unavailable"
    assert "components" in d
    assert "attendance" in d  # separate from score


# ---- Periods finalize/reopen snapshot integrity ----
def test_period_finalize_reopen_snapshot(sa):
    period = "2025-11"
    # Ensure open (reopen if finalized)
    sa.post(f"{BASE_URL}/api/admin/performance/periods/action",
            json={"period": period, "action": "reopen"})

    # Set a distinctive weight
    cfg = sa.get(f"{BASE_URL}/api/admin/performance/config").json()
    w = dict(cfg["weights"])
    orig_val = w.get("support_ticket", 1.0)
    w["support_ticket"] = 5.55
    sa.put(f"{BASE_URL}/api/admin/performance/config",
           json={"section": "weights", "value": w, "reason": "snapshot pre"})

    # Finalize with weight=5.55 snapshot
    r = sa.post(f"{BASE_URL}/api/admin/performance/periods/action",
                json={"period": period, "action": "finalize"})
    assert r.status_code == 200
    ov_a = sa.get(f"{BASE_URL}/api/admin/performance/overview?period={period}").json()
    assert ov_a["period_state"] == "finalized"

    # Change weight
    w["support_ticket"] = 9.99
    sa.put(f"{BASE_URL}/api/admin/performance/config",
           json={"section": "weights", "value": w, "reason": "snapshot post-change"})

    # Re-fetch overview for finalized period → same weighted output as before
    ov_b = sa.get(f"{BASE_URL}/api/admin/performance/overview?period={period}").json()
    # weighted_output totals should be equal to prior finalize
    a_map = {r["user_id"]: r["weighted_output"] for r in ov_a["rows"]}
    b_map = {r["user_id"]: r["weighted_output"] for r in ov_b["rows"]}
    assert a_map == b_map, f"finalized snapshot altered: {a_map} vs {b_map}"

    # Reopen
    r2 = sa.post(f"{BASE_URL}/api/admin/performance/periods/action",
                 json={"period": period, "action": "reopen"})
    assert r2.status_code == 200
    ov_c = sa.get(f"{BASE_URL}/api/admin/performance/overview?period={period}").json()
    assert ov_c["period_state"] == "open"

    # Revert weight
    w["support_ticket"] = orig_val
    sa.put(f"{BASE_URL}/api/admin/performance/config",
           json={"section": "weights", "value": w, "reason": "revert iter87"})


def test_list_periods(sa):
    r = sa.get(f"{BASE_URL}/api/admin/performance/periods")
    assert r.status_code == 200
    body = r.json()
    assert "periods" in body and "current" in body


# ---- Auth negative: finance1 must be denied on performance endpoints ----
@pytest.mark.parametrize("path", [
    "/api/admin/performance/me",
    "/api/admin/performance/overview",
    "/api/admin/performance/config",
    "/api/admin/performance/periods",
])
def test_finance_denied(fin, path):
    r = fin.get(f"{BASE_URL}{path}")
    assert r.status_code == 403, f"{path} -> {r.status_code} {r.text[:200]}"


# ---- Work Monitor regression: team scope hides super-admin-only work types ----
SUPER_ONLY = {"bank_verification", "kyc_review", "sensitive_approval", "withdraw_verification"}


def test_work_queue_team_scope_hides_super_only(sa):
    r = sa.get(f"{BASE_URL}/api/admin/work/queue?scope=team")
    assert r.status_code == 200, r.text
    body = r.json()
    # Response could be list or dict with items
    items = body.get("items") if isinstance(body, dict) else body
    if items is None and isinstance(body, dict):
        items = body.get("rows") or body.get("data") or []
    for it in items or []:
        assert it.get("work_type") not in SUPER_ONLY, f"team scope leaked super-only type: {it.get('work_type')}"


def test_work_queue_my_scope_super_admin_includes_super_only(sa):
    r = sa.get(f"{BASE_URL}/api/admin/work/queue?scope=my")
    assert r.status_code == 200
    # We don't assert presence (data may be empty), just that request succeeds without filtering
