"""Phase 43 — expanded track metadata and post-approval combined PPR invoice."""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pymongo
import requests
from dotenv import load_dotenv

from auth_utils import hash_password
from tests.support_config import SUPERADMIN, temporary_password


load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/frontend/.env", override=True)
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _login(email, password):
    response = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _seed_ppr_label(db, suffix):
    now = "2026-09-01T00:00:00+00:00"
    user_id = f"phase43-user-{suffix}"
    label_id = f"phase43-label-{suffix}"
    email = f"phase43-{suffix}@example.com"
    password = temporary_password("PprRelease")
    db.users.insert_one({
        "id": user_id, "name": "Phase 43 Label", "email": email,
        "password_hash": hash_password(password), "role": "label", "status": "active",
        "token_version": 0, "email_verified_at": now, "created_at": now, "updated_at": now,
    })
    db.labels.insert_one({
        "id": label_id, "user_id": user_id, "label_name": "Phase 43 Label",
        "pic_name": "Phase 43 PIC", "whatsapp": "081234567890",
        "address": "Jl. Pengujian 43", "city": "Jakarta", "country": "Indonesia",
        "logo_storage_key": f"label-logo/{label_id}/verified.png",
        "kyc_document_id": f"phase43-kyc-{suffix}", "kyc_status": "verified",
        "kyc_verified_at": now,
        "account_status": "active", "payment_type": "pay_per_release",
        "subscription_status": "none", "created_at": now, "updated_at": now,
    })
    db.kyc_documents.insert_one({
        "id": f"phase43-kyc-{suffix}", "label_id": label_id,
        "storage_key": f"kyc-private/{label_id}/verified.png", "content_type": "image/png",
        "status": "verified", "is_current": True, "uploaded_at": now, "reviewed_at": now,
    })
    db.bank_accounts.insert_one({
        "id": f"phase43-bank-{suffix}", "label_id": label_id, "bank_name": "BCA",
        "account_number": "1234567890", "account_holder_name": "Phase 43 PIC",
        "verified_status": "verified", "created_at": now,
    })
    db.contracts.insert_one({
        "id": f"phase43-contract-{suffix}", "label_id": label_id, "status": "active",
        "start_date": "2026-01-01", "end_date": "2030-12-31", "created_at": now,
    })
    return {"user_id": user_id, "label_id": label_id, "email": email, "password": password}


def _cleanup(db, seeded, release_id, product_id):
    db.notifications.delete_many({"meta.release_id": release_id})
    db.activity_logs.delete_many({"reference_id": release_id})
    db.payments.delete_many({"release_id": release_id})
    db.tracks.delete_many({"release_id": release_id})
    db.releases.delete_many({"id": release_id})
    db.payment_products.delete_many({"id": product_id})
    db.kyc_documents.delete_many({"label_id": seeded["label_id"]})
    db.bank_accounts.delete_many({"label_id": seeded["label_id"]})
    db.contracts.delete_many({"label_id": seeded["label_id"]})
    db.labels.delete_one({"id": seeded["label_id"]})
    db.users.delete_one({"id": seeded["user_id"]})


