"""Seed/cleanup helper for Iteration 34 label analytics + admin label detail UI checks."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pymongo
from dotenv import load_dotenv

sys.path.append("/app/backend")
from auth_utils import hash_password


load_dotenv("/app/backend/.env", override=True)

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
PREFIX = "ITER34_UI"
CTX_PATH = Path("/app/tests/iter34_seed_context.json")


def db():
    client = pymongo.MongoClient(MONGO_URL)
    return client[DB_NAME]


def seed() -> None:
    database = db()
    user_id = f"{PREFIX}_USER"
    label_id = f"{PREFIX}_LABEL"
    other_label_id = f"{PREFIX}_OTHER_LABEL"
    email = "iter34_ui_label@example.com"
    password = "Iter34UI#2026"
    now = "2026-08-30T00:00:00+00:00"

    cleanup()

    database.users.insert_one({
        "id": user_id,
        "name": "Iter34 UI Label",
        "email": email,
        "password_hash": hash_password(password),
        "role": "label",
        "status": "active",
        "email_verified_at": now,
        "token_version": 0,
        "created_at": now,
        "updated_at": now,
    })

    database.labels.insert_many([
        {
            "id": label_id,
            "user_id": user_id,
            "label_name": "ITER34 Label Analytics",
            "pic_name": "Iter QA",
            "email": email,
            "last_withdrawn_period": "2025-12",
            "balance_pending_idr": 0,
            "balance_available_idr": 0,
            "balance_withdraw_requested_idr": 0,
            "royalty_percentage_default": 60,
            "account_status": "active",
            "payment_type": "annual_subscription",
            "subscription_status": "active",
            "subscription_tier": "annual_vip",
            "contract_status": "contract_active",
            "bank_verified": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": other_label_id,
            "label_name": "ITER34 Other Label",
            "account_status": "active",
            "created_at": now,
            "updated_at": now,
        },
    ])

    database.royalty_lines.insert_many([
        {"id": f"{PREFIX}-legacy-hidden", "label_id": label_id, "period": "2024-12", "status": "withdrawn", "legacy_settled": True, "quantity": 99999, "label_idr": 9999999, "track_title_raw": "Legacy Hidden", "artist_name_raw": "Legacy", "platform": "Legacy", "country": "XX"},
        {"id": f"{PREFIX}-jan", "label_id": label_id, "period": "2026-01", "status": "withdrawn", "legacy_settled": False, "quantity": 100, "label_idr": 1000, "track_title_raw": "Song Alpha", "artist_name_raw": "Artist One", "platform": "Spotify", "country": "ID"},
        {"id": f"{PREFIX}-feb", "label_id": label_id, "period": "2026-02", "status": "withdrawn", "legacy_settled": False, "quantity": 120, "label_idr": 1200, "track_title_raw": "Song Beta", "artist_name_raw": "Artist Two", "platform": "Apple Music", "country": "US"},
        {"id": f"{PREFIX}-mar", "label_id": label_id, "period": "2026-03", "status": "withdrawn", "legacy_settled": False, "quantity": 130, "label_idr": 1300, "track_title_raw": "Song Alpha", "artist_name_raw": "Artist One", "platform": "Spotify", "country": "ID"},
        {"id": f"{PREFIX}-apr", "label_id": label_id, "period": "2026-04", "status": "pending", "legacy_settled": False, "quantity": 140, "label_idr": 1400, "track_title_raw": "Song Gamma", "artist_name_raw": "Artist Three", "platform": "YouTube Music", "country": "ID"},
        {"id": f"{PREFIX}-may", "label_id": label_id, "period": "2026-05", "status": "available", "legacy_settled": False, "quantity": 150, "label_idr": 1500, "track_title_raw": "Song Alpha", "artist_name_raw": "Artist One", "platform": "Spotify", "country": "ID"},
        {"id": f"{PREFIX}-jun-a", "label_id": label_id, "period": "2026-06", "status": "available", "legacy_settled": False, "quantity": 220, "label_idr": 2200, "track_title_raw": "Song Alpha", "artist_name_raw": "Artist One", "platform": "Spotify", "country": "ID"},
        {"id": f"{PREFIX}-jun-b", "label_id": label_id, "period": "2026-06", "status": "available", "legacy_settled": False, "quantity": 180, "label_idr": 1800, "track_title_raw": "Song Beta", "artist_name_raw": "Artist Two", "platform": "Apple Music", "country": "US"},
        {"id": f"{PREFIX}-draft-hidden", "label_id": label_id, "period": "2026-06", "status": "draft", "legacy_settled": False, "quantity": 999999, "label_idr": 9999999, "track_title_raw": "Draft Hidden", "artist_name_raw": "Hidden", "platform": "Hidden", "country": "ZZ"},
        {"id": f"{PREFIX}-other-label", "label_id": other_label_id, "period": "2026-06", "status": "available", "legacy_settled": False, "quantity": 888888, "label_idr": 8888888, "track_title_raw": "Other Label Hidden", "artist_name_raw": "Other", "platform": "Other", "country": "OO"},
    ])

    database.withdraw_requests.insert_many([
        {"id": f"{PREFIX}-paid", "label_id": label_id, "status": "paid", "amount_idr": 1600, "legacy_import": False, "created_at": now, "updated_at": now},
        {"id": f"{PREFIX}-active", "label_id": label_id, "status": "approved", "amount_idr": 500, "legacy_import": False, "created_at": now, "updated_at": now},
    ])

    database.releases.insert_many([
        {"id": f"{PREFIX}-rel-1", "label_id": label_id, "release_title": "ITER34 Release One", "artist_name": "Artist One", "release_date": "2026-06-01", "status": "live", "created_at": now, "updated_at": now},
        {"id": f"{PREFIX}-rel-2", "label_id": label_id, "release_title": "ITER34 Release Two", "artist_name": "Artist Two", "release_date": "2026-05-01", "status": "approved", "created_at": now, "updated_at": now},
    ])

    payload = {
        "seeded": True,
        "label_email": email,
        "label_password": password,
        "label_id": label_id,
    }
    CTX_PATH.write_text(json.dumps(payload), encoding="utf-8")
    print(json.dumps(payload))


def cleanup() -> None:
    database = db()
    database.balance_transactions.delete_many({"id": {"$regex": f"^{PREFIX}"}})
    database.withdraw_requests.delete_many({"id": {"$regex": f"^{PREFIX}"}})
    database.royalty_lines.delete_many({"id": {"$regex": f"^{PREFIX}"}})
    database.releases.delete_many({"id": {"$regex": f"^{PREFIX}"}})
    database.labels.delete_many({"id": {"$regex": f"^{PREFIX}"}})
    database.users.delete_many({"id": {"$regex": f"^{PREFIX}"}})
    database.users.delete_many({"email": "iter34_ui_label@example.com"})
    CTX_PATH.unlink(missing_ok=True)
    print(json.dumps({"cleanup": "done"}))


if __name__ == "__main__":
    action = (sys.argv[1] if len(sys.argv) > 1 else "seed").strip().lower()
    if action == "seed":
        seed()
    elif action == "cleanup":
        cleanup()
    else:
        raise SystemExit("Usage: python /app/tests/iter34_seed_label_dashboard_ui.py [seed|cleanup]")
