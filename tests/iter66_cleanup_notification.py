import os
import sys

import pymongo
from dotenv import load_dotenv


def main(notification_id: str):
    load_dotenv("/app/backend/.env", override=True)
    db = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    result = db.notifications.delete_many({"id": notification_id})
    print(result.deleted_count)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python /app/tests/iter66_cleanup_notification.py <notification_id>")
    main(sys.argv[1])
