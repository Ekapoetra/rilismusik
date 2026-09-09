"""Iter 67 — release artist metadata + admin package/RBAC regression coverage."""

import asyncio
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import pymongo
import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from auth_utils import hash_password
from tests.support_config import FINANCE, SUPERADMIN, SUPPORT, temporary_password


load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/frontend/.env", override=True)

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _login(email: str, password: str):
    response = requests.post(
        f"{API}/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    assert response.status_code == 200, response.text
    token = response.json().get("access_token")
    assert isinstance(token, str) and token
    return response, token


def _headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _seed_label_fixture(db, prefix: str):
    """modules/features: isolated fixture label/users/releases/artists/tracks for iter67 coverage."""
    suffix = uuid.uuid4().hex[:8]
    now = _iso_now()

    owner_user_id = f"{prefix}-user-owner-{suffix}"
    owner_label_id = f"{prefix}-label-owner-{suffix}"
    owner_email = f"{prefix}-owner-{suffix}@example.com"
    owner_password = temporary_password("Iter67Owner")
    owner_kyc_id = f"{prefix}-kyc-owner-{suffix}"

    other_user_id = f"{prefix}-user-other-{suffix}"
    other_label_id = f"{prefix}-label-other-{suffix}"
    other_email = f"{prefix}-other-{suffix}@example.com"
    other_password = temporary_password("Iter67Other")
    other_kyc_id = f"{prefix}-kyc-other-{suffix}"

    db.users.insert_many([
        {
            "id": owner_user_id,
            "name": f"Iter67 Owner {suffix}",
            "email": owner_email,
            "password_hash": hash_password(owner_password),
            "role": "label",
            "status": "active",
            "token_version": 0,
            "email_verified_at": now,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": other_user_id,
            "name": f"Iter67 Other {suffix}",
            "email": other_email,
            "password_hash": hash_password(other_password),
            "role": "label",
            "status": "active",
            "token_version": 0,
            "email_verified_at": now,
            "created_at": now,
            "updated_at": now,
        },
    ])

    db.labels.insert_many([
        {
            "id": owner_label_id,
            "user_id": owner_user_id,
            "label_name": f"Iter67 Owner Label {suffix}",
            "pic_name": "Owner PIC",
            "email": owner_email,
            "whatsapp": "081234567800",
            "address": "Jl. Iter67 Owner",
            "city": "Jakarta",
            "country": "Indonesia",
            "logo_storage_key": f"label-logo/{owner_label_id}.png",
            "account_status": "active",
            "payment_type": "pay_per_release",
            "subscription_status": "inactive",
            "subscription_tier": None,
            "subscription_expires_at": None,
            "royalty_percentage_default": 60.0,
            "contract_status": "active",
            "kyc_status": "verified",
            "kyc_document_id": owner_kyc_id,
            "balance_available_idr": 0,
            "balance_pending_idr": 0,
            "balance_withdraw_requested_idr": 0,
            "package_revision": 0,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": other_label_id,
            "user_id": other_user_id,
            "label_name": f"Iter67 Other Label {suffix}",
            "pic_name": "Other PIC",
            "email": other_email,
            "whatsapp": "081234567801",
            "address": "Jl. Iter67 Other",
            "city": "Bandung",
            "country": "Indonesia",
            "logo_storage_key": f"label-logo/{other_label_id}.png",
            "account_status": "active",
            "payment_type": "pay_per_release",
            "subscription_status": "inactive",
            "subscription_tier": None,
            "subscription_expires_at": None,
            "royalty_percentage_default": 60.0,
            "contract_status": "active",
            "kyc_status": "verified",
            "kyc_document_id": other_kyc_id,
            "balance_available_idr": 0,
            "balance_pending_idr": 0,
            "balance_withdraw_requested_idr": 0,
            "package_revision": 0,
            "created_at": now,
            "updated_at": now,
        },
    ])

    db.kyc_documents.insert_many([
        {
            "id": owner_kyc_id,
            "label_id": owner_label_id,
            "status": "verified",
            "is_current": True,
            "storage_key": f"kyc-private/{owner_label_id}/ktp.png",
            "uploaded_at": now,
            "reviewed_at": now,
        },
        {
            "id": other_kyc_id,
            "label_id": other_label_id,
            "status": "verified",
            "is_current": True,
            "storage_key": f"kyc-private/{other_label_id}/ktp.png",
            "uploaded_at": now,
            "reviewed_at": now,
        },
    ])

    db.bank_accounts.insert_many([
        {
            "id": f"{prefix}-bank-owner-{suffix}",
            "label_id": owner_label_id,
            "bank_name": "Bank QA",
            "account_number": f"9900{suffix}",
            "account_holder_name": "Owner PIC",
            "verified_status": "verified",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": f"{prefix}-bank-other-{suffix}",
            "label_id": other_label_id,
            "bank_name": "Bank QA",
            "account_number": f"8800{suffix}",
            "account_holder_name": "Other PIC",
            "verified_status": "verified",
            "created_at": now,
            "updated_at": now,
        },
    ])

    db.contracts.insert_many([
        {
            "id": f"{prefix}-contract-owner-{suffix}",
            "label_id": owner_label_id,
            "status": "active",
            "file_url": "/api/files/contract/iter67-owner.pdf",
            "filename": "iter67-owner.pdf",
            "start_date": "2026-01-01",
            "end_date": "2030-01-01",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": f"{prefix}-contract-other-{suffix}",
            "label_id": other_label_id,
            "status": "active",
            "file_url": "/api/files/contract/iter67-other.pdf",
            "filename": "iter67-other.pdf",
            "start_date": "2026-01-01",
            "end_date": "2030-01-01",
            "created_at": now,
            "updated_at": now,
        },
    ])

    owner_artist_id = f"{prefix}-artist-owner-{suffix}"
    owner_feat_id = f"{prefix}-artist-owner-feat-{suffix}"
    foreign_artist_id = f"{prefix}-artist-foreign-{suffix}"
    db.artists.insert_many([
        {"id": owner_artist_id, "label_id": owner_label_id, "artist_name": "Owner Main", "created_at": now, "updated_at": now},
        {"id": owner_feat_id, "label_id": owner_label_id, "artist_name": "Owner Feat", "created_at": now, "updated_at": now},
        {"id": foreign_artist_id, "label_id": other_label_id, "artist_name": "Foreign Artist", "created_at": now, "updated_at": now},
    ])

    release_main = f"{prefix}-release-main-{suffix}"
    release_nocredit = f"{prefix}-release-nocredit-{suffix}"
    release_zero_tracks = f"{prefix}-release-zerotrack-{suffix}"
    release_other = f"{prefix}-release-other-{suffix}"
    future_date = (date.today() + timedelta(days=14)).isoformat()

    db.releases.insert_many([
        {
            "id": release_main,
            "label_id": owner_label_id,
            "release_title": f"Iter67 Legacy Metadata {suffix}",
            "artist_name": "",
            "primary_artists": [],
            "featured_artists": [{"name": "FeatOne"}, {"name": "featone"}],
            "release_type": "single",
            "release_date": future_date,
            "status": "draft",
            "upc": "001234560000",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": release_nocredit,
            "label_id": owner_label_id,
            "release_title": f"Iter67 No Credit {suffix}",
            "artist_name": "",
            "primary_artists": [],
            "featured_artists": [],
            "release_type": "single",
            "release_date": future_date,
            "status": "draft",
            "upc": "000000000999",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": release_zero_tracks,
            "label_id": owner_label_id,
            "release_title": f"Iter67 Zero Track {suffix}",
            "artist_name": "Alpha",
            "primary_artists": [{"name": "Alpha"}],
            "featured_artists": [],
            "release_type": "single",
            "release_date": future_date,
            "status": "draft",
            "upc": "000000000111",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": release_other,
            "label_id": other_label_id,
            "release_title": f"Iter67 Other Scope {suffix}",
            "artist_name": "Should Not Leak",
            "primary_artists": [{"name": "Should Not Leak"}],
            "featured_artists": [],
            "release_type": "single",
            "release_date": future_date,
            "status": "draft",
            "upc": "000000000222",
            "created_at": now,
            "updated_at": now,
        },
    ])

    db.tracks.insert_many([
        {
            "id": f"{prefix}-track-main-2-{suffix}",
            "release_id": release_main,
            "label_id": owner_label_id,
            "track_number": 2,
            "track_title": "Track Two",
            "artist_name": "Legacy Primary",
            "isrc": "IDAAA2600002",
            "primary_artists": [{"name": "ALPHA"}, {"artist_id": owner_artist_id}, {"artist_id": foreign_artist_id}],
            "featured_artists": [{"artist_id": owner_feat_id}],
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": f"{prefix}-track-main-1-{suffix}",
            "release_id": release_main,
            "label_id": owner_label_id,
            "track_number": 1,
            "track_title": "Track One",
            "artist_name": "Alpha",
            "isrc": "",
            "primary_artists": [],
            "featured_artists": [{"name": "FeatTwo"}, {"name": "feattwo"}],
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": f"{prefix}-track-other-1-{suffix}",
            "release_id": release_other,
            "label_id": other_label_id,
            "track_number": 1,
            "track_title": "Leak Guard Track",
            "artist_name": "Other",
            "isrc": "IDAAA2600999",
            "primary_artists": [{"name": "Other"}],
            "featured_artists": [],
            "created_at": now,
            "updated_at": now,
        },
    ])

    return {
        "suffix": suffix,
        "owner": {"user_id": owner_user_id, "label_id": owner_label_id, "email": owner_email, "password": owner_password},
        "other": {"user_id": other_user_id, "label_id": other_label_id, "email": other_email, "password": other_password},
        "release_ids": [release_main, release_nocredit, release_zero_tracks, release_other],
        "artist_ids": [owner_artist_id, owner_feat_id, foreign_artist_id],
    }


def _cleanup_fixture(db, fixture: dict):
    owner = fixture["owner"]
    other = fixture["other"]
    label_ids = [owner["label_id"], other["label_id"]]
    user_ids = [owner["user_id"], other["user_id"]]

    db.activity_logs.delete_many({"$or": [{"reference_id": {"$in": label_ids + fixture["release_ids"]}}, {"user_id": {"$in": user_ids}}]})
    db.notifications.delete_many({"user_id": {"$in": user_ids}})
    db.royalty_percentage_history.delete_many({"label_id": {"$in": label_ids}})
    db.migrate_jobs.delete_many({"label_id": {"$in": label_ids}})
    db.payments.delete_many({"label_id": {"$in": label_ids}})
    db.withdraw_requests.delete_many({"label_id": {"$in": label_ids}})
    db.balance_transactions.delete_many({"label_id": {"$in": label_ids}})
    db.royalty_lines.delete_many({"label_id": {"$in": label_ids}})
    db.tracks.delete_many({"label_id": {"$in": label_ids}})
    db.releases.delete_many({"id": {"$in": fixture["release_ids"]}})
    db.artists.delete_many({"id": {"$in": fixture["artist_ids"]}})
    db.kyc_documents.delete_many({"label_id": {"$in": label_ids}})
    db.bank_accounts.delete_many({"label_id": {"$in": label_ids}})
    db.contracts.delete_many({"label_id": {"$in": label_ids}})
    db.labels.delete_many({"id": {"$in": label_ids}})
    db.users.delete_many({"id": {"$in": user_ids}})


# modules/features: auth playbook sanity (cookies, bcrypt prefix, CORS credentials, brute-force lockout)
def test_auth_cookie_bcrypt_cors_and_lockout_sanity():
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    user_id = f"iter67-auth-user-{suffix}"
    email = f"iter67-auth-{suffix}@example.com"
    password = temporary_password("Iter67Auth")
    now = _iso_now()
    db.users.insert_one(
        {
            "id": user_id,
            "name": "Iter67 Auth",
            "email": email,
            "password_hash": hash_password(password),
            "role": "label",
            "status": "active",
            "token_version": 0,
            "email_verified_at": now,
            "created_at": now,
            "updated_at": now,
        }
    )
    try:
        user = db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 1})
        assert isinstance((user or {}).get("password_hash"), str)
        assert user["password_hash"].startswith("$2b$")

        login = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
        assert login.status_code == 200, login.text
        set_cookie = login.headers.get("set-cookie", "")
        assert "HttpOnly" in set_cookie
        assert "access_token=" in set_cookie and "refresh_token=" in set_cookie

        origin = BASE
        preflight = requests.options(
            f"{API}/auth/login",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
            timeout=30,
        )
        if preflight.status_code in (200, 204):
            assert preflight.headers.get("access-control-allow-origin") == origin
            assert preflight.headers.get("access-control-allow-credentials") == "true"
        else:
            # Public ingress/WAF may answer OPTIONS before FastAPI; verify direct backend CORS contract.
            direct = requests.options(
                "http://127.0.0.1:8001/api/auth/login",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type",
                },
                timeout=30,
            )
            assert direct.status_code in (200, 204)
            assert direct.headers.get("access-control-allow-origin") == origin
            assert direct.headers.get("access-control-allow-credentials") == "true"

        for _ in range(5):
            bad = requests.post(f"{API}/auth/login", json={"email": email, "password": "WrongPass#2026"}, timeout=30)
            assert bad.status_code == 401
        locked = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
        assert locked.status_code == 429
    finally:
        db.login_attempts.delete_many({"identifier": {"$regex": email}})
        db.labels.delete_many({"user_id": user_id})
        db.users.delete_many({"id": user_id})


