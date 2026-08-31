"""Phase 44 — CMS signature upload and copyright PDF generation."""
import asyncio
import os
import uuid
from io import BytesIO

import pymongo
import requests
from dotenv import load_dotenv
from PIL import Image

from auth_utils import hash_password
from tests.support_config import SUPERADMIN, temporary_password


load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/frontend/.env", override=True)
import storage_service
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _login(email, password):
    response = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _png_bytes():
    buffer = BytesIO()
    image = Image.new("RGBA", (480, 180), (255, 255, 255, 0))
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_cms_signature_generates_downloadable_copyright_pdf():
    db = _db()
    suffix = uuid.uuid4().hex[:10]
    now = "2026-09-01T00:00:00+00:00"
    user_id = f"phase44-user-{suffix}"
    label_id = f"phase44-label-{suffix}"
    release_id = f"phase44-release-{suffix}"
    email = f"phase44-{suffix}@example.com"
    password = temporary_password("Copyright")
    previous_documents = db.landing_settings.find_one({"key": "documents"}, {"_id": 0})
    admin_token = _login(SUPERADMIN["email"], SUPERADMIN["password"])
    signature_key = None
    db.users.insert_one({
        "id": user_id, "name": "Phase 44 Label", "email": email,
        "password_hash": hash_password(password), "role": "label", "status": "active",
        "token_version": 0, "email_verified_at": now, "created_at": now, "updated_at": now,
    })
    db.labels.insert_one({
        "id": label_id, "user_id": user_id, "label_name": "Label Hak Cipta",
        "account_status": "active", "created_at": now, "updated_at": now,
    })
    db.releases.insert_one({
        "id": release_id, "label_id": label_id, "release_title": "Karya Asli",
        "artist_name": "Artis Hak Cipta", "status": "approved",
        "copyright_line": "2026 Label Hak Cipta", "p_line": "2026 Label Hak Cipta",
        "created_at": now, "updated_at": now,
    })
    db.tracks.insert_one({
        "id": f"phase44-track-{suffix}", "release_id": release_id,
        "track_title": "Lagu Karya Asli", "track_number": 1,
    })
    try:
        upload = requests.post(
            f"{API}/cms/documents/upload-signature",
            files={"file": ("signature.png", _png_bytes(), "image/png")},
            headers=_headers(admin_token), timeout=60,
        )
        assert upload.status_code == 200, upload.text
        signature_url = upload.json()["url"]
        signature_key = upload.json()["key"]
        settings = requests.patch(
            f"{API}/cms/landing",
            json={"settings": {"documents": {
                "responsible_person_name": "Direktur Pengujian",
                "responsible_person_title": "Direktur Utama",
                "signature_url": signature_url,
                "stamp_url": "",
            }}},
            headers=_headers(admin_token), timeout=30,
        )
        assert settings.status_code == 200, settings.text

        label_token = _login(email, password)
        response = requests.get(
            f"{API}/releases/{release_id}/copyright-letter",
            headers=_headers(label_token), timeout=60,
        )
        assert response.status_code == 200, response.text[:300]
        assert response.headers["content-type"].startswith("application/pdf")
        assert response.content.startswith(b"%PDF-")
        assert len(response.content) > 3000
        release = db.releases.find_one({"id": release_id}, {"_id": 0})
        assert release["copyright_pdf_url"] == f"/api/files/copyright/{release_id}.pdf"
    finally:
        if previous_documents:
            db.landing_settings.replace_one({"key": "documents"}, previous_documents, upsert=True)
        else:
            db.landing_settings.delete_one({"key": "documents"})
        db.activity_logs.delete_many({"reference_id": {"$in": [signature_key, release_id]}})
        db.tracks.delete_many({"release_id": release_id})
        db.releases.delete_one({"id": release_id})
        db.labels.delete_one({"id": label_id})
        db.users.delete_one({"id": user_id})
        if signature_key:
            asyncio.run(storage_service.delete_object(key=signature_key))
        asyncio.run(storage_service.delete_object(key=f"copyright/{release_id}.pdf"))