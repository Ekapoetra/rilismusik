"""KYC readiness, private document handling, and feature authorization."""
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException

from .deps import db


KYC_REQUIRED_CODE = "KYC_REQUIRED"


def valid_whatsapp(value: Optional[str]) -> bool:
    raw = str(value or "").strip()
    digits = re.sub(r"\D", "", raw)
    return 8 <= len(digits) <= 16 and (
        raw.startswith("+") or raw.startswith("0") or raw.startswith("62")
    )


def _active_contract_query(label_id: str) -> Dict[str, Any]:
    today = datetime.now(timezone.utc).date().isoformat()
    return {
        "label_id": label_id,
        "status": {"$in": ["active", "signed"]},
        "$and": [
            {"$or": [{"start_date": {"$exists": False}}, {"start_date": None}, {"start_date": {"$lte": today}}]},
            {"$or": [{"end_date": {"$exists": False}}, {"end_date": None}, {"end_date": {"$gte": today}}]},
        ],
    }


async def compute_kyc_state(*, user: Dict[str, Any], label: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if label is None:
        label = await db.labels.find_one({"user_id": user["id"]}, {"_id": 0})
    if not label:
        raise HTTPException(status_code=404, detail="Label belum diset")
    bank = await db.bank_accounts.find_one(
        {"label_id": label["id"]},
        {"_id": 0, "bank_name": 1, "account_number": 1, "account_holder_name": 1, "verified_status": 1},
    )
    contract = await db.contracts.find_one(
        _active_contract_query(label["id"]), {"_id": 0, "id": 1, "status": 1, "start_date": 1, "end_date": 1},
        sort=[("created_at", -1)],
    )
    doc = None
    if label.get("kyc_document_id"):
        doc = await db.kyc_documents.find_one(
            {"id": label["kyc_document_id"], "label_id": label["id"], "is_current": True},
            {"_id": 0, "storage_key": 0, "sha256": 0},
        )
    checks = [
        {"key": "pic_name", "label": "Nama Penanggung Jawab", "complete": bool(str(label.get("pic_name") or "").strip()), "action_path": "/label/profile"},
        {"key": "label_name", "label": "Nama Label", "complete": bool(str(label.get("label_name") or "").strip()), "action_path": "/label/profile"},
        {"key": "logo", "label": "Logo Label", "complete": bool(label.get("logo_storage_key")), "action_path": "/label/profile"},
        {"key": "email", "label": "Email Aktif & Terverifikasi", "complete": bool(user.get("email") and user.get("email_verified_at") and user.get("status") == "active"), "action_path": "/label/profile"},
        {"key": "whatsapp", "label": "Kontak WhatsApp Aktif", "complete": valid_whatsapp(label.get("whatsapp")), "action_path": "/label/profile"},
        {"key": "contract", "label": "Kontrak Aktif", "complete": bool(contract), "action_path": "/label/contract"},
        {"key": "bank", "label": "Nomor Rekening Lengkap", "complete": bool(bank and all(str(bank.get(field) or "").strip() for field in ("bank_name", "account_number", "account_holder_name"))), "action_path": "/label/profile"},
        {"key": "address", "label": "Alamat", "complete": bool(str(label.get("address") or "").strip()), "action_path": "/label/profile"},
        {"key": "city", "label": "Kota", "complete": bool(str(label.get("city") or "").strip()), "action_path": "/label/profile"},
    ]
    prerequisites_complete = all(item["complete"] for item in checks)
    stored_status = label.get("kyc_status") or "incomplete"
    document_status = (doc or {}).get("status")
    is_verified = bool(stored_status == "verified" and document_status == "verified" and prerequisites_complete)
    if is_verified:
        status = "verified"
    elif stored_status == "verified" and not prerequisites_complete:
        status = "needs_update"
    elif document_status == "pending_review":
        status = "pending_review"
    elif document_status == "rejected" or stored_status == "rejected":
        status = "rejected"
    else:
        status = "incomplete"
    completed = sum(1 for item in checks if item["complete"]) + (1 if document_status in ("pending_review", "verified") else 0)
    return {
        "status": status,
        "is_verified": is_verified,
        "prerequisites_complete": prerequisites_complete,
        "completed": completed,
        "total": len(checks) + 1,
        "missing_keys": [item["key"] for item in checks if not item["complete"]],
        "checks": checks,
        "document": doc,
        "rejection_reason": (doc or {}).get("rejection_reason") or label.get("kyc_rejection_reason"),
        "verified_at": label.get("kyc_verified_at") if is_verified else None,
        "contract": contract,
        "bank_complete": next(item["complete"] for item in checks if item["key"] == "bank"),
    }


async def ensure_label_kyc(user: Dict[str, Any]) -> Dict[str, Any]:
    if user.get("role") != "label":
        return {"is_verified": True}
    state = await compute_kyc_state(user=user)
    if not state["is_verified"]:
        raise HTTPException(status_code=403, detail={
            "code": KYC_REQUIRED_CODE,
            "message": "Aktivasi KYC diperlukan untuk membuka fitur ini.",
            "status": state["status"],
            "missing_keys": state["missing_keys"],
        })
    return state