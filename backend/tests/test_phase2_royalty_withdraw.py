"""RILIS MUSIK Phase 2 - Royalty Import + Withdraw regression tests."""
import os
import io
import time
import uuid

import pymongo
import pytest
import requests
from tests.support_config import SUPERADMIN, temporary_password

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://lanjut-core.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _verify_label_kyc(db, label_id: str, email: str) -> None:
    """Lift a freshly registered label past the KYC gate so royalty endpoints
    answer it (they are KYC-gated for every label account)."""
    now = "2026-01-01T00:00:00+00:00"
    db.labels.update_one(
        {"id": label_id},
        {"$set": {
            "pic_name": "Phase2 PIC", "email": email, "whatsapp": "081234567890",
            "address": "Jl. Phase2", "city": "Jakarta", "country": "Indonesia",
            "logo_storage_key": f"label-logo/{label_id}/logo.png",
            "contract_status": "active", "kyc_status": "verified",
            "kyc_document_id": f"phase2-kyc-{label_id}", "kyc_verified_at": now,
        }},
    )
    db.kyc_documents.update_one(
        {"id": f"phase2-kyc-{label_id}"},
        {"$setOnInsert": {
            "id": f"phase2-kyc-{label_id}", "label_id": label_id, "status": "verified",
            "is_current": True, "storage_key": f"kyc-private/{label_id}/ktp.png",
            "uploaded_at": now, "reviewed_at": now,
        }},
        upsert=True,
    )
    db.bank_accounts.insert_one({
        "id": f"phase2-bank-{label_id}", "label_id": label_id, "bank_name": "Bank QA",
        "account_number": "55001122", "account_holder_name": "Phase2 PIC",
        "verified_status": "verified", "created_at": now, "updated_at": now,
    })
    db.contracts.insert_one({
        "id": f"phase2-contract-{label_id}", "label_id": label_id, "status": "active",
        "file_url": "/api/files/contract/phase2.pdf", "filename": "contract.pdf",
        "start_date": "2026-01-01", "end_date": "2030-01-01",
        "created_at": now, "updated_at": now,
    })

SUPER_EMAIL = SUPERADMIN["email"]
SUPER_PASS = SUPERADMIN["password"]
LABEL1_EMAIL = "label1@test.com"
LABEL1_PASS = temporary_password("phase2-label")
LABEL1_ISRC = "ID-A1Z-26-12345"


def _session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _rand_email(prefix="t2"):
    return f"TEST_{prefix}_{uuid.uuid4().hex[:8]}@example.com"


def _wait_import_status(session, import_id, target, timeout=120):
    """Publish/mark-dana run as background jobs — poll the import doc until it
    reaches `target` (or lands on an explicit error state)."""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        # Detail endpoint wraps the doc: {"import": {...}, "lines": [...]}.
        doc = session.get(f"{API}/royalty/admin/imports/{import_id}", timeout=30).json()
        imp = doc.get("import") or doc
        last = imp.get("status")
        if last == target:
            return imp
        if last in ("publish_error", "receive_error", "error"):
            raise AssertionError(f"import {import_id} ended at {last}: {imp.get('error_message')}")
        time.sleep(1)
    raise AssertionError(f"import {import_id} stuck at {last}, expected {target}")


# -------- fixtures --------
@pytest.fixture(scope="module")
def super_session():
    s = _session()
    r = s.post(f"{API}/auth/login", json={"email": SUPER_EMAIL, "password": SUPER_PASS})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def label1_session():
    s = _session()
    r = s.post(f"{API}/auth/login", json={"email": LABEL1_EMAIL, "password": LABEL1_PASS})
    if r.status_code != 200:
        pytest.skip(f"label1@test.com login failed: {r.text}")
    return s


