"""Prepare immutable creator statements before publishing a Content ID ticket."""
import asyncio
from collections import Counter
from uuid import NAMESPACE_URL, uuid5

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
import storage_service
from models import new_id, now_iso
from .deps import db, logger
from .contentid_pdf import generate_contentid_pdf
from .believe_letters_generator import generate_indemnification_pdf_bytes, generate_dmca_pdf_bytes


def contentid_ticket_id(label_id, request_id):
    return str(uuid5(NAMESPACE_URL, f"rilis-contentid:{label_id}:{request_id}"))


def _dmca_explanation(tracks, artist):
    titles = ", ".join(f'"{t.get("track_title") or ""}"' for t in tracks) or '""'
    return (
        f"The removal of this content is a mistake. I am the original producer and rights owner of the "
        f'sound recording {titles} performed by "{artist or ""}". The track was created and produced by me '
        f"and legally distributed via Believe. I hold full rights to the master recording and composition. "
        f"The claimant does not own the rights to this recording. Therefore this claim is a misidentification "
        f"and should be withdrawn."
    )


async def rollback_contentid(ticket_id):
    async for doc in db.contentid_declarations.find({"ticket_id": ticket_id}, {"_id": 0, "id": 1, "pdf_key": 1}):
        try: await storage_service.delete_object(key=doc["pdf_key"])
        except Exception: logger.warning("Content ID PDF cleanup pending: %s", doc["id"])
    await db.contentid_declarations.delete_many({"ticket_id": ticket_id})
    await db.contentid_assets.update_many({"ticket_id": ticket_id, "status": {"$in": ["reserved", "bound"]}}, {"$set": {"status": "staged", "ticket_id": None}})
    await db.contentid_requests.delete_one({"_id": ticket_id})


