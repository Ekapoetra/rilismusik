"""Admin-only royalty adjustments using the existing royalty.manage permission."""
import re
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from .deps import db, require_admin, assert_admin_permission
from .royalty_adjustment_models import (
    AdjustmentInput, AdjustmentCommit, AdjustmentVoid, AdjustmentHistory,
    AdjustmentRecord, AdjustmentPreview, AdjustmentResult,
)
from .royalty_adjustment_service import source_summary, preview_adjustment
from .royalty_adjustment_mutations import commit_adjustment, void_adjustment
from .royalty_adjustment_balance import ADJUSTMENT_TYPE

adjustment_r = APIRouter(prefix="/royalty/admin/adjustments", tags=["royalty-adjustments"])


async def royalty_manager(user: dict = Depends(require_admin)):
    assert_admin_permission(user, "royalty.manage")
    return user


class SourceSummary(BaseModel):
    label_id: str
    label_name: str
    legacy_period_to: str | None
    believe_legacy_idr: int | None
    new_royalty_idr: int | None
    unclassified_csv_idr: int
    admin_adjustment_idr: int
    withdraw_reserved_idr: int
    balance_available_idr: int
    has_active_withdraw: bool
    legacy_needs_review: bool


class LabelOption(BaseModel):
    id: str
    label_name: str


@adjustment_r.get("/labels", response_model=list[LabelOption])
async def label_options(q: str = Query("", max_length=120), user: dict = Depends(royalty_manager)):
    query = {"label_name": {"$regex": re.escape(q.strip()), "$options": "i"}} if q.strip() else {}
    items = await db.labels.find(query, {"_id": 0, "id": 1, "label_name": 1}).sort("label_name", 1).limit(30).to_list(30)
    return [LabelOption(id=item["id"], label_name=item.get("label_name") or item["id"]) for item in items]


@adjustment_r.get("/labels/{label_id}/summary", response_model=SourceSummary)
async def summary(label_id: str, legacy_period_to: str | None = Query(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"), user: dict = Depends(royalty_manager)):
    result, _ = await source_summary(label_id, legacy_period_to)
    return SourceSummary(**result)


@adjustment_r.post("/labels/{label_id}/preview", response_model=AdjustmentPreview)
async def preview(label_id: str, body: AdjustmentInput, user: dict = Depends(royalty_manager)):
    return await preview_adjustment(label_id, body, user)


@adjustment_r.post("/labels/{label_id}", response_model=AdjustmentResult)
async def create(label_id: str, body: AdjustmentCommit, user: dict = Depends(royalty_manager)):
    return await commit_adjustment(label_id, body.preview_id, user)


@adjustment_r.post("/labels/{label_id}/{adjustment_id}/void", response_model=AdjustmentResult)
async def void(label_id: str, adjustment_id: str, body: AdjustmentVoid, user: dict = Depends(royalty_manager)):
    return await void_adjustment(label_id, adjustment_id, body.reason, user)


@adjustment_r.get("/labels/{label_id}", response_model=AdjustmentHistory)
async def history(label_id: str, q: str = Query("", max_length=120), status: str | None = Query(None, pattern="^(active|voided)$"), page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100), user: dict = Depends(royalty_manager)):
    if not await db.labels.find_one({"id": label_id}, {"_id": 0, "id": 1}):
        raise HTTPException(404, "Label tidak ditemukan")
    query = {"label_id": label_id, "type": ADJUSTMENT_TYPE}
    if status:
        query["status"] = status
    if q.strip():
        query["$or"] = [{field: {"$regex": re.escape(q.strip()), "$options": "i"}} for field in ("id", "reason", "reference", "created_by_name")]
    total = await db.balance_transactions.count_documents(query)
    items = await db.balance_transactions.find(query, {"_id": 0}).sort("created_at", -1).skip((page - 1) * limit).limit(limit).to_list(limit)
    ids = [item["id"] for item in items]
    allocations = {}
    async for withdrawal in db.withdraw_requests.find({"label_id": label_id, "adjustment_ids": {"$in": ids}, "status": {"$in": ["requested", "approved", "paid"]}}, {"_id": 0, "id": 1, "status": 1, "adjustment_ids": 1}):
        for adjustment_id in withdrawal.get("adjustment_ids") or []:
            allocations[adjustment_id] = withdrawal
    active = await db.withdraw_requests.find_one({"label_id": label_id, "status": {"$in": ["requested", "approved"]}, "legacy_import": {"$ne": True}}, {"_id": 0, "id": 1})
    for item in items:
        allocation = allocations.get(item["id"], {})
        item.update(withdrawal_id=allocation.get("id"), withdrawal_status=allocation.get("status"), can_void=item["status"] == "active" and not allocation and not active)
    return AdjustmentHistory(items=[AdjustmentRecord(**item) for item in items], total=total, page=page, limit=limit)