# modules/features: seed_admin password repair updates existing admin when configured password changes
def test_seed_admin_updates_existing_admin_password_in_isolated_db():
    from routes import seed as seed_module

    async def _run():
        temp_name = f"iter67_tmp_seed_{uuid.uuid4().hex[:8]}"
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        temp_db = client[temp_name]
        email = f"iter67-seed-admin-{uuid.uuid4().hex[:6]}@example.com"
        try:
            await temp_db.users.insert_one(
                {
                    "id": "iter67-seed-admin",
                    "name": "Seed Admin",
                    "email": email,
                    "password_hash": hash_password("OldPassword#2026"),
                    "role": "super_admin",
                    "status": "active",
                    "created_at": _iso_now(),
                    "updated_at": _iso_now(),
                }
            )

            with patch.object(seed_module, "db", temp_db), patch.object(seed_module, "db_bg", temp_db), patch.dict(
                os.environ,
                {"ADMIN_EMAIL": email, "ADMIN_PASSWORD": "NewPassword#2026"},
                clear=False,
            ):
                await seed_module.seed_indexes_and_admins()

            stored = await temp_db.users.find_one({"email": email}, {"_id": 0, "password_hash": 1})
            assert stored is not None
            from auth_utils import verify_password
            assert verify_password("NewPassword#2026", stored["password_hash"]) is True
        finally:
            await client.drop_database(temp_name)
            client.close()

    asyncio.run(_run())


