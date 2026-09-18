"""Merge Wizard QA fixture — 3 separate single-label accounts (ids prefixed `mgqa-`).

  python -m scripts.seed_merge_fixture seed|cleanup

Account A → Label A → Annual, BCA verified, eligible 2.000.000, last_withdrawn 2026-04
Account B → Label B → VIP,    BRI verified, eligible 3.000.000, last_withdrawn 2026-06
Account C → Label C → PPR,    Mandiri verified, eligible 4.000.000, last_withdrawn 2026-02
Also Label C has a legacy line that must NOT appear in Multi Label balance.
"""
import asyncio, os, sys
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from auth_utils import hash_password  # noqa: E402

ACCTS = [
    ("mgqa-user-a", "mgqa-a@example.com", "MergeA#2026", "mgqa-label-a", "MGQA Label A", "Budi", "annual_normal", "Bank Central Asia", "1111111111", 2_000_000, "2026-04"),
    ("mgqa-user-b", "mgqa-b@example.com", "MergeB#2026", "mgqa-label-b", "MGQA Label B", "Eka", "annual_vip", "Bank Rakyat Indonesia", "2222222222", 3_000_000, "2026-06"),
    ("mgqa-user-c", "mgqa-c@example.com", "MergeC#2026", "mgqa-label-c", "MGQA Label C", "Eka Saputra", None, "Bank Mandiri", "3333333333", 4_000_000, "2026-02"),
]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


async def seed(db):
    now = now_iso()
    for uid, email, pw, lid, lname, pic, tier, bank, acc, bal, cutoff in ACCTS:
        await db.users.update_one({"id": uid}, {"$set": {
            "id": uid, "email": email, "name": pic, "role": "label", "status": "active",
            "password_hash": hash_password(pw), "email_verified": True,
            "created_at": now, "updated_at": now,
        }}, upsert=True)
        await db.labels.update_one({"id": lid}, {"$set": {
            "id": lid, "user_id": uid, "label_name": lname, "pic_name": pic, "email": email,
            "whatsapp": "0812000000" + lid[-1], "label_type": "label", "country": "Indonesia",
            "address": "Jl QA", "city": "Jakarta", "logo_storage_key": f"logo/{lid}.png",
            "royalty_percentage_default": 60.0, "account_status": "active", "kyc_status": "verified",
            "kyc_document_id": f"{lid}-kycdoc", "package_revision": 0,
            "payment_type": "annual_subscription" if tier else "pay_per_release",
            "subscription_tier": tier, "subscription_status": "active" if tier else "inactive",
            "subscription_expires_at": "2027-06-30T00:00:00+00:00" if tier else None,
            "last_withdrawn_period": cutoff,
            "bank_name": bank, "bank_account_number": acc, "bank_account_holder": pic,
            "bank_verification_status": "verified",
            "created_at": now, "updated_at": now,
        }}, upsert=True)
        await db.bank_accounts.update_one({"id": f"{lid}-bank"}, {"$set": {
            "id": f"{lid}-bank", "label_id": lid, "bank_name": bank, "account_number": acc,
            "account_holder_name": pic, "verified_status": "verified", "created_at": now, "updated_at": now,
        }}, upsert=True)
        await db.contracts.update_one({"id": f"{lid}-contract"}, {"$set": {
            "id": f"{lid}-contract", "label_id": lid, "status": "active",
            "start_date": "2026-01-01", "end_date": "2027-12-31", "created_at": now,
        }}, upsert=True)
        await db.kyc_documents.update_one({"id": f"{lid}-kycdoc"}, {"$set": {
            "id": f"{lid}-kycdoc", "label_id": lid, "is_current": True, "status": "verified",
            "storage_key": f"kyc/{lid}.pdf", "created_at": now,
        }}, upsert=True)
        # eligible royalty AFTER the label cutoff so it counts
        await db.royalty_lines.update_one({"id": f"{lid}-line"}, {"$set": {
            "id": f"{lid}-line", "label_id": lid, "period": "2026-08",
            "status": "available", "label_idr": bal, "legacy_settled": False,
        }}, upsert=True)
    # Legacy line on Label C — must NOT appear in balance
    await db.royalty_lines.update_one({"id": "mgqa-label-c-legacy"}, {"$set": {
        "id": "mgqa-label-c-legacy", "label_id": "mgqa-label-c", "period": "2025-01",
        "status": "available", "label_idr": 9_999_999, "legacy_settled": True,
    }}, upsert=True)
    print("SEEDED merge fixture: A/B/C (primary=mgqa-user-a). Bank BCA id=mgqa-label-a-bank")
    print("logins: mgqa-a@example.com/MergeA#2026, mgqa-b@.../MergeB#2026, mgqa-c@.../MergeC#2026")


async def cleanup(db):
    uids = [a[0] for a in ACCTS]
    lids = [a[3] for a in ACCTS]
    await db.users.delete_many({"id": {"$in": uids}})
    await db.labels.delete_many({"id": {"$in": lids}})
    await db.bank_accounts.delete_many({"label_id": {"$in": lids}})
    await db.contracts.delete_many({"label_id": {"$in": lids}})
    await db.kyc_documents.delete_many({"label_id": {"$in": lids}})
    await db.royalty_lines.delete_many({"label_id": {"$in": lids}})
    await db.multi_label_merges.delete_many({"label_ids": {"$in": lids}})
    await db.multi_label_withdraw_batches.delete_many({"user_id": {"$in": uids}})
    await db.withdraw_requests.delete_many({"label_id": {"$in": lids}})
    print("CLEANED merge fixture")


async def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "seed"
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"]); db = cli[os.environ["DB_NAME"]]
    await (seed(db) if cmd == "seed" else cleanup(db))
    cli.close()


if __name__ == "__main__":
    asyncio.run(main())
