"""Iter 61 — admin + label release deletion regression and service guards."""
import os
import uuid
from typing import Any, Dict, List
from unittest.mock import AsyncMock

import pymongo
import pytest
import requests
from dotenv import load_dotenv
from fastapi import HTTPException

from auth_utils import hash_password
from tests.support_config import FINANCE, RELEASE_ADMIN, SUPERADMIN, temporary_password


load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/frontend/.env", override=True)
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"
NOW = "2026-02-01T00:00:00+00:00"


# --- shared auth/db helpers for API tests ---
def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _login(email: str, password: str) -> str:
    response = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_label_user(db, suffix: str, *, with_kyc: bool = True) -> Dict[str, str]:
    user_id = f"iter61-user-{suffix}"
    label_id = f"iter61-label-{suffix}"
    email = f"iter61-{suffix}@example.com"
    password = temporary_password("Iter61Label")
    db.users.insert_one({
        "id": user_id,
        "name": f"Iter61 Label {suffix}",
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
        "label_name": f"Iter61 Label {suffix}",
        "pic_name": "Iter61 PIC",
        "whatsapp": "081200000000",
        "address": "Jl. Iter61",
        "city": "Jakarta",
        "country": "Indonesia",
        "logo_storage_key": f"label-logo/{label_id}.png" if with_kyc else None,
        "account_status": "active",
        "kyc_status": "verified" if with_kyc else "pending_review",
        "kyc_document_id": f"iter61-kyc-{suffix}" if with_kyc else None,
        "created_at": NOW,
        "updated_at": NOW,
    })
    if with_kyc:
        db.bank_accounts.insert_one({
            "id": f"iter61-bank-{suffix}",
            "label_id": label_id,
            "bank_name": "BCA",
            "account_number": "1234567890",
            "account_holder_name": "Iter61 PIC",
            "verified_status": "verified",
            "created_at": NOW,
        })
        db.contracts.insert_one({
            "id": f"iter61-contract-{suffix}",
            "label_id": label_id,
            "status": "active",
            "start_date": "2026-01-01",
            "end_date": "2030-12-31",
            "created_at": NOW,
        })
    if with_kyc:
        db.kyc_documents.insert_one({
            "id": f"iter61-kyc-{suffix}",
            "label_id": label_id,
            "storage_key": f"kyc-private/{label_id}/ktp.png",
            "status": "verified",
            "is_current": True,
            "uploaded_at": NOW,
            "reviewed_at": NOW,
        })
    return {"user_id": user_id, "label_id": label_id, "email": email, "password": password}


def _insert_release_with_tracks(
    db,
    *,
    release_id: str,
    label_id: str,
    status: str,
    title: str,
    cover_url: str = "/api/files/iter61-cover.jpg",
    track_urls: List[str] | None = None,
):
    db.releases.insert_one({
        "id": release_id,
        "label_id": label_id,
        "release_title": title,
        "artist_name": "Iter61 Artist",
        "release_type": "single",
        "release_date": "2026-03-10",
        "status": status,
        "cover_url": cover_url,
        "created_at": NOW,
        "updated_at": NOW,
    })
    for index, audio_url in enumerate(track_urls or ["/api/files/iter61-audio.wav"], start=1):
        db.tracks.insert_one({
            "id": f"iter61-track-{release_id}-{index}",
            "release_id": release_id,
            "label_id": label_id,
            "track_title": f"Track {index}",
            "track_number": index,
            "audio_url": audio_url,
            "created_at": NOW,
            "updated_at": NOW,
        })


def _cleanup_label_seed(db, seeded: Dict[str, str]):
    db.bank_accounts.delete_many({"label_id": seeded["label_id"]})
    db.contracts.delete_many({"label_id": seeded["label_id"]})
    db.kyc_documents.delete_many({"label_id": seeded["label_id"]})
    db.tracks.delete_many({"label_id": seeded["label_id"]})
    db.releases.delete_many({"label_id": seeded["label_id"]})
    db.labels.delete_one({"id": seeded["label_id"]})
    db.users.delete_one({"id": seeded["user_id"]})


