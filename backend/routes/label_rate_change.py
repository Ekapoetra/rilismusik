"""Sensitive Action: Label Rate/Fee Change — request → approval → apply workflow.

Separates the DIRECT change (labels.rate) from the request/approval flow
(labels.rate.request / labels.rate.request.view / labels.rate.approve). The live
royalty percentage never changes until a Super Admin approves the request or an
authorized holder performs a direct change. Every change is audited.
"""
import asyncio
import secrets
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException

from models import RateChangeRequestIn, RateChangeDecisionIn, new_id, now_iso
from .deps import db, log_activity, notify, notify_many, require_admin
from .admin_permission_service import assert_admin_permission
from .royalty_recalculation import run_label_recalculation_job


rate_change_r = APIRouter(prefix="/admin", tags=["rate-change"])


def _reference_id() -> str:
    return "RC-" + secrets.token_hex(4).upper()


def _actor_name(user: dict) -> str:
    return user.get("name") or user.get("role_name") or user.get("email") or user["id"]


async def _get_label(label_id: str) -> dict:
    label = await db.labels.find_one({"id": label_id}, {"_id": 0})
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    return label


async def _guard_active_withdraw(label_id: str) -> None:
    active = await db.withdraw_requests.find_one({
        "label_id": label_id,
        "status": {"$in": ["requested", "approved"]},
        "legacy_import": {"$ne": True},
    }, {"_id": 0, "id": 1})
    if active:
        raise HTTPException(status_code=409, detail="Selesaikan atau tolak withdraw aktif sebelum mengubah persentase royalti.")


async def _approver_ids() -> list:
    role_ids = await db.admin_roles.distinct("id", {"permissions": "labels.rate.approve", "active": {"$ne": False}})
    ids = []
    async for u in db.users.find(
        {"$or": [{"role": "super_admin"}, {"admin_role_id": {"$in": role_ids}}], "status": {"$nin": ["suspended", "disabled"]}},
        {"_id": 0, "id": 1},
    ):
        ids.append(u["id"])
    return ids


async def _apply_rate_change(*, label: dict, percentage: float, reason: str, actor: dict, source: str) -> Optional[str]:
    """Apply the value using the existing safe recalculation workflow. Guard runs when the value actually changes."""
    label_id = label["id"]
    percentage = float(percentage)
    current = float(label.get("royalty_percentage_default", 60) or 60)
    if current != percentage:
        await _guard_active_withdraw(label_id)
    await db.royalty_percentage_history.insert_one({
        "id": new_id(), "label_id": label_id, "percentage": percentage,
        "effective_month": now_iso()[:7], "changed_by": actor["id"], "changed_at": now_iso(),
        "reason": reason, "source": source,
    })
    update: Dict[str, Any] = {"royalty_percentage_default": percentage, "updated_at": now_iso()}
    job_id = None
    if current != percentage:
        job_id = new_id()
        update.update({"royalty_recalculation_status": "queued", "royalty_recalculation_job_id": job_id})
        await db.migrate_jobs.insert_one({
            "id": job_id, "kind": "recalculate_label_unwithdrawn", "status": "queued",
            "label_id": label_id, "percentage": percentage, "submitted_by": actor["id"],
            "submitted_at": now_iso(), "updated_at": now_iso(),
            "progress_lines_done": 0, "progress_lines_total": 0,
        })
    await db.labels.update_one({"id": label_id}, {"$set": update})
    await log_activity(actor["id"], f"rate_change_{source}", "label", label_id,
                       before={"royalty_percentage_default": current},
                       after={"royalty_percentage_default": percentage, "reason": reason})
    if job_id:
        asyncio.create_task(run_label_recalculation_job(job_id=job_id, label_id=label_id, percentage=percentage))
    return job_id


