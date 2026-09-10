"""Iter69 follow-up: Content ID signature visual, multi-creator, privacy, and rollback checks."""

import asyncio
import json
import os
import sys
import uuid
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pypdfium2 as pdfium
import pytest
import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw
from pypdf import PdfReader

from tests.support_config import DEMO_PPR, FINANCE, SUPPORT


sys.path.insert(0, "/app/backend")
from routes.contentid_pdf import generate_contentid_pdf  # noqa: E402
from routes import contentid_service  # noqa: E402


load_dotenv("/app/backend/.env", override=True)
load_dotenv("/app/backend/.env.test", override=True)
load_dotenv("/app/frontend/.env", override=True)

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
if not Path("/app/tests/iter66_ui_fixture_state.json").exists():
    pytest.skip("Seed isolated fixture with /app/tests/iter66_ui_fixture.py seed before running.", allow_module_level=True)
FIXTURE = json.loads(Path("/app/tests/iter66_ui_fixture_state.json").read_text())
OWNER_EMAIL = FIXTURE["seeded"]["email"]
OWNER_PASSWORD = FIXTURE["seeded"]["password"]
RELEASE_ID = FIXTURE["release_id"]


def _login(email: str, password: str) -> str:
    response = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=40)
    assert response.status_code == 200, response.text
    token = response.json().get("access_token")
    assert token, "Login succeeded without access_token"
    return token


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _signature_png(strokes: int = 3) -> bytes:
    image = Image.new("RGB", (760, 320), "white")
    draw = ImageDraw.Draw(image)
    for i in range(strokes):
        x = 40 + i * 40
        draw.line((x, 220, x + 140, 90, x + 280, 230, x + 420, 110), fill="black", width=8)
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def _ktp_png(nik: str) -> bytes:
    image = Image.new("RGB", (1280, 760), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((26, 26, 1252, 734), outline="black", width=6)
    draw.text((70, 90), "KTP QA WATERMARK - SYNTHETIC ONLY", fill="black")
    draw.text((70, 160), f"NIK: {nik}", fill="black")
    draw.text((70, 230), "NAMA: QA CREATOR", fill="black")
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def _ink_bbox_area(png_bytes: bytes) -> int:
    image = Image.open(BytesIO(png_bytes)).convert("L")
    mask = image.point(lambda v: 255 if v < 235 else 0)
    box = mask.getbbox()
    if not box:
        return 0
    return (box[2] - box[0]) * (box[3] - box[1])


def _upload_asset(token: str, kind: str, content: bytes, signature_mode: str = "upload") -> requests.Response:
    return requests.post(
        f"{API}/tickets/content-id/assets",
        headers=_headers(token),
        data={"release_id": RELEASE_ID, "kind": kind, "signature_mode": signature_mode},
        files={"file": (f"{kind}.png", content, "image/png")},
        timeout=90,
    )


@pytest.fixture(scope="module")
def state():
    import pymongo
    import storage_service

    db = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    owner = db.users.find_one({"email": OWNER_EMAIL}, {"_id": 0, "id": 1})
    if not owner:
        pytest.skip("Iter66 owner fixture account missing")
    label = db.labels.find_one({"user_id": owner["id"]}, {"_id": 0, "id": 1})
    if not label:
        pytest.skip("Iter66 label missing")
    release = db.releases.find_one({"id": RELEASE_ID, "label_id": label["id"]}, {"_id": 0, "id": 1})
    if not release:
        pytest.skip("Iter66 release missing or not owned")
    track_ids = [
        row["id"]
        for row in db.tracks.find({"release_id": RELEASE_ID}, {"_id": 0, "id": 1}).sort("track_number", 1)
    ]
    if len(track_ids) < 2:
        pytest.skip("Need at least two tracks")

    data = {
        "db": db,
        "owner_token": _login(OWNER_EMAIL, OWNER_PASSWORD),
        "support_token": _login(SUPPORT["email"], SUPPORT["password"]),
        "finance_token": _login(FINANCE["email"], FINANCE["password"]),
        "other_label_token": _login(DEMO_PPR["email"], DEMO_PPR["password"]),
        "label_id": label["id"],
        "foreign_release_id": (db.releases.find_one({"label_id": {"$ne": label["id"]}}, {"_id": 0, "id": 1}) or {}).get("id"),
        "track_ids": track_ids,
        "created_asset_ids": set(),
        "created_ticket_ids": set(),
    }
    yield data

    ticket_ids = list(data["created_ticket_ids"])
    docs = list(db.contentid_declarations.find({"ticket_id": {"$in": ticket_ids}}, {"_id": 0})) if ticket_ids else []
    all_assets = set(data["created_asset_ids"]) | {doc["signature_asset_id"] for doc in docs} | {doc["ktp_asset_id"] for doc in docs}

    for doc in docs:
        key = doc.get("pdf_key")
        if key:
            try:
                asyncio.run(storage_service.delete_object(key=key))
            except Exception:
                pass
    for asset in db.contentid_assets.find({"id": {"$in": list(all_assets)}}, {"_id": 0, "storage_key": 1}):
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
    if all_assets:
        db.contentid_assets.delete_many({"id": {"$in": list(all_assets)}})


# Integration: multi-creator, per-track scope, privacy authz, and post-download access behavior.
def test_multi_creator_submission_and_privacy(state):
    sig_a = _upload_asset(state["owner_token"], "signature", _signature_png(strokes=4), signature_mode="drawn")
    ktp_a = _upload_asset(state["owner_token"], "ktp", _ktp_png("1111222233334444"))
    sig_b = _upload_asset(state["owner_token"], "signature", _signature_png(strokes=5), signature_mode="upload")
    ktp_b = _upload_asset(state["owner_token"], "ktp", _ktp_png("5555666677778888"))
    for resp in (sig_a, ktp_a, sig_b, ktp_b):
        assert resp.status_code == 200, resp.text
    ids = [sig_a.json()["id"], ktp_a.json()["id"], sig_b.json()["id"], ktp_b.json()["id"]]
    state["created_asset_ids"].update(ids)

    selected = state["track_ids"][:2]
    payload = {
        "release_id": RELEASE_ID,
        "category": "content_id_claim",
        "subject": "ignored",
        "description": "",
        "originality_declared": True,
        "youtube_urls": ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
        "content_id_request_id": str(uuid.uuid4()),
        "content_id_track_ids": selected,
        "content_id_creators": [
            {
                "full_name": "QA CREATOR SATU",
                "nik": "1111222233334444",
                "domicile": "Bandung QA Address Panjang",
                "signing_city": "Bandung",
                "authorship": "sole",
                "track_ids": [selected[0]],
                "signature_asset_id": ids[0],
                "ktp_asset_id": ids[1],
            },
            {
                "full_name": "QA CREATOR DUA",
                "nik": "5555666677778888",
                "domicile": "Jakarta QA Address Panjang",
                "signing_city": "Jakarta",
                "authorship": "sole",
                "track_ids": [selected[1]],
                "signature_asset_id": ids[2],
                "ktp_asset_id": ids[3],
            },
        ],
        "content_id_consent": True,
    }
    created = requests.post(f"{API}/tickets/label/create", headers=_headers(state["owner_token"]), json=payload, timeout=180)
    assert created.status_code == 200, created.text
    ticket = created.json()
    ticket_id = ticket["id"]
    state["created_ticket_ids"].add(ticket_id)
    assert len(ticket.get("content_id_documents") or []) == 2

    owner_docs = requests.get(f"{API}/tickets/content-id/tickets/{ticket_id}", headers=_headers(state["owner_token"]), timeout=80)
    assert owner_docs.status_code == 200, owner_docs.text
    docs = owner_docs.json()
    assert len(docs) == 2
    by_name = {doc["creator_name"]: doc for doc in docs}
    assert by_name["QA CREATOR SATU"]["nik"] == "1111222233334444"
    assert by_name["QA CREATOR DUA"]["nik"] == "5555666677778888"
    assert [t["id"] for t in by_name["QA CREATOR SATU"]["tracks"]] == [selected[0]]
    assert [t["id"] for t in by_name["QA CREATOR DUA"]["tracks"]] == [selected[1]]

    support_docs = requests.get(f"{API}/tickets/content-id/tickets/{ticket_id}", headers=_headers(state["support_token"]), timeout=80)
    assert support_docs.status_code == 200, support_docs.text
    finance_docs = requests.get(f"{API}/tickets/content-id/tickets/{ticket_id}", headers=_headers(state["finance_token"]), timeout=80)
    assert finance_docs.status_code in (403, 404), finance_docs.text
    other_label_docs = requests.get(
        f"{API}/tickets/content-id/tickets/{ticket_id}", headers=_headers(state["other_label_token"]), timeout=80
    )
    assert other_label_docs.status_code == 404, other_label_docs.text
    unauth_docs = requests.get(f"{API}/tickets/content-id/tickets/{ticket_id}", timeout=80)
    assert unauth_docs.status_code == 401, unauth_docs.text

    for doc in docs:
        pdf = requests.get(
            f"{API}/tickets/content-id/tickets/{ticket_id}/{doc['id']}/pdf",
            headers=_headers(state["owner_token"]),
            timeout=120,
        )
        assert pdf.status_code == 200, pdf.text[:200]
        assert pdf.content.startswith(b"%PDF-")
        text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf.content)).pages)
        assert doc["creator_name"] in text
        assert doc["nik"] in text
        for assigned in doc["tracks"]:
            assert assigned["track_title"] in text

        support_pdf = requests.get(
            f"{API}/tickets/content-id/tickets/{ticket_id}/{doc['id']}/pdf",
            headers=_headers(state["support_token"]),
            timeout=120,
        )
        assert support_pdf.status_code == 200, support_pdf.text[:200]

        support_sig = requests.get(
            f"{API}/tickets/content-id/assets/{doc['signature_asset_id']}",
            headers=_headers(state["support_token"]),
            timeout=80,
        )
        assert support_sig.status_code == 200, support_sig.text[:200]

    # Owner has read docs/PDF; verify direct private prefix still blocked publicly.
    sample_asset_key = state["db"].contentid_assets.find_one({"id": ids[0]}, {"_id": 0, "storage_key": 1})["storage_key"]
    blocked = requests.get(f"{API}/files/{sample_asset_key}", timeout=40)
    assert blocked.status_code == 404
    other_label_after_owner_download = requests.get(
        f"{API}/tickets/content-id/tickets/{ticket_id}", headers=_headers(state["other_label_token"]), timeout=60
    )
    assert other_label_after_owner_download.status_code == 404


