"""D11 - Add-on revision loop + refund (label accept/revision, admin decision, dual-refund guard)."""
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
    "DB_NAME": "addon_test",
    "JWT_SECRET": "test-only-unused-jwt-secret",
    "UPLOAD_DIR": "/tmp/rilismusik-test-uploads",
})

from fastapi.testclient import TestClient
import server
from server import app
from routes.deps import get_current_user
import routes.addon_orders as addon_route
import routes.refund_service as refund_route


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
        return self._rows[:limit]

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

    async def find_one(self, query, projection=None):
        return next((d for d in self.docs if _query(d, query)), None)

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def update_one(self, query, update, **kw):
        doc = await self.find_one(query)
        if not doc:
            return SimpleNamespace(modified_count=0, upserted_id=None)
        doc.update(update.get("$set", {}))
        for key, value in (update.get("$inc") or {}).items():
            doc[key] = (doc.get(key) or 0) + value
        return SimpleNamespace(modified_count=1, upserted_id=None)

    async def update_many(self, query, update):
        n = 0
        for doc in self.docs:
            if _query(doc, query):
                doc.update(update.get("$set", {}))
                n += 1
        return SimpleNamespace(modified_count=n)


ADMIN = {"id": "adm-1", "role": "super_admin", "name": "Admin", "email": "adm@test"}
LABEL_USER = {"id": "u-lab", "role": "label", "name": "Label", "email": "lab@test"}
LABEL = {"id": "lab-1", "user_id": "u-lab", "label_name": "Label A", "email": "lab@test"}


def _order(**over):
    base = {
        "id": "ord-1", "dedupe_key": "rel-1:prod-1", "label_id": "lab-1",
        "label_name": "Label A", "release_id": "rel-1", "release_title": "Rilis A",
        "product_id": "prod-1", "product_name": "Visualizer",
        "amount": 150000, "payment_id": "pay-1", "source": "release",
        "status": "delivered", "delivery_url": "https://example.com/r.mp4",
        "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00",
    }
    base.update(over)
    return base


def _db(**colls):
    return SimpleNamespace(**colls)


