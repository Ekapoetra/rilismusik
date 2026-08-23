"""Iteration 9 — refactor verification smoke test.
Covers areas not explicitly exercised by phase2-6 suites:
  - /api/health
  - super_admin + sub_admin logins
  - GET /api/cms/landing returns ALL 12 keys
  - /api/admin/dashboard, /api/admin/labels, /api/admin/releases, /api/admin/artists, /api/admin/payments
  - /api/notifications/me shape
  - /api/withdraw/window (label)
  - /api/releases/{id} 404-on-other-label
  - /api/auth/register persists verification token in DB (NOT in HTTP response — SEC-001), then logout
"""
import os
import uuid
import requests
from dotenv import dotenv_values
from tests.support_config import DEMO_PPR, DEMO_VIP, FINANCE, MARKETING, RELEASE_ADMIN, SUPPORT, SUPERADMIN, temporary_password
import pytest

BASE = (os.environ.get("REACT_APP_BACKEND_URL") or dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"]).rstrip("/")
SA_EMAIL = SUPERADMIN["email"]
SA_PASS = SUPERADMIN["password"]
SUB_ADMINS = [
    (FINANCE["email"], FINANCE["password"]),
    (SUPPORT["email"], SUPPORT["password"]),
    (RELEASE_ADMIN["email"], RELEASE_ADMIN["password"]),
    (MARKETING["email"], MARKETING["password"]),
]


def _mongo_db():
    import pymongo
    client = pymongo.MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    return client[os.environ.get("DB_NAME", "test_database")]


def _cleanup_refactor_artifacts():
    db = _mongo_db()
    labels = list(db.labels.find({"$or": [
        {"label_name": {"$regex": "^Refactor Test Label"}},
        {"email": {"$regex": "^test_refactor_"}},
    ]}, {"_id": 0, "id": 1, "user_id": 1}))
    label_ids = [label["id"] for label in labels]
    user_ids = [label.get("user_id") for label in labels if label.get("user_id")]
    for collection in ("royalty_lines", "withdraw_requests", "balance_transactions", "contracts", "releases", "tracks", "artists", "bank_accounts"):
        db[collection].delete_many({"label_id": {"$in": label_ids}})
    db.labels.delete_many({"id": {"$in": label_ids}})
    db.users.delete_many({"$or": [{"id": {"$in": user_ids}}, {"email": {"$regex": "^test_refactor_"}}]})


@pytest.fixture(scope="session", autouse=True)
def cleanup_refactor_artifacts():
    _cleanup_refactor_artifacts()
    yield
    _cleanup_refactor_artifacts()


def _login(email, password):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    data = r.json()
    assert "access_token" in data and "user" in data
    return data["access_token"], data


def _hdr(tok):
    return {"Authorization": f"Bearer {tok}"}


def test_health_ok():
    r = requests.get(f"{BASE}/api/health", timeout=10)
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_superadmin_login():
    tok, data = _login(SA_EMAIL, SA_PASS)
    assert data["user"]["role"] == "super_admin"
    assert isinstance(tok, str) and len(tok) > 20


@pytest.mark.parametrize("email,password", SUB_ADMINS)
def test_subadmin_logins(email, password):
    tok, data = _login(email, password)
    assert data["user"]["role"].startswith("admin_") or data["user"]["role"] == "super_admin"


def test_register_persists_verification_token_then_logout():
    """SEC-001: register no longer returns verification_token in HTTP body.
    The token must be persisted to MongoDB so the verification email link works.
    """
    suffix = uuid.uuid4().hex[:8]
    email = f"test_refactor_{suffix}@example.com"
    payload = {
        "email": email,
        "password": temporary_password("refactor-smoke"),
        "label_name": f"Refactor Test Label {suffix}",
        "contact_name": "Refactor Tester",
        "pic_name": "Refactor Tester",
        "country": "ID",
        "whatsapp": "+6281234567890",
        "mda_accepted": True,
    }
    r = requests.post(f"{BASE}/api/auth/register", json=payload, timeout=30)
    assert r.status_code in (200, 201), r.text
    body = r.json()
    # SEC-001: token MUST NOT be in the response (only sent via email)
    assert "verification_token" not in body, "SEC-001: verification_token leaked in HTTP body"
    assert "reset_token" not in body
    # Token must be persisted in MongoDB so the email link works
    db = _mongo_db()
    user_doc = db.users.find_one({"email": email.lower()})
    assert user_doc, "user not created"
    tok_doc = db.email_verification_tokens.find_one({"user_id": user_doc["id"]})
    assert tok_doc and tok_doc.get("token") and len(tok_doc["token"]) > 10

    tok, _ = _login(SA_EMAIL, SA_PASS)
    rlo = requests.post(f"{BASE}/api/auth/logout", headers=_hdr(tok), timeout=10)
    assert rlo.status_code in (200, 204)


def test_cms_landing_has_all_12_keys():
    r = requests.get(f"{BASE}/api/cms/landing", timeout=10)
    assert r.status_code == 200
    data = r.json()
    expected = {"general", "hero", "benefits", "how_it_works", "pricing", "royalty_sim",
                "dashboard_previews", "testimonials", "faq", "seo", "footer", "legal_entity"}
    missing = expected - set(data.keys())
    assert not missing, f"Missing CMS keys: {missing}"


def test_admin_dashboards_and_lists():
    tok, _ = _login(SA_EMAIL, SA_PASS)
    h = _hdr(tok)
    for path in ["/api/admin/dashboard", "/api/admin/labels", "/api/admin/releases",
                 "/api/admin/artists", "/api/admin/payments"]:
        r = requests.get(f"{BASE}{path}", headers=h, timeout=20)
        assert r.status_code == 200, f"{path}: {r.status_code} {r.text[:300]}"


def test_admin_cron_triggers_role_matrix():
    sa_tok, _ = _login(SA_EMAIL, SA_PASS)
    fin_tok, _ = _login(FINANCE["email"], FINANCE["password"])
    sup_tok, _ = _login(SUPPORT["email"], SUPPORT["password"])
    rel_tok, _ = _login(RELEASE_ADMIN["email"], RELEASE_ADMIN["password"])

    # subscription-check: super_admin + finance OK, support/release 403
    for tok in (sa_tok, fin_tok):
        r = requests.post(f"{BASE}/api/admin/cron/subscription-check", headers=_hdr(tok), timeout=20)
        assert r.status_code == 200 and r.json().get("ok") is True, r.text
    for tok in (sup_tok, rel_tok):
        r = requests.post(f"{BASE}/api/admin/cron/subscription-check", headers=_hdr(tok), timeout=20)
        assert r.status_code == 403, f"expected 403 got {r.status_code}: {r.text}"

    # contract-check: super_admin + release OK, finance/support 403
    for tok in (sa_tok, rel_tok):
        r = requests.post(f"{BASE}/api/admin/cron/contract-check", headers=_hdr(tok), timeout=20)
        assert r.status_code == 200 and r.json().get("ok") is True, r.text
    for tok in (fin_tok, sup_tok):
        r = requests.post(f"{BASE}/api/admin/cron/contract-check", headers=_hdr(tok), timeout=20)
        assert r.status_code == 403, f"expected 403 got {r.status_code}: {r.text}"


def _find_label(sa_tok, query):
    r = requests.get(f"{BASE}/api/admin/labels", headers=_hdr(sa_tok),
                     params={"q": query}, timeout=20)
    assert r.status_code == 200
    items = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
    assert items, f"No label found for query={query}"
    return items[0]


def _demo_login(label):
    email = label.get("primary_user_email") or label.get("owner_email") or label.get("email")
    assert email, f"label record missing email field: {label.keys()}"
    credentials = DEMO_VIP if email == DEMO_VIP["email"] else DEMO_PPR
    return _login(email, credentials["password"])


def test_label_dashboard_strips_internal_fields():
    sa_tok, _ = _login(SA_EMAIL, SA_PASS)
    lbl = _find_label(sa_tok, "Demo Label PPR")
    tok, login_data = _demo_login(lbl)
    # login response should already redact
    lbl_in_login = login_data.get("label") or {}
    for f in ("royalty_percentage_default", "royalty_percentage_history", "default_royalty_share"):
        assert f not in lbl_in_login, f"login.label leaked {f}"

    r = requests.get(f"{BASE}/api/label/me", headers=_hdr(tok), timeout=20)
    assert r.status_code == 200
    me = r.json()
    me_label = me.get("label") or me
    for f in ("royalty_percentage_default", "royalty_percentage_history", "default_royalty_share"):
        assert f not in me_label, f"/label/me leaked {f}"

    r = requests.get(f"{BASE}/api/label/dashboard", headers=_hdr(tok), timeout=20)
    assert r.status_code == 200
    body = r.json()
    flat = str(body)
    for f in ("royalty_percentage_default", "royalty_percentage_history", "default_royalty_share"):
        assert f not in flat, f"/label/dashboard leaked {f}"


def test_label_withdraw_window():
    sa_tok, _ = _login(SA_EMAIL, SA_PASS)
    lbl = _find_label(sa_tok, "Demo Label PPR")
    tok, _ = _demo_login(lbl)
    r = requests.get(f"{BASE}/api/withdraw/window", headers=_hdr(tok), timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert "request_open" in body or "payment_window" in body or "phase" in body, f"unexpected window shape: {body}"


def test_notifications_me_shape():
    sa_tok, _ = _login(SA_EMAIL, SA_PASS)
    lbl = _find_label(sa_tok, "Demo Label PPR")
    tok, _ = _demo_login(lbl)
    r = requests.get(f"{BASE}/api/notifications/me", headers=_hdr(tok), timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data and "unread_count" in data, f"shape={list(data.keys())}"


def test_release_404_for_other_label():
    """Verifies the renamed `label_uids` variable (was label_user_ids) in releases admin action did not break label-side access."""
    sa_tok, _ = _login(SA_EMAIL, SA_PASS)
    # Find two different labels with releases
    lbl_a = _find_label(sa_tok, "Demo Label PPR")
    lbl_b = _find_label(sa_tok, "Demo Label VIP")
    tok_a, _ = _demo_login(lbl_a)
    tok_b, _ = _demo_login(lbl_b)

    # label A lists releases
    r = requests.get(f"{BASE}/api/releases/", headers=_hdr(tok_a), timeout=20)
    assert r.status_code == 200
    items = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
    if not items:
        pytest.skip("Label A has no releases to cross-test")
    rid = items[0].get("id") or items[0].get("_id")
    assert rid

    # owner sees it
    r_own = requests.get(f"{BASE}/api/releases/{rid}", headers=_hdr(tok_a), timeout=10)
    assert r_own.status_code == 200

    # other label gets 403 (current API contract: "Bukan rilisan Anda") or 404 — both prove isolation
    r_other = requests.get(f"{BASE}/api/releases/{rid}", headers=_hdr(tok_b), timeout=10)
    assert r_other.status_code in (403, 404), f"cross-label leak: {r_other.status_code} {r_other.text}"
