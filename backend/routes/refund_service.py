"""Payment refunds for orphaned paid payments (release rejected or deleted).

Refund method per business decision = MANUAL: admin transfers the money outside
the system, then marks the payment as 'refunded' here (status/audit record only).
No balance credit and no Xendit refund call is made. Gated by `payments.refund`
(Super Admin only by default).
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from models import now_iso
from .deps import db, require_admin, log_activity
from .admin_permission_service import assert_admin_permission

refund_r = APIRouter(prefix="/admin/refunds", tags=["refunds"])

# Payments tied to a release (the reject/delete scenario).
_RELEASE_PAYMENT_TYPES = ["pay_per_release", "release_shortfall"]


async def _label_names(label_ids: List[str]) -> Dict[str, str]:
    names: Dict[str, str] = {}
    async for lab in db.labels.find({"id": {"$in": list(set(label_ids))}}, {"_id": 0, "id": 1, "label_name": 1}):
        names[lab["id"]] = lab.get("label_name") or "-"
    return names


async def _build_item(pay: Dict[str, Any], release_status: str, release_title: Optional[str], label_name: str) -> Dict[str, Any]:
    return {
        "payment_id": pay["id"],
        "label_id": pay.get("label_id"),
        "label_name": label_name,
        "amount_idr": int(pay.get("amount") or 0),
        "type": pay.get("type"),
        "paid_at": pay.get("paid_at"),
        "created_at": pay.get("created_at"),
        "release_id": pay.get("release_id"),
        "release_title": release_title or pay.get("release_title_snapshot") or "-",
        "release_status": release_status,  # 'rejected' | 'deleted'
        "refund_status": pay.get("refund_status"),
        "refunded_at": pay.get("refunded_at"),
        "refunded_by_name": pay.get("refunded_by_name"),
        "refund_note": pay.get("refund_note"),
    }


async def _scan(refunded: bool) -> List[Dict[str, Any]]:
    match: Dict[str, Any] = {"status": "paid", "release_id": {"$ne": None}, "type": {"$in": _RELEASE_PAYMENT_TYPES}}
    if refunded:
        match["refund_status"] = "refunded"
    else:
        match["refund_status"] = {"$ne": "refunded"}
    payments = await db.payments.find(match, {"_id": 0}).sort("paid_at", -1).to_list(5000)

    release_ids = list({p.get("release_id") for p in payments if p.get("release_id")})
    releases: Dict[str, Dict[str, Any]] = {}
    async for rel in db.releases.find({"id": {"$in": release_ids}}, {"_id": 0, "id": 1, "status": 1, "release_title": 1}):
        releases[rel["id"]] = rel
    label_names = await _label_names([p.get("label_id") for p in payments if p.get("label_id")])

    out: List[Dict[str, Any]] = []
    for p in payments:
        rel = releases.get(p.get("release_id"))
        if rel is None:
            release_status, title = "deleted", None
        elif rel.get("status") == "rejected":
            release_status, title = "rejected", rel.get("release_title")
        else:
            if not refunded:
                continue  # release is healthy → not an orphan
            release_status, title = rel.get("status") or "-", rel.get("release_title")
        out.append(await _build_item(p, release_status, title, label_names.get(p.get("label_id"), "-")))
    return out


@refund_r.get("/pending")
async def pending_refunds(user: dict = Depends(require_admin)):
    assert_admin_permission(user, "payments.refund")
    items = await _scan(refunded=False)
    return {"items": items, "total_idr": sum(i["amount_idr"] for i in items), "count": len(items)}


@refund_r.get("/history")
async def refund_history(user: dict = Depends(require_admin)):
    assert_admin_permission(user, "payments.refund")
    items = await _scan(refunded=True)
    return {"items": items, "total_idr": sum(i["amount_idr"] for i in items), "count": len(items)}


class MarkRefundedIn(BaseModel):
    note: str = Field(..., min_length=3, max_length=500)  # transfer reference / manual proof


@refund_r.post("/{payment_id}/mark-refunded")
async def mark_refunded(payment_id: str, body: MarkRefundedIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "payments.refund")
    pay = await db.payments.find_one({"id": payment_id}, {"_id": 0})
    if not pay:
        raise HTTPException(status_code=404, detail="Pembayaran tidak ditemukan")
    if pay.get("status") != "paid":
        raise HTTPException(status_code=409, detail="Hanya pembayaran berstatus lunas yang bisa direfund")
    if pay.get("refund_status") == "refunded":
        raise HTTPException(status_code=409, detail="Pembayaran ini sudah ditandai direfund")
    # Guard: must genuinely be an orphan (release rejected or missing).
    rel = await db.releases.find_one({"id": pay.get("release_id")}, {"_id": 0, "status": 1}) if pay.get("release_id") else None
    if rel is not None and rel.get("status") != "rejected":
        raise HTTPException(status_code=400, detail="Rilisan masih aktif — hanya rilisan ditolak/dihapus yang bisa direfund")
    patch = {
        "refund_status": "refunded",
        "refunded_by": user["id"],
        "refunded_by_name": user.get("name") or user.get("email"),
        "refunded_at": now_iso(),
        "refund_method": "manual_transfer",
        "refund_note": body.note.strip(),
        "updated_at": now_iso(),
    }
    await db.payments.update_one({"id": payment_id}, {"$set": patch})
    await log_activity(user["id"], "payment_mark_refunded", "payment", payment_id,
                       before={"refund_status": pay.get("refund_status")},
                       after={"refund_status": "refunded", "amount": int(pay.get("amount") or 0), "note": body.note.strip()})
    return {"ok": True, "payment_id": payment_id, **patch}
