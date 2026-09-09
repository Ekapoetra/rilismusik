"""Iter67 UI fixture seed/cleanup for release artist + package manager UI verification."""

import json
import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pymongo
import requests
from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")

from auth_utils import hash_password


STATE_PATH = Path("/app/tests/iter67_ui_fixture_state.json")
CREDS_PATH = Path("/app/memory/test_credentials.md")


def _load_env():
    load_dotenv("/app/backend/.env", override=True)
    load_dotenv("/app/backend/.env.test", override=True)
    load_dotenv("/app/frontend/.env", override=True)


def _api_base() -> str:
    return os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _login(email: str, password: str) -> str:
    response = requests.post(
        f"{_api_base()}/auth/login",
        json={"email": email, "password": password},
        timeout=40,
    )
    response.raise_for_status()
    token = response.json().get("access_token")
    if not token:
        raise RuntimeError("Login success without access_token")
    return token


def _append_credential(line: str):
    with CREDS_PATH.open("a", encoding="utf-8") as stream:
        stream.write(f"\n- {line} — ACTIVE QA\n")


def _retire_credential(email: str):
    if not CREDS_PATH.exists():
        return
    lines = CREDS_PATH.read_text(encoding="utf-8").splitlines()
    updated = []
    for line in lines:
        if f"`{email}`" in line and "ACTIVE QA" in line:
            updated.append(line.replace("ACTIVE QA", "REMOVED (fixture teardown)"))
        else:
            updated.append(line)
    CREDS_PATH.write_text("\n".join(updated) + "\n", encoding="utf-8")


def seed():
    _load_env()
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc).isoformat()

    label_user_id = f"iter67-ui-user-{suffix}"
    label_id = f"iter67-ui-label-{suffix}"
    label_email = f"iter67-ui-label-{suffix}@example.com"
    label_password = f"Iter67Ui#{suffix}Aa!"
    kyc_id = f"iter67-ui-kyc-{suffix}"
    bank_id = f"iter67-ui-bank-{suffix}"
    contract_id = f"iter67-ui-contract-{suffix}"

    db.users.insert_one(
        {
            "id": label_user_id,
            "name": f"Iter67 Label {suffix}",
            "email": label_email,
            "password_hash": hash_password(label_password),
            "role": "label",
            "status": "active",
            "token_version": 0,
            "email_verified_at": now,
            "created_at": now,
            "updated_at": now,
        }
    )
    db.labels.insert_one(
        {
            "id": label_id,
            "user_id": label_user_id,
            "label_name": f"Iter67 Label Package {suffix}",
            "pic_name": "Iter67 PIC",
            "email": label_email,
            "whatsapp": "081299990000",
            "address": "Jl. Iter67",
            "city": "Jakarta",
            "country": "Indonesia",
            "logo_storage_key": f"label-logo/{label_id}.png",
            "account_status": "active",
            "payment_type": "pay_per_release",
            "subscription_status": "inactive",
            "subscription_tier": None,
            "subscription_expires_at": None,
            "royalty_percentage_default": 60,
            "contract_status": "active",
            "kyc_status": "verified",
            "kyc_document_id": kyc_id,
            "bank_verified": True,
            "package_revision": 0,
            "balance_available_idr": 0,
            "balance_pending_idr": 0,
            "balance_withdraw_requested_idr": 0,
            "created_at": now,
            "updated_at": now,
        }
    )
    db.kyc_documents.insert_one(
        {
            "id": kyc_id,
            "label_id": label_id,
            "storage_key": f"kyc-private/{label_id}/ktp.png",
            "status": "verified",
            "is_current": True,
            "uploaded_at": now,
            "reviewed_at": now,
        }
    )
    db.bank_accounts.insert_one(
        {
            "id": bank_id,
            "label_id": label_id,
            "bank_name": "BCA",
            "account_number": f"7777{suffix}",
            "account_holder_name": "Iter67 PIC",
            "verified_status": "verified",
            "created_at": now,
            "updated_at": now,
        }
    )
    db.contracts.insert_one(
        {
            "id": contract_id,
            "label_id": label_id,
            "status": "active",
            "file_url": "/api/files/contract/iter67-ui.pdf",
            "filename": "iter67-ui.pdf",
            "start_date": "2026-01-01",
            "end_date": "2030-12-31",
            "created_at": now,
            "updated_at": now,
        }
    )

    release_main_id = f"iter67-ui-release-main-{suffix}"
    release_zero_id = f"iter67-ui-release-zero-{suffix}"
    future_date = (date.today() + timedelta(days=14)).isoformat()
    very_long_primary = "SangatPanjangNamaArtisUtamaPertamaTanpaTruncateIter67"
    very_long_featured = "FeaturingNamaArtisSangatPanjangKeduaIter67"
    db.releases.insert_many(
        [
            {
                "id": release_main_id,
                "label_id": label_id,
                "release_title": f"Iter67 UI Metadata Test {suffix}",
                "artist_name": "",
                "primary_artists": [{"name": very_long_primary}],
                "featured_artists": [{"name": very_long_featured}],
                "release_type": "single",
                "release_date": future_date,
                "status": "draft",
                "upc": "0011112222333",
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": release_zero_id,
                "label_id": label_id,
                "release_title": f"Iter67 UI Zero Track {suffix}",
                "artist_name": "No Track",
                "primary_artists": [{"name": "No Track"}],
                "featured_artists": [],
                "release_type": "single",
                "release_date": future_date,
                "status": "draft",
                "upc": "0000000099999",
                "created_at": now,
                "updated_at": now,
            },
        ]
    )
    db.tracks.insert_many(
        [
            {
                "id": f"iter67-ui-track-2-{suffix}",
                "release_id": release_main_id,
                "label_id": label_id,
                "track_number": 2,
                "track_title": "Track Dua",
                "isrc": "IDAAA2601002",
                "artist_name": very_long_primary,
                "primary_artists": [{"name": very_long_primary}],
                "featured_artists": [{"name": very_long_featured}],
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": f"iter67-ui-track-1-{suffix}",
                "release_id": release_main_id,
                "label_id": label_id,
                "track_number": 1,
                "track_title": "Track Satu",
                "isrc": "",
                "artist_name": very_long_primary,
                "primary_artists": [{"name": very_long_primary}],
                "featured_artists": [{"name": very_long_featured}],
                "created_at": now,
                "updated_at": now,
            },
        ]
    )

    super_email = os.environ.get("TEST_SUPERADMIN_EMAIL", "superadmin@rilismusik.com").strip().replace('"', "")
    super_password = os.environ.get("TEST_SUPERADMIN_PASSWORD", "SuperAdmin#2026").strip().replace('"', "")
    super_token = _login(super_email, super_password)

    manager_email = f"iter67-ui-manager-{suffix}@example.com"
    manager_password = f"Iter67Mgr#{suffix}Aa!"
    manager_create = requests.post(
        f"{_api_base()}/admin/admin-users",
        headers={"Authorization": f"Bearer {super_token}"},
        json={
            "name": f"Iter67 Package Manager {suffix}",
            "email": manager_email,
            "password": manager_password,
            "admin_role_id": "admin_package_manager",
        },
        timeout=40,
    )
    manager_create.raise_for_status()
    manager_user_id = manager_create.json()["id"]

    _append_credential(f"Iter67 fixture label `{label_email}` / `{label_password}`")
    _append_credential(f"Iter67 fixture package-manager `{manager_email}` / `{manager_password}`")

    state = {
        "suffix": suffix,
        "label": {
            "id": label_id,
            "user_id": label_user_id,
            "email": label_email,
            "password": label_password,
            "release_main_id": release_main_id,
            "release_zero_id": release_zero_id,
            "long_primary": very_long_primary,
            "long_featured": very_long_featured,
        },
        "manager": {"id": manager_user_id, "email": manager_email, "password": manager_password},
        "refs": {"kyc_id": kyc_id, "bank_id": bank_id, "contract_id": contract_id},
    }
    STATE_PATH.write_text(json.dumps(state), encoding="utf-8")
    print(json.dumps({"ok": True, "state_path": str(STATE_PATH), "label_id": label_id, "manager_id": manager_user_id}))


