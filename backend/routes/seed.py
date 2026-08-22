"""Startup seeding: indexes, super-admin, sub-admins, landing settings, migrations."""
import os
from .deps import db, db_bg, logger
from auth_utils import hash_password, verify_password, SUPER_ADMIN
from models import now_iso, new_id
from .cms_defaults import DEFAULT_LANDING_SETTINGS


async def seed_indexes_and_admins():
    # ---- Indexes ----
    # Use db_bg because building/migrating an index on a multi-million-row
    # collection (e.g. `royalty_lines` in production) routinely exceeds the
    # 10s client-side CSOT cap on Atlas. create_index is idempotent so already-
    # existing indexes are no-ops regardless of client.
    await db_bg.users.create_index("id", unique=True)
    await db_bg.labels.create_index("user_id")
    await db_bg.labels.create_index("id", unique=True)
    await db_bg.artists.create_index("user_id")
    await db_bg.artists.create_index("label_id")
    await db_bg.releases.create_index("label_id")
    await db_bg.releases.create_index("status")
    await db_bg.releases.create_index("upc")
    await db_bg.tracks.create_index("release_id")
    await db_bg.tracks.create_index("artist_id")
    await db_bg.tracks.create_index("isrc")
    await db_bg.tracks.create_index("label_id")
    await db_bg.payments.create_index("label_id")
    await db_bg.payments.create_index("status")
    await db_bg.payments.create_index("xendit_invoice_id")
    await db_bg.payments.create_index("reference_id", unique=True, sparse=True)
    session_index = (await db_bg.payments.index_information()).get("xendit_session_id_1")
    if session_index and not session_index.get("partialFilterExpression"):
        await db_bg.payments.drop_index("xendit_session_id_1")
    await db_bg.payments.create_index(
        "xendit_session_id", unique=True,
        partialFilterExpression={"xendit_session_id": {"$type": "string"}},
    )
    await db_bg.payments.create_index([("label_id", 1), ("created_at", -1)])
    await db_bg.payment_products.create_index("id", unique=True)
    await db_bg.payment_products.create_index("active")
    await db_bg.service_orders.create_index("id", unique=True)
    await db_bg.service_orders.create_index("label_id")
    await db_bg.password_reset_tokens.create_index("token")
    await db_bg.email_verification_tokens.create_index("token")
    await db_bg.login_attempts.create_index("identifier")
    await db_bg.activity_logs.create_index("created_at")
    await db_bg.landing_settings.create_index("key", unique=True)
    await db_bg.royalty_imports.create_index("created_at")
    await db_bg.royalty_lines.create_index("import_id")
    await db_bg.royalty_lines.create_index("label_id")
    await db_bg.royalty_lines.create_index("artist_id")
    await db_bg.royalty_lines.create_index("period")
    await db_bg.royalty_lines.create_index("status")
    await db_bg.royalty_lines.create_index([("import_id", 1), ("match_status", 1), ("status", 1)])
    await db_bg.royalty_lines.create_index([("import_id", 1), ("label_id", 1)])
    # Phase 27 — critical compound + secondary indexes for migration tools
    # Per-label Withdraw FIFO dry-run aggregations (filters by label_id + period + status)
    await db_bg.royalty_lines.create_index([("label_id", 1), ("period", 1), ("status", 1)])
    # Materialize Artists scans by (label_id, artist_name_raw) and matches status
    await db_bg.royalty_lines.create_index([("label_id", 1), ("artist_name_raw", 1)])
    await db_bg.royalty_lines.create_index("artist_name_raw")
    # Backfill row_period: paginate-by-_id where row_period exists & differs from period
    await db_bg.royalty_lines.create_index("row_period")
    # Release/track entity rollup lookups
    await db_bg.royalty_lines.create_index("release_id")
    await db_bg.royalty_lines.create_index("track_id")
    # Migration jobs (Phase 26+): admin polls by id; status used for resume logic
    await db_bg.migrate_jobs.create_index("id", unique=True)
    await db_bg.migrate_jobs.create_index([("status", 1), ("submitted_at", -1)])
    await db_bg.migrate_jobs.create_index("kind")
    await db_bg.withdraw_requests.create_index("label_id")
    await db_bg.withdraw_requests.create_index("status")
    await db_bg.balance_transactions.create_index("label_id")
    await db_bg.bank_accounts.create_index("label_id", unique=True)
    await db_bg.support_tickets.create_index("label_id")
    await db_bg.support_tickets.create_index("status")
    await db_bg.support_tickets.create_index("category")
    await db_bg.support_tickets.create_index("created_at")
    await db_bg.ticket_comments.create_index("ticket_id")
    await db_bg.contracts.create_index("label_id")
    await db_bg.contracts.create_index("status")
    await db_bg.contracts.create_index("end_date")
    await db_bg.notifications.create_index("user_id")
    await db_bg.notifications.create_index([("user_id", 1), ("read_at", 1)])
    await db_bg.notifications.create_index("created_at")
    await db_bg.wami_orders.create_index("label_id")
    await db_bg.wami_orders.create_index("track_id")
    await db_bg.wami_orders.create_index("status")

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

    # Phase 32 — distributor fee has been removed from the royalty formula.
    # Force old CMS documents to zero so existing production settings cannot
    # reintroduce the retired fee in public copy/simulators.
    await db.landing_settings.update_one(
        {"key": "pricing"},
        {"$set": {"value.distributor_fee_percent": 0, "updated_at": now_iso()}},
    )
    await db.landing_settings.update_one(
        {"key": "royalty_sim"},
        {"$set": {"value.fee_percent": 0, "updated_at": now_iso()}},
    )
