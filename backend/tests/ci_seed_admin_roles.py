"""Live-suite helper: seed dynamic admin role documents on a fresh database.

Production databases already contain role rows created historically; a fresh
CI MongoDB does not, so seeded sub-admin users (admin_finance, admin_support,
...) would fail login with "Role admin sedang dinonaktifkan". This script
inserts the builtin role defaults with schema version 0, then re-runs
ensure_admin_access_defaults() so every versioned permission migration applies
— mirroring what a long-lived production DB looks like.

Usage (from backend/):  python -m tests.ci_seed_admin_roles
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

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


if __name__ == "__main__":
    asyncio.run(main())
