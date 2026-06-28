"""Startup seeding: indexes, super-admin, sub-admins, landing settings, migrations."""
import os
from .deps import db, logger
from auth_utils import hash_password, verify_password, SUPER_ADMIN
from models import now_iso, new_id
from .cms_defaults import DEFAULT_LANDING_SETTINGS


async def seed_indexes_and_admins():
    # ---- Indexes ----
    await db.users.create_index("id", unique=True)
    await db.labels.create_index("user_id")
    await db.labels.create_index("id", unique=True)
    await db.artists.create_index("user_id")
    await db.artists.create_index("label_id")
    await db.releases.create_index("label_id")
    await db.releases.create_index("status")
    await db.tracks.create_index("release_id")
    await db.tracks.create_index("artist_id")
    await db.payments.create_index("label_id")
    await db.payments.create_index("status")
    await db.payments.create_index("xendit_invoice_id")
    await db.password_reset_tokens.create_index("token")
    await db.email_verification_tokens.create_index("token")
    await db.login_attempts.create_index("identifier")
    await db.activity_logs.create_index("created_at")
    await db.landing_settings.create_index("key", unique=True)
    await db.royalty_imports.create_index("created_at")
    await db.royalty_lines.create_index("import_id")
    await db.royalty_lines.create_index("label_id")
    await db.royalty_lines.create_index("artist_id")
    await db.royalty_lines.create_index("period")
    await db.royalty_lines.create_index("status")
    await db.withdraw_requests.create_index("label_id")
    await db.withdraw_requests.create_index("status")
    await db.balance_transactions.create_index("label_id")
    await db.bank_accounts.create_index("label_id", unique=True)
    await db.support_tickets.create_index("label_id")
    await db.support_tickets.create_index("status")
    await db.support_tickets.create_index("category")
    await db.support_tickets.create_index("created_at")
    await db.ticket_comments.create_index("ticket_id")
    await db.contracts.create_index("label_id")
    await db.contracts.create_index("status")
    await db.contracts.create_index("end_date")
    await db.notifications.create_index("user_id")
    await db.notifications.create_index([("user_id", 1), ("read_at", 1)])
    await db.notifications.create_index("created_at")
    await db.wami_orders.create_index("label_id")
    await db.wami_orders.create_index("track_id")
    await db.wami_orders.create_index("status")

    # ---- Migrate legacy "annual_subscription" labels without subscription_tier to VIP ----
    try:
        result = await db.labels.update_many(
            {"payment_type": "annual_subscription", "subscription_tier": {"$exists": False}},
            {"$set": {"subscription_tier": "annual_vip", "updated_at": now_iso()}},
        )
        if result.modified_count:
            logger.info("Migrated %s legacy annual subscribers to VIP tier", result.modified_count)
    except Exception as e:
        logger.warning("Legacy subscription migration skipped: %s", e)

    # ---- Super admin ----
    admin_email = os.environ.get("ADMIN_EMAIL", "superadmin@rilismusik.com").lower().strip()
    admin_password = os.environ.get("ADMIN_PASSWORD", "SuperAdmin#2026")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        await db.users.insert_one({
            "id": new_id(),
            "name": "Super Admin",
            "email": admin_email,
            "password_hash": hash_password(admin_password),
            "role": SUPER_ADMIN,
            "email_verified_at": now_iso(),
            "status": "active",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        })
        logger.info("Super admin seeded: %s", admin_email)
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one(
            {"email": admin_email},
            {"$set": {"password_hash": hash_password(admin_password), "updated_at": now_iso()}},
        )
        logger.info("Super admin password updated for: %s", admin_email)

    # ---- Sub-admin accounts (idempotent — only create if missing) ----
    sub_admins = [
        ("Admin Support", "support1@rilismusik.com", "Support#2026", "admin_support"),
        ("Admin Finance", "finance1@rilismusik.com", "Finance#2026", "admin_finance"),
        ("Admin Release", "release1@rilismusik.com", "Release#2026", "admin_release"),
        ("Admin Marketing", "marketing1@rilismusik.com", "Marketing#2026", "admin_marketing"),
        ("Admin Content", "content1@rilismusik.com", "Content#2026", "admin_content"),
    ]
    for name, email, pwd, role in sub_admins:
        if await db.users.find_one({"email": email}) is None:
            await db.users.insert_one({
                "id": new_id(),
                "name": name,
                "email": email,
                "password_hash": hash_password(pwd),
                "role": role,
                "email_verified_at": now_iso(),
                "status": "active",
                "created_at": now_iso(),
                "updated_at": now_iso(),
            })
            logger.info("Sub-admin seeded: %s (%s)", email, role)

    # ---- Default landing settings (idempotent — only insert missing top-level keys) ----
    for key, value in DEFAULT_LANDING_SETTINGS.items():
        existing_setting = await db.landing_settings.find_one({"key": key})
        if not existing_setting:
            await db.landing_settings.insert_one({
                "id": new_id(),
                "key": key,
                "value": value,
                "updated_by": None,
                "updated_at": now_iso(),
            })

    # ---- Migration: backfill missing sub-keys inside existing landing_settings docs ----
    # When new pricing/legal_entity fields are added to DEFAULT_LANDING_SETTINGS,
    # this loop ensures they appear on already-seeded keys without overwriting admin edits.
    for key, default_value in DEFAULT_LANDING_SETTINGS.items():
        if not isinstance(default_value, dict):
            continue
        existing_setting = await db.landing_settings.find_one({"key": key})
        if not existing_setting:
            continue
        current_value = existing_setting.get("value") or {}
        if not isinstance(current_value, dict):
            continue
        added = {k: v for k, v in default_value.items() if k not in current_value}
        if added:
            await db.landing_settings.update_one(
                {"key": key},
                {"$set": {f"value.{k}": v for k, v in added.items()} | {"updated_at": now_iso()}},
            )
            logger.info("CMS migration: added %s to '%s'", list(added.keys()), key)