# modules/features: release list enrichment + artist fallback + cross-label guards
def test_release_list_artist_fallback_and_scope_and_admin_identifiers():
    db = _db()
    fixture = _seed_label_fixture(db, "iter67")
    try:
        _, owner_token = _login(fixture["owner"]["email"], fixture["owner"]["password"])
        label_resp = requests.get(f"{API}/releases/", headers=_headers(owner_token), timeout=30)
        assert label_resp.status_code == 200, label_resp.text
        rows = label_resp.json()
        row_map = {item["id"]: item for item in rows}

        assert fixture["release_ids"][3] not in row_map  # no cross-label leak
        main = row_map[fixture["release_ids"][0]]
        assert main["display_primary_artists"] == ["Alpha", "Owner Main"]
        assert main["display_featured_artists"] == ["FeatOne", "FeatTwo", "Owner Feat"]

        no_credit = row_map[fixture["release_ids"][1]]
        assert no_credit["display_primary_artists"] == []
        assert no_credit["display_featured_artists"] == []

        _, super_token = _login(SUPERADMIN["email"], SUPERADMIN["password"])
        admin_resp = requests.get(f"{API}/admin/releases", headers=_headers(super_token), timeout=30)
        assert admin_resp.status_code == 200, admin_resp.text
        admin_map = {item["id"]: item for item in admin_resp.json()}
        admin_main = admin_map[fixture["release_ids"][0]]

        assert admin_main["upc"] == "001234560000"
        numbers = [int(str(track["track_number"])) for track in admin_main["track_identifiers"]]
        assert numbers == [1, 2]
        assert admin_main["track_identifiers"][0]["track_title"] == "Track One"
        assert admin_main["track_identifiers"][0]["isrc"] == ""
        assert admin_main["track_identifiers"][1]["isrc"] == "IDAAA2600002"

        zero_track = admin_map[fixture["release_ids"][2]]
        assert zero_track["track_identifiers"] == []
    finally:
        _cleanup_fixture(db, fixture)


