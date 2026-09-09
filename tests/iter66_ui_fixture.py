"""Iter66 UI fixture seed/cleanup for isolated label release + audio/chat/notification checks."""

import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")


STATE_PATH = "/app/tests/iter66_ui_fixture_state.json"
CREDS_PATH = Path("/app/memory/test_credentials.md")
WAV_OK = "https://raw.githubusercontent.com/pdx-cs-sound/wavs/master/sine.wav"
WAV_BAD = "/api/files/iter66-missing.wav"


def _load_env():
    load_dotenv("/app/backend/.env", override=True)
    load_dotenv("/app/backend/.env.test", override=True)
    load_dotenv("/app/frontend/.env", override=True)


def _api_base() -> str:
    base = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
    return f"{base}/api"


def _db():
    import pymongo

    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _login(email: str, password: str) -> str:
    response = requests.post(
        f"{_api_base()}/auth/login",
        json={"email": email, "password": password},
        timeout=40,
    )
    response.raise_for_status()
    token = response.json().get("access_token")
    if not token:
        raise RuntimeError("Login succeeded without access_token")
    return token


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _append_credential(email: str, password: str):
    line = f"\n- Iter66 fixture `{email}` / `{password}` — ACTIVE QA\n"
    with CREDS_PATH.open("a", encoding="utf-8") as stream:
        stream.write(line)


def _retire_credential(email: str):
    if not CREDS_PATH.exists():
        return
    lines = CREDS_PATH.read_text(encoding="utf-8").splitlines()
    updated = []
    for line in lines:
        if f"`{email}`" in line and "ACTIVE QA" in line:
            updated.append(line.replace("ACTIVE QA", "REMOVED (fixture teardown)"))
        else:
            updated.append(line)
    CREDS_PATH.write_text("\n".join(updated) + "\n", encoding="utf-8")


def _seed_verified_label(db, suffix: str) -> dict:
    from auth_utils import hash_password

    now = datetime.now(timezone.utc).isoformat()
    user_id = f"iter66-user-{suffix}"
    label_id = f"iter66-label-{suffix}"
    email = f"iter66-ui-{suffix}@example.com"
    password = f"Iter66Ui#{suffix}Aa!"
    kyc_id = f"iter66-kyc-{suffix}"

    db.users.insert_one(
        {
            "id": user_id,
            "name": f"Iter66 Label {suffix}",
            "email": email,
            "password_hash": hash_password(password),
            "role": "label",
            "status": "active",
            "token_version": 0,
            "email_verified_at": now,
            "created_at": now,
            "updated_at": now,
        }
    )
    db.labels.insert_one(
        {
            "id": label_id,
            "user_id": user_id,
            "label_name": f"Iter66 Label {suffix}",
            "pic_name": "Iter66 PIC",
            "whatsapp": "081234567890",
            "address": "Jl. Iter66",
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
        }
    )
    db.kyc_documents.insert_one(
        {
            "id": kyc_id,
            "label_id": label_id,
            "storage_key": f"kyc-private/{label_id}/ktp.png",
            "status": "verified",
            "is_current": True,
            "uploaded_at": now,
            "reviewed_at": now,
        }
    )
    db.bank_accounts.insert_one(
        {
            "id": f"iter66-bank-{suffix}",
            "label_id": label_id,
            "bank_name": "BCA",
            "account_number": "1234567890",
            "account_holder_name": "Iter66 PIC",
            "verified_status": "verified",
            "created_at": now,
            "updated_at": now,
        }
    )
    db.contracts.insert_one(
        {
            "id": f"iter66-contract-{suffix}",
            "label_id": label_id,
            "status": "active",
            "start_date": "2026-01-01",
            "end_date": "2030-12-31",
            "created_at": now,
        }
    )
    _append_credential(email, password)
    return {"user_id": user_id, "label_id": label_id, "email": email, "password": password}


