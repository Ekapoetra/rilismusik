"""Iter64 - Support ticket workflow regression tests (API + persistence)."""
import os
import asyncio
import uuid
from pathlib import Path
from typing import Dict, List

import pymongo
import pytest
import requests
from dotenv import load_dotenv

from auth_utils import hash_password
from tests.support_config import SUPERADMIN, SUPPORT


load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/backend/.env.test", override=True)
load_dotenv("/app/frontend/.env", override=True)

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
NOW = "2026-02-10T00:00:00+00:00"


# Support workflow modules: auth, ticket categories, create/list/detail, role/ownership guards
def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _login(email: str, password: str) -> str:
    response = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=40)
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _record_credential(email, password):
    path = Path("/app/memory/test_credentials.md")
    with path.open("a") as stream:
        stream.write(f"\n- Iter64 fixture `{email}` / `{password}` — ACTIVE QA\n")


def _retire_credentials(emails):
    path = Path("/app/memory/test_credentials.md")
    lines = path.read_text().splitlines()
    for index, line in enumerate(lines):
        if any(f"`{email}`" in line for email in emails) and "ACTIVE QA" in line:
            lines[index] = line.replace("ACTIVE QA", "REMOVED (fixture teardown)")
    path.write_text("\n".join(lines) + "\n")


def _seed_verified_label_with_releases(db, prefix: str) -> Dict[str, str]:
    user_id = f"iter64-user-{prefix}"
    label_id = f"iter64-label-{prefix}"
    email = f"iter64-{prefix}@example.com"
    password = os.environ["TEST_ITER64_LABEL_PASSWORD"]
    _record_credential(email, password)
    db.users.insert_one({
        "id": user_id,
        "name": f"Iter64 Label {prefix}",
        "email": email,
        "password_hash": hash_password(password),
        "role": "label",
        "status": "active",
        "token_version": 0,
        "email_verified_at": NOW,
        "created_at": NOW,
        "updated_at": NOW,
    })
    db.labels.insert_one({
        "id": label_id,
        "user_id": user_id,
        "label_name": f"iter64-label-{prefix}",
        "pic_name": "Iter64 PIC",
        "whatsapp": "081234567890",
        "address": "Jl. Iter64 No. 1",
        "city": "Jakarta",
        "country": "Indonesia",
        "logo_storage_key": f"label-logo/{label_id}.png",
        "account_status": "active",
        "kyc_status": "verified",
        "kyc_document_id": f"iter64-kyc-{prefix}",
        "created_at": NOW,
        "updated_at": NOW,
    })
    db.bank_accounts.insert_one({
        "id": f"iter64-bank-{prefix}",
        "label_id": label_id,
        "bank_name": "BCA",
        "account_number": "123123123",
        "account_holder_name": "Iter64 PIC",
        "verified_status": "verified",
        "created_at": NOW,
        "updated_at": NOW,
    })
    db.kyc_documents.insert_one({
        "id": f"iter64-kyc-{prefix}",
        "label_id": label_id,
        "storage_key": f"kyc-private/{label_id}/ktp.png",
        "status": "verified",
        "is_current": True,
        "uploaded_at": NOW,
        "reviewed_at": NOW,
    })
    db.contracts.insert_one({
        "id": f"iter64-contract-{prefix}",
        "label_id": label_id,
        "status": "active",
        "start_date": "2026-01-01",
        "end_date": "2030-01-01",
        "created_at": NOW,
    })

    release_a = f"iter64-release-a-{prefix}"
    release_b = f"iter64-release-b-{prefix}"
    db.releases.insert_many([
        {
            "id": release_a,
            "label_id": label_id,
            "release_title": f"Iter64 Release A {prefix}",
            "artist_name": "Iter64 Artist",
            "genre": "Pop",
            "language": "Indonesia",
            "copyright_line": "© Iter64",
            "p_line": "℗ Iter64",
            "upc": 123456789012,
            "status": "live",
            "cover_url": "/api/files/iter64-a.jpg",
            "created_at": NOW,
            "updated_at": NOW,
        },
        {
            "id": release_b,
            "label_id": label_id,
            "release_title": f"Iter64 Release B {prefix}",
            "artist_name": "Iter64 Artist B",
            "genre": "Rock",
            "language": "English",
            "copyright_line": "© Iter64B",
            "p_line": "℗ Iter64B",
            "upc": None,
            "status": "live",
            "cover_url": "/api/files/iter64-b.jpg",
            "created_at": NOW,
            "updated_at": NOW,
        },
    ])
    db.tracks.insert_many([
        {
            "id": f"iter64-track-a1-{prefix}",
            "release_id": release_a,
            "label_id": label_id,
            "track_title": "A1",
            "track_number": 1,
            "isrc": "IDAAA2600001",
            "created_at": NOW,
            "updated_at": NOW,
        },
        {
            "id": f"iter64-track-a2-{prefix}",
            "release_id": release_a,
            "label_id": label_id,
            "track_title": "A2",
            "track_number": 2,
            "isrc": "IDAAA2600002",
            "created_at": NOW,
            "updated_at": NOW,
        },
        {
            "id": f"iter64-track-b1-{prefix}",
            "release_id": release_b,
            "label_id": label_id,
            "track_title": "B1",
            "track_number": 1,
            "isrc": None,
            "created_at": NOW,
            "updated_at": NOW,
        },
    ])
    return {
        "user_id": user_id,
        "label_id": label_id,
        "email": email,
        "password": password,
        "release_a": release_a,
        "release_b": release_b,
    }