# Integration: signature ink should remain non-trivial after server crop; missing creator track coverage must fail.
def test_signature_ink_visibility_and_track_coverage_validation(state):
    sig = _upload_asset(state["owner_token"], "signature", _signature_png(strokes=6), signature_mode="drawn")
    ktp = _upload_asset(state["owner_token"], "ktp", _ktp_png("9999000011112222"))
    assert sig.status_code == 200, sig.text
    assert ktp.status_code == 200, ktp.text
    sig_id = sig.json()["id"]
    ktp_id = ktp.json()["id"]
    state["created_asset_ids"].update({sig_id, ktp_id})

    fetched = requests.get(f"{API}/tickets/content-id/assets/{sig_id}", headers=_headers(state["owner_token"]), timeout=60)
    assert fetched.status_code == 200, fetched.text[:200]
    area = _ink_bbox_area(fetched.content)
    assert area >= 1200, f"Expected substantial signature area, got {area}"

    selected = state["track_ids"][:2]
    response = requests.post(
        f"{API}/tickets/label/create",
        headers=_headers(state["owner_token"]),
        json={
            "release_id": RELEASE_ID,
            "category": "content_id_claim",
            "subject": "ignored",
            "description": "",
            "originality_declared": True,
            "youtube_urls": ["https://www.youtube.com/watch?v=5qap5aO4i9A"],
            "content_id_request_id": str(uuid.uuid4()),
            "content_id_track_ids": selected,
            "content_id_creators": [
                {
                    "full_name": "COVERAGE QA",
                    "nik": "9999000011112222",
                    "domicile": "Yogyakarta",
                    "signing_city": "Yogyakarta",
                    "authorship": "sole",
                    "track_ids": [selected[0]],
                    "signature_asset_id": sig_id,
                    "ktp_asset_id": ktp_id,
                }
            ],
            "content_id_consent": True,
        },
        timeout=120,
    )
    assert response.status_code == 400, response.text
    assert "Setiap lagu wajib" in response.text


