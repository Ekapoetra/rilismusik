"""Seed/cleanup helper for iter31 analytics + royalty detail UI verification."""
import json
import os
import sys
from pathlib import Path

import pymongo
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
CTX_PATH = Path("/app/tests/iter31_seed_context.json")


def _db():
    client = pymongo.MongoClient(MONGO_URL)
    return client[DB_NAME]


def seed():
    db = _db()
    import_id = "c306c465-3a37-4bbf-a959-3fa8a3f53749"
    label_id = "ITER31_LABEL_ANALYTICS"

    db.labels.update_one(
        {"id": label_id},
        {"$set": {
            "id": label_id,
            "label_name": "ITER31 Label",
            "balance_pending_idr": 0,
            "balance_available_idr": 0,
            "updated_at": "2026-02-01T00:00:00+00:00",
        }},
        upsert=True,
    )

    db.royalty_imports.update_one(
        {"id": import_id},
        {"$set": {
            "id": import_id,
            "filename": "NOVEMBER 2023.csv",
            "status": "published",
            "period": "2023-11",
            "period_start": "2023-11",
            "period_end": "2023-11",
            "is_multi_period": False,
            "dana_received_at": "2026-01-01T00:00:00+00:00",
            "uploaded_by": "iter31-ui-seed",
            "updated_at": "2026-02-01T00:00:00+00:00",
        }},
        upsert=True,
    )

    db.royalty_lines.delete_many({"import_id": import_id, "id": {"$regex": "^ITER31-"}})
    db.royalty_lines.insert_many([
        {
            "id": "ITER31-STABLE-1",
            "import_id": import_id,
            "period": "2023-11",
            "row_period": "2023-11",
            "status": "available",
            "match_status": "matched",
            "label_id": label_id,
            "platform": "Spotify",
            "country": "ID",
            "quantity": 100,
            "revenue_eur": 2.0,
            "label_idr": 30000,
        }
    ])

    db.royalty_lines.delete_many({"id": {"$in": ["ITER31-AN-1", "ITER31-AN-2"]}})
    db.royalty_lines.insert_many([
        {
            "id": "ITER31-AN-1",
            "import_id": "ITER31-ANALYTICS",
            "period": "2026-05",
            "status": "available",
            "match_status": "matched",
            "label_id": label_id,
            "platform": "ITER31 Platform",
            "country": "ID",
            "quantity": 50,
            "revenue_eur": 1.0,
            "label_idr": 15000,
        },
        {
            "id": "ITER31-AN-2",
            "import_id": "ITER31-ANALYTICS",
            "period": "2026-06",
            "status": "available",
            "match_status": "matched",
            "label_id": label_id,
            "platform": "ITER31 Platform",
            "country": "ID",
            "quantity": 75,
            "revenue_eur": 1.5,
            "label_idr": 25000,
        },
    ])

    # Keep cache intentionally stale at 2026-05 only; periods endpoint should union with source.
    db.monthly_analytics.delete_many({"key": "ITER31 Platform"})
    db.monthly_analytics.insert_one({
        "period": "2026-05",
        "dim": "platform",
        "key": "ITER31 Platform",
        "revenue_eur": 1.0,
        "revenue_idr": 15000,
        "quantity": 50,
        "lines_count": 1,
    })

    CTX_PATH.write_text(json.dumps({"import_id": import_id, "label_id": label_id}), encoding="utf-8")
    print(json.dumps({"seeded": True, "import_id": import_id, "label_id": label_id}))


def cleanup():
    db = _db()
    import_id = "c306c465-3a37-4bbf-a959-3fa8a3f53749"
    label_id = "ITER31_LABEL_ANALYTICS"
    db.balance_transactions.delete_many({"reference_id": import_id})
    db.royalty_lines.delete_many({"id": {"$in": ["ITER31-STABLE-1", "ITER31-AN-1", "ITER31-AN-2"]}})
    db.royalty_imports.delete_one({"id": import_id, "uploaded_by": "iter31-ui-seed"})
    db.monthly_analytics.delete_many({"key": "ITER31 Platform"})
    db.labels.delete_one({"id": label_id})
    CTX_PATH.unlink(missing_ok=True)
    print(json.dumps({"cleanup": "done"}))


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "seed"
    if action == "seed":
        seed()
    elif action == "cleanup":
        cleanup()
    else:
        raise SystemExit(f"Unknown action: {action}")