@pytest.fixture(scope="module")
def seeded_env():
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    owner = _seed_verified_label_with_releases(db, f"owner-{suffix}")
    outsider = _seed_verified_label_with_releases(db, f"outsider-{suffix}")
    state = {"db": db, "owner": owner, "outsider": outsider, "suffix": suffix, "admin_ids": [], "role_ids": [], "uploaded_keys": [], "admin_emails": []}
    sentinel_id = f"iter64-cleanup-sentinel-{suffix}"
    db.notifications.insert_one({"id": sentinel_id, "user_id": "iter64-unrelated-sentinel", "title": "Tiket di luar scope fixture", "meta": {"ticket_id": "unrelated-ticket-sentinel"}})
    yield state
    label_ids = [owner["label_id"], outsider["label_id"]]
    release_ids = [owner["release_a"], owner["release_b"], outsider["release_a"], outsider["release_b"]]
    user_ids = [owner["user_id"], outsider["user_id"], *state["admin_ids"]]
    ticket_ids = [row["id"] for row in db.support_tickets.find({"label_id": {"$in": label_ids}}, {"_id": 0, "id": 1})]
    db.ticket_comments.delete_many({"ticket_id": {"$in": ticket_ids}})
    db.support_tickets.delete_many({"id": {"$in": ticket_ids}})
    db.notifications.delete_many({"$or": [{"meta.ticket_id": {"$in": ticket_ids}}, {"user_id": {"$in": user_ids}}]})
    db.activity_logs.delete_many({"reference_id": {"$in": ticket_ids + user_ids + state["role_ids"]}})
    db.tracks.delete_many({"release_id": {"$in": release_ids}})
    db.releases.delete_many({"id": {"$in": release_ids}})
    for name in ("bank_accounts", "contracts", "kyc_documents"):
        db[name].delete_many({"label_id": {"$in": label_ids}})
    db.labels.delete_many({"id": {"$in": label_ids}})
    db.users.delete_many({"id": {"$in": user_ids}})
    db.admin_roles.delete_many({"id": {"$in": state["role_ids"]}})
    import storage_service
    for key in state["uploaded_keys"]:
        asyncio.run(storage_service.delete_object(key=key))
    _retire_credentials([owner["email"], outsider["email"], *state["admin_emails"]])
    assert db.notifications.count_documents({"id": sentinel_id}) == 1, "Cleanup must not delete notifications outside owned fixture IDs"
    db.notifications.delete_one({"id": sentinel_id})


@pytest.fixture(scope="module")
def auth(seeded_env):
    owner_token = _login(seeded_env["owner"]["email"], seeded_env["owner"]["password"])
    outsider_token = _login(seeded_env["outsider"]["email"], seeded_env["outsider"]["password"])
    support_token = _login(SUPPORT["email"], SUPPORT["password"])
    super_token = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    return {
        "owner": owner_token,
        "outsider": outsider_token,
        "support": support_token,
        "super": super_token,
    }