# Integration: foreign release must be denied; default single creator may own all selected tracks.
def test_foreign_release_denied_and_single_creator_all_tracks(state):
    if state.get("foreign_release_id"):
        foreign_attempt = requests.post(
            f"{API}/tickets/label/create",
            headers=_headers(state["owner_token"]),
            json={
                "release_id": state["foreign_release_id"],
                "category": "content_id_claim",
                "subject": "ignored",
                "description": "",
                "originality_declared": True,
                "youtube_urls": ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
                "content_id_request_id": str(uuid.uuid4()),
                "content_id_track_ids": state["track_ids"][:2],
                "content_id_creators": [],
                "content_id_consent": True,
            },
            timeout=120,
        )
        assert foreign_attempt.status_code == 403, foreign_attempt.text

    sig = _upload_asset(state["owner_token"], "signature", _signature_png(strokes=5), signature_mode="drawn")
    ktp = _upload_asset(state["owner_token"], "ktp", _ktp_png("3333444455556666"))
    assert sig.status_code == 200, sig.text
    assert ktp.status_code == 200, ktp.text
    sig_id = sig.json()["id"]
    ktp_id = ktp.json()["id"]
    state["created_asset_ids"].update({sig_id, ktp_id})

    selected = state["track_ids"][:2]
    single = requests.post(
        f"{API}/tickets/label/create",
        headers=_headers(state["owner_token"]),
        json={
            "release_id": RELEASE_ID,
            "category": "content_id_claim",
            "subject": "ignored",
            "description": "",
            "originality_declared": True,
            "youtube_urls": ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
            "content_id_request_id": str(uuid.uuid4()),
            "content_id_track_ids": selected,
            "content_id_creators": [
                {
                    "full_name": "SINGLE QA CREATOR",
                    "nik": "3333444455556666",
                    "domicile": "Depok",
                    "signing_city": "Depok",
                    "authorship": "sole",
                    "track_ids": selected,
                    "signature_asset_id": sig_id,
                    "ktp_asset_id": ktp_id,
                }
            ],
            "content_id_consent": True,
        },
        timeout=180,
    )
    assert single.status_code == 200, single.text
    ticket_id = single.json()["id"]
    state["created_ticket_ids"].add(ticket_id)
    docs = requests.get(f"{API}/tickets/content-id/tickets/{ticket_id}", headers=_headers(state["owner_token"]), timeout=80)
    assert docs.status_code == 200, docs.text
    rows = docs.json()
    assert len(rows) == 1
    assert len(rows[0]["tracks"]) == 2


