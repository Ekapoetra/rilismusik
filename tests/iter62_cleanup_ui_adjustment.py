"""Cleanup temporary Iter62 royalty-adjustment UI fixtures."""

import os

import pymongo
from dotenv import load_dotenv


load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/backend/.env.test", override=True)

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

LABEL_ID = "iter62-ui-label"
USER_ID = "iter62-ui-label-user"
EMAIL = os.environ["TEST_ITER62_UI_EMAIL"]


def main() -> None:
    db = pymongo.MongoClient(MONGO_URL)[DB_NAME]
    ui_admin_email = os.environ["TEST_ITER63_UI_ADMIN_EMAIL"]
    ui_admin = db.users.find_one({"email": ui_admin_email}, {"_id": 0, "id": 1, "admin_role_id": 1})
    if ui_admin:
        db.users.delete_one({"id": ui_admin["id"], "email": ui_admin_email})
        db.admin_roles.delete_one({"id": ui_admin.get("admin_role_id"), "name": "Iter63 UI Royalty Manage"})
        db.activity_logs.delete_many({"$or": [{"user_id": ui_admin["id"]}, {"reference_id": {"$in": [ui_admin["id"], ui_admin.get("admin_role_id")]}}]})
        db.notifications.delete_many({"user_id": ui_admin["id"]})
    refs = [item["id"] for item in db.balance_transactions.find({"label_id": LABEL_ID}, {"_id": 0, "id": 1})]
    refs += [item["id"] for item in db.withdraw_requests.find({"label_id": LABEL_ID}, {"_id": 0, "id": 1})]
    db.financial_operation_locks.delete_many({"_id": LABEL_ID})
    db.withdraw_requests.delete_many({"label_id": LABEL_ID})
    db.balance_transactions.delete_many({"label_id": LABEL_ID})
    db.royalty_adjustment_previews.delete_many({"label_id": LABEL_ID})
    db.royalty_lines.delete_many({"label_id": LABEL_ID})
    db.contracts.delete_many({"label_id": LABEL_ID})
    db.bank_accounts.delete_many({"label_id": LABEL_ID})
    db.kyc_documents.delete_many({"label_id": LABEL_ID})
    db.labels.delete_many({"id": LABEL_ID})
    db.users.delete_many({"$or": [{"id": USER_ID}, {"email": EMAIL}]})
    db.notifications.delete_many({"user_id": USER_ID})
    db.activity_logs.delete_many({"$or": [
        {"reference_id": {"$in": refs + [LABEL_ID]}},
        {"user_id": USER_ID},
    ]})
    print(f"Cleaned {LABEL_ID}")


if __name__ == "__main__":
    main()
