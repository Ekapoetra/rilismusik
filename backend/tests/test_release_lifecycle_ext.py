"""Release lifecycle extensions - label cancel/cancel-request/clarification, admin
cancel decisions, follow-up flag, per-track partial go-live, partial_closed."""
import os
import re
import unittest
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.update({
    "MONGO_URL": "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=100",
    "DB_NAME": "rel_lifecycle_test",
    "JWT_SECRET": "test-only-unused-jwt-secret",
    "UPLOAD_DIR": "/tmp/rilismusik-test-uploads",
})

from fastapi.testclient import TestClient
import server
from server import app
from routes.deps import get_current_user
import routes.kyc_service as kyc_service
import routes.releases as rel_route


def _match(doc, key, cond):
    value = doc.get(key)
    if not isinstance(cond, dict):
        return value == cond
    if "$ne" in cond and value == cond["$ne"]:
        return False
    if "$nin" in cond and value in cond["$nin"]:
        return False
    if "$in" in cond and value not in cond["$in"]:
        return False
    if "$regex" in cond:
        flags = re.I if "i" in (cond.get("$options") or "") else 0
        if not re.search(cond["$regex"], value or "", flags):
            return False
    return True


def _query(doc, q):
    for key, cond in (q or {}).items():
        if key == "$or":
            if not any(_query(doc, branch) for branch in cond):
                return False
        elif not _match(doc, key, cond):
            return False
    return True


class _Cursor:
    def __init__(self, rows):
        self._rows = list(rows)

    def sort(self, key, direction=-1):
        self._rows.sort(key=lambda r: r.get(key) or "", reverse=direction < 0)
        return self

    def limit(self, n):
        self._rows = self._rows[:n]
        return self

    async def to_list(self, limit):
        return self._rows if limit is None else self._rows[:limit]

    def __aiter__(self):
        async def gen():
            for row in self._rows:
                yield row
        return gen()


class _FakeCollection:
    def __init__(self):
        self.docs = []

    def find(self, query=None, projection=None):
        return _Cursor([d for d in self.docs if _query(d, query)])

    async def find_one(self, query, projection=None, sort=None):
        rows = [d for d in self.docs if _query(d, query)]
        if sort:
            key, direction = sort[0]
            rows.sort(key=lambda r: r.get(key) or "", reverse=direction < 0)
        return rows[0] if rows else None

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def update_one(self, query, update, **kw):
        doc = await self.find_one(query)
        if not doc:
            return SimpleNamespace(modified_count=0, upserted_id=None)
        doc.update(update.get("$set", {}))
        for key, value in (update.get("$inc") or {}).items():
            doc[key] = (doc.get(key) or 0) + value
        for key, value in (update.get("$push") or {}).items():
            doc.setdefault(key, []).append(value)
        return SimpleNamespace(modified_count=1, upserted_id=None)

    async def update_many(self, query, update):
        n = 0
        for doc in self.docs:
            if _query(doc, query):
                doc.update(update.get("$set", {}))
                n += 1
        return SimpleNamespace(modified_count=n)

    async def count_documents(self, query):
        return sum(1 for d in self.docs if _query(d, query))


ADMIN = {"id": "adm-1", "role": "super_admin", "name": "Admin", "email": "adm@test"}
STAFF = {"id": "adm-2", "role": "admin_custom", "name": "Staff", "email": "staff@test",
         "permissions": ["releases.review", "releases.go_live", "releases.takedown"]}
LABEL_USER = {"id": "u-lab", "role": "label", "name": "Label", "email": "lab@test"}
LABEL = {"id": "lab-1", "user_id": "u-lab", "label_name": "Label A", "email": "lab@test"}


def _release(**over):
    base = {
        "id": "rel-1", "label_id": "lab-1", "release_title": "Rilis A",
        "release_type": "ep", "status": "submitted", "payment_status": "free_subscription",
        "billing_flow": "subscription", "status_history": [],
        "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00",
    }
    base.update(over)
    return base


def _track(tid, **over):
    base = {"id": tid, "release_id": "rel-1", "track_number": 1, "track_title": f"Lagu {tid}",
            "isrc": f"ID-{tid}", "created_at": "2026-01-01T00:00:00"}
    base.update(over)
    return base


def _db(**colls):
    return SimpleNamespace(**colls)


class ReleaseLifecycleExtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bootstrap = patch.object(server, "_bootstrap_async", new_callable=AsyncMock)
        cls.bootstrap.start()
        cls.context = TestClient(app)
        cls.client = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)
        cls.bootstrap.stop()

    def setUp(self):
        self.releases = _FakeCollection()
        self.releases.docs = [_release()]
        self.tracks = _FakeCollection()
        self.tracks.docs = [_track("t-1"), _track("t-2", track_number=2)]
        self.labels = _FakeCollection()
        self.labels.docs = [dict(LABEL)]
        self.payments = _FakeCollection()
        self._db = patch.object(rel_route, "db", _db(
            releases=self.releases, tracks=self.tracks, labels=self.labels,
            payments=self.payments,
            addon_orders=_FakeCollection(), notifications=_FakeCollection(),
            activity_logs=_FakeCollection(), release_metadata_edits=_FakeCollection(),
        ))
        self._db.start()
        patch.object(rel_route, "notify_many", new_callable=AsyncMock).start()
        patch.object(rel_route, "admin_user_ids", new_callable=AsyncMock, return_value=["adm-1"]).start()
        patch.object(rel_route, "label_user_ids", new_callable=AsyncMock, return_value=["u-lab"]).start()
        patch.object(rel_route, "log_activity", new_callable=AsyncMock).start()
        patch.object(rel_route, "run_background", new_callable=AsyncMock).start()
        patch.object(rel_route, "cancel_release_pending_payments", new_callable=AsyncMock).start()
        patch.object(rel_route, "get_label_by_user", new_callable=AsyncMock, return_value=LABEL).start()
        patch.object(rel_route, "release_subscription_covered", new_callable=AsyncMock, return_value=True).start()
        patch.object(kyc_service, "ensure_label_kyc", new_callable=AsyncMock, return_value={"is_verified": True}).start()

    def tearDown(self):
        patch.stopall()
        app.dependency_overrides.clear()

    def _as_label(self):
        app.dependency_overrides[get_current_user] = lambda: LABEL_USER

    def _as_admin(self):
        app.dependency_overrides[get_current_user] = lambda: ADMIN

    def _admin_action(self, action, **kw):
        return self.client.post("/api/releases/rel-1/admin/action", json={"action": action, **kw})

    # ---------- Label: self-cancel ----------
    def test_label_cancel_submitted_closes_and_voids_invoice(self):
        self._as_label()
        r = self.client.post("/api/releases/rel-1/cancel", json={"note": "salah upload"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["status"], "closed")
        self.assertEqual(self.releases.docs[0]["closed_reason"], "label_cancelled")
        rel_route.cancel_release_pending_payments.assert_awaited()
        rel_route.admin_user_ids.assert_awaited()

    def test_label_cancel_blocked_too_late(self):
        self._as_label()
        for st in ("paid", "approved", "delivered", "partial", "live", "cancel_requested"):
            self.releases.docs[0]["status"] = st
            r = self.client.post("/api/releases/rel-1/cancel", json={"note": "x"})
            self.assertEqual(r.status_code, 409, st)

    def test_label_cannot_cancel_other_label_release(self):
        patch.object(rel_route, "get_label_by_user", new_callable=AsyncMock,
                     return_value={"id": "lab-lain", "user_id": "u-lab"}).start()
        self._as_label()
        self.assertEqual(self.client.post("/api/releases/rel-1/cancel", json={}).status_code, 403)
        self.assertEqual(self.client.post("/api/releases/rel-1/cancel-request",
                                          json={"note": "x"}).status_code, 403)
        self.assertEqual(self.client.post("/api/releases/rel-1/clarification",
                                          json={"note": "x"}).status_code, 403)

    # ---------- Label: cancel request ----------
    def test_label_cancel_request_from_delivered(self):
        self.releases.docs[0]["status"] = "delivered"
        self._as_label()
        r = self.client.post("/api/releases/rel-1/cancel-request", json={"note": "salah harga"})
        self.assertEqual(r.status_code, 200, r.text)
        doc = self.releases.docs[0]
        self.assertEqual(doc["status"], "cancel_requested")
        self.assertEqual(doc["cancel_from_status"], "delivered")
        self.assertEqual(doc["cancel_reason"], "salah harga")

    def test_label_cancel_request_requires_reason_and_late_status(self):
        self.releases.docs[0]["status"] = "delivered"
        self._as_label()
        self.assertEqual(self.client.post("/api/releases/rel-1/cancel-request",
                                          json={"note": " "}).status_code, 400)
        self.releases.docs[0]["status"] = "submitted"
        r = self.client.post("/api/releases/rel-1/cancel-request", json={"note": "x"})
        self.assertEqual(r.status_code, 409)

    # ---------- Admin: cancel decision ----------
    def test_admin_cancel_confirm_closes_release(self):
        self.releases.docs[0].update(status="cancel_requested", cancel_from_status="delivered",
                                     cancel_reason="salah")
        self._as_admin()
        self.assertEqual(self._admin_action("cancel_confirm").status_code, 400)
        r = self._admin_action("cancel_confirm", note="Believe sudah dihubungi, delivery batal")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["status"], "closed")
        self.assertEqual(self.releases.docs[0]["closed_reason"], "cancel_confirmed")

    def test_admin_cancel_deny_restores_status(self):
        self.releases.docs[0].update(status="cancel_requested", cancel_from_status="approved",
                                     cancel_reason="x")
        self._as_admin()
        r = self._admin_action("cancel_deny", note="Sudah terlanjur proses")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["status"], "approved")

    def test_cancel_actions_require_cancel_requested(self):
        self._as_admin()
        self.assertEqual(self._admin_action("cancel_confirm", note="x").status_code, 409)
        self.assertEqual(self._admin_action("cancel_deny", note="x").status_code, 409)

    # ---------- Clarification ----------
    def test_label_clarification_once_per_revision_cycle(self):
        self.releases.docs[0]["status"] = "need_revision"
        self._as_label()
        r = self.client.post("/api/releases/rel-1/clarification",
                             json={"note": "Bagian mana yang salah?"})
        self.assertEqual(r.status_code, 200, r.text)
        doc = self.releases.docs[0]
        self.assertEqual(doc["status"], "clarification")
        self.assertTrue(doc["clarification_used"])
        # admin answers -> back to need_revision, flag stays consumed
        self._as_admin()
        r = self._admin_action("answer_clarification", note="Cover blur")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.releases.docs[0]["status"], "need_revision")
        self.assertTrue(self.releases.docs[0]["clarification_used"])
        # second question in the SAME revision cycle -> blocked by the flag
        self._as_label()
        self.assertEqual(self.client.post("/api/releases/rel-1/clarification",
                                          json={"note": "lagi"}).status_code, 409)
        # a fresh need_revision cycle re-arms the flag
        self.releases.docs[0]["status"] = "under_review"
        self._as_admin()
        self._admin_action("need_revision", note="siklus baru")
        self._as_label()
        r = self.client.post("/api/releases/rel-1/clarification", json={"note": "pertanyaan baru"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.releases.docs[0]["status"], "clarification")

    def test_clarification_requires_note_and_need_revision(self):
        self._as_label()
        self.releases.docs[0]["status"] = "need_revision"
        self.assertEqual(self.client.post("/api/releases/rel-1/clarification",
                                          json={"note": ""}).status_code, 400)
        self.releases.docs[0]["status"] = "submitted"
        self.assertEqual(self.client.post("/api/releases/rel-1/clarification",
                                          json={"note": "halo"}).status_code, 409)

    def test_admin_answer_returns_to_need_revision(self):
        self.releases.docs[0].update(status="clarification", clarification_used=True,
                                     clarification_question="Bagian mana?")
        self._as_admin()
        self.assertEqual(self._admin_action("answer_clarification").status_code, 400)
        r = self._admin_action("answer_clarification", note="Cover masih blur")
        self.assertEqual(r.status_code, 200, r.text)
        doc = self.releases.docs[0]
        self.assertEqual(doc["status"], "need_revision")
        self.assertEqual(doc["clarification_answer"], "Cover masih blur")
        self.assertTrue(doc["clarification_used"])

    def test_new_need_revision_resets_clarification_flag(self):
        self.releases.docs[0].update(status="under_review", clarification_used=True,
                                     clarification_question="lama", clarification_answer="jawab")
        self._as_admin()
        r = self._admin_action("need_revision", note="perbaiki lagi")
        self.assertEqual(r.status_code, 200, r.text)
        doc = self.releases.docs[0]
        self.assertEqual(doc["status"], "need_revision")
        self.assertFalse(doc["clarification_used"])
        self.assertIsNone(doc["clarification_question"])

    # ---------- Follow-up flag ----------
    def test_followup_flag_toggle_on_delivered(self):
        self.releases.docs[0]["status"] = "delivered"
        self._as_admin()
        r = self._admin_action("followup", note="belum muncul di Spotify")
        self.assertEqual(r.status_code, 200, r.text)
        doc = self.releases.docs[0]
        self.assertEqual(doc["status"], "delivered")
        self.assertTrue(doc["followup_flag"])
        self.assertEqual(doc["followup_note"], "belum muncul di Spotify")
        r = self._admin_action("clear_followup")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertFalse(self.releases.docs[0]["followup_flag"])

    def test_followup_blocked_on_wrong_status(self):
        self._as_admin()
        self.assertEqual(self._admin_action("followup", note="x").status_code, 409)

    # ---------- Partial per-track go-live ----------
    def test_mark_live_subset_creates_partial(self):
        self.releases.docs[0].update(status="delivered", upc="UPC-1")
        self._as_admin()
        r = self._admin_action("mark_live", upc="UPC-1", track_ids=["t-1"])
        self.assertEqual(r.status_code, 200, r.text)
        doc = self.releases.docs[0]
        self.assertEqual(doc["status"], "partial")
        self.assertTrue(doc.get("went_partial_at"))
        self.assertFalse(doc.get("live_at"))
        t1 = next(t for t in self.tracks.docs if t["id"] == "t-1")
        t2 = next(t for t in self.tracks.docs if t["id"] == "t-2")
        self.assertTrue(t1["live"])
        self.assertIsNone(t2.get("live"))

    def test_mark_live_remaining_completes_live(self):
        self.releases.docs[0].update(status="partial", upc="UPC-1")
        self.tracks.docs[0]["live"] = True
        self._as_admin()
        r = self._admin_action("mark_live", upc="UPC-1", track_ids=["t-2"])
        self.assertEqual(r.status_code, 200, r.text)
        doc = self.releases.docs[0]
        self.assertEqual(doc["status"], "live")
        self.assertTrue(doc.get("live_at"))
        self.assertTrue(next(t for t in self.tracks.docs if t["id"] == "t-2")["live"])

    def test_mark_live_all_when_no_track_ids(self):
        self.releases.docs[0].update(status="delivered", upc="UPC-1")
        self._as_admin()
        r = self._admin_action("mark_live", upc="UPC-1")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["status"], "live")
        self.assertTrue(all(t.get("live") for t in self.tracks.docs))

    def test_mark_live_isrc_required_only_for_marked_tracks(self):
        self.releases.docs[0].update(status="delivered", upc="UPC-1")
        self.tracks.docs[1]["isrc"] = None  # unmarked track lacks ISRC — fine
        self._as_admin()
        r = self._admin_action("mark_live", upc="UPC-1", track_ids=["t-1"])
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["status"], "partial")

    def test_mark_live_rejects_unknown_and_empty_selection(self):
        self.releases.docs[0].update(status="delivered", upc="UPC-1")
        self._as_admin()
        self.assertEqual(self._admin_action("mark_live", upc="U", track_ids=[]).status_code, 400)
        self.assertEqual(self._admin_action("mark_live", upc="U", track_ids=["nope"]).status_code, 400)

    # ---------- close_partial ----------
    def test_super_closes_partial(self):
        self.releases.docs[0].update(status="partial", upc="UPC-1")
        self.tracks.docs[0]["live"] = True
        self._as_admin()
        self.assertEqual(self._admin_action("close_partial").status_code, 400)
        r = self._admin_action("close_partial", note="track 2 tidak pernah tersedia")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["status"], "partial_closed")
        self.assertEqual(self.releases.docs[0]["closed_reason"], "partial_closed")

    def test_close_partial_super_only_and_needs_partial(self):
        self.releases.docs[0]["status"] = "partial"
        app.dependency_overrides[get_current_user] = lambda: STAFF
        r = self._admin_action("close_partial", note="x")
        self.assertEqual(r.status_code, 403)
        self._as_admin()
        self.releases.docs[0]["status"] = "delivered"
        self.assertEqual(self._admin_action("close_partial", note="x").status_code, 409)


if __name__ == "__main__":
    unittest.main()