# Integration: shared tracks across creators should trigger joint authorship wording in PDF.
def test_shared_track_joint_authorship_wording(state):
    sig_1 = _upload_asset(state["owner_token"], "signature", _signature_png(strokes=4), signature_mode="drawn")
    ktp_1 = _upload_asset(state["owner_token"], "ktp", _ktp_png("7777888899990001"))
    sig_2 = _upload_asset(state["owner_token"], "signature", _signature_png(strokes=4), signature_mode="drawn")
    ktp_2 = _upload_asset(state["owner_token"], "ktp", _ktp_png("7777888899990002"))
    for response in (sig_1, ktp_1, sig_2, ktp_2):
        assert response.status_code == 200, response.text
    ids = [sig_1.json()["id"], ktp_1.json()["id"], sig_2.json()["id"], ktp_2.json()["id"]]
    state["created_asset_ids"].update(ids)

    selected = state["track_ids"][:2]
    shared = requests.post(
        f"{API}/tickets/label/create",
        headers=_headers(state["owner_token"]),
        json={
            "release_id": RELEASE_ID,
            "category": "content_id_claim",
            "subject": "ignored",
            "description": "",
            "originality_declared": True,
            "youtube_urls": ["https://www.youtube.com/watch?v=jfKfPfyJRdk"],
            "content_id_request_id": str(uuid.uuid4()),
            "content_id_track_ids": selected,
            "content_id_creators": [
                {
                    "full_name": "JOINT CREATOR 1",
                    "nik": "7777888899990001",
                    "domicile": "Semarang",
                    "signing_city": "Semarang",
                    "authorship": "sole",
                    "track_ids": [selected[0]],
                    "signature_asset_id": ids[0],
                    "ktp_asset_id": ids[1],
                },
                {
                    "full_name": "JOINT CREATOR 2",
                    "nik": "7777888899990002",
                    "domicile": "Semarang",
                    "signing_city": "Semarang",
                    "authorship": "sole",
                    "track_ids": [selected[0], selected[1]],
                    "signature_asset_id": ids[2],
                    "ktp_asset_id": ids[3],
                },
            ],
            "content_id_consent": True,
        },
        timeout=180,
    )
    assert shared.status_code == 200, shared.text
    ticket_id = shared.json()["id"]
    state["created_ticket_ids"].add(ticket_id)

    docs = requests.get(f"{API}/tickets/content-id/tickets/{ticket_id}", headers=_headers(state["owner_token"]), timeout=80)
    assert docs.status_code == 200, docs.text
    for doc in docs.json():
        pdf = requests.get(
            f"{API}/tickets/content-id/tickets/{ticket_id}/{doc['id']}/pdf",
            headers=_headers(state["owner_token"]),
            timeout=120,
        )
        assert pdf.status_code == 200, pdf.text[:160]
        text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf.content)).pages)
        assert "ciptaan saya bersama pencipta lain" in text


