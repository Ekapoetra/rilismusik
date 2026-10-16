"""Label rename / catalog transfer requests for label owners and admins."""
import re
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from models import now_iso
from .admin_permission_service import assert_admin_permission
from .deps import db, get_labels_for_user, log_activity, notify, require_admin, require_label
from .label_transfer_service import (
    LabelTransferDecisionIn, LabelTransferIn, apply_transfer, build_plan, build_transfer_request,
    can_apply_directly, can_decide, get_transfer, notify_submitted, preview_view, serialize, summarize,
)

label_transfer_r = APIRouter(tags=["label-transfers"])

_RELEASE_FIELDS = {"_id": 0, "id": 1, "release_title": 1, "primary_artist": 1, "upc": 1, "status": 1, "release_date": 1}


async def _preview(body: LabelTransferIn, actor: dict, kind: str) -> Dict[str, Any]:
    doc = await build_transfer_request(body, actor=actor, actor_kind=kind)
    return {"summary": summarize(doc), "transfer": doc, "plan": preview_view(await build_plan(doc))}


async def _releases(label_id: str):
    return await db.releases.find({"label_id": label_id}, _RELEASE_FIELDS).sort("release_date", -1).to_list(2000)


# ---------------------------------------------------------------- label owner
@label_transfer_r.get("/label/transfers")
async def label_list_transfers(user: dict = Depends(require_label)):
    items = await db.label_transfers.find(
        {"$or": [{"source_user_id": user["id"]}, {"target_user_id": user["id"]}]}, {"_id": 0},
    ).sort("requested_at", -1).to_list(100)
    # A sale's amounts belong to the seller; the other party sees only the summary.
    return [{**serialize(item), "plan": None} if item["mode"] == "sale" else serialize(item) for item in items]


@label_transfer_r.get("/label/transfers/options")
async def label_transfer_options(user: dict = Depends(require_label)):
    labels = await get_labels_for_user(user)
    return {"labels": [{
        "id": label["id"], "label_name": label.get("label_name"),
        "merged_into_label_name": label.get("merged_into_label_name"),
        "former_names": [alias.get("name") for alias in label.get("label_name_aliases") or []],
    } for label in labels]}


@label_transfer_r.get("/label/transfers/releases")
async def label_transfer_releases(label_id: str = Query(...), user: dict = Depends(require_label)):
    if not any(label["id"] == label_id for label in await get_labels_for_user(user)):
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    return await _releases(label_id)


@label_transfer_r.post("/label/transfers/preview")
async def label_preview_transfer(body: LabelTransferIn, user: dict = Depends(require_label)):
    return await _preview(body, user, "label")


@label_transfer_r.post("/label/transfers")
async def label_create_transfer(body: LabelTransferIn, user: dict = Depends(require_label)):
    doc = await build_transfer_request(body, actor=user, actor_kind="label")
    await build_plan(doc)  # refuse now what could never be applied
    doc["believe_confirmed"] = False  # only an admin can confirm the Believe side
    await db.label_transfers.insert_one(doc)
    await log_activity(user["id"], "label_transfer_request", "label", doc["source_label_id"], after={"transfer_id": doc["id"], "summary": summarize(doc)})
    await notify_submitted(doc)
    return serialize(doc)


@label_transfer_r.post("/label/transfers/{transfer_id}/cancel")
async def label_cancel_transfer(transfer_id: str, user: dict = Depends(require_label)):
    result = await db.label_transfers.update_one(
        {"id": transfer_id, "requested_by": user["id"], "status": "pending"},
        {"$set": {"status": "cancelled", "decided_at": now_iso(), "updated_at": now_iso()}},
    )
    if not result.matched_count:
        raise HTTPException(status_code=409, detail="Pengajuan tidak bisa dibatalkan")
    return await get_transfer(transfer_id)


# ---------------------------------------------------------------------- admin
@label_transfer_r.get("/admin/label-transfers")
async def admin_list_transfers(status: Optional[str] = Query(None, pattern="^(pending|approved|applying|failed|completed|rejected|cancelled)$"),
                               label_id: Optional[str] = None, user: dict = Depends(require_admin)):
    query: Dict[str, Any] = {}
    if status:
        query["status"] = status
    if label_id:
        query["$or"] = [{"source_label_id": label_id}, {"target_label_id": label_id}]
    items = await db.label_transfers.find(query, {"_id": 0}).sort("requested_at", -1).to_list(300)
    return [{**serialize(item), "can_decide": can_decide(user, item)} for item in items]


