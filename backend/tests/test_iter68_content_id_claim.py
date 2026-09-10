"""Iter68 - Content ID claim flow (assets, validation, privacy, idempotency)."""
import asyncio
import json
import os
import uuid
from io import BytesIO
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pymongo
import pytest
import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw
from tests.support_config import SUPPORT, FINANCE

import storage_service


load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/backend/.env.test", override=True)
load_dotenv("/app/frontend/.env", override=True)

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
if not Path("/app/tests/iter66_ui_fixture_state.json").exists():
    pytest.skip("Seed isolated fixture with /app/tests/iter66_ui_fixture.py seed before running.", allow_module_level=True)
_fixture = json.loads(Path("/app/tests/iter66_ui_fixture_state.json").read_text())
OWNER_EMAIL = _fixture["seeded"]["email"]
OWNER_PASSWORD = _fixture["seeded"]["password"]
SUPPORT_EMAIL, SUPPORT_PASSWORD = SUPPORT["email"], SUPPORT["password"]
FINANCE_EMAIL, FINANCE_PASSWORD = FINANCE["email"], FINANCE["password"]
FIXTURE_RELEASE_ID = _fixture["release_id"]


def assert_no_storage(response):
    # RFC9111 §5.2.2.5: no-store forbids BOTH shared and private caches.
    # Preview's edge replaces the origin's "no-store, private" with
    # "no-store, no-cache, must-revalidate". Test the security property,
    # not byte-for-byte formatting of equivalent cache restrictions.
    directives = {part.strip().split("=", 1)[0].lower() for part in response.headers.get("cache-control", "").split(",")}
    assert "no-store" in directives, response.headers
    assert "public" not in directives, response.headers
    assert int(response.headers.get("age", "0")) == 0, response.headers


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _login(email: str, password: str) -> str:
    response = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=40)
    assert response.status_code == 200, response.text
    token = response.json().get("access_token")
    assert token, "Login succeeded without access_token"
    return token


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _image_bytes(kind: str = "signature", *, blank: bool = False) -> bytes:
    size = (640, 280) if kind == "signature" else (1100, 700)
    image = Image.new("RGB", size, "white")
    if not blank:
        draw = ImageDraw.Draw(image)
        if kind == "signature":
            draw.line((40, 180, 220, 80, 420, 210, 600, 110), fill="black", width=8)
        else:
            draw.rectangle((40, 40, 1060, 660), outline="black", width=6)
            draw.text((70, 90), "KTP QA FAKE - JANGAN GUNAKAN DATA NYATA", fill="black")
            draw.text((70, 150), "NIK: 0000000000000123", fill="black")
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def _upload_asset(token: str, release_id: str, kind: str, content: bytes, filename: str = "fixture.png", signature_mode: str = "upload"):
    return requests.post(
        f"{API}/tickets/content-id/assets",
        headers=_headers(token),
        data={"release_id": release_id, "kind": kind, "signature_mode": signature_mode},
        files={"file": (filename, content, "image/png")},
        timeout=60,
    )


@pytest.fixture(scope="module")
def state():
    db = _db()
    owner = db.users.find_one({"email": OWNER_EMAIL}, {"_id": 0, "id": 1})
    if not owner:
        pytest.skip("Iter66 owner fixture account not found")
    label = db.labels.find_one({"user_id": owner["id"]}, {"_id": 0, "id": 1})
    if not label:
        pytest.skip("Iter66 owner label not found")
    release = db.releases.find_one({"id": FIXTURE_RELEASE_ID, "label_id": label["id"]}, {"_id": 0, "id": 1})
    if not release:
        pytest.skip("Iter66 fixture release not found or no longer owned by fixture label")
    track_ids = [
        row["id"]
        for row in db.tracks.find({"release_id": FIXTURE_RELEASE_ID}, {"_id": 0, "id": 1}).sort("track_number", 1)
    ]
    if len(track_ids) < 2:
        pytest.skip("Fixture release must contain at least two tracks")

    data = {
        "db": db,
        "owner_token": _login(OWNER_EMAIL, OWNER_PASSWORD),
        "support_token": _login(SUPPORT_EMAIL, SUPPORT_PASSWORD),
        "finance_token": _login(FINANCE_EMAIL, FINANCE_PASSWORD),
        "label_id": label["id"],
        "release_id": FIXTURE_RELEASE_ID,
        "track_ids": track_ids,
        "created_asset_ids": set(),
        "created_ticket_ids": set(),
    }
    yield data

    ticket_ids = list(data["created_ticket_ids"])
    explicit_assets = set(data["created_asset_ids"])
    docs = list(db.contentid_declarations.find({"ticket_id": {"$in": ticket_ids}}, {"_id": 0})) if ticket_ids else []
    asset_ids_from_docs = {
        doc["signature_asset_id"]
        for doc in docs
    } | {
        doc["ktp_asset_id"]
        for doc in docs
    }
    all_asset_ids = list(explicit_assets | asset_ids_from_docs)

    for doc in docs:
        if doc.get("pdf_key"):
            try:
                asyncio.run(storage_service.delete_object(key=doc["pdf_key"]))
            except Exception:
                pass
    for asset in db.contentid_assets.find({"id": {"$in": all_asset_ids}}, {"_id": 0, "storage_key": 1}):
        if asset.get("storage_key"):
            try:
                asyncio.run(storage_service.delete_object(key=asset["storage_key"]))
            except Exception:
                pass

    if ticket_ids:
        db.ticket_comments.delete_many({"ticket_id": {"$in": ticket_ids}})
        db.support_tickets.delete_many({"id": {"$in": ticket_ids}})
        db.contentid_declarations.delete_many({"ticket_id": {"$in": ticket_ids}})
        db.contentid_requests.delete_many({"_id": {"$in": ticket_ids}})
        db.notifications.delete_many({"meta.ticket_id": {"$in": ticket_ids}})
        db.activity_logs.delete_many({"reference_id": {"$in": ticket_ids}})
    if all_asset_ids:
        db.contentid_assets.delete_many({"id": {"$in": all_asset_ids}})


