"""Approval workflow for sensitive bank-account changes."""
from typing import Any, Dict

from fastapi import HTTPException

from models import new_id, now_iso
from .deps import db


PENDING_BANK_CHANGE_STATUSES = {"pending_admin_approval", "pending_label_approval"}


def _bank_values(payload: Dict[str, Any]) -> Dict[str, str]:
    return {
        "bank_name": str(payload.get("bank_name") or "").strip(),
        "account_number": str(payload.get("account_number") or "").strip(),
        "account_holder_name": str(payload.get("account_holder_name") or "").strip(),
    }


async def create_bank_change_request(
    *, label: dict, payload: Dict[str, Any], requester: dict, approval_target: str,
) -> dict:
    current = await db.bank_accounts.find_one({"label_id": label["id"]}, {"_id": 0})
    if not current:
        raise HTTPException(status_code=400, detail="Rekening awal belum tersedia")
    pending = await db.bank_account_change_requests.find_one({
        "label_id": label["id"], "status": {"$in": list(PENDING_BANK_CHANGE_STATUSES)},
    }, {"_id": 0, "id": 1})
    if pending:
        raise HTTPException(status_code=409, detail="Masih ada permintaan perubahan rekening yang menunggu persetujuan")
    proposed = _bank_values(payload)
    current_values = _bank_values(current)
    if proposed == current_values:
        raise HTTPException(status_code=400, detail="Data rekening baru sama dengan rekening saat ini")
    status = "pending_admin_approval" if approval_target == "admin" else "pending_label_approval"
    document = {
        "id": new_id(),
        "label_id": label["id"],
        "label_name": label.get("label_name"),
        "current_bank": current_values,
        "proposed_bank": proposed,
        "reason": (payload.get("reason") or "").strip() or None,
        "requested_by": requester["id"],
        "requested_by_name": requester.get("name"),
        "requested_by_role": requester.get("role"),
        "approval_target": approval_target,
        "status": status,
        "reviewed_by": None,
        "reviewed_by_name": None,
        "review_note": None,
        "reviewed_at": None,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.bank_account_change_requests.insert_one(document)
    document.pop("_id", None)
    return document


async def review_bank_change_request(
    *, request_id: str, action: str, note: str | None, reviewer: dict,
    expected_status: str, label_id: str | None = None,
) -> dict:
    request_doc = await db.bank_account_change_requests.find_one({"id": request_id}, {"_id": 0})
    if not request_doc or (label_id and request_doc.get("label_id") != label_id):
        raise HTTPException(status_code=404, detail="Permintaan perubahan rekening tidak ditemukan")
    if request_doc.get("status") != expected_status:
        raise HTTPException(status_code=409, detail="Permintaan ini sudah diproses atau menunggu pihak lain")
    final_status = "approved" if action == "approve" else "rejected"
    claimed = await db.bank_account_change_requests.update_one(
        {"id": request_id, "status": expected_status},
        {"$set": {
            "status": final_status,
            "reviewed_by": reviewer["id"],
            "reviewed_by_name": reviewer.get("name"),
            "review_note": (note or "").strip() or None,
            "reviewed_at": now_iso(),
            "updated_at": now_iso(),
        }},
    )
    if not claimed.modified_count:
        raise HTTPException(status_code=409, detail="Permintaan sedang diproses oleh pihak lain")
    if action == "approve":
        proposed = request_doc["proposed_bank"]
        await db.bank_accounts.update_one(
            {"label_id": request_doc["label_id"]},
            {
                "$set": {
                    **proposed,
                    "verified_status": "verified",
                    "verified_by": reviewer["id"],
                    "verified_at": now_iso(),
                    "updated_at": now_iso(),
                },
                "$setOnInsert": {
                    "id": new_id(), "label_id": request_doc["label_id"], "created_at": now_iso(),
                },
            },
            upsert=True,
        )
        await db.labels.update_one(
            {"id": request_doc["label_id"]},
            {"$set": {"bank_verified": True, "updated_at": now_iso()}},
        )
    return await db.bank_account_change_requests.find_one({"id": request_id}, {"_id": 0})