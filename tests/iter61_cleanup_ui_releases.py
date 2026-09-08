"""Cleanup isolated admin release fixtures for Iter 61 UI tests."""
import os

import pymongo
from dotenv import load_dotenv


load_dotenv("/app/backend/.env", override=True)
db = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

db.notifications.delete_many({"meta.release_id": {"$regex": r"^iter61-ui-"}})
db.activity_logs.delete_many({"reference_id": {"$regex": r"^iter61-ui-"}})
db.tracks.delete_many({"release_id": {"$regex": r"^iter61-ui-"}})
db.releases.delete_many({"id": {"$regex": r"^iter61-ui-"}})
db.payments.delete_many({"release_id": {"$regex": r"^iter61-ui-"}})
db.labels.delete_one({"id": "iter61-ui-label-a"})

print("Cleaned iter61 UI releases")
