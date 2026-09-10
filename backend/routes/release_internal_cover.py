"""Private dashboard-only artwork. Never updates canonical distribution artwork."""
import io
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel
import storage_service
from models import new_id, now_iso
from .deps import db, get_current_user, get_label_by_user, require_kyc_for_label_user, log_activity, logger
from .admin_permission_service import has_permission, is_admin_identity
from .release_submission_quota import release_operation

internal_cover_r = APIRouter(prefix="/releases", tags=["internal-release-artwork"])


class InternalCoverOut(BaseModel):
    release_id: str
    internal_cover_url: str
    display_cover_url: str
    internal_cover_updated_at: str
    imported_legacy: bool = True


async def authorize_cover(release_id, user, write=False):
    release = await db.releases.find_one({"id": release_id}, {"_id": 0})
    if not release: raise HTTPException(404, "Rilisan tidak ditemukan")
    if user.get("role") == "label":
        label = await get_label_by_user(user)
        if release.get("label_id") != label["id"]: raise HTTPException(404, "Rilisan tidak ditemukan")
        if write and label.get("account_status") in ("suspended", "blacklisted"): raise HTTPException(403, "Akun tidak dapat mengubah cover")
    elif not is_admin_identity(user) or not (has_permission(user, "releases.review") or (not write and has_permission(user, "releases.view"))):
        raise HTTPException(403, "Anda tidak memiliki izin cover rilisan")
    if not release.get("imported_legacy"):
        raise HTTPException(400, "Cover internal hanya untuk rilisan legacy. Gunakan alur cover distribusi untuk rilisan web.")
    return release


@internal_cover_r.post("/{release_id}/internal-cover", response_model=InternalCoverOut)
async def upload_internal_cover(release_id: str, file: UploadFile = File(...), user: dict = Depends(require_kyc_for_label_user)):
    release = await authorize_cover(release_id, user, write=True)
    raw = await file.read(10 * 1024 * 1024 + 1)
    if len(raw) > 10 * 1024 * 1024: raise HTTPException(413, "Cover internal maksimal 10 MB")
    try:
        image = Image.open(io.BytesIO(raw))
        if image.format not in ("PNG", "JPEG") or image.width * image.height > 25_000_000: raise ValueError()
        image.verify(); image = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
        if min(image.size) < 100: raise ValueError()
        image.thumbnail((1600, 1600)); output = io.BytesIO(); image.save(output, "JPEG", quality=92)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(400, "Gunakan cover JPG/PNG yang valid, minimal 100 px dan maksimal 25 megapiksel.")
    async with release_operation(db, release_id, "internal-cover"):
        version = new_id(); key = f"release-internal/{release['label_id']}/{release_id}/{version}.jpg"; updated_at = now_iso()
        previous = await db.release_internal_covers.find_one({"_id": release_id}, {"_id": 0})
        url = f"/api/releases/{release_id}/internal-cover?v={version}"
        uploaded = False
        try:
            await storage_service.upload_bytes(key=key, data=output.getvalue(), content_type="image/jpeg"); uploaded = True
            await db.release_internal_covers.replace_one({"_id": release_id}, {"release_id": release_id, "label_id": release["label_id"], "key": key, "version": version, "uploaded_by": user["id"], "updated_at": updated_at}, upsert=True)
            result = await db.releases.update_one({"id": release_id, "imported_legacy": True}, {"$set": {"internal_cover_url": url, "internal_cover_updated_at": updated_at}})
            if not result.matched_count: raise HTTPException(409, "Rilisan telah berubah. Muat ulang halaman.")
        except Exception as exc:
            logger.exception("Internal cover update failed for release %s", release_id)
            if previous: await db.release_internal_covers.replace_one({"_id": release_id}, previous)
            else: await db.release_internal_covers.delete_one({"_id": release_id})
            if uploaded:
                try: await storage_service.delete_object(key=key)
                except Exception: logger.exception("Failed internal cover compensation")
            if isinstance(exc, HTTPException): raise
            raise HTTPException(502, "Cover internal gagal disimpan. Silakan coba lagi.")
        if previous:
            try: await storage_service.delete_object(key=previous["key"])
            except Exception: logger.warning("Previous internal cover cleanup pending for %s", release_id)
        try: await log_activity(user["id"], "update_internal_cover", "release", release_id, after={"internal_only": True, "version": version})
        except Exception: logger.exception("Internal cover audit mirror failed; uploader/version retained")
    return InternalCoverOut(release_id=release_id, internal_cover_url=url, display_cover_url=url, internal_cover_updated_at=updated_at)


@internal_cover_r.get("/{release_id}/internal-cover")
async def get_internal_cover(release_id: str, user: dict = Depends(get_current_user)):
    await authorize_cover(release_id, user)
    record = await db.release_internal_covers.find_one({"_id": release_id}, {"_id": 0})
    if not record: raise HTTPException(404, "Cover internal belum tersedia")
    try: data = await storage_service.download_bytes(key=record["key"])
    except Exception: raise HTTPException(502, "Cover belum dapat dimuat")
    return Response(data, media_type="image/jpeg", headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})