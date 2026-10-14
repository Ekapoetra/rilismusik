"""Audit 2026-10 — money-path regressions: token pricing vs add-ons, pay-with-token
claim + Xendit session retirement, closed-release payments, atomic token
settlement, token/rupiah double refunds, withdraw reject after a reopened
correction, release compare-and-set transitions."""
import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

import test_token_foundation as base  # env + fake DB are set up on import
from test_token_foundation import LABEL_USER, SUPER, _FakeCollection, run
import payment_service as pay_svc
import token_service as tok
import routes.refund_service as refund_mod
import routes.addon_orders as addon_mod
import routes.withdraw as wd_mod
import routes.releases as rel_mod
from models import WithdrawAdminAction


async def _aiter_rows(self):
    for row in list(self._rows):
        yield row


# The refund paths iterate cursors with `async for` and cascade with
# update_many; the shared fake only offered to_list()/update_one().
base._Cursor.__aiter__ = _aiter_rows


async def _update_many(self, query, update, **kw):
    hits = [d for d in self.docs if base._query(d, query)]
    for doc in hits:
        base._apply(doc, update)
    return base.SimpleNamespace(modified_count=len(hits), matched_count=len(hits))


base._FakeCollection.update_many = _update_many


class AuditMoneyFixTests(unittest.TestCase):
    # Reuse the token suite fixtures without re-running its tests here.
    setUpClass = classmethod(base.TokenFoundationTests.setUpClass.__func__)
    tearDownClass = classmethod(base.TokenFoundationTests.tearDownClass.__func__)
    tearDown = base.TokenFoundationTests.tearDown
    _as = base.TokenFoundationTests._as
    _label = base.TokenFoundationTests._label

    def setUp(self):
        base.TokenFoundationTests.setUp(self)
        self.addon_orders = _FakeCollection()
        self.withdraws = _FakeCollection()
        self.balance_tx = _FakeCollection()
        fake = tok.db
        fake.addon_orders = self.addon_orders
        fake.withdraw_requests = self.withdraws
        fake.balance_transactions = self.balance_tx
        for mod in (refund_mod, addon_mod, wd_mod, rel_mod):
            patch.object(mod, "db", fake).start()
        self.xendit = AsyncMock(return_value={})
        patch.object(pay_svc, "_xendit_request", self.xendit).start()

    # ---------- helpers ----------
    def _release(self, rid="rel-1", status="awaiting_payment", rtype="album", **extra):
        doc = {"id": rid, "label_id": "lab-1", "release_type": rtype, "status": status,
               "release_title": "Album Uji", **extra}
        self.releases.docs.append(doc)
        return doc

    def _ppr_invoice(self, pid="pay-1", base=300_000, addons=0, **extra):
        doc = {"id": pid, "label_id": "lab-1", "type": "pay_per_release", "release_id": "rel-1",
               "amount": base + addons, "base_amount": base, "addon_amount": addons,
               "status": "pending", "currency": "IDR", "fulfillment_status": "pending",
               "reference_id": f"rm-{pid}", "created_at": "x", "updated_at": "x"}
        if addons:
            doc["addon_product_ids"] = ["prod-x"]
        doc.update(extra)
        self.payments.docs.append(doc)
        return doc

    # ---------- C1: tokens never settle add-ons ----------
    def test_token_quote_hidden_when_invoice_has_addons(self):
        self._release()
        self._ppr_invoice(base=300_000, addons=500_000)
        self._as(LABEL_USER)
        q = self.client.get("/api/payments/pay-1/token-quote").json()
        self.assertFalse(q["offered"])
        self.assertEqual(self.client.post("/api/payments/pay-1/pay-with-token").status_code, 400)
        self.assertEqual(self._label().get("token_daily_used") or 0, 0)

    def test_token_quote_compares_against_base_amount(self):
        self._release()
        # album = 6 tokens = 210k; base 200k → not cheaper even though amount is larger
        self._ppr_invoice(base=200_000, addons=0, amount=900_000)
        self._as(LABEL_USER)
        self.assertFalse(self.client.get("/api/payments/pay-1/token-quote").json()["offered"])

    # ---------- H1: claim + retire the rupiah session ----------
    def test_pay_with_token_cancels_live_xendit_session(self):
        self._release()
        self._ppr_invoice(xendit_session_id="ps-1", xendit_invoice_url="https://pay")
        self._as(LABEL_USER)
        r = self.client.post("/api/payments/pay-1/pay-with-token")
        self.assertEqual(r.status_code, 200, r.text)
        self.xendit.assert_awaited_with("POST", "/sessions/ps-1/cancel")
        pay = self.payments.docs[0]
        self.assertEqual(pay["status"], "paid")
        self.assertNotIn("xendit_session_id", pay)
        self.assertEqual(self._label()["token_daily_used"], 6)
        # a second attempt is rejected and spends nothing more
        self.assertEqual(self.client.post("/api/payments/pay-1/pay-with-token").status_code, 409)
        self.assertEqual(self._label()["token_daily_used"], 6)

    def test_pay_with_token_aborts_when_session_cannot_be_cancelled(self):
        self._release()
        self._ppr_invoice(xendit_session_id="ps-1", xendit_invoice_url="https://pay")
        self.xendit.side_effect = HTTPException(status_code=502, detail="already completed")
        self._as(LABEL_USER)
        self.assertEqual(self.client.post("/api/payments/pay-1/pay-with-token").status_code, 409)
        self.assertEqual(self.payments.docs[0]["status"], "pending")
        self.assertEqual(self._label().get("token_daily_used") or 0, 0)

    def test_pay_with_token_rejects_in_flight_claim(self):
        self._release()
        self._ppr_invoice(status="token_processing")
        self._as(LABEL_USER)
        self.assertEqual(self.client.post("/api/payments/pay-1/pay-with-token").status_code, 409)

    def test_poll_skips_token_paid_invoices(self):
        pay = {"id": "p", "status": "paid", "payment_method": "token_balance",
               "fulfillment_status": "processing", "xendit_session_id": "ps-old"}
        self.assertIs(run(pay_svc.poll_payment(pay, force=True)), pay)
        self.xendit.assert_not_awaited()

    # ---------- H3: closed releases stay closed ----------
    def test_closed_release_invoice_cannot_be_paid(self):
        self._release(status="closed")
        self._ppr_invoice(status="cancelled")
        self._as(LABEL_USER)
        self.assertEqual(self.client.post("/api/payments/pay-1/checkout").status_code, 409)
        self.payments.docs[0]["status"] = "pending"
        self.assertEqual(self.client.post("/api/payments/pay-1/pay-with-token").status_code, 409)

    def test_late_payment_for_closed_release_is_flagged_not_reopened(self):
        self._release(status="closed")
        pay = self._ppr_invoice(status="paid")
        run(pay_svc._fulfill_release(pay))
        self.assertEqual(self.releases.docs[0]["status"], "closed")
        self.assertTrue(self.payments.docs[0]["needs_refund"])

    # ---------- H3 (tokens): settlement claims each payment once ----------
    def test_concurrent_settlement_refunds_once(self):
        self.payments.docs.append({
            "id": "pay-r", "label_id": "lab-1", "type": "pay_per_release", "release_id": "rel-1",
            "amount": 35_000, "status": "paid", "payment_method": "token_balance",
            "token_parts": {"daily": 0, "purchased": 3}, "fulfillment_status": "fulfilled",
        })

        async def both():
            return await asyncio.gather(
                tok.settle_release_tokens("rel-1", "return", "a"),
                tok.settle_release_tokens("rel-1", "return", "b"),
            )
        self.assertEqual(sum(run(both())), 1)
        self.assertEqual(self._label()["token_balance"], 3)

    # ---------- H2 / M4: refunds ----------
    def test_token_paid_invoice_never_enters_rupiah_refund_queue(self):
        self._release(status="rejected")
        self._ppr_invoice(status="paid", payment_method="token_balance")
        self._as(SUPER)
        self.assertEqual(self.client.get("/api/admin/refunds/pending").json()["count"], 0)
        r = self.client.post("/api/admin/refunds/pay-1/mark-refunded", json={"note": "transfer"})
        self.assertEqual(r.status_code, 400)

    def test_payment_refund_excludes_addons_already_refunded(self):
        self._release(status="rejected")
        self._ppr_invoice(status="paid", base=300_000, addons=500_000)
        self.addon_orders.docs.append({"id": "ao-1", "payment_id": "pay-1", "status": "refunded",
                                       "refund_status": "refunded", "refund_amount": 500_000})
        self._as(SUPER)
        item = self.client.get("/api/admin/refunds/pending").json()["items"][0]
        self.assertEqual(item["amount_idr"], 300_000)
        r = self.client.post("/api/admin/refunds/pay-1/mark-refunded", json={"note": "transfer"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.payments.docs[0]["refund_amount_idr"], 300_000)
        r = self.client.post("/api/admin/refunds/pay-1/mark-refunded", json={"note": "lagi"})
        self.assertEqual(r.status_code, 409)

    def test_addon_on_token_paid_invoice_has_no_rupiah_refund(self):
        self._ppr_invoice(status="paid", payment_method="token_balance")
        self.addon_orders.docs.append({"id": "ao-1", "payment_id": "pay-1", "status": "pending",
                                       "amount": 500_000, "label_id": "lab-1"})
        self._as(SUPER)
        r = self.client.post("/api/admin/addon-orders/ao-1/refund", json={"note": "transfer"})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(self.addon_orders.docs[0]["status"], "pending")

    # ---------- H4: reopened correction cannot be rejected ----------
    def test_reject_after_correction_reopen_is_blocked(self):
        self.withdraws.docs.append({"id": "wd-1", "label_id": "lab-1", "status": "approved",
                                    "amount_idr": 2_000_000, "financial_settled": True})
        with self.assertRaises(HTTPException) as ctx:
            run(wd_mod._apply_admin_withdraw_action("wd-1", WithdrawAdminAction(action="reject"), SUPER))
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(self.balance_tx.docs, [])
        self.assertEqual(self.withdraws.docs[0]["status"], "approved")

    # ---------- release lifecycle guards ----------
    def test_label_cannot_self_cancel_a_paid_release(self):
        self._release(status="under_review", payment_status="paid")
        self._as(LABEL_USER)
        r = self.client.post("/api/releases/rel-1/cancel", json={"note": "batal"})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(self.releases.docs[0]["status"], "under_review")

    def test_release_transition_is_compare_and_set(self):
        rel = self._release(status="under_review")
        stale = dict(rel)
        rel["status"] = "approved"  # staff moved it after the label loaded it
        with self.assertRaises(HTTPException) as ctx:
            run(rel_mod._transition_release(stale, {"status": "closed"}, {"to": "closed"}))
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(self.releases.docs[0]["status"], "approved")


if __name__ == "__main__":
    unittest.main()
