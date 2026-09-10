"""Iter70 targeted backend regression for release URL, credits, quota, internal cover, and takedown."""

import io
import asyncio
from pathlib import Path
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

import pymongo
import requests
from dotenv import load_dotenv
from PIL import Image

from auth_utils import hash_password
from tests.support_config import FINANCE, SUPERADMIN, SUPPORT, temporary_password


load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/frontend/.env", override=True)
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _login(email: str, password: str) -> str:
    response = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=40)
    assert response.status_code == 200, response.text
    token = response.json().get("access_token")
    assert token
    return token


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _seed_label(db, suffix: str, name_prefix: str = "Iter70") -> dict:
    now = datetime.now(timezone.utc).isoformat()
    user_id = f"iter70-user-{suffix}"
    label_id = f"iter70-label-{suffix}"
    email = f"iter70-{suffix}@example.com"
    password = temporary_password("Iter70")
    kyc_id = f"iter70-kyc-{suffix}"
    db.users.insert_one({
        "id": user_id,
        "name": f"{name_prefix} Label {suffix}",
        "email": email,
        "password_hash": hash_password(password),
        "role": "label",
        "status": "active",
        "token_version": 0,
        "email_verified_at": now,
        "created_at": now,
        "updated_at": now,
    })
    db.labels.insert_one({
        "id": label_id,
        "user_id": user_id,
        "label_name": f"{name_prefix} Label {suffix}",
        "pic_name": "PIC Iter70",
        "whatsapp": "081234567890",
        "address": "Jl. Iter70",
        "city": "Jakarta",
        "country": "Indonesia",
        "logo_storage_key": f"label-logo/{label_id}.png",
        "account_status": "active",
        "payment_type": "pay_per_release",
        "subscription_status": "none",
        "kyc_status": "verified",
        "kyc_document_id": kyc_id,
        "created_at": now,
        "updated_at": now,
    })
    db.kyc_documents.insert_one({
        "id": kyc_id,
        "label_id": label_id,
        "storage_key": f"kyc-private/{label_id}/ktp.png",
        "status": "verified",
        "is_current": True,
        "uploaded_at": now,
        "reviewed_at": now,
    })
    db.bank_accounts.insert_one({
        "id": f"iter70-bank-{suffix}",
        "label_id": label_id,
        "bank_name": "BCA",
        "account_number": "1234567890",
        "account_holder_name": "PIC Iter70",
        "verified_status": "verified",
        "created_at": now,
        "updated_at": now,
    })
    db.contracts.insert_one({
        "id": f"iter70-contract-{suffix}",
        "label_id": label_id,
        "status": "active",
        "start_date": "2026-01-01",
        "end_date": "2030-12-31",
        "created_at": now,
    })
    credentials = Path("/app/memory/test_credentials.md")
    with credentials.open("a") as handle:
        handle.write(f"\n- Iter70 isolated fixture `{email}` / `{password}` — ACTIVE QA\n")
    return {"user_id": user_id, "label_id": label_id, "email": email, "password": password, "suffix": suffix}