def _cleanup_release_artifacts(db, release_ids: List[str]):
    db.notifications.delete_many({"meta.release_id": {"$in": release_ids}})
    db.activity_logs.delete_many({"reference_id": {"$in": release_ids}})
    db.tracks.delete_many({"release_id": {"$in": release_ids}})
    db.releases.delete_many({"id": {"$in": release_ids}})
    db.payments.delete_many({"release_id": {"$in": release_ids}})
    db.royalty_lines.delete_many({"release_id": {"$in": release_ids}})


# --- admin endpoint behavior + audit + isolation checks ---
def test_admin_delete_draft_and_rejected_with_audit_and_isolation():
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    target_release = f"iter61-target-{suffix}"
    rejected_release = f"iter61-rejected-{suffix}"
    unrelated_release = f"iter61-unrelated-{suffix}"
    _insert_release_with_tracks(
        db,
        release_id=target_release,
        label_id=f"iter61-label-a-{suffix}",
        status="draft",
        title="Iter61 Draft Delete",
        cover_url="/api/files/iter61-shared-cover.jpg",
        track_urls=["/api/files/iter61-target.wav"],
    )
    _insert_release_with_tracks(
        db,
        release_id=rejected_release,
        label_id=f"iter61-label-b-{suffix}",
        status="rejected",
        title="Iter61 Rejected Delete",
        track_urls=["/api/files/iter61-rejected.wav"],
    )
    _insert_release_with_tracks(
        db,
        release_id=unrelated_release,
        label_id=f"iter61-label-b-{suffix}",
        status="live",
        title="Iter61 Keep Me",
        track_urls=["/api/files/iter61-unrelated.wav"],
    )
    db.payments.insert_one({"id": f"iter61-pay-{suffix}", "release_id": unrelated_release, "status": "paid", "amount": 12000, "created_at": NOW})
    db.royalty_lines.insert_one({"id": f"iter61-royalty-{suffix}", "release_id": unrelated_release, "label_id": f"iter61-label-b-{suffix}", "status": "available"})

    super_token = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    release_admin_token = _login(RELEASE_ADMIN["email"], RELEASE_ADMIN["password"])
    try:
        deleted = requests.delete(f"{API}/admin/releases/{target_release}", headers=_headers(super_token), timeout=30)
        assert deleted.status_code == 200, deleted.text
        assert deleted.json()["deleted"] == target_release
        assert db.releases.find_one({"id": target_release}) is None
        assert db.tracks.count_documents({"release_id": target_release}) == 0

        audit = db.activity_logs.find_one({"reference_id": target_release, "action": "release_delete"}, {"_id": 0})
        assert audit is not None
        assert audit.get("before_data", {}).get("title") == "Iter61 Draft Delete"
        assert audit.get("before_data", {}).get("status") == "draft"
        assert audit.get("before_data", {}).get("label_id") == f"iter61-label-a-{suffix}"

        deleted_rejected = requests.delete(f"{API}/admin/releases/{rejected_release}", headers=_headers(release_admin_token), timeout=30)
        assert deleted_rejected.status_code == 200, deleted_rejected.text
        assert db.releases.find_one({"id": rejected_release}) is None

        assert db.releases.find_one({"id": unrelated_release}, {"_id": 0, "id": 1}) is not None
        assert db.tracks.count_documents({"release_id": unrelated_release}) == 1
        assert db.payments.count_documents({"release_id": unrelated_release}) == 1
        assert db.royalty_lines.count_documents({"release_id": unrelated_release}) == 1
    finally:
        _cleanup_release_artifacts(db, [target_release, rejected_release, unrelated_release])


