"""D1-a — Token foundation: super-only config, wallet state, spend order
(daily quota first, purchased second), refunds, burns, purchase fulfillment
idempotency."""
import asyncio
import os
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.update({
    "MONGO_URL": "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=100",
    "DB_NAME": "token_test",
    "JWT_SECRET": "test-only-unused-jwt-secret",
    "UPLOAD_DIR": "/tmp/rilismusik-test-uploads",
})

from fastapi.testclient import TestClient
import server
from server import app
from routes.deps import get_current_user
import routes.deps as deps
import routes.tokens as tokens_mod
import routes.payments as pay_mod
import routes.system_settings as sys_mod
import payment_service as pay_svc
import token_service as tok

WIB = timezone(timedelta(hours=7))


def _match(doc, key, cond):
    value = doc.get(key)
    if not isinstance(cond, dict):
        return value == cond
    if "$ne" in cond and value == cond["$ne"]:
        return False
    if "$in" in cond and value not in cond["$in"]:
        return False
    if "$nin" in cond and value in cond["$nin"]:
        return False
    if "$gte" in cond and not (value is not None and value >= cond["$gte"]):
        return False
    if "$lte" in cond and not (value is not None and value <= cond["$lte"]):
        return False
    if "$lt" in cond and not (value is not None and value < cond["$lt"]):
        return False
    if "$gt" in cond and not (value is not None and value > cond["$gt"]):
        return False
    if "$exists" in cond and ((key in doc) != bool(cond["$exists"])):
        return False
    return True


def _query(doc, q):
    for key, cond in (q or {}).items():
        if key == "$or":
            if not any(_query(doc, sub) for sub in cond):
                return False
            continue
        if not _match(doc, key, cond):
            return False
    return True


class _Cursor:
    def __init__(self, rows):
        self._rows = list(rows)

    def sort(self, key, direction=-1):
        self._rows.sort(key=lambda r: r.get(key) or "", reverse=direction < 0)
        return self

    async def to_list(self, limit):
        return self._rows if limit is None else self._rows[:limit]


def _apply(doc, update):
    doc.update(update.get("$set", {}))
    for key, value in (update.get("$inc") or {}).items():
        doc[key] = (doc.get(key) or 0) + value
    for key, value in (update.get("$addToSet") or {}).items():
        lst = doc.setdefault(key, [])
        if value not in lst:
            lst.append(value)
    for key, value in (update.get("$push") or {}).items():
        doc.setdefault(key, []).append(value)
    for key in (update.get("$unset") or {}):
        doc.pop(key, None)


def _project(doc, projection):
    if not projection:
        return doc
    keys = {k for k, v in projection.items() if v and k != "_id"}
    return {k: doc[k] for k in keys if k in doc} if keys else dict(doc)


class _FakeCollection:
    def __init__(self):
        self.docs = []

    def find(self, query=None, projection=None):
        return _Cursor([d for d in self.docs if _query(d, query)])

    async def find_one(self, query, projection=None, sort=None):
        rows = [d for d in self.docs if _query(d, query)]
        return _project(rows[0], projection) if rows else None

    async def find_one_and_update(self, query, update, upsert=False,
                                  return_document=False, projection=None, **kw):
        doc = None
        for d in self.docs:
            if _query(d, query):
                doc = d
                break
        if doc is None:
            if not upsert:
                return None
            doc = {k: v for k, v in (query or {}).items()
                   if not k.startswith("$") and not isinstance(v, dict)}
            doc.update(update.get("$setOnInsert", {}))
            _apply(doc, update)
            self.docs.append(doc)
            return _project(doc, projection) if return_document else None
        _apply(doc, update)
        return _project(doc, projection) if return_document else doc

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def update_one(self, query, update, upsert=False, **kw):
        found = False
        for d in self.docs:
            if _query(d, query):
                _apply(d, update)
                found = True
                break
        if not found and upsert:
            doc = {k: v for k, v in (query or {}).items()
                   if not k.startswith("$") and not isinstance(v, dict)}
            doc.update(update.get("$setOnInsert", {}))
            _apply(doc, update)
            self.docs.append(doc)
            return SimpleNamespace(modified_count=0, upserted_id="new", matched_count=0)
        return SimpleNamespace(modified_count=1 if found else 0,
                               upserted_id=None, matched_count=1 if found else 0)

    async def delete_one(self, query):
        before = len(self.docs)
        self.docs = [d for d in self.docs if not _query(d, query)]
        return SimpleNamespace(deleted_count=before - len(self.docs))

    async def count_documents(self, query):
        return sum(1 for d in self.docs if _query(d, query))


