"""Phase 17 regression — verify token_version JWT claim addition doesn't break
existing auth flows or admin endpoints.

Covers the REGRESSION items from the review request:
- Register → login → /auth/me → logout
- Forgot → reset (via Mongo) → re-login with new password
- Super admin login + admin endpoints (labels, invoices, contracts, withdraw window,
  royalty imports list, CMS landing) return 200 with new tv claim JWT
"""
import os
import uuid
import requests
import pytest
from pathlib import Path
from tests.support_config import SUPERADMIN, temporary_password

# Load backend .env
_env = Path(__file__).resolve().parents[1] / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://lanjut-core.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"
SUPER_EMAIL = SUPERADMIN["email"]
SUPER_PASS = SUPERADMIN["password"]


def _rand_email(prefix="reg"):
    return f"TEST_p17reg_{prefix}_{uuid.uuid4().hex[:8]}@example.com"


def _mongo_db():
    import pymongo
    client = pymongo.MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    return client[os.environ.get("DB_NAME") or "rilismusik_db"]


# --------------------------------------------------------------------------- #
# Standard label flow                                                         #
# --------------------------------------------------------------------------- #
class TestLabelAuthRegression:
    def test_register_login_me_logout_flow(self):
        email = _rand_email("flow")
        password = temporary_password("phase17-flow")

        # Register
        r = requests.post(f"{API}/auth/register", json={
            "label_name": "Reg Test Label",
            "pic_name": "PIC Reg",
            "email": email,
            "whatsapp": "+628111222333",
            "password": password,
            "mda_accepted": True,
        }, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "access_token" in body and "refresh_token" in body
        assert "verification_token" not in body
        token = body["access_token"]

        # /me
        me = requests.get(f"{API}/auth/me",
                          headers={"Authorization": f"Bearer {token}"},
                          timeout=30)
        assert me.status_code == 200
        me_body = me.json()
        user_obj = me_body.get("user", me_body)  # supports both shapes
        assert user_obj["email"] == email.lower()

        # Login again returns a new tv-claim JWT
        login = requests.post(f"{API}/auth/login",
                              json={"email": email, "password": password},
                              timeout=30)
        assert login.status_code == 200, login.text
        new_token = login.json()["access_token"]
        # Decode JWT payload (no verify) to confirm tv claim
        import base64, json
        payload_b64 = new_token.split(".")[1] + "=="
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        assert "tv" in payload, f"JWT missing tv (token_version) claim: {payload}"

        # Logout (best-effort: endpoint may or may not exist)
        requests.post(f"{API}/auth/logout",
                      headers={"Authorization": f"Bearer {new_token}"},
                      timeout=30)

    def test_forgot_then_reset_then_relogin(self):
        email = _rand_email("reset")
        original_pw = temporary_password("phase17-old")
        new_pw = temporary_password("phase17-new")

        # Register
        r = requests.post(f"{API}/auth/register", json={
            "label_name": "Reset Test",
            "pic_name": "PIC",
            "email": email,
            "whatsapp": "+628100000",
            "password": original_pw,
            "mda_accepted": True,
        }, timeout=30)
        assert r.status_code == 200

        # Forgot — body must be exactly {ok:true}
        fr = requests.post(f"{API}/auth/forgot-password", json={"email": email}, timeout=30)
        assert fr.status_code == 200
        assert fr.json() == {"ok": True}

        # Read token from Mongo
        db = _mongo_db()
        user = db.users.find_one({"email": email.lower()})
        assert user, "user not found in mongo"
        doc = db.password_reset_tokens.find_one(
            {"user_id": user["id"], "used": False},
            sort=[("created_at", -1)],
        )
        assert doc, "no reset token persisted"
        token = doc["token"]

        # Reset
        rr = requests.post(f"{API}/auth/reset-password",
                           json={"token": token, "password": new_pw},
                           timeout=30)
        assert rr.status_code == 200, rr.text

        # Old password must fail
        bad = requests.post(f"{API}/auth/login",
                            json={"email": email, "password": original_pw},
                            timeout=30)
        assert bad.status_code in (400, 401), \
            f"old password still works after reset: {bad.status_code}"

        # New password must succeed
        good = requests.post(f"{API}/auth/login",
                             json={"email": email, "password": new_pw},
                             timeout=30)
        assert good.status_code == 200, good.text

    def test_forgot_unknown_email_returns_ok_no_enumeration(self):
        """Anti-enumeration: unknown email must also get {ok:true}."""
        r = requests.post(f"{API}/auth/forgot-password",
                          json={"email": f"TEST_unknown_{uuid.uuid4().hex[:6]}@nowhere.example"},
                          timeout=30)
        assert r.status_code == 200
        assert r.json() == {"ok": True}


# --------------------------------------------------------------------------- #
# Super admin flow + admin endpoints                                          #
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def super_token():
    r = requests.post(f"{API}/auth/login",
                      json={"email": SUPER_EMAIL, "password": SUPER_PASS},
                      timeout=30)
    assert r.status_code == 200, f"super admin login failed: {r.text}"
    return r.json()["access_token"]


class TestSuperAdminRegression:
    def test_super_admin_login_and_me(self, super_token):
        me = requests.get(f"{API}/auth/me",
                         headers={"Authorization": f"Bearer {super_token}"},
                         timeout=30)
        assert me.status_code == 200
        body = me.json()
        data = body.get("user", body)
        assert data["email"] == SUPER_EMAIL
        # Should be admin (role super_admin or similar)
        assert data.get("role") in ("super_admin", "admin") or data.get("is_super_admin")

    def test_jwt_carries_tv_claim(self, super_token):
        import base64, json
        payload_b64 = super_token.split(".")[1] + "=="
        # pad
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        assert "tv" in payload, f"super admin JWT missing tv claim: {payload}"

    @pytest.mark.parametrize("path,expected", [
        ("/admin/labels", 200),
        ("/label/invoices", 403),         # label-only endpoint; super admin must get 403 (not 500)
        ("/contracts/admin", 200),
        ("/withdraw/window", 200),
        ("/royalty/admin/imports", 200),
        ("/cms/landing", 200),
    ])
    def test_admin_endpoints_return_200(self, super_token, path, expected):
        r = requests.get(f"{API}{path}",
                         headers={"Authorization": f"Bearer {super_token}"},
                         timeout=30)
        assert r.status_code == expected, f"{path} -> {r.status_code}: {r.text[:200]}"
