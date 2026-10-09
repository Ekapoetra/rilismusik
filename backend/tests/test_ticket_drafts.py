"""D11 - Free-form ticket categories + server-side drafts."""
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
    "DB_NAME": "ticket_drafts_test",
    "JWT_SECRET": "test-only-unused-jwt-secret",
    "UPLOAD_DIR": "/tmp/rilismusik-test-uploads",
})

from fastapi.testclient import TestClient
import server
from server import app
from routes.deps import get_current_user
import routes.tickets as tickets_route
import routes.kyc_service as kyc_service


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
            return SimpleNamespace(modified_count=0)
        doc.update(update.get("$set", {}))
        return SimpleNamespace(modified_count=1)


LABEL_USER = {"id": "u-lab", "role": "label", "name": "Pemilik", "email": "lab@test"}
OTHER_LABEL = {"id": "u-lain", "role": "label", "name": "Asing", "email": "lain@test"}
ADMIN = {"id": "adm-1", "role": "admin_support", "name": "Support", "email": "adm@test",
         "admin_role_active": True, "permissions": ["support.view", "support.manage"]}
LABEL_DOC = {"id": "lab-1", "user_id": "u-lab", "label_name": "Label Uji",
             "email": "lab@test", "account_status": "active"}
OTHER_LABEL_DOC = {"id": "lab-2", "user_id": "u-lain", "label_name": "Label Lain",
                   "email": "lain@test", "account_status": "active"}


class TicketDraftTests(unittest.TestCase):
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
        self.tickets = _FakeCollection()
        self.comments = _FakeCollection()
        self.releases = _FakeCollection()
        self.releases.docs = [{"id": "rel-1", "label_id": "lab-1", "release_title": "Single A"}]
        self.labels = _FakeCollection()
        self.labels.docs = [dict(LABEL_DOC), dict(OTHER_LABEL_DOC)]
        fake_db = SimpleNamespace(
            support_tickets=self.tickets, ticket_comments=self.comments,
            releases=self.releases, labels=self.labels,
        )
        patch.object(tickets_route, "db", fake_db).start()
        self.get_label = patch.object(
            tickets_route, "get_label_by_user", new_callable=AsyncMock,
            side_effect=lambda user: LABEL_DOC if user["id"] == "u-lab" else OTHER_LABEL_DOC,
        ).start()
        self.notify = patch.object(tickets_route, "notify_many", new_callable=AsyncMock).start()
        patch.object(tickets_route, "admin_user_ids", new_callable=AsyncMock, return_value=["adm-1"]).start()
        patch.object(tickets_route, "log_activity", new_callable=AsyncMock).start()
        self.background = patch.object(tickets_route, "run_background", new_callable=AsyncMock).start()
        patch.object(kyc_service, "ensure_label_kyc", new_callable=AsyncMock).start()
        app.dependency_overrides[get_current_user] = lambda: LABEL_USER

    def tearDown(self):
        patch.stopall()
        app.dependency_overrides.clear()

    def _create_draft(self, **over):
        payload = {
            "category": "royalty_issue",
            "subject": "Royalti bulan lalu belum masuk",
            "description": "Periode Januari tidak muncul di laporan.",
            "is_draft": True,
        }
        payload.update(over)
        return self.client.post("/api/tickets/label/create", json=payload)

    # ---------- kategori bebas ----------

    def test_free_category_without_release(self):
        r = self.client.post("/api/tickets/label/create", json={
            "category": "other",
            "subject": "Pertanyaan umum",
            "description": "Bagaimana cara mengubah PIC akun?",
        })
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual(body["status"], "open")
        self.assertIsNone(body["release_id"])

    def test_release_bound_category_requires_release(self):
        r = self.client.post("/api/tickets/label/create", json={
            "category": "takedown",
            "subject": "Turunkan rilisan",
            "description": "Mohon takedown",
            "reason": "Pindah Aggregator",
        })
        self.assertEqual(r.status_code, 400)
        self.assertIn("Rilisan", r.json()["detail"])

    def test_free_category_foreign_release_rejected(self):
        self.releases.docs.append({"id": "rel-asing", "label_id": "lab-2", "release_title": "Bukan Milik"})
        r = self.client.post("/api/tickets/label/create", json={
            "category": "royalty_issue",
            "release_id": "rel-asing",
            "subject": "Royalti tidak cocok",
            "description": "Selisih angka laporan.",
        })
        self.assertEqual(r.status_code, 403)

    # ---------- draft ----------

    def test_draft_created_silently(self):
        r = self._create_draft()
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["status"], "draft")
        self.notify.assert_not_called()
        self.background.assert_not_called()
        self.assertEqual(len(self.comments.docs), 0)

    def test_draft_rejected_for_release_bound_category(self):
        r = self._create_draft(category="takedown")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Draf", r.json()["detail"])

    def test_draft_hidden_from_admin_queue(self):
        self._create_draft()
        app.dependency_overrides[get_current_user] = lambda: ADMIN
        r = self.client.get("/api/tickets/admin")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual([t for t in r.json() if t["status"] == "draft"], [])

    def test_draft_visible_to_owner(self):
        self._create_draft()
        r = self.client.get("/api/tickets/label")
        self.assertEqual(r.status_code, 200, r.text)
        drafts = [t for t in r.json() if t["status"] == "draft"]
        self.assertEqual(len(drafts), 1)

    def test_draft_edit_and_submit(self):
        ticket = self._create_draft().json()
        r = self.client.patch(f"/api/tickets/label/{ticket['id']}", json={
            "subject": "Subjek diperbarui",
        })
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["subject"], "Subjek diperbarui")
        self.assertEqual(r.json()["status"], "draft")

        r = self.client.post(f"/api/tickets/label/{ticket['id']}/submit")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["status"], "open")
        self.notify.assert_called_once()
        self.assertEqual(len(self.comments.docs), 1)
        self.assertEqual(self.comments.docs[0]["body"], "Periode Januari tidak muncul di laporan.")

    def test_submit_requires_subject(self):
        ticket = self._create_draft(subject="").json()
        r = self.client.post(f"/api/tickets/label/{ticket['id']}/submit")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Subjek", r.json()["detail"])

    def test_comment_blocked_on_draft(self):
        ticket = self._create_draft().json()
        r = self.client.post(f"/api/tickets/{ticket['id']}/comment", json={"body": "halo"})
        self.assertEqual(r.status_code, 400)

    def test_foreign_draft_not_editable(self):
        ticket = self._create_draft().json()
        app.dependency_overrides[get_current_user] = lambda: OTHER_LABEL
        r = self.client.patch(f"/api/tickets/label/{ticket['id']}", json={"subject": "Bajak"})
        self.assertEqual(r.status_code, 404)
        r = self.client.post(f"/api/tickets/label/{ticket['id']}/submit")
        self.assertEqual(r.status_code, 404)

    def test_submitted_ticket_not_editable_via_draft_route(self):
        r = self.client.post("/api/tickets/label/create", json={
            "category": "other", "subject": "Sudah terkirim", "description": "Isi tiket terkirim.",
        })
        ticket = r.json()
        r = self.client.patch(f"/api/tickets/label/{ticket['id']}", json={"subject": "Ubah"})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