# --- admin endpoint auth and permission matrix ---
def test_admin_delete_permission_and_status_matrix():
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    draft_release = f"iter61-matrix-draft-{suffix}"
    submitted_release = f"iter61-matrix-submitted-{suffix}"
    _insert_release_with_tracks(db, release_id=draft_release, label_id=f"iter61-label-m-{suffix}", status="draft", title="Iter61 Matrix Draft")
    _insert_release_with_tracks(db, release_id=submitted_release, label_id=f"iter61-label-m-{suffix}", status="submitted", title="Iter61 Matrix Submitted")

    super_token = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    finance_token = _login(FINANCE["email"], FINANCE["password"])

    role_id = None
    admin_user_id = None
    no_perm_email = f"iter61-noperm-{suffix}@example.com"
    no_perm_password = temporary_password("Iter61NoPerm")
    with_perm_email = f"iter61-withperm-{suffix}@example.com"
    with_perm_password = temporary_password("Iter61WithPerm")
    role_with_perm_id = None
    admin_with_perm_id = None
    try:
        unauth = requests.delete(f"{API}/admin/releases/{draft_release}", timeout=30)
        assert unauth.status_code == 401

        missing = requests.delete(f"{API}/admin/releases/iter61-missing-{suffix}", headers=_headers(super_token), timeout=30)
        assert missing.status_code == 404

        forbidden_status = requests.delete(f"{API}/admin/releases/{submitted_release}", headers=_headers(super_token), timeout=30)
        assert forbidden_status.status_code == 400

        finance_forbidden = requests.delete(f"{API}/admin/releases/{draft_release}", headers=_headers(finance_token), timeout=30)
        assert finance_forbidden.status_code == 403

        role_create = requests.post(
            f"{API}/admin/access/roles",
            headers=_headers(super_token),
            json={"name": f"Iter61 ReadOnly {suffix}", "description": "No release review", "permissions": ["dashboard.view"]},
            timeout=30,
        )
        assert role_create.status_code == 200, role_create.text
        role_id = role_create.json()["id"]
        create_admin = requests.post(
            f"{API}/admin/admin-users",
            headers=_headers(super_token),
            json={"name": "Iter61 No Perm", "email": no_perm_email, "password": no_perm_password, "admin_role_id": role_id},
            timeout=30,
        )
        assert create_admin.status_code == 200, create_admin.text
        admin_user_id = create_admin.json()["id"]
        no_perm_token = _login(no_perm_email, no_perm_password)
        no_perm_delete = requests.delete(f"{API}/admin/releases/{draft_release}", headers=_headers(no_perm_token), timeout=30)
        assert no_perm_delete.status_code == 403

        with_perm_role = requests.post(
            f"{API}/admin/access/roles",
            headers=_headers(super_token),
            json={"name": f"Iter61 Release Review {suffix}", "description": "Has releases.review", "permissions": ["dashboard.view", "releases.review", "releases.view"]},
            timeout=30,
        )
        assert with_perm_role.status_code == 200, with_perm_role.text
        role_with_perm_id = with_perm_role.json()["id"]
        create_with_perm = requests.post(
            f"{API}/admin/admin-users",
            headers=_headers(super_token),
            json={"name": "Iter61 With Perm", "email": with_perm_email, "password": with_perm_password, "admin_role_id": role_with_perm_id},
            timeout=30,
        )
        assert create_with_perm.status_code == 200, create_with_perm.text
        admin_with_perm_id = create_with_perm.json()["id"]
        with_perm_token = _login(with_perm_email, with_perm_password)
        with_perm_delete = requests.delete(f"{API}/admin/releases/{draft_release}", headers=_headers(with_perm_token), timeout=30)
        assert with_perm_delete.status_code == 200, with_perm_delete.text

        repeat_delete = requests.delete(f"{API}/admin/releases/{draft_release}", headers=_headers(with_perm_token), timeout=30)
        assert repeat_delete.status_code == 404
    finally:
        if admin_user_id:
            requests.delete(f"{API}/admin/admin-users/{admin_user_id}", headers=_headers(super_token), timeout=30)
        if admin_with_perm_id:
            requests.delete(f"{API}/admin/admin-users/{admin_with_perm_id}", headers=_headers(super_token), timeout=30)
        if role_id:
            requests.delete(f"{API}/admin/access/roles/{role_id}", headers=_headers(super_token), timeout=30)
        if role_with_perm_id:
            requests.delete(f"{API}/admin/access/roles/{role_with_perm_id}", headers=_headers(super_token), timeout=30)
        db.users.delete_many({"email": {"$in": [no_perm_email, with_perm_email]}})
        _cleanup_release_artifacts(db, [draft_release, submitted_release])


