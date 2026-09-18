"""Shared deletion rules for label-owned and authorized admin releases."""
from fastapi import HTTPException
from pydantic import BaseModel

import storage_service
from .deps import db, log_activity, logger


class ReleaseDeletionResult(BaseModel):
    ok: bool
    deleted: str


async def delete_release_record(release_id: str, actor_id: str, *, label_id: str = None):
    release = await db.releases.find_one({"id": release_id}, {"_id": 0})
    if not release:
        raise HTTPException(status_code=404, detail="Rilisan tidak ditemukan")
    if label_id is not None and release.get("label_id") != label_id:
        raise HTTPException(status_code=403, detail="Bukan rilisan Anda")
    if release.get("status") not in ("draft", "rejected"):
        raise HTTPException(status_code=400, detail="Hanya rilisan berstatus draft atau ditolak yang dapat dihapus")

    tracks = await db.tracks.find({"release_id": release_id}, {"_id": 0, "audio_url": 1}).to_list(None)
    # Re-check status and ownership in the atomic delete, before touching any files.
    result = await db.releases.delete_one({
        "id": release_id, "status": release["status"], "label_id": release.get("label_id"),
    })
    if result.deleted_count != 1:
        raise HTTPException(status_code=409, detail="Status rilisan berubah atau rilisan sudah dihapus. Muat ulang daftar rilisan.")
    await db.tracks.delete_many({"release_id": release_id})
    # Void any still-open Xendit payment link so a deleted release can't be paid anymore.
    try:
        from payment_service import cancel_release_pending_payments
        await cancel_release_pending_payments(release_id, actor_id, "Rilisan dihapus")
    except Exception as exc:
        logger.warning("Pending payment cleanup failed for deleted release %s: %s", release_id, exc)
    internal = await db.release_internal_covers.find_one_and_delete({"_id": release_id}, projection={"_id": 0})
    if internal:
        try: await storage_service.delete_object(key=internal["key"])
        except Exception: logger.warning("Internal cover cleanup pending for deleted release %s", release_id)
    await log_activity(actor_id, "release_delete", "release", release_id, before={
        "status": release["status"], "title": release.get("release_title"), "label_id": release.get("label_id"),
    })

    urls = {release.get("cover_url"), *(track.get("audio_url") for track in tracks)}
    for url in urls:
        if not isinstance(url, str) or not url.startswith("/api/files/"):
            continue
        key = url.removeprefix("/api/files/")
        if not key:
            continue
        # Legacy releases may reference a shared file; never remove another release's asset.
        shared_cover = await db.releases.find_one({"cover_url": url}, {"_id": 0, "id": 1})
        shared_audio = await db.tracks.find_one({"audio_url": url}, {"_id": 0, "id": 1})
        if shared_cover or shared_audio:
            continue
        try:
            await storage_service.delete_object(key=key)
        except Exception as exc:
            logger.warning("Release file cleanup failed release=%s key=%s: %s", release_id, key, exc)
    return ReleaseDeletionResult(ok=True, deleted=release_id)