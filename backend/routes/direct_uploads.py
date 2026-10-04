"""Private staging uploads for files too large for a Vercel request body.

Finalization invokes the existing upload route with the same authenticated
request, preserving its ownership, role, status and file-content validation.
"""
import asyncio
import os
import secrets
import tempfile
import time
from pathlib import Path
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.params import File as FileParameter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import storage_service
from .deps import db, get_current_user, UPLOAD_DIR

direct_upload_r = APIRouter(prefix="/uploads", tags=["uploads"])
MAX_UPLOAD_BYTES = 200 * 1024 * 1024


class UploadInitiateIn(BaseModel):
    target: str = Field(min_length=2, max_length=250)
    filename: str = Field(min_length=1, max_length=200)
    content_type: str = Field(default="application/octet-stream", max_length=100)
    size: int = Field(gt=0, le=MAX_UPLOAD_BYTES)
    fields: dict[str, str] = Field(default_factory=dict)
    query: dict[str, str | int | float | bool] = Field(default_factory=dict)


class UploadFinalizeIn(BaseModel):
    upload_id: str = Field(min_length=32, max_length=32)


def upload_route(request: Request, target: str):
    if not target.startswith("/") or target.startswith("//") or "?" in target or ".." in target or "\\" in target:
        raise HTTPException(400, "Tujuan unggahan tidak valid")
    path = "/api" + target
    for route in request.app.routes:
        if "POST" not in (getattr(route, "methods", None) or ()):
            continue
        if not getattr(route, "path_regex", None) or not route.path_regex.fullmatch(path):
            continue
        files = [field for field in route.dependant.body_params if isinstance(field.field_info, FileParameter)]
        if len(files) == 1 and files[0].name == "file":
            return route
    raise HTTPException(400, "Tujuan unggahan tidak didukung")


async def ensure_upload_origin(request: Request):
    from server import cors_origins, expand_origin_variants
    from .auth import _trusted_request_origin
    origin = _trusted_request_origin(request)
    allowed = set(cors_origins)
    for name in ("VERCEL_URL", "VERCEL_BRANCH_URL", "VERCEL_PROJECT_PRODUCTION_URL"):
        host = os.environ.get(name, "").strip()
        if host:
            allowed.update(expand_origin_variants(["https://" + host]))
    # These are the project's existing production domains, not arbitrary clients.
    allowed.update({"https://rilismusik.com", "https://www.rilismusik.com", "https://rilismusik.vercel.app"})
    if not origin or origin not in allowed:
        raise HTTPException(403, "Buka unggahan dari halaman aplikasi yang resmi")
    await storage_service.ensure_cors(sorted(allowed))


@direct_upload_r.post("/initiate")
async def initiate_upload(body: UploadInitiateIn, request: Request, user: dict = Depends(get_current_user)):
    upload_route(request, body.target)
    if len(body.fields) > 30 or len(body.query) > 20 or sum(map(len, body.fields.values())) > 100_000:
        raise HTTPException(400, "Metadata unggahan terlalu besar")
    await ensure_upload_origin(request)
    upload_id = secrets.token_hex(16)
    key = f"direct-uploads/{upload_id}/source"
    filename = body.filename.replace("\\", "/").rsplit("/", 1)[-1]
    await db.direct_upload_sessions.insert_one({
        "_id": upload_id, "actor_id": user["id"], "key": key, "target": body.target,
        "filename": filename, "content_type": body.content_type, "size": body.size,
        "fields": body.fields, "query": body.query, "status": "uploading",
        "created_epoch": time.time(), "expires_epoch": time.time() + 7200,
    })
    url = await storage_service.generate_presigned_put_url(key=key, content_type=body.content_type, ttl=7200)
    return {"upload_id": upload_id, "url": url, "content_type": body.content_type}


@direct_upload_r.post("/finalize")
async def finalize_upload(body: UploadFinalizeIn, request: Request, user: dict = Depends(get_current_user)):
    document = await db.direct_upload_sessions.find_one({"_id": body.upload_id, "actor_id": user["id"]})
    if not document:
        raise HTTPException(404, "Unggahan tidak ditemukan")
    if document.get("status") == "done":
        return JSONResponse(document["result"], status_code=document["result_status"])
    if document["expires_epoch"] < time.time():
        raise HTTPException(400, "Unggahan kedaluwarsa. Unggah kembali file Anda")
    upload_route(request, document["target"])
    claimed = await db.direct_upload_sessions.update_one({
        "_id": body.upload_id, "actor_id": user["id"], "status": "uploading",
    }, {"$set": {"status": "processing"}})
    if not claimed.matched_count:
        raise HTTPException(409, "Unggahan ini sedang atau sudah diproses")
    local_path = None
    try:
        meta = await storage_service.head_object(key=document["key"])
        if not meta or int(meta.get("ContentLength", 0)) != document["size"]:
            raise HTTPException(400, "Ukuran file unggahan tidak sesuai. Unggah kembali")
        staging = UPLOAD_DIR / "direct"
        staging.mkdir(parents=True, exist_ok=True)
        descriptor, local_path = tempfile.mkstemp(dir=staging)
        os.close(descriptor)
        await storage_service.download_to_file(key=document["key"], local_path=local_path)
        headers = {name: request.headers[name] for name in ("cookie", "authorization", "origin", "x-forwarded-host") if name in request.headers}
        target = "/api" + document["target"]
        if document.get("query"):
            target += "?" + urlencode(document["query"])
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=request.app), base_url=str(request.base_url), timeout=240) as client:
            with open(local_path, "rb") as source:
                result = await client.post(target, headers=headers, data=document["fields"],
                    files={"file": (document["filename"], source, document["content_type"])})
        try:
            payload = result.json()
        except ValueError:
            payload = {"detail": "Unggahan belum dapat diproses"}
        await db.direct_upload_sessions.update_one({"_id": body.upload_id, "actor_id": user["id"]}, {"$set": {
            "status": "done", "result": payload, "result_status": result.status_code,
        }})
        try:
            await storage_service.delete_object(key=document["key"])
        except Exception:
            pass
        return JSONResponse(payload, status_code=result.status_code)
    except Exception:
        await db.direct_upload_sessions.update_one({"_id": body.upload_id, "actor_id": user["id"], "status": "processing"},
            {"$set": {"status": "failed"}})
        raise
    finally:
        if local_path:
            Path(local_path).unlink(missing_ok=True)


async def cleanup_expired_direct_uploads():
    """Remove only expired transient upload objects; never final application files."""
    async for document in db.direct_upload_sessions.find({
        "expires_epoch": {"$lt": time.time()}, "status": {"$ne": "processing"},
        "cleaned": {"$ne": True},
    }).limit(100):
        key = document.get("key", "")
        if key != f"direct-uploads/{document['_id']}/source":
            continue
        await storage_service.delete_object(key=key)
        await db.direct_upload_sessions.update_one({"_id": document["_id"]}, {"$set": {"cleaned": True}})