def _cleanup_seed(db, seeded: dict, release_ids: list[str], artist_ids: list[str] | None = None, ticket_ids: list[str] | None = None):
    release_ids = list(dict.fromkeys([rid for rid in release_ids if rid]))
    ticket_ids = list(dict.fromkeys(ticket_ids or []))
    artist_ids = list(dict.fromkeys(artist_ids or []))
    if ticket_ids:
        db.support_comments.delete_many({"ticket_id": {"$in": ticket_ids}})
        db.support_tickets.delete_many({"id": {"$in": ticket_ids}})
        db.notifications.delete_many({"meta.ticket_id": {"$in": ticket_ids}})
        db.activity_logs.delete_many({"reference_id": {"$in": ticket_ids}})
    if release_ids:
        import storage_service
        internal_covers = list(db.release_internal_covers.find({"release_id": {"$in": release_ids}, "label_id": seeded["label_id"]}, {"_id": 0, "key": 1}))
        async def remove_owned_covers():
            for cover in internal_covers:
                assert cover["key"].startswith(f"release-internal/{seeded['label_id']}/")
                await storage_service.delete_object(key=cover["key"])
        asyncio.run(remove_owned_covers())
        db.notifications.delete_many({"meta.release_id": {"$in": release_ids}})
        db.activity_logs.delete_many({"reference_id": {"$in": release_ids}})
        db.payments.delete_many({"release_id": {"$in": release_ids}})
        db.tracks.delete_many({"release_id": {"$in": release_ids}})
        db.release_internal_covers.delete_many({"release_id": {"$in": release_ids}})
        db.release_internal_covers.delete_many({"_id": {"$in": release_ids}})
        db.releases.delete_many({"id": {"$in": release_ids}})
        db.release_operation_locks.delete_many({"_id": {"$in": [f"submit:{rid}" for rid in release_ids] + [f"internal-cover:{rid}" for rid in release_ids] + [f"support-takedown:{rid}" for rid in release_ids]}})
    db.label_daily_submissions.delete_many({"label_id": seeded["label_id"]})
    db.labels.delete_one({"id": seeded["label_id"]})
    db.users.delete_one({"id": seeded["user_id"]})
    db.auth_sessions.delete_many({"user_id": seeded["user_id"]})
    db.kyc_documents.delete_many({"label_id": seeded["label_id"]})
    db.bank_accounts.delete_many({"label_id": seeded["label_id"]})
    db.contracts.delete_many({"label_id": seeded["label_id"]})
    if artist_ids:
        db.artists.delete_many({"id": {"$in": artist_ids}})
    db.artists.delete_many({"label_id": seeded["label_id"], "source": "release_submission"})
    credentials = Path("/app/memory/test_credentials.md")
    lines = credentials.read_text().splitlines()
    credentials.write_text("\n".join(line.replace("ACTIVE QA", "REMOVED (fixture teardown)") if seeded["email"] in line else line for line in lines) + "\n")


def _release_payload(title: str, release_type: str = "single", artist_web_url=None, track_featured: bool = True):
    track_count = 1 if release_type == "single" else 2
    tracks = []
    for index in range(track_count):
        featured = []
        if track_featured:
            featured = [{
                "name": f"Track Feat {index + 1}",
                "artist_id": None,
                "spotify_url": "https://open.spotify.com/artist/1Xyo4u8uXC1ZmMpatF05PJ",
                "social_links": [{"platform": "spotify", "url": "https://open.spotify.com/artist/1Xyo4u8uXC1ZmMpatF05PJ"}],
            }]
        tracks.append({
            "track_title": f"Track {index + 1}",
            "artist_name": "Iter70 Main",
            "composer": "Composer",
            "lyricist": "Lyricist",
            "producer": "Producer",
            "arranger": "Arranger",
            "performer": "Performer",
            "genre": "Pop",
            "language": "Indonesian",
            "explicit": False,
            "track_number": index + 1,
            "preview_start_seconds": 10,
            "title_language": "Indonesian",
            "lyric_language": "Indonesian",
            "track_type": "original",
            "lyrics": "Lirik lengkap iter70",
            "vocal_type": "vocal",
            "featured_artists": featured,
        })
    return {
        "release_title": title,
        "artist_name": "Iter70 Main",
        "release_type": release_type,
        "release_date": (date.today() + timedelta(days=10)).isoformat(),
        "genre": "Pop",
        "subgenre": "Pop",
        "language": "Indonesian",
        "explicit": False,
        "copyright_line": "© 2026 Iter70",
        "p_line": "℗ 2026 Iter70",
        "year": date.today().year,
        "artist_web_url": artist_web_url,
        "primary_artists": [{
            "name": "Iter70 Main",
            "spotify_url": "https://open.spotify.com/artist/0du5cEVh5yTK9QJze8zA0C",
            "social_links": [{"platform": "spotify", "url": "https://open.spotify.com/artist/0du5cEVh5yTK9QJze8zA0C"}],
        }],
        "featured_artists": [{
            "name": "Release Feat",
            "spotify_url": "https://open.spotify.com/artist/66CXWjxzNUsdJxJ2JdwvnR",
            "social_links": [{"platform": "spotify", "url": "https://open.spotify.com/artist/66CXWjxzNUsdJxJ2JdwvnR"}],
        }],
        "platforms": ["Spotify"],
        "notes": "iter70",
        "tracks": tracks,
    }


def _mark_release_ready(db, release_id: str):
    db.releases.update_one({"id": release_id}, {"$set": {"cover_url": f"/api/files/{release_id}.jpg", "cover_width": 3000, "cover_height": 3000}})
    db.tracks.update_many({"release_id": release_id}, {"$set": {"audio_url": f"/api/files/{release_id}.wav", "audio_filename": f"{release_id}.wav", "audio_sample_rate": 44100}})


