"""Phase 25 — Label account lifecycle (revoke + change email) + dashboard speed.

Validates:
  - POST /api/admin/labels/{id}/revoke-account disables the PIC user, clears
    label.user_id, and bumps token_version (so existing JWTs are invalidated).
  - With cascade_artists=true, all artist sub-accounts under that label also
    get status='disabled' + token_version bumped.
  - POST /api/admin/labels/{id}/change-email updates user.email + label.email,
    bumps token_version, and (with notify=true) attempts to send emails.
  - RBAC: super_admin/support/release allowed; admin_finance/support_role
    etc. denied where appropriate.
  - Label dashboard last_month_revenue reads from monthly_analytics cache
    (sub-second) when available, falls back to live aggregate otherwise.
"""
import os
import uuid
import requests
from tests.support_config import FINANCE as FINANCE_CRED, SUPPORT as SUPPORT_CRED, SUPERADMIN, temporary_password
import pytest
import pymongo

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://lanjut-core.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"
SUPER = (SUPERADMIN["email"], SUPERADMIN["password"])
FINANCE = (FINANCE_CRED["email"], FINANCE_CRED["password"])
SUPPORT = (SUPPORT_CRED["email"], SUPPORT_CRED["password"])


def _db():
    client = pymongo.MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    return client[os.environ.get("DB_NAME", "rilismusik_db")]


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def _hdr(t):
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture(scope="module")
def super_token():
    return _login(*SUPER)


@pytest.fixture
def label_with_user_and_artists():
    """Seed a label + PIC user + 2 artist sub-accounts. All status='active'."""
    db = _db()
    from auth_utils import hash_password as _hp
    label_id = f"phase25-lab-{uuid.uuid4().hex[:10]}"
    label_user_id = f"phase25-luser-{uuid.uuid4().hex[:10]}"
    artist1_user_id = f"phase25-a1user-{uuid.uuid4().hex[:10]}"
    artist2_user_id = f"phase25-a2user-{uuid.uuid4().hex[:10]}"
    artist1_id = f"phase25-art1-{uuid.uuid4().hex[:10]}"
    artist2_id = f"phase25-art2-{uuid.uuid4().hex[:10]}"
    pwd_hash = _hp(temporary_password("phase25-original"))

    db.users.insert_many([
        {"id": label_user_id, "email": f"label-{label_id[-6:]}@test.com", "password_hash": pwd_hash,
         "role": "label", "status": "active", "name": "Label PIC",
         "token_version": 0, "created_at": "2026-01-01"},
        {"id": artist1_user_id, "email": f"artist1-{label_id[-6:]}@test.com", "password_hash": pwd_hash,
         "role": "artist", "status": "active", "name": "Artist 1",
         "token_version": 0, "created_at": "2026-01-01"},
        {"id": artist2_user_id, "email": f"artist2-{label_id[-6:]}@test.com", "password_hash": pwd_hash,
         "role": "artist", "status": "active", "name": "Artist 2",
         "token_version": 0, "created_at": "2026-01-01"},
    ])
    db.labels.insert_one({
        "id": label_id, "label_name": f"Phase25 {label_id[-6:]}", "user_id": label_user_id,
        "email": f"label-{label_id[-6:]}@test.com", "account_status": "active",
        "balance_pending_idr": 0, "balance_available_idr": 0,
    })
    db.artists.insert_many([
        {"id": artist1_id, "label_id": label_id, "user_id": artist1_user_id,
         "artist_name": "Artist 1", "status": "active"},
        {"id": artist2_id, "label_id": label_id, "user_id": artist2_user_id,
         "artist_name": "Artist 2", "status": "active"},
    ])
    yield {
        "label_id": label_id, "label_user_id": label_user_id,
        "label_email": f"label-{label_id[-6:]}@test.com",
        "artist_user_ids": [artist1_user_id, artist2_user_id],
        "artist_ids": [artist1_id, artist2_id],
    }
    # cleanup
    db.users.delete_many({"id": {"$in": [label_user_id, artist1_user_id, artist2_user_id]}})
    db.users.delete_many({"email": {"$regex": f"^(label|artist[12])-{label_id[-6:]}@"}})
    db.artists.delete_many({"id": {"$in": [artist1_id, artist2_id]}})
    db.labels.delete_one({"id": label_id})


