"""A support completion can take down only its own linked live release."""
from fastapi import HTTPException
from models import new_id, now_iso
from .deps import db, log_activity
from .release_submission_quota import release_operation


async def complete_takedown_ticket(ticket, update, user):
    if ticket["status"] in ("cancelled", "rejected"):
        raise HTTPException(409, "Tiket ditolak/dibatalkan harus dibuka kembali sebelum diselesaikan.")
    release_id = ticket.get("release_id")
    async with release_operation(db, release_id, "support-takedown"):
        release = await db.releases.find_one({"id": release_id, "label_id": ticket["label_id"]}, {"_id": 0})
        if not release: raise HTTPException(404, "Rilisan tiket tidak ditemukan")
        if release.get("status") not in ("live", "partial", "taken_down"):
            raise HTTPException(409, "Takedown hanya dapat diselesaikan untuk rilisan Live/Tayang Sebagian atau yang sudah Takedown.")
        # partial = some tracks already live on DSPs, so it is taken down too.
        from_status = release["status"]
        stamp = now_iso(); event_id = new_id(); changed = from_status in ("live", "partial")
        if changed:
            event = {"id": event_id, "from": from_status, "to": "taken_down", "changed_by": user["id"], "changed_at": stamp,
                     "note": f"Tiket takedown {ticket['ticket_no']} selesai", "ticket_id": ticket["id"]}
            result = await db.releases.update_one({"id": release_id, "label_id": ticket["label_id"], "status": from_status},
                {"$set": {"status": "taken_down", "updated_at": stamp, "takedown_ticket_id": ticket["id"], "taken_down_at": stamp}, "$push": {"status_history": event}})
            if result.modified_count != 1: raise HTTPException(409, "Status rilisan berubah. Muat ulang tiket.")
        try:
            result = await db.support_tickets.update_one({"id": ticket["id"], "status": ticket["status"]},
                {"$set": {**update, "linked_release_status": "taken_down", "takedown_completed_at": stamp}})
            if result.matched_count != 1: raise HTTPException(409, "Status tiket berubah. Muat ulang halaman.")
        except Exception:
            if changed:
                restore = {"status": from_status, "updated_at": release.get("updated_at")}
                unset = {}
                for key in ("takedown_ticket_id", "taken_down_at"):
                    if key in release: restore[key] = release[key]
                    else: unset[key] = ""
                rollback = {"$set": restore, "$pull": {"status_history": {"id": event_id}}}
                if unset: rollback["$unset"] = unset
                await db.releases.update_one({"id": release_id, "status": "taken_down", "updated_at": stamp, "takedown_ticket_id": ticket["id"]}, rollback)
            raise
        if changed:
            await log_activity(user["id"], "ticket_release_takedown", "release", release_id, before={"status": from_status}, after={"status": "taken_down", "ticket_id": ticket["id"]})