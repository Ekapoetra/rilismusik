"""RILIS MUSIK Phase 3 - Support Ticketing system regression tests.

Covers:
- Categories endpoint
- Label create ticket (success + category validation + multi-tenant guard)
- Label list / detail / status flips on comment
- Admin list with filters, comment flips status to waiting_label
- Admin status update creates system comment
- Label cancel (allowed vs blocked statuses)
- Closed-ticket comment block
- Attachment upload validation
"""
import os
import io
import uuid

import pytest
import requests
from tests.support_config import SUPERADMIN, temporary_password

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"

SUPER_EMAIL = SUPERADMIN["email"]
SUPER_PASS = SUPERADMIN["password"]
LABEL1_EMAIL = "label1@test.com"
LABEL1_PASS = temporary_password("phase3-label")


def _session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _rand_email(prefix="t3"):
    return f"TEST_{prefix}_{uuid.uuid4().hex[:8]}@example.com"


@pytest.fixture(scope="module")
def super_session():
    s = _session()
    r = s.post(f"{API}/auth/login", json={"email": SUPER_EMAIL, "password": SUPER_PASS})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def label1_session():
    s = _session()
    r = s.post(f"{API}/auth/login", json={"email": LABEL1_EMAIL, "password": LABEL1_PASS})
    if r.status_code != 200:
        pytest.skip(f"label1 login failed: {r.text}")
    # also fetch label's first release
    r2 = s.get(f"{API}/releases/")
    assert r2.status_code == 200, r2.text
    releases = r2.json()
    if not releases:
        pytest.skip("label1 has no releases")
    return {"session": s, "release_id": releases[0]["id"], "label_id": releases[0]["label_id"]}


@pytest.fixture(scope="module")
def other_label():
    """Register a fresh label + create a release so we have a 2nd tenant."""
    s = _session()
    email = _rand_email("lbl")
    r = s.post(f"{API}/auth/register", json={
        "label_name": "TEST P3 Other Label", "pic_name": "PIC",
        "email": email, "whatsapp": "+62811", "password": LABEL1_PASS,
        "account_type": "label",
            "mda_accepted": True,
    })
    assert r.status_code == 200, r.text
    label_id = r.json()["label"]["id"]
    return {"session": s, "email": email, "label_id": label_id}


# ============== CATEGORIES ==============
class TestCategories:
    def test_list_categories(self, label1_session):
        r = label1_session["session"].get(f"{API}/tickets/categories")
        assert r.status_code == 200
        items = r.json()
        values = {i["value"] for i in items}
        expected = {"takedown", "edit_metadata", "edit_audio", "edit_cover",
                    "content_id_claim", "content_id_release", "royalty_issue", "other"}
        assert values == expected, values
        # Indonesian labels present
        labels_by_value = {i["value"]: i["label"] for i in items}
        assert "Takedown" in labels_by_value["takedown"]
        assert "Royalti" in labels_by_value["royalty_issue"]


