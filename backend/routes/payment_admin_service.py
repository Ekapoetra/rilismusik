"""Admin payment enrichment and manual follow-up workflow."""
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from models import now_iso
from .deps import db


MANUAL_PAYMENT_TYPES = ("pay_per_release", "custom_service", "wami_addon")


async def _related_maps(payments: List[Dict[str, Any]]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    label_ids = {row.get("label_id") for row in payments if row.get("label_id")}
    release_ids = {row.get("release_id") for row in payments if row.get("release_id")}
    service_ids = {row.get("service_order_id") for row in payments if row.get("service_order_id")}
    wami_ids = {row.get("wami_order_id") for row in payments if row.get("wami_order_id")}

    labels = await db.labels.find(
        {"id": {"$in": list(label_ids)}},
        {"_id": 0, "id": 1, "label_name": 1, "email": 1, "user_id": 1},
    ).to_list(len(label_ids) or 1)
    user_ids = {row.get("user_id") for row in labels if row.get("user_id")}
    users = await db.users.find(
        {"id": {"$in": list(user_ids)}}, {"_id": 0, "id": 1, "email": 1},
    ).to_list(len(user_ids) or 1)
    releases = await db.releases.find(
        {"id": {"$in": list(release_ids)}},
        {"_id": 0, "id": 1, "release_title": 1, "status": 1},
    ).to_list(len(release_ids) or 1)
    services = await db.service_orders.find(
        {"id": {"$in": list(service_ids)}},
        {"_id": 0, "id": 1, "name": 1, "status": 1},
    ).to_list(len(service_ids) or 1)
    wami = await db.wami_orders.find(
        {"id": {"$in": list(wami_ids)}},
        {"_id": 0, "id": 1, "track_title": 1, "status": 1},
    ).to_list(len(wami_ids) or 1)
    user_map = {row["id"]: row for row in users}
    for label in labels:
        label["resolved_email"] = label.get("email") or (user_map.get(label.get("user_id")) or {}).get("email")
    return {
        "labels": {row["id"]: row for row in labels},
        "releases": {row["id"]: row for row in releases},
        "services": {row["id"]: row for row in services},
        "wami": {row["id"]: row for row in wami},
    }


def _decorate(payment: Dict[str, Any], maps: Dict[str, Dict[str, Dict[str, Any]]]) -> Dict[str, Any]:
    row = {key: value for key, value in payment.items() if key != "_id"}
    row.setdefault("payment_method", None)
    label = maps["labels"].get(row.get("label_id"), {})
    release = maps["releases"].get(row.get("release_id"), {})
    service = maps["services"].get(row.get("service_order_id"), {})
    wami = maps["wami"].get(row.get("wami_order_id"), {})
    row.update({
        "label_name": label.get("label_name") or "Label tidak ditemukan",
        "label_email": label.get("resolved_email"),
        "release_title": release.get("release_title"),
        "release_status": release.get("status"),
        "service_name": service.get("name"),
        "service_status": service.get("status"),
        "wami_track_title": wami.get("track_title"),
        "wami_status": wami.get("status"),
        "admin_action_required": False,
        "admin_action_type": "automatic",
        "admin_action_status": "automatic",
        "admin_action_path": None,
    })
    if row.get("status") != "paid":
        return row
    if row.get("type") == "pay_per_release":
        row["admin_action_type"] = "release"
        row["admin_action_status"] = release.get("status") or "unknown"
        row["admin_action_required"] = release.get("status") in {"under_review", "approved"}
        row["admin_action_path"] = f"/admin/releases/{row['release_id']}" if row.get("release_id") else None
    elif row.get("type") == "custom_service":
        row["admin_action_type"] = "custom_service"
        row["admin_action_status"] = service.get("status") or "paid"
        row["admin_action_required"] = row["admin_action_status"] in {"paid", "in_progress"}
    elif row.get("type") == "wami_addon":
        row["admin_action_type"] = "wami"
        row["admin_action_status"] = wami.get("status") or "pending"
        row["admin_action_required"] = row["admin_action_status"] in {"pending", "in_progress"}
        row["admin_action_path"] = "/admin/wami"
    return row


async def list_admin_payments(
    *, status: Optional[str] = None, payment_type: Optional[str] = None,
    needs_action: bool = False, limit: int = 1000,
) -> List[Dict[str, Any]]:
    query: Dict[str, Any] = {}
    if status:
        query["status"] = status
    if payment_type:
        query["type"] = payment_type
    if needs_action:
        query.update({"status": "paid", "type": {"$in": list(MANUAL_PAYMENT_TYPES)}})
    payments = await db.payments.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    maps = await _related_maps(payments)
    rows = [_decorate(payment, maps) for payment in payments]
    return [row for row in rows if row["admin_action_required"]] if needs_action else rows


async def count_actionable_payments() -> int:
    rows = await list_admin_payments(needs_action=True, limit=10_000)
    return len(rows)


async def update_custom_service_action(payment_id: str, action: str) -> Dict[str, Any]:
    payment = await db.payments.find_one({"id": payment_id}, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Pembayaran tidak ditemukan")
    if payment.get("status") != "paid" or payment.get("type") != "custom_service":
        raise HTTPException(status_code=400, detail="Aksi ini hanya untuk layanan tambahan yang sudah dibayar")
    order = await db.service_orders.find_one({"id": payment.get("service_order_id")}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Pesanan layanan tidak ditemukan")
    current = order.get("status") or "paid"
    if current == "completed":
        raise HTTPException(status_code=409, detail="Layanan ini sudah selesai")
    if action == "in_progress" and current not in {"paid", "in_progress"}:
        raise HTTPException(status_code=409, detail="Status layanan tidak dapat diubah")
    now = now_iso()
    await db.service_orders.update_one(
        {"id": order["id"]},
        {"$set": {"status": action, "updated_at": now, f"{action}_at": now}},
    )
    await db.payments.update_one(
        {"id": payment_id}, {"$set": {"admin_action_status": action, "admin_action_updated_at": now}},
    )
    updated = await db.payments.find_one({"id": payment_id}, {"_id": 0})
    maps = await _related_maps([updated])
    return _decorate(updated, maps)