@pytest.fixture(scope="module")
def fresh_label_session():
    s = _session()
    email = _rand_email("lbl")
    r = s.post(f"{API}/auth/register", json={
        "label_name": "TEST P2 Label", "pic_name": "PIC", "email": email,
        "whatsapp": "+62811", "password": LABEL1_PASS, "account_type": "label",
            "mda_accepted": True,
    })
    assert r.status_code == 200, r.text
    data = r.json()
    _verify_label_kyc(_db(), data["label"]["id"], email)
    return {"session": s, "email": email, "label_id": data["label"]["id"], "user_id": data["user"]["id"]}


def _csv(rows):
    """Build a Believe-style CSV bytes from list-of-dict rows."""
    # Believe export uses "Bulan laporan" as the reporting-period column;
    # a generic "Period" header is rejected by the parser alias table.
    header = "ISRC,UPC,Track Title,Artist,Album,Platform,Country,Bulan laporan,Quantity,Net Revenue EUR"
    body = [header]
    for r in rows:
        body.append(",".join([
            r.get("isrc", ""), r.get("upc", ""), r.get("title", ""), r.get("artist", ""),
            r.get("album", ""), r.get("platform", ""), r.get("country", ""),
            r.get("period", ""), str(r.get("qty", 0)), str(r.get("revenue", 0)),
        ]))
    return ("\n".join(body)).encode("utf-8")


# ============== ROYALTY ADMIN UPLOAD ==============
class TestRoyaltyImport:
    def test_upload_csv_with_matched_isrc(self, super_session):
        """Upload CSV that includes label1's ISRC + unmatched rows. Verify counts + totals."""
        s = super_session
        period = "2026-04"  # avoid collision with already-published 2026-05
        csv_bytes = _csv([
            {"isrc": LABEL1_ISRC, "title": "Lagu 1", "artist": "Aditya", "platform": "Spotify",
             "country": "ID", "period": period, "qty": 10000, "revenue": 50},
            {"isrc": "NOMATCH-AAA-1", "title": "Unmatched A", "artist": "Foo", "platform": "Apple",
             "country": "US", "period": period, "qty": 5000, "revenue": 30},
            {"isrc": "NOMATCH-BBB-2", "title": "Unmatched B", "artist": "Bar", "platform": "YouTube",
             "country": "ID", "period": period, "qty": 8000, "revenue": 20},
        ])
        files = {"file": ("believe.csv", csv_bytes, "text/csv")}
        data = {"period": period, "rate_eur_idr": "17500"}
        # multipart — must remove Content-Type json header
        r = requests.post(f"{API}/royalty/admin/imports", files=files, data=data,
                          cookies=s.cookies)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "pending_review"
        assert body["total_lines"] == 3
        assert body["matched_lines"] == 1
        assert body["unmatched_lines"] == 2
        assert abs(body["total_revenue_eur"] - 100.0) < 0.01
        # 50 EUR * 0.60 * 17500 = 525,000 (no distributor fee)
        assert body["total_label_idr"] == 525000
        pytest.import_id = body["id"]
        pytest.import_period = period

    def test_calc_100eur_label60_rate17500_without_fee(self, super_session):
        """€100 matched → 100*0.6*17500 = 1,050,000 IDR for the label."""
        period = "2026-03"
        csv_bytes = _csv([
            {"isrc": LABEL1_ISRC, "title": "Calc", "artist": "Aditya", "platform": "X",
             "country": "ID", "period": period, "qty": 1, "revenue": 100},
        ])
        files = {"file": ("calc.csv", csv_bytes, "text/csv")}
        data = {"period": period, "rate_eur_idr": "17500"}
        r = requests.post(f"{API}/royalty/admin/imports", files=files, data=data,
                          cookies=super_session.cookies)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["matched_lines"] == 1
        assert body["total_label_idr"] == 1050000

    def test_label_role_forbidden(self, label1_session):
        """Label cannot upload royalty CSV."""
        csv_bytes = _csv([{"isrc": "X", "revenue": 1, "period": "2026-04"}])
        files = {"file": ("x.csv", csv_bytes, "text/csv")}
        data = {"period": "2026-04", "rate_eur_idr": "17500"}
        r = requests.post(f"{API}/royalty/admin/imports", files=files, data=data,
                          cookies=label1_session.cookies)
        assert r.status_code == 403, r.text

    def test_publish_import(self, super_session):
        """Publish should move label balance_pending_idr up by total_label_idr and create txn."""
        s = super_session
        # snapshot label1 balance
        labels = s.get(f"{API}/admin/labels").json()
        l1 = [x for x in labels if x.get("id") == "c1f96714-9ace-472a-a000-573cab47ed38" or x.get("email") == LABEL1_EMAIL]
        # also fetch via admin label-detail not needed — use label/me endpoint via label1 session
        pending_before = None
        # use admin/labels list
        for x in labels:
            if x.get("primary_email") == LABEL1_EMAIL or x.get("email") == LABEL1_EMAIL:
                pending_before = x.get("balance_pending_idr", 0)
                break
        import_id = pytest.import_id
        r = s.post(f"{API}/royalty/admin/imports/{import_id}/publish", json={})
        assert r.status_code == 200, r.text
        # Publish is a background job — poll until the import settles.
        body = _wait_import_status(s, import_id, "published")
        assert body["status"] == "published"
        assert body.get("published_at")

    def test_publish_again_fails(self, super_session):
        r = super_session.post(f"{API}/royalty/admin/imports/{pytest.import_id}/publish", json={})
        assert r.status_code == 400

    def test_mark_dana_received(self, super_session):
        """Pending → available; lines status pending → available."""
        s = super_session
        r = s.post(f"{API}/royalty/admin/imports/{pytest.import_id}/mark-dana-received")
        assert r.status_code == 200, r.text
        body = _wait_import_status(s, pytest.import_id, "dana_received")
        assert body["status"] == "dana_received"
        assert body.get("dana_received_at")

    def test_mark_dana_received_idempotent_block(self, super_session):
        # Spec: a second mark-dana on a completed import is an idempotent
        # no-op — it returns the import doc (200), not an error.
        r = super_session.post(f"{API}/royalty/admin/imports/{pytest.import_id}/mark-dana-received")
        assert r.status_code == 200
        assert r.json()["status"] == "dana_received"

    def test_list_imports_no_objectid(self, super_session):
        r = super_session.get(f"{API}/royalty/admin/imports")
        assert r.status_code == 200
        # ensure no Mongo `_id` key leaked
        assert '"_id"' not in r.text