# ============== LABEL CREATE TICKET ==============
class TestLabelCreate:
    def test_create_takedown_success(self, label1_session):
        s = label1_session["session"]
        r = s.post(f"{API}/tickets/label/create", json={
            "release_id": label1_session["release_id"],
            "category": "takedown",
            "subject": "TEST_TD Subject",
            "description": "TEST_TD description body",
            "reason": "Wrong metadata, needs takedown",
        })
        assert r.status_code == 200, r.text
        t = r.json()
        assert t["status"] == "open"
        assert t["category"] == "takedown"
        assert t["label_id"] == label1_session["label_id"]
        assert t["ticket_no"].startswith("RM-")
        # ticket_no format RM-YYMMDD-XXXXX
        parts = t["ticket_no"].split("-")
        assert len(parts) == 3 and len(parts[1]) == 6 and len(parts[2]) == 5
        assert "_id" not in t
        pytest.ticket_id = t["id"]

    def test_create_takedown_requires_reason(self, label1_session):
        s = label1_session["session"]
        r = s.post(f"{API}/tickets/label/create", json={
            "release_id": label1_session["release_id"],
            "category": "takedown",
            "subject": "No reason", "description": "missing reason",
        })
        assert r.status_code == 400, r.text
        assert "alasan" in r.json()["detail"].lower()

    def test_create_edit_audio_requires_both(self, label1_session):
        s = label1_session["session"]
        # missing both -> error
        r = s.post(f"{API}/tickets/label/create", json={
            "release_id": label1_session["release_id"],
            "category": "edit_audio",
            "subject": "Edit audio", "description": "need to swap",
        })
        assert r.status_code == 400
        # only url, missing track_id
        r = s.post(f"{API}/tickets/label/create", json={
            "release_id": label1_session["release_id"],
            "category": "edit_audio",
            "subject": "Edit audio", "description": "need to swap",
            "new_audio_url": "/api/files/audio/x.wav",
        })
        assert r.status_code == 400
        assert "track" in r.json()["detail"].lower()

    def test_create_edit_cover_requires_url(self, label1_session):
        s = label1_session["session"]
        r = s.post(f"{API}/tickets/label/create", json={
            "release_id": label1_session["release_id"],
            "category": "edit_cover",
            "subject": "Edit cover", "description": "need new cover",
        })
        assert r.status_code == 400
        assert "cover" in r.json()["detail"].lower()

    def test_create_edit_metadata_requires_both(self, label1_session):
        s = label1_session["session"]
        r = s.post(f"{API}/tickets/label/create", json={
            "release_id": label1_session["release_id"],
            "category": "edit_metadata",
            "subject": "Edit meta", "description": "need change",
        })
        assert r.status_code == 400
        r = s.post(f"{API}/tickets/label/create", json={
            "release_id": label1_session["release_id"],
            "category": "edit_metadata",
            "subject": "Edit meta", "description": "need change",
            "new_metadata": {"genre": "Rock"},
        })
        assert r.status_code == 400
        assert "alasan" in r.json()["detail"].lower()

    def test_create_content_id_requires_originality(self, label1_session):
        s = label1_session["session"]
        r = s.post(f"{API}/tickets/label/create", json={
            "release_id": label1_session["release_id"],
            "category": "content_id_claim",
            "subject": "CID claim", "description": "claim CID",
            "originality_declared": False,
        })
        assert r.status_code == 400
        assert "original" in r.json()["detail"].lower()

    def test_cannot_create_for_other_label_release(self, other_label, label1_session):
        """Other label trying to ticket label1's release -> 403."""
        s = other_label["session"]
        r = s.post(f"{API}/tickets/label/create", json={
            "release_id": label1_session["release_id"],
            "category": "other",
            "subject": "Trying", "description": "hack",
        })
        assert r.status_code == 403, r.text


# ============== LIST / DETAIL / VISIBILITY ==============
class TestListAndDetail:
    def test_label_list_own_only(self, label1_session):
        r = label1_session["session"].get(f"{API}/tickets/label")
        assert r.status_code == 200
        items = r.json()
        assert any(t["id"] == pytest.ticket_id for t in items)
        for t in items:
            assert t["label_id"] == label1_session["label_id"]

    def test_other_label_cannot_read(self, other_label):
        r = other_label["session"].get(f"{API}/tickets/{pytest.ticket_id}")
        assert r.status_code == 403, r.text

    def test_admin_list_all(self, super_session):
        r = super_session.get(f"{API}/tickets/admin")
        assert r.status_code == 200
        items = r.json()
        assert any(t["id"] == pytest.ticket_id for t in items)
        assert all("_id" not in t for t in items)

    def test_admin_filter_by_category(self, super_session):
        r = super_session.get(f"{API}/tickets/admin", params={"category": "takedown"})
        assert r.status_code == 200
        items = r.json()
        for t in items:
            assert t["category"] == "takedown"

    def test_admin_filter_by_status_q(self, super_session):
        r = super_session.get(f"{API}/tickets/admin", params={"status": "open", "q": "TEST_TD"})
        assert r.status_code == 200


