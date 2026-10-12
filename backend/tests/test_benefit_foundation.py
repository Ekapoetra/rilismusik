"""D4 â€” monthly benefit quota + bonus grants: config defaults, count-based
usage, funding order (grant -> quota -> paid), expiry, account scope,
monitor signals, and permission gates."""
import os
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.update({
    "MONGO_URL": "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=100",
    "DB_NAME": "benefit_test",
    "JWT_SECRET": "test-only-unused-jwt-secret",
    "UPLOAD_DIR": "/tmp/rilismusik-test-uploads",
    "RILISMUSIK_DEPLOYMENT_MODE": "preview",
    "FRONTEND_URL": "https://preview.example.invalid",
    "SMTP_HOST": "smtp.example.invalid",
    "SMTP_PORT": "465",
    "SMTP_USER": "",
    "SMTP_PASSWORD": "",
    "SENDER_EMAIL": "test@example.invalid",
    "SENDER_NAME": "Preview test",
    "R2_ENDPOINT_URL": "",
    "R2_ACCESS_KEY_ID": "",
    "R2_SECRET_ACCESS_KEY": "",
    "R2_BUCKET": "",
})

from fastapi.testclient import TestClient
import server
from server import app
from routes.deps import get_current_user
import routes.deps as deps
import routes.benefits as ben_mod
import routes.system_settings as sys_mod
import benefit_service as ben
from test_token_foundation import _FakeCollection, _db, run

WIB = timezone(timedelta(hours=7))
NOW = datetime.now(timezone.utc)
FUTURE = (NOW + timedelta(days=30)).isoformat()
PAST = (NOW - timedelta(days=30)).isoformat()

SUPER = {"id": "u-super", "role": "super_admin", "email": "super@test.dev"}
STAFF = {"id": "u-staff", "role": "staff", "assigned_role": "admin_support",
         "permissions": [], "email": "staff@test.dev"}
LABEL_USER = {"id": "u-label", "role": "label", "email": "label@test.dev"}

LABEL_DOC = {
    "id": "lab-1", "user_id": "u-label", "label_name": "Label Satu",
    "account_status": "active", "subscription_status": "active",
    "subscription_tier": "annual_vip",
    "subscription_expires_at": FUTURE,
    "payment_type": "annual_subscription", "created_at": PAST,
}