@rate_change_r.post("/labels/{label_id}/rate-change/request")
async def create_rate_request(label_id: str, body: RateChangeRequestIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "labels.rate.request")
    label = await _get_label(label_id)
    reason = (body.reason or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="Alasan perubahan wajib diisi")
    current = float(label.get("royalty_percentage_default", 60) or 60)
    if float(body.proposed_value) == current:
        raise HTTPException(status_code=400, detail="Nilai usulan sama dengan nilai saat ini")
    existing = await db.label_rate_change_requests.find_one({"label_id": label_id, "status": "pending"}, {"_id": 0, "id": 1})
    if existing:
        raise HTTPException(status_code=409, detail="Sudah ada permintaan perubahan rate/fee yang menunggu persetujuan untuk label ini")
    doc = {
        "id": new_id(), "reference_id": _reference_id(), "label_id": label_id,
        "label_name": label.get("label_name"), "current_value": current,
        "proposed_value": float(body.proposed_value), "reason": reason, "status": "pending",
        "requested_by": user["id"], "requested_by_name": _actor_name(user), "requested_at": now_iso(),
        "decided_by": None, "decided_by_name": None, "decided_at": None, "decision_note": None,
        "applied": False, "recalculation_job_id": None,
    }
    await db.label_rate_change_requests.insert_one(doc)
    doc.pop("_id", None)
    await log_activity(user["id"], "rate_change_request", "label_rate_change", doc["id"], after=doc)
    approvers = await _approver_ids()
    await notify_many(approvers, "rate_change_request", "Permintaan Perubahan Rate/Fee",
                      f"{label.get('label_name')}: {current}% → {body.proposed_value}% menunggu persetujuan.",
                      link="/admin/rate-changes", meta={"request_id": doc["id"], "label_id": label_id})
    return doc


@rate_change_r.get("/rate-changes")
async def list_rate_requests(status: Optional[str] = None, label_id: Optional[str] = None, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "labels.rate.request.view")
    query: Dict[str, Any] = {}
    if status:
        if status not in {"pending", "approved", "rejected"}:
            raise HTTPException(status_code=400, detail="Status tidak valid")
        query["status"] = status
    if label_id:
        query["label_id"] = label_id
    return await db.label_rate_change_requests.find(query, {"_id": 0}).sort("requested_at", -1).to_list(500)


@rate_change_r.post("/rate-changes/{request_id}/decision")
async def decide_rate_request(request_id: str, body: RateChangeDecisionIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "labels.rate.approve")
    req = await db.label_rate_change_requests.find_one({"id": request_id}, {"_id": 0})
    if not req:
        raise HTTPException(status_code=404, detail="Permintaan tidak ditemukan")
    if req.get("status") != "pending":
        raise HTTPException(status_code=409, detail="Permintaan sudah diproses")
    now = now_iso()
    decision: Dict[str, Any] = {
        "decided_by": user["id"], "decided_by_name": _actor_name(user),
        "decided_at": now, "decision_note": (body.note or "").strip() or None,
    }
    if body.action == "reject":
        decision["status"] = "rejected"
        await db.label_rate_change_requests.update_one({"id": request_id}, {"$set": decision})
        await log_activity(user["id"], "rate_change_reject", "label_rate_change", request_id, before=req, after={**req, **decision})
        await notify(req["requested_by"], "rate_change_decided", "Permintaan Rate/Fee Ditolak",
                     f"Permintaan {req.get('reference_id')} untuk {req.get('label_name')} ditolak.",
                     link=f"/admin/labels/{req['label_id']}", meta={"request_id": request_id})
        return {**req, **decision}
    label = await _get_label(req["label_id"])
    job_id = await _apply_rate_change(label=label, percentage=req["proposed_value"], reason=req["reason"], actor=user, source="approved")
    decision.update({"status": "approved", "applied": True, "recalculation_job_id": job_id})
    await db.label_rate_change_requests.update_one({"id": request_id}, {"$set": decision})
    await log_activity(user["id"], "rate_change_approve", "label_rate_change", request_id, before=req, after={**req, **decision})
    await notify(req["requested_by"], "rate_change_decided", "Permintaan Rate/Fee Disetujui",
                 f"Permintaan {req.get('reference_id')} untuk {req.get('label_name')} disetujui: {req['current_value']}% → {req['proposed_value']}%.",
                 link=f"/admin/labels/{req['label_id']}", meta={"request_id": request_id})
    return {**req, **decision, "royalty_recalculation_job_id": job_id}


@rate_change_r.post("/labels/{label_id}/rate-change/direct")
async def direct_rate_change(label_id: str, body: RateChangeRequestIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "labels.rate")
    label = await _get_label(label_id)
    reason = (body.reason or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="Alasan perubahan wajib diisi")
    job_id = await _apply_rate_change(label=label, percentage=body.proposed_value, reason=reason, actor=user, source="direct")
    return {"ok": True, "royalty_recalculation_job_id": job_id, "royalty_percentage_default": float(body.proposed_value)}
