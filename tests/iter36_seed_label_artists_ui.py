"""Seed/cleanup temporary ITER36 label + artists for UI verification."""
import argparse
import json
import os
import secrets
import uuid
from pathlib import Path

import pymongo
from dotenv import load_dotenv

import sys
sys.path.append("/app/backend")
from auth_utils import hash_password


STATE_PATH = Path("/tmp/iter36_label_artists_ui_seed.json")


def _db():
    load_dotenv("/app/backend/.env", override=True)
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


def _password() -> str:
    return f"Iter36Ui#{secrets.token_hex(6)}Aa1"


def seed():
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    now = "2026-02-20T00:00:00+00:00"

    state = {
        "suffix": suffix,
        "user_id": f"iter36-ui-user-{suffix}",
        "label_id": f"iter36-ui-label-{suffix}",
        "other_label_id": f"iter36-ui-other-{suffix}",
        "active_artist_id": f"iter36-ui-artist-active-{suffix}",
        "paid_artist_id": f"iter36-ui-artist-paid-{suffix}",
        "email": f"iter36-ui-{suffix}@example.com",
        "password": _password(),
    }

    db.users.insert_one({
        "id": state["user_id"],
        "name": "ITER36 UI Label",
        "email": state["email"],
        "password_hash": hash_password(state["password"]),
        "role": "label",
        "status": "active",
        "email_verified_at": now,
        "created_at": now,
        "updated_at": now,
        "token_version": 0,
    })
    db.labels.insert_many([
        {
            "id": state["label_id"],
            "user_id": state["user_id"],
            "label_name": f"ITER36 UI Label {suffix}",
            "last_withdrawn_period": "2026-08",
            "account_status": "active",
            "subscription_status": "active",
            "contract_status": "contract_active",
            "payment_type": "annual_subscription",
            "bank_verified": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": state["other_label_id"],
            "label_name": f"ITER36 UI Other Label {suffix}",
            "created_at": now,
            "updated_at": now,
        },
    ])
    db.artists.insert_many([
        {
            "id": state["active_artist_id"],
            "label_id": state["label_id"],
            "artist_name": "ITER36 Active Artist Name That Is Intentionally Very Very Long To Test Overflow Behavior",
            "email": f"iter36-active-{suffix}@example.com",
            "status": "active",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": state["paid_artist_id"],
            "label_id": state["label_id"],
            "artist_name": "ITER36 Paid Artist",
            "email": f"iter36-paid-{suffix}@example.com",
            "status": "active",
            "created_at": now,
            "updated_at": now,
        },
    ])
    db.royalty_lines.insert_many([
        {"id": f"iter36-ui-cutoff-{suffix}", "label_id": state["label_id"], "artist_id": state["active_artist_id"], "period": "2026-08", "status": "pending", "legacy_settled": False, "label_idr": 100_000, "revenue_eur": 10},
        {"id": f"iter36-ui-pending-{suffix}", "label_id": state["label_id"], "artist_id": state["active_artist_id"], "period": "2026-09", "status": "pending", "legacy_settled": False, "label_idr": 1_250_000_000, "revenue_eur": 125_000},
        {"id": f"iter36-ui-available-{suffix}", "label_id": state["label_id"], "artist_id": state["active_artist_id"], "period": "2026-10", "status": "available", "legacy_settled": False, "label_idr": 2_750_000_000, "revenue_eur": 275_000},
        {"id": f"iter36-ui-withdrawn-{suffix}", "label_id": state["label_id"], "artist_id": state["active_artist_id"], "period": "2026-10", "status": "withdrawn", "legacy_settled": False, "label_idr": 9_999_000_000, "revenue_eur": 999_900},
        {"id": f"iter36-ui-draft-{suffix}", "label_id": state["label_id"], "artist_id": state["active_artist_id"], "period": "2026-10", "status": "draft", "legacy_settled": False, "label_idr": 8_888_000_000, "revenue_eur": 888_800},
        {"id": f"iter36-ui-legacy-{suffix}", "label_id": state["label_id"], "artist_id": state["active_artist_id"], "period": "2026-10", "status": "available", "legacy_settled": True, "label_idr": 7_777_000_000, "revenue_eur": 777_700},
        {"id": f"iter36-ui-other-label-{suffix}", "label_id": state["other_label_id"], "artist_id": state["active_artist_id"], "period": "2026-10", "status": "available", "legacy_settled": False, "label_idr": 6_666_000_000, "revenue_eur": 666_600},
        {"id": f"iter36-ui-paid-only-{suffix}", "label_id": state["label_id"], "artist_id": state["paid_artist_id"], "period": "2026-10", "status": "withdrawn", "legacy_settled": False, "label_idr": 555_000_000, "revenue_eur": 55_500},
    ])

    STATE_PATH.write_text(json.dumps(state), encoding="utf-8")
    print(str(STATE_PATH))


def cleanup():
    if not STATE_PATH.exists():
        print("state_not_found")
        return
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    db = _db()
    suffix = state["suffix"]
    db.royalty_lines.delete_many({"id": {"$regex": f"^iter36-ui-.*-{suffix}$"}})
    db.artists.delete_many({"id": {"$in": [state["active_artist_id"], state["paid_artist_id"]]}})
    db.labels.delete_many({"id": {"$in": [state["label_id"], state["other_label_id"]]}})
    db.users.delete_one({"id": state["user_id"]})
    STATE_PATH.unlink(missing_ok=True)
    print("cleaned")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["seed", "cleanup"])
    args = parser.parse_args()
    if args.action == "seed":
        seed()
    else:
        cleanup()
