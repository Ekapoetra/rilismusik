"""Deterministic Multi Label QA fixture (seed/cleanup). Isolated test account.

Usage:
    python -m scripts.seed_multilabel_fixture seed
    python -m scripts.seed_multilabel_fixture cleanup

Creates ONE label account (multilabel-qa@example.com / MultiLabelQA#2026) that owns
TWO labels (A + B). Label A holds the account Multi Label entitlement (tier=multi_label,
active). Royalty lines give A=Rp2.000.000 and B=Rp3.000.000 available (per-label cutoff
null). Label A also gets one LIVE release + track for the free-WAMI test.
All ids are prefixed 'mlqa-' so cleanup is exact.
"""
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta

from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from auth_utils import hash_password  # noqa: E402

EMAIL = "multilabel-qa@example.com"
PASSWORD = "MultiLabelQA#2026"
USER_ID = "mlqa-user"
LABEL_A = "mlqa-label-a"
LABEL_B = "mlqa-label-b"
RELEASE = "mlqa-release-a"
TRACK = "mlqa-track-a"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


async def _provision_kyc(db, label_id, now):
    """Satisfy compute_kyc_state for a label (bank + contract + kyc document)."""
    await db.bank_accounts.update_one({"label_id": label_id}, {"$set": {
        "id": f"{label_id}-bank", "label_id": label_id, "bank_name": "Bank Central Asia",
        "account_number": "1234567890", "account_holder_name": "Multi Label QA",
        "verified_status": "verified", "created_at": now, "updated_at": now,
    }}, upsert=True)
    await db.contracts.update_one({"id": f"{label_id}-contract"}, {"$set": {
        "id": f"{label_id}-contract", "label_id": label_id, "status": "active",
        "start_date": "2026-01-01", "end_date": "2027-12-31", "created_at": now,
    }}, upsert=True)
    await db.kyc_documents.update_one({"id": f"{label_id}-kycdoc"}, {"$set": {
        "id": f"{label_id}-kycdoc", "label_id": label_id, "is_current": True,
        "status": "verified", "storage_key": f"kyc/{label_id}.pdf", "created_at": now,
    }}, upsert=True)


async def seed(db):
    now = now_iso()
    far = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
    await db.users.update_one({"id": USER_ID}, {"$set": {
        "id": USER_ID, "email": EMAIL, "name": "Multi Label QA",
        "role": "label", "status": "active",
        "password_hash": hash_password(PASSWORD),
        "primary_label_id": LABEL_A, "email_verified": True,
        "created_at": now, "updated_at": now,
    }}, upsert=True)
    base_label = {
        "user_id": USER_ID, "pic_name": "Multi Label QA", "email": EMAIL,
        "whatsapp": "081200000009", "label_type": "label", "country": "Indonesia",
        "address": "Jl. QA No. 9", "city": "Jakarta", "logo_storage_key": "label-logo/mlqa.png",
        "royalty_percentage_default": 60.0, "account_status": "active",
        "kyc_status": "verified", "kyc_verified_at": now, "package_revision": 0,
        "bank_name": "Bank Central Asia", "bank_account_number": "1234567890",
        "bank_account_holder": "Multi Label QA", "bank_verification_status": "verified",
        "created_at": now, "updated_at": now,
    }
    # Label A = account authority (Multi Label active)
    await db.labels.update_one({"id": LABEL_A}, {"$set": {
        **base_label, "id": LABEL_A, "label_name": "MLQA Label A", "kyc_document_id": f"{LABEL_A}-kycdoc",
        "payment_type": "annual_subscription", "subscription_tier": "multi_label",
        "subscription_status": "active", "subscription_expires_at": far,
        "last_withdrawn_period": None,
    }}, upsert=True)
    # Label B = child (own package irrelevant; inherits account entitlement)
    await db.labels.update_one({"id": LABEL_B}, {"$set": {
        **base_label, "id": LABEL_B, "label_name": "MLQA Label B", "kyc_document_id": f"{LABEL_B}-kycdoc",
        "payment_type": "pay_per_release", "subscription_tier": None,
        "subscription_status": "inactive", "subscription_expires_at": None,
        "last_withdrawn_period": None,
    }}, upsert=True)
    await _provision_kyc(db, LABEL_A, now)
    await _provision_kyc(db, LABEL_B, now)
    # Royalty: A=2.000.000 (2026-05), B=3.000.000 (2026-06), both available
    await db.royalty_lines.update_one({"id": "mlqa-line-a"}, {"$set": {
        "id": "mlqa-line-a", "label_id": LABEL_A, "period": "2026-05",
        "status": "available", "label_idr": 2_000_000, "legacy_settled": False,
    }}, upsert=True)
    await db.royalty_lines.update_one({"id": "mlqa-line-b"}, {"$set": {
        "id": "mlqa-line-b", "label_id": LABEL_B, "period": "2026-06",
        "status": "available", "label_idr": 3_000_000, "legacy_settled": False,
    }}, upsert=True)
    # Live release + track on Label A for free-WAMI test
    await db.releases.update_one({"id": RELEASE}, {"$set": {
        "id": RELEASE, "label_id": LABEL_A, "label_name": "MLQA Label A",
        "release_title": "MLQA Live Single", "release_type": "single",
        "status": "live", "artist_name": "MLQA Artist",
        "primary_artists": [{"name": "MLQA Artist"}],
        "live_at": now, "created_at": now, "updated_at": now,
    }}, upsert=True)
    await db.tracks.update_one({"id": TRACK}, {"$set": {
        "id": TRACK, "release_id": RELEASE, "label_id": LABEL_A,
        "track_title": "MLQA Live Track", "track_number": 1, "isrc": "IDMLQA2600001",
        "created_at": now, "updated_at": now,
    }}, upsert=True)
    print(f"SEEDED. login {EMAIL} / {PASSWORD}")
    print(f"labels: {LABEL_A} (multi_label), {LABEL_B}; expected account_available_idr=5000000")
    print(f"free-WAMI track_id={TRACK} (release live)")


async def cleanup(db):
    await db.users.delete_one({"id": USER_ID})
    await db.labels.delete_many({"id": {"$in": [LABEL_A, LABEL_B]}})
    await db.royalty_lines.delete_many({"id": {"$in": ["mlqa-line-a", "mlqa-line-b"]}})
    await db.releases.delete_many({"id": RELEASE})
    await db.tracks.delete_many({"id": TRACK})
    await db.wami_orders.delete_many({"label_id": {"$in": [LABEL_A, LABEL_B]}})
    await db.addon_orders.delete_many({"label_id": {"$in": [LABEL_A, LABEL_B]}})
    await db.bank_accounts.delete_many({"label_id": {"$in": [LABEL_A, LABEL_B]}})
    await db.contracts.delete_many({"label_id": {"$in": [LABEL_A, LABEL_B]}})
    await db.kyc_documents.delete_many({"label_id": {"$in": [LABEL_A, LABEL_B]}})
    await db.label_daily_submissions.delete_many({"scope_key": f"acct:{USER_ID}"})
    await db.label_daily_submissions.delete_many({"scope_key": {"$in": [LABEL_A, LABEL_B]}})
    print("CLEANED UP MLQA fixture")


async def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "seed"
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"]); db = cli[os.environ["DB_NAME"]]
    if cmd == "seed":
        await seed(db)
    elif cmd == "cleanup":
        await cleanup(db)
    else:
        print("unknown command", cmd)
    cli.close()


if __name__ == "__main__":
    asyncio.run(main())