# Unit: PDF pagination/layout for long escaped fields + 30+ tracks; emit final artifact files.
def test_pdf_long_content_pagination_and_render_artifacts():
    tracks = [
        {
            "id": f"t-{i}",
            "track_title": f"LAGU QA {i:02d} <xml> & panjang sekali " + ("A" * 80),
            "isrc": f"IDQA{i:010d}"[:12],
        }
        for i in range(1, 36)
    ]
    document = {
        "creator_name": "QA CREATOR NAMA SANGAT PANJANG <script>alert(1)</script>",
        "nik": "1234567890123456",
        "domicile": "Alamat sangat panjang " + ("Jl. Mawar " * 40),
        "signing_city": "Jakarta",
        "issued_at": "2026-02-10T10:20:00+00:00",
        "release_title": "RILIS QA PANJANG " + ("R" * 120),
        "upc": "899001122334",
        "tracks": tracks,
        "authorship": "joint",
    }
    pdf_bytes = generate_contentid_pdf(document, _signature_png(strokes=6), _ktp_png("1234567890123456"))
    assert pdf_bytes.startswith(b"%PDF-")

    pdf_path = Path("/app/test_reports/iter68_final_sample.pdf")
    render_dir = Path("/app/test_reports/iter68_final_rendered")
    render_dir.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(pdf_bytes)

    reader = PdfReader(BytesIO(pdf_bytes))
    assert len(reader.pages) >= 3
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "QA CREATOR NAMA SANGAT PANJANG" in text

    pdf_doc = pdfium.PdfDocument(pdf_bytes)
    for index in range(min(4, len(pdf_doc))):
        pil = pdf_doc[index].render(scale=2.0).to_pil()
        pil.save(render_dir / f"page_{index + 1}.png")
        gray = pil.convert("L")
        lo, hi = gray.getextrema()
        assert hi - lo > 20


@dataclass
class _FakeCreator:
    full_name: str
    nik: str
    domicile: str
    signing_city: str
    authorship: str
    track_ids: list
    signature_asset_id: str
    ktp_asset_id: str


class _AsyncList:
    def __init__(self, rows):
        self.rows = rows

    def sort(self, *_args, **_kwargs):
        return self

    async def to_list(self, _limit):
        return list(self.rows)

    def __aiter__(self):
        self._iter = iter(self.rows)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class _FakeResult:
    def __init__(self, modified_count=1):
        self.modified_count = modified_count


