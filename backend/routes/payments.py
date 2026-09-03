"""Production Xendit payments using Payment Sessions + backend polling."""
import os
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from .deps import (
    ADMIN_ROLES, LABEL_ROLE, db, get_current_user, get_label_by_user,
    require_kyc_for_label_user,
    require_admin, require_label, log_activity, admin_user_ids, notify_many,
)
from models import (
    CreateSubscriptionPaymentIn, CreateWamiOrderIn, PaymentProductCreateIn,
    PaymentProductUpdateIn, PaymentAdminActionIn, now_iso, new_id,
)
from .payment_admin_service import update_custom_service_action
from payment_service import (
    PaymentCreateData, create_payment_document, create_xendit_session, fulfill_payment,
    payment_price, poll_payment, reconcile_payment, xendit_configured,
)


pay_r = APIRouter(prefix="/payments", tags=["payments"])


async def _owned_payment(payment_id: str, user: dict) -> Dict[str, Any]:
    payment = await db.payments.find_one({"id": payment_id}, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Invoice tidak ditemukan")
    if user["role"] == LABEL_ROLE:
        label = await get_label_by_user(user)
        if payment["label_id"] != label["id"]:
            raise HTTPException(status_code=404, detail="Invoice tidak ditemukan")
    elif user["role"] not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Tidak diperbolehkan")
    return payment


@pay_r.get("/config")
async def payment_config(user: dict = Depends(get_current_user)):
    return {"provider": "xendit", "mode": "production_polling", "configured": xendit_configured(), "webhook_required": False}


@pay_r.post("/subscription")
async def create_subscription_invoice(body: CreateSubscriptionPaymentIn, user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    tier = body.tier or "annual_vip"
    existing = await db.payments.find_one({
        "label_id": label["id"], "type": "annual_subscription", "tier": tier, "status": "pending",
    }, {"_id": 0})
    if existing:
        return existing
    amount = await payment_price(tier)
    return await create_payment_document(PaymentCreateData(
        label_id=label["id"], payment_type="annual_subscription", amount=amount,
        tier=tier, description=f"Paket {tier.replace('_', ' ').title()} 1 Tahun",
        return_path="/label/invoices",
    ))


@pay_r.post("/wami")
async def create_wami_invoice(body: CreateWamiOrderIn, user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    track = await db.tracks.find_one({"id": body.track_id}, {"_id": 0})
    if not track:
        raise HTTPException(status_code=404, detail="Track tidak ditemukan")
    release = await db.releases.find_one({"id": track.get("release_id")}, {"_id": 0})
    if not release or release.get("label_id") != label["id"]:
        raise HTTPException(status_code=403, detail="Track ini bukan milik Anda")
    if release.get("status") != "live":
        raise HTTPException(status_code=400, detail="Pendaftaran WAMI hanya dapat dilakukan setelah rilisan LIVE")
    existing_order = await db.wami_orders.find_one(
        {"track_id": body.track_id, "status": {"$nin": ["cancelled", "rejected"]}}, {"_id": 0},
    )
    if existing_order:
        if existing_order.get("status") == "unpaid":
            existing_invoice = await db.payments.find_one(
                {"wami_order_id": existing_order["id"], "status": {"$ne": "paid"}}, {"_id": 0},
                sort=[("created_at", -1)],
            )
            if existing_invoice:
                return {"order": existing_order, "invoice": existing_invoice, "free_vip": False}
        raise HTTPException(status_code=400, detail="Track ini sudah memiliki pendaftaran WAMI aktif")

    vip_expiry_ok = False
    if label.get("subscription_expires_at"):
        try:
            vip_expiry_ok = datetime.fromisoformat(str(label["subscription_expires_at"]).replace("Z", "+00:00")) > datetime.now(timezone.utc)
        except Exception:
            vip_expiry_ok = False
    is_vip = label.get("payment_type") == "annual_subscription" and label.get("subscription_tier") == "annual_vip" and label.get("subscription_status") == "active" and vip_expiry_ok
    order_id = new_id()
    amount = 0 if is_vip else await payment_price("wami_addon")
    order = {
        "id": order_id, "label_id": label["id"], "release_id": release["id"],
        "release_title": release.get("release_title"), "track_id": body.track_id,
        "track_title": track.get("track_title"), "isrc": track.get("isrc"),
        "is_free_vip": is_vip, "amount_idr": amount,
        "status": "pending" if is_vip else "unpaid", "wami_reference": None,
        "admin_note": None, "paid_at": now_iso() if is_vip else None,
        "registered_at": None, "created_at": now_iso(), "updated_at": now_iso(),
    }
    await db.wami_orders.insert_one(order)
    order.pop("_id", None)
    if is_vip:
        await notify_many(
            await admin_user_ids(("super_admin", "admin_release")), "wami_new",
            "WAMI baru (VIP — gratis)",
            f"{label.get('label_name')} mengajukan WAMI untuk '{track.get('track_title')}'.",
            "/admin/wami", {"wami_order_id": order_id},
        )
        return {"order": order, "invoice": None, "free_vip": True}

    invoice = await create_payment_document(PaymentCreateData(
        label_id=label["id"], payment_type="wami_addon", amount=amount,
        release_id=release["id"], track_id=body.track_id, wami_order_id=order_id,
        description=f"Pendaftaran WAMI — {track.get('track_title')}",
        return_path="/label/wami",
    ))
    await db.wami_orders.update_one({"id": order_id}, {"$set": {"payment_id": invoice["id"], "updated_at": now_iso()}})
    order["payment_id"] = invoice["id"]
    return {"order": order, "invoice": invoice, "free_vip": False}


@pay_r.get("/products")
async def list_payment_products(user: dict = Depends(require_label)):
    return await db.payment_products.find({"active": True}, {"_id": 0}).sort("created_at", -1).to_list(200)


@pay_r.post("/service/{product_id}")
async def create_service_invoice(product_id: str, user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    product = await db.payment_products.find_one({"id": product_id, "active": True}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Layanan tidak tersedia")
    order_id = new_id()
    await db.service_orders.insert_one({
        "id": order_id, "product_id": product_id, "label_id": label["id"],
        "name": product["name"], "amount": int(product["amount"]), "status": "unpaid",
        "created_at": now_iso(), "updated_at": now_iso(),
    })
    return await create_payment_document(PaymentCreateData(
        label_id=label["id"], payment_type="custom_service", amount=int(product["amount"]),
        product_id=product_id, service_order_id=order_id, description=product["name"],
        return_path="/label/invoices",
    ))


@pay_r.get("/admin/products")
async def admin_list_products(user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    return await db.payment_products.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)


@pay_r.post("/admin/products")
async def admin_create_product(body: PaymentProductCreateIn, user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    document = {
        "id": new_id(), "name": body.name.strip(), "description": (body.description or "").strip(),
        "amount": int(body.amount), "active": body.active, "created_by": user["id"],
        "created_at": now_iso(), "updated_at": now_iso(),
    }
    await db.payment_products.insert_one(document)
    document.pop("_id", None)
    return document


@pay_r.patch("/admin/products/{product_id}")
async def admin_update_product(product_id: str, body: PaymentProductUpdateIn, user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    update = {key: value for key, value in body.model_dump(exclude_none=True).items()}
    if "name" in update:
        update["name"] = update["name"].strip()
    update["updated_at"] = now_iso()
    result = await db.payment_products.update_one({"id": product_id}, {"$set": update})
    if not result.matched_count:
        raise HTTPException(status_code=404, detail="Layanan tidak ditemukan")
    return await db.payment_products.find_one({"id": product_id}, {"_id": 0})


@pay_r.delete("/admin/products/{product_id}")
async def admin_delete_product(product_id: str, user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    product = await db.payment_products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Layanan tidak ditemukan")
    used = await db.payments.count_documents({"addon_product_ids": product_id})
    if used:
        await db.payment_products.update_one({"id": product_id}, {"$set": {"active": False, "archived_at": now_iso(), "updated_at": now_iso()}})
        return {"ok": True, "archived": True}
    await db.payment_products.delete_one({"id": product_id})
    return {"ok": True, "deleted": True}


@pay_r.post("/admin/{payment_id}/action")
async def admin_payment_action(
    payment_id: str, body: PaymentAdminActionIn, user: dict = Depends(require_admin),
):
    if user["role"] not in ("super_admin", "admin_finance", "admin_support"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance, Support, atau Super Admin")
    payment = await update_custom_service_action(payment_id, body.action)
    await log_activity(
        user["id"], f"payment_service_{body.action}", "payment", payment_id,
        after={"admin_action_status": body.action},
    )
    return payment


@pay_r.post("/{payment_id}/checkout")
async def start_checkout(payment_id: str, user: dict = Depends(require_kyc_for_label_user)):
    payment = await _owned_payment(payment_id, user)
    session = await create_xendit_session(payment)
    await log_activity(user["id"], "xendit_checkout", "payment", payment_id)
    return {
        "payment_id": payment_id, "status": session["status"],
        "payment_url": session["xendit_invoice_url"],
        "expires_at": session.get("expired_at"),
    }


@pay_r.get("/{payment_id}/status")
async def payment_status(payment_id: str, user: dict = Depends(require_kyc_for_label_user)):
    payment = await _owned_payment(payment_id, user)
    payment = await poll_payment(payment)
    return {
        "payment_id": payment["id"], "status": payment["status"],
        "provider_status": payment.get("provider_status"),
        "fulfillment_status": payment.get("fulfillment_status"),
        "paid_at": payment.get("paid_at"),
    }


@pay_r.post("/{payment_id}/mock-pay")
async def mock_pay(payment_id: str, user: dict = Depends(require_kyc_for_label_user)):
    if os.environ.get("XENDIT_ALLOW_MOCK_PAY", "false").lower() != "true":
        raise HTTPException(status_code=404, detail="Endpoint tidak tersedia")
    payment = await _owned_payment(payment_id, user)
    await db.payments.update_one({"id": payment_id}, {"$set": {"status": "paid", "provider_status": "COMPLETED", "paid_at": now_iso()}})
    return {"ok": True, "invoice": await fulfill_payment(await db.payments.find_one({"id": payment_id}, {"_id": 0}))}


@pay_r.post("/webhook/xendit")
async def xendit_webhook(payload: Dict[str, Any], request: Request):
    """Optional compatibility path; production confirmation defaults to polling."""
    if os.environ.get("XENDIT_WEBHOOK_ENABLED", "false").lower() != "true":
        raise HTTPException(status_code=410, detail="Webhook dinonaktifkan; status dikonfirmasi melalui polling")
    expected = os.environ.get("XENDIT_WEBHOOK_VERIFICATION_TOKEN", "")
    provided = request.headers.get("x-callback-token", "")
    if not expected or not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Invalid callback token")
    session_id = payload.get("payment_session_id") or payload.get("id")
    payment = await db.payments.find_one({"xendit_session_id": session_id}, {"_id": 0})
    if not payment:
        return {"ok": True, "ignored": True}
    await reconcile_payment(payment, payload)
    return {"ok": True}