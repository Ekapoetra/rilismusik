"""Paid add-on order tracking (visualizer, link preset, etc.).

Add-ons purchased while submitting a release are line items on the release payment
but previously had no processable task. This module turns each paid add-on into a
trackable order with a status lifecycle so both admin and label can follow it.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from models import new_id, now_iso
from .deps import (
    db, require_admin, require_label, get_label_by_user,
    log_activity, notify_many, label_user_ids,
)
from .admin_permission_service import assert_admin_permission
import asyncio
from email_service import send_addon_status_email


async def _email_addon(order: Dict[str, Any], status: str, delivery_url: Optional[str] = None,
                       delivery_note: Optional[str] = None):
    """Best-effort email to the label when an add-on is processed/available."""
    if status not in ("in_progress", "delivered", "completed"):
        return
    label = await db.labels.find_one({"id": order["label_id"]}, {"_id": 0, "email": 1, "label_name": 1})
    if label and label.get("email"):
        asyncio.create_task(send_addon_status_email(
            to=label["email"], label_name=label.get("label_name") or "Label",
            product_name=order.get("product_name") or "Layanan Tambahan",
            release_title=order.get("release_title"), release_id=order.get("release_id"),
            status=status, delivery_url=delivery_url or order.get("delivery_url"),
            delivery_note=delivery_note or order.get("delivery_note"),
        ))

addon_admin_r = APIRouter(prefix="/admin/addon-orders", tags=["addon-orders"])
addon_label_r = APIRouter(prefix="/label/addon-orders", tags=["addon-orders"])

STATUS_FLOW = ["pending", "in_progress", "delivered", "completed"]
OPEN_STATUSES = ["pending", "in_progress"]
TERMINAL = {"completed", "cancelled"}
STATUS_LABELS = {
    "pending": "Menunggu", "in_progress": "Diproses",
    "delivered": "Terkirim", "completed": "Selesai", "cancelled": "Dibatalkan",
}


def _public(order: Dict[str, Any]) -> Dict[str, Any]:
    row = {k: v for k, v in order.items() if k != "_id"}
    row["status_label"] = STATUS_LABELS.get(row.get("status"), row.get("status"))
    return row


async def sync_release_addon_orders(release: Dict[str, Any], payment: Dict[str, Any]) -> int:
    """Create one addon_order per paid add-on on a release. Idempotent per (release, product)."""
    addons = release.get("selected_addons") or []
    if not addons:
        return 0
    # Resolve per-product delivery type (link vs file) from the catalog.
    product_ids = [item.get("id") for item in addons if item.get("id")]
    dtype_map = {}
    if product_ids:
        async for p in db.payment_products.find({"id": {"$in": product_ids}}, {"_id": 0, "id": 1, "delivery_type": 1}):
            dtype_map[p["id"]] = p.get("delivery_type") or "link"
    created = 0
    now = now_iso()
    for item in addons:
        product_id = item.get("id")
        if not product_id:
            continue
        dedupe = f"{release['id']}:{product_id}"
        result = await db.addon_orders.update_one(
            {"dedupe_key": dedupe},
            {"$setOnInsert": {
                "id": new_id(), "dedupe_key": dedupe,
                "label_id": release.get("label_id"), "label_name": release.get("label_name"),
                "release_id": release.get("id"), "release_title": release.get("release_title"),
                "product_id": product_id,
                "product_name": item.get("name") or "Layanan Tambahan",
                "product_description": item.get("description") or "",
                "delivery_type": dtype_map.get(product_id, "link"),
                "amount": int(item.get("amount") or 0),
                "payment_id": payment.get("id"),
                "source": "release",
                "status": "pending",
                "delivery_url": None, "delivery_note": None, "delivery_filename": None,
                "created_at": now, "updated_at": now,
            }},
            upsert=True,
        )
        if result.upserted_id is not None:
            created += 1
    return created


async def sync_free_addon_orders(release: Dict[str, Any], benefit_source: str) -> int:
    """Create one FREE (Rp0) addon_order per selected add-on for subscription/Multi Label
    accounts. Idempotent per (release, product). Order still enters the processing queue."""
    addons = release.get("selected_addons") or []
    if not addons:
        return 0
    product_ids = [item.get("id") for item in addons if item.get("id")]
    dtype_map = {}
    if product_ids:
        async for p in db.payment_products.find({"id": {"$in": product_ids}}, {"_id": 0, "id": 1, "delivery_type": 1}):
            dtype_map[p["id"]] = p.get("delivery_type") or "link"
    created = 0
    now = now_iso()
    for item in addons:
        product_id = item.get("id")
        if not product_id:
            continue
        dedupe = f"{release['id']}:{product_id}"
        result = await db.addon_orders.update_one(
            {"dedupe_key": dedupe},
            {"$setOnInsert": {
                "id": new_id(), "dedupe_key": dedupe,
                "label_id": release.get("label_id"), "label_name": release.get("label_name"),
                "release_id": release.get("id"), "release_title": release.get("release_title"),
                "product_id": product_id,
                "product_name": item.get("name") or "Layanan Tambahan",
                "product_description": item.get("description") or "",
                "delivery_type": dtype_map.get(product_id, "link"),
                "amount": 0, "benefit_source": benefit_source,
                "payment_id": None,
                "source": "subscription_free",
                "status": "pending",
                "delivery_url": None, "delivery_note": None, "delivery_filename": None,
                "created_at": now, "updated_at": now,
            }},
            upsert=True,
        )
        if result.upserted_id is not None:
            created += 1
    return created


async def backfill_addon_orders() -> Dict[str, int]:
    """Create missing addon_orders from already-paid release payments."""
    """Create missing addon_orders from already-paid release payments."""
    scanned = 0
    created = 0
    cursor = db.payments.find(
        {"type": "pay_per_release", "status": "paid", "addon_product_ids": {"$exists": True, "$ne": []}},
        {"_id": 0},
    )
    async for payment in cursor:
        scanned += 1
        release = await db.releases.find_one({"id": payment.get("release_id")}, {"_id": 0})
        if not release:
            continue
        created += await sync_release_addon_orders(release, payment)
    return {"scanned_payments": scanned, "orders_created": created}


# ---------------- Admin ----------------
class AddonStatusIn(BaseModel):
    status: str


class AddonDeliveryIn(BaseModel):
    delivery_url: Optional[str] = Field(default=None, max_length=2000)
    delivery_note: Optional[str] = Field(default=None, max_length=2000)


def _safe_url(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    if not (value.startswith("http://") or value.startswith("https://")):
        raise HTTPException(status_code=400, detail="Tautan hasil harus diawali http:// atau https://")
    return value


@addon_admin_r.get("")
async def admin_list_addon_orders(status: Optional[str] = None, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "addon.view")
    query: Dict[str, Any] = {}
    if status and status != "all":
        query["status"] = status
    orders = await db.addon_orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(2000)
    counts: Dict[str, int] = {s: 0 for s in list(STATUS_LABELS)}
    async for row in db.addon_orders.aggregate([{"$group": {"_id": "$status", "n": {"$sum": 1}}}]):
        counts[row["_id"]] = row["n"]
    return {"items": [_public(o) for o in orders], "counts": counts, "flow": STATUS_FLOW, "labels": STATUS_LABELS}


@addon_admin_r.patch("/{order_id}/status")
async def admin_update_status(order_id: str, body: AddonStatusIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "addon.manage")
    if body.status not in STATUS_LABELS:
        raise HTTPException(status_code=400, detail="Status tidak valid")
    order = await db.addon_orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order add-on tidak ditemukan")
    current = order.get("status")
    if current in TERMINAL:
        raise HTTPException(status_code=409, detail=f"Order sudah {STATUS_LABELS.get(current)}")
    new_status = body.status
    if new_status != "cancelled":
        if new_status not in STATUS_FLOW:
            raise HTTPException(status_code=400, detail="Status tidak valid")
        if STATUS_FLOW.index(new_status) < STATUS_FLOW.index(current if current in STATUS_FLOW else "pending"):
            raise HTTPException(status_code=409, detail="Status tidak dapat mundur")
    now = now_iso()
    await db.addon_orders.update_one({"id": order_id}, {"$set": {
        "status": new_status, "updated_at": now, f"{new_status}_at": now,
    }})
    await log_activity(user["id"], "addon_order_status", "addon", order_id,
                       before={"status": current}, after={"status": new_status})
    if new_status in ("delivered", "completed"):
        await notify_many(
            await label_user_ids(order["label_id"]), "addon_order_update",
            f"Layanan tambahan: {STATUS_LABELS[new_status]}",
            f"{order.get('product_name')} untuk rilisan \"{order.get('release_title')}\" berstatus {STATUS_LABELS[new_status]}.",
            link=f"/label/releases/{order.get('release_id')}" if order.get("release_id") else "/label/dashboard",
        )
    await _email_addon(order, new_status)
    return _public(await db.addon_orders.find_one({"id": order_id}, {"_id": 0}))


@addon_admin_r.patch("/{order_id}/delivery")
async def admin_set_delivery(order_id: str, body: AddonDeliveryIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "addon.manage")
    order = await db.addon_orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order add-on tidak ditemukan")
    if order.get("status") == "cancelled":
        raise HTTPException(status_code=409, detail="Order sudah dibatalkan")
    url = _safe_url(body.delivery_url)
    note = (body.delivery_note or "").strip() or None
    now = now_iso()
    update: Dict[str, Any] = {"delivery_url": url, "delivery_note": note, "updated_at": now}
    # Attaching a result auto-advances to Terkirim if still in an earlier stage.
    if url and order.get("status") in ("pending", "in_progress"):
        update["status"] = "delivered"
        update["delivered_at"] = now
    await db.addon_orders.update_one({"id": order_id}, {"$set": update})
    await log_activity(user["id"], "addon_order_delivery", "addon", order_id,
                       before={"delivery_url": order.get("delivery_url")}, after={"delivery_url": url})
    if update.get("status") == "delivered":
        await notify_many(
            await label_user_ids(order["label_id"]), "addon_order_update",
            "Layanan tambahan: Terkirim",
            f"Hasil {order.get('product_name')} untuk rilisan \"{order.get('release_title')}\" sudah tersedia.",
            link=f"/label/releases/{order.get('release_id')}" if order.get("release_id") else "/label/dashboard",
        )
        await _email_addon(order, "delivered", delivery_url=url, delivery_note=note)
    return _public(await db.addon_orders.find_one({"id": order_id}, {"_id": 0}))


@addon_admin_r.post("/{order_id}/delivery-file")
async def admin_upload_delivery_file(order_id: str, file: UploadFile = File(...), user: dict = Depends(require_admin)):
    assert_admin_permission(user, "addon.manage")
    order = await db.addon_orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order add-on tidak ditemukan")
    if order.get("status") == "cancelled":
        raise HTTPException(status_code=409, detail="Order sudah dibatalkan")
    filename = (file.filename or "").strip()
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    allowed = {"mp4", "mov", "webm", "zip", "rar", "png", "jpg", "jpeg", "pdf", "mp3", "wav", "gif"}
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Format file tidak didukung: .{ext or '?'}")
    import storage_service
    key = f"addon-delivery/{order_id}.{ext}"
    content_type = file.content_type or "application/octet-stream"
    await storage_service.upload_fileobj(key=key, fileobj=file.file, content_type=content_type)
    now = now_iso()
    await db.addon_orders.update_one({"id": order_id}, {"$set": {
        "delivery_url": f"/api/files/{key}", "delivery_filename": filename,
        "status": "delivered", "delivered_at": now, "updated_at": now,
    }})
    await log_activity(user["id"], "addon_order_delivery_file", "addon", order_id, after={"filename": filename})
    await notify_many(
        await label_user_ids(order["label_id"]), "addon_order_update",
        "Layanan tambahan: Terkirim",
        f"Hasil {order.get('product_name')} untuk rilisan \"{order.get('release_title')}\" sudah tersedia untuk diunduh.",
        link=f"/label/releases/{order.get('release_id')}" if order.get("release_id") else "/label/dashboard",
    )
    await _email_addon(order, "delivered", delivery_url=f"/api/files/{key}")
    return _public(await db.addon_orders.find_one({"id": order_id}, {"_id": 0}))


@addon_admin_r.post("/backfill")
async def admin_backfill(user: dict = Depends(require_admin)):
    assert_admin_permission(user, "addon.manage")
    result = await backfill_addon_orders()
    await log_activity(user["id"], "addon_order_backfill", "addon", None, after=result)
    return result


# ---------------- Label ----------------
@addon_label_r.get("")
async def label_list_addon_orders(release_id: Optional[str] = None, user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    query: Dict[str, Any] = {"label_id": label["id"]}
    if release_id:
        query["release_id"] = release_id
    orders = await db.addon_orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return {"items": [_public(o) for o in orders], "labels": STATUS_LABELS}