def _create_ready_release(db, label_token: str, title: str, release_type: str = "single") -> str:
    response = requests.post(f"{API}/releases/draft", json=_release_payload(title, release_type=release_type), headers=_headers(label_token), timeout=40)
    assert response.status_code == 200, response.text
    rid = response.json()["id"]
    _mark_release_ready(db, rid)
    return rid


def _jpg_bytes(width=600, height=600):
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color=(120, 30, 190)).save(buffer, format="JPEG")
    return buffer.getvalue()


# Feature: optional artist_web_url and URL validation behavior.
def test_optional_artist_web_url_accepts_blank_or_null_and_rejects_malformed():
    db = _db()
    seeded = _seed_label(db, uuid.uuid4().hex[:8])
    token = _login(seeded["email"], seeded["password"])
    created_ids = []
    try:
        for idx, value in enumerate(["", None]):
            payload = _release_payload(f"Iter70 Optional URL {idx}", artist_web_url=value, track_featured=True)
            created = requests.post(f"{API}/releases/draft", json=payload, headers=_headers(token), timeout=40)
            assert created.status_code == 200, created.text
            created_ids.append(created.json()["id"])

        omitted_payload = _release_payload("Iter70 Optional URL omitted")
        omitted_payload.pop("artist_web_url", None)
        omitted = requests.post(f"{API}/releases/draft", json=omitted_payload, headers=_headers(token), timeout=40)
        assert omitted.status_code == 200, omitted.text
        created_ids.append(omitted.json()["id"])

        malformed = _release_payload("Iter70 malformed", artist_web_url="htp:/broken-url")
        malformed_response = requests.post(f"{API}/releases/draft", json=malformed, headers=_headers(token), timeout=40)
        assert malformed_response.status_code == 400

        youtube_bad = _release_payload("Iter70 youtube bad", artist_web_url="https://youtube.com/@notchannel")
        youtube_bad_response = requests.post(f"{API}/releases/draft", json=youtube_bad, headers=_headers(token), timeout=40)
        assert youtube_bad_response.status_code == 400

        youtube_good = _release_payload("Iter70 youtube good", artist_web_url="https://youtube.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw")
        youtube_good_response = requests.post(f"{API}/releases/draft", json=youtube_good, headers=_headers(token), timeout=40)
        assert youtube_good_response.status_code == 200, youtube_good_response.text
        created_ids.append(youtube_good_response.json()["id"])
    finally:
        _cleanup_seed(db, seeded, created_ids)


# Feature: track-level featured artists save/read/edit behavior.
def test_track_featured_artists_save_read_edit_and_clear_without_resurrection():
    db = _db()
    seeded = _seed_label(db, uuid.uuid4().hex[:8])
    token = _login(seeded["email"], seeded["password"])
    created_ids = []
    try:
        created = requests.post(f"{API}/releases/draft", json=_release_payload("Iter70 Track Credits EP", release_type="ep", track_featured=True), headers=_headers(token), timeout=40)
        assert created.status_code == 200, created.text
        release_id = created.json()["id"]
        created_ids.append(release_id)

        detail = requests.get(f"{API}/releases/{release_id}", headers=_headers(token), timeout=40)
        assert detail.status_code == 200
        tracks = detail.json()["tracks"]
        assert len(tracks) == 2
        assert all(len(track.get("featured_artists") or []) == 1 for track in tracks)

        edited_payload = _release_payload("Iter70 Track Credits EP edited", release_type="ep", track_featured=True)
        edited_payload["tracks"][0]["id"] = tracks[0]["id"]
        edited_payload["tracks"][1]["id"] = tracks[1]["id"]
        edited_payload["tracks"][0]["featured_artists"] = []
        updated = requests.patch(f"{API}/releases/{release_id}", json=edited_payload, headers=_headers(token), timeout=40)
        assert updated.status_code == 200, updated.text

        refreshed = requests.get(f"{API}/releases/{release_id}", headers=_headers(token), timeout=40)
        assert refreshed.status_code == 200
        refreshed_tracks = refreshed.json()["tracks"]
        assert refreshed_tracks[0].get("featured_artists") == []
        assert refreshed_tracks[0].get("featuring_artist_name") in (None, "")
        assert len(refreshed_tracks[1].get("featured_artists") or []) == 1
    finally:
        _cleanup_seed(db, seeded, created_ids)


