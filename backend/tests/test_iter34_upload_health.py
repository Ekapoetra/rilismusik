"""Iteration 34 — royalty upload health checks (multipart + direct R2)."""
import os
import time
import uuid

import pymongo
import requests
from dotenv import dotenv_values, load_dotenv

from tests.support_config import SUPERADMIN


load_dotenv("/app/backend/.env", override=True)
FRONTEND_ENV = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or FRONTEND_ENV["REACT_APP_BACKEND_URL"]).rstrip("/")
API = f"{BASE_URL}/api"


def _db():
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


def _login_superadmin_token():
    response = requests.post(
        f"{API}/auth/login",
        json={"email": SUPERADMIN["email"], "password": SUPERADMIN["password"]},
        timeout=30,
    )
    assert response.status_code == 200, response.text
    token = response.json().get("access_token")
    assert token
    return token


def _headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def _cleanup_import(import_id: str):
    database = _db()
    database.royalty_lines.delete_many({"import_id": import_id})
    database.royalty_imports.delete_one({"id": import_id})
    database.labels.delete_many({"auto_created_from": import_id})
    database.releases.delete_many({"auto_created_from": import_id})
    database.tracks.delete_many({"auto_created_from": import_id})
    database.artists.delete_many({"auto_created_from": import_id})


def _csv_payload(tag: str) -> str:
    return (
        "ISRC,UPC,Judul Track,Nama Artis,Nama Label,Platform,Negara,Kuantitas,Pendapatan Bersih,Bulan Laporan\n"
        f"USITER3400{tag[:4]},1234567890123,ITER34 Track {tag},ITER34 Artist {tag},ITER34 Label {tag},Spotify,ID,123,1.11,2026-06\n"
    )


def test_legacy_multipart_upload_persists_to_r2_and_enforces_10mb_cap():
    # Royalty multipart endpoint: small upload persists source to R2, >10MB is rejected.
    token = _login_superadmin_token()
    created_import_id = None
    tag = uuid.uuid4().hex[:8]

    try:
        small_csv = _csv_payload(tag)
        response = requests.post(
            f"{API}/royalty/admin/imports",
            headers=_headers(token),
            data={"period": "2026-06", "rate_eur_idr": "17500", "note": f"ITER34 multipart {tag}"},
            files={"file": (f"iter34_multipart_{tag}.csv", small_csv, "text/csv")},
            timeout=60,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        created_import_id = body["id"]
        assert body["status"] in ("pending_review", "processing")
        assert body.get("file_url", "").startswith("r2://")
        assert body.get("r2_key", "").startswith("csv/")
        assert body.get("total_lines", 0) >= 1

        oversized = b"a" * (10 * 1024 * 1024 + 1)
        too_big = requests.post(
            f"{API}/royalty/admin/imports",
            headers=_headers(token),
            data={"period": "2026-06", "rate_eur_idr": "17500"},
            files={"file": (f"iter34_oversized_{tag}.csv", oversized, "text/csv")},
            timeout=90,
        )
        assert too_big.status_code == 413, too_big.text
        detail = (too_big.json().get("detail") or "").lower()
        assert "10 mb" in detail or "10mb" in detail
    finally:
        if created_import_id:
            _cleanup_import(created_import_id)


def test_direct_r2_initiate_put_finalize_flow_healthy():
    # Royalty direct-R2 upload: initiate + PUT + finalize reaches pending_review.
    token = _login_superadmin_token()
    tag = uuid.uuid4().hex[:8]
    import_id = None

    try:
        initiate = requests.post(
            f"{API}/royalty/admin/imports/initiate",
            headers=_headers(token),
            json={
                "filename": f"iter34_direct_{tag}.csv",
                "rate_eur_idr": 17500,
                "period": "2026-06",
                "note": f"ITER34 direct {tag}",
                "file_size_bytes": len(_csv_payload(tag).encode("utf-8")),
            },
            timeout=30,
        )
        assert initiate.status_code == 200, initiate.text
        init_body = initiate.json()
        import_id = init_body["import_id"]
        assert init_body.get("presigned_put_url")
        assert init_body.get("r2_key", "").startswith("csv/")

        put_result = requests.put(
            init_body["presigned_put_url"],
            data=_csv_payload(tag).encode("utf-8"),
            headers={"Content-Type": init_body.get("content_type", "text/csv")},
            timeout=60,
        )
        assert put_result.status_code in (200, 201), f"PUT failed: {put_result.status_code} {put_result.text[:200]}"

        finalize = requests.post(
            f"{API}/royalty/admin/imports/{import_id}/finalize",
            headers=_headers(token),
            timeout=60,
        )
        assert finalize.status_code == 200, finalize.text
        assert finalize.json().get("status") in ("processing", "pending_review")

        final_doc = None
        deadline = time.time() + 30
        while time.time() < deadline:
            probe = requests.get(
                f"{API}/royalty/admin/imports/{import_id}",
                headers=_headers(token),
                timeout=30,
            )
            assert probe.status_code == 200, probe.text
            final_doc = probe.json()["import"]
            if final_doc.get("status") in ("pending_review", "error"):
                break
            time.sleep(2)
        assert final_doc is not None
        assert final_doc.get("status") == "pending_review", final_doc.get("error_message")
        assert final_doc.get("total_lines", 0) >= 1
        assert final_doc.get("matched_lines", 0) >= 0
    finally:
        if import_id:
            _cleanup_import(import_id)
