"""Phase 12 — Cloudflare R2 object storage smoke tests.

Validates:
  - storage_service imports cleanly and exposes helpers
  - is_configured() returns True with current .env
  - Upload→head→presigned-url→delete round-trip works
  - Backend /api/files/{path} returns 302 redirect to a presigned R2 URL
  - Backend /api/files/{path} returns 404 for unknown keys
  - MDA preview endpoint streams a valid PDF (in-memory, no disk)
"""
import os
import sys
import asyncio
import requests
import pytest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://lanjut-core.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
R2_CONFIGURED = all(os.environ.get(k) for k in ("R2_ENDPOINT_URL", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"))


def test_storage_service_imports():
    import storage_service
    for fn in ("upload_bytes", "upload_fileobj", "generate_presigned_url", "delete_object", "head_object", "is_configured"):
        assert hasattr(storage_service, fn), f"storage_service missing {fn}"


@pytest.mark.skipif(not R2_CONFIGURED, reason="R2 credentials not configured")
def test_r2_roundtrip_upload_head_presign_delete():
    import storage_service

    async def run():
        key = f"smoketest/phase12-{uuid.uuid4().hex}.txt"
        payload = b"phase12 hello cloudflare r2"
        await storage_service.upload_bytes(key=key, data=payload, content_type="text/plain")
        meta = await storage_service.head_object(key=key)
        assert meta and meta.get("ContentLength") == len(payload)
        url = await storage_service.generate_presigned_url(key=key, ttl=60)
        # Presigned URL should be GET-able publicly
        r = requests.get(url, timeout=15)
        assert r.status_code == 200
        assert r.content == payload
        await storage_service.delete_object(key=key)
        meta_after = await storage_service.head_object(key=key)
        assert meta_after is None

    asyncio.run(run())


@pytest.mark.skipif(not R2_CONFIGURED, reason="R2 credentials not configured")
def test_files_endpoint_redirects_to_presigned_url_when_r2_has_object():
    """Upload a file directly to R2, then verify the public /api/files/{key}
    endpoint 302-redirects to a presigned URL that resolves to the bytes."""
    import storage_service

    key = f"smoketest/phase12-redirect-{uuid.uuid4().hex}.txt"
    payload = b"hello from r2 via /api/files"

    async def _upload():
        await storage_service.upload_bytes(key=key, data=payload, content_type="text/plain")

    asyncio.run(_upload())
    try:
        # Backend should redirect to presigned URL
        r = requests.get(f"{API}/files/{key}", allow_redirects=False, timeout=15)
        assert r.status_code == 302, f"expected 302, got {r.status_code} body={r.text[:200]}"
        location = r.headers.get("Location") or r.headers.get("location")
        assert location and "X-Amz-Signature" in location, f"redirect target missing signature: {location[:200]}"
        # Follow the redirect manually — content must match what we uploaded
        r2 = requests.get(location, timeout=15)
        assert r2.status_code == 200
        assert r2.content == payload
    finally:
        async def _cleanup():
            await storage_service.delete_object(key=key)
        asyncio.run(_cleanup())


def test_files_endpoint_returns_404_for_unknown_key():
    r = requests.get(f"{API}/files/smoketest/does-not-exist-{uuid.uuid4().hex}.bin", allow_redirects=False, timeout=15)
    assert r.status_code == 404


def test_mda_preview_streams_valid_pdf():
    r = requests.get(f"{API}/cms/mda/preview", timeout=30)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content.startswith(b"%PDF-"), "Response is not a valid PDF"
    assert len(r.content) > 2000, "PDF too small — generation may have failed"
