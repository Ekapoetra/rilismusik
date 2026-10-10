"""Production Xendit payments using Payment Sessions + backend polling."""
import os
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

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
from .admin_permission_service import assert_admin_permission
from payment_service import (
    PaymentCreateData, create_payment_document, create_xendit_session, fulfill_payment,
    payment_price, poll_payment, reconcile_payment, xendit_configured,
)


pay_r = APIRouter(prefix="/payments", tags=["payments"])


class TokenPurchaseIn(BaseModel):
    quantity: int = Field(ge=1, le=500)


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


@pay_r.post("/token-purchase")
async def create_token_purchase_invoice(body: TokenPurchaseIn, user: dict = Depends(require_label)):
    """D1: buy tokens with rupiah via the normal Xendit flow. Fulfillment
    credits the purchased-token balance (see token_service.fulfill_purchase)."""
    label = await get_label_by_user(user)
    from token_service import get_token_config
    cfg = await get_token_config()
    unit = int(cfg["token_price_idr"])
    amount = int(body.quantity) * unit
    return await create_payment_document(PaymentCreateData(
        label_id=label["id"], payment_type="token_purchase", amount=amount,
        token_quantity=int(body.quantity),
        description=f"Pembelian {body.quantity} Token Rilis Musik",
        return_path="/label/wallet",
        line_items=[{
            "reference_id": "token-purchase", "name": "Token Rilis Musik",
            "description": f"{body.quantity} token × Rp {unit:,.0f}",
            "amount": amount, "quantity": int(body.quantity),
        }],
        base_amount=amount, addon_amount=0,
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
    # Free WAMI is an account-level benefit (VIP and Multi Label). Resolve via the
    # central entitlement resolver so Multi Label is never wrongly billed.
    from .deps import account_entitlements
    ent = await account_entitlements(user)
    is_vip = bool(ent.get("free_wami"))
    benefit_source = ent.get("package") if is_vip else None
    order_id = new_id()
    amount = 0 if is_vip else await payment_price("wami_addon")
    order = {
        "id": order_id, "label_id": label["id"], "release_id": release["id"],
        "release_title": release.get("release_title"), "track_id": body.track_id,
        "track_title": track.get("track_title"), "isrc": track.get("isrc"),
        "is_free_vip": is_vip, "benefit_source": benefit_source, "amount_idr": amount,
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
    assert_admin_permission(user, "addon.view")
    return await db.payment_products.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)


@pay_r.post("/admin/products")
async def admin_create_product(body: PaymentProductCreateIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "addon.manage")
    document = {
        "id": new_id(), "name": body.name.strip(), "description": (body.description or "").strip(),
        "amount": int(body.amount), "active": body.active,
        "delivery_type": body.delivery_type if body.delivery_type in ("link", "file") else "link",
        "created_by": user["id"],
        "created_at": now_iso(), "updated_at": now_iso(),
    }
    await db.payment_products.insert_one(document)
    document.pop("_id", None)
    return document


@pay_r.patch("/admin/products/{product_id}")
async def admin_update_product(product_id: str, body: PaymentProductUpdateIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "addon.manage")
    update = {key: value for key, value in body.model_dump(exclude_none=True).items()}
    if "name" in update:
        update["name"] = update["name"].strip()
    if "delivery_type" in update and update["delivery_type"] not in ("link", "file"):
        raise HTTPException(status_code=400, detail="Tipe pengiriman tidak valid")
    update["updated_at"] = now_iso()
    result = await db.payment_products.update_one({"id": product_id}, {"$set": update})
    if not result.matched_count:
        raise HTTPException(status_code=404, detail="Layanan tidak ditemukan")
    return await db.payment_products.find_one({"id": product_id}, {"_id": 0})


@pay_r.delete("/admin/products/{product_id}")
async def admin_delete_product(product_id: str, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "addon.manage")
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
    assert_admin_permission(user, "payments.manage")
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


@pay_r.get("/{payment_id}/token-quote")
async def token_quote(payment_id: str, user: dict = Depends(require_label)):
    """How many tokens this pending invoice costs — only when cheaper than
    rupiah (auto-hide rule)."""
    payment = await _owned_payment(payment_id, user)
    if payment.get("status") != "pending":
        return {"offered": False, "tokens": 0}
    from token_service import get_token_config, token_quote_for_payment, wallet_state
    cfg = await get_token_config()
    offer = await token_quote_for_payment(payment, cfg)
    label = await get_label_by_user(user)
    state = wallet_state(label, cfg)
    available = state["token_balance"] + state["daily"]["remaining"]
    return {**offer, "available_tokens": available,
            "affordable": bool(offer.get("offered") and available >= offer["tokens"])}


@pay_r.post("/{payment_id}/pay-with-token")
async def pay_with_token(payment_id: str, user: dict = Depends(require_label)):
    """Settle a pending invoice with tokens instead of rupiah. Rupiah stays
    the default rail — this is the optional cheaper path."""
    payment = await _owned_payment(payment_id, user)
    if payment.get("status") != "pending":
        raise HTTPException(status_code=409, detail="Invoice tidak dalam status menunggu pembayaran")
    from token_service import (
        get_token_config, spend_tokens, refund_tokens, token_quote_for_payment,
    )
    cfg = await get_token_config()
    offer = await token_quote_for_payment(payment, cfg)
    if not offer.get("offered"):
        raise HTTPException(status_code=400, detail="Pembayaran token tidak tersedia untuk layanan ini")
    label = await get_label_by_user(user)
    parts = await spend_tokens(
        label["id"], offer["tokens"], "payment", payment_id,
        f"Pembayaran {payment.get('description') or payment['type']}",
        cfg=cfg,
    )
    await db.payments.update_one({"id": payment_id}, {"$set": {
        "status": "paid", "provider": "token", "provider_status": "PAID",
        "payment_method": "token_balance", "token_cost": offer["tokens"],
        "token_parts": parts, "paid_at": now_iso(), "updated_at": now_iso(),
    }})
    fresh = await db.payments.find_one({"id": payment_id}, {"_id": 0})
    try:
        fresh = await fulfill_payment(fresh)
    except Exception:
        # Entitlement pipeline failed — compensate the token spend so the
        # member is never charged for a payment that did not fulfill.
        await refund_tokens(label["id"], parts, "payment", payment_id,
                            "Fulfillment gagal — token dikembalikan")
        await db.payments.update_one({"id": payment_id}, {"$set": {
            "status": "pending", "provider": "xendit", "provider_status": None,
            "payment_method": None, "token_cost": None, "token_parts": None,
            "paid_at": None, "updated_at": now_iso(),
        }})
        raise HTTPException(status_code=502, detail="Pembayaran token gagal diproses — token dikembalikan")
    await log_activity(user["id"], "pay_with_token", "payment", payment_id,
                       after={"tokens": offer["tokens"], "parts": parts})
    return fresh


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