"""Iter56 — extended mandatory KYC coverage (limits, reviewer RBAC, notifications access)."""
import io
import os
import uuid

import requests
from PIL import Image

from tests.support_config import FINANCE, SUPPORT
from tests.test_phase43_release_approval_invoice import API, _db, _headers, _login
from tests.test_phase66_mandatory_label_kyc import _cleanup, _png_bytes, _seed_label


# Module coverage: /api/label/kyc, /api/label/logo, /api/label/kyc/ktp, /api/admin/kyc*, /api/notifications/me
def _jpeg_over_bytes(min_bytes: int) -> bytes:
    width = 1900
    height = 1900
    while True:
        raw = os.urandom(width * height * 3)
        image = Image.frombytes("RGB", (width, height), raw)
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=100, subsampling=0)
        payload = output.getvalue()
        if len(payload) > min_bytes:
            return payload
        width += 200
        height += 200


def test_unverified_label_notifications_access_but_core_blocked():
    db = _db()
    seeded = _seed_label(db, uuid.uuid4().hex[:10])
    token = _login(seeded["email"], seeded["password"])
    headers = _headers(token)
    try:
        notif = requests.get(f"{API}/notifications/me", headers=headers, timeout=30)
        assert notif.status_code == 200, notif.text
        notif_payload = notif.json()
        assert isinstance(notif_payload.get("items"), list)
        assert isinstance(notif_payload.get("unread_count"), int)

        blocked = requests.get(f"{API}/releases/", headers=headers, timeout=30)
        assert blocked.status_code == 403
        detail = blocked.json().get("detail") or {}
        assert detail.get("code") == "KYC_REQUIRED"
    finally:
        _cleanup(db, seeded)


def test_logo_5mb_and_ktp_10mb_limits_enforced_after_prerequisites():
    db = _db()
    seeded = _seed_label(db, uuid.uuid4().hex[:10])
    token = _login(seeded["email"], seeded["password"])
    headers = _headers(token)
    try:
        too_big_logo = _jpeg_over_bytes(5 * 1024 * 1024)
        logo_large = requests.post(
            f"{API}/label/logo",
            headers=headers,
            files={"file": ("logo-big.jpg", too_big_logo, "image/jpeg")},
            timeout=30,
        )
        assert logo_large.status_code == 413
        assert "5 MB" in logo_large.json().get("detail", "")

        logo_ok = requests.post(
            f"{API}/label/logo",
            headers=headers,
            files={"file": ("logo-ok.png", _png_bytes(), "image/png")},
            timeout=30,
        )
        assert logo_ok.status_code == 200, logo_ok.text

        too_big_ktp = _jpeg_over_bytes(10 * 1024 * 1024)
        ktp_large = requests.post(
            f"{API}/label/kyc/ktp",
            headers=headers,
            files={"file": ("ktp-big.jpg", too_big_ktp, "image/jpeg")},
            timeout=30,
        )
        assert ktp_large.status_code == 413
        assert "10 MB" in ktp_large.json().get("detail", "")
    finally:
        _cleanup(db, seeded)


def test_reviewer_rbac_blocks_finance_allows_support_and_pending_dashboard():
    db = _db()
    seeded = _seed_label(db, uuid.uuid4().hex[:10])
    label_token = _login(seeded["email"], seeded["password"])
    support_token = _login(SUPPORT["email"], SUPPORT["password"])
    finance_token = _login(FINANCE["email"], FINANCE["password"])
    try:
        logo_ok = requests.post(
            f"{API}/label/logo",
            headers=_headers(label_token),
            files={"file": ("logo-ok.png", _png_bytes(), "image/png")},
            timeout=30,
        )
        assert logo_ok.status_code == 200, logo_ok.text
        submit = requests.post(
            f"{API}/label/kyc/ktp",
            headers=_headers(label_token),
            files={"file": ("ktp-ok.png", _png_bytes(), "image/png")},
            timeout=30,
        )
        assert submit.status_code == 200, submit.text
        assert submit.json().get("status") == "pending_review"

        finance_queue = requests.get(f"{API}/admin/kyc", headers=_headers(finance_token), timeout=30)
        finance_detail = requests.get(f"{API}/admin/kyc/{seeded['label_id']}", headers=_headers(finance_token), timeout=30)
        finance_ktp = requests.get(f"{API}/admin/kyc/{seeded['label_id']}/ktp", headers=_headers(finance_token), timeout=30)
        finance_action = requests.post(
            f"{API}/admin/kyc/{seeded['label_id']}/action",
            headers=_headers(finance_token),
            json={"action": "reject", "reason": "Forbidden finance reviewer"},
            timeout=30,
        )
        assert finance_queue.status_code == 403
        assert finance_detail.status_code == 403
        assert finance_ktp.status_code == 403
        assert finance_action.status_code == 403

        support_queue = requests.get(f"{API}/admin/kyc", headers=_headers(support_token), timeout=30)
        assert support_queue.status_code == 200
        queue_items = support_queue.json()
        assert any(item.get("label_id") == seeded["label_id"] for item in queue_items)

        support_detail = requests.get(f"{API}/admin/kyc/{seeded['label_id']}", headers=_headers(support_token), timeout=30)
        assert support_detail.status_code == 200
        assert support_detail.json().get("label", {}).get("id") == seeded["label_id"]

        dashboard = requests.get(f"{API}/admin/dashboard", headers=_headers(support_token), timeout=30)
        assert dashboard.status_code == 200
        assert isinstance(dashboard.json().get("pending_kyc"), int)
    finally:
        _cleanup(db, seeded)


def test_verified_label_regression_core_endpoints_still_open():
    db = _db()
    seeded = _seed_label(db, uuid.uuid4().hex[:10])
    now = "2026-09-04T00:00:00+00:00"
    document_id = f"iter56-verified-{seeded['label_id']}"
    db.kyc_documents.insert_one({
        "id": document_id, "label_id": seeded["label_id"],
        "storage_key": f"kyc-private/{seeded['label_id']}/verified.png",
        "content_type": "image/png", "status": "verified", "is_current": True,
        "uploaded_at": now, "reviewed_at": now,
    })
    db.labels.update_one({"id": seeded["label_id"]}, {"$set": {
        "logo_storage_key": f"label-logo/{seeded['label_id']}/verified.png",
        "kyc_document_id": document_id, "kyc_status": "verified", "kyc_verified_at": now,
    }})
    token = _login(seeded["email"], seeded["password"])
    headers = _headers(token)
    try:
        kyc = requests.get(f"{API}/label/kyc", headers=headers, timeout=30)
        assert kyc.status_code == 200, kyc.text
        assert kyc.json().get("is_verified") is True

        releases = requests.get(f"{API}/releases/", headers=headers, timeout=30)
        assert releases.status_code == 200, releases.text
        assert isinstance(releases.json(), list)

        royalty = requests.get(f"{API}/royalty/summary", headers=headers, timeout=30)
        assert royalty.status_code == 200, royalty.text
        assert "total_idr" in royalty.json().get("summary", {})
    finally:
        _cleanup(db, seeded)