def test_admin_endpoint_rejects_non_admin_label_and_artist():
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    draft_release = f"iter61-nonadmin-{suffix}"
    _insert_release_with_tracks(db, release_id=draft_release, label_id=f"iter61-label-nonadmin-{suffix}", status="draft", title="Iter61 Nonadmin")
    seeded_label = _seed_label_user(db, f"nonadmin-{suffix}", with_kyc=True)
    artist_email = f"iter61-artist-{suffix}@example.com"
    artist_password = temporary_password("Iter61Artist")
    db.users.insert_one({
        "id": f"iter61-artist-{suffix}",
        "name": "Iter61 Artist",
        "email": artist_email,
        "password_hash": hash_password(artist_password),
        "role": "artist",
        "status": "active",
        "token_version": 0,
        "email_verified_at": NOW,
        "created_at": NOW,
        "updated_at": NOW,
    })
    try:
        label_token = _login(seeded_label["email"], seeded_label["password"])
        artist_token = _login(artist_email, artist_password)
        label_forbidden = requests.delete(f"{API}/admin/releases/{draft_release}", headers=_headers(label_token), timeout=30)
        assert label_forbidden.status_code == 403
        artist_forbidden = requests.delete(f"{API}/admin/releases/{draft_release}", headers=_headers(artist_token), timeout=30)
        assert artist_forbidden.status_code == 403
    finally:
        db.users.delete_one({"email": artist_email})
        _cleanup_label_seed(db, seeded_label)
        _cleanup_release_artifacts(db, [draft_release])


# --- label endpoint regression: ownership + status + KYC enforcement ---
def test_label_delete_endpoint_requires_ownership_status_and_kyc():
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    owner = _seed_label_user(db, f"owner-{suffix}", with_kyc=True)
    other = _seed_label_user(db, f"other-{suffix}", with_kyc=True)
    no_kyc = _seed_label_user(db, f"nokyc-{suffix}", with_kyc=False)

    owner_draft = f"iter61-owner-draft-{suffix}"
    owner_rejected = f"iter61-owner-rejected-{suffix}"
    owner_live = f"iter61-owner-live-{suffix}"
    other_draft = f"iter61-other-draft-{suffix}"
    nokyc_draft = f"iter61-nokyc-draft-{suffix}"
    for rid, lid, status in [
        (owner_draft, owner["label_id"], "draft"),
        (owner_rejected, owner["label_id"], "rejected"),
        (owner_live, owner["label_id"], "live"),
        (other_draft, other["label_id"], "draft"),
        (nokyc_draft, no_kyc["label_id"], "draft"),
    ]:
        _insert_release_with_tracks(db, release_id=rid, label_id=lid, status=status, title=f"Iter61 {rid}")

    owner_token = _login(owner["email"], owner["password"])
    other_token = _login(other["email"], other["password"])
    no_kyc_token = _login(no_kyc["email"], no_kyc["password"])
    super_token = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    try:
        ok_draft = requests.delete(f"{API}/releases/{owner_draft}", headers=_headers(owner_token), timeout=30)
        assert ok_draft.status_code == 200, ok_draft.text
        ok_rejected = requests.delete(f"{API}/releases/{owner_rejected}", headers=_headers(owner_token), timeout=30)
        assert ok_rejected.status_code == 200, ok_rejected.text

        forbidden_other = requests.delete(f"{API}/releases/{other_draft}", headers=_headers(owner_token), timeout=30)
        assert forbidden_other.status_code == 403
        forbidden_live = requests.delete(f"{API}/releases/{owner_live}", headers=_headers(owner_token), timeout=30)
        assert forbidden_live.status_code == 400

        owner_cannot_delete_other = requests.delete(f"{API}/releases/{owner_live}", headers=_headers(other_token), timeout=30)
        assert owner_cannot_delete_other.status_code in (403, 404)

        non_label_cannot_use_endpoint = requests.delete(f"{API}/releases/{owner_live}", headers=_headers(super_token), timeout=30)
        assert non_label_cannot_use_endpoint.status_code == 403

        missing_kyc = requests.delete(f"{API}/releases/{nokyc_draft}", headers=_headers(no_kyc_token), timeout=30)
        assert missing_kyc.status_code == 403
    finally:
        _cleanup_release_artifacts(db, [owner_draft, owner_rejected, owner_live, other_draft, nokyc_draft])
        _cleanup_label_seed(db, owner)
        _cleanup_label_seed(db, other)
        _cleanup_label_seed(db, no_kyc)


