"""Iter79 - Verify email hooks (best-effort) do not regress endpoints.

Scope:
- POST /api/admin/cron/payment-reminders-check (new)
- POST /api/admin/cron/subscription-check (loop 30/7/3/1 + expired)
- POST /api/tickets/label/create (adds send_ticket_created_email best-effort)
- POST /api/tickets/admin/{id}/status (adds _email_ticket_status best-effort)
- POST /api/releases/{id}/submit (adds submitted-status email best-effort)
- POST /api/releases/{id}/admin/action (adds send_release_status_email for
  start_review, need_revision, approve, reject, takedown)
- PATCH /api/admin/addon-orders/{id}/status + /delivery (_email_addon)

Fixtures use TEST_ prefix and @example.com so real SMTP is not spammed.
All fixture docs (release, ticket, addon_order, payment) are inserted directly
and torn down at end. Demo VIP label email is temporarily rewritten during the
tests to a @example.com address to avoid real inbox delivery, then restored.
"""
import os
import uuid
import time
from typing import Dict, Any

import pymongo
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/frontend/.env", override=True)

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

SUPER = ("superadmin@rilismusik.com", "SuperAdmin#2026")
RELEASE_ADMIN = ("release1@rilismusik.com", "Release#2026")
LABEL = ("demo_vip@rilismusik.com", "DemoVIP#2026")


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _login(email: str, password: str) -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _H(tok):
    return {"Authorization": f"Bearer {tok}"}


# ---------- Session-level fixtures & tokens ----------
@pytest.fixture(scope="module")
def tokens():
    return {
        "super": _login(*SUPER),
        "release": _login(*RELEASE_ADMIN),
        "label": _login(*LABEL),
    }


@pytest.fixture(scope="module")
def demo_ctx():
    """Locate demo VIP label + user + (any) release; temporarily rewrite the
    label email so any best-effort emails go to @example.com."""
    d = _db()
    label = d.labels.find_one({"email": "demo_vip@rilismusik.com"}, {"_id": 0, "id": 1, "user_id": 1, "email": 1, "label_name": 1})
    assert label, "demo_vip label not found"
    original_email = label.get("email")
    test_email = f"test_iter79_{uuid.uuid4().hex[:8]}@example.com"
    d.labels.update_one({"id": label["id"]}, {"$set": {"email": test_email}})
    yield {"label_id": label["id"], "user_id": label["user_id"], "label_name": label.get("label_name") or "Label", "email": test_email}
    # restore
    d.labels.update_one({"id": label["id"]}, {"$set": {"email": original_email}})


