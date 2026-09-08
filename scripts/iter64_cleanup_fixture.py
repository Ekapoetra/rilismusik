"""Cleanup iter64 temporary QA fixtures and uploaded references."""
import os
import asyncio
import sys

import pymongo
from dotenv import load_dotenv


load_dotenv("/app/backend/.env", override=True)
sys.path.append("/app/backend")
import storage_service


def main() -> None:
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    # UI label fixture cleanup
    label_id = "iter64-ui-label"
    user_id = "iter64-ui-user"
    release_ids = ["iter64-ui-release-a", "iter64-ui-release-b"]
    # Include only known Iter64 fixture labels, including orphaned test tickets from the initial run.
    tickets = list(db.support_tickets.find({"$or": [{"label_id": label_id}, {"label_id": {"$regex": r"^iter64-label-(owner|outsider)-[a-f0-9]{8}$"}}]}, {"_id": 0, "id": 1, "attachments": 1}))
    ticket_ids = [item["id"] for item in tickets]
    keys = {url.removeprefix("/api/files/") for item in tickets for url in item.get("attachments", []) if url.startswith("/api/files/ticket-")}

    if ticket_ids:
        db.ticket_comments.delete_many({"ticket_id": {"$in": ticket_ids}})
        db.notifications.delete_many({"meta.ticket_id": {"$in": ticket_ids}})
        db.activity_logs.delete_many({"reference_id": {"$in": ticket_ids}})
    db.support_tickets.delete_many({"id": {"$in": ticket_ids}})
    for key in keys:
        asyncio.run(storage_service.delete_object(key=key))

    db.tracks.delete_many({"release_id": {"$in": release_ids}})
    db.releases.delete_many({"id": {"$in": release_ids}})
    db.bank_accounts.delete_many({"id": "iter64-ui-bank"})
    db.contracts.delete_many({"id": "iter64-ui-contract"})
    db.kyc_documents.delete_many({"id": "iter64-ui-kyc"})
    db.labels.delete_many({"id": label_id})
    db.users.delete_many({"id": user_id})

    # Dynamic admin fixture leftovers from test file (if any)
    iter64_admins = list(db.users.find({"email": {"$regex": r"^iter64-viewonly-.*@example\.com$"}}, {"_id": 0, "id": 1}))
    for admin in iter64_admins:
        db.users.delete_one({"id": admin["id"]})
    db.admin_roles.delete_many({"name": {"$regex": r"^iter64-support-view-"}})

    print("iter64 cleanup completed")


if __name__ == "__main__":
    main()