class AddonRevisionRefundTests(unittest.TestCase):
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
        self.orders = _FakeCollection()
        self.orders.docs = [_order()]
        self.payments = _FakeCollection()
        self.payments.docs = [{"id": "pay-1", "status": "paid", "refund_status": None}]
        self.labels = _FakeCollection()
        self.labels.docs = [dict(LABEL)]
        self._db = patch.object(addon_route, "db",
                                _db(addon_orders=self.orders, payments=self.payments, labels=self.labels))
        self._db.start()
        patch.object(addon_route, "notify_many", new_callable=AsyncMock).start()
        patch.object(addon_route, "admin_user_ids", new_callable=AsyncMock, return_value=["adm-1"]).start()
        patch.object(addon_route, "label_user_ids", new_callable=AsyncMock, return_value=["u-lab"]).start()
        patch.object(addon_route, "log_activity", new_callable=AsyncMock).start()
        patch.object(addon_route, "run_background", new_callable=AsyncMock).start()
        patch.object(addon_route, "get_label_by_user", new_callable=AsyncMock, return_value=LABEL).start()

    def tearDown(self):
        patch.stopall()
        app.dependency_overrides.clear()

    def _as_label(self):
        app.dependency_overrides[get_current_user] = lambda: LABEL_USER

    def _as_admin(self):
        app.dependency_overrides[get_current_user] = lambda: ADMIN

    # ---------- Label: accept ----------
    def test_label_accept_delivered_completes(self):
        self._as_label()
        r = self.client.post("/api/label/addon-orders/ord-1/accept")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["status"], "completed")
        self.assertTrue(self.orders.docs[0].get("accepted_by_label_at"))

    def test_label_accept_requires_delivered(self):
        self.orders.docs[0]["status"] = "in_progress"
        self._as_label()
        r = self.client.post("/api/label/addon-orders/ord-1/accept")
        self.assertEqual(r.status_code, 409)

    def test_label_cannot_touch_other_label_order(self):
        patch.object(addon_route, "get_label_by_user", new_callable=AsyncMock,
                     return_value={"id": "lab-lain", "user_id": "u-lab"}).start()
        self._as_label()
        self.assertEqual(self.client.post("/api/label/addon-orders/ord-1/accept").status_code, 404)
        self.assertEqual(self.client.post("/api/label/addon-orders/ord-1/revision",
                                          json={"note": "warna salah"}).status_code, 404)

    # ---------- Label: revision ----------
    def test_label_revision_request(self):
        self._as_label()
        r = self.client.post("/api/label/addon-orders/ord-1/revision",
                             json={"note": "warna visualizer tidak sesuai"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["status"], "revision")
        doc = self.orders.docs[0]
        self.assertEqual(doc["revision_note"], "warna visualizer tidak sesuai")
        self.assertEqual(doc["revision_count"], 1)
        addon_route.notify_many.assert_awaited()

    def test_label_revision_requires_note_and_delivered(self):
        self._as_label()
        self.assertEqual(self.client.post("/api/label/addon-orders/ord-1/revision",
                                          json={"note": "ok"}).status_code, 422)
        self.orders.docs[0]["status"] = "pending"
        r = self.client.post("/api/label/addon-orders/ord-1/revision", json={"note": "belum ada hasil"})
        self.assertEqual(r.status_code, 409)

    # ---------- Admin: revision decision ----------
    def test_admin_approve_revision_returns_to_in_progress(self):
        self.orders.docs[0].update(status="revision", revision_note="revisi")
        self._as_admin()
        r = self.client.post("/api/admin/addon-orders/ord-1/revision-decision",
                             json={"decision": "approve"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["status"], "in_progress")
        self.assertEqual(self.orders.docs[0]["revision_decision"], "approve")

    def test_admin_decline_revision_requires_note(self):
        self.orders.docs[0].update(status="revision", revision_note="revisi")
        self._as_admin()
        r = self.client.post("/api/admin/addon-orders/ord-1/revision-decision",
                             json={"decision": "decline"})
        self.assertEqual(r.status_code, 400)
        r = self.client.post("/api/admin/addon-orders/ord-1/revision-decision",
                             json={"decision": "decline", "note": "Hasil sudah sesuai brief"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["status"], "delivered")
        self.assertEqual(self.orders.docs[0]["revision_decision_note"], "Hasil sudah sesuai brief")

    def test_revision_decision_requires_revision_status(self):
        self._as_admin()
        r = self.client.post("/api/admin/addon-orders/ord-1/revision-decision",
                             json={"decision": "approve"})
        self.assertEqual(r.status_code, 409)

    def test_generic_status_and_delivery_blocked_during_revision(self):
        self.orders.docs[0].update(status="revision", revision_note="revisi")
        self._as_admin()
        r = self.client.patch("/api/admin/addon-orders/ord-1/status", json={"status": "completed"})
        self.assertEqual(r.status_code, 409)
        r = self.client.patch("/api/admin/addon-orders/ord-1/delivery",
                              json={"delivery_url": "https://example.com/x"})
        self.assertEqual(r.status_code, 409)

    def test_revision_and_refund_not_settable_via_generic_status(self):
        self.orders.docs[0]["status"] = "in_progress"
        self._as_admin()
        for st in ("revision", "refunded"):
            r = self.client.patch("/api/admin/addon-orders/ord-1/status", json={"status": st})
            self.assertEqual(r.status_code, 400, st)

    # ---------- Admin: refund ----------
    def test_refund_paid_order(self):
        self.orders.docs[0]["status"] = "in_progress"
        self._as_admin()
        r = self.client.post("/api/admin/addon-orders/ord-1/refund",
                             json={"note": "TF BCA 123"})
        self.assertEqual(r.status_code, 200, r.text)
        doc = self.orders.docs[0]
        self.assertEqual(doc["status"], "refunded")
        self.assertEqual(doc["refund_amount"], 150000)
        self.assertEqual(doc["refund_method"], "manual_transfer")

    def test_refund_blocked_after_delivery(self):
        self._as_admin()
        for st in ("delivered", "completed", "cancelled"):
            self.orders.docs[0]["status"] = st
            r = self.client.post("/api/admin/addon-orders/ord-1/refund", json={"note": "coba"})
            self.assertEqual(r.status_code, 409, st)

    def test_dual_refund_blocked_when_payment_refunded(self):
        self.orders.docs[0]["status"] = "in_progress"
        self.payments.docs[0]["refund_status"] = "refunded"
        self._as_admin()
        r = self.client.post("/api/admin/addon-orders/ord-1/refund", json={"note": "double"})
        self.assertEqual(r.status_code, 409)
        self.assertNotEqual(self.orders.docs[0]["status"], "refunded")

    def test_benefit_order_refund_restores_slot(self):
        self.orders.docs[0].update(status="pending", amount=0, payment_id=None,
                                   source="subscription_free", benefit_source="vip")
        self._as_admin()
        r = self.client.post("/api/admin/addon-orders/ord-1/refund", json={"note": "benefit kembali"})
        self.assertEqual(r.status_code, 200, r.text)
        doc = self.orders.docs[0]
        self.assertTrue(doc["benefit_restored"])
        self.assertTrue(doc["dedupe_key"].startswith("rel-1:prod-1:refunded"))

    def test_refund_requires_note(self):
        self._as_admin()
        r = self.client.post("/api/admin/addon-orders/ord-1/refund", json={"note": "x"})
        self.assertEqual(r.status_code, 422)

    # ---------- Payment-refund cascade ----------
    def test_payment_refund_cascades_to_addon_orders(self):
        self.orders.docs[0]["status"] = "in_progress"
        self.orders.docs.append(_order(id="ord-2", status="completed"))  # already done: untouched
        self.payments.docs[0].update(
            status="paid", type="pay_per_release", release_id="rel-1",
            amount=300000, label_id="lab-1",
        )
        releases = _FakeCollection()
        releases.docs = [{"id": "rel-1", "status": "rejected"}]
        patch.object(refund_route, "db",
                     _db(payments=self.payments, releases=releases,
                         addon_orders=self.orders, labels=self.labels)).start()
        patch.object(refund_route, "log_activity", new_callable=AsyncMock).start()
        self._as_admin()
        r = self.client.post("/api/admin/refunds/pay-1/mark-refunded", json={"note": "TF BCA 999"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["addon_orders_refunded"], 1)
        self.assertEqual(self.orders.docs[0]["status"], "refunded")
        self.assertEqual(self.orders.docs[1]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