def _create_ticket(token: str, payload: Dict) -> requests.Response:
    return requests.post(f"{API}/tickets/label/create", headers=_headers(token), json=payload, timeout=40)


def test_categories_only_six_active(auth):
    response = requests.get(f"{API}/tickets/categories", headers=_headers(auth["owner"]), timeout=40)
    assert response.status_code == 200, response.text
    values = {item["value"] for item in response.json()}
    assert values == {"takedown", "edit_metadata", "edit_audio", "edit_cover", "content_id_claim", "content_id_release"}


def test_create_rejects_removed_categories_with_422(auth, seeded_env):
    for removed in ("royalty_issue", "other"):
        response = _create_ticket(auth["owner"], {
            "release_id": seeded_env["owner"]["release_a"],
            "category": removed,
            "subject": "will fail",
            "description": "will fail",
        })
        assert response.status_code == 422, response.text


def test_legacy_removed_type_still_listable_for_owner_and_admin(auth, seeded_env):
    tid = f"iter64-legacy-{seeded_env['suffix']}"
    seeded_env["db"].support_tickets.insert_one({
        "id": tid,
        "ticket_no": f"RM-260210-{seeded_env['suffix'][:5].upper()}",
        "label_id": seeded_env["owner"]["label_id"],
        "release_id": seeded_env["owner"]["release_a"],
        "release_title": "Legacy",
        "category": "other",
        "category_label": "Lainnya",
        "subject": "Legacy Ticket",
        "description": "legacy description",
        "status": "open",
        "created_at": NOW,
        "updated_at": NOW,
    })
    owner_list = requests.get(f"{API}/tickets/label", headers=_headers(auth["owner"]), timeout=40)
    assert owner_list.status_code == 200
    assert any(item["id"] == tid for item in owner_list.json())
    admin_detail = requests.get(f"{API}/tickets/{tid}", headers=_headers(auth["support"]), timeout=40)
    assert admin_detail.status_code == 200
    assert admin_detail.json()["ticket"]["category"] == "other"


def test_noauth_401_and_other_label_403(seeded_env, auth):
    unauth = requests.get(f"{API}/tickets/{'iter64-missing'}", timeout=40)
    assert unauth.status_code == 401

    created = _create_ticket(auth["owner"], {
        "release_id": seeded_env["owner"]["release_a"],
        "category": "takedown",
        "subject": "spoof subject",
        "description": "valid description",
        "reason": "Revisi Metadata",
    })
    assert created.status_code == 200, created.text
    ticket_id = created.json()["id"]
    forbidden = requests.get(f"{API}/tickets/{ticket_id}", headers=_headers(auth["outsider"]), timeout=40)
    assert forbidden.status_code == 403


def test_takedown_server_rules_autosubject_and_db_authoritative_codes(auth, seeded_env):
    invalid_reason = _create_ticket(auth["owner"], {
        "release_id": seeded_env["owner"]["release_a"],
        "category": "takedown",
        "subject": "client fake",
        "description": "abc",
        "reason": "Alasan Bebas",
    })
    assert invalid_reason.status_code == 400

    blank_desc = _create_ticket(auth["owner"], {
        "release_id": seeded_env["owner"]["release_a"],
        "category": "takedown",
        "subject": "client fake",
        "description": "  ",
        "reason": "Konflik Hak Cipta",
    })
    assert blank_desc.status_code == 400

    ok = _create_ticket(auth["owner"], {
        "release_id": seeded_env["owner"]["release_a"],
        "category": "takedown",
        "subject": "CLIENT_SUBJECT_SHOULD_BE_IGNORED",
        "description": "Tolong takedown rilisan ini",
        "reason": "Konflik Internal",
    })
    assert ok.status_code == 200, ok.text
    payload = ok.json()
    assert payload["subject"].startswith("Takedown Rilisan — Iter64 Release A")
    assert payload["upc"] == "123456789012"
    assert payload["isrcs"] == ["IDAAA2600001", "IDAAA2600002"]
    assert len(payload["release_tracks"]) == 2

    detail = requests.get(f"{API}/tickets/{payload['id']}", headers=_headers(auth["owner"]), timeout=40)
    assert detail.status_code == 200
    assert detail.json()["comments"][0]["body"] == "Tolong takedown rilisan ini"