# modules/features: permission catalog + built-in package manager role + migration idempotency in isolated temp DB
def test_rbac_catalog_and_isolated_migration_idempotency_for_labels_package():
    _, super_token = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    catalog = requests.get(f"{API}/admin/access/catalog", headers=_headers(super_token), timeout=30)
    assert catalog.status_code == 200, catalog.text
    modules = catalog.json()["modules"]
    labels_module = next((module for module in modules if module.get("key") == "labels"), None)
    assert labels_module is not None
    label_actions = [action["key"] for action in labels_module["actions"]]
    assert "labels.package" in label_actions

    roles = requests.get(f"{API}/admin/access/roles", headers=_headers(super_token), timeout=30)
    assert roles.status_code == 200, roles.text
    package_role = next((role for role in roles.json() if role.get("key") == "admin_package_manager"), None)
    assert package_role is not None
    assert package_role.get("permissions") == ["labels.view", "labels.package"]

    from routes.admin_permission_service import ensure_admin_access_defaults

    async def _run_isolated_migration_twice():
        temp_name = f"iter67_tmp_rbac_{uuid.uuid4().hex[:8]}"
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        temp_db = client[temp_name]
        try:
            await temp_db.admin_roles.insert_many([
                {
                    "id": "admin_finance",
                    "key": "admin_finance",
                    "name": "Admin Finance",
                    "builtin": True,
                    "permissions": ["labels.view", "labels.manage"],
                    "active": True,
                    "rbac_schema_version": 6,
                },
                {
                    "id": "admin_release",
                    "key": "admin_release",
                    "name": "Admin Release",
                    "builtin": True,
                    "permissions": ["releases.view"],
                    "active": True,
                    "rbac_schema_version": 6,
                },
            ])
            await ensure_admin_access_defaults(temp_db)
            await ensure_admin_access_defaults(temp_db)

            finance = await temp_db.admin_roles.find_one({"key": "admin_finance"}, {"_id": 0})
            release = await temp_db.admin_roles.find_one({"key": "admin_release"}, {"_id": 0})
            package_manager = await temp_db.admin_roles.find_one({"key": "admin_package_manager"}, {"_id": 0})

            assert "labels.package" not in (finance.get("permissions") or [])  # revocation preserved at schema v6
            assert release.get("permissions") == ["releases.view"]
            assert package_manager.get("permissions") == ["labels.view", "labels.package"]
        finally:
            await client.drop_database(temp_name)
            client.close()

    asyncio.run(_run_isolated_migration_twice())


