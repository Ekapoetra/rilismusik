"""Live-suite helper: seed dynamic admin role documents on a fresh database.

Production databases already contain role rows created historically; a fresh
CI MongoDB does not, so seeded sub-admin users (admin_finance, admin_support,
...) would fail login with "Role admin sedang dinonaktifkan". This script
inserts the builtin role defaults with schema version 0, then re-runs
ensure_admin_access_defaults() so every versioned permission migration applies
— mirroring what a long-lived production DB looks like.

It also seeds the static label fixture several phase-2 tests query
(`label1@test.com` + a track carrying LABEL1_ISRC). The account is inserted
directly — label1 cannot log in through the API because EmailStr rejects the
`.test` TLD, so the session-based label tests skip; admin-side import tests
only need the label/track documents to exist for ISRC matching.

Usage (from backend/):  python -m tests.ci_seed_admin_roles
"""
import asyncio
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

from auth_utils import hash_password  # noqa: E402
from models import now_iso  # noqa: E402
from routes.admin_permission_service import (  # noqa: E402
    BUILTIN_ROLE_DEFAULTS,
    BUILTIN_ROLE_NAMES,
    SYSTEM_ROLE,
    ensure_admin_access_defaults,
)


async def main() -> None:
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    for key, permissions in BUILTIN_ROLE_DEFAULTS.items():
        if key == SYSTEM_ROLE:
            continue
        name = BUILTIN_ROLE_NAMES.get(key, key)
        await db.admin_roles.update_one(
            {"key": key},
            {"$setOnInsert": {
                "id": key,
                "key": key,
                "name": name,
                "normalized_name": name.casefold(),
                "permissions": list(permissions),
                "active": True,
                "system": False,
                "builtin": False,
                "rbac_schema_version": 0,
            }},
            upsert=True,
        )
    await ensure_admin_access_defaults(db)
    count = await db.admin_roles.count_documents({})
    print(f"live-suite admin roles seeded; admin_roles now holds {count} docs")

    await _seed_label1_fixture(db)


async def _seed_label1_fixture(db) -> None:
    """Docs-only fixture: phase-2 ISRC matching needs label1's track."""
    now = now_iso()
    user_id = "ci-label1-user"
    label_id = "ci-label1-label"
    release_id = "ci-label1-release"
    track_id = "ci-label1-track"
    await db.users.update_one(
        {"id": user_id},
        {"$setOnInsert": {
            "id": user_id, "name": "CI Label One", "email": "label1@test.com",
            "password_hash": hash_password(f"ci-unused-{uuid.uuid4().hex}"),
            "role": "label", "status": "active", "token_version": 0,
            "email_verified_at": now, "created_at": now, "updated_at": now,
        }},
        upsert=True,
    )
    await db.labels.update_one(
        {"id": label_id},
        {"$setOnInsert": {
            "id": label_id, "user_id": user_id, "label_name": "Label One",
            "pic_name": "Label One PIC", "email": "label1@test.com",
            "whatsapp": "081234567890", "address": "Jl. CI", "city": "Jakarta",
            "country": "Indonesia", "logo_storage_key": f"label-logo/{label_id}/logo.png",
            "contract_status": "active", "kyc_status": "verified",
            "kyc_document_id": "ci-label1-kyc", "kyc_verified_at": now,
            "account_status": "active", "payment_type": "pay_per_release",
            "subscription_status": "inactive", "subscription_tier": None,
            "subscription_expires_at": None, "royalty_percentage_default": 60.0,
            "balance_available_idr": 0, "balance_pending_idr": 0,
            "balance_withdraw_requested_idr": 0, "package_revision": 0,
            "created_at": now, "updated_at": now,
        }},
        upsert=True,
    )
    await db.kyc_documents.update_one(
        {"id": "ci-label1-kyc"},
        {"$setOnInsert": {
            "id": "ci-label1-kyc", "label_id": label_id, "status": "verified",
            "is_current": True, "storage_key": f"kyc-private/{label_id}/ktp.png",
            "uploaded_at": now, "reviewed_at": now,
        }},
        upsert=True,
    )
    await db.releases.update_one(
        {"id": release_id},
        {"$setOnInsert": {
            "id": release_id, "label_id": label_id,
            "release_title": "CI Label One Release", "primary_artist": "CI Artist",
            "release_type": "single", "release_date": "2026-01-01",
            "status": "live", "imported_legacy": True,
            "created_at": now, "updated_at": now,
        }},
        upsert=True,
    )
    await db.tracks.update_one(
        {"id": track_id},
        {"$setOnInsert": {
            "id": track_id, "release_id": release_id, "label_id": label_id,
            "track_title": "CI Label One Track", "artist_name": "CI Artist",
            "isrc": "ID-A1Z-26-12345", "track_number": 1,
            "imported_legacy": True, "created_at": now, "updated_at": now,
        }},
        upsert=True,
    )
    print("live-suite label1 fixture seeded (ci-label1-*)")


if __name__ == "__main__":
    asyncio.run(main())
