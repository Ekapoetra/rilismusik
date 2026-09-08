"""Seed temporary QA label fixture for Iter62 royalty-adjustment UI verification."""

import os
import sys
from datetime import datetime, timezone

import pymongo
from dotenv import load_dotenv

sys.path.append("/app/backend")
from auth_utils import hash_password


load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/backend/.env.test", override=True)

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

LABEL_ID = "iter62-ui-label"
USER_ID = "iter62-ui-label-user"
EMAIL = os.environ["TEST_ITER62_UI_EMAIL"]
PASSWORD = os.environ["TEST_ITER62_UI_PASSWORD"]


def main() -> None:
    db = pymongo.MongoClient(MONGO_URL)[DB_NAME]
    now = datetime.now(timezone.utc).isoformat()

    db.withdraw_requests.delete_many({"label_id": LABEL_ID})
    db.balance_transactions.delete_many({"label_id": LABEL_ID})
    db.royalty_adjustment_previews.delete_many({"label_id": LABEL_ID})
    db.royalty_lines.delete_many({"label_id": LABEL_ID})
    db.contracts.delete_many({"label_id": LABEL_ID})
    db.bank_accounts.delete_many({"label_id": LABEL_ID})
    db.kyc_documents.delete_many({"label_id": LABEL_ID})
    db.labels.delete_many({"id": LABEL_ID})
    db.users.delete_many({"$or": [{"id": USER_ID}, {"email": EMAIL}]})

    db.users.insert_one({
        "id": USER_ID,
        "name": "Iter62 UI Label",
        "email": EMAIL,
        "password_hash": hash_password(PASSWORD),
        "role": "label",
        "status": "active",
        "token_version": 0,
        "email_verified_at": now,
        "created_at": now,
        "updated_at": now,
    })
    db.labels.insert_one({
        "id": LABEL_ID,
        "user_id": USER_ID,
        "label_name": "Iter62 UI Label",
        "pic_name": "QA Iter62",
        "whatsapp": "+6281234567890",
        "address": "Jl. QA Iter62",
        "city": "Jakarta",
        "logo_storage_key": f"label-logo/{LABEL_ID}/logo.png",
        "account_status": "active",
        "kyc_status": "verified",
        "kyc_document_id": f"{LABEL_ID}-kyc",
        "kyc_verified_at": now,
        "bank_verified": True,
        "balance_pending_idr": 0,
        "balance_available_idr": 0,
        "balance_withdraw_requested_idr": 0,
        "created_at": now,
        "updated_at": now,
    })
    db.bank_accounts.insert_one({
        "id": f"{LABEL_ID}-bank",
        "label_id": LABEL_ID,
        "bank_name": "Bank QA",
        "account_number": "620000000162",
        "account_holder_name": "Iter62 UI Label",
        "verified_status": "verified",
        "verified_at": now,
        "created_at": now,
        "updated_at": now,
    })
    db.contracts.insert_one({
        "id": f"{LABEL_ID}-contract",
        "label_id": LABEL_ID,
        "status": "active",
        "file_url": "/api/files/contract/test.pdf",
        "filename": "test.pdf",
        "start_date": "2025-01-01",
        "end_date": "2030-01-01",
        "created_at": now,
        "updated_at": now,
    })
    db.kyc_documents.insert_one({
        "id": f"{LABEL_ID}-kyc",
        "label_id": LABEL_ID,
        "status": "verified",
        "is_current": True,
        "storage_key": f"kyc-private/{LABEL_ID}/ktp.pdf",
        "sha256": "iter62ui",
        "uploaded_at": now,
        "verified_at": now,
    })
    db.royalty_lines.insert_many([
        {
            "id": f"{LABEL_ID}-line-legacy",
            "label_id": LABEL_ID,
            "period": "2026-06",
            "status": "available",
            "legacy_settled": False,
            "label_idr": 900_000,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": f"{LABEL_ID}-line-excluded",
            "label_id": LABEL_ID,
            "period": "2026-05",
            "status": "available",
            "legacy_settled": True,
            "label_idr": 123_456,
            "created_at": now,
            "updated_at": now,
        },
    ])

    print(f"Seeded {LABEL_ID} / {EMAIL}")


if __name__ == "__main__":
    main()
