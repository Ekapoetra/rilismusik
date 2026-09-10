"""Private creator ID/signature intake and authenticated binary delivery."""
import hashlib
import io
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

import storage_service
from contentid_models import ContentIdAssetOut, ContentIdDocumentOut
from models import new_id, now_iso
from .deps import db, get_current_user, get_label_by_user, require_label, log_activity, logger

contentid_r = APIRouter(prefix="/tickets/content-id", tags=["content-id-documents"])
PRIVATE_HEADERS = {"Cache-Control": "no-store, private", "Pragma": "no-cache", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"}


async def visible_ticket(ticket_id, user):
    from .tickets import _ticket_visible_to
    ticket = await db.support_tickets.find_one({"id": ticket_id}, {"_id": 0})
    if not ticket or not await _ticket_visible_to(user, ticket):
        raise HTTPException(404, "Dokumen tidak ditemukan")
    return ticket


async def normalized_image(file, kind):
    limit = (5 if kind == "signature" else 10) * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"File melebihi batas {limit // (1024 * 1024)} MB")
    try:
        image = Image.open(io.BytesIO(data))
        if image.format not in ("PNG", "JPEG") or image.width * image.height > 25_000_000:
            raise ValueError()
        image.verify()
        image = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
        if min(image.size) < 24:
            raise ValueError()
        image = image.convert("RGBA")
        matte = Image.new("RGBA", image.size, "white"); matte.alpha_composite(image)
        gray = matte.convert("L")
        low, high = gray.getextrema()
        if high - low < 12:
            raise HTTPException(400, "Gambar kosong atau tidak terbaca. Unggah gambar yang jelas.")
        if kind == "signature":
            ink = gray.point(lambda value: 255 if value < 235 else 0)
            box = ink.getbbox()
            if not box or max(box[2] - box[0], box[3] - box[1]) < 24 or (box[2] - box[0]) * (box[3] - box[1]) < 120:
                raise HTTPException(400, "Tanda tangan terlalu kecil. Gambar atau unggah tanda tangan yang jelas.")
            padding = max(10, round(max(box[2] - box[0], box[3] - box[1]) * .03))
            image = image.crop((max(0, box[0] - padding), max(0, box[1] - padding), min(image.width, box[2] + padding), min(image.height, box[3] + padding)))
        image.thumbnail((1600, 1600) if kind == "signature" else (2400, 2400))
        output = io.BytesIO()
        image.save(output, "PNG", optimize=True)
        return output.getvalue()
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(400, "Gunakan gambar PNG/JPG yang valid, maksimal 25 megapiksel.")