def test_content_id_claim_requires_creator_payload(state):
    response = requests.post(
        f"{API}/tickets/label/create",
        headers=_headers(state["owner_token"]),
        json={
            "release_id": state["release_id"],
            "category": "content_id_claim",
            "subject": "ignored",
            "description": "",
            "originality_declared": True,
            "youtube_urls": ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
            "content_id_request_id": str(uuid.uuid4()),
            "content_id_consent": True,
        },
        timeout=60,
    )
    assert response.status_code == 400, response.text
    assert "Pilih lagu" in response.text


def test_non_claim_category_rejects_creator_payload(state):
    response = requests.post(
        f"{API}/tickets/label/create",
        headers=_headers(state["owner_token"]),
        json={
            "release_id": state["release_id"],
            "category": "content_id_release",
            "subject": "ignored",
            "description": "",
            "originality_declared": True,
            "youtube_urls": ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
            "content_id_track_ids": [state["track_ids"][0]],
        },
        timeout=60,
    )
    assert response.status_code == 400, response.text
    assert "Surat pencipta hanya untuk Pengajuan Content ID" in response.text


def test_asset_upload_validation_and_private_headers(state):
    blank = _upload_asset(state["owner_token"], state["release_id"], "signature", _image_bytes("signature", blank=True))
    assert blank.status_code == 400, blank.text

    invalid = requests.post(
        f"{API}/tickets/content-id/assets",
        headers=_headers(state["owner_token"]),
        data={"release_id": state["release_id"], "kind": "ktp", "signature_mode": "upload"},
        files={"file": ("invalid.png", b"this-is-not-a-real-png", "image/png")},
        timeout=60,
    )
    assert invalid.status_code == 400, invalid.text

    valid = _upload_asset(state["owner_token"], state["release_id"], "signature", _image_bytes("signature"))
    assert valid.status_code == 200, valid.text
    asset_id = valid.json()["id"]
    state["created_asset_ids"].add(asset_id)

    unauth = requests.get(f"{API}/tickets/content-id/assets/{asset_id}", timeout=40)
    assert unauth.status_code == 401

    fetched = requests.get(f"{API}/tickets/content-id/assets/{asset_id}", headers=_headers(state["owner_token"]), timeout=40)
    assert fetched.status_code == 200, fetched.text[:200]
    assert_no_storage(fetched)
    assert fetched.headers.get("x-content-type-options") == "nosniff"
    assert fetched.headers.get("content-type", "").startswith("image/png")

    key = state["db"].contentid_assets.find_one({"id": asset_id}, {"_id": 0, "storage_key": 1})["storage_key"]
    no_public = requests.get(f"{API}/files/{key}", timeout=40)
    assert no_public.status_code == 404
    no_alias = requests.get(f"{API}/files/./{key}", timeout=40)
    assert no_alias.status_code == 404

    deleted = requests.delete(f"{API}/tickets/content-id/assets/{asset_id}", headers=_headers(state["owner_token"]), timeout=40)
    assert deleted.status_code == 200, deleted.text