def test_edit_metadata_merges_partial_rejects_unknown_and_preserves_release(auth, seeded_env):
    bad_reason = _create_ticket(auth["owner"], {
        "release_id": seeded_env["owner"]["release_a"],
        "category": "edit_metadata",
        "reason": "   ",
        "new_metadata": {"genre": "Dangdut"},
    })
    assert bad_reason.status_code == 400

    bad_field = _create_ticket(auth["owner"], {
        "release_id": seeded_env["owner"]["release_a"],
        "category": "edit_metadata",
        "reason": "valid",
        "new_metadata": {"unknown_key": "X"},
    })
    assert bad_field.status_code == 400

    original_release = seeded_env["db"].releases.find_one({"id": seeded_env["owner"]["release_a"]}, {"_id": 0})
    response = _create_ticket(auth["owner"], {
        "release_id": seeded_env["owner"]["release_a"],
        "category": "edit_metadata",
        "description": "should be ignored",
        "reason": "Perbaiki penulisan judul",
        "new_metadata": {"release_title": "Judul Baru Iter64"},
    })
    assert response.status_code == 200, response.text
    ticket = response.json()
    assert ticket["description"] == ""
    assert ticket["new_metadata"]["release_title"] == "Judul Baru Iter64"
    assert ticket["new_metadata"]["artist_name"] == "Iter64 Artist"

    detail = requests.get(f"{API}/tickets/{ticket['id']}", headers=_headers(auth["owner"]), timeout=40)
    assert detail.status_code == 200
    assert detail.json()["comments"][0]["body"] == "Perbaiki penulisan judul"

    after_release = seeded_env["db"].releases.find_one({"id": seeded_env["owner"]["release_a"]}, {"_id": 0})
    assert after_release["release_title"] == original_release["release_title"]
    assert after_release["genre"] == original_release["genre"]


def test_content_id_claim_and_release_urls_validation_and_compatibility(auth, seeded_env):
    bad_http = _create_ticket(auth["owner"], {
        "release_id": seeded_env["owner"]["release_a"],
        "category": "content_id_claim",
        "originality_declared": True,
        "youtube_urls": ["http://youtube.com/watch?v=dQw4w9WgXcQ"],
    })
    assert bad_http.status_code == 400

    duplicate_video = _create_ticket(auth["owner"], {
        "release_id": seeded_env["owner"]["release_a"],
        "category": "content_id_claim",
        "originality_declared": True,
        "youtube_urls": [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
        ],
    })
    assert duplicate_video.status_code == 400

    valid_claim = _create_ticket(auth["owner"], {
        "release_id": seeded_env["owner"]["release_a"],
        "category": "content_id_claim",
        "description": "",
        "originality_declared": True,
        "youtube_urls": [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/jfKfPfyJRdk",
        ],
    })
    assert valid_claim.status_code == 200, valid_claim.text
    claim_ticket = valid_claim.json()
    assert len(claim_ticket["youtube_urls"]) == 2

    claim_detail = requests.get(f"{API}/tickets/{claim_ticket['id']}", headers=_headers(auth["owner"]), timeout=40)
    assert claim_detail.status_code == 200
    assert claim_detail.json()["comments"][0]["body"].strip() != ""

    legacy_single = _create_ticket(auth["owner"], {
        "release_id": seeded_env["owner"]["release_a"],
        "category": "content_id_release",
        "description": "",
        "originality_declared": True,
        "youtube_url": "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
    })
    assert legacy_single.status_code == 200, legacy_single.text
    assert legacy_single.json()["youtube_urls"][0] == "https://m.youtube.com/watch?v=dQw4w9WgXcQ"