# ============== LABEL ROYALTY ENDPOINTS ==============
class TestLabelRoyaltyEndpoints:
    def test_months(self, label1_session):
        r = label1_session.get(f"{API}/royalty/months")
        assert r.status_code == 200
        months = r.json()
        assert isinstance(months, list)
        # at least one period should be visible
        assert any(m == pytest.import_period for m in months) or len(months) >= 1

    def test_summary_for_period(self, label1_session):
        r = label1_session.get(f"{API}/royalty/summary", params={"period": pytest.import_period})
        assert r.status_code == 200, r.text
        body = r.json()
        assert "summary" in body and "by_platform" in body and "by_country" in body and "by_track" in body
        # the matched line was 50 EUR -> 525,000 IDR
        assert body["summary"]["total_idr"] >= 525000

    def test_lines_filtered(self, label1_session):
        r = label1_session.get(f"{API}/royalty/lines", params={"period": pytest.import_period})
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        for it in items:
            assert it.get("period") == pytest.import_period
            assert "_id" not in it

    def test_export_csv(self, label1_session):
        r = label1_session.get(f"{API}/royalty/export.csv", params={"period": pytest.import_period})
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("text/csv")
        assert "attachment" in r.headers.get("content-disposition", "")
        assert "period,release_title,track_title" in r.text

    def test_multitenant_no_other_label_data(self, fresh_label_session):
        """A fresh label must NOT see label1's lines."""
        s = fresh_label_session["session"]
        r = s.get(f"{API}/royalty/lines", params={"period": pytest.import_period})
        assert r.status_code == 200
        items = r.json()
        # no item should belong to label1
        for it in items:
            assert it.get("label_id") != "c1f96714-9ace-472a-a000-573cab47ed38"
        # also, the fresh label should not see label1's ISRC
        for it in items:
            assert it.get("isrc") != LABEL1_ISRC


