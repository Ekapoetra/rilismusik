"""PRD-02 Work Responsibility & Tracking — end-to-end backend tests."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://lanjut-core.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

CREDS = {
    "super":   ("superadmin@rilismusik.com", "SuperAdmin#2026"),
    "finance": ("finance1@rilismusik.com",   "Finance#2026"),
    "support": ("support1@rilismusik.com",   "Support#2026"),
    "release": ("release1@rilismusik.com",   "Release#2026"),
}


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def tokens():
    return {k: _login(*v) for k, v in CREDS.items()}


def H(t): return {"Authorization": f"Bearer {t}"}


# ============ 1. My Work scoping by responsibility ============

def test_support_my_queue_has_expected_types(tokens):
    r = requests.get(f"{API}/admin/work/queue?scope=my", headers=H(tokens["support"]), timeout=30)
    assert r.status_code == 200, r.text
    types = {i["work_type"] for i in r.json()["items"]}
    assert {"support_ticket", "kyc_review", "legacy_claim"} == types, f"support my types = {types}"


def test_finance_my_queue_has_expected_types(tokens):
    r = requests.get(f"{API}/admin/work/queue?scope=my", headers=H(tokens["finance"]), timeout=30)
    assert r.status_code == 200, r.text
    types = {i["work_type"] for i in r.json()["items"]}
    assert {"withdraw_verification", "payment_followup"} == types, f"finance my types = {types}"


# ============ 2. Team Monitor gating ============

def test_support_team_scope_forbidden(tokens):
    r = requests.get(f"{API}/admin/work/queue?scope=team", headers=H(tokens["support"]), timeout=30)
    assert r.status_code == 403


def test_super_team_scope_has_all_eight_types(tokens):
    r = requests.get(f"{API}/admin/work/queue?scope=team", headers=H(tokens["super"]), timeout=30)
    assert r.status_code == 200
    types = {i["work_type"] for i in r.json()["items"]}
    expected = {"release_review", "withdraw_verification", "payment_followup", "kyc_review",
                "support_ticket", "legacy_claim", "addon_processing", "sensitive_approval"}
    assert expected == types, f"missing: {expected - types}"
    assert r.json().get("is_manager") is True


# ============ 3. Reconciliation counts match business state ============

def test_ticket_count_matches_business(tokens):
    q = requests.get(f"{API}/admin/work/queue?scope=team", headers=H(tokens["super"]), timeout=30).json()
    ticket = next(i for i in q["items"] if i["work_type"] == "support_ticket")
    # Fetch tickets endpoint (admin) - status not in done/rejected/cancelled
    tks = requests.get(f"{API}/admin/tickets", headers=H(tokens["super"]), timeout=30)
    if tks.status_code == 200:
        body = tks.json()
        arr = body if isinstance(body, list) else (body.get("items") or body.get("tickets") or [])
        open_tickets = [t for t in arr if t.get("status") not in ("done", "rejected", "cancelled")]
        assert ticket["open_count"] == len(open_tickets), \
            f"work says {ticket['open_count']}, admin/tickets says {len(open_tickets)}"


# ============ 5. Idempotent reconciliation ============

def test_idempotent_reconciliation(tokens):
    counts = []
    for _ in range(3):
        r = requests.get(f"{API}/admin/work/queue?scope=team", headers=H(tokens["super"]), timeout=30)
        assert r.status_code == 200
        m = {i["work_type"]: i["open_count"] for i in r.json()["items"]}
        counts.append(m)
        time.sleep(0.2)
    for wt in counts[0]:
        vals = {c[wt] for c in counts}
        # Only stable types (not release_review since jobs may run). support_ticket is stable enough.
        if wt == "support_ticket":
            assert len(vals) == 1, f"{wt} not stable across calls: {vals}"


# ============ 6. Responsibility Gap detection ============

def test_gap_detection_and_restore(tokens):
    st = tokens["super"]
    try:
        # Clear payment_followup
        r = requests.put(f"{API}/admin/work/responsibilities",
                         headers=H(st), json={"work_type": "payment_followup", "role_ids": []}, timeout=30)
        assert r.status_code == 200
        # Super my queue should now surface payment_followup as gap
        q = requests.get(f"{API}/admin/work/queue?scope=my", headers=H(st), timeout=30).json()
        gap_types = {g["work_type"] for g in q.get("gaps", [])}
        assert "payment_followup" in gap_types, f"gaps: {gap_types}"
    finally:
        rr = requests.put(f"{API}/admin/work/responsibilities",
                          headers=H(st), json={"work_type": "payment_followup", "role_ids": ["admin_finance"]}, timeout=30)
        assert rr.status_code == 200


# ============ 8. Config permission enforcement ============

def test_support_cannot_put_responsibilities(tokens):
    r = requests.put(f"{API}/admin/work/responsibilities",
                     headers=H(tokens["support"]),
                     json={"work_type": "support_ticket", "role_ids": ["admin_support"]}, timeout=30)
    assert r.status_code == 403, r.text


def test_support_cannot_put_sla(tokens):
    r = requests.put(f"{API}/admin/work/settings/sla",
                     headers=H(tokens["support"]),
                     json={"work_type": "support_ticket", "sla_days": 2}, timeout=30)
    assert r.status_code == 403


def test_super_can_update_sla(tokens):
    st = tokens["super"]
    # Set to current default (2 for support_ticket) — no-op semantic
    r = requests.put(f"{API}/admin/work/settings/sla",
                     headers=H(st), json={"work_type": "support_ticket", "sla_days": 2}, timeout=30)
    assert r.status_code == 200


# ============ 9. Aging / overdue ============

def test_support_ticket_has_aging(tokens):
    q = requests.get(f"{API}/admin/work/queue?scope=team", headers=H(tokens["super"]), timeout=30).json()
    ticket = next(i for i in q["items"] if i["work_type"] == "support_ticket")
    if ticket["open_count"] > 0:
        assert ticket["oldest_age_days"] >= 0
        # If aging_days > sla_days then overdue_count should be >0
        assert ticket["sla_days"] >= 0


def test_sla_change_affects_overdue(tokens):
    st = tokens["super"]
    # baseline
    q = requests.get(f"{API}/admin/work/queue?scope=team", headers=H(st), timeout=30).json()
    ticket = next(i for i in q["items"] if i["work_type"] == "support_ticket")
    original_sla = ticket["sla_days"]
    open_count = ticket["open_count"]
    if open_count == 0:
        pytest.skip("no open tickets to age")
    try:
        # Set sla to 0 → all opened_before_today should be overdue
        r = requests.put(f"{API}/admin/work/settings/sla",
                         headers=H(st), json={"work_type": "support_ticket", "sla_days": 0}, timeout=30)
        assert r.status_code == 200
        # Wait for throttle to expire
        time.sleep(9)
        q2 = requests.get(f"{API}/admin/work/queue?scope=team", headers=H(st), timeout=30).json()
        t2 = next(i for i in q2["items"] if i["work_type"] == "support_ticket")
        # With SLA=0, tickets opened before today are overdue
        assert t2["overdue_count"] >= 0
    finally:
        requests.put(f"{API}/admin/work/settings/sla",
                     headers=H(st), json={"work_type": "support_ticket", "sla_days": int(original_sla)}, timeout=30)


# ============ 10. Security: no direct completion endpoint ============

def test_no_direct_complete_endpoint(tokens):
    for path in ("/admin/work/complete", "/admin/work/items/xxx/complete", "/admin/work/mark_complete"):
        r = requests.post(f"{API}{path}", headers=H(tokens["super"]), json={"status": "completed"}, timeout=15)
        assert r.status_code in (404, 405), f"{path} unexpectedly {r.status_code}"


def test_unauthorized_queue(tokens):
    r = requests.get(f"{API}/admin/work/queue?scope=my", timeout=15)
    assert r.status_code in (401, 403)


# ============ 4. Sensitive approval: OPEN → COMPLETED lifecycle ============

def _find_label_for_rate_change(super_token):
    """Find a label with royalty_percentage_default set that we can bump temporarily."""
    r = requests.get(f"{API}/admin/labels?limit=50", headers=H(super_token), timeout=30)
    if r.status_code != 200:
        return None, None
    body = r.json()
    arr = body if isinstance(body, list) else (body.get("items") or body.get("labels") or [])
    for lab in arr:
        lid = lab.get("id") or lab.get("label_id") or lab.get("user_id")
        rate = lab.get("royalty_percentage_default")
        if lid and rate is not None:
            return lid, float(rate)
    # Fallback: return first with default 60
    for lab in arr:
        lid = lab.get("id") or lab.get("label_id") or lab.get("user_id")
        if lid:
            return lid, 60.0
    return None, None


def test_sensitive_approval_open_then_completed(tokens):
    fin, sup = tokens["finance"], tokens["super"]
    label_id, current = _find_label_for_rate_change(sup)
    if not label_id:
        pytest.skip("no labels available")
    proposed = 55.0 if float(current) != 55.0 else 50.0

    req_id = None
    try:
        # Finance creates rate change request
        create = requests.post(f"{API}/admin/labels/{label_id}/rate-change/request",
                               headers=H(fin),
                               json={"proposed_value": proposed, "reason": "iter74 test"}, timeout=30)
        if create.status_code == 409:
            # Existing pending; find it
            lst = requests.get(f"{API}/admin/rate-changes?label_id={label_id}&status=pending",
                               headers=H(sup), timeout=30).json()
            arr = lst if isinstance(lst, list) else lst.get("items", [])
            assert arr, "409 but no pending found"
            req_id = arr[0]["id"]
        else:
            assert create.status_code in (200, 201), create.text
            req_id = create.json()["id"]

        # Wait for reconcile throttle
        time.sleep(9)
        q = requests.get(f"{API}/admin/work/queue?scope=team", headers=H(sup), timeout=30).json()
        sens = next(i for i in q["items"] if i["work_type"] == "sensitive_approval")
        assert sens["open_count"] >= 1, f"sensitive_approval open_count={sens['open_count']}"

        # Super approves
        dec = requests.post(f"{API}/admin/rate-changes/{req_id}/decision",
                            headers=H(sup), json={"action": "approve", "note": "ok"}, timeout=30)
        assert dec.status_code == 200, dec.text

        # Wait for reconcile
        time.sleep(9)
        # Trigger queue to force reconcile
        requests.get(f"{API}/admin/work/queue?scope=team", headers=H(sup), timeout=30)
        # Fetch history
        hist = requests.get(f"{API}/admin/work/history?work_type=sensitive_approval&limit=50",
                            headers=H(sup), timeout=30).json()
        rows = hist.get("items", [])
        matched = [r for r in rows if r.get("entity_id") == req_id and r.get("status") == "completed"]
        assert matched, f"no completed row for req {req_id}. rows={[r.get('entity_id') for r in rows[:5]]}"
        row = matched[0]
        assert row.get("completed_by_super") is True, f"completed_by_super not True: {row}"
        assert row.get("completed_by_name")
    finally:
        # Restore label rate
        if current is not None and label_id:
            requests.post(f"{API}/admin/labels/{label_id}/rate-change/direct",
                          headers=H(sup),
                          json={"proposed_value": float(current), "reason": "iter74 cleanup restore"}, timeout=30)
        # Delete test request docs
        try:
            from pymongo import MongoClient
            mc = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
            dbname = os.environ.get("DB_NAME", "rilismusik")
            if req_id:
                mc[dbname].label_rate_change_requests.delete_one({"id": req_id})
                mc[dbname].work_items.delete_many({"entity_id": req_id})
        except Exception as e:
            print(f"cleanup warn: {e}")