def test_asset_upload_rejects_oversize_and_gif_bytes(state):
    too_big_sig = _upload_asset(
        state["owner_token"],
        state["release_id"],
        "signature",
        b"\x89PNG\r\n\x1a\n" + (b"A" * (5 * 1024 * 1024 + 256)),
        filename="big-signature.png",
    )
    assert too_big_sig.status_code == 413, too_big_sig.text

    too_big_ktp = _upload_asset(
        state["owner_token"],
        state["release_id"],
        "ktp",
        b"\x89PNG\r\n\x1a\n" + (b"B" * (10 * 1024 * 1024 + 256)),
        filename="big-ktp.png",
    )
    assert too_big_ktp.status_code == 413, too_big_ktp.text

    gif_header = b"GIF89a" + (b"\x00" * 512)
    renamed_gif = requests.post(
        f"{API}/tickets/content-id/assets",
        headers=_headers(state["owner_token"]),
        data={"release_id": state["release_id"], "kind": "signature", "signature_mode": "upload"},
        files={"file": ("renamed.jpg", gif_header, "image/jpeg")},
        timeout=60,
    )
    assert renamed_gif.status_code == 400, renamed_gif.text


def test_content_id_ticket_idempotency_docs_and_visibility(state):
    sig = _upload_asset(state["owner_token"], state["release_id"], "signature", _image_bytes("signature"), signature_mode="drawn")
    ktp = _upload_asset(state["owner_token"], state["release_id"], "ktp", _image_bytes("ktp"))
    assert sig.status_code == 200, sig.text
    assert ktp.status_code == 200, ktp.text
    sig_id = sig.json()["id"]
    ktp_id = ktp.json()["id"]
    state["created_asset_ids"].update({sig_id, ktp_id})

    request_id = str(uuid.uuid4())
    payload = {
        "release_id": state["release_id"],
        "category": "content_id_claim",
        "subject": "ignored",
        "description": "",
        "originality_declared": True,
        "youtube_urls": ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
        "content_id_request_id": request_id,
        "content_id_track_ids": state["track_ids"][:2],
        "content_id_creators": [
            {
                "full_name": "QA Dummy Creator",
                "nik": "0000000000000123",
                "domicile": "Jakarta Selatan, Indonesia",
                "signing_city": "Jakarta",
                "authorship": "sole",
                "track_ids": state["track_ids"][:2],
                "signature_asset_id": sig_id,
                "ktp_asset_id": ktp_id,
            }
        ],
        "content_id_consent": True,
    }
    created = requests.post(f"{API}/tickets/label/create", headers=_headers(state["owner_token"]), json=payload, timeout=180)
    assert created.status_code == 200, created.text
    ticket = created.json()
    ticket_id = ticket["id"]
    state["created_ticket_ids"].add(ticket_id)
    assert ticket["category"] == "content_id_claim"
    assert len(ticket.get("content_id_documents") or []) == 1
    assert "nik" not in ticket["content_id_documents"][0]
    assert "signature_asset_id" not in ticket["content_id_documents"][0]
    assert "ktp_asset_id" not in ticket["content_id_documents"][0]

    listed = requests.get(f"{API}/tickets/label", headers=_headers(state["owner_token"]), timeout=60)
    assert listed.status_code == 200, listed.text
    listed_ticket = next(item for item in listed.json() if item["id"] == ticket_id)
    assert "nik" not in str(listed_ticket)
    assert "contentid-private" not in str(listed_ticket)

    docs_owner = requests.get(f"{API}/tickets/content-id/tickets/{ticket_id}", headers=_headers(state["owner_token"]), timeout=60)
    assert docs_owner.status_code == 200, docs_owner.text
    assert_no_storage(docs_owner)
    doc = docs_owner.json()[0]
    assert doc["nik"] == "0000000000000123"
    assert doc["creator_name"] == "QA Dummy Creator"
    assert len(doc["tracks"]) == 2

    docs_support = requests.get(f"{API}/tickets/content-id/tickets/{ticket_id}", headers=_headers(state["support_token"]), timeout=60)
    assert docs_support.status_code == 200, docs_support.text

    docs_finance = requests.get(f"{API}/tickets/content-id/tickets/{ticket_id}", headers=_headers(state["finance_token"]), timeout=60)
    assert docs_finance.status_code in (403, 404), docs_finance.text

    asset_blocked = requests.delete(f"{API}/tickets/content-id/assets/{sig_id}", headers=_headers(state["owner_token"]), timeout=40)
    assert asset_blocked.status_code == 404, asset_blocked.text

    pdf = requests.get(
        f"{API}/tickets/content-id/tickets/{ticket_id}/{doc['id']}/pdf",
        headers=_headers(state["owner_token"]),
        timeout=120,
    )
    assert pdf.status_code == 200, pdf.text[:200]
    assert pdf.headers.get("content-type", "").startswith("application/pdf")
    assert_no_storage(pdf)
    assert pdf.content.startswith(b"%PDF-")
    assert len(pdf.content) > 3000
    Path("/app/test_reports/iter68_contentid_sample.pdf").write_bytes(pdf.content)

    replay = requests.post(f"{API}/tickets/label/create", headers=_headers(state["owner_token"]), json=payload, timeout=180)
    assert replay.status_code == 200, replay.text
    replay_body = replay.json()
    assert replay_body["id"] == ticket_id
    assert replay_body.get("submission_replayed") is True