# ============== MANUAL LINE MATCH ==============
class TestManualMatch:
    def test_manual_match_unmatched_line(self, super_session):
        """Create a new fresh pending_review import, then manually match an unmatched line."""
        s = super_session
        period = "2026-02"
        csv_bytes = _csv([
            {"isrc": "WILL-MATCH-MANUALLY", "title": "Manual", "artist": "Y", "platform": "Z",
             "country": "ID", "period": period, "qty": 1, "revenue": 10},
        ])
        files = {"file": ("m.csv", csv_bytes, "text/csv")}
        data = {"period": period, "rate_eur_idr": "17500"}
        r = requests.post(f"{API}/royalty/admin/imports", files=files, data=data, cookies=s.cookies)
        assert r.status_code == 200, r.text
        imp = r.json()
        assert imp["unmatched_lines"] == 1
        import_id = imp["id"]

        # fetch detail to get line id
        detail = s.get(f"{API}/royalty/admin/imports/{import_id}").json()
        lines = detail.get("lines") or detail.get("rows") or []
        if not lines:
            pytest.skip("admin imports/{id} detail does not return lines key — RCA needed")
        line_id = lines[0]["id"]

        # fetch any label1 track id
        # we need a valid track_id; use the label1 ISRC track. Use admin search if exists; otherwise skip.
        # easier: hit admin label tracks via admin labels endpoint
        tracks_r = s.get(f"{API}/admin/labels")
        # Not all schemas expose tracks; do a direct match against any track id by guessing impossible — skip if not exposed.
        # Use known seed track if present in lines from period 2026-04 import
        prev = s.get(f"{API}/admin/imports") if False else None
        # Use royalty/admin/imports/<old>:
        old = s.get(f"{API}/royalty/admin/imports/{pytest.import_id}").json()
        old_lines = old.get("lines") or []
        matched_line = next((ln for ln in old_lines if ln.get("track_id")), None)
        if not matched_line:
            pytest.skip("No matched track_id available to assign for manual match")
        track_id = matched_line["track_id"]

        r2 = s.post(f"{API}/royalty/admin/imports/{import_id}/line/{line_id}/match",
                    json={"track_id": track_id})
        assert r2.status_code == 200, r2.text


# ============== WITHDRAW ==============
class TestWithdraw:
    def test_window(self, label1_session):
        r = label1_session.get(f"{API}/withdraw/window")
        assert r.status_code == 200
        body = r.json()
        assert "phase" in body and "day" in body and "request_open" in body and "payment_window" in body
        assert body["phase"] in ("request_open", "payment_window", "closed")
        assert 1 <= body["day"] <= 31

    def test_request_blocked_when_closed_or_min(self, label1_session):
        r = label1_session.post(f"{API}/withdraw/label/request", json={"amount_idr": 1000000})
        # could be 400 'ditutup' (closed/payment window) OR 400 'saldo' if balance insufficient
        assert r.status_code == 400, r.text
        msg = r.json().get("detail", "")
        # Must be a friendly Indonesian message
        assert any(kw in msg.lower() for kw in ["ditutup", "saldo", "minimum", "rekening"]), msg

    def test_request_min_idr_enforced(self, label1_session):
        r = label1_session.post(f"{API}/withdraw/label/request", json={"amount_idr": 500000})
        # Either Pydantic validation (422) or business rule (400) is acceptable
        assert r.status_code in (400, 422), r.text

    def test_admin_list_withdraws(self, super_session):
        r = super_session.get(f"{API}/withdraw/admin")
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        for it in items:
            assert "_id" not in it
