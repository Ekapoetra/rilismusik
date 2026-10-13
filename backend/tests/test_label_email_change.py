"""Offline regressions for changing a label account email (direct + approval flow)."""
import unittest
from unittest.mock import AsyncMock, patch

import test_vercel_preview  # Configures offline environment before real router imports.
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from routes import admin_label_service, deps, sensitive_requests
from routes.admin import admin_r
from routes.admin_permission_service import permission_for_request

SUPER = {"id": "super", "role": "super_admin", "is_admin": True, "admin_role_active": True, "permissions": []}
# Roles created after the RBAC unification are stored as role="admin_custom".
SUPPORT = {"id": "support", "role": "admin_custom", "admin_role_id": "r-support", "is_admin": True,
           "admin_role_active": True, "permissions": ["labels.view", "labels.manage", "labels.accounts"]}
SUPPORT_2 = {**SUPPORT, "id": "support-2"}
APPROVER = {"id": "approver", "role": "admin_custom", "admin_role_id": "r-approver", "is_admin": True,
            "admin_role_active": True, "permissions": ["labels.view", "labels.email.approve"]}
FINANCE = {"id": "finance", "role": "admin_custom", "admin_role_id": "r-finance", "is_admin": True,
           "admin_role_active": True, "permissions": ["labels.view", "labels.manage"]}


class LabelEmailChangeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = AsyncMongoMockClient().test
        self.patches = [
            patch.object(admin_label_service, "db", self.db),
            patch.object(sensitive_requests, "db", self.db),
            patch.object(deps, "db", self.db),
            patch.object(admin_label_service, "send_email", new_callable=AsyncMock),
        ]
        for item in self.patches:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in self.patches])
        await self.db.users.insert_many([
            {"id": "lu", "email": "label@gmial.com", "role": "label", "token_version": 0},
            {"id": "other", "email": "taken@example.com", "role": "label", "token_version": 0},
            {"id": "super", "role": "super_admin", "status": "active"},
        ])
        await self.db.labels.insert_many([
            {"id": "l1", "user_id": "lu", "label_name": "Label Satu", "email": "label@gmial.com"},
            {"id": "l2", "user_id": "lu", "label_name": "Label Dua", "email": "label@gmial.com"},
            {"id": "l3", "user_id": "lu", "label_name": "Label Tiga", "email": "kontak@lain.com"},
        ])

    async def emails(self):
        user = await self.db.users.find_one({"id": "lu"})
        labels = {doc["id"]: doc["email"] async for doc in self.db.labels.find({})}
        return user["email"], user["token_version"], labels

    async def request_change(self, user=SUPPORT, new_email="label@gmail.com"):
        body = sensitive_requests.EmailChangeRequestIn(new_email=new_email, reason="Salah ketik saat daftar")
        return await sensitive_requests.request_email_change("l1", body, user=user)

    async def decide(self, request_id, user, action="approve"):
        body = sensitive_requests.SensitiveDecisionIn(action=action)
        return await sensitive_requests.decide_sensitive_request(request_id, body, user=user)

    def test_route_permissions(self):
        self.assertEqual(permission_for_request("/api/admin/labels/l1/change-email", "POST"), "labels.email")
        self.assertEqual(permission_for_request("/api/admin/labels/l1/email-change-request", "POST"), "labels.accounts")
        self.assertEqual(permission_for_request("/api/admin/labels/l1/revoke-account", "POST"), "labels.accounts")

    async def test_super_admin_changes_email_directly(self):
        result = await admin_label_service.change_label_email(
            label_id="l1", new_email=" Label@Gmail.com ", send_notification=True, user=SUPER)
        self.assertEqual((result["old_email"], result["new_email"]), ("label@gmial.com", "label@gmail.com"))
        email, version, labels = await self.emails()
        self.assertEqual((email, version), ("label@gmail.com", 1))
        # Labels mirroring the login email follow it; a separate contact email is kept.
        self.assertEqual(labels, {"l1": "label@gmail.com", "l2": "label@gmail.com", "l3": "kontak@lain.com"})
        self.assertEqual(admin_label_service.send_email.await_count, 2)

    async def test_non_super_admin_cannot_change_directly(self):
        with self.assertRaises(HTTPException) as ctx:
            await admin_label_service.change_label_email(
                label_id="l1", new_email="label@gmail.com", send_notification=False, user=SUPPORT)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual((await self.emails())[0], "label@gmial.com")

    async def test_custom_role_request_then_super_admin_approves(self):
        req = await self.request_change()
        self.assertEqual((req["action_type"], req["status"]), ("email", "pending"))
        self.assertEqual((await self.emails())[0], "label@gmial.com")  # unchanged until approved
        listed = await sensitive_requests.list_sensitive_requests(label_id="l1", user=SUPPORT)
        self.assertEqual([row["id"] for row in listed], [req["id"]])
        decided = await self.decide(req["id"], SUPER)
        self.assertEqual((decided["status"], decided["applied"]), ("approved", True))
        email, version, _ = await self.emails()
        self.assertEqual((email, version), ("label@gmail.com", 1))
        log = await self.db.activity_logs.find_one({"action": "change_label_email"})
        self.assertEqual((log["user_id"], log["after_data"]["request_id"]), ("super", req["id"]))

    async def test_requester_cannot_approve_own_request(self):
        requester = {**SUPPORT, "permissions": [*SUPPORT["permissions"], "labels.email.approve"]}
        req = await self.request_change(user=requester)
        with self.assertRaises(HTTPException) as ctx:
            await self.decide(req["id"], requester)
        self.assertEqual(ctx.exception.status_code, 403)
        await self.decide(req["id"], APPROVER)
        self.assertEqual((await self.emails())[0], "label@gmail.com")

    async def test_account_admin_without_approve_permission_cannot_decide(self):
        req = await self.request_change()
        with self.assertRaises(HTTPException) as ctx:
            await self.decide(req["id"], SUPPORT_2)
        self.assertEqual(ctx.exception.status_code, 403)

    async def test_rejected_request_changes_nothing(self):
        req = await self.request_change()
        decided = await self.decide(req["id"], SUPER, action="reject")
        self.assertEqual(decided["status"], "rejected")
        self.assertEqual(await self.emails(), ("label@gmial.com", 0, {
            "l1": "label@gmial.com", "l2": "label@gmial.com", "l3": "kontak@lain.com"}))

    async def test_request_validation(self):
        for new_email, status in (("taken@example.com", 409), ("label@gmial.com", 400), ("label@gmail", 400)):
            with self.subTest(new_email=new_email), self.assertRaises(HTTPException) as ctx:
                await self.request_change(new_email=new_email)
            self.assertEqual(ctx.exception.status_code, status)
        await self.request_change()
        with self.assertRaises(HTTPException) as ctx:
            await self.request_change(new_email="label2@gmail.com")
        self.assertEqual(ctx.exception.status_code, 409)  # one pending request per label

    async def test_stale_request_is_not_applied(self):
        req = await self.request_change()
        await admin_label_service.change_label_email(
            label_id="l1", new_email="fixed@gmail.com", send_notification=False, user=SUPER)
        with self.assertRaises(HTTPException) as ctx:
            await self.decide(req["id"], SUPER)
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual((await self.emails())[0], "fixed@gmail.com")
        self.assertEqual((await self.db.sensitive_action_requests.find_one({"id": req["id"]}))["status"], "pending")

    async def test_custom_role_can_manage_label_accounts(self):
        result = await admin_label_service.revoke_label_account(
            label_id="l1", cascade_artists=False, reason="tes", user=SUPPORT)
        self.assertTrue(result["ok"])
        with self.assertRaises(HTTPException) as ctx:
            await admin_label_service.revoke_label_account(
                label_id="l2", cascade_artists=False, reason="tes", user=FINANCE)
        self.assertEqual(ctx.exception.status_code, 403)