def cleanup():
    _load_env()
    if not STATE_PATH.exists():
        print(json.dumps({"ok": True, "message": "no_state"}))
        return
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    db = _db()

    super_email = os.environ.get("TEST_SUPERADMIN_EMAIL", "superadmin@rilismusik.com").strip().replace('"', "")
    super_password = os.environ.get("TEST_SUPERADMIN_PASSWORD", "SuperAdmin#2026").strip().replace('"', "")
    super_token = _login(super_email, super_password)

    manager = state.get("manager") or {}
    if manager.get("id"):
        requests.delete(
            f"{_api_base()}/admin/admin-users/{manager['id']}",
            headers={"Authorization": f"Bearer {super_token}"},
            timeout=40,
        )
    if manager.get("email"):
        db.users.delete_many({"email": manager["email"]})
        _retire_credential(manager["email"])

    label = state.get("label") or {}
    label_id = label.get("id")
    user_id = label.get("user_id")
    release_ids = [value for value in [label.get("release_main_id"), label.get("release_zero_id")] if value]

    if release_ids:
        db.notifications.delete_many({"meta.release_id": {"$in": release_ids}})
        db.activity_logs.delete_many({"reference_id": {"$in": release_ids}})
        db.tracks.delete_many({"release_id": {"$in": release_ids}})
        db.releases.delete_many({"id": {"$in": release_ids}})
        db.payments.delete_many({"release_id": {"$in": release_ids}})

    if label_id:
        db.notifications.delete_many({"$or": [{"user_id": user_id}, {"meta.label_id": label_id}]})
        db.activity_logs.delete_many({"$or": [{"reference_id": label_id}, {"user_id": user_id}]})
        db.royalty_percentage_history.delete_many({"label_id": label_id})
        db.migrate_jobs.delete_many({"label_id": label_id})
        db.withdraw_requests.delete_many({"label_id": label_id})
        db.balance_transactions.delete_many({"label_id": label_id})
        db.royalty_lines.delete_many({"label_id": label_id})
        db.bank_accounts.delete_many({"label_id": label_id})
        db.contracts.delete_many({"label_id": label_id})
        db.kyc_documents.delete_many({"label_id": label_id})
        db.labels.delete_many({"id": label_id})
    if user_id:
        db.auth_sessions.delete_many({"user_id": user_id})
        db.users.delete_many({"id": user_id})
    if label.get("email"):
        _retire_credential(label["email"])

    STATE_PATH.unlink(missing_ok=True)
    print(json.dumps({"ok": True, "message": "cleaned"}))


if __name__ == "__main__":
    action = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
    if action == "seed":
        seed()
    elif action == "cleanup":
        cleanup()
    else:
        raise SystemExit("Usage: python /app/tests/iter67_ui_fixture.py [seed|cleanup]")