class BenefitFoundationTests(unittest.TestCase):
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
        self.wami_orders = _FakeCollection()
        self.addon_orders = _FakeCollection()
        self.benefit_grants = _FakeCollection()
        self.settings = _FakeCollection()
        self.users = _FakeCollection()
        self.users.docs = [dict(SUPER), dict(STAFF), dict(LABEL_USER)]
        self.notifications = _FakeCollection()
        self.payments = _FakeCollection()
        self.payment_products = _FakeCollection()
        self.releases = _FakeCollection()
        self.logs = _FakeCollection()
        fake = _db(
            labels=self.labels, wami_orders=self.wami_orders,
            addon_orders=self.addon_orders, benefit_grants=self.benefit_grants,
            system_settings=self.settings, users=self.users,
            notifications=self.notifications, payments=self.payments,
            payment_products=self.payment_products, releases=self.releases,
            activity_logs=self.logs,
        )
        self.fake = fake
        patch.object(ben, "db", fake).start()
        patch.object(ben_mod, "db", fake).start()
        patch.object(sys_mod, "db", fake).start()
        patch.object(deps, "db", fake).start()
        import routes.kyc_service as kyc_mod
        patch.object(kyc_mod, "ensure_label_kyc", new_callable=AsyncMock).start()

    def tearDown(self):
        patch.stopall()
        app.dependency_overrides.clear()

    def _as(self, user):
        app.dependency_overrides[get_current_user] = lambda: user

    def _free_wami(self, created=None):
        self.wami_orders.docs.append({
            "id": f"wo-{len(self.wami_orders.docs)}", "label_id": "lab-1",
            "is_free_vip": True, "status": "pending",
            "created_at": created or NOW.isoformat(),
        })

    def _free_addon(self, created=None, grant_id=None, status="pending"):
        doc = {
            "id": f"ao-{len(self.addon_orders.docs)}", "label_id": "lab-1",
            "source": "subscription_free", "status": status,
            "created_at": created or NOW.isoformat(),
        }
        if grant_id:
            doc["grant_id"] = grant_id
        self.addon_orders.docs.append(doc)

    # ---------- consumption order ----------
    def test_quota_consumed_from_orders(self):
        self._as(LABEL_USER)
        self._free_wami()
        r = self.client.get("/api/label/benefits")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["quota"], 2)
        self.assertEqual(r.json()["used"], 1)
        self.assertEqual(r.json()["remaining"], 1)

    def test_refunded_order_restores_quota(self):
        self._as(LABEL_USER)
        self._free_wami(); self._free_addon()
        self.addon_orders.docs[0]["status"] = "refunded"
        r = self.client.get("/api/label/benefits")
        self.assertEqual(r.json()["used"], 1)

    def test_grant_orders_do_not_eat_quota(self):
        self._as(LABEL_USER)
        self._free_addon(grant_id="g-1")
        r = self.client.get("/api/label/benefits")
        self.assertEqual(r.json()["used"], 0)

    def test_consume_order_grant_then_quota_then_paid(self):
        self._as(LABEL_USER)
        self.benefit_grants.docs.append({
            "id": "g-1", "scope_key": "lab-1", "service": "wami",
            "quantity": 1, "used": 0, "expires_at": FUTURE,
        })
        scope = {"key": "lab-1", "label_ids": ["lab-1"], "package": "annual_vip", "vip_benefits": True}
        first = run(ben.consume_benefit(scope, "wami"))
        self.assertEqual(first["kind"], "grant")
        self.assertEqual(first["grant_id"], "g-1")
        second = run(ben.consume_benefit(scope, "wami"))
        self.assertEqual(second["kind"], "quota")

    def test_expired_grant_falls_to_quota(self):
        self._as(LABEL_USER)
        self.benefit_grants.docs.append({
            "id": "g-x", "scope_key": "lab-1", "service": "wami",
            "quantity": 1, "used": 0, "expires_at": (NOW - timedelta(days=1)).isoformat(),
        })
        scope = {"key": "lab-1", "label_ids": ["lab-1"], "package": "annual_vip", "vip_benefits": True}
        r = run(ben.consume_benefit(scope, "wami"))
        self.assertEqual(r["kind"], "quota")

    def test_quota_exhausted_returns_paid(self):
        self._as(LABEL_USER)
        self._free_wami(); self._free_wami()
        scope = {"key": "lab-1", "label_ids": ["lab-1"], "package": "annual_vip", "vip_benefits": True}
        r = run(ben.consume_benefit(scope, "wami"))
        self.assertEqual(r["kind"], "paid")
        self.assertTrue(r["exhausted"])

    def test_non_vip_always_paid(self):
        self._as(LABEL_USER)
        scope = {"key": "lab-1", "label_ids": ["lab-1"], "package": "pay_per_release", "vip_benefits": False}
        r = run(ben.consume_benefit(scope, "wami"))
        self.assertEqual(r["kind"], "paid")

    def test_multi_label_shares_quota(self):
        self._as(LABEL_USER)
        self.labels.docs.append(dict(LABEL_DOC, id="lab-2", label_name="Label Dua"))
        # child label used its free WAMI -- counts against the account scope
        self.wami_orders.docs.append({
            "id": "wo-child", "label_id": "lab-2", "is_free_vip": True,
            "status": "pending", "created_at": NOW.isoformat(),
        })
        self.labels.docs[0]["subscription_tier"] = "multi_label"
        self.labels.docs[1]["subscription_tier"] = None
        r = self.client.get("/api/label/benefits")
        self.assertEqual(r.json()["quota"], 3)
        self.assertEqual(r.json()["used"], 1)

    # ---------- admin grant ----------
    def test_grant_requires_manage_permission(self):
        self._as(STAFF)
        r = self.client.post("/api/admin/benefits/grant", json={
            "label_id": "lab-1", "service": "wami", "quantity": 2, "days": 30, "note": "reward",
        })
        self.assertEqual(r.status_code, 403)

    def test_grant_created_and_notified(self):
        self._as(SUPER)
        r = self.client.post("/api/admin/benefits/grant", json={
            "label_id": "lab-1", "service": "any", "quantity": 3, "days": 14, "note": "rilisan ke-10",
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["scope_key"], "lab-1")
        self.assertEqual(self.benefit_grants.docs[0]["quantity"], 3)
        self.assertEqual(len(self.notifications.docs), 1)

    def test_revoke_grant(self):
        self._as(SUPER)
        self.benefit_grants.docs.append({
            "id": "g-1", "scope_key": "lab-1", "label_id": "lab-1", "service": "any",
            "quantity": 2, "used": 0, "expires_at": FUTURE,
        })
        r = self.client.post("/api/admin/benefits/grants/g-1/revoke")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(self.benefit_grants.docs[0]["revoked"])

    # ---------- monitor ----------
    def test_monitor_signals(self):
        self._as(SUPER)
        # quota_max: 2 free orders this month on a Pro package
        self._free_wami(); self._free_addon()
        r = self.client.get("/api/admin/benefits/monitor")
        self.assertEqual(r.status_code, 200)
        items = {i["label_id"]: i for i in r.json()["items"]}
        self.assertIn("lab-1", items)
        keys = {s["key"] for s in items["lab-1"]["signals"]}
        self.assertIn("quota_max", keys)

    def test_monitor_requires_view(self):
        self._as(STAFF)
        self.assertEqual(self.client.get("/api/admin/benefits/monitor").status_code, 403)

    # ---------- batch quota reservation (audit B1) ----------
    def test_batch_consume_reserves_quota(self):
        self._as(LABEL_USER)
        scope = {"key": "lab-1", "label_ids": ["lab-1"], "package": "annual_vip", "vip_benefits": True}
        # quota 2 — three services in one batch must fail, not all pass
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            run(ben.consume_benefits(scope, ["svc-a", "svc-b", "svc-c"]))
        self.assertEqual(ctx.exception.status_code, 400)
        # two services fit the quota
        funded = run(ben.consume_benefits(scope, ["svc-a", "svc-b"]))
        self.assertEqual([r["kind"] for r in funded], ["quota", "quota"])

    # ---------- terminal status returns benefits (audit B2) ----------
    def test_rejected_order_restores_quota(self):
        self._as(LABEL_USER)
        self._free_wami()
        self._free_addon(status="rejected")
        r = self.client.get("/api/label/benefits")
        self.assertEqual(r.json()["used"], 1)

    def test_wami_reject_restores_grant(self):
        import routes.wami as wami_mod
        from models import AdminWamiUpdateIn
        patch.object(wami_mod, "db", self.fake).start()
        self.benefit_grants.docs.append({
            "id": "g-1", "scope_key": "lab-1", "service": "wami",
            "quantity": 1, "used": 1, "expires_at": FUTURE,
        })
        self.wami_orders.docs.append({
            "id": "wo-g", "label_id": "lab-1", "grant_id": "g-1",
            "is_free_vip": True, "status": "pending", "track_title": "Lagu",
            "created_at": NOW.isoformat(),
        })
        result = run(wami_mod.admin_update_wami("wo-g", AdminWamiUpdateIn(status="rejected"), SUPER))
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(self.benefit_grants.docs[0]["used"], 0)

    def test_addon_cancel_restores_grant(self):
        import routes.addon_orders as addon_mod
        patch.object(addon_mod, "db", self.fake).start()
        patch.object(addon_mod, "_email_addon", new_callable=AsyncMock).start()
        self.benefit_grants.docs.append({
            "id": "g-2", "scope_key": "lab-1", "service": "any",
            "quantity": 1, "used": 1, "expires_at": FUTURE,
        })
        self.addon_orders.docs.append({
            "id": "ao-g", "label_id": "lab-1", "grant_id": "g-2",
            "source": "subscription_free", "status": "in_progress",
            "product_name": "Visualizer", "created_at": NOW.isoformat(),
        })
        run(addon_mod.admin_update_status("ao-g", addon_mod.AddonStatusIn(status="cancelled"), SUPER))
        self.assertEqual(self.addon_orders.docs[0]["status"], "cancelled")
        self.assertEqual(self.benefit_grants.docs[0]["used"], 0)

    # ---------- settings area ----------
    def test_benefits_area_in_list(self):
        self._as(SUPER)
        r = self.client.get("/api/admin/system/areas")
        areas = [a["area"] for a in r.json()["areas"]]
        self.assertIn("benefits", areas)


if __name__ == "__main__":
    unittest.main()