class _FakeCursor:
    def __init__(self, items: List[dict]):
        self._items = items

    async def to_list(self, _):
        return list(self._items)


class _DeleteResult:
    def __init__(self, deleted_count: int):
        self.deleted_count = deleted_count


@pytest.mark.anyio
async def test_service_deletes_only_unshared_api_assets_and_tracks(monkeypatch):
    from routes import release_deletion_service as service

    release_id = "iter61-service-asset"
    release_doc = {
        "id": release_id,
        "label_id": "label-a",
        "status": "draft",
        "release_title": "Service Asset",
        "cover_url": "/api/files/shared-cover.jpg",
    }
    tracks = [
        {"id": "t1", "audio_url": "/api/files/unique.wav"},
        {"id": "t2", "audio_url": "/api/files/shared-audio.wav"},
        {"id": "t3", "audio_url": "https://cdn.example.com/file.mp3"},
    ]

    async def fake_release_find_one(query: dict, *_args, **_kwargs):
        if query.get("id") == release_id:
            return release_doc
        if query.get("cover_url") == "/api/files/shared-cover.jpg":
            return {"id": "other-release"}
        return None

    async def fake_track_find_one(query: dict, *_args, **_kwargs):
        if query.get("audio_url") == "/api/files/shared-audio.wav":
            return {"id": "other-track"}
        return None

    fake_db = type("FakeDB", (), {})()
    fake_db.releases = type("Releases", (), {
        "find_one": AsyncMock(side_effect=fake_release_find_one),
        "delete_one": AsyncMock(return_value=_DeleteResult(1)),
    })()
    fake_db.tracks = type("Tracks", (), {
        "find": lambda *_args, **_kwargs: _FakeCursor(tracks),
        "find_one": AsyncMock(side_effect=fake_track_find_one),
        "delete_many": AsyncMock(),
    })()

    deleted_keys: List[str] = []
    delete_object_mock = AsyncMock(side_effect=lambda key: deleted_keys.append(key))
    log_activity_mock = AsyncMock()

    monkeypatch.setattr(service, "db", fake_db)
    monkeypatch.setattr(service.storage_service, "delete_object", delete_object_mock)
    monkeypatch.setattr(service, "log_activity", log_activity_mock)

    result = await service.delete_release_record(release_id, actor_id="admin-1")
    assert result.ok is True
    assert result.deleted == release_id
    assert deleted_keys == ["unique.wav"]
    fake_db.tracks.delete_many.assert_awaited_once_with({"release_id": release_id})
    log_activity_mock.assert_awaited_once()


@pytest.mark.anyio
async def test_service_returns_409_before_track_and_storage_delete_on_status_race(monkeypatch):
    from routes import release_deletion_service as service

    release_id = "iter61-service-race"
    release_doc = {
        "id": release_id,
        "label_id": "label-a",
        "status": "draft",
        "release_title": "Service Race",
        "cover_url": "/api/files/race-cover.jpg",
    }

    fake_db = type("FakeDB", (), {})()
    fake_db.releases = type("Releases", (), {
        "find_one": AsyncMock(return_value=release_doc),
        "delete_one": AsyncMock(return_value=_DeleteResult(0)),
    })()
    fake_db.tracks = type("Tracks", (), {
        "find": lambda *_args, **_kwargs: _FakeCursor([{"id": "t1", "audio_url": "/api/files/race.wav"}]),
        "find_one": AsyncMock(return_value=None),
        "delete_many": AsyncMock(),
    })()

    delete_object_mock = AsyncMock()
    log_activity_mock = AsyncMock()

    monkeypatch.setattr(service, "db", fake_db)
    monkeypatch.setattr(service.storage_service, "delete_object", delete_object_mock)
    monkeypatch.setattr(service, "log_activity", log_activity_mock)

    with pytest.raises(HTTPException) as exc:
        await service.delete_release_record(release_id, actor_id="admin-1")
    assert exc.value.status_code == 409
    fake_db.tracks.delete_many.assert_not_awaited()
    delete_object_mock.assert_not_awaited()
    log_activity_mock.assert_not_awaited()