def test_edit_metadata_optional_attachment_upload_and_persist(auth, seeded_env):
    files = {"file": ("iter64-note.txt", b"iter64 attachment", "text/plain")}
    data = {"purpose": "general"}
    upload = requests.post(
        f"{API}/tickets/upload-attachment",
        headers={"Authorization": f"Bearer {auth['owner']}"},
        files=files,
        data=data,
        timeout=40,
    )
    assert upload.status_code == 200, upload.text
    uploaded_url = upload.json()["url"]
    seeded_env["uploaded_keys"].append(uploaded_url.removeprefix("/api/files/"))

    created = _create_ticket(auth["owner"], {
        "release_id": seeded_env["owner"]["release_a"],
        "category": "edit_metadata",
        "reason": "Attachment regression",
        "new_metadata": {"genre": "Jazz"},
        "attachments": [uploaded_url],
    })
    assert created.status_code == 200, created.text
    assert uploaded_url in created.json().get("attachments", [])


def test_internal_note_redacted_for_label_list_and_detail(auth, seeded_env):
    created = _create_ticket(auth["owner"], {
        "release_id": seeded_env["owner"]["release_a"],
        "category": "takedown",
        "description": "deskripsi valid",
        "reason": "Revisi Metadata",
    })
    assert created.status_code == 200
    ticket_id = created.json()["id"]

    admin_update = requests.post(
        f"{API}/tickets/admin/{ticket_id}/status",
        headers=_headers(auth["support"]),
        json={"status": "in_progress", "internal_note": "iter64 secret"},
        timeout=40,
    )
    assert admin_update.status_code == 200
    assert admin_update.json().get("internal_note") == "iter64 secret"

    owner_list = requests.get(f"{API}/tickets/label", headers=_headers(auth["owner"]), timeout=40)
    assert owner_list.status_code == 200
    own_item = next(item for item in owner_list.json() if item["id"] == ticket_id)
    assert "internal_note" not in own_item

    owner_detail = requests.get(f"{API}/tickets/{ticket_id}", headers=_headers(auth["owner"]), timeout=40)
    assert owner_detail.status_code == 200
    assert "internal_note" not in owner_detail.json()["ticket"]


def test_dynamic_admin_view_only_can_read_not_mutate(auth, seeded_env):
    ticket = _create_ticket(auth["owner"], {
        "release_id": seeded_env["owner"]["release_a"],
        "category": "takedown",
        "description": "deskripsi valid",
        "reason": "Pindah Aggregator",
    }).json()
    ticket_id = ticket["id"]

    role_resp = requests.post(
        f"{API}/admin/access/roles",
        headers=_headers(auth["super"]),
        json={
            "name": f"iter64-support-view-{seeded_env['suffix']}",
            "permissions": ["support.view"],
        },
        timeout=40,
    )
    assert role_resp.status_code == 200, role_resp.text
    role_id = role_resp.json()["id"]
    seeded_env["role_ids"].append(role_id)

    admin_email = f"iter64-viewonly-{seeded_env['suffix']}@example.com"
    admin_pass = os.environ["TEST_ITER64_VIEW_PASSWORD"]
    _record_credential(admin_email, admin_pass)
    seeded_env["admin_emails"].append(admin_email)
    admin_resp = requests.post(
        f"{API}/admin/admin-users",
        headers=_headers(auth["super"]),
        json={
            "name": f"iter64-viewonly-{seeded_env['suffix']}",
            "email": admin_email,
            "password": admin_pass,
            "admin_role_id": role_id,
        },
        timeout=40,
    )
    assert admin_resp.status_code == 200, admin_resp.text
    seeded_env["admin_ids"].append(admin_resp.json()["id"])

    view_token = _login(admin_email, admin_pass)
    can_read = requests.get(f"{API}/tickets/{ticket_id}", headers=_headers(view_token), timeout=40)
    assert can_read.status_code == 200

    cannot_status = requests.post(
        f"{API}/tickets/admin/{ticket_id}/status",
        headers=_headers(view_token),
        json={"status": "done"},
        timeout=40,
    )
    assert cannot_status.status_code == 403

    cannot_comment = requests.post(
        f"{API}/tickets/{ticket_id}/comment",
        headers=_headers(view_token),
        json={"body": "admin read-only should not reply"},
        timeout=40,
    )
    assert cannot_comment.status_code == 403
