"""Emit one delayed notification for iter66 UI sound verification."""

import os
import sys
import time
from datetime import datetime, timezone

import pymongo
from dotenv import load_dotenv


def main(delay_seconds: int = 3):
    load_dotenv("/app/backend/.env", override=True)
    load_dotenv("/app/backend/.env.test", override=True)
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    super_email = (os.environ.get("TEST_SUPERADMIN_EMAIL") or "").replace('"', "")
    user = db.users.find_one({"email": super_email}, {"_id": 0, "id": 1})
    if not user or not user.get("id"):
        raise RuntimeError("Super admin user not found")

    time.sleep(delay_seconds)
    notif_id = f"iter66-live-notif-{int(time.time())}"
    db.notifications.insert_one(
        {
            "id": notif_id,
            "user_id": user["id"],
            "type": "system_alert",
            "title": "Iter66 delayed notification",
            "body": "Sound verification event",
            "link": "/admin/dashboard",
            "meta": {"iter": 66, "owned": True, "kind": "delayed"},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "read_at": None,
        }
    )
    print(notif_id)


if __name__ == "__main__":
    delay = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    main(delay)
