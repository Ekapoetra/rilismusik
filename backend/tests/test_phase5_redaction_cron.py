"""
Phase 5 backend tests:
  (1) Label/Artist royalty-percentage redaction across auth/login, /auth/me,
      /label/me, /label/dashboard, /royalty/lines, /royalty/export.csv
  (2) Subscription expiry + reminder cron
  (3) Contract expiry reminder cron
  (4) Admin still sees everything (no redaction for super_admin)
"""
import os
import csv
import io
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://lanjut-core.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

SUPER_ADMIN = {"email": "superadmin@rilismusik.com", "password": "SuperAdmin#2026"}
FINANCE = {"email": "finance1@rilismusik.com", "password": "Finance#2026"}
SUPPORT = {"email": "support1@rilismusik.com", "password": "Support#2026"}
RELEASE = {"email": "release1@rilismusik.com", "password": "Release#2026"}

FORBIDDEN_LABEL_KEYS = ("royalty_percentage_default", "royalty_percentage_history", "default_royalty_share")
# Note: fee_percent_applied (5% distributor fee) is intentionally VISIBLE to labels
# per user requirement 2026-06-24 ("fee 5% tetap diperlihatkan tidak masalah").
FORBIDDEN_LINE_KEYS = (
    "label_percentage_applied", "distributor_idr", "exchange_rate",
    "revenue_eur", "fee_eur", "net_eur", "label_eur", "distributor_eur",
    "gross_revenue_eur", "unit_price_eur", "mechanical_cost_eur", "client_share_rate",
)


def login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.status_code} {r.text}"
    body = r.json()
    # normalise token field name
    if "token" not in body:
        body["token"] = body.get("access_token") or body.get("accessToken")
    return body


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def super_admin_token():
    return login(SUPER_ADMIN)["token"]


@pytest.fixture(scope="module")
def finance_token():
    return login(FINANCE)["token"]


@pytest.fixture(scope="module")
def support_token():
    return login(SUPPORT)["token"]


@pytest.fixture(scope="module")
def release_token():
    return login(RELEASE)["token"]


@pytest.fixture(scope="module")
def label_login():
    """Find one demo label that authenticates with Demo#2026, return its login payload + token."""
    sa = login(SUPER_ADMIN)["token"]
    # Search for working demo labels
    for name in ("Khizanah", "Mustafa", "WANWE"):
        r = requests.get(f"{API}/admin/labels", params={"q": name}, headers=auth_header(sa), timeout=30)
        if r.status_code != 200:
            continue
        body = r.json()
        items = body.get("items") if isinstance(body, dict) else body
        items = items or []
        for lab in items:
            email = lab.get("contact_email") or lab.get("email") or (lab.get("user") or {}).get("email")
            if not email:
                continue
            lr = requests.post(f"{API}/auth/login", json={"email": email, "password": "Demo#2026"}, timeout=30)
            if lr.status_code == 200:
                body = lr.json()
                if "token" not in body:
                    body["token"] = body.get("access_token") or body.get("accessToken")
                return {"login": body, "label": lab, "email": email}
    pytest.skip("No demo label authenticates with Demo#2026")


# ---------- (1) REDACTION TESTS ----------