# Feature: reject cross-label artist_id usage in submission credits resolution.
def test_submit_rejects_cross_label_artist_id_in_track_featured_artist():
    db = _db()
    owner = _seed_label(db, uuid.uuid4().hex[:8], name_prefix="Iter70 Owner")
    outsider = _seed_label(db, uuid.uuid4().hex[:8], name_prefix="Iter70 Outsider")
    owner_token = _login(owner["email"], owner["password"])
    created_ids = []
    outsider_artist_id = f"iter70-outsider-artist-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    db.artists.insert_one({
        "id": outsider_artist_id,
        "label_id": outsider["label_id"],
        "artist_name": "Outsider Artist",
        "social_links": [{"platform": "spotify", "url": "https://open.spotify.com/artist/3TVXtAsR1Inumwj472S9r4"}],
        "status": "active",
        "created_at": now,
        "updated_at": now,
    })
    try:
        payload = _release_payload("Iter70 Cross Label", release_type="single", track_featured=True)
        payload["tracks"][0]["featured_artists"] = [{
            "artist_id": outsider_artist_id,
            "name": "Outsider Artist",
            "spotify_url": None,
            "social_links": [{"platform": "spotify", "url": "https://open.spotify.com/artist/3TVXtAsR1Inumwj472S9r4"}],
        }]
        created = requests.post(f"{API}/releases/draft", json=payload, headers=_headers(owner_token), timeout=40)
        assert created.status_code == 200, created.text
        release_id = created.json()["id"]
        created_ids.append(release_id)
        _mark_release_ready(db, release_id)

        submit = requests.post(f"{API}/releases/{release_id}/submit", json={"contract_declaration_checked": True, "addon_product_ids": []}, headers=_headers(owner_token), timeout=40)
        assert submit.status_code == 400
        assert "Artis tersimpan" in str(submit.text)
    finally:
        _cleanup_seed(db, owner, created_ids, artist_ids=[outsider_artist_id])
        _cleanup_seed(db, outsider, [])


# Feature: daily quota atomicity for seven successful distinct submissions.
def test_daily_quota_allows_only_seven_distinct_submissions_and_returns_429_for_eighth():
    db = _db()
    seeded = _seed_label(db, uuid.uuid4().hex[:8])
    token = _login(seeded["email"], seeded["password"])
    release_ids = []
    try:
        for i in range(8):
            release_ids.append(_create_ready_release(db, token, f"Iter70 Quota {i+1}"))

        def _submit(rid: str):
            return requests.post(
                f"{API}/releases/{rid}/submit",
                json={"contract_declaration_checked": True, "addon_product_ids": []},
                headers=_headers(token),
                timeout=60,
            )

        with ThreadPoolExecutor(max_workers=8) as pool:
            responses = list(pool.map(_submit, release_ids))

        success = [r for r in responses if r.status_code == 200]
        rejected = [r for r in responses if r.status_code == 429]
        assert len(success) == 7, [r.status_code for r in responses]
        assert len(rejected) == 1, [r.status_code for r in responses]
        assert "Retry-After" in rejected[0].headers

        quota = requests.get(f"{API}/releases/submission-quota", headers=_headers(token), timeout=40)
        assert quota.status_code == 200
        data = quota.json()
        assert data["limit"] == 7
        assert data["used"] == 7
        assert data["remaining"] == 0
    finally:
        _cleanup_seed(db, seeded, release_ids)


# Feature: duplicate concurrent submit on same release should only commit one success.
def test_duplicate_concurrent_same_release_only_one_success_and_one_history_entry():
    db = _db()
    seeded = _seed_label(db, uuid.uuid4().hex[:8])
    token = _login(seeded["email"], seeded["password"])
    release_ids = []
    try:
        release_id = _create_ready_release(db, token, "Iter70 duplicate same release")
        release_ids.append(release_id)

        def _submit_same():
            return requests.post(
                f"{API}/releases/{release_id}/submit",
                json={"contract_declaration_checked": True, "addon_product_ids": []},
                headers=_headers(token),
                timeout=60,
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: _submit_same(), [0, 1]))

        success = [r for r in responses if r.status_code == 200]
        conflicts = [r for r in responses if r.status_code in (409, 400)]
        assert len(success) == 1, [r.status_code for r in responses]
        assert len(conflicts) == 1, [r.status_code for r in responses]

        release = db.releases.find_one({"id": release_id}, {"_id": 0})
        submitted_events = [h for h in release.get("status_history") or [] if h.get("to") == "submitted"]
        assert len(submitted_events) == 1

        ledger = db.label_daily_submissions.find_one({"label_id": seeded["label_id"], "entries.release_id": release_id}, {"_id": 0})
        assert ledger
        entries = [entry for entry in ledger.get("entries", []) if entry.get("release_id") == release_id]
        assert len(entries) == 1
    finally:
        _cleanup_seed(db, seeded, release_ids)


