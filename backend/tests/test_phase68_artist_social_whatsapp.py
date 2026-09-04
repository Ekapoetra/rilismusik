"""Phase 68 — mandatory artist socials, reusable profiles, and admin contact metadata."""
import uuid

import requests

from tests.support_config import SUPERADMIN, temporary_password
from tests.test_phase43_release_approval_invoice import API, _cleanup, _db, _headers, _login, _seed_ppr_label
from tests.test_phase65_release_submission_workflow import _payload


def test_artist_account_requires_valid_social_links_and_supports_updates():
    db = _db(); suffix = uuid.uuid4().hex[:10]
    seeded = _seed_ppr_label(db, suffix)
    token = _login(seeded["email"], seeded["password"])
    email = f"phase68-artist-{suffix}@example.com"
    artist_user_id = None
    try:
        missing = requests.post(f"{API}/artists/", headers=_headers(token), json={
            "artist_name": "Artis Tanpa Sosial", "email": email,
            "password": temporary_password("Artist68"),
        }, timeout=30)
        assert missing.status_code == 422

        invalid = requests.post(f"{API}/artists/", headers=_headers(token), json={
            "artist_name": "Artis Salah Tautan", "email": email,
            "password": temporary_password("Artist68"),
            "social_links": [{"platform": "instagram", "url": "https://tiktok.com/@salah"}],
        }, timeout=30)
        assert invalid.status_code == 400
        assert db.users.count_documents({"email": email}) == 0

        created = requests.post(f"{API}/artists/", headers=_headers(token), json={
            "artist_name": "Artis Sosial Phase 68", "email": email, "whatsapp": "081268000001",
            "password": temporary_password("Artist68"),
            "social_links": [
                {"platform": "instagram", "url": "https://instagram.com/artistphase68"},
                {"platform": "tiktok", "url": "https://tiktok.com/@artistphase68"},
            ],
        }, timeout=30)
        assert created.status_code == 200, created.text
        artist = created.json(); artist_user_id = artist["user_id"]
        assert len(artist["social_links"]) == 2

        updated = requests.patch(f"{API}/artists/{artist['id']}", headers=_headers(token), json={
            "social_links": [{"platform": "youtube", "url": "https://youtube.com/@artistphase68"}],
        }, timeout=30)
        assert updated.status_code == 200, updated.text
        assert updated.json()["social_links"][0]["platform"] == "youtube"
    finally:
        _cleanup(db, seeded, "", f"phase68-unused-{suffix}")
        if artist_user_id:
            db.users.delete_one({"id": artist_user_id})


def test_submit_snapshots_saved_socials_persists_new_artist_and_exposes_whatsapp():
    db = _db(); suffix = uuid.uuid4().hex[:10]
    seeded = _seed_ppr_label(db, suffix); release_id = ""; legacy_release_id = ""
    token = _login(seeded["email"], seeded["password"])
    admin_token = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    saved_id = f"phase68-saved-{suffix}"; legacy_id = f"phase68-legacy-{suffix}"
    db.artists.insert_many([
        {
            "id": saved_id, "label_id": seeded["label_id"], "artist_name": "Artis Tersimpan Phase 68",
            "social_links": [
                {"platform": "instagram", "url": "https://instagram.com/savedphase68"},
                {"platform": "spotify", "url": "https://open.spotify.com/artist/savedphase68"},
            ], "status": "active", "created_at": "2026-09-04T00:00:00+00:00",
        },
        {
            "id": legacy_id, "label_id": seeded["label_id"], "artist_name": "Artis Legacy Tanpa Sosial",
            "status": "active", "created_at": "2026-09-04T00:00:00+00:00",
        },
    ])
    try:
        payload = _payload("Rilisan Sosial Phase 68")
        payload["primary_artists"] = [{
            "artist_id": saved_id, "name": "Nama Diubah Klien",
            "social_links": [{"platform": "facebook", "url": "https://facebook.com/palsu"}],
        }]
        payload["featured_artists"] = [{
            "name": "Artis Baru Otomatis Phase 68",
            "social_links": [
                {"platform": "instagram", "url": "https://instagram.com/newphase68"},
                {"platform": "youtube", "url": "https://youtube.com/@newphase68"},
            ],
        }]
        created = requests.post(f"{API}/releases/draft", headers=_headers(token), json=payload, timeout=30)
        assert created.status_code == 200, created.text
        release_id = created.json()["id"]
        db.releases.update_one({"id": release_id}, {"$set": {"cover_url": "/api/files/phase68.jpg", "cover_width": 3000, "cover_height": 3000}})
        db.tracks.update_many({"release_id": release_id}, {"$set": {"audio_url": "/api/files/phase68.wav", "audio_sample_rate": 48000}})
        submitted = requests.post(f"{API}/releases/{release_id}/submit", headers=_headers(token), json={"contract_declaration_checked": True, "addon_product_ids": []}, timeout=30)
        assert submitted.status_code == 200, submitted.text
        body = submitted.json()
        assert body["primary_artists"][0]["name"] == "Artis Tersimpan Phase 68"
        assert len(body["primary_artists"][0]["social_links"]) == 2
        new_credit = body["featured_artists"][0]
        assert new_credit["artist_id"] and len(new_credit["social_links"]) == 2
        assert db.artists.find_one({"id": new_credit["artist_id"], "label_id": seeded["label_id"], "profile_only": True})

        detail = requests.get(f"{API}/releases/{release_id}", headers=_headers(admin_token), timeout=30)
        assert detail.status_code == 200, detail.text
        assert detail.json()["label_whatsapp"] == "081234567890"
        assert detail.json()["featured_artists"][0]["social_links"][1]["platform"] == "youtube"

        legacy_payload = _payload("Rilisan Legacy Tanpa Sosial")
        legacy_payload["primary_artists"] = [{
            "artist_id": legacy_id, "name": "Artis Legacy Tanpa Sosial",
            "social_links": [{"platform": "instagram", "url": "https://instagram.com/manipulasi"}],
        }]
        legacy_payload["featured_artists"] = []
        legacy_created = requests.post(f"{API}/releases/draft", headers=_headers(token), json=legacy_payload, timeout=30)
        assert legacy_created.status_code == 200, legacy_created.text
        legacy_release_id = legacy_created.json()["id"]
        db.releases.update_one({"id": legacy_release_id}, {"$set": {"cover_url": "/api/files/legacy68.jpg", "cover_width": 3000, "cover_height": 3000}})
        db.tracks.update_many({"release_id": legacy_release_id}, {"$set": {"audio_url": "/api/files/legacy68.wav", "audio_sample_rate": 44100}})
        blocked = requests.post(f"{API}/releases/{legacy_release_id}/submit", headers=_headers(token), json={"contract_declaration_checked": True, "addon_product_ids": []}, timeout=30)
        assert blocked.status_code == 400
        assert "Manajemen Artis" in blocked.text
    finally:
        if legacy_release_id:
            db.tracks.delete_many({"release_id": legacy_release_id})
            db.releases.delete_one({"id": legacy_release_id})
        _cleanup(db, seeded, release_id, f"phase68-unused-{suffix}")