def test_duplicate_nik_rejected(state):
    sig1 = _upload_asset(state["owner_token"], state["release_id"], "signature", _image_bytes("signature"))
    ktp1 = _upload_asset(state["owner_token"], state["release_id"], "ktp", _image_bytes("ktp"))
    sig2 = _upload_asset(state["owner_token"], state["release_id"], "signature", _image_bytes("signature"))
    ktp2 = _upload_asset(state["owner_token"], state["release_id"], "ktp", _image_bytes("ktp"))
    for response in (sig1, ktp1, sig2, ktp2):
        assert response.status_code == 200, response.text
    ids = [sig1.json()["id"], ktp1.json()["id"], sig2.json()["id"], ktp2.json()["id"]]
    state["created_asset_ids"].update(ids)

    response = requests.post(
        f"{API}/tickets/label/create",
        headers=_headers(state["owner_token"]),
        json={
            "release_id": state["release_id"],
            "category": "content_id_claim",
            "subject": "ignored",
            "description": "",
            "originality_declared": True,
            "youtube_urls": ["https://www.youtube.com/watch?v=jfKfPfyJRdk"],
            "content_id_request_id": str(uuid.uuid4()),
            "content_id_track_ids": state["track_ids"][:2],
            "content_id_creators": [
                {
                    "full_name": "Creator A",
                    "nik": "0000000000000456",
                    "domicile": "Bandung",
                    "signing_city": "Bandung",
                    "authorship": "sole",
                    "track_ids": [state["track_ids"][0]],
                    "signature_asset_id": ids[0],
                    "ktp_asset_id": ids[1],
                },
                {
                    "full_name": "Creator B",
                    "nik": "0000000000000456",
                    "domicile": "Bandung",
                    "signing_city": "Bandung",
                    "authorship": "sole",
                    "track_ids": [state["track_ids"][1]],
                    "signature_asset_id": ids[2],
                    "ktp_asset_id": ids[3],
                },
            ],
            "content_id_consent": True,
        },
        timeout=120,
    )
    assert response.status_code == 400, response.text
    assert "NIK" in response.text


def test_swapped_signature_and_ktp_asset_ids_rejected(state):
    sig = _upload_asset(state["owner_token"], state["release_id"], "signature", _image_bytes("signature"))
    ktp = _upload_asset(state["owner_token"], state["release_id"], "ktp", _image_bytes("ktp"))
    assert sig.status_code == 200, sig.text
    assert ktp.status_code == 200, ktp.text
    sig_id = sig.json()["id"]
    ktp_id = ktp.json()["id"]
    state["created_asset_ids"].update({sig_id, ktp_id})

    response = requests.post(
        f"{API}/tickets/label/create",
        headers=_headers(state["owner_token"]),
        json={
            "release_id": state["release_id"],
            "category": "content_id_claim",
            "subject": "ignored",
            "description": "",
            "originality_declared": True,
            "youtube_urls": ["https://www.youtube.com/watch?v=5qap5aO4i9A"],
            "content_id_request_id": str(uuid.uuid4()),
            "content_id_track_ids": [state["track_ids"][0]],
            "content_id_creators": [
                {
                    "full_name": "Creator Swap",
                    "nik": "0000000000000789",
                    "domicile": "Surabaya",
                    "signing_city": "Surabaya",
                    "authorship": "sole",
                    "track_ids": [state["track_ids"][0]],
                    "signature_asset_id": ktp_id,
                    "ktp_asset_id": sig_id,
                }
            ],
            "content_id_consent": True,
        },
        timeout=120,
    )
    assert response.status_code == 400, response.text
    assert "KTP atau tanda tangan tidak valid" in response.text


def test_content_id_request_in_progress_returns_409(state):
    request_id = str(uuid.uuid4())
    ticket_id = str(uuid5(NAMESPACE_URL, f"rilis-contentid:{state['label_id']}:{request_id}"))
    state["db"].contentid_requests.insert_one(
        {
            "_id": ticket_id,
            "label_id": state["label_id"],
            "created_at": "2026-02-01T00:00:00+00:00",
            "updated_at": "3026-02-01T00:00:00+00:00",
        }
    )
    response = requests.post(
        f"{API}/tickets/label/create",
        headers=_headers(state["owner_token"]),
        json={
            "release_id": state["release_id"],
            "category": "content_id_claim",
            "content_id_request_id": request_id,
        },
        timeout=60,
    )
    assert response.status_code == 409, response.text
    assert "sedang diproses" in response.text
    state["db"].contentid_requests.delete_one({"_id": ticket_id})