# ============== COMMENT / STATUS FLIPS ==============
class TestCommentsAndStatusFlow:
    def test_admin_comment_flips_to_waiting_label(self, super_session):
        r = super_session.post(f"{API}/tickets/{pytest.ticket_id}/comment",
                               json={"body": "Hai, ini admin"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["new_status"] == "waiting_label"

    def test_label_comment_flips_to_waiting_admin(self, label1_session):
        r = label1_session["session"].post(f"{API}/tickets/{pytest.ticket_id}/comment",
                                           json={"body": "OK admin, terima kasih"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["new_status"] == "waiting_admin"

    def test_admin_update_status_in_progress(self, super_session):
        r = super_session.post(f"{API}/tickets/admin/{pytest.ticket_id}/status",
                               json={"status": "in_progress", "internal_note": "Working on it"})
        assert r.status_code == 200, r.text
        t = r.json()
        assert t["status"] == "in_progress"
        assert t["internal_note"] == "Working on it"
        # system comment added
        det = super_session.get(f"{API}/tickets/{pytest.ticket_id}").json()
        sys_comments = [c for c in det["comments"] if c.get("is_system")]
        assert any("Sedang Diproses" in c["body"] for c in sys_comments)


# ============== LABEL CANCEL ==============
class TestLabelCancel:
    def test_cannot_cancel_done(self, super_session, label1_session):
        """Create a ticket → admin marks done → label cancel must 400."""
        s = label1_session["session"]
        r = s.post(f"{API}/tickets/label/create", json={
            "release_id": label1_session["release_id"],
            "category": "other",
            "subject": "TEST_OTHER will close",
            "description": "to be closed",
        })
        assert r.status_code == 200
        tid = r.json()["id"]
        # admin sets done
        r2 = super_session.post(f"{API}/tickets/admin/{tid}/status",
                                json={"status": "done"})
        assert r2.status_code == 200
        # label cancel -> 400
        r3 = s.post(f"{API}/tickets/{tid}/cancel")
        assert r3.status_code == 400, r3.text
        # also cannot comment on done ticket
        r4 = s.post(f"{API}/tickets/{tid}/comment", json={"body": "still there?"})
        assert r4.status_code == 400, r4.text
        assert "ditutup" in r4.json()["detail"].lower()

    def test_label_can_cancel_open(self, label1_session):
        s = label1_session["session"]
        r = s.post(f"{API}/tickets/label/create", json={
            "release_id": label1_session["release_id"],
            "category": "other",
            "subject": "TEST_OTHER cancel me",
            "description": "to be cancelled",
        })
        assert r.status_code == 200
        tid = r.json()["id"]
        r2 = s.post(f"{API}/tickets/{tid}/cancel")
        assert r2.status_code == 200, r2.text
        assert r2.json()["status"] == "cancelled"


# ============== ATTACHMENT UPLOAD ==============
class TestAttachmentUpload:
    def test_audio_purpose_requires_wav(self, label1_session):
        s = label1_session["session"]
        files = {"file": ("song.mp3", b"FAKE", "audio/mpeg")}
        data = {"purpose": "audio"}
        r = requests.post(f"{API}/tickets/upload-attachment",
                          files=files, data=data, cookies=s.cookies)
        assert r.status_code == 400
        assert "wav" in r.json()["detail"].lower()

    def test_cover_purpose_requires_3000(self, label1_session):
        s = label1_session["session"]
        # 100x100 png
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (100, 100), "red").save(buf, "PNG")
        buf.seek(0)
        files = {"file": ("c.png", buf.read(), "image/png")}
        data = {"purpose": "cover"}
        r = requests.post(f"{API}/tickets/upload-attachment",
                          files=files, data=data, cookies=s.cookies)
        assert r.status_code == 400
        assert "3000" in r.json()["detail"]

    def test_general_purpose_accepts_pdf(self, label1_session):
        s = label1_session["session"]
        files = {"file": ("note.pdf", b"%PDF-1.4\n", "application/pdf")}
        data = {"purpose": "general"}
        r = requests.post(f"{API}/tickets/upload-attachment",
                          files=files, data=data, cookies=s.cookies)
        assert r.status_code == 200, r.text
        assert r.json()["url"].endswith(".pdf")

    def test_general_purpose_rejects_exe(self, label1_session):
        s = label1_session["session"]
        files = {"file": ("bad.exe", b"MZ", "application/octet-stream")}
        data = {"purpose": "general"}
        r = requests.post(f"{API}/tickets/upload-attachment",
                          files=files, data=data, cookies=s.cookies)
        assert r.status_code == 400
