"""Phase 66 — mandatory label KYC, private KTP access, and reviewer RBAC."""
import io
import uuid

import requests
from PIL import Image

import storage_service
from auth_utils import hash_password
from tests.support_config import FINANCE, SUPPORT, temporary_password
from tests.test_phase43_release_approval_invoice import API, _db, _headers, _login


def _png_bytes(width=80, height=50):
    output = io.BytesIO()
    Image.new("RGB", (width, height), color=(28, 110, 90)).save(output, format="PNG")
    return output.getvalue()


def _seed_label(db, suffix):
    now = "2026-09-04T00:00:00+00:00"
    user_id = f"phase66-user-{suffix}"
    label_id = f"phase66-label-{suffix}"
    email = f"phase66-{suffix}@example.com"
    password = temporary_password("KycFlow")
    db.users.insert_one({
        "id": user_id, "name": "PIC Phase 66", "email": email,
        "password_hash": hash_password(password), "role": "label", "status": "active",
        "token_version": 0, "email_verified_at": now, "created_at": now, "updated_at": now,
    })
    db.labels.insert_one({
        "id": label_id, "user_id": user_id, "label_name": "Label Phase 66",
        "pic_name": "PIC Phase 66", "email": email, "whatsapp": "081234567890",
        "address": "Jl. Verifikasi No. 66", "city": "Bandung", "country": "Indonesia",
        "kyc_status": "incomplete", "account_status": "active", "created_at": now, "updated_at": now,
    })
    db.bank_accounts.insert_one({
        "id": f"phase66-bank-{suffix}", "label_id": label_id, "bank_name": "BCA",
        "account_number": "6600123456", "account_holder_name": "PIC Phase 66",
        "verified_status": "pending", "created_at": now,
    })
    db.contracts.insert_one({
        "id": f"phase66-contract-{suffix}", "label_id": label_id, "status": "active",
        "start_date": "2026-01-01", "end_date": "2030-12-31", "created_at": now,
    })
    return {"user_id": user_id, "label_id": label_id, "email": email, "password": password}


def _cleanup(db, seeded):
    documents = list(db.kyc_documents.find({"label_id": seeded["label_id"]}, {"_id": 0, "storage_key": 1}))
    label = db.labels.find_one({"id": seeded["label_id"]}, {"_id": 0, "logo_storage_key": 1}) or {}
    for key in [label.get("logo_storage_key"), *[item.get("storage_key") for item in documents]]:
        if key:
            try:
                import asyncio
                asyncio.run(storage_service.delete_object(key=key))
            except Exception:
                pass
    db.notifications.delete_many({"meta.label_id": seeded["label_id"]})
    db.activity_logs.delete_many({"after_data.label_id": seeded["label_id"]})
    db.kyc_documents.delete_many({"label_id": seeded["label_id"]})
    db.bank_accounts.delete_many({"label_id": seeded["label_id"]})
    db.contracts.delete_many({"label_id": seeded["label_id"]})
    db.labels.delete_one({"id": seeded["label_id"]})
    db.users.delete_one({"id": seeded["user_id"]})