async def build_contentid_documents(body, release, label, ticket_id, user):
    creators = body.content_id_creators or []
    selected = body.content_id_track_ids
    if not creators or not selected or body.content_id_consent is not True:
        raise HTTPException(400, "Pilih lagu, lengkapi identitas, KTP dan tanda tangan pencipta, lalu setujui pernyataan.")
    if len(set(selected)) != len(selected):
        raise HTTPException(400, "Lagu yang dipilih tidak boleh duplikat")
    tracks = await db.tracks.find({"release_id": release["id"], "id": {"$in": selected}}, {"_id": 0, "id": 1, "track_number": 1, "track_title": 1, "isrc": 1}).sort("track_number", 1).to_list(200)
    if {track["id"] for track in tracks} != set(selected):
        raise HTTPException(400, "Lagu harus berasal dari rilisan terpilih")
    if len({creator.nik for creator in creators}) != len(creators):
        raise HTTPException(400, "Satu pencipta cukup satu formulir. Gabungkan lagu untuk NIK yang sama.")
    assigned = set()
    asset_ids = []
    for creator in creators:
        if len(set(creator.track_ids)) != len(creator.track_ids) or not set(creator.track_ids).issubset(selected):
            raise HTTPException(400, "Penugasan lagu pencipta tidak sesuai lagu yang dipilih")
        assigned.update(creator.track_ids)
        asset_ids += [creator.signature_asset_id, creator.ktp_asset_id]
    if assigned != set(selected) or len(set(asset_ids)) != len(asset_ids):
        raise HTTPException(400, "Setiap lagu wajib memiliki pencipta dan setiap pencipta wajib memiliki dokumen sendiri.")
    assets = await db.contentid_assets.find({"id": {"$in": asset_ids}, "label_id": label["id"], "release_id": release["id"], "uploaded_by": user["id"], "status": "staged", "expires_at": {"$gt": now_iso()}}, {"_id": 0}).to_list(40)
    by_id = {asset["id"]: asset for asset in assets}
    if len(assets) != len(asset_ids) or any(by_id[c.signature_asset_id]["kind"] != "signature" or by_id[c.ktp_asset_id]["kind"] != "ktp" for c in creators):
        raise HTTPException(400, "KTP atau tanda tangan tidak valid, telah digunakan, atau bukan milik pengajuan ini.")
    try:
        await db.contentid_requests.insert_one({"_id": ticket_id, "label_id": label["id"], "created_at": now_iso(), "updated_at": now_iso()})
    except DuplicateKeyError:
        raise HTTPException(409, "Pengajuan ini sedang diproses. Tunggu sebentar lalu periksa daftar tiket.")
    pdf_keys = []
    try:
        for asset in assets:
            claim = await db.contentid_assets.update_one({"id": asset["id"], "status": "staged"}, {"$set": {"ticket_id": ticket_id, "status": "reserved"}})
            if claim.modified_count != 1:
                raise HTTPException(409, "Dokumen sedang digunakan oleh pengajuan lain")
        overlaps = Counter(track_id for creator in creators for track_id in creator.track_ids)
        docs = []
        issued_at = now_iso()
        artist_name = release.get("artist_name") or ""
        upc = str(release.get("upc") or "")
        for index, creator in enumerate(creators):
            await db.contentid_requests.update_one({"_id": ticket_id}, {"$set": {"updated_at": now_iso()}})
            doc_id = new_id(); key = f"contentid-private/{label['id']}/letters/{ticket_id}/{doc_id}.pdf"
            indem_key = f"contentid-private/{label['id']}/letters/{ticket_id}/{doc_id}-indemnification.pdf"
            dmca_key = f"contentid-private/{label['id']}/letters/{ticket_id}/{doc_id}-dmca.pdf"
            creator_tracks = [track for track in tracks if track["id"] in creator.track_ids]
            doc = {"id": doc_id, "ticket_id": ticket_id, "label_id": label["id"], "sequence": index + 1,
                   "creator_name": creator.full_name, "nik": creator.nik, "domicile": creator.domicile,
                   "signing_city": creator.signing_city, "issued_at": issued_at, "release_title": release.get("release_title") or "",
                   "upc": upc, "tracks": creator_tracks,
                   "signature_asset_id": creator.signature_asset_id, "ktp_asset_id": creator.ktp_asset_id,
                   "authorship": "joint" if creator.authorship == "joint" or any(overlaps[t] > 1 for t in creator.track_ids) else "sole",
                   "pdf_key": key, "indemnification_pdf_key": indem_key, "dmca_pdf_key": dmca_key,
                   "status": "ready", "consent_by": user["id"], "consent_at": issued_at, "template_version": 2}
            signature = await storage_service.download_bytes(key=by_id[creator.signature_asset_id]["storage_key"])
            ktp = await storage_service.download_bytes(key=by_id[creator.ktp_asset_id]["storage_key"])
            pdf = await asyncio.to_thread(generate_contentid_pdf, doc, signature, ktp)
            pdf_keys.append(key)
            await storage_service.upload_bytes(key=key, data=pdf, content_type="application/pdf")
            # Indemnification Letter — signed with the creator's own signature; company = label name.
            creator_isrcs = [t.get("isrc") for t in creator_tracks if t.get("isrc")]
            indem_pdf = await asyncio.to_thread(
                generate_indemnification_pdf_bytes,
                isrcs=creator_isrcs, upc=upc,
                legal_entity={"company_name": label.get("label_name") or "", "city": creator.signing_city},
                document_settings={"responsible_person_name": creator.full_name, "responsible_person_title": "Pencipta / Pemilik Hak"},
                signature_bytes=signature,
            )
            pdf_keys.append(indem_key)
            await storage_service.upload_bytes(key=indem_key, data=indem_pdf, content_type="application/pdf")
            # DMCA Counter Notification — auto-filled from creator + label; signed with creator legal name.
            dmca_items = [{"isrc": t.get("isrc"), "title": t.get("track_title"), "artist": artist_name} for t in creator_tracks]
            dmca_contact = {"legal_name": creator.full_name, "phone": label.get("whatsapp") or "",
                            "email": user.get("email") or "", "country": "Indonesia",
                            "street": label.get("address") or "", "city": label.get("city") or creator.domicile or "", "postcode": ""}
            dmca_pdf = await asyncio.to_thread(
                generate_dmca_pdf_bytes,
                items=dmca_items, explanation=_dmca_explanation(creator_tracks, artist_name),
                contact=dmca_contact, signature_name=creator.full_name,
            )
            pdf_keys.append(dmca_key)
            await storage_service.upload_bytes(key=dmca_key, data=dmca_pdf, content_type="application/pdf")
            docs.append(doc)
        await db.contentid_declarations.insert_many([doc.copy() for doc in docs])
        return [{"id": doc["id"], "creator_name": doc["creator_name"], "track_count": len(doc["tracks"]), "status": "ready"} for doc in docs]
    except Exception as exc:
        for key in pdf_keys:
            try: await storage_service.delete_object(key=key)
            except Exception: logger.warning("Content ID partial PDF cleanup will retry")
        await rollback_contentid(ticket_id)
        if isinstance(exc, HTTPException): raise
        logger.error("Content ID generation failed for ticket %s (%s)", ticket_id, type(exc).__name__)
        raise HTTPException(502, "Surat pernyataan gagal dibuat. Tiket belum dikirim; silakan coba lagi.")