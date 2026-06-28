"""Cloudflare R2 object storage service for RILIS MUSIK.

R2 is S3-compatible — we use the standard AWS boto3 SDK pointed at the R2
endpoint. Per Cloudflare docs:
  • region_name MUST be 'auto'
  • signature_version='s3v4'

All file uploads (release covers, audio masters, contracts, ticket
attachments, withdraw proofs, landing images) live in a single bucket and are
namespaced by a top-level prefix (e.g. 'covers/', 'audio/', 'contracts/').

Files are PRIVATE by default. Frontend never gets a direct R2 URL — it gets
either a backend endpoint that 302-redirects to a freshly-signed URL, or (for
hot paths) a pre-signed URL with a short TTL embedded by the backend.

The module is import-safe: if R2 env vars are missing, helpers log a warning
and raise on use — they never crash at import time.
"""
import os
import io
import asyncio
import logging
import mimetypes
from typing import Optional, BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger("rilismusik")

R2_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL", "").rstrip("/")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET = os.environ.get("R2_BUCKET", "")
R2_PUBLIC_BASE_URL = os.environ.get("R2_PUBLIC_BASE_URL", "").rstrip("/")  # optional custom CDN domain

_DEFAULT_TTL = 3600  # 1h


def _client():
    """Build a boto3 S3 client pointed at R2. Cached on the function attribute."""
    if not getattr(_client, "_c", None):
        if not all([R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET]):
            raise RuntimeError("R2 credentials not configured — check R2_* env vars in /app/backend/.env")
        _client._c = boto3.client(
            "s3",
            endpoint_url=R2_ENDPOINT_URL,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            region_name="auto",
            config=Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
        )
    return _client._c


def is_configured() -> bool:
    return all([R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET])


def guess_content_type(filename: str, fallback: str = "application/octet-stream") -> str:
    if not filename:
        return fallback
    ct, _ = mimetypes.guess_type(filename)
    return ct or fallback


# ---------- Sync impl (run inside asyncio.to_thread) ----------
def _upload_bytes_sync(*, key: str, data: bytes, content_type: str) -> str:
    _client().put_object(
        Bucket=R2_BUCKET,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return key


def _upload_fileobj_sync(*, key: str, fileobj: BinaryIO, content_type: str) -> str:
    _client().upload_fileobj(
        Fileobj=fileobj,
        Bucket=R2_BUCKET,
        Key=key,
        ExtraArgs={"ContentType": content_type},
    )
    return key


def _generate_presigned_url_sync(*, key: str, ttl: int, filename: Optional[str] = None) -> str:
    params = {"Bucket": R2_BUCKET, "Key": key}
    if filename:
        # Force the browser to use this filename on download
        params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'
    return _client().generate_presigned_url("get_object", Params=params, ExpiresIn=ttl)


def _delete_object_sync(*, key: str) -> None:
    _client().delete_object(Bucket=R2_BUCKET, Key=key)


def _head_object_sync(*, key: str) -> Optional[dict]:
    try:
        return _client().head_object(Bucket=R2_BUCKET, Key=key)
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
            return None
        raise


# ---------- Async wrappers ----------
async def upload_bytes(*, key: str, data: bytes, content_type: str) -> str:
    """Upload raw bytes to R2. Returns the object key on success.

    Never overwrites silently — the key is treated as a stable identifier.
    If the caller wants atomic replace, they must delete first.
    """
    try:
        return await asyncio.to_thread(_upload_bytes_sync, key=key, data=data, content_type=content_type)
    except (BotoCoreError, ClientError) as e:
        logger.exception("[R2] upload_bytes failed key=%s: %s", key, e)
        raise


async def upload_fileobj(*, key: str, fileobj: BinaryIO, content_type: str) -> str:
    """Multipart-aware upload from a file-like object — preferred for large
    audio WAV files (boto3 chunks automatically above 8MB).
    """
    try:
        return await asyncio.to_thread(_upload_fileobj_sync, key=key, fileobj=fileobj, content_type=content_type)
    except (BotoCoreError, ClientError) as e:
        logger.exception("[R2] upload_fileobj failed key=%s: %s", key, e)
        raise


async def generate_presigned_url(*, key: str, ttl: int = _DEFAULT_TTL, filename: Optional[str] = None) -> str:
    """Generate a time-limited signed GET URL for an R2 object."""
    return await asyncio.to_thread(_generate_presigned_url_sync, key=key, ttl=ttl, filename=filename)


async def delete_object(*, key: str) -> None:
    """Best-effort delete — logs but doesn't raise on failure."""
    try:
        await asyncio.to_thread(_delete_object_sync, key=key)
    except (BotoCoreError, ClientError) as e:
        logger.warning("[R2] delete_object failed key=%s: %s", key, e)


async def head_object(*, key: str) -> Optional[dict]:
    """Return object metadata or None if not found."""
    try:
        return await asyncio.to_thread(_head_object_sync, key=key)
    except (BotoCoreError, ClientError) as e:
        logger.warning("[R2] head_object failed key=%s: %s", key, e)
        return None


# ---------- Convenience: upload a FastAPI UploadFile ----------
async def upload_upload_file(*, key: str, upload_file, content_type: Optional[str] = None) -> str:
    """Upload a FastAPI UploadFile to R2. Reads bytes once — fine for files
    up to a few hundred MB given Kubernetes ingress limits.
    """
    ct = content_type or upload_file.content_type or guess_content_type(upload_file.filename or key)
    data = await upload_file.read()
    return await upload_bytes(key=key, data=data, content_type=ct)