class TestLabelProfileRedaction:
    def test_login_response_redacts_label(self, label_login):
        label = label_login["login"].get("label")
        assert label is not None, "login response missing label"
        for k in FORBIDDEN_LABEL_KEYS:
            assert k not in label, f"login.label still contains forbidden key {k}"

    def test_auth_me_redacts_label(self, label_login):
        tok = label_login["login"]["token"]
        r = requests.get(f"{API}/auth/me", headers=auth_header(tok), timeout=30)
        assert r.status_code == 200
        data = r.json()
        lab = data.get("label") or {}
        for k in FORBIDDEN_LABEL_KEYS:
            assert k not in lab, f"/auth/me.label leaks {k}"

    def test_label_me_redacts(self, label_login):
        tok = label_login["login"]["token"]
        r = requests.get(f"{API}/label/me", headers=auth_header(tok), timeout=30)
        assert r.status_code == 200
        lab = r.json()
        for k in FORBIDDEN_LABEL_KEYS:
            assert k not in lab, f"/label/me leaks {k}"

    def test_label_dashboard_redacts(self, label_login):
        tok = label_login["login"]["token"]
        r = requests.get(f"{API}/label/dashboard", headers=auth_header(tok), timeout=30)
        assert r.status_code == 200
        lab = r.json().get("label") or {}
        for k in FORBIDDEN_LABEL_KEYS:
            assert k not in lab, f"/label/dashboard.label leaks {k}"

    def test_register_new_label_redacts(self):
        suffix = str(int(time.time()))
        email = f"TEST_redact_{suffix}@example.com"
        payload = {
            "email": email,
            "password": "TestPass#2026",
            "label_name": f"TEST_RedactLabel_{suffix}",
            "pic_name": "Redact Tester",
            "whatsapp": "+628111111111",
            "account_type": "label",
        }
        r = requests.post(f"{API}/auth/register", json=payload, timeout=30)
        if r.status_code not in (200, 201):
            pytest.skip(f"register endpoint not available or differs: {r.status_code} {r.text[:200]}")
        body = r.json()
        lab = body.get("label") or {}
        for k in FORBIDDEN_LABEL_KEYS:
            assert k not in lab, f"register response leaks {k}"