# Feature: same-day rejected resubmit should stay allowed without consuming new slot.
def test_same_day_rejected_resubmit_when_quota_full_keeps_same_quota_slot():
    db = _db()
    seeded = _seed_label(db, uuid.uuid4().hex[:8])
    token = _login(seeded["email"], seeded["password"])
    admin_token = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    release_ids = []
    try:
        target_release = _create_ready_release(db, token, "Iter70 Rejected Resubmit")
        release_ids.append(target_release)
        submit = requests.post(f"{API}/releases/{target_release}/submit", json={"contract_declaration_checked": True, "addon_product_ids": []}, headers=_headers(token), timeout=60)
        assert submit.status_code == 200, submit.text

        reject = requests.post(f"{API}/releases/{target_release}/admin/action", json={"action": "reject", "note": "iter70 reject"}, headers=_headers(admin_token), timeout=40)
        assert reject.status_code == 200, reject.text
        assert reject.json()["status"] == "rejected"

        for i in range(6):
            rid = _create_ready_release(db, token, f"Iter70 Fill Quota {i+1}")
            release_ids.append(rid)
            filled = requests.post(f"{API}/releases/{rid}/submit", json={"contract_declaration_checked": True, "addon_product_ids": []}, headers=_headers(token), timeout=60)
            assert filled.status_code == 200, filled.text

        quota_full = requests.get(f"{API}/releases/submission-quota", headers=_headers(token), timeout=40)
        assert quota_full.status_code == 200 and quota_full.json()["remaining"] == 0

        detail = requests.get(f"{API}/releases/{target_release}", headers=_headers(token), timeout=40)
        assert detail.status_code == 200
        patch_payload = _release_payload("Iter70 Rejected Resubmit edited", release_type="single")
        patch_payload["tracks"][0]["id"] = detail.json()["tracks"][0]["id"]
        patched = requests.patch(f"{API}/releases/{target_release}", json=patch_payload, headers=_headers(token), timeout=40)
        assert patched.status_code == 200, patched.text
        _mark_release_ready(db, target_release)

        resubmit = requests.post(f"{API}/releases/{target_release}/submit", json={"contract_declaration_checked": True, "addon_product_ids": []}, headers=_headers(token), timeout=60)
        assert resubmit.status_code == 200, resubmit.text

        quota_with_release = requests.get(f"{API}/releases/submission-quota", params={"release_id": target_release}, headers=_headers(token), timeout=40)
        assert quota_with_release.status_code == 200
        quota_data = quota_with_release.json()
        assert quota_data["used"] == 7
        assert quota_data["already_counted"] is True
    finally:
        _cleanup_seed(db, seeded, release_ids)