# modules/features: dedicated package endpoint validation matrix + authz and revision guards
def test_package_endpoint_validation_auth_and_revision_conflict_without_duplicate_audit():
    db = _db()
    fixture = _seed_label_fixture(db, "iter67pkg")
    label_id = fixture["owner"]["label_id"]

    _, super_token = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    _, finance_token = _login(FINANCE["email"], FINANCE["password"])
    _, support_token = _login(SUPPORT["email"], SUPPORT["password"])
    _, label_token = _login(fixture["owner"]["email"], fixture["owner"]["password"])

    pm_email = f"iter67-pm-{fixture['suffix']}@example.com"
    pm_password = temporary_password("Iter67PkgMgr")
    pm_user_id = None
    role_no_pkg_id = None
    user_no_pkg_id = None
    role_pkg_only_id = None
    user_pkg_only_id = None
    try:
        create_pm = requests.post(
            f"{API}/admin/admin-users",
            headers=_headers(super_token),
            json={"name": "Iter67 Package Manager", "email": pm_email, "password": pm_password, "admin_role_id": "admin_package_manager"},
            timeout=30,
        )
        assert create_pm.status_code == 200, create_pm.text
        pm_user_id = create_pm.json()["id"]
        _, pm_token = _login(pm_email, pm_password)

        unauth = requests.patch(
            f"{API}/admin/labels/{label_id}/package",
            json={"package": "pay_per_release", "reason": "xxy", "expected_revision": 0, "confirm": True},
            timeout=30,
        )
        assert unauth.status_code == 401

        label_forbidden = requests.patch(
            f"{API}/admin/labels/{label_id}/package",
            headers=_headers(label_token),
            json={"package": "pay_per_release", "reason": "forbidden label", "expected_revision": 0, "confirm": True},
            timeout=30,
        )
        assert label_forbidden.status_code == 403

        support_forbidden = requests.patch(
            f"{API}/admin/labels/{label_id}/package",
            headers=_headers(support_token),
            json={"package": "pay_per_release", "reason": "support cannot", "expected_revision": 0, "confirm": True},
            timeout=30,
        )
        assert support_forbidden.status_code == 403

        bad_pkg = requests.patch(
            f"{API}/admin/labels/{label_id}/package",
            headers=_headers(finance_token),
            json={"package": "gold", "reason": "invalid", "expected_revision": 0, "confirm": True},
            timeout=30,
        )
        assert bad_pkg.status_code == 422

        short_reason = requests.patch(
            f"{API}/admin/labels/{label_id}/package",
            headers=_headers(finance_token),
            json={"package": "pay_per_release", "reason": "aa", "expected_revision": 0, "confirm": True},
            timeout=30,
        )
        assert short_reason.status_code == 422

        missing_confirm = requests.patch(
            f"{API}/admin/labels/{label_id}/package",
            headers=_headers(finance_token),
            json={"package": "pay_per_release", "reason": "missing confirm", "expected_revision": 0},
            timeout=30,
        )
        assert missing_confirm.status_code == 422

        false_confirm = requests.patch(
            f"{API}/admin/labels/{label_id}/package",
            headers=_headers(finance_token),
            json={"package": "pay_per_release", "reason": "false confirm", "expected_revision": 0, "confirm": False},
            timeout=30,
        )
        assert false_confirm.status_code == 422

        extra_fields = requests.patch(
            f"{API}/admin/labels/{label_id}/package",
            headers=_headers(finance_token),
            json={"package": "pay_per_release", "reason": "extra payload", "expected_revision": 0, "confirm": True, "unexpected": "x"},
            timeout=30,
        )
        assert extra_fields.status_code == 422

        ppr_with_date = requests.patch(
            f"{API}/admin/labels/{label_id}/package",
            headers=_headers(finance_token),
            json={"package": "pay_per_release", "expires_on": "2030-01-01", "reason": "ppr date invalid", "expected_revision": 0, "confirm": True},
            timeout=30,
        )
        assert ppr_with_date.status_code == 422

        missing_annual_date = requests.patch(
            f"{API}/admin/labels/{label_id}/package",
            headers=_headers(finance_token),
            json={"package": "annual_normal", "reason": "annual needs date", "expected_revision": 0, "confirm": True},
            timeout=30,
        )
        assert missing_annual_date.status_code == 422

        invalid_date = requests.patch(
            f"{API}/admin/labels/{label_id}/package",
            headers=_headers(finance_token),
            json={"package": "annual_normal", "expires_on": "2026-02-30", "reason": "invalid date", "expected_revision": 0, "confirm": True},
            timeout=30,
        )
        assert invalid_date.status_code == 422

        missing_label = requests.patch(
            f"{API}/admin/labels/iter67-missing/package",
            headers=_headers(finance_token),
            json={"package": "pay_per_release", "reason": "missing label", "expected_revision": 0, "confirm": True},
            timeout=30,
        )
        assert missing_label.status_code == 404

        # Finance success
        before_payment_count = db.payments.count_documents({"label_id": label_id})
        before_withdraw_count = db.withdraw_requests.count_documents({"label_id": label_id})
        before_royalty_count = db.royalty_lines.count_documents({"label_id": label_id})
        before_revision = int((db.labels.find_one({"id": label_id}, {"_id": 0, "package_revision": 1}) or {}).get("package_revision") or 0)

        future_date = (date.today() + timedelta(days=30)).isoformat()
        finance_ok = requests.patch(
            f"{API}/admin/labels/{label_id}/package",
            headers=_headers(finance_token),
            json={"package": "annual_normal", "expires_on": future_date, "reason": "finance update annual", "expected_revision": before_revision, "confirm": True},
            timeout=30,
        )
        assert finance_ok.status_code == 200, finance_ok.text
        finance_body = finance_ok.json()
        assert finance_body["payment_type"] == "annual_subscription"
        assert finance_body["subscription_tier"] == "annual_normal"
        assert finance_body["subscription_status"] == "active"
        expires = datetime.fromisoformat(finance_body["subscription_expires_at"])
        assert expires.hour == 16 and expires.minute == 59 and expires.second == 59  # 23:59:59 Asia/Jakarta in UTC

        # stale expected_revision should reject and must not append audit
        stale = requests.patch(
            f"{API}/admin/labels/{label_id}/package",
            headers=_headers(finance_token),
            json={"package": "annual_normal", "expires_on": future_date, "reason": "stale duplicate", "expected_revision": before_revision, "confirm": True},
            timeout=30,
        )
        assert stale.status_code == 409
        label_after_stale = db.labels.find_one({"id": label_id}, {"_id": 0, "package_change_history": 1, "package_revision": 1}) or {}
        assert int(label_after_stale.get("package_revision") or 0) == before_revision + 1
        assert len(label_after_stale.get("package_change_history") or []) == 1

        # Super admin success (set expired annual)
        second_revision = int(label_after_stale.get("package_revision") or 0)
        past_date = (date.today() - timedelta(days=1)).isoformat()
        super_ok = requests.patch(
            f"{API}/admin/labels/{label_id}/package",
            headers=_headers(super_token),
            json={"package": "annual_vip", "expires_on": past_date, "reason": "super set expired vip", "expected_revision": second_revision, "confirm": True},
            timeout=30,
        )
        assert super_ok.status_code == 200, super_ok.text
        assert super_ok.json()["subscription_tier"] == "annual_vip"
        assert super_ok.json()["subscription_status"] == "expired"

        # Package manager success (switch back to PPR clears tier/status/expiry)
        third_revision = int(super_ok.json()["package_revision"])
        pm_ok = requests.patch(
            f"{API}/admin/labels/{label_id}/package",
            headers=_headers(pm_token),
            json={"package": "pay_per_release", "expires_on": None, "reason": "package manager to ppr", "expected_revision": third_revision, "confirm": True},
            timeout=30,
        )
        assert pm_ok.status_code == 200, pm_ok.text
        pm_body = pm_ok.json()
        assert pm_body["payment_type"] == "pay_per_release"
        assert pm_body["subscription_tier"] is None
        assert pm_body["subscription_status"] == "inactive"
        assert pm_body["subscription_expires_at"] is None

        # invariant checks: no invoices/payments/royalty side-effects
        assert db.payments.count_documents({"label_id": label_id}) == before_payment_count
        assert db.withdraw_requests.count_documents({"label_id": label_id}) == before_withdraw_count
        assert db.royalty_lines.count_documents({"label_id": label_id}) == before_royalty_count

        label_after = db.labels.find_one({"id": label_id}, {"_id": 0})
        assert int(label_after.get("package_revision") or 0) == before_revision + 3
        history = label_after.get("package_change_history") or []
        assert len(history) == 3
        assert history[0]["reason"] == "finance update annual"
        assert history[-1]["after"]["payment_type"] == "pay_per_release"

        logs = list(db.activity_logs.find({"reference_id": label_id, "action": "change_label_package"}, {"_id": 0}).sort("created_at", 1))
        assert len(logs) == 3
        assert all((entry.get("after_data") or {}).get("audit_id") for entry in logs)

        # label self profile must hide package_change_history
        me = requests.get(f"{API}/label/me", headers=_headers(label_token), timeout=30)
        assert me.status_code == 200, me.text
        assert "package_change_history" not in me.json()

        # old generic patch: labels.manage-only role must still be denied for package changes
        role_no_pkg = requests.post(
            f"{API}/admin/access/roles",
            headers=_headers(super_token),
            json={"name": f"Iter67 NoPkg {fixture['suffix']}", "permissions": ["labels.view", "labels.manage"]},
            timeout=30,
        )
        assert role_no_pkg.status_code == 200, role_no_pkg.text
        role_no_pkg_id = role_no_pkg.json()["id"]

        no_pkg_email = f"iter67-nopkg-{fixture['suffix']}@example.com"
        no_pkg_password = temporary_password("Iter67NoPkg")
        create_no_pkg = requests.post(
            f"{API}/admin/admin-users",
            headers=_headers(super_token),
            json={"name": "Iter67 NoPkg", "email": no_pkg_email, "password": no_pkg_password, "admin_role_id": role_no_pkg_id},
            timeout=30,
        )
        assert create_no_pkg.status_code == 200, create_no_pkg.text
        user_no_pkg_id = create_no_pkg.json()["id"]
        _, no_pkg_token = _login(no_pkg_email, no_pkg_password)

        no_pkg_old_patch = requests.patch(
            f"{API}/admin/labels/{label_id}",
            headers=_headers(no_pkg_token),
            json={"payment_type": "annual_subscription", "subscription_tier": "annual_normal", "subscription_expires_at": future_date},
            timeout=30,
        )
        assert no_pkg_old_patch.status_code == 403

        # package-only role cannot use old generic patch to mutate label fields and must not create side effects
        role_pkg_only = requests.post(
            f"{API}/admin/access/roles",
            headers=_headers(super_token),
            json={"name": f"Iter67 PkgOnly {fixture['suffix']}", "permissions": ["labels.view", "labels.package"]},
            timeout=30,
        )
        assert role_pkg_only.status_code == 200, role_pkg_only.text
        role_pkg_only_id = role_pkg_only.json()["id"]

        pkg_only_email = f"iter67-pkgonly-{fixture['suffix']}@example.com"
        pkg_only_password = temporary_password("Iter67PkgOnly")
        create_pkg_only = requests.post(
            f"{API}/admin/admin-users",
            headers=_headers(super_token),
            json={"name": "Iter67 PkgOnly", "email": pkg_only_email, "password": pkg_only_password, "admin_role_id": role_pkg_only_id},
            timeout=30,
        )
        assert create_pkg_only.status_code == 200, create_pkg_only.text
        user_pkg_only_id = create_pkg_only.json()["id"]
        _, pkg_only_token = _login(pkg_only_email, pkg_only_password)

        pre_histories = db.royalty_percentage_history.count_documents({"label_id": label_id})
        pre_jobs = db.migrate_jobs.count_documents({"label_id": label_id})
        pkg_only_generic = requests.patch(
            f"{API}/admin/labels/{label_id}",
            headers=_headers(pkg_only_token),
            json={
                "payment_type": "pay_per_release",
                "royalty_percentage_default": 77,
                "royalty_change_reason": "must not run",
                "account_status": "suspended",
            },
            timeout=30,
        )
        assert pkg_only_generic.status_code == 403
        assert db.royalty_percentage_history.count_documents({"label_id": label_id}) == pre_histories
        assert db.migrate_jobs.count_documents({"label_id": label_id}) == pre_jobs
    finally:
        if pm_user_id:
            requests.delete(f"{API}/admin/admin-users/{pm_user_id}", headers=_headers(super_token), timeout=30)
        if user_no_pkg_id:
            requests.delete(f"{API}/admin/admin-users/{user_no_pkg_id}", headers=_headers(super_token), timeout=30)
        if user_pkg_only_id:
            requests.delete(f"{API}/admin/admin-users/{user_pkg_only_id}", headers=_headers(super_token), timeout=30)
        if role_no_pkg_id:
            requests.delete(f"{API}/admin/access/roles/{role_no_pkg_id}", headers=_headers(super_token), timeout=30)
        if role_pkg_only_id:
            requests.delete(f"{API}/admin/access/roles/{role_pkg_only_id}", headers=_headers(super_token), timeout=30)
        db.users.delete_many({"email": {"$in": [pm_email, f"iter67-nopkg-{fixture['suffix']}@example.com", f"iter67-pkgonly-{fixture['suffix']}@example.com"]}})
        if role_no_pkg_id:
            db.admin_roles.delete_many({"id": role_no_pkg_id})
        if role_pkg_only_id:
            db.admin_roles.delete_many({"id": role_pkg_only_id})
        _cleanup_fixture(db, fixture)
