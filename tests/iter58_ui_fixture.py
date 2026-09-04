"""Temporary fixture for iteration 58 UI checks (seed/cleanup)."""
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

import requests

sys.path.insert(0, "/app/backend")
from tests.test_phase43_release_approval_invoice import _cleanup, _db, _seed_ppr_label


STATE_PATH = "/app/tests/iter58_ui_fixture_state.json"
API_BASE = "https://lanjut-core.preview.emergentagent.com/api"
PRODUCT_ID_PREFIX = "iter58-unused"


def _login(email: str, password: str) -> str:
    response = requests.post(f"{API_BASE}/auth/login", json={"email": email, "password": password}, timeout=30)
    response.raise_for_status()
    token = response.json().get("access_token")
    if not token:
        raise RuntimeError("No access_token from login")
    return token


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _payload(title: str) -> dict:
    release_date = (datetime.now(timezone.utc).date() + timedelta(days=8)).isoformat()
    return {
        "release_title": title,
        "release_type": "single",
        "artist_name": "Iter58 Placeholder",
        "release_date": release_date,
        "year": 2026,
        "genre": "Pop",
        "subgenre": "Pop",
        "language": "Indonesian",
        "explicit": False,
        "copyright_line": "℗ 2026 Iter58",
        "p_line": "© 2026 Iter58",
        "platforms": ["Spotify"],
        "notes": "Fixture iter58",
        "artist_web_url": "https://youtube.com/channel/UC0aA0aA0aA0aA0aA0aA0aA0",
        "primary_artists": [],
        "featured_artists": [],
        "tracks": [
            {
                "track_title": "Iter58 Track",
                "artist_name": "Iter58 Artist",
                "composer": "Komposer Iter58",
                "lyricist": "Penulis Iter58",
                "producer": "Produser Iter58",
                "arranger": "Arranger Iter58",
                "performer": "Performer Iter58",
                "genre": "Pop",
                "language": "Indonesian",
                "explicit": False,
                "track_number": 1,
                "preview_start_seconds": 0,
                "title_language": "Indonesian",
                "lyric_language": "Indonesian",
                "track_type": "original",
                "lyrics": "Lirik uji iter58",
                "vocal_type": "vocal",
            }
        ],
    }


def seed() -> None:
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    seeded = _seed_ppr_label(db, suffix)
    label_id = seeded["label_id"]

    saved_artist_id = f"iter58-saved-{suffix}"
    legacy_artist_id = f"iter58-legacy-{suffix}"
    created_artist_user_ids = []
    release_id = None

    now_iso = datetime.now(timezone.utc).isoformat()
    db.artists.insert_many([
        {
            "id": saved_artist_id,
            "label_id": label_id,
            "user_id": None,
            "artist_name": f"Iter58 Artis Tersimpan {suffix}",
            "email": None,
            "whatsapp": None,
            "social_links": [
                {"platform": "instagram", "url": f"https://instagram.com/iter58_{suffix}"},
                {"platform": "spotify", "url": f"https://open.spotify.com/artist/iter58{suffix}"},
            ],
            "profile_only": True,
            "source": "iteration58_ui",
            "visibility_settings": {},
            "status": "active",
            "created_at": now_iso,
            "updated_at": now_iso,
        },
        {
            "id": legacy_artist_id,
            "label_id": label_id,
            "user_id": None,
            "artist_name": f"Iter58 Artis Legacy {suffix}",
            "email": None,
            "whatsapp": None,
            "social_links": [],
            "profile_only": True,
            "source": "iteration58_ui",
            "visibility_settings": {},
            "status": "active",
            "created_at": now_iso,
            "updated_at": now_iso,
        },
    ])

    token = _login(seeded["email"], seeded["password"])
    payload = _payload(f"Iter58 Rilisan {suffix}")
    payload["primary_artists"] = [
        {
            "artist_id": saved_artist_id,
            "name": f"Manipulasi Nama {suffix}",
            "social_links": [{"platform": "facebook", "url": "https://facebook.com/invalidsnapshot"}],
        }
    ]
    payload["featured_artists"] = [
        {
            "name": f"Iter58 Feat Baru {suffix}",
            "social_links": [
                {"platform": "instagram", "url": f"https://instagram.com/iter58feat_{suffix}"},
                {"platform": "youtube", "url": f"https://youtube.com/@iter58feat{suffix}"},
            ],
        }
    ]
    created = requests.post(f"{API_BASE}/releases/draft", headers=_headers(token), json=payload, timeout=30)
    created.raise_for_status()
    release_id = created.json()["id"]

    db.releases.update_one(
        {"id": release_id},
        {"$set": {"cover_url": "/api/files/iter58-cover.jpg", "cover_width": 3000, "cover_height": 3000}},
    )
    db.tracks.update_many(
        {"release_id": release_id},
        {"$set": {"audio_url": "/api/files/iter58-audio.wav", "audio_sample_rate": 44100}},
    )
    submitted = requests.post(
        f"{API_BASE}/releases/{release_id}/submit",
        headers=_headers(token),
        json={"contract_declaration_checked": True, "addon_product_ids": []},
        timeout=30,
    )
    submitted.raise_for_status()

    # create label-artist account through API for management page coverage
    artist_email = f"iter58-artist-{suffix}@example.com"
    artist_create = requests.post(
        f"{API_BASE}/artists/",
        headers=_headers(token),
        json={
            "artist_name": f"Iter58 Akun Artis {suffix}",
            "email": artist_email,
            "password": f"Iter58#{suffix}Pwd",
            "social_links": [
                {"platform": "instagram", "url": f"https://instagram.com/iter58akun_{suffix}"},
            ],
        },
        timeout=30,
    )
    artist_create.raise_for_status()
    artist_body = artist_create.json()
    if artist_body.get("user_id"):
        created_artist_user_ids.append(artist_body["user_id"])

    with open(STATE_PATH, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "label_id": label_id,
                "saved_artist_id": saved_artist_id,
                "legacy_artist_id": legacy_artist_id,
                "release_id": release_id,
                "artist_user_ids": created_artist_user_ids,
                "suffix": suffix,
                "seeded": seeded,
            },
            handle,
        )
    print(f"seeded:{release_id}")


def cleanup() -> None:
    db = _db()
    if not os.path.exists(STATE_PATH):
        print("no_state")
        return

    with open(STATE_PATH, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    seeded = data.get("seeded") or {}
    if seeded:
        _cleanup(db, seeded, data.get("release_id") or "", f"{PRODUCT_ID_PREFIX}-{data.get('suffix', '')}")
    else:
        release_id = data.get("release_id")
        if release_id:
            db.tracks.delete_many({"release_id": release_id})
            db.releases.delete_many({"id": release_id})
        db.artists.delete_many({"label_id": data.get("label_id")})

    if data.get("artist_user_ids"):
        db.users.delete_many({"id": {"$in": data.get("artist_user_ids") or []}})

    os.remove(STATE_PATH)
    print("cleaned")


if __name__ == "__main__":
    action = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
    if action == "seed":
        seed()
    elif action == "cleanup":
        cleanup()
    else:
        raise SystemExit("Usage: python /app/tests/iter58_ui_fixture.py [seed|cleanup]")