@label_transfer_r.get("/admin/label-transfers/labels")
async def admin_transfer_label_search(q: str = Query("", max_length=120), user: dict = Depends(require_admin)):
    query: Dict[str, Any] = {"merged_into_label_id": {"$in": [None, ""]}}
    if q.strip():
        query["label_name"] = {"$regex": re.escape(q.strip()), "$options": "i"}
    labels = await db.labels.find(query, {"_id": 0, "id": 1, "label_name": 1, "user_id": 1, "email": 1}).sort("label_name", 1).limit(30).to_list(30)
    return labels


@label_transfer_r.get("/admin/label-transfers/labels/{label_id}/releases")
async def admin_transfer_releases(label_id: str, user: dict = Depends(require_admin)):
    return await _releases(label_id)


@label_transfer_r.get("/admin/label-transfers/{transfer_id}")
async def admin_get_transfer(transfer_id: str, user: dict = Depends(require_admin)):
    doc = await get_transfer(transfer_id)
    return {**doc, "can_decide": can_decide(user, doc)}


@label_transfer_r.post("/admin/label-transfers/preview")
async def admin_preview_transfer(body: LabelTransferIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "labels.manage")
    return {**await _preview(body, user, "admin"), "can_apply_directly": can_apply_directly(user, body.mode)}


@label_transfer_r.post("/admin/label-transfers")
async def admin_create_transfer(body: LabelTransferIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "labels.manage")
    doc = await build_transfer_request(body, actor=user, actor_kind="admin")
    await build_plan(doc)
    direct = body.apply_now and can_apply_directly(user, body.mode)
    if direct:
        if not body.believe_confirmed:
            raise HTTPException(status_code=400, detail="Konfirmasi dulu bahwa perpindahan di Believe sudah berhasil")
        doc.update({"status": "approved", "decided_by": user["id"], "decided_by_name": doc["requested_by_name"],
                    "decided_at": now_iso(), "decision_note": "Diterapkan langsung"})
    await db.label_transfers.insert_one(doc)
    await log_activity(user["id"], "label_transfer_request", "label", doc["source_label_id"], after={"transfer_id": doc["id"], "summary": summarize(doc), "direct": direct})
    if direct:
        return await apply_transfer(doc["id"], user)
    await notify_submitted(doc)
    return serialize(doc)


@label_transfer_r.post("/admin/label-transfers/{transfer_id}/decision")
async def admin_decide_transfer(transfer_id: str, body: LabelTransferDecisionIn, user: dict = Depends(require_admin)):
    doc = await db.label_transfers.find_one({"id": transfer_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Perpindahan tidak ditemukan")
    if not can_decide(user, doc):
        detail = ("Penjualan label hanya bisa disetujui Super Admin selain pengaju" if doc["mode"] == "sale"
                  else "Anda tidak dapat memutuskan pengajuan ini")
        raise HTTPException(status_code=403, detail=detail)
    if body.action == "approve" and not body.believe_confirmed:
        raise HTTPException(status_code=400, detail="Konfirmasi dulu bahwa perpindahan di Believe sudah berhasil")
    decision = {"decided_by": user["id"], "decided_by_name": user.get("name") or user.get("email") or user["id"],
                "decided_at": now_iso(), "decision_note": (body.note or "").strip() or None, "updated_at": now_iso()}
    status = "approved" if body.action == "approve" else "rejected"
    extra = {"believe_confirmed": True} if status == "approved" else {}
    result = await db.label_transfers.update_one({"id": transfer_id, "status": "pending"},
                                                 {"$set": {**decision, **extra, "status": status}})
    if not result.matched_count:
        raise HTTPException(status_code=409, detail="Pengajuan sudah diproses")
    await log_activity(user["id"], f"label_transfer_{body.action}", "label", doc["source_label_id"], after={"transfer_id": transfer_id})
    if status == "rejected":
        if doc.get("requested_by_kind") == "label" or doc["requested_by"] != user["id"]:
            await notify(doc["requested_by"], "label_transfer_rejected", "Pengajuan Pindah Label Ditolak",
                         f"{summarize(doc)} ditolak.{(' Catatan: ' + decision['decision_note']) if decision['decision_note'] else ''}",
                         link="/label/dashboard" if doc.get("requested_by_kind") == "label" else "/admin/label-transfers",
                         meta={"transfer_id": transfer_id})
        return await get_transfer(transfer_id)
    return await apply_transfer(transfer_id, user)


@label_transfer_r.post("/admin/label-transfers/{transfer_id}/resume")
async def admin_resume_transfer(transfer_id: str, user: dict = Depends(require_admin)):
    doc = await db.label_transfers.find_one({"id": transfer_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Perpindahan tidak ditemukan")
    allowed = user["id"] in {doc.get("decided_by"), doc.get("applied_by")} or can_decide(user, doc) or can_apply_directly(user, doc["mode"])
    if not allowed:
        raise HTTPException(status_code=403, detail="Anda tidak dapat melanjutkan perpindahan ini")
    return await apply_transfer(transfer_id, user)
