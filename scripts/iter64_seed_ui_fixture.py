"""Seed iter64 UI fixture label with verified KYC and two releases/tracks."""
import os
from datetime import datetime, timezone

import pymongo
from dotenv import load_dotenv

import sys
sys.path.append("/app/backend")
from auth_utils import hash_password


load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/backend/.env.test", override=True)

EMAIL = os.environ["TEST_ITER64_UI_EMAIL"]
PASSWORD = os.environ["TEST_ITER64_UI_PASSWORD"]
NOW = datetime.now(timezone.utc).isoformat()


def main() -> None:
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    user_id = "iter64-ui-user"
    label_id = "iter64-ui-label"
    kyc_id = "iter64-ui-kyc"

    db.users.update_one(
        {"id": user_id},
        {"$set": {
            "id": user_id,
            "name": "Iter64 UI Label",
            "email": EMAIL,
            "password_hash": hash_password(PASSWORD),
            "role": "label",
            "status": "active",
            "token_version": 0,
            "email_verified_at": NOW,
            "created_at": NOW,
            "updated_at": NOW,
        }},
        upsert=True,
    )

    db.labels.update_one(
        {"id": label_id},
        {"$set": {
            "id": label_id,
            "user_id": user_id,
            "label_name": "iter64-ui-label",
            "pic_name": "Iter64 QA",
            "email": EMAIL,
            "whatsapp": "081200000064",
            "address": "Jl QA Iter64",
            "city": "Jakarta",
            "country": "Indonesia",
            "logo_storage_key": "label-logo/iter64-ui-logo.png",
            "account_status": "active",
            "kyc_status": "verified",
            "kyc_document_id": kyc_id,
            "created_at": NOW,
            "updated_at": NOW,
        }},
        upsert=True,
    )

    db.kyc_documents.update_one(
        {"id": kyc_id},
        {"$set": {
            "id": kyc_id,
            "label_id": label_id,
            "storage_key": f"kyc-private/{label_id}/ktp.png",
            "status": "verified",
            "is_current": True,
            "uploaded_at": NOW,
            "reviewed_at": NOW,
        }},
        upsert=True,
    )

    db.bank_accounts.update_one(
        {"id": "iter64-ui-bank"},
        {"$set": {
            "id": "iter64-ui-bank",
            "label_id": label_id,
            "bank_name": "BCA",
            "account_number": "6400640064",
            "account_holder_name": "Iter64 QA",
            "verified_status": "verified",
            "created_at": NOW,
            "updated_at": NOW,
        }},
        upsert=True,
    )

    db.contracts.update_one(
        {"id": "iter64-ui-contract"},
        {"$set": {
            "id": "iter64-ui-contract",
            "label_id": label_id,
            "status": "active",
            "start_date": "2026-01-01",
            "end_date": "2030-12-31",
            "created_at": NOW,
        }},
        upsert=True,
    )

    releases = [
        {
            "id": "iter64-ui-release-a",
            "label_id": label_id,
            "release_title": "Iter64 UI Release A",
            "artist_name": "Iter64 Artist A",
            "genre": "Pop",
            "language": "Indonesia",
            "copyright_line": "© Iter64",
            "p_line": "℗ Iter64",
            "upc": 640000000001,
            "status": "live",
            "cover_url": "/api/files/iter64-ui-a.jpg",
            "created_at": NOW,
            "updated_at": NOW,
        },
        {
            "id": "iter64-ui-release-b",
            "label_id": label_id,
            "release_title": "Iter64 UI Release B",
            "artist_name": "Iter64 Artist B",
            "genre": "Rock",
            "language": "English",
            "copyright_line": "© Iter64B",
            "p_line": "℗ Iter64B",
            "upc": None,
            "status": "live",
            "cover_url": "/api/files/iter64-ui-b.jpg",
            "created_at": NOW,
            "updated_at": NOW,
        },
    ]
    for release in releases:
        db.releases.update_one({"id": release["id"]}, {"$set": release}, upsert=True)

    tracks = [
        {"id": "iter64-ui-track-a1", "release_id": "iter64-ui-release-a", "label_id": label_id, "track_title": "A1", "track_number": 1, "isrc": "IDAAA2601001", "created_at": NOW, "updated_at": NOW},
        {"id": "iter64-ui-track-a2", "release_id": "iter64-ui-release-a", "label_id": label_id, "track_title": "A2", "track_number": 2, "isrc": "IDAAA2601002", "created_at": NOW, "updated_at": NOW},
        {"id": "iter64-ui-track-b1", "release_id": "iter64-ui-release-b", "label_id": label_id, "track_title": "B1", "track_number": 1, "isrc": None, "created_at": NOW, "updated_at": NOW},
    ]
    for track in tracks:
        db.tracks.update_one({"id": track["id"]}, {"$set": track}, upsert=True)

    print("iter64 fixture seeded")


if __name__ == "__main__":
    main()
