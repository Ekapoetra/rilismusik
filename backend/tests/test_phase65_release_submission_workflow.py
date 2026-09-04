"""Phase 65 — complete release submission and admin state machine."""
import io
import uuid
import wave
from datetime import date, timedelta

import requests
from PIL import Image

from tests.support_config import SUPERADMIN
from tests.test_phase43_release_approval_invoice import (
    API, _cleanup, _db, _headers, _login, _seed_ppr_label,
)


def _payload(title="Phase 65 Release"):
    return {
        "release_title": title, "artist_name": "Primary One, Primary Two",
        "release_type": "ep", "release_date": (date.today() + timedelta(days=10)).isoformat(),
        "genre": "Pop", "subgenre": "Indie Pop", "language": "Indonesian",
        "explicit": True, "copyright_line": "Pemilik Hak Cipta",
        "p_line": "Pemilik Master", "year": date.today().year,
        "artist_web_url": "https://youtube.com/channel/UCphase65original",
        "primary_artists": [
            {"name": "Primary One", "spotify_url": "https://open.spotify.com/artist/primaryone", "social_links": [{"platform": "spotify", "url": "https://open.spotify.com/artist/primaryone"}]},
            {"name": "Primary Two", "spotify_url": None, "social_links": [{"platform": "instagram", "url": "https://instagram.com/primarytwo"}]},
        ],
        "featured_artists": [
            {"name": "Featured One", "spotify_url": "https://open.spotify.com/artist/featuredone", "social_links": [{"platform": "spotify", "url": "https://open.spotify.com/artist/featuredone"}, {"platform": "tiktok", "url": "https://tiktok.com/@featuredone"}]},
        ],
        "platforms": ["Spotify", "Apple Music", "TikTok"], "notes": "Metadata lengkap",
        "tracks": [
            {
                "track_title": "Track Vokal", "artist_name": "Primary One", "track_number": 1,
                "isrc": None, "vocal_type": "vocal", "lyricist": "Writer Lengkap",
                "composer": "Composer Lengkap", "arranger": "Arranger Satu",
                "producer": "Producer Satu", "explicit": True, "preview_start_seconds": 24,
                "title_language": "Indonesian", "lyric_language": "Indonesian",
                "lyrics": "Baris pertama\nBaris kedua",
            },
            {
                "track_title": "Track Instrumental", "artist_name": "Primary Two", "track_number": 2,
                "isrc": None, "vocal_type": "instrumental", "lyricist": "Writer Instrumental",
                "composer": "Composer Instrumental", "arranger": "Arranger Dua",
                "producer": "Producer Dua", "explicit": False, "preview_start_seconds": 18,
                "title_language": "English", "lyric_language": "", "lyrics": "",
            },
        ],
    }


def _invalid_cover():
    output = io.BytesIO()
    Image.new("RGB", (2999, 3000), color=(20, 20, 20)).save(output, format="JPEG")
    return output.getvalue()


def _invalid_wav():
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(2); wav.setsampwidth(2); wav.setframerate(22050)
        wav.writeframes(b"\x00\x00" * 100)
    return output.getvalue()