@contentid_r.post("/assets", response_model=ContentIdAssetOut)
async def upload_asset(release_id: str = Form(...), kind: Literal["signature", "ktp"] = Form(...),
                       signature_mode: Literal["upload", "drawn"] = Form("upload"),
                       file: UploadFile = File(...), user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    if label.get("account_status") in ("suspended", "blacklisted"):
        raise HTTPException(403, "Akun tidak dapat mengunggah dokumen")
    if not await db.releases.find_one({"id": release_id, "label_id": label["id"]}, {"_id": 0, "id": 1}):
        raise HTTPException(404, "Rilisan tidak ditemukan")
    data = await normalized_image(file, kind)
    asset_id = new_id(); key = f"contentid-private/{label['id']}/assets/{asset_id}.png"
    doc = {"id": asset_id, "kind": kind, "label_id": label["id"], "release_id": release_id,
           "uploaded_by": user["id"], "storage_key": key, "filename": f"{kind}.png", "content_type": "image/png",
           "size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "signature_mode": signature_mode,
           "status": "staged", "ticket_id": None, "created_at": now_iso(),
           "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()}
    try:
        await storage_service.upload_bytes(key=key, data=data, content_type="image/png")
        await db.contentid_assets.insert_one(doc)
    except Exception:
        try: await storage_service.delete_object(key=key)
        except Exception: logger.warning("Content ID upload compensation pending: %s", asset_id)
        raise HTTPException(502, "Dokumen gagal disimpan. Silakan coba lagi.")
    return ContentIdAssetOut(**{k: doc[k] for k in ContentIdAssetOut.model_fields})


async def owned_asset(asset_id, user):
    asset = await db.contentid_assets.find_one({"id": asset_id}, {"_id": 0})
    if not asset:
        raise HTTPException(404, "Dokumen tidak ditemukan")
    if asset.get("status") == "bound":
        await visible_ticket(asset["ticket_id"], user)
    else:
        if user.get("role") != "label" or asset["uploaded_by"] != user["id"] or asset["expires_at"] <= now_iso():
            raise HTTPException(404, "Dokumen tidak ditemukan")
    return asset


async def binary_response(key, content_type, filename, attachment=False):
    try:
        data = await storage_service.download_bytes(key=key)
    except Exception:
        raise HTTPException(502, "Dokumen belum dapat diunduh. Silakan coba lagi.")
    disposition = "attachment" if attachment else "inline"
    return Response(data, media_type=content_type, headers={**PRIVATE_HEADERS, "Content-Disposition": f'{disposition}; filename="{filename}"'})


@contentid_r.get("/assets/{asset_id}")
async def get_asset(asset_id: str, download: bool = False, user: dict = Depends(get_current_user)):
    asset = await owned_asset(asset_id, user)
    await log_activity(user["id"], "contentid_asset_access", "support", asset.get("ticket_id") or asset_id,
                       after={"asset_id": asset_id, "kind": asset["kind"]})
    return await binary_response(asset["storage_key"], asset["content_type"], asset["filename"], download)


@contentid_r.delete("/assets/{asset_id}")
async def delete_staged_asset(asset_id: str, user: dict = Depends(require_label)):
    asset = await db.contentid_assets.find_one_and_delete({"id": asset_id, "uploaded_by": user["id"], "status": "staged"}, projection={"_id": 0})
    if not asset:
        raise HTTPException(404, "Dokumen tidak tersedia atau sudah digunakan pada tiket")
    try:
        await storage_service.delete_object(key=asset["storage_key"])
    except Exception:
        await db.contentid_assets.insert_one(asset)
        raise HTTPException(502, "Dokumen belum dapat dihapus")
    return {"ok": True}


@contentid_r.get("/tickets/{ticket_id}", response_model=list[ContentIdDocumentOut])
async def list_documents(ticket_id: str, response: Response, user: dict = Depends(get_current_user)):
    await visible_ticket(ticket_id, user)
    response.headers.update(PRIVATE_HEADERS)
    documents = await db.contentid_declarations.find({"ticket_id": ticket_id}, {"_id": 0, "pdf_key": 0, "label_id": 0}).sort("sequence", 1).to_list(20)
    if documents:
        await log_activity(user["id"], "contentid_identity_access", "support", ticket_id, after={"document_count": len(documents)})
    return [ContentIdDocumentOut(**item) for item in documents]


@contentid_r.get("/tickets/{ticket_id}/{document_id}/pdf")
async def download_pdf(ticket_id: str, document_id: str, user: dict = Depends(get_current_user)):
    await visible_ticket(ticket_id, user)
    doc = await db.contentid_declarations.find_one({"id": document_id, "ticket_id": ticket_id, "status": "ready"}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Surat tidak ditemukan")
    await log_activity(user["id"], "contentid_pdf_download", "support", ticket_id, after={"document_id": document_id})
    return await binary_response(doc["pdf_key"], "application/pdf", f"Surat-Pernyataan-Hak-Cipta-{doc['sequence']}.pdf", True)


async def cleanup_expired_contentid_assets():
    # Only unsubmitted uploads in this dedicated collection; never submitted KTP/signatures.
    async for asset in db.contentid_assets.find({"status": "staged", "expires_at": {"$lt": now_iso()}}, {"_id": 0}).limit(200):
        removed = await db.contentid_assets.find_one_and_delete({"id": asset["id"], "status": "staged"}, projection={"_id": 0})
        if removed:
            try: await storage_service.delete_object(key=removed["storage_key"])
            except Exception:
                await db.contentid_assets.insert_one(removed)
                logger.warning("Expired Content ID asset cleanup will retry: %s", removed["id"])


async def contentid_maintenance():
    import asyncio
    from .contentid_service import rollback_contentid
    indexed = False
    while True:
        try:
            if not indexed:
                for collection in (db.contentid_assets, db.contentid_declarations):
                    await collection.create_index("id", unique=True)
                await db.contentid_assets.create_index([("status", 1), ("expires_at", 1)])
                await db.contentid_declarations.create_index("ticket_id")
                indexed = True
            await cleanup_expired_contentid_assets()
            stale = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
            async for request in db.contentid_requests.find({"updated_at": {"$lt": stale}}, {"_id": 1}).limit(100):
                ticket_id = request["_id"]
                if await db.support_tickets.find_one({"id": ticket_id}, {"_id": 0, "id": 1}):
                    await db.contentid_assets.update_many({"ticket_id": ticket_id, "status": "reserved"}, {"$set": {"status": "bound"}})
                    await db.contentid_requests.delete_one({"_id": ticket_id})
                else:
                    await rollback_contentid(ticket_id)
        except Exception as exc:
            logger.warning("Content ID maintenance will retry (%s)", type(exc).__name__)
        await asyncio.sleep(900)