def test_submit_waits_for_admin_then_creates_one_combined_invoice():
    db = _db()
    suffix = uuid.uuid4().hex[:10]
    seeded = _seed_ppr_label(db, suffix)
    product_id = f"phase43-addon-{suffix}"
    release_id = ""
    db.payment_products.insert_one({
        "id": product_id, "name": "Promosi Reels", "description": "Satu video promo",
        "amount": 12500, "active": True, "created_at": "2026-09-01T00:00:00+00:00",
        "updated_at": "2026-09-01T00:00:00+00:00",
    })
    label_token = _login(seeded["email"], seeded["password"])
    admin_token = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    release_payload = {
        "release_title": "Metadata Lengkap",
        "artist_name": "Artist Phase 43",
        "release_type": "single",
        "release_date": "2026-10-01",
        "genre": "Pop",
        "subgenre": "Indie Pop",
        "language": "Indonesian",
        "explicit": False,
        "copyright_line": "2026 Phase 43",
        "p_line": "2026 Phase 43",
        "year": 2026,
        "artist_web_url": "https://youtube.com/channel/UCphase43original",
        "primary_artists": [{"name": "Artist Phase 43", "spotify_url": "https://open.spotify.com/artist/phase43"}],
        "featured_artists": [{"name": "Featured Artist", "spotify_url": None}],
        "platforms": ["Spotify", "YouTube Music"],
        "cover_url": "/api/files/phase43-cover.jpg",
        "tracks": [{
            "track_title": "Track Lengkap", "artist_name": "Artist Phase 43",
            "composer": "Composer", "lyricist": "Lyricist", "producer": "Producer",
            "arranger": "Arranger", "audio_url": "/api/files/phase43.wav",
            "audio_filename": "phase43.wav", "track_number": 1,
            "preview_start_seconds": 37, "title_language": "Indonesian",
            "lyric_language": "Indonesian", "track_type": "original",
            "featuring_artist_name": "Featured Artist", "spotify_artist_id": "spotify-artist-43",
            "youtube_artist_id": "youtube-artist-43", "lyrics": "Lirik pengujian lengkap",
            "vocal_type": "vocal",
        }],
    }
    try:
        created = requests.post(f"{API}/releases/draft", json=release_payload, headers=_headers(label_token), timeout=30)
        assert created.status_code == 200, created.text
        release_id = created.json()["id"]
        track = db.tracks.find_one({"release_id": release_id}, {"_id": 0})
        assert track["preview_start_seconds"] == 37
        assert track["track_type"] == "original"
        assert track["arranger"] == "Arranger"
        assert track["lyrics"] == "Lirik pengujian lengkap"
        db.releases.update_one({"id": release_id}, {"$set": {"cover_url": "/api/files/phase43-cover.jpg", "cover_width": 3000, "cover_height": 3000}})
        db.tracks.update_one({"release_id": release_id}, {"$set": {"audio_url": "/api/files/phase43.wav", "audio_filename": "phase43.wav", "audio_sample_rate": 44100}})

        submitted = requests.post(
            f"{API}/releases/{release_id}/submit",
            json={"contract_declaration_checked": True, "addon_product_ids": [product_id]},
            headers=_headers(label_token), timeout=30,
        )
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["status"] == "submitted"
        assert submitted.json()["payment_status"] == "not_generated"
        assert db.payments.count_documents({"release_id": release_id}) == 0
        assert submitted.json()["selected_addons"][0]["amount"] == 12500

        review = requests.post(
            f"{API}/releases/{release_id}/admin/action", json={"action": "start_review"},
            headers=_headers(admin_token), timeout=30,
        )
        assert review.status_code == 200, review.text
        assert review.json()["status"] == "under_review"

        def send_payment():
            return requests.post(
                f"{API}/releases/{release_id}/admin/action", json={"action": "send_payment"},
                headers=_headers(admin_token), timeout=30,
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(lambda _: send_payment(), range(2)))
        assert all(response.status_code == 200 for response in responses), [response.text for response in responses]
        payments = list(db.payments.find({"release_id": release_id}, {"_id": 0}))
        assert len(payments) == 1
        payment = payments[0]
        expected_base = int(submitted.json()["ppr_base_amount"])
        assert payment["amount"] == expected_base + 12500
        assert payment["base_amount"] == expected_base
        assert payment["addon_amount"] == 12500
        assert len(payment["line_items"]) == 2
        assert not payment.get("xendit_session_id")
        approved_release = db.releases.find_one({"id": release_id}, {"_id": 0})
        assert approved_release["status"] == "awaiting_payment"
        assert approved_release["payment_status"] == "pending"
        assert approved_release["payment_id"] == payment["id"]
    finally:
        _cleanup(db, seeded, release_id, product_id)


def test_content_id_claim_requires_valid_youtube_link():
    db = _db()
    suffix = uuid.uuid4().hex[:10]
    seeded = _seed_ppr_label(db, suffix)
    release_id = f"phase43-ticket-release-{suffix}"
    product_id = f"phase43-unused-{suffix}"
    now = "2026-09-01T00:00:00+00:00"
    db.releases.insert_one({
        "id": release_id, "label_id": seeded["label_id"], "release_title": "Content ID Test",
        "artist_name": "Artist", "status": "approved", "created_at": now, "updated_at": now,
    })
    label_token = _login(seeded["email"], seeded["password"])
    payload = {
        "release_id": release_id, "category": "content_id_claim", "subject": "Ajukan Content ID",
        "description": "Mohon proses video ini", "originality_declared": True, "attachments": [],
    }
    try:
        invalid = requests.post(f"{API}/tickets/label/create", json={**payload, "youtube_url": "https://example.com/video"}, headers=_headers(label_token), timeout=30)
        assert invalid.status_code == 400
        valid = requests.post(f"{API}/tickets/label/create", json={**payload, "youtube_url": "https://youtu.be/abcdefghijk"}, headers=_headers(label_token), timeout=30)
        assert valid.status_code == 200, valid.text
        assert valid.json()["youtube_url"] == "https://youtu.be/abcdefghijk"
    finally:
        db.ticket_comments.delete_many({"ticket_id": {"$regex": "^phase43"}})
        db.tickets.delete_many({"label_id": seeded["label_id"]})
        _cleanup(db, seeded, release_id, product_id)