def test_complete_ppr_revision_payment_believe_live_takedown_flow():
    db = _db(); suffix = uuid.uuid4().hex[:10]
    seeded = _seed_ppr_label(db, suffix); release_id = ""; product_id = f"phase65-unused-{suffix}"
    label_token = _login(seeded["email"], seeded["password"])
    admin_token = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    try:
        invalid_spotify = _payload("Invalid Spotify")
        invalid_spotify["primary_artists"][0]["spotify_url"] = "https://spotify.com/not-an-artist"
        invalid = requests.post(f"{API}/releases/draft", json=invalid_spotify, headers=_headers(label_token), timeout=30)
        assert invalid.status_code == 400

        created = requests.post(f"{API}/releases/draft", json=_payload(), headers=_headers(label_token), timeout=30)
        assert created.status_code == 200, created.text
        release_id = created.json()["id"]
        tracks = list(db.tracks.find({"release_id": release_id}).sort("track_number", 1))

        bad_cover = requests.post(
            f"{API}/releases/{release_id}/upload-cover", headers=_headers(label_token),
            files={"file": ("cover.jpg", _invalid_cover(), "image/jpeg")}, timeout=60,
        )
        assert bad_cover.status_code == 400
        bad_audio = requests.post(
            f"{API}/releases/{release_id}/upload-audio", headers=_headers(label_token),
            data={"track_id": tracks[0]["id"]},
            files={"file": ("track.wav", _invalid_wav(), "audio/wav")}, timeout=60,
        )
        assert bad_audio.status_code == 400

        db.releases.update_one({"id": release_id}, {"$set": {
            "cover_url": "/api/files/phase65-cover.jpg", "cover_width": 3000,
            "cover_height": 3000, "cover_content_type": "image/jpeg",
        }})
        db.tracks.update_many({"release_id": release_id}, {"$set": {
            "audio_url": "/api/files/phase65.wav", "audio_filename": "phase65.wav",
            "audio_sample_rate": 48000,
        }})
        submitted = requests.post(
            f"{API}/releases/{release_id}/submit",
            json={"contract_declaration_checked": True, "addon_product_ids": []},
            headers=_headers(label_token), timeout=30,
        )
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["status"] == "submitted"

        review = requests.post(f"{API}/releases/{release_id}/admin/action", json={"action": "start_review"}, headers=_headers(admin_token), timeout=30)
        assert review.status_code == 200 and review.json()["status"] == "under_review"
        revision = requests.post(f"{API}/releases/{release_id}/admin/action", json={"action": "need_revision", "note": "Perbaiki kapitalisasi judul"}, headers=_headers(admin_token), timeout=30)
        assert revision.status_code == 200 and revision.json()["status"] == "need_revision"

        detail = requests.get(f"{API}/releases/{release_id}", headers=_headers(label_token), timeout=30).json()
        edited_payload = _payload("Phase 65 Release Revised")
        for index, track in enumerate(edited_payload["tracks"]):
            track["id"] = detail["tracks"][index]["id"]
            track["audio_url"] = detail["tracks"][index]["audio_url"]
        edited = requests.patch(f"{API}/releases/{release_id}", json=edited_payload, headers=_headers(label_token), timeout=30)
        assert edited.status_code == 200, edited.text
        preserved = list(db.tracks.find({"release_id": release_id}).sort("track_number", 1))
        assert all(track["audio_url"] == "/api/files/phase65.wav" and track["audio_sample_rate"] == 48000 for track in preserved)
        resubmitted = requests.post(f"{API}/releases/{release_id}/submit", json={"contract_declaration_checked": True, "addon_product_ids": []}, headers=_headers(label_token), timeout=30)
        assert resubmitted.status_code == 200 and resubmitted.json()["status"] == "submitted"
        requests.post(f"{API}/releases/{release_id}/admin/action", json={"action": "start_review"}, headers=_headers(admin_token), timeout=30).raise_for_status()

        premature = requests.post(f"{API}/releases/{release_id}/admin/action", json={"action": "approve"}, headers=_headers(admin_token), timeout=30)
        assert premature.status_code == 409
        invoiced = requests.post(f"{API}/releases/{release_id}/admin/action", json={"action": "send_payment"}, headers=_headers(admin_token), timeout=30)
        assert invoiced.status_code == 200 and invoiced.json()["status"] == "awaiting_payment"
        payment_id = invoiced.json()["payment_id"]
        assert db.payments.find_one({"id": payment_id, "status": "pending"})

        db.payments.update_one({"id": payment_id}, {"$set": {"status": "paid", "paid_at": "2026-09-03T12:00:00+00:00"}})
        db.releases.update_one({"id": release_id}, {"$set": {"status": "paid", "payment_status": "paid"}})
        approved = requests.post(f"{API}/releases/{release_id}/admin/action", json={"action": "approve"}, headers=_headers(admin_token), timeout=30)
        assert approved.status_code == 200 and approved.json()["status"] == "approved"
        delivered = requests.post(f"{API}/releases/{release_id}/admin/action", json={"action": "deliver"}, headers=_headers(admin_token), timeout=30)
        assert delivered.status_code == 200 and delivered.json()["status"] == "delivered"
        track_ids = [track["id"] for track in preserved]
        missing_isrc = requests.post(f"{API}/releases/{release_id}/admin/action", json={"action": "mark_live", "upc": "899000000001", "track_isrcs": {track_ids[0]: "IDABC2600001"}}, headers=_headers(admin_token), timeout=30)
        assert missing_isrc.status_code == 400
        assert db.tracks.find_one({"id": track_ids[0]}).get("isrc") in (None, "")
        live = requests.post(f"{API}/releases/{release_id}/admin/action", json={"action": "mark_live", "upc": "899000000001", "track_isrcs": {track_ids[0]: "IDABC2600001", track_ids[1]: "IDABC2600002"}}, headers=_headers(admin_token), timeout=30)
        assert live.status_code == 200 and live.json()["status"] == "live"
        no_reason = requests.post(f"{API}/releases/{release_id}/admin/action", json={"action": "takedown"}, headers=_headers(admin_token), timeout=30)
        assert no_reason.status_code == 400
        takedown = requests.post(f"{API}/releases/{release_id}/admin/action", json={"action": "takedown", "note": "Permintaan resmi pemilik hak"}, headers=_headers(admin_token), timeout=30)
        assert takedown.status_code == 200 and takedown.json()["status"] == "taken_down"
        history = db.releases.find_one({"id": release_id})["status_history"]
        assert [item["to"] for item in history][-7:] == ["submitted", "under_review", "awaiting_payment", "approved", "delivered", "live", "taken_down"]
    finally:
        _cleanup(db, seeded, release_id, product_id)


def test_annual_release_bypasses_payment_after_review():
    db = _db(); suffix = uuid.uuid4().hex[:10]
    release_id = f"phase65-annual-{suffix}"
    db.releases.insert_one({
        "id": release_id, "label_id": f"phase65-label-{suffix}", "release_title": "Annual Flow",
        "status": "submitted", "billing_flow": "subscription", "payment_status": "free_subscription",
        "created_at": "2026-09-03T00:00:00+00:00",
    })
    admin_token = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    try:
        review = requests.post(f"{API}/releases/{release_id}/admin/action", json={"action": "start_review"}, headers=_headers(admin_token), timeout=30)
        assert review.status_code == 200 and review.json()["status"] == "under_review"
        approve = requests.post(f"{API}/releases/{release_id}/admin/action", json={"action": "approve"}, headers=_headers(admin_token), timeout=30)
        assert approve.status_code == 200 and approve.json()["status"] == "approved"
        assert db.payments.count_documents({"release_id": release_id}) == 0
    finally:
        db.notifications.delete_many({"meta.release_id": release_id})
        db.activity_logs.delete_many({"reference_id": release_id})
        db.releases.delete_one({"id": release_id})