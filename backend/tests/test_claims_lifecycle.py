"""D8 - Claim lifecycle: honesty statement, conflict, superseded, quarantine, revoke."""
import asyncio
import os
import re
import unittest
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.update({
    "MONGO_URL": "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=100",
    "DB_NAME": "claims_test",
    "JWT_SECRET": "test-only-unused-jwt-secret",
    "UPLOAD_DIR": "/tmp/rilismusik-test-uploads",
})

from fastapi import HTTPException
from fastapi.testclient import TestClient
import server
from server import app
from routes.deps import get_current_user
import routes.labels as labels_route
import routes.migrate as migrate_route
import routes.admin_label_service as label_service
import routes.withdraw as withdraw_route


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

    async def insert_many(self, docs):
        self.docs.extend(dict(d) for d in docs)

    async def update_one(self, query, update, **kw):
        doc = await self.find_one(query)
        if not doc:
            return SimpleNamespace(modified_count=0)
        doc.update(update.get("$set", {}))
        return SimpleNamespace(modified_count=1)

    async def update_many(self, query, update):
        n = 0
        for doc in self.docs:
            if _query(doc, query):
                doc.update(update.get("$set", {}))
                n += 1
        return SimpleNamespace(modified_count=n)

    async def delete_one(self, query):
        doc = await self.find_one(query)
        if doc in self.docs:
            self.docs.remove(doc)

    async def delete_many(self, query):
        self.docs = [d for d in self.docs if not _query(d, query)]


SUPER = {"id": "super-1", "role": "super_admin", "name": "Super", "email": "super@test"}
SUPPORT = {"id": "sup-1", "role": "admin_support", "name": "Support", "email": "sup@test"}
CLAIMER = {"id": "u-claim", "role": "label", "name": "Klaimer", "email": "claimer@test"}
RIVAL = {"id": "u-rival", "role": "label", "name": "Rival", "email": "rival@test"}


def _db(**colls):
    return SimpleNamespace(**colls)


class ClaimRequestTests(unittest.TestCase):
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
        self.users = _FakeCollection()
        self.users.docs = [dict(CLAIMER), dict(RIVAL)]
        self.labels = _FakeCollection()
        self.labels.docs = [{"id": "lab-new", "user_id": "u-claim", "label_name": "Baru", "whatsapp": "62"}]
        self._db = patch.object(labels_route, "db", _db(users=self.users, labels=self.labels))
        self._db.start()
        patch.object(labels_route, "get_label_by_user", new_callable=AsyncMock,
                     return_value=self.labels.docs[0]).start()
        patch.object(labels_route, "admin_user_ids", new_callable=AsyncMock, return_value=[]).start()
        patch.object(labels_route, "notify_many", new_callable=AsyncMock).start()
        patch.object(labels_route, "log_activity", new_callable=AsyncMock).start()
        app.dependency_overrides[get_current_user] = lambda: CLAIMER

    def tearDown(self):
        patch.stopall()
        app.dependency_overrides.clear()

    def test_statement_required(self):
        r = self.client.post("/api/label/claim-request", json={"legacy_label_name": "Warisan Records"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("Pernyataan", r.json()["detail"])

    def test_pending_claim_stores_fields(self):
        r = self.client.post("/api/label/claim-request", json={
            "legacy_label_name": "Warisan Records",
            "ownership_statement": True,
            "evidence_note": "Email lama a@b.c, bergabung 2019",
        })
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["claim_status"], "pending_link")
        doc = next(d for d in self.users.docs if d["id"] == "u-claim")
        self.assertEqual(doc["claim_status"], "pending_link")
        self.assertEqual(doc["claim_legacy_name_norm"], "warisan records")
        self.assertEqual(doc["claim_evidence_note"], "Email lama a@b.c, bergabung 2019")
        self.assertTrue(doc.get("claim_statement_accepted_at"))

    def test_duplicate_claim_becomes_conflict(self):
        # rival already claims the same name
        rival = next(d for d in self.users.docs if d["id"] == "u-rival")
        rival.update(claim_status="pending_link", claim_legacy_name="Warisan Records",
                     claim_legacy_name_norm="warisan records")
        r = self.client.post("/api/label/claim-request", json={
            "legacy_label_name": "Warisan Records", "ownership_statement": True,
        })
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["claim_status"], "conflict")
        self.assertEqual(rival["claim_status"], "conflict")

        # nama berbeda tidak memicu konflik (claimer baru)
        claimer = next(d for d in self.users.docs if d["id"] == "u-claim")
        claimer.pop("claim_status", None)
        rival.update(claim_status="conflict")
        r = self.client.post("/api/label/claim-request", json={
            "legacy_label_name": "Lain Records", "ownership_statement": True,
        })
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["claim_status"], "pending_link")