def seed():
    _load_env()
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    seeded = _seed_verified_label(db, suffix)
    release_date = (datetime.now(timezone.utc).date() + timedelta(days=8)).isoformat()

    token = _login(seeded["email"], seeded["password"])
    payload = {
        "release_title": f"Iter66 Audio Release {suffix}",
        "release_type": "ep",
        "artist_name": "Iter66 Artist",
        "release_date": release_date,
        "year": 2026,
        "genre": "Pop",
        "subgenre": "Pop",
        "language": "Indonesian",
        "explicit": False,
        "copyright_line": "℗ 2026 Iter66",
        "p_line": "© 2026 Iter66",
        "platforms": ["Spotify"],
        "artist_web_url": "https://youtube.com/channel/UC0aA0aA0aA0aA0aA0aA0aA0",
        "primary_artists": [],
        "featured_artists": [],
        "tracks": [
            {
                "track_title": "Iter66 Valid WAV",
                "artist_name": "Iter66 Artist",
                "composer": "Komposer A",
                "lyricist": "Penulis A",
                "producer": "Produser A",
                "arranger": "Arranger A",
                "performer": "Performer A",
                "genre": "Pop",
                "language": "Indonesian",
                "explicit": False,
                "track_number": 1,
                "preview_start_seconds": 5,
                "title_language": "Indonesian",
                "lyric_language": "Indonesian",
                "track_type": "original",
                "lyrics": "Lirik iter66 track satu",
                "vocal_type": "vocal",
            },
            {
                "track_title": "Iter66 Broken WAV",
                "artist_name": "Iter66 Artist",
                "composer": "Komposer B",
                "lyricist": "Penulis B",
                "producer": "Produser B",
                "arranger": "Arranger B",
                "performer": "Performer B",
                "genre": "Pop",
                "language": "Indonesian",
                "explicit": False,
                "track_number": 2,
                "preview_start_seconds": 0,
                "title_language": "Indonesian",
                "lyric_language": "Indonesian",
                "track_type": "original",
                "lyrics": "Lirik iter66 track dua",
                "vocal_type": "vocal",
            },
        ],
    }

    created = requests.post(f"{_api_base()}/releases/draft", headers=_headers(token), json=payload, timeout=40)
    created.raise_for_status()
    release_id = created.json()["id"]

    db.releases.update_one(
        {"id": release_id},
        {"$set": {"cover_url": "/api/files/iter66-cover.jpg", "cover_width": 3000, "cover_height": 3000}},
    )
    tracks = list(db.tracks.find({"release_id": release_id}, {"_id": 0, "id": 1}).sort("track_number", 1))
    if len(tracks) >= 2:
        db.tracks.update_one(
            {"id": tracks[0]["id"]},
            {
                "$set": {
                    "audio_url": WAV_OK,
                    "audio_filename": "iter66-valid.wav",
                    "audio_sample_rate": 44100,
                }
            },
        )
        db.tracks.update_one(
            {"id": tracks[1]["id"]},
            {
                "$set": {
                    "audio_url": WAV_BAD,
                    "audio_filename": "iter66-broken.wav",
                    "audio_sample_rate": 44100,
                }
            },
        )

    super_email = os.environ.get("TEST_SUPERADMIN_EMAIL", "").replace('"', "")
    super_admin = db.users.find_one({"email": super_email}, {"_id": 0, "id": 1})
    notification_id = f"iter66-notif-{suffix}"
    if super_admin and super_admin.get("id"):
        db.notifications.insert_one(
            {
                "id": notification_id,
                "user_id": super_admin["id"],
                "type": "system_alert",
                "title": f"Iter66 notification {suffix}",
                "body": "Notification sound validation target",
                "link": "/admin/dashboard",
                "meta": {"iter": 66, "owned": True},
                "created_at": datetime.now(timezone.utc).isoformat(),
                "read_at": None,
            }
        )

    state = {
        "suffix": suffix,
        "seeded": seeded,
        "release_id": release_id,
        "track_ids": [row["id"] for row in tracks],
        "notification_id": notification_id,
    }
    Path(STATE_PATH).write_text(json.dumps(state), encoding="utf-8")
    print(json.dumps({"ok": True, "release_id": release_id, "email": seeded["email"], "password": seeded["password"]}))


def cleanup():
    _load_env()
    state_file = Path(STATE_PATH)
    if not state_file.exists():
        print(json.dumps({"ok": True, "message": "no_state"}))
        return
    data = json.loads(state_file.read_text(encoding="utf-8"))
    seeded = data.get("seeded") or {}
    db = _db()

    release_id = data.get("release_id")
    if release_id:
        db.notifications.delete_many({"meta.release_id": release_id})
        db.activity_logs.delete_many({"reference_id": release_id})
        db.payments.delete_many({"release_id": release_id})
        db.tracks.delete_many({"release_id": release_id})
        db.releases.delete_many({"id": release_id})

    if data.get("notification_id"):
        db.notifications.delete_many({"id": data["notification_id"]})

    if seeded:
        label_id = seeded.get("label_id")
        user_id = seeded.get("user_id")
        if label_id:
            conversations = list(db.chat_conversations.find({"label_id": label_id}, {"_id": 0, "id": 1}))
            conversation_ids = [row["id"] for row in conversations]
            db.chat_messages.delete_many({"conversation_id": {"$in": conversation_ids}})
            db.chat_typing.delete_many({"conversation_id": {"$in": conversation_ids}})
            db.notifications.delete_many({"meta.conversation_id": {"$in": conversation_ids}})
            db.chat_conversations.delete_many({"id": {"$in": conversation_ids}})
            db.notifications.delete_many({"user_id": user_id})
            db.artists.delete_many({"label_id": label_id})
            db.bank_accounts.delete_many({"label_id": label_id})
            db.contracts.delete_many({"label_id": label_id})
            db.kyc_documents.delete_many({"label_id": label_id})
            db.labels.delete_many({"id": label_id})
        if user_id:
            db.chat_presence.delete_many({"user_id": user_id})
            db.auth_sessions.delete_many({"user_id": user_id})
            db.users.delete_many({"id": user_id})
        if seeded.get("email"):
            _retire_credential(seeded["email"])

    state_file.unlink(missing_ok=True)
    print(json.dumps({"ok": True, "message": "cleaned"}))


if __name__ == "__main__":
    action = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
    if action == "seed":
        seed()
    elif action == "cleanup":
        cleanup()
    else:
        raise SystemExit("Usage: python /app/tests/iter66_ui_fixture.py [seed|cleanup]")
