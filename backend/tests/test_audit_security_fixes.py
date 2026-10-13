"""Audit hardening — CSRF origin guard, authenticated file serving, and chat
typing participant checks."""
import os
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.update({
    "MONGO_URL": "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=100",
    "DB_NAME": "security_test",
    "JWT_SECRET": "test-only-unused-jwt-secret",
    "UPLOAD_DIR": "/tmp/rilismusik-test-uploads",
    "RILISMUSIK_DEPLOYMENT_MODE": "preview",
    "FRONTEND_URL": "https://preview.example.invalid",
    "CORS_ORIGINS": "https://preview.example.invalid",
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
import routes.chat as chat_mod
import routes.file_access as file_access
from test_token_foundation import _FakeCollection, _db, run

NOW = datetime.now(timezone.utc)
SUPER = {"id": "u-super", "role": "super_admin", "email": "super@test.dev"}
SUPPORT = {"id": "u-sup", "role": "admin_support", "email": "sup@test.dev",
           "permissions": ["support.manage"], "admin_role_active": True}
LABEL_USER = {"id": "u-label", "role": "label", "email": "label@test.dev"}
OTHER_LABEL = {"id": "u-other", "role": "label", "email": "other@test.dev"}

LABEL_DOC = {"id": "lab-1", "user_id": "u-label", "label_name": "Label Satu",
             "account_status": "active", "created_at": NOW.isoformat()}
OTHER_LABEL_DOC = {"id": "lab-2", "user_id": "u-other", "label_name": "Label Dua",
                   "account_status": "active", "created_at": NOW.isoformat()}


class AuditSecurityTests(unittest.TestCase):
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
        self.labels.docs = [dict(LABEL_DOC), dict(OTHER_LABEL_DOC)]
        self.contracts = _FakeCollection()
        self.withdraw_requests = _FakeCollection()
        self.releases = _FakeCollection()
        self.tracks = _FakeCollection()
        self.addon_orders = _FakeCollection()
        self.chat_messages = _FakeCollection()
        self.chat_conversations = _FakeCollection()
        self.chat_typing = _FakeCollection()
        self.support_tickets = _FakeCollection()
        self.ticket_comments = _FakeCollection()
        self.users = _FakeCollection()
        fake = _db(
            labels=self.labels, contracts=self.contracts,
            withdraw_requests=self.withdraw_requests, releases=self.releases,
            tracks=self.tracks, addon_orders=self.addon_orders,
            chat_messages=self.chat_messages, chat_conversations=self.chat_conversations,
            chat_typing=self.chat_typing, users=self.users,
            support_tickets=self.support_tickets, ticket_comments=self.ticket_comments,
        )
        self.fake = fake
        patch.object(deps, "db", fake).start()
        patch.object(file_access, "db", fake).start()
        patch.object(chat_mod, "db", fake).start()

    def tearDown(self):
        patch.stopall()
        app.dependency_overrides.clear()

    def _as(self, user):
        app.dependency_overrides[get_current_user] = lambda: user

    # ---------- L1: CSRF origin guard ----------
    def test_untrusted_origin_mutation_rejected(self):
        r = self.client.post("/api/notifications/mark-all-read",
                             headers={"Origin": "https://evil.example"})
        self.assertEqual(r.status_code, 403)

    def test_trusted_origin_reaches_auth(self):
        # 401 (not 403) proves the request passed the CSRF guard and failed on
        # missing credentials instead.
        r = self.client.post("/api/notifications/mark-all-read",
                             headers={"Origin": "https://preview.example.invalid"})
        self.assertEqual(r.status_code, 401)

    def test_no_origin_still_works(self):
        # server-to-server / scripted calls carry no Origin — unaffected
        r = self.client.post("/api/notifications/mark-all-read")
        self.assertEqual(r.status_code, 401)

    def test_get_with_any_origin_passes(self):
        r = self.client.get("/api/health", headers={"Origin": "https://evil.example"})
        self.assertEqual(r.status_code, 200)

    # ---------- L2: authenticated file prefixes ----------
    def test_contract_requires_auth(self):
        r = self.client.get("/api/files/contract/whatever.pdf")
        self.assertEqual(r.status_code, 401)

    def test_public_prefix_stays_open(self):
        r = self.client.get("/api/files/cover/nonexistent.jpg")
        self.assertEqual(r.status_code, 404)  # not 401 — auth not required

    def test_hard_blocked_prefix_stays_blocked(self):
        self._as(SUPER)
        r = self.client.get("/api/files/kyc-private/lab-1/doc.png")
        self.assertEqual(r.status_code, 404)

    def test_owner_can_open_contract(self):
        self.contracts.docs.append({
            "id": "c-1", "label_id": "lab-1",
            "file_url": "/api/files/contract/c-1.pdf",
        })
        result = run(file_access.authorize_file_path("contract/c-1.pdf", LABEL_USER))
        self.assertTrue(result)

    def test_other_label_denied_contract(self):
        self.contracts.docs.append({
            "id": "c-1", "label_id": "lab-1",
            "file_url": "/api/files/contract/c-1.pdf",
        })
        result = run(file_access.authorize_file_path("contract/c-1.pdf", OTHER_LABEL))
        self.assertFalse(result)

    def test_admin_allowed_anywhere(self):
        self.assertTrue(run(file_access.authorize_file_path("csv/imp-1.csv", SUPER)))

    def test_label_denied_admin_only_prefixes(self):
        self.assertFalse(run(file_access.authorize_file_path("csv/imp-1.csv", LABEL_USER)))
        self.assertFalse(run(file_access.authorize_file_path("background-inputs/t1/x.bin", LABEL_USER)))

    def test_chat_attachment_requires_membership(self):
        self.chat_conversations.docs.append({
            "id": "conv-1", "kind": "support", "label_id": "lab-1", "label_user_id": "u-label",
        })
        self.chat_messages.docs.append({
            "id": "m-1", "conversation_id": "conv-1",
            "attachment": {"url": "/api/files/chat/att-1.png"},
        })
        self.assertTrue(run(file_access.authorize_file_path("chat/att-1.png", LABEL_USER)))
        self.assertFalse(run(file_access.authorize_file_path("chat/att-1.png", OTHER_LABEL)))
        self.assertTrue(run(file_access.authorize_file_path("chat/att-1.png", SUPER)))

    def test_audio_owner_only(self):
        self.releases.docs.append({"id": "rel-1", "label_id": "lab-1"})
        self.tracks.docs.append({"id": "trk-1", "release_id": "rel-1"})
        self.assertTrue(run(file_access.authorize_file_path("audio/trk-1.wav", LABEL_USER)))
        self.assertFalse(run(file_access.authorize_file_path("audio/trk-1.wav", OTHER_LABEL)))

    def test_ticket_audio_attachment_owner(self):
        # purpose=audio ticket uploads land under audio/ticket_* — they must
        # resolve via the owning ticket, not the tracks collection.
        self.support_tickets.docs.append({
            "id": "t-1", "label_id": "lab-1",
            "attachments": ["/api/files/audio/ticket_att1.wav"],
        })
        self.assertTrue(run(file_access.authorize_file_path("audio/ticket_att1.wav", LABEL_USER)))
        self.assertFalse(run(file_access.authorize_file_path("audio/ticket_att1.wav", OTHER_LABEL)))

    def test_ticket_file_attachment_via_comment(self):
        self.support_tickets.docs.append({"id": "t-1", "label_id": "lab-1"})
        self.ticket_comments.docs.append({
            "id": "cm-1", "ticket_id": "t-1",
            "attachments": ["/api/files/ticket/ticket_doc1.pdf"],
        })
        self.assertTrue(run(file_access.authorize_file_path("ticket/ticket_doc1.pdf", LABEL_USER)))
        self.assertFalse(run(file_access.authorize_file_path("ticket/ticket_doc1.pdf", OTHER_LABEL)))

    # ---------- L3: typing requires membership ----------
    def test_typing_own_support_thread(self):
        self.chat_conversations.docs.append({
            "id": "conv-1", "kind": "support", "label_id": "lab-1", "label_user_id": "u-label",
        })
        self._as(LABEL_USER)
        r = self.client.post("/api/chat/typing/conv-1")
        self.assertEqual(r.status_code, 200)

    def test_typing_foreign_support_thread_denied(self):
        self.chat_conversations.docs.append({
            "id": "conv-1", "kind": "support", "label_id": "lab-1", "label_user_id": "u-label",
        })
        self._as(OTHER_LABEL)
        r = self.client.post("/api/chat/typing/conv-1")
        self.assertEqual(r.status_code, 403)

    def test_typing_support_staff_allowed(self):
        self.chat_conversations.docs.append({
            "id": "conv-1", "kind": "support", "label_id": "lab-1", "label_user_id": "u-label",
        })
        self._as(SUPPORT)
        r = self.client.post("/api/chat/typing/conv-1")
        self.assertEqual(r.status_code, 200)

    def test_typing_internal_requires_participant(self):
        self.chat_conversations.docs.append({
            "id": "conv-i", "kind": "internal", "participant_ids": ["u-sup", "u-super"],
        })
        self._as(SUPPORT)
        self.assertEqual(self.client.post("/api/chat/typing/conv-i").status_code, 200)
        self._as(LABEL_USER)
        self.assertEqual(self.client.post("/api/chat/typing/conv-i").status_code, 403)


if __name__ == "__main__":
    unittest.main()