SUPER = {"id": "adm-1", "role": "super_admin", "name": "Super", "email": "s@t"}
STAFF = {"id": "adm-2", "role": "admin_finance", "name": "Fin", "email": "f@t",
         "permissions": ["payments.manage"], "admin_role_active": True}
LABEL_USER = {"id": "u-1", "role": "label", "name": "Lab", "email": "l@t"}

LABEL_DOC = {
    "id": "lab-1", "user_id": "u-1", "label_name": "Label Uji",
    "subscription_tier": "annual_vip", "subscription_status": "active",
    "subscription_expires_at": (datetime.now(timezone.utc) + timedelta(days=100)).isoformat(),
}


def _db(**colls):
    return SimpleNamespace(**colls)


def run(coro):
    return asyncio.run(coro)


class TokenFoundationTests(unittest.TestCase):
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
        self.labels = _FakeCollection()
        self.labels.docs = [dict(LABEL_DOC)]
        self.ledger = _FakeCollection()
        self.config = _FakeCollection()
        self.payments = _FakeCollection()
        self.logs = _FakeCollection()
        self.users = _FakeCollection()
        self.notifications = _FakeCollection()
        self.deliveries = _FakeCollection()
        self.settings = _FakeCollection()
        self.audit = _FakeCollection()
        self.releases = _FakeCollection()
        self.service_orders = _FakeCollection()
        self.payment_products = _FakeCollection()
        fake = _db(
            labels=self.labels, token_ledger=self.ledger, token_config=self.config,
            payments=self.payments, activity_logs=self.logs, users=self.users,
            notifications=self.notifications,
            payment_notification_deliveries=self.deliveries,
            system_settings=self.settings, system_audit=self.audit,
            releases=self.releases, service_orders=self.service_orders,
            payment_products=self.payment_products,
        )
        patch.object(tok, "db", fake).start()
        patch.object(sys_mod, "db", fake).start()
        patch.object(tokens_mod, "db", fake).start()
        patch.object(deps, "db", fake).start()
        patch.object(pay_mod, "db", fake).start()
        patch.object(pay_svc, "db", fake).start()
        # label endpoints are KYC-gated; bypass the check in tests
        import routes.kyc_service as kyc_mod
        patch.object(kyc_mod, "ensure_label_kyc", new_callable=AsyncMock).start()

    def tearDown(self):
        patch.stopall()
        app.dependency_overrides.clear()

    def _as(self, user):
        app.dependency_overrides[get_current_user] = lambda: user

    def _label(self):
        return self.labels.docs[0]

    # ---------- config (system area "token", super only) ----------
    def test_token_area_defaults_and_super_only(self):
        self._as(LABEL_USER)
        self.assertEqual(self.client.get("/api/admin/system/token").status_code, 403)
        self._as(STAFF)
        self.assertEqual(self.client.get("/api/admin/system/token").status_code, 403)
        self._as(SUPER)
        r = self.client.get("/api/admin/system/token")
        self.assertEqual(r.status_code, 200, r.text)
        cfg = r.json()["published"]
        self.assertEqual(cfg["price_idr"], 35_000)
        self.assertEqual(cfg["daily_quota"]["annual_vip"], 10)
        self.assertEqual(cfg["daily_quota"]["multi_label"], 15)
        self.assertEqual(cfg["service_costs"]["release_ep"], 5)

    def test_token_area_draft_publish_and_validation(self):
        self._as(SUPER)
        draft = {"price_idr": 40_000,
                 "daily_quota": {"annual_vip": 20},
                 "service_costs": {"release_ep": 4, "cover": 2}}
        r = self.client.post("/api/admin/system/token/draft",
                             json={"value": draft, "version": 0, "draft_version": 0})
        self.assertEqual(r.status_code, 200, r.text)
        r = self.client.post("/api/admin/system/token/publish",
                             json={"note": "ubah harga", "version": 0, "draft_version": 1})
        self.assertEqual(r.status_code, 200, r.text)
        published = r.json()["published"]
        self.assertEqual(published["daily_quota"]["annual_vip"], 20)
        self.assertEqual(published["daily_quota"]["multi_label"], 15)  # merged default
        self.assertEqual(published["service_costs"]["cover"], 2)
        # consumers see the published value
        cfg = run(tok.get_token_config())
        self.assertEqual(cfg["token_price_idr"], 40_000)
        self.assertEqual(cfg["service_tokens"]["release_ep"], 4)
        # audit entry recorded
        self.assertTrue(any(e["kind"] == "publish" and e["area"] == "token"
                            for e in self.audit.docs))
        # invalid drafts rejected
        for bad in ({"price_idr": 0}, {"price_idr": "x"},
                    {"daily_quota": {"annual_vip": -1}},
                    {"daily_quota": {"bukan_tier": 5}},
                    {"service_costs": {"album": 999}},
                    {"unknown_key": 1}):
            r = self.client.post("/api/admin/system/token/draft",
                                 json={"value": bad, "version": 1, "draft_version": 2})
            self.assertEqual(r.status_code, 400, bad)

    # ---------- wallet ----------
    def test_wallet_state(self):
        self._as(LABEL_USER)
        r = self.client.get("/api/token/wallet")
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual(body["token_balance"], 0)
        self.assertEqual(body["daily"]["quota"], 10)  # annual_vip
        self.assertEqual(body["daily"]["used"], 0)
        self.assertEqual(body["daily"]["remaining"], 10)
        self.assertEqual(body["daily"]["date"], tok.jakarta_today())

    def test_wallet_daily_reset_new_day(self):
        yesterday = (datetime.now(WIB) - timedelta(days=1)).date().isoformat()
        self._label().update({"token_daily_date": yesterday, "token_daily_used": 9})
        self._as(LABEL_USER)
        body = self.client.get("/api/token/wallet").json()
        self.assertEqual(body["daily"]["used"], 0)  # stale counter reset by date
        self.assertEqual(body["daily"]["remaining"], 10)

    def test_wallet_ownership_and_acl(self):
        self._as(SUPER)
        self.assertEqual(self.client.get("/api/token/wallet").status_code, 403)
        self._as(LABEL_USER)
        r = self.client.get("/api/token/config")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["daily_quota"], {"annual_vip": 10})

    # ---------- spend / refund / burn ----------
    def test_spend_daily_first_then_purchased(self):
        self._label()["token_balance"] = 3
        parts = run(tok.spend_tokens("lab-1", 8, "release", "rel-1", "EP"))
        self.assertEqual(parts, {"daily": 8, "purchased": 0})  # quota 10 covers all
        self.assertEqual(self._label()["token_daily_used"], 8)
        self.assertEqual(self._label()["token_balance"], 3)

        parts = run(tok.spend_tokens("lab-1", 5, "release", "rel-2", "Album"))
        self.assertEqual(parts, {"daily": 2, "purchased": 3})
        self.assertEqual(self._label()["token_balance"], 0)
        kinds = [(e["kind"], e["source"], e["amount"]) for e in self.ledger.docs]
        self.assertIn(("spend", "daily", -8), kinds)
        self.assertIn(("spend", "purchased", -3), kinds)

    def test_spend_insufficient_409(self):
        self._label()["token_balance"] = 1
        with self.assertRaises(Exception) as ctx:
            run(tok.spend_tokens("lab-1", 20, "release", "rel-x", "x"))
        self.assertEqual(getattr(ctx.exception, "status_code", None), 409)

    def test_refund_purchased_and_daily_same_day(self):
        self._label()["token_balance"] = 4
        parts = run(tok.spend_tokens("lab-1", 12, "release", "rel-1", "album"))
        self.assertEqual(parts, {"daily": 10, "purchased": 2})
        self.assertEqual(self._label()["token_balance"], 2)
        out = run(tok.refund_tokens("lab-1", parts, "release", "rel-1",
                                    "ditolak internal"))
        self.assertEqual(out, {"daily": 10, "purchased": 2})
        self.assertEqual(self._label()["token_balance"], 4)
        self.assertEqual(self._label()["token_daily_used"], 0)
        self.assertTrue(any(e["kind"] == "refund" and e["source"] == "purchased"
                            for e in self.ledger.docs))

    def test_refund_daily_after_day_rollover_skips(self):
        yesterday = (datetime.now(WIB) - timedelta(days=1)).date().isoformat()
        self._label().update({"token_daily_date": yesterday, "token_daily_used": 6})
        out = run(tok.refund_tokens("lab-1", {"daily": 4, "purchased": 0},
                                    "release", "rel-x", "batal"))
        self.assertEqual(out["daily"], 0)  # yesterday's quota can't return
        self.assertEqual(self._label()["token_daily_used"], 6)
        self.assertTrue(any(e["kind"] == "refund-skipped" for e in self.ledger.docs))

    def test_burn_daily_writes_ledger_only(self):
        self._label()["token_balance"] = 4
        run(tok.spend_tokens("lab-1", 3, "release", "rel-1", "n"))
        run(tok.burn_tokens("lab-1", 3, "release", "rel-1", "Believe menolak: metadata"))
        burn = [e for e in self.ledger.docs if e["kind"] == "burn"]
        self.assertEqual(len(burn), 1)
        self.assertIn("Believe", burn[0]["note"])
        self.assertEqual(self._label()["token_balance"], 4)

    # ---------- purchase ----------
    def test_token_purchase_invoice_and_fulfill(self):
        self._as(LABEL_USER)
        r = self.client.post("/api/payments/token-purchase", json={"quantity": 5})
        self.assertEqual(r.status_code, 200, r.text)
        pay = r.json()
        self.assertEqual(pay["type"], "token_purchase")
        self.assertEqual(pay["amount"], 5 * 35_000)
        self.assertEqual(pay["token_quantity"], 5)

        pay["status"] = "paid"
        run(pay_svc.fulfill_payment(pay))
        self.assertEqual(self._label()["token_balance"], 5)
        entry = [e for e in self.ledger.docs if e["kind"] == "purchase"]
        self.assertEqual(len(entry), 1)
        self.assertEqual(entry[0]["ref_id"], pay["id"])
        self.assertEqual(entry[0]["balance_after"], 5)

        # repeated fulfillment (polling/webhook) must not double-credit
        run(pay_svc.fulfill_payment({**pay, "fulfillment_status": "pending"}))
        self.assertEqual(self._label()["token_balance"], 5)
        self.assertEqual(len([e for e in self.ledger.docs if e["kind"] == "purchase"]), 1)

    def test_token_purchase_validation(self):
        self._as(LABEL_USER)
        self.assertEqual(self.client.post("/api/payments/token-purchase",
                                          json={"quantity": 0}).status_code, 422)
        self.assertEqual(self.client.post("/api/payments/token-purchase",
                                          json={"quantity": 501}).status_code, 422)
        self._as(STAFF)
        self.assertEqual(self.client.post("/api/payments/token-purchase",
                                          json={"quantity": 1}).status_code, 403)

    # ---------- pay an invoice with tokens (D1-b) ----------
    def _custom_service_invoice(self, amount=200_000):
        self.payment_products.docs.append({
            "id": "prod-1", "name": "Cover Art", "description": "d",
            "amount": amount, "active": True, "delivery_type": "file",
        })
        self._as(LABEL_USER)
        r = self.client.post("/api/payments/service/prod-1", json={})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_token_quote_offered_when_cheaper(self):
        pay = self._custom_service_invoice(200_000)
        # default price 35k — 5 tokens = 175k < 200k → offered
        self.settings.docs.append({"area": "token", "published": {
            "service_costs": {"prod-1": 5}}})
        r = self.client.get(f"/api/payments/{pay['id']}/token-quote")
        self.assertEqual(r.status_code, 200, r.text)
        q = r.json()
        self.assertTrue(q["offered"])
        self.assertEqual(q["tokens"], 5)
        self.assertTrue(q["affordable"])  # VIP quota 10 ≥ 5

    def test_pay_with_token_deducts_daily_first(self):
        pay = self._custom_service_invoice(200_000)
        self.settings.docs.append({"area": "token", "published": {
            "service_costs": {"prod-1": 5}}})
        self._label()["token_balance"] = 1
        r = self.client.post(f"/api/payments/{pay['id']}/pay-with-token")
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual(body["status"], "paid")
        self.assertEqual(body["payment_method"], "token_balance")
        # daily quota (10) covers all 5 → purchased untouched
        self.assertEqual(body["token_parts"], {"daily": 5, "purchased": 0})
        self.assertEqual(self._label()["token_daily_used"], 5)
        self.assertEqual(self._label()["token_balance"], 1)
        # service order fulfilled through the normal pipeline
        order = self.service_orders.docs[0]
        self.assertEqual(order["status"], "paid")
        self.assertTrue(any(e["kind"] == "spend" for e in self.ledger.docs))

    def test_pay_with_token_not_offered_when_not_cheaper(self):
        # PPR single: 1 token = 35k = same as rupiah → auto-hide
        self.releases.docs.append({"id": "rel-1", "label_id": "lab-1",
                                   "release_type": "single"})
        self.payments.docs.append({
            "id": "pay-1", "label_id": "lab-1", "type": "pay_per_release",
            "release_id": "rel-1", "amount": 35_000, "status": "pending",
            "currency": "IDR", "fulfillment_status": "pending",
            "created_at": "x", "updated_at": "x",
        })
        self._as(LABEL_USER)
        r = self.client.get("/api/payments/pay-1/token-quote")
        self.assertEqual(r.json()["offered"], False)
        r = self.client.post("/api/payments/pay-1/pay-with-token")
        self.assertEqual(r.status_code, 400)

    def test_pay_with_token_rejects_non_pending_and_unpayable(self):
        self._as(LABEL_USER)
        self.payments.docs.append({
            "id": "pay-p", "label_id": "lab-1", "type": "custom_service",
            "product_id": "prod-1", "amount": 200_000, "status": "paid",
            "fulfillment_status": "fulfilled", "created_at": "x",
        })
        self.assertEqual(self.client.post("/api/payments/pay-p/pay-with-token").status_code, 409)
        # token_purchase invoices are never payable with tokens
        self.payments.docs.append({
            "id": "pay-t", "label_id": "lab-1", "type": "token_purchase",
            "amount": 70_000, "status": "pending", "token_quantity": 2,
            "fulfillment_status": "pending", "created_at": "x",
        })
        self.assertEqual(self.client.post("/api/payments/pay-t/pay-with-token").status_code, 400)

    # ---------- release settlement matrix ----------
    def test_settle_return_vs_believe(self):
        self.payments.docs.append({
            "id": "pay-r", "label_id": "lab-1", "type": "pay_per_release",
            "release_id": "rel-1", "amount": 200_000, "status": "paid",
            "payment_method": "token_balance", "token_parts": {"daily": 4, "purchased": 2},
            "fulfillment_status": "fulfilled", "created_at": "x",
        })
        # Believe-side failure → purchased back, daily burned
        n = run(tok.settle_release_tokens("rel-1", "believe", "Believe menolak"))
        self.assertEqual(n, 1)
        self.assertEqual(self._label()["token_balance"], 2)
        self.assertTrue(any(e["kind"] == "burn" for e in self.ledger.docs))
        self.assertEqual(self.payments.docs[0]["token_settled"], "believe")
        # already settled — a second call is a no-op
        self.assertEqual(run(tok.settle_release_tokens("rel-1", "return", "x")), 0)

    def test_settle_return_pre_believe(self):
        self._label().update({"token_daily_date": tok.jakarta_today(),
                              "token_daily_used": 1})
        self.payments.docs.append({
            "id": "pay-r2", "label_id": "lab-1", "type": "pay_per_release",
            "release_id": "rel-9", "amount": 35_000, "status": "paid",
            "payment_method": "token_balance", "token_parts": {"daily": 1, "purchased": 0},
            "fulfillment_status": "fulfilled", "created_at": "x",
        })
        run(tok.settle_release_tokens("rel-9", "return", "Ditolak internal"))
        # same-day daily token returns to the counter
        self.assertTrue(any(e["kind"] == "refund" and e["source"] == "daily"
                            for e in self.ledger.docs))

    # ---------- admin grant ----------
    def test_admin_grant_super_only(self):
        self._as(STAFF)
        self.assertEqual(self.client.post("/api/admin/token/grant",
                                          json={"label_id": "lab-1", "quantity": 2,
                                                "note": "koreksi"}).status_code, 403)
        self._as(SUPER)
        r = self.client.post("/api/admin/token/grant",
                             json={"label_id": "lab-1", "quantity": 2, "note": "koreksi"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["token_balance"], 2)
        self.assertTrue(any(e["kind"] == "admin_grant" for e in self.ledger.docs))
        r = self.client.post("/api/admin/token/grant",
                             json={"label_id": "nope", "quantity": 2, "note": "koreksi"})
        self.assertEqual(r.status_code, 404)


if __name__ == "__main__":
    unittest.main()
