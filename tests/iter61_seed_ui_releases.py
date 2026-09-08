"""Seed isolated admin release fixtures for Iter 61 UI deletion tests."""
import os

import pymongo
from dotenv import load_dotenv


load_dotenv("/app/backend/.env", override=True)

db = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
now = "2026-02-10T00:00:00+00:00"

release_rows = [
    {"id": "iter61-ui-draft-main", "label_id": "iter61-ui-label-a", "release_title": "ITER61 UI Draft Main", "status": "draft", "release_type": "single", "artist_name": "QA Artist", "release_date": "2026-03-10", "created_at": now, "updated_at": now},
    {"id": "iter61-ui-rejected-main", "label_id": "iter61-ui-label-a", "release_title": "ITER61 UI Rejected Main", "status": "rejected", "release_type": "single", "artist_name": "QA Artist", "release_date": "2026-03-11", "created_at": now, "updated_at": now},
    {"id": "iter61-ui-submitted-main", "label_id": "iter61-ui-label-a", "release_title": "ITER61 UI Submitted Main", "status": "submitted", "release_type": "single", "artist_name": "QA Artist", "release_date": "2026-03-12", "created_at": now, "updated_at": now},
    {"id": "iter61-ui-draft-intercept", "label_id": "iter61-ui-label-a", "release_title": "ITER61 UI Draft Intercept", "status": "draft", "release_type": "single", "artist_name": "QA Artist", "release_date": "2026-03-13", "created_at": now, "updated_at": now},
]

db.tracks.delete_many({"release_id": {"$regex": r"^iter61-ui-"}})
db.releases.delete_many({"id": {"$regex": r"^iter61-ui-"}})
db.activity_logs.delete_many({"reference_id": {"$regex": r"^iter61-ui-"}})

db.labels.update_one(
    {"id": "iter61-ui-label-a"},
    {"$set": {"id": "iter61-ui-label-a", "label_name": "ITER61 QA Label", "updated_at": now}, "$setOnInsert": {"created_at": now}},
    upsert=True,
)

for release in release_rows:
    db.releases.insert_one(release)
    db.tracks.insert_one({
        "id": f"iter61-ui-track-{release['id']}",
        "release_id": release["id"],
        "label_id": release["label_id"],
        "track_title": f"Track {release['id']}",
        "track_number": 1,
        "audio_url": f"/api/files/{release['id']}.wav",
        "created_at": now,
        "updated_at": now,
    })

print("Seeded iter61 UI releases:", [r["id"] for r in release_rows])