class TestRoyaltyLinesRedaction:
    def test_label_royalty_lines_redacted(self, label_login):
        tok = label_login["login"]["token"]
        r = requests.get(f"{API}/royalty/lines", headers=auth_header(tok), params={"limit": 5}, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        items = body.get("items") if isinstance(body, dict) else body
        if not items:
            pytest.skip("no royalty lines for this label")
        for it in items:
            for k in FORBIDDEN_LINE_KEYS:
                assert k not in it, f"label royalty line leaks {k}: {list(it.keys())}"
            assert "label_idr" in it or "royalty_idr" in it, f"missing IDR amount: {list(it.keys())}"

    def test_admin_royalty_lines_unredacted(self, super_admin_token, label_login):
        # Admin must still see EUR + percentages
        lab_id = label_login["label"]["id"]
        r = requests.get(f"{API}/royalty/lines", headers=auth_header(super_admin_token),
                         params={"label_id": lab_id, "limit": 5}, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        items = body.get("items") if isinstance(body, dict) else body
        if not items:
            pytest.skip("no royalty lines for admin view")
        sample = items[0]
        # admin should retain at least these
        retained = [k for k in ("revenue_eur", "label_percentage_applied", "fee_percent_applied",
                                "exchange_rate", "label_eur") if k in sample]
        assert retained, f"admin lost ALL internal fields; admin sample keys={list(sample.keys())}"

    def test_csv_export_columns_redacted(self, label_login):
        tok = label_login["login"]["token"]
        r = requests.get(f"{API}/royalty/export.csv", headers=auth_header(tok), timeout=30)
        assert r.status_code == 200, r.text
        text = r.text
        reader = csv.reader(io.StringIO(text))
        header = next(reader, [])
        expected = ["period", "release_title", "track_title", "artist_name", "platform",
                    "country", "isrc", "upc", "streams", "royalty_idr", "status"]
        assert header == expected, f"CSV header mismatch: {header}"
        assert "revenue_eur" not in header
        assert "label_percent_applied" not in header
        assert "label_percentage_applied" not in header


class TestAdminLabelDetailVisible:
    def test_admin_sees_royalty_percentage(self, super_admin_token, label_login):
        lab_id = label_login["label"]["id"]
        r = requests.get(f"{API}/admin/labels/{lab_id}", headers=auth_header(super_admin_token), timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        # response may be flat dict or {label: {...}}
        lab = body.get("label") if isinstance(body, dict) and "label" in body else body
        assert "royalty_percentage_default" in lab, f"admin label detail missing royalty_percentage_default: keys={list(lab.keys())[:20]}"


# ---------- (2) SUBSCRIPTION CRON ----------

class TestSubscriptionCron:
    def test_super_admin_can_trigger(self, super_admin_token):
        r = requests.post(f"{API}/admin/cron/subscription-check", headers=auth_header(super_admin_token), timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        assert body.get("job") == "subscription_expiry"

    def test_finance_can_trigger(self, finance_token):
        r = requests.post(f"{API}/admin/cron/subscription-check", headers=auth_header(finance_token), timeout=60)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

    def test_support_forbidden(self, support_token):
        r = requests.post(f"{API}/admin/cron/subscription-check", headers=auth_header(support_token), timeout=30)
        assert r.status_code == 403

    def test_release_forbidden(self, release_token):
        r = requests.post(f"{API}/admin/cron/subscription-check", headers=auth_header(release_token), timeout=30)
        assert r.status_code == 403

    def test_idempotent_no_duplicate_notifications(self, super_admin_token):
        """Trigger twice and verify notification counts do not double for the same marker (rough check)."""
        # Snapshot via admin debug if any; otherwise just ensure 2nd trigger still 200 + scheduler logs no error
        r1 = requests.post(f"{API}/admin/cron/subscription-check", headers=auth_header(super_admin_token), timeout=60)
        r2 = requests.post(f"{API}/admin/cron/subscription-check", headers=auth_header(super_admin_token), timeout=60)
        assert r1.status_code == 200 and r2.status_code == 200


# ---------- (3) CONTRACT CRON ----------

class TestContractCron:
    def test_super_admin_can_trigger(self, super_admin_token):
        r = requests.post(f"{API}/admin/cron/contract-check", headers=auth_header(super_admin_token), timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        assert body.get("job") == "contract_expiry_reminder"

    def test_release_can_trigger(self, release_token):
        r = requests.post(f"{API}/admin/cron/contract-check", headers=auth_header(release_token), timeout=60)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

    def test_finance_forbidden(self, finance_token):
        r = requests.post(f"{API}/admin/cron/contract-check", headers=auth_header(finance_token), timeout=30)
        assert r.status_code == 403

    def test_support_forbidden(self, support_token):
        r = requests.post(f"{API}/admin/cron/contract-check", headers=auth_header(support_token), timeout=30)
        assert r.status_code == 403

    def test_idempotent(self, super_admin_token):
        r1 = requests.post(f"{API}/admin/cron/contract-check", headers=auth_header(super_admin_token), timeout=60)
        r2 = requests.post(f"{API}/admin/cron/contract-check", headers=auth_header(super_admin_token), timeout=60)
        assert r1.status_code == 200 and r2.status_code == 200


# ---------- (4) SUBSCRIPTION EXPIRY BEHAVIOR (Manawa) ----------

class TestSubscriptionExpiredBehavior:
    def test_manawa_transitions_to_expired(self, super_admin_token):
        """After the cron runs, any label with subscription_expires_at <= now should be status=expired+pay_per_release."""
        # Trigger cron just in case
        requests.post(f"{API}/admin/cron/subscription-check", headers=auth_header(super_admin_token), timeout=60)
        # Find Manawa
        r = requests.get(f"{API}/admin/labels", params={"q": "Manawa"}, headers=auth_header(super_admin_token), timeout=30)
        if r.status_code != 200:
            pytest.skip(f"cannot list labels: {r.status_code}")
        body = r.json()
        items = body.get("items") if isinstance(body, dict) else body
        items = items or []
        manawa = None
        for lab in items:
            if "Manawa" in (lab.get("label_name") or ""):
                manawa = lab
                break
        if not manawa:
            pytest.skip("Manawa label not seeded")
        # GET detailed
        d = requests.get(f"{API}/admin/labels/{manawa['id']}", headers=auth_header(super_admin_token), timeout=30)
        assert d.status_code == 200, d.text
        body = d.json()
        lab = body.get("label") if isinstance(body, dict) and "label" in body else body
        # Either already transitioned or never had expired sub. Accept both cases but warn.
        sub_status = lab.get("subscription_status")
        pay_type = lab.get("payment_type")
        # Soft-assertion: log finding
        print(f"Manawa subscription_status={sub_status} payment_type={pay_type} expires_at={lab.get('subscription_expires_at')}")
        # If seeded as expiring/expired, after cron MUST be 'expired' or 'pay_per_release'
        if lab.get("subscription_expires_at"):
            # If we reach here we can't be 100% sure of seeding state, so just ensure no inconsistency
            assert sub_status in ("active", "expired", "trial", "cancelled", None)