def test_mandatory_kyc_private_document_and_review_flow():
    db = _db()
    seeded = _seed_label(db, uuid.uuid4().hex[:10])
    token = _login(seeded["email"], seeded["password"])
    support_token = _login(SUPPORT["email"], SUPPORT["password"])
    finance_token = _login(FINANCE["email"], FINANCE["password"])
    headers = _headers(token)
    image = _png_bytes()
    try:
        initial = requests.get(f"{API}/label/kyc", headers=headers, timeout=30)
        assert initial.status_code == 200, initial.text
        assert initial.json()["status"] == "incomplete"
        assert "logo" in initial.json()["missing_keys"]

        blocked = requests.get(f"{API}/releases/", headers=headers, timeout=30)
        assert blocked.status_code == 403
        assert blocked.json()["detail"]["code"] == "KYC_REQUIRED"

        early_ktp = requests.post(
            f"{API}/label/kyc/ktp", headers=headers,
            files={"file": ("ktp.png", image, "image/png")}, timeout=30,
        )
        assert early_ktp.status_code == 409

        logo = requests.post(
            f"{API}/label/logo", headers=headers,
            files={"file": ("logo.png", image, "image/png")}, timeout=30,
        )
        assert logo.status_code == 200, logo.text
        assert logo.json()["logo_url"].startswith("/api/files/label-logo/")
        profile_with_logo = requests.get(f"{API}/label/me", headers=headers, timeout=30)
        dashboard_with_logo = requests.get(f"{API}/label/dashboard", headers=headers, timeout=30)
        assert profile_with_logo.status_code == dashboard_with_logo.status_code == 200
        assert profile_with_logo.json()["logo_url"] == logo.json()["logo_url"]
        assert dashboard_with_logo.json()["label"]["logo_url"] == logo.json()["logo_url"]

        submitted = requests.post(
            f"{API}/label/kyc/ktp", headers=headers,
            files={"file": ("ktp.png", image, "image/png")}, timeout=30,
        )
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["status"] == "pending_review"
        document = db.kyc_documents.find_one({"id": submitted.json()["id"]}, {"_id": 0})
        assert document["storage_key"].startswith(f"kyc-private/{seeded['label_id']}/")

        public = requests.get(f"{API}/files/{document['storage_key']}", timeout=30)
        assert public.status_code == 404
        own = requests.get(f"{API}/label/kyc/ktp", headers=headers, timeout=30)
        assert own.status_code == 200 and "no-store" in own.headers["cache-control"]
        admin_view = requests.get(f"{API}/admin/kyc/{seeded['label_id']}/ktp", headers=_headers(support_token), timeout=30)
        assert admin_view.status_code == 200

        forbidden_queue = requests.get(f"{API}/admin/kyc", headers=_headers(finance_token), timeout=30)
        assert forbidden_queue.status_code == 403
        queue = requests.get(f"{API}/admin/kyc", headers=_headers(support_token), timeout=30)
        assert queue.status_code == 200
        queued = next(item for item in queue.json() if item["label_id"] == seeded["label_id"])
        assert "storage_key" not in queued and "sha256" not in queued
        dashboard = requests.get(f"{API}/admin/dashboard", headers=_headers(support_token), timeout=30)
        assert dashboard.status_code == 200 and dashboard.json()["pending_kyc"] >= 1

        no_reason = requests.post(f"{API}/admin/kyc/{seeded['label_id']}/action", headers=_headers(support_token), json={"action": "reject"}, timeout=30)
        assert no_reason.status_code == 400
        rejected = requests.post(f"{API}/admin/kyc/{seeded['label_id']}/action", headers=_headers(support_token), json={"action": "reject", "reason": "Foto identitas kurang jelas"}, timeout=30)
        assert rejected.status_code == 200 and rejected.json()["kyc"]["status"] == "rejected"

        resubmitted = requests.post(
            f"{API}/label/kyc/ktp", headers=headers,
            files={"file": ("ktp-baru.png", image, "image/png")}, timeout=30,
        )
        assert resubmitted.status_code == 200, resubmitted.text
        approved = requests.post(f"{API}/admin/kyc/{seeded['label_id']}/action", headers=_headers(support_token), json={"action": "approve"}, timeout=30)
        assert approved.status_code == 200 and approved.json()["kyc"]["is_verified"] is True
        assert requests.get(f"{API}/releases/", headers=headers, timeout=30).status_code == 200

        changed = requests.patch(f"{API}/label/me", headers=headers, json={"address": "Jl. Identitas Baru No. 1"}, timeout=30)
        assert changed.status_code == 200 and changed.json()["kyc"]["status"] == "incomplete"
        assert requests.get(f"{API}/releases/", headers=headers, timeout=30).status_code == 403
    finally:
        _cleanup(db, seeded)