class _FakeDB:
    def __init__(self):
        self.assets = {
            "sig-1": {"id": "sig-1", "kind": "signature", "status": "staged", "storage_key": "sig-1", "ticket_id": None},
            "ktp-1": {"id": "ktp-1", "kind": "ktp", "status": "staged", "storage_key": "ktp-1", "ticket_id": None},
        }
        self.requests = {}
        self.declarations = []
        self.tracks = SimpleNamespace(find=lambda *_args, **_kwargs: _AsyncList([{"id": "t1", "track_number": 1, "track_title": "Track 1", "isrc": "IDQA00000001"}]))
        self.contentid_assets = self
        self.contentid_requests = self
        self.contentid_declarations = self

    def find(self, query, *_args, **_kwargs):
        if "status" in query and "id" in query:
            rows = []
            for aid in query["id"]["$in"]:
                row = self.assets.get(aid)
                if row and row["status"] == "staged":
                    rows.append(row.copy())
            return _AsyncList(rows)
        return _AsyncList([])

    async def insert_one(self, doc):
        self.requests[doc["_id"]] = doc

    async def update_one(self, query, update):
        aid = query.get("id")
        if aid and self.assets.get(aid, {}).get("status") == "staged":
            self.assets[aid]["status"] = update["$set"]["status"]
            self.assets[aid]["ticket_id"] = update["$set"]["ticket_id"]
            return _FakeResult(1)
        if "_id" in query:
            return _FakeResult(1)
        return _FakeResult(0)

    async def update_many(self, query, update):
        for aid, row in self.assets.items():
            if row.get("ticket_id") == query.get("ticket_id") and row.get("status") in query["status"]["$in"]:
                self.assets[aid]["status"] = update["$set"]["status"]
                self.assets[aid]["ticket_id"] = update["$set"]["ticket_id"]
        return _FakeResult(1)

    async def delete_one(self, query):
        self.requests.pop(query["_id"], None)

    async def insert_many(self, docs):
        self.declarations.extend(docs)

    async def delete_many(self, *_args, **_kwargs):
        self.declarations = []


# Unit: on PDF upload failure, rollback must release reserved assets and avoid declaration persistence.
def test_unit_pdf_upload_failure_rolls_back(monkeypatch):
    fake_db = _FakeDB()

    async def fake_download_bytes(key):
        if key.startswith("sig"):
            return _signature_png(strokes=4)
        return _ktp_png("1000000000000001")

    async def fake_upload_bytes(**_kwargs):
        raise RuntimeError("forced-upload-fail")

    async def fake_delete_object(**_kwargs):
        return None

    monkeypatch.setattr(contentid_service, "db", fake_db)
    monkeypatch.setattr(contentid_service.storage_service, "download_bytes", fake_download_bytes)
    monkeypatch.setattr(contentid_service.storage_service, "upload_bytes", fake_upload_bytes)
    monkeypatch.setattr(contentid_service.storage_service, "delete_object", fake_delete_object)

    body = SimpleNamespace(
        content_id_creators=[
            _FakeCreator(
                full_name="Rollback QA",
                nik="1000000000000001",
                domicile="Bandung",
                signing_city="Bandung",
                authorship="sole",
                track_ids=["t1"],
                signature_asset_id="sig-1",
                ktp_asset_id="ktp-1",
            )
        ],
        content_id_track_ids=["t1"],
        content_id_consent=True,
    )
    release = {"id": "rel-1", "release_title": "Rel", "upc": "123"}
    label = {"id": "lbl-1"}
    user = {"id": "usr-1"}

    with pytest.raises(Exception) as exc:
        asyncio.run(contentid_service.build_contentid_documents(body, release, label, "ticket-1", user))
    assert "Surat pernyataan gagal dibuat" in str(exc.value)
    assert fake_db.assets["sig-1"]["status"] == "staged"
    assert fake_db.assets["sig-1"]["ticket_id"] is None
    assert fake_db.assets["ktp-1"]["status"] == "staged"
    assert fake_db.declarations == []
    assert "ticket-1" not in fake_db.requests