# =============================================================================
# Cron endpoints
# =============================================================================
class TestCron:
    def test_payment_reminders_endpoint(self, tokens):
        r = requests.post(f"{API}/admin/cron/payment-reminders-check", headers=_H(tokens["super"]), timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert data.get("job") == "payment_reminders"

    def test_payment_reminders_marks_stale_invoice(self, tokens, demo_ctx):
        """Insert a synthetic pending PPR payment older than 72h and ensure the
        job marks it with the '72h' marker (idempotent)."""
        d = _db()
        pid = f"TEST_iter79_pay_{uuid.uuid4().hex[:8]}"
        d.payments.insert_one({
            "id": pid,
            "label_id": demo_ctx["label_id"],
            "type": "pay_per_release",
            "status": "pending",
            "amount": 150000,
            "description": "TEST_iter79 pending invoice",
            "release_id": None,
            "created_at": "2024-01-01T00:00:00+00:00",  # very old
            "payment_reminders": [],
        })
        try:
            r = requests.post(f"{API}/admin/cron/payment-reminders-check", headers=_H(tokens["super"]), timeout=60)
            assert r.status_code == 200
            # First run should tag '72h'
            doc = d.payments.find_one({"id": pid}, {"_id": 0, "payment_reminders": 1})
            assert doc and "72h" in (doc.get("payment_reminders") or []), doc
            # Idempotent: second call should not error
            r2 = requests.post(f"{API}/admin/cron/payment-reminders-check", headers=_H(tokens["super"]), timeout=60)
            assert r2.status_code == 200
        finally:
            d.payments.delete_one({"id": pid})

    def test_subscription_check_endpoint(self, tokens):
        r = requests.post(f"{API}/admin/cron/subscription-check", headers=_H(tokens["super"]), timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert data.get("job") == "subscription_expiry"


# =============================================================================
# Ticket create + admin status update (email hooks)
# =============================================================================
class TestTicketEmailHooks:
    @pytest.fixture(scope="class")
    def synth_release(self, demo_ctx):
        """Create a synthetic release owned by demo VIP for ticket testing."""
        d = _db()
        rid = f"TEST_iter79_rel_{uuid.uuid4().hex[:8]}"
        d.releases.insert_one({
            "id": rid,
            "label_id": demo_ctx["label_id"],
            "label_name": demo_ctx["label_name"],
            "release_title": "TEST_iter79 Sample",
            "primary_artist_name": "Test Artist",
            "artist_name": "Test Artist",
            "status": "delivered",
            "payment_status": "paid",
            "release_date": "2026-01-01",
            "cover_url": None,
            "billing_flow": "subscription",
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        })
        yield rid
        d.releases.delete_one({"id": rid})
        d.support_tickets.delete_many({"release_id": rid})
        d.ticket_comments.delete_many({"ticket_id": {"$regex": "^TEST_iter79"}})

    def test_ticket_create_includes_email_hook(self, tokens, synth_release):
        payload = {
            "release_id": synth_release,
            "category": "not_live",
            "subject": "TEST_iter79 not live",
            "description": "TEST_iter79 automated test — do not action",
        }
        r = requests.post(f"{API}/tickets/label/create", headers=_H(tokens["label"]), json=payload, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("id")
        # Persist ticket id for the next test via db lookup
        d = _db()
        assert d.support_tickets.find_one({"id": body["id"]}) is not None

    def test_admin_ticket_status_transitions_dont_500(self, tokens, synth_release):
        d = _db()
        ticket = d.support_tickets.find_one({"release_id": synth_release}, {"_id": 0, "id": 1})
        assert ticket, "ticket seed missing"
        tid = ticket["id"]
        # in_progress -> triggers _email_ticket_status
        r = requests.post(f"{API}/tickets/admin/{tid}/status", headers=_H(tokens["super"]),
                          json={"status": "in_progress"}, timeout=30)
        assert r.status_code == 200, r.text
        # done -> triggers _email_ticket_status
        r = requests.post(f"{API}/tickets/admin/{tid}/status", headers=_H(tokens["super"]),
                          json={"status": "done"}, timeout=30)
        assert r.status_code == 200, r.text
        # Re-open then reject to cover 'rejected' branch too
        d.support_tickets.update_one({"id": tid}, {"$set": {"status": "in_progress", "resolved_at": None}})
        r = requests.post(f"{API}/tickets/admin/{tid}/status", headers=_H(tokens["super"]),
                          json={"status": "rejected"}, timeout=30)
        assert r.status_code == 200, r.text


# =============================================================================
# Release admin_action email hooks
# =============================================================================
class TestReleaseAdminActionEmailHooks:
    @pytest.fixture
    def synth_submitted_release(self, demo_ctx):
        d = _db()
        rid = f"TEST_iter79_rel_{uuid.uuid4().hex[:8]}"
        d.releases.insert_one({
            "id": rid,
            "label_id": demo_ctx["label_id"],
            "label_name": demo_ctx["label_name"],
            "release_title": "TEST_iter79 Admin Action",
            "primary_artist_name": "Test Artist",
            "artist_name": "Test Artist",
            "status": "submitted",
            "payment_status": "paid",
            "billing_flow": "subscription",
            "release_date": "2026-01-01",
            "cover_url": None,
            "status_history": [],
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        })
        yield rid
        d.releases.delete_one({"id": rid})

    def _reset(self, rid, status):
        _db().releases.update_one({"id": rid}, {"$set": {"status": status}})

    def test_all_lifecycle_actions_do_not_500(self, tokens, synth_submitted_release):
        rid = synth_submitted_release

        # start_review: submitted -> under_review, email 'under_review'
        r = requests.post(f"{API}/releases/{rid}/admin/action", headers=_H(tokens["release"]),
                          json={"action": "start_review"}, timeout=30)
        assert r.status_code == 200, r.text
        assert (_db().releases.find_one({"id": rid}) or {}).get("status") == "under_review"

        # need_revision (needs note), under_review -> need_revision
        r = requests.post(f"{API}/releases/{rid}/admin/action", headers=_H(tokens["release"]),
                          json={"action": "need_revision", "note": "TEST_iter79 please fix cover"}, timeout=30)
        assert r.status_code == 200, r.text
        assert (_db().releases.find_one({"id": rid}) or {}).get("status") == "need_revision"

        # approve: reset to under_review; approve
        self._reset(rid, "under_review")
        r = requests.post(f"{API}/releases/{rid}/admin/action", headers=_H(tokens["release"]),
                          json={"action": "approve"}, timeout=30)
        assert r.status_code == 200, r.text
        assert (_db().releases.find_one({"id": rid}) or {}).get("status") == "approved"

        # reject: reset to submitted; reject (needs note)
        self._reset(rid, "submitted")
        r = requests.post(f"{API}/releases/{rid}/admin/action", headers=_H(tokens["release"]),
                          json={"action": "reject", "note": "TEST_iter79 rejected reason"}, timeout=30)
        assert r.status_code == 200, r.text
        assert (_db().releases.find_one({"id": rid}) or {}).get("status") == "rejected"

        # takedown: reset to live; takedown (needs note)
        self._reset(rid, "live")
        r = requests.post(f"{API}/releases/{rid}/admin/action", headers=_H(tokens["release"]),
                          json={"action": "takedown", "note": "TEST_iter79 takedown reason"}, timeout=30)
        assert r.status_code == 200, r.text
        assert (_db().releases.find_one({"id": rid}) or {}).get("status") == "taken_down"


# =============================================================================
# Add-on order status/delivery email hooks
# =============================================================================
class TestAddonOrderEmailHooks:
    @pytest.fixture
    def synth_addon_order(self, demo_ctx):
        d = _db()
        oid = f"TEST_iter79_addon_{uuid.uuid4().hex[:8]}"
        d.addon_orders.insert_one({
            "id": oid,
            "dedupe_key": f"test-iter79-{oid}",
            "label_id": demo_ctx["label_id"],
            "label_name": demo_ctx["label_name"],
            "release_id": None,
            "release_title": None,
            "product_id": "test-product",
            "product_name": "TEST_iter79 Visualizer",
            "product_description": "",
            "delivery_type": "link",
            "amount": 100000,
            "payment_id": None,
            "source": "manual",
            "status": "pending",
            "delivery_url": None,
            "delivery_note": None,
            "delivery_filename": None,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        })
        yield oid
        d.addon_orders.delete_one({"id": oid})

    def test_admin_status_and_delivery_hooks(self, tokens, synth_addon_order):
        oid = synth_addon_order

        # status -> in_progress
        r = requests.patch(f"{API}/admin/addon-orders/{oid}/status", headers=_H(tokens["super"]),
                           json={"status": "in_progress"}, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json().get("status") == "in_progress"

        # delivery (patch link) -> auto-advance to delivered
        r = requests.patch(f"{API}/admin/addon-orders/{oid}/delivery", headers=_H(tokens["super"]),
                           json={"delivery_url": "https://example.com/asset.mp4", "delivery_note": "TEST_iter79 hasil"},
                           timeout=30)
        assert r.status_code == 200, r.text
        assert r.json().get("status") == "delivered"