class LabelEmailChangeHttpTests(unittest.TestCase):
    """Route wiring: multipart parsing, path permission gate and request JSON body."""

    def setUp(self):
        app = FastAPI()
        app.include_router(admin_r, prefix="/api")
        app.include_router(sensitive_requests.sensitive_r, prefix="/api")
        self.user = SUPER
        app.dependency_overrides[deps.get_current_user] = lambda: self.user
        self.client = TestClient(app)

    def test_direct_change_accepts_multipart_form(self):
        with patch("routes.admin.change_label_email", new_callable=AsyncMock, return_value={"ok": True}) as change:
            response = self.client.post("/api/admin/labels/l1/change-email",
                                        files={"new_email": (None, "label@gmail.com"), "notify": (None, "false")})
        self.assertEqual(response.status_code, 200, response.text)
        kwargs = change.await_args.kwargs
        self.assertEqual((kwargs["new_email"], kwargs["send_notification"]), ("label@gmail.com", False))

    def test_direct_change_is_gated_for_account_admins(self):
        self.user = SUPPORT
        response = self.client.post("/api/admin/labels/l1/change-email",
                                    files={"new_email": (None, "label@gmail.com")})
        self.assertEqual(response.status_code, 403)

    def test_account_admin_reaches_request_endpoint(self):
        self.user = SUPPORT
        with patch.object(sensitive_requests, "prepare_label_email_change",
                          new_callable=AsyncMock, side_effect=HTTPException(404, "Label tidak ditemukan")):
            response = self.client.post("/api/admin/labels/l1/email-change-request",
                                        json={"new_email": "label@gmail.com", "reason": "Salah ketik"})
        self.assertEqual(response.status_code, 404, response.text)


if __name__ == "__main__":
    unittest.main()
