"""One-off helper: provision 2 demo label accounts for user-testing in preview.

Run: python3 -m scripts.seed_demo_labels
"""
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path(__file__).parent.parent / ".env.test")

from motor.motor_asyncio import AsyncIOMotorClient
from auth_utils import hash_password
from models import now_iso, new_id


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    now = now_iso()
    today = datetime.now(timezone.utc)

    demo_labels = [
        {
            "tag": "PPR",
            "email": os.environ["TEST_DEMO_PPR_EMAIL"],
            "password": os.environ["TEST_DEMO_PPR_PASSWORD"],
            "label_name": "Demo Label PPR",
            "pic_name": "Demo PPR PIC",
            "whatsapp": "081200000001",
            "payment_type": "pay_per_release",
            "subscription_tier": None,
            "subscription_status": "inactive",
            "subscription_expires_at": None,
            "balance_available_idr": 5_000_000,
            "balance_pending_idr": 1_500_000,
            "releases": [
                {"title": "Suara Hujan", "artist": "Demo Artist PPR", "type": "single", "isrc": "IDDEMOPPR0001", "upc": "3650DEMOPPR001"},
                {"title": "Pulang", "artist": "Demo Artist PPR", "type": "single", "isrc": "IDDEMOPPR0002", "upc": "3650DEMOPPR002"},
            ],
        },
        {
            "tag": "VIP",
            "email": os.environ["TEST_DEMO_VIP_EMAIL"],
            "password": os.environ["TEST_DEMO_VIP_PASSWORD"],
            "label_name": "Demo Label VIP",
            "pic_name": "Demo VIP PIC",
            "whatsapp": "081200000002",
            "payment_type": "annual_subscription",
            "subscription_tier": "annual_vip",
            "subscription_status": "active",
            "subscription_expires_at": (today + timedelta(days=300)).isoformat(),
            "balance_available_idr": 15_000_000,
            "balance_pending_idr": 3_200_000,
            "releases": [
                {"title": "Cinta Sederhana", "artist": "Demo Artist VIP", "type": "single", "isrc": "IDDEMOVIP0001", "upc": "3650DEMOVIP001"},
                {"title": "Kota Mati", "artist": "Demo Artist VIP", "type": "ep", "isrc": "IDDEMOVIP0002", "upc": "3650DEMOVIP002"},
                {"title": "Symphony Kecil", "artist": "Demo Artist VIP", "type": "album", "isrc": "IDDEMOVIP0003", "upc": "3650DEMOVIP003"},
            ],
        },
    ]

    for cfg in demo_labels:
        # Cleanup any prior demo
        existing = await db.users.find_one({"email": cfg["email"]})
        if existing:
            await db.users.delete_one({"id": existing["id"]})
            old_lab = await db.labels.find_one({"user_id": existing["id"]})
            if old_lab:
                await db.labels.delete_one({"id": old_lab["id"]})
                await db.releases.delete_many({"label_id": old_lab["id"]})
                await db.tracks.delete_many({"label_id": old_lab["id"]})
                await db.contracts.delete_many({"label_id": old_lab["id"]})
                await db.balance_transactions.delete_many({"label_id": old_lab["id"]})
                await db.wami_orders.delete_many({"label_id": old_lab["id"]})

        user_id = new_id()
        await db.users.insert_one({
            "id": user_id,
            "name": cfg["pic_name"],
            "email": cfg["email"],
            "password_hash": hash_password(cfg["password"]),
            "role": "label",
            "email_verified_at": now,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        })
        label_id = new_id()
        await db.labels.insert_one({
            "id": label_id,
            "user_id": user_id,
            "label_name": cfg["label_name"],
            "pic_name": cfg["pic_name"],
            "email": cfg["email"],
            "whatsapp": cfg["whatsapp"],
            "address": "Jl. Demo No. 1",
            "city": "Jakarta",
            "country": "Indonesia",
            "label_type": "label",
            "royalty_percentage_default": 60.0,
            "payment_type": cfg["payment_type"],
            "subscription_status": cfg["subscription_status"],
            "subscription_tier": cfg["subscription_tier"],
            "subscription_expires_at": cfg["subscription_expires_at"],
            "contract_status": "active",
            "account_status": "active",
            "bank_verified": True,
            "blacklisted": False,
            "balance_available_idr": cfg["balance_available_idr"],
            "balance_pending_idr": cfg["balance_pending_idr"],
            "balance_withdraw_requested_idr": 0,
            "mda_accepted_at": now,
            "demo_account": True,
            "created_at": now,
            "updated_at": now,
        })
        # MDA contract
        await db.contracts.insert_one({
            "id": new_id(),
            "label_id": label_id,
            "label_name": cfg["label_name"],
            "title": "Master Distribution Agreement",
            "kind": "mda",
            "file_url": None,
            "filename": f"MDA-Demo-{cfg['tag']}.pdf",
            "start_date": now[:10],
            "end_date": None,
            "is_lifetime": True,
            "status": "active",
            "notes": "Demo account auto-seeded.",
            "accepted_at": now,
            "accepted_by_name": cfg["pic_name"],
            "accepted_by_email": cfg["email"],
            "created_at": now,
            "updated_at": now,
            "created_by": "system",
        })
        # Bank account
        await db.bank_accounts.insert_one({
            "id": new_id(),
            "label_id": label_id,
            "bank_name": "BCA",
            "account_number": "1234567890",
            "account_holder": cfg["pic_name"],
            "verified": True,
            "created_at": now,
            "updated_at": now,
        })
        # Releases + tracks
        for i, r in enumerate(cfg["releases"]):
            release_id = new_id()
            await db.releases.insert_one({
                "id": release_id,
                "label_id": label_id,
                "release_title": r["title"],
                "primary_artist": r["artist"],
                "isrc_release": None,
                "upc": r["upc"],
                "release_type": r["type"],
                "release_date": (today - timedelta(days=60 + i * 30)).date().isoformat(),
                "status": "live",
                "cover_url": None,
                "imported_legacy": True,
                "demo_account": True,
                "created_at": now,
                "updated_at": now,
            })
            await db.tracks.insert_one({
                "id": new_id(),
                "release_id": release_id,
                "label_id": label_id,
                "artist_id": None,
                "track_title": r["title"],
                "artist_name": r["artist"],
                "isrc": r["isrc"],
                "duration_sec": 220,
                "composer": cfg["pic_name"],
                "audio_url": None,
                "imported_legacy": True,
                "demo_account": True,
                "created_at": now,
                "updated_at": now,
            })

        # Sample balance transactions
        await db.balance_transactions.insert_many([
            {
                "id": new_id(),
                "label_id": label_id,
                "type": "royalty_available",
                "amount_idr": cfg["balance_available_idr"],
                "reference_type": "royalty_import",
                "reference_id": "demo-seed",
                "description": f"[Demo seed] Saldo awal Rp {cfg['balance_available_idr']:,}".replace(",", "."),
                "created_at": (today - timedelta(days=5)).isoformat(),
            },
            {
                "id": new_id(),
                "label_id": label_id,
                "type": "royalty_pending",
                "amount_idr": cfg["balance_pending_idr"],
                "reference_type": "royalty_import",
                "reference_id": "demo-seed",
                "description": f"[Demo seed] Saldo pending Rp {cfg['balance_pending_idr']:,}".replace(",", "."),
                "created_at": (today - timedelta(days=2)).isoformat(),
            },
        ])

        # For VIP — add 1 historical paid withdraw + 1 free WAMI order
        if cfg["tag"] == "VIP":
            await db.withdraw_requests.insert_one({
                "id": new_id(),
                "label_id": label_id,
                "amount_idr": 5_000_000,
                "status": "paid",
                "bank_ref": "BCA-DEMO-001",
                "notes": "Demo seed — withdraw historis",
                "requested_at": (today - timedelta(days=45)).isoformat(),
                "paid_at": (today - timedelta(days=40)).isoformat(),
                "created_at": (today - timedelta(days=45)).isoformat(),
                "updated_at": (today - timedelta(days=40)).isoformat(),
            })
            first_track = await db.tracks.find_one({"label_id": label_id})
            if first_track:
                await db.wami_orders.insert_one({
                    "id": new_id(),
                    "label_id": label_id,
                    "release_id": first_track["release_id"],
                    "track_id": first_track["id"],
                    "track_title": first_track["track_title"],
                    "price_idr": 0,
                    "is_free_vip": True,
                    "status": "registered",
                    "invoice_id": None,
                    "wami_id": "WAMI-DEMO-001",
                    "notes": "Demo VIP free registration.",
                    "created_at": (today - timedelta(days=30)).isoformat(),
                    "updated_at": (today - timedelta(days=10)).isoformat(),
                })

        print(f"✓ Demo {cfg['tag']}: {cfg['email']} | balance Rp {cfg['balance_available_idr']:,}".replace(",", "."))

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