class ClaimAdminTests(unittest.TestCase):
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
        self.users = _FakeCollection()
        self.users.docs = [
            dict(CLAIMER, claim_status="conflict", claim_legacy_name="Warisan Records",
                 claim_legacy_name_norm="warisan records"),
            dict(RIVAL, claim_status="conflict", claim_legacy_name="Warisan Records",
                 claim_legacy_name_norm="warisan records"),
        ]
        self.labels = _FakeCollection()
        self.labels.docs = [{"id": "leg-1", "label_name": "Warisan Records", "user_id": None}]
        self._colls = {name: _FakeCollection() for name in
                       ("releases", "royalty_lines", "contracts", "bank_accounts",
                        "kyc_documents", "landing_settings", "notifications")}
        self._db = patch.object(migrate_route, "db",
                                _db(users=self.users, labels=self.labels, **self._colls))
        self._db.start()
        patch.object(migrate_route, "notify", new_callable=AsyncMock).start()
        patch.object(migrate_route, "log_activity", new_callable=AsyncMock).start()
        self._mail = patch("email_service.send_claim_approved_email", new_callable=AsyncMock)
        self._mail.start()
        patch("email_service.send_claim_rejected_email", new_callable=AsyncMock).start()
        app.dependency_overrides[get_current_user] = lambda: SUPER

    def tearDown(self):
        patch.stopall()
        app.dependency_overrides.clear()

    def test_list_includes_conflict(self):
        r = self.client.get("/api/admin/migrate/claims")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 2)

    def test_link_requires_super(self):
        app.dependency_overrides[get_current_user] = lambda: SUPPORT
        r = self.client.post("/api/admin/migrate/claims/u-claim/link/leg-1")
        self.assertEqual(r.status_code, 403)

    def test_reject_requires_super(self):
        app.dependency_overrides[get_current_user] = lambda: SUPPORT
        r = self.client.post("/api/admin/migrate/claims/u-claim/reject", data={"reason": "x"})
        self.assertEqual(r.status_code, 403)

    def test_link_quarantines_and_supersedes_rivals(self):
        r = self.client.post("/api/admin/migrate/claims/u-claim/link/leg-1")
        self.assertEqual(r.status_code, 200, r.text)
        lab = self.labels.docs[0]
        self.assertTrue(lab["claim_quarantined"])
        self.assertEqual(lab["user_id"], "u-claim")
        claimer = next(d for d in self.users.docs if d["id"] == "u-claim")
        rival = next(d for d in self.users.docs if d["id"] == "u-rival")
        self.assertEqual(claimer["claim_status"], "linked")
        self.assertEqual(rival["claim_status"], "superseded")
        self.assertEqual(rival["claim_resolved_by"], "super-1")

    def test_reject_conflict_allowed_for_super(self):
        r = self.client.post("/api/admin/migrate/claims/u-claim/reject", data={"reason": "Bukti kurang"})
        self.assertEqual(r.status_code, 200, r.text)
        claimer = next(d for d in self.users.docs if d["id"] == "u-claim")
        self.assertEqual(claimer["claim_status"], "rejected")
        self.assertEqual(claimer["claim_reject_reason"], "Bukti kurang")

    def test_quarantine_list_and_release(self):
        self.labels.docs[0].update(claim_quarantined=True, user_id="u-claim")
        r = self.client.get("/api/admin/migrate/labels/quarantined")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 1)

        # release khusus super
        app.dependency_overrides[get_current_user] = lambda: SUPPORT
        r = self.client.post("/api/admin/migrate/labels/leg-1/release-quarantine")
        self.assertEqual(r.status_code, 403)

        app.dependency_overrides[get_current_user] = lambda: SUPER
        r = self.client.post("/api/admin/migrate/labels/leg-1/release-quarantine")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertFalse(self.labels.docs[0]["claim_quarantined"])
        self.assertTrue(self.labels.docs[0].get("claim_baseline_released_at"))

        # idempotent-ish: release ulang -> 400 bukan error aneh
        r = self.client.post("/api/admin/migrate/labels/leg-1/release-quarantine")
        self.assertEqual(r.status_code, 400)


class RevokeAndQuarantineTests(unittest.TestCase):
    def test_revoke_marks_linked_claim_revoked(self):
        users = _FakeCollection()
        users.docs = [{"id": "u-claim", "role": "label", "email": "c@t", "claim_status": "linked"}]
        labels = _FakeCollection()
        labels.docs = [{"id": "leg-1", "label_name": "Warisan", "user_id": "u-claim",
                        "claim_quarantined": True}]
        artists = _FakeCollection()
        with patch.object(label_service, "db", _db(users=users, labels=labels, artists=artists)), \
             patch.object(label_service, "log_activity", new_callable=AsyncMock), \
             patch.object(label_service, "_disable_users", new_callable=AsyncMock, return_value=1):
            out = asyncio.run(label_service.revoke_label_account(
                label_id="leg-1", cascade_artists=False, reason="salah klaim", user=SUPER))
        self.assertTrue(out["ok"])
        self.assertIsNone(labels.docs[0]["user_id"])
        self.assertEqual(users.docs[0]["claim_status"], "revoked")
        self.assertEqual(users.docs[0]["claim_revoked_by"], "super-1")
        # karantina tetap menempel di label — baseline harus disahkan ulang
        self.assertTrue(labels.docs[0]["claim_quarantined"])

    def test_revoke_rejects_non_super(self):
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(label_service.revoke_label_account(
                label_id="leg-1", cascade_artists=False, reason="", user=SUPPORT))
        self.assertEqual(ctx.exception.status_code, 403)

    def test_withdraw_blocked_while_quarantined(self):
        state = {"request_open": True, "message": ""}
        with patch.object(withdraw_route, "withdraw_window_state", return_value=state):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(withdraw_route._create_label_withdrawal(
                    {"id": "leg-1", "claim_quarantined": True}, CLAIMER))
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("karantina", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