def test_revoke_account_clears_user_id_and_disables_user(super_token, label_with_user_and_artists):
    db = _db()
    ctx = label_with_user_and_artists
    r = requests.post(
        f"{API}/admin/labels/{ctx['label_id']}/revoke-account",
        headers=_hdr(super_token),
        data={"cascade_artists": "false", "reason": "test revoke"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ok"] is True
    assert j["revoked_email"] == ctx["label_email"]
    assert j["artists_disabled"] == 0
    # DB assertions
    label = db.labels.find_one({"id": ctx["label_id"]})
    assert label["user_id"] is None
    assert label["account_status"] == "no_account"
    assert label["previous_account_email"] == ctx["label_email"]
    luser = db.users.find_one({"id": ctx["label_user_id"]})
    assert luser["status"] == "disabled"
    assert luser["token_version"] >= 1
    assert luser["disabled_reason"] == "test revoke"
    # Artists untouched
    for aid in ctx["artist_user_ids"]:
        au = db.users.find_one({"id": aid})
        assert au["status"] == "active", f"artist {aid} should NOT be disabled"
        assert au["token_version"] == 0


def test_revoke_account_cascade_disables_artists(super_token, label_with_user_and_artists):
    db = _db()
    ctx = label_with_user_and_artists
    r = requests.post(
        f"{API}/admin/labels/{ctx['label_id']}/revoke-account",
        headers=_hdr(super_token),
        data={"cascade_artists": "true", "reason": "cascade test"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["artists_disabled"] == 2
    for aid in ctx["artist_user_ids"]:
        au = db.users.find_one({"id": aid})
        assert au["status"] == "disabled"
        assert au["token_version"] >= 1


def test_revoke_account_rejects_label_without_user(super_token):
    """Calling revoke on a label whose user_id is already null returns 400."""
    db = _db()
    label_id = f"phase25-nouser-{uuid.uuid4().hex[:10]}"
    db.labels.insert_one({"id": label_id, "label_name": "No User Label", "user_id": None})
    try:
        r = requests.post(
            f"{API}/admin/labels/{label_id}/revoke-account",
            headers=_hdr(super_token),
            data={"cascade_artists": "false"},
            timeout=30,
        )
        assert r.status_code == 400
        assert "belum punya akun" in r.text.lower() or "user" in r.text.lower()
    finally:
        db.labels.delete_one({"id": label_id})


def test_revoke_account_rbac_finance_denied(label_with_user_and_artists):
    """Admin Finance must NOT be able to revoke accounts (only super/support/release)."""
    ctx = label_with_user_and_artists
    finance_t = _login(*FINANCE)
    r = requests.post(
        f"{API}/admin/labels/{ctx['label_id']}/revoke-account",
        headers=_hdr(finance_t),
        data={"cascade_artists": "false"},
        timeout=30,
    )
    assert r.status_code == 403


def test_change_email_updates_user_and_label(super_token, label_with_user_and_artists):
    db = _db()
    ctx = label_with_user_and_artists
    new_email = f"new-{uuid.uuid4().hex[:8]}@phase25.test"
    r = requests.post(
        f"{API}/admin/labels/{ctx['label_id']}/change-email",
        headers=_hdr(super_token),
        data={"new_email": new_email, "notify": "false"},  # skip email send for speed
        timeout=30,
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ok"] is True
    assert j["old_email"] == ctx["label_email"]
    assert j["new_email"] == new_email
    # DB checks
    luser = db.users.find_one({"id": ctx["label_user_id"]})
    assert luser["email"] == new_email
    assert luser["token_version"] >= 1
    assert luser.get("email_changed_at") is not None
    label = db.labels.find_one({"id": ctx["label_id"]})
    assert label["email"] == new_email


def test_change_email_rejects_duplicate(super_token, label_with_user_and_artists):
    """Cannot change to an email already used by another user."""
    ctx = label_with_user_and_artists
    # The super admin's email is already taken
    r = requests.post(
        f"{API}/admin/labels/{ctx['label_id']}/change-email",
        headers=_hdr(super_token),
        data={"new_email": SUPERADMIN["email"], "notify": "false"},
        timeout=30,
    )
    assert r.status_code == 409
    assert "sudah dipakai" in r.text.lower() or "duplicate" in r.text.lower() or "exist" in r.text.lower()


def test_change_email_rejects_invalid_format(super_token, label_with_user_and_artists):
    ctx = label_with_user_and_artists
    r = requests.post(
        f"{API}/admin/labels/{ctx['label_id']}/change-email",
        headers=_hdr(super_token),
        data={"new_email": "not-an-email", "notify": "false"},
        timeout=30,
    )
    assert r.status_code == 400


def test_change_email_rejects_same_email(super_token, label_with_user_and_artists):
    ctx = label_with_user_and_artists
    r = requests.post(
        f"{API}/admin/labels/{ctx['label_id']}/change-email",
        headers=_hdr(super_token),
        data={"new_email": ctx["label_email"], "notify": "false"},
        timeout=30,
    )
    assert r.status_code == 400
    assert "sama" in r.text.lower()


def test_change_email_rbac_finance_denied(label_with_user_and_artists):
    ctx = label_with_user_and_artists
    finance_t = _login(*FINANCE)
    r = requests.post(
        f"{API}/admin/labels/{ctx['label_id']}/change-email",
        headers=_hdr(finance_t),
        data={"new_email": f"new-{uuid.uuid4().hex[:6]}@test.com", "notify": "false"},
        timeout=30,
    )
    assert r.status_code == 403


def test_label_dashboard_reads_latest_unwithdrawn_revenue(super_token):
    """Customer dashboard ignores settled history and shows active royalty."""
    db = _db()
    from auth_utils import hash_password as _hp
    label_id = f"phase25-dash-{uuid.uuid4().hex[:10]}"
    user_id = f"phase25-dashu-{uuid.uuid4().hex[:10]}"
    email = f"dashlabel-{label_id[-6:]}@test.com"
    pwd = temporary_password("phase25-dashboard")
    db.users.insert_one({
        "id": user_id, "email": email, "password_hash": _hp(pwd),
        "role": "label", "status": "active", "name": "Dash Label",
        "token_version": 0, "email_verified_at": "2026-01-01",
        "created_at": "2026-01-01",
    })
    db.labels.insert_one({
        "id": label_id, "label_name": f"Dash {label_id[-6:]}", "user_id": user_id,
        "email": email, "account_status": "active",
        "balance_available_idr": 12345, "balance_pending_idr": 6789,
    })
    db.royalty_lines.insert_many([
        {"id": f"{label_id}-1", "label_id": label_id, "period": "2025-01", "status": "pending", "label_idr": 100000},
        {"id": f"{label_id}-2", "label_id": label_id, "period": "2025-02", "status": "available", "label_idr": 200000},
        {"id": f"{label_id}-3", "label_id": label_id, "period": "2025-03", "status": "pending", "label_idr": 7777777},
        {"id": f"{label_id}-4", "label_id": label_id, "period": "2025-04", "status": "withdrawn", "label_idr": 9999999},
    ])
    try:
        # Log in as the new label user
        ltok = _login(email, pwd)
        r = requests.get(f"{API}/label/dashboard", headers=_hdr(ltok), timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["stats"]["last_month_revenue_idr"] == 7777777
        assert body["stats"]["last_month_period"] == "2025-03"
        assert body["stats"]["balance_available_idr"] == 12345
        assert body["stats"]["balance_pending_idr"] == 6789
    finally:
        db.royalty_lines.delete_many({"label_id": label_id})
        db.labels.delete_one({"id": label_id})
        db.users.delete_one({"id": user_id})
