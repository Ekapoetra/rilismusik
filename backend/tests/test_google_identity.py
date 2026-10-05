"""Offline API/security checks using real signatures, no Google or Atlas writes."""
import asyncio
import copy
import json
import time
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from test_vercel_preview import app
from fastapi import HTTPException
from fastapi.testclient import TestClient
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import jwt
from pymongo.errors import DuplicateKeyError
from routes import google_identity as google
from auth_utils import decode_token

CLIENT_ID = "test-client.apps.googleusercontent.com"
ORIGIN = "https://preview.example.invalid"


def matches(doc, query):
    for key, value in query.items():
        if key == "$or":
            if not any(matches(doc, child) for child in value): return False
        elif isinstance(value, dict) and "$exists" in value:
            if (key in doc) != value["$exists"]: return False
        elif doc.get(key) != value: return False
    return True


class Collection:
    def __init__(self, docs=()): self.docs = copy.deepcopy(list(docs))
    async def find_one(self, query, *args):
        return next((copy.deepcopy(d) for d in self.docs if matches(d, query)), None)
    async def insert_one(self, doc):
        if any(d.get("_id") == doc.get("_id") for d in self.docs):
            raise DuplicateKeyError("fixture duplicate")
        self.docs.append(copy.deepcopy(doc))
    async def update_one(self, query, update):
        for d in self.docs:
            if matches(d, query):
                d.update(update["$set"])
                return SimpleNamespace(matched_count=1)
        return SimpleNamespace(matched_count=0)


class GoogleIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Offline Google fixture")])
        cls.cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(cls.key.public_key()).serial_number(1)
            .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=1))
            .sign(cls.key, hashes.SHA256()).public_bytes(serialization.Encoding.PEM).decode())

    def setUp(self):
        self.env = patch.dict("os.environ", {"GOOGLE_CLIENT_ID": CLIENT_ID})
        self.env.start()
        self.user = {"id":"label-user", "email":"label@gmail.com", "role":"label",
                     "status":"active", "password_hash":"never-return", "token_version":3}
        self.label = {"id":"label-1", "user_id":"label-user", "account_status":"active",
                      "royalty_percentage_default":80}
        self.db = SimpleNamespace(users=Collection([self.user]), labels=Collection([self.label]),
            google_identities=Collection(), google_auth_sessions=Collection())
        self.db_patch = patch.object(google, "db", self.db)
        self.db_patch.start()
        self.certs_patch = patch.object(google, "_certificates", AsyncMock(return_value=json.dumps({"test-key":self.cert}).encode()))
        self.certs_patch.start()
        self.client = TestClient(app, base_url=ORIGIN, headers={"Origin": ORIGIN})
        self.nonce = self.client.get("/api/auth/google/nonce").json()["nonce"]

    def tearDown(self):
        app.dependency_overrides.pop(google.get_current_user, None)
        self.client.close()
        self.certs_patch.stop(); self.db_patch.stop(); self.env.stop()

    def token(self, **changes):
        payload = {"aud":CLIENT_ID, "iss":"https://accounts.google.com", "sub":"google-sub-1",
            "email":self.user["email"], "email_verified":True, "iat":int(time.time()),
            "exp":int(time.time())+3600, "nonce":self.nonce}
        payload.update(changes)
        return jwt.encode(payload, self.key, algorithm="RS256", headers={"kid":"test-key"})

    def login(self, token=None):
        return self.client.post("/api/auth/google/id-token", json={"credential":token or self.token()})

    def test_success_sets_app_cookies_and_redacts_secrets(self):
        response = self.login()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn("password_hash", response.text)
        self.assertNotIn("royalty_percentage", response.text)
        self.assertNotIn("access_token", response.json())
        payload = decode_token(self.client.cookies["access_token"])
        self.assertEqual((payload["sub"],payload["role"],payload["tv"]), ("label-user","label",3))
        self.assertIn("HttpOnly", response.headers["set-cookie"])
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(self.db.google_identities.docs[0]["_id"], "google-sub-1")
        self.assertNotIn("credential", self.db.google_auth_sessions.docs[0])
        self.assertEqual(response.json()["user"]["google_subject"], "google-sub-1")
        # Google sign-in never changes the account's verification state.
        self.assertIsNone(response.json()["user"].get("email_verified_at"))

    def test_forged_signature_is_rejected(self):
        token = self.token().split(".")
        token[-1] = "A" * len(token[-1])
        self.assertEqual(self.login(".".join(token)).status_code, 401)
        self.assertEqual(self.db.google_auth_sessions.docs, [])

    def test_wrong_audience_issuer_expiry_are_rejected(self):
        for changes in ({"aud":"other-client"},{"iss":"https://attacker.invalid"},{"exp":int(time.time())-60}):
            with self.subTest(changes=changes):
                self.assertEqual(self.login(self.token(**changes)).status_code,401)
        self.assertEqual(self.db.google_auth_sessions.docs, [])

    def test_missing_or_wrong_nonce_is_rejected(self):
        self.assertEqual(self.login(self.token(nonce="other-nonce")).status_code,401)
        self.client.cookies.clear()
        self.assertEqual(self.login().status_code,401)

    def test_cross_origin_and_missing_origin_rejected(self):
        self.client.headers["Origin"] = "https://attacker.invalid"
        self.assertEqual(self.login().status_code,403)
        del self.client.headers["Origin"]
        self.assertEqual(self.login().status_code,403)

    def test_same_credential_cannot_be_used_twice_even_without_seeded_indexes(self):
        token = self.token()
        self.assertEqual(self.login(token).status_code,200)
        self.client.cookies.set(google.NONCE_COOKIE,self.nonce,domain="preview.example.invalid",path="/")
        self.assertEqual(self.login(token).status_code,409)
        self.assertEqual(len(self.db.google_auth_sessions.docs),1)

    def test_unknown_or_admin_user_not_auto_registered(self):
        self.assertEqual(self.login(self.token(email="unknown@gmail.com")).status_code,403)
        self.db.users.docs[0]["role"]="super_admin"
        self.assertEqual(self.login().status_code,403)
        self.assertEqual(len(self.db.users.docs),1)

    def test_inactive_merged_and_blacklisted_accounts_rejected(self):
        for status in ("suspended","disabled","merged"):
            self.db.users.docs[0]["status"] = status
            self.assertEqual(self.login().status_code,403)
        self.db.users.docs[0]["status"]="active"
        self.db.labels.docs[0]["account_status"]="blacklisted"
        self.assertEqual(self.login().status_code,403)

    def test_unverified_email_rejected(self):
        for value in (False, "true", None):
            self.assertEqual(self.login(self.token(email_verified=value)).status_code,401)

    def test_workspace_email_can_link_automatically(self):
        self.db.users.docs[0]["email"]="label@workspace.example"
        self.assertEqual(self.login(self.token(email="label@workspace.example",hd="workspace.example")).status_code,200)

    def test_third_party_email_needs_authenticated_link(self):
        self.db.users.docs[0]["email"]="label@other.example"
        response=self.login(self.token(email="label@other.example"))
        self.assertEqual(response.status_code,403)
        self.assertIn("Profil",response.text)
        self.assertEqual(self.db.google_identities.docs,[])

    def test_link_requires_authentication_and_same_email(self):
        self.assertEqual(self.client.post("/api/auth/google/link",json={"credential":self.token()}).status_code,401)
        async def current(): return copy.deepcopy(self.db.users.docs[0])
        app.dependency_overrides[google.get_current_user] = current
        wrong=self.client.post("/api/auth/google/link",json={"credential":self.token(email="other@gmail.com")})
        self.assertEqual(wrong.status_code,403)
        self.assertEqual(self.db.google_identities.docs,[])

    def test_link_then_login_uses_stable_subject_for_third_party_email(self):
        self.db.users.docs[0]["email"]="label@other.example"
        async def current(): return copy.deepcopy(self.db.users.docs[0])
        app.dependency_overrides[google.get_current_user]=current
        token=self.token(email="label@other.example")
        response=self.client.post("/api/auth/google/link",json={"credential":token})
        self.assertEqual(response.status_code,200,response.text)
        self.nonce=self.client.get("/api/auth/google/nonce").json()["nonce"]
        # The linked stable subject is authoritative even if Google email changes.
        self.assertEqual(self.login(self.token(email="changed@other.example")).status_code,200)

    def test_profile_link_does_not_change_verification_status(self):
        self.db.users.docs[0].update(email_verified_at=None)
        self.db.labels.docs[0].update(kyc_status="incomplete")
        label_before = copy.deepcopy(self.db.labels.docs[0])
        async def current(): return copy.deepcopy(self.db.users.docs[0])
        app.dependency_overrides[google.get_current_user] = current
        with patch.object(google, "log_activity", AsyncMock()) as audit:
            response = self.client.post("/api/auth/google/link", json={"credential": self.token()})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["google_email"], "label@gmail.com")
        stored = self.db.users.docs[0]
        self.assertEqual(stored["google_subject"], "google-sub-1")
        self.assertEqual(stored["google_email"], "label@gmail.com")
        self.assertTrue(stored["google_linked_at"])
        self.assertIsNone(stored["email_verified_at"])
        self.assertEqual(stored["status"], "active")
        self.assertEqual(self.db.labels.docs[0], label_before)
        audit.assert_awaited_once()
        # An already verified account stays verified with the same timestamp.
        self.db.users.docs[0].update(email_verified_at="2026-01-01T00:00:00+00:00", google_subject=None)
        self.db.google_identities.docs.clear()
        self.nonce = self.client.get("/api/auth/google/nonce").json()["nonce"]
        with patch.object(google, "log_activity", AsyncMock()):
            self.assertEqual(self.client.post("/api/auth/google/link", json={"credential": self.token()}).status_code, 200)
        self.assertEqual(self.db.users.docs[0]["email_verified_at"], "2026-01-01T00:00:00+00:00")

    def test_google_login_after_profile_link_keeps_email_unverified(self):
        self.db.users.docs[0].update(email="owner@company.example", email_verified_at=None)
        self.assertEqual(self.login(self.token(email="owner@company.example")).status_code, 403)
        self.nonce = self.client.get("/api/auth/google/nonce").json()["nonce"]
        async def current(): return copy.deepcopy(self.db.users.docs[0])
        app.dependency_overrides[google.get_current_user] = current
        with patch.object(google, "log_activity", AsyncMock()):
            linked = self.client.post("/api/auth/google/link", json={"credential": self.token(email="owner@company.example")})
        self.assertEqual(linked.status_code, 200, linked.text)
        for email in ("owner@company.example", "changed@company.example"):
            self.nonce = self.client.get("/api/auth/google/nonce").json()["nonce"]
            self.assertEqual(self.login(self.token(email=email)).status_code, 200)
            self.assertIsNone(self.db.users.docs[0]["email_verified_at"])

    def test_other_google_subject_cannot_replace_existing_binding(self):
        self.db.users.docs[0]["google_subject"]="different-sub"
        self.assertEqual(self.login().status_code,409)
        self.assertEqual(self.db.google_auth_sessions.docs,[])

    def test_missing_configuration_and_provider_outage_fail_cleanly(self):
        with patch.dict("os.environ",{"GOOGLE_CLIENT_ID":""}):
            self.assertEqual(self.client.get("/api/auth/google/nonce").status_code,503)
        self.certs_patch.stop()
        self.certs_patch=patch.object(google,"_certificates",AsyncMock(side_effect=HTTPException(503,"Google belum dapat dihubungi.")))
        self.certs_patch.start()
        response=self.login()
        self.assertEqual(response.status_code,503)
        self.assertEqual(self.db.google_auth_sessions.docs,[])

    def test_input_size_is_limited_and_preview_still_blocks_business_writes(self):
        self.assertEqual(self.login("x"*9000).status_code,422)
        for path in ("/api/auth/register","/api/payments/create","/api/label/me"):
            self.assertEqual(self.client.post(path,json={}).status_code,503)


class CertificateCacheTests(unittest.IsolatedAsyncioTestCase):
    async def test_certificate_cache_reuses_response_and_refreshes_after_expiry(self):
        google._cert_cache.update(data=b"",until=0)
        google._cert_lock=asyncio.Lock()
        response=MagicMock()
        response.json.return_value={"key":"fixture-certificate"}
        response.headers={"cache-control":"public, max-age=120", "age":"20"}
        client=MagicMock()
        client.get=AsyncMock(return_value=response)
        client.__aenter__=AsyncMock(return_value=client)
        client.__aexit__=AsyncMock(return_value=None)
        with patch.object(google.httpx,"AsyncClient",return_value=client):
            first=await google._certificates()
            self.assertEqual(await google._certificates(),first)
            self.assertEqual(client.get.await_count,1)
            google._cert_cache["until"]=0
            self.assertEqual(await google._certificates(),first)
            self.assertEqual(client.get.await_count,2)
        google._cert_cache.update(data=b"",until=0)

if __name__ == "__main__": unittest.main()