# Feature: internal cover upload/read permissions and canonical cover immutability.
def test_internal_cover_owner_upload_and_permission_guards():
    db = _db()
    owner = _seed_label(db, uuid.uuid4().hex[:8], name_prefix="Iter70 OwnerCover")
    outsider = _seed_label(db, uuid.uuid4().hex[:8], name_prefix="Iter70 OutsiderCover")
    owner_token = _login(owner["email"], owner["password"])
    outsider_token = _login(outsider["email"], outsider["password"])
    release_id = f"iter70-legacy-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    db.releases.insert_one({
        "id": release_id,
        "label_id": owner["label_id"],
        "release_title": "Iter70 Legacy",
        "release_type": "single",
        "status": "live",
        "imported_legacy": True,
        "cover_url": "/api/files/canonical-legacy.jpg",
        "created_at": now,
        "updated_at": now,
    })
    try:
        upload = requests.post(
            f"{API}/releases/{release_id}/internal-cover",
            headers=_headers(owner_token),
            files={"file": ("internal.jpg", _jpg_bytes(), "image/jpeg")},
            timeout=80,
        )
        assert upload.status_code == 200, upload.text
        data = upload.json()
        assert data["release_id"] == release_id
        assert "internal-cover" in data["internal_cover_url"]

        release = db.releases.find_one({"id": release_id}, {"_id": 0})
        assert release.get("cover_url") == "/api/files/canonical-legacy.jpg"
        assert release.get("internal_cover_url")

        outsider_write = requests.post(
            f"{API}/releases/{release_id}/internal-cover",
            headers=_headers(outsider_token),
            files={"file": ("internal.jpg", _jpg_bytes(), "image/jpeg")},
            timeout=80,
        )
        assert outsider_write.status_code == 404

        finance_token = _login(FINANCE["email"], FINANCE["password"])
        finance_get = requests.get(f"{API}/releases/{release_id}/internal-cover", headers=_headers(finance_token), timeout=40)
        # Finance has releases.view: artwork is visible, while modifications require review.
        assert finance_get.status_code == 200
        finance_write = requests.post(f"{API}/releases/{release_id}/internal-cover", headers=_headers(finance_token),
            files={"file": ("forbidden.jpg", _jpg_bytes(), "image/jpeg")}, timeout=40)
        assert finance_write.status_code == 403

        anonymous_get = requests.get(f"{API}/releases/{release_id}/internal-cover", timeout=30)
        assert anonymous_get.status_code in (401, 403)

        owner_get = requests.get(f"{API}/releases/{release_id}/internal-cover", headers=_headers(owner_token), timeout=40)
        assert owner_get.status_code == 200
        cache = (owner_get.headers.get("Cache-Control") or "").lower()
        assert "no-store" in cache
    finally:
        _cleanup_seed(db, owner, [release_id])
        _cleanup_seed(db, outsider, [])


# Feature: takedown ticket completion should move linked live release to taken_down once.
def test_support_done_takedown_changes_release_status_and_finance_forbidden():
    db = _db()
    seeded = _seed_label(db, uuid.uuid4().hex[:8], name_prefix="Iter70 Takedown")
    label_token = _login(seeded["email"], seeded["password"])
    support_token = _login(SUPPORT["email"], SUPPORT["password"])
    finance_token = _login(FINANCE["email"], FINANCE["password"])
    release_id = f"iter70-live-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    db.releases.insert_one({
        "id": release_id,
        "label_id": seeded["label_id"],
        "release_title": "Iter70 Live",
        "release_type": "single",
        "status": "live",
        "cover_url": "/api/files/live.jpg",
        "tracks_count": 1,
        "created_at": now,
        "updated_at": now,
    })
    db.tracks.insert_one({
        "id": f"iter70-track-{uuid.uuid4().hex[:8]}",
        "release_id": release_id,
        "label_id": seeded["label_id"],
        "track_title": "Iter70 Track",
        "track_number": 1,
        "isrc": "IDAAA2600001",
        "created_at": now,
        "updated_at": now,
    })
    ticket_ids = []
    try:
        created = requests.post(
            f"{API}/tickets/label/create",
            json={
                "release_id": release_id,
                "category": "takedown",
                "subject": "",
                "description": "Mohon takedown karena konflik hak cipta.",
                "reason": "Konflik Hak Cipta",
                "attachments": [],
            },
            headers=_headers(label_token),
            timeout=60,
        )
        assert created.status_code == 200, created.text
        ticket_id = created.json()["id"]
        ticket_ids.append(ticket_id)

        forbidden = requests.post(
            f"{API}/tickets/admin/{ticket_id}/status",
            json={"status": "done"},
            headers=_headers(finance_token),
            timeout=40,
        )
        assert forbidden.status_code == 403

        done = requests.post(
            f"{API}/tickets/admin/{ticket_id}/status",
            json={"status": "done"},
            headers=_headers(support_token),
            timeout=40,
        )
        assert done.status_code == 200, done.text
        assert done.json().get("linked_release_status") == "taken_down"

        release = db.releases.find_one({"id": release_id}, {"_id": 0})
        assert release["status"] == "taken_down"
        history = [h for h in release.get("status_history") or [] if h.get("to") == "taken_down"]
        assert len(history) == 1

        repeat = requests.post(
            f"{API}/tickets/admin/{ticket_id}/status",
            json={"status": "done"},
            headers=_headers(support_token),
            timeout=40,
        )
        assert repeat.status_code == 200, repeat.text
        release2 = db.releases.find_one({"id": release_id}, {"_id": 0})
        history2 = [h for h in release2.get("status_history") or [] if h.get("to") == "taken_down"]
        assert len(history2) == 1
    finally:
        _cleanup_seed(db, seeded, [release_id], ticket_ids=ticket_ids)
