"""Temporary UI fixture for iteration 57 (seed/cleanup)."""
import json
import os
import sys
import uuid
from datetime import datetime, timezone

import pymongo
from dotenv import load_dotenv


STATE_PATH = "/app/tests/iter57_ui_fixture_state.json"


def _db():
    load_dotenv("/app/backend/.env", override=True)
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def seed() -> None:
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    label_id = f"iter57-ui-label-{suffix}"
    now_iso = datetime.now(timezone.utc).isoformat()
    withdraw_ids = [f"iter57-ui-wd-old-{suffix}", f"iter57-ui-wd-new-{suffix}"]

    db.labels.insert_one({
        "id": label_id,
        "label_name": f"Demo Label PPR UI {suffix}",
        "email": f"iter57-ui-{suffix}@example.com",
        "created_at": now_iso,
        "updated_at": now_iso,
    })
    db.withdraw_requests.insert_many([
        {
            "id": withdraw_ids[0],
            "label_id": label_id,
            "status": "requested",
            "amount_idr": 125000,
            "request_date": "2024-05-10T00:00:00+07:00",
            "created_at": "2024-05-10T00:00:00+07:00",
            "updated_at": now_iso,
        },
        {
            "id": withdraw_ids[1],
            "label_id": label_id,
            "status": "requested",
            "amount_idr": 245000,
            "request_date": "2026-09-12T00:00:00+07:00",
            "created_at": "2026-09-12T00:00:00+07:00",
            "updated_at": now_iso,
        },
    ])

    with open(STATE_PATH, "w", encoding="utf-8") as handle:
        json.dump({"label_id": label_id, "withdraw_ids": withdraw_ids}, handle)
    print(f"seeded:{label_id}")


def cleanup() -> None:
    db = _db()
    if not os.path.exists(STATE_PATH):
        print("no_state")
        return
    with open(STATE_PATH, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    db.withdraw_requests.delete_many({"id": {"$in": data.get("withdraw_ids", [])}})
    if data.get("label_id"):
        db.labels.delete_many({"id": data["label_id"]})
    os.remove(STATE_PATH)
    print("cleaned")


if __name__ == "__main__":
    action = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
    if action == "seed":
        seed()
    elif action == "cleanup":
        cleanup()
    else:
        raise SystemExit("Usage: python /app/tests/iter57_ui_fixture.py [seed|cleanup]")
