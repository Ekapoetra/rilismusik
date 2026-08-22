"""Xendit Payment Sessions + idempotent local fulfillment.

This integration intentionally uses backend polling. Redirect return URLs are
navigation only and are never trusted as proof of payment.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException
from pymongo import ReturnDocument

from models import new_id, now_iso
from routes.deps import db, logger, admin_user_ids, label_user_ids, notify_many
from email_service import send_payment_receipt_email


XENDIT_TERMINAL = {"COMPLETED", "EXPIRED", "CANCELED"}
LOCAL_STATUS = {
    "ACTIVE": "pending",
    "COMPLETED": "paid",
    "EXPIRED": "expired",
    "CANCELED": "cancelled",
}
DEFAULT_PRICES = {
    "pay_per_release": 35_000,
    "annual_normal": 350_000,
    "annual_vip": 500_000,
    "wami_addon": 100_000,
}


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise HTTPException(status_code=503, detail="Konfigurasi Xendit belum lengkap")
    return value


def xendit_configured() -> bool:
    return bool(os.environ.get("XENDIT_SECRET_KEY", "").strip())


async def payment_price(code: str) -> int:
    pricing = await db.landing_settings.find_one({"key": "pricing"}, {"_id": 0, "value": 1})
    values = (pricing or {}).get("value") or {}
    key_map = {
        "pay_per_release": "pay_per_release_price",
        "annual_normal": "annual_normal_price",
        "annual_vip": "annual_subscription_price",
        "wami_addon": "wami_addon_price",
    }
    configured = values.get(key_map.get(code))
    return int(configured or DEFAULT_PRICES[code])


async def create_payment_document(
    *, label_id: str, payment_type: str, amount: int, description: str,
    release_id: Optional[str] = None, track_id: Optional[str] = None,
    wami_order_id: Optional[str] = None, tier: Optional[str] = None,
    product_id: Optional[str] = None, service_order_id: Optional[str] = None,
    return_path: str = "/label/invoices",
) -> Dict[str, Any]:
    payment_id = new_id()
    document = {
        "id": payment_id,
        "label_id": label_id,
        "release_id": release_id,
        "track_id": track_id,
        "wami_order_id": wami_order_id,
        "service_order_id": service_order_id,
        "product_id": product_id,
        "type": payment_type,
        "tier": tier,
        "description": description,
        "amount": int(amount),
        "currency": "IDR",
        "status": "pending",
        "provider": "xendit",
        "provider_status": None,
        "reference_id": f"rm-{payment_id}",
        "xendit_invoice_url": None,
        "payment_request_id": None,
        "payment_id_provider": None,
        "fulfillment_status": "pending",
        "return_path": return_path,
        "paid_at": None,
        "expired_at": None,
        "last_provider_poll_at": None,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.payments.insert_one(document)
    document.pop("_id", None)
    return document


def build_session_payload(payment: Dict[str, Any]) -> Dict[str, Any]:
    # Browser return URL only — not a callback/webhook. Keep it separate from
    # preview FRONTEND_URL so production payments always return to the live app.
    frontend_url = _required_env("XENDIT_RETURN_URL_BASE").rstrip("/")
    return_url = f"{frontend_url}{payment.get('return_path') or '/label/invoices'}?payment_id={payment['id']}"
    amount = int(payment["amount"])
    description = str(payment.get("description") or payment.get("type") or "Pembayaran RILIS MUSIK")[:255]
    return {
        "reference_id": payment["reference_id"][:64],
        "session_type": "PAY",
        "mode": "PAYMENT_LINK",
        "amount": amount,
        "currency": "IDR",
        "country": "ID",
        "capture_method": "AUTOMATIC",
        "locale": "id",
        "description": description,
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat().replace("+00:00", "Z"),
        "success_return_url": return_url,
        "cancel_return_url": return_url,
        "metadata": {
            "local_payment_id": payment["id"],
            "payment_type": payment["type"],
        },
        "items": [{
            "reference_id": (payment.get("product_id") or payment.get("release_id") or payment["id"])[:255],
            "name": description,
            "description": description,
            "type": "DIGITAL_SERVICE",
            "category": "MUSIC_DISTRIBUTION",
            "net_unit_amount": amount,
            "quantity": 1,
        }],
    }


async def _xendit_request(method: str, path: str, **kwargs) -> Dict[str, Any]:
    secret = _required_env("XENDIT_SECRET_KEY")
    base_url = _required_env("XENDIT_API_URL").rstrip("/")
    try:
        async with httpx.AsyncClient(
            base_url=base_url,
            auth=(secret, ""),
            timeout=httpx.Timeout(20.0, connect=7.0),
        ) as client:
            response = await client.request(method, path, **kwargs)
    except httpx.RequestError as exc:
        logger.warning("[XENDIT] network error %s %s: %s", method, path, type(exc).__name__)
        raise HTTPException(status_code=502, detail="Xendit tidak dapat dihubungi. Coba lagi.") from exc
    if response.status_code >= 400:
        try:
            remote = response.json()
            code = remote.get("error_code")
            message = remote.get("message")
        except Exception:
            code, message = None, None
        logger.warning("[XENDIT] request rejected %s %s status=%s code=%s", method, path, response.status_code, code)
        if response.status_code == 401:
            raise HTTPException(status_code=503, detail="Otorisasi Xendit production ditolak")
        raise HTTPException(status_code=502, detail=message or "Xendit menolak permintaan pembayaran")
    return response.json()


async def create_xendit_session(payment: Dict[str, Any]) -> Dict[str, Any]:
    if payment.get("status") == "paid":
        raise HTTPException(status_code=409, detail="Pembayaran ini sudah lunas")
    if payment.get("status") in ("expired", "cancelled", "failed"):
        attempt = int(payment.get("session_attempt") or 0) + 1
        reference_id = f"rm-{payment['id']}-{attempt}"[:64]
        await db.payments.update_one(
            {"id": payment["id"]},
            {
                "$set": {
                    "status": "pending", "provider_status": None,
                    "reference_id": reference_id, "session_attempt": attempt,
                    "xendit_invoice_url": None, "expired_at": None,
                    "last_provider_poll_at": None, "updated_at": now_iso(),
                },
                "$unset": {"xendit_session_id": "", "xendit_invoice_id": ""},
            },
        )
        payment = await db.payments.find_one({"id": payment["id"]}, {"_id": 0})
    if payment.get("xendit_session_id") and payment.get("xendit_invoice_url"):
        return payment

    payload = build_session_payload(payment)
    remote = await _xendit_request(
        "POST", "/sessions", json=payload,
        headers={"Idempotency-Key": payment["reference_id"]},
    )
    session_id = remote.get("payment_session_id")
    payment_url = remote.get("payment_link_url")
    if not session_id or not payment_url:
        raise HTTPException(status_code=502, detail="Respons checkout Xendit tidak lengkap")
    await db.payments.update_one({"id": payment["id"]}, {"$set": {
        "xendit_session_id": session_id,
        "xendit_invoice_id": session_id,
        "xendit_invoice_url": payment_url,
        "provider_status": remote.get("status") or "ACTIVE",
        "expired_at": remote.get("expires_at"),
        "updated_at": now_iso(),
    }})
    return await db.payments.find_one({"id": payment["id"]}, {"_id": 0})


async def get_xendit_session(session_id: str) -> Dict[str, Any]:
    return await _xendit_request("GET", f"/sessions/{session_id}")


async def _send_receipt(payment: Dict[str, Any]) -> None:
    try:
        label = await db.labels.find_one(
            {"id": payment["label_id"]}, {"_id": 0, "label_name": 1, "user_id": 1},
        )
        user_doc = await db.users.find_one(
            {"id": (label or {}).get("user_id")}, {"_id": 0, "email": 1},
        )
        if label and user_doc and user_doc.get("email"):
            await send_payment_receipt_email(
                to=user_doc["email"],
                label_name=label.get("label_name") or "Label",
                description=payment.get("description") or payment["type"],
                amount_idr=int(payment.get("amount") or 0),
                invoice_id=payment["id"],
            )
    except Exception as exc:
        logger.warning("[XENDIT] receipt email failed payment=%s error=%s", payment["id"], type(exc).__name__)


async def fulfill_payment(payment: Dict[str, Any]) -> Dict[str, Any]:
    """Apply paid entitlements exactly once, safe across repeated polling."""
    if payment.get("fulfillment_status") == "fulfilled":
        return payment
    stale_before = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    claimed = await db.payments.find_one_and_update(
        {
            "id": payment["id"],
            "$or": [
                {"fulfillment_status": {"$in": [None, "pending", "failed"]}},
                {"fulfillment_status": "processing", "fulfillment_started_at": {"$lt": stale_before}},
            ],
        },
        {"$set": {
            "fulfillment_status": "processing",
            "fulfillment_started_at": now_iso(),
            "updated_at": now_iso(),
        }},
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    if not claimed:
        return await db.payments.find_one({"id": payment["id"]}, {"_id": 0})

    payment_id = claimed["id"]
    try:
        if claimed["type"] == "pay_per_release":
            await db.releases.update_one(
                {"id": claimed["release_id"], "fulfilled_payment_ids": {"$ne": payment_id}},
                {"$set": {"payment_status": "paid", "status": "under_review", "updated_at": now_iso()},
                 "$addToSet": {"fulfilled_payment_ids": payment_id}},
            )
        elif claimed["type"] == "annual_subscription":
            label = await db.labels.find_one({"id": claimed["label_id"]}, {"_id": 0})
            base = datetime.now(timezone.utc)
            if label and label.get("subscription_expires_at"):
                try:
                    current_expiry = datetime.fromisoformat(str(label["subscription_expires_at"]).replace("Z", "+00:00"))
                    if current_expiry > base:
                        base = current_expiry
                except Exception:
                    pass
            await db.labels.update_one(
                {"id": claimed["label_id"], "fulfilled_payment_ids": {"$ne": payment_id}},
                {"$set": {
                    "subscription_status": "active",
                    "subscription_expires_at": (base + timedelta(days=365)).isoformat(),
                    "payment_type": "annual_subscription",
                    "subscription_tier": claimed.get("tier") or "annual_vip",
                    "updated_at": now_iso(),
                }, "$addToSet": {"fulfilled_payment_ids": payment_id}},
            )
        elif claimed["type"] == "wami_addon":
            await db.wami_orders.update_one(
                {"id": claimed.get("wami_order_id"), "fulfilled_payment_ids": {"$ne": payment_id}},
                {"$set": {"status": "pending", "paid_at": now_iso(), "updated_at": now_iso()},
                 "$addToSet": {"fulfilled_payment_ids": payment_id}},
            )
            order = await db.wami_orders.find_one({"id": claimed.get("wami_order_id")}, {"_id": 0})
            if order:
                await notify_many(
                    await admin_user_ids(("super_admin", "admin_release")), "wami_new",
                    "WAMI baru — sudah dibayar",
                    f"WAMI '{order.get('track_title')}' menunggu diproses.",
                    "/admin/wami", {"wami_order_id": order["id"]},
                )
        elif claimed["type"] == "custom_service":
            await db.service_orders.update_one(
                {"id": claimed.get("service_order_id"), "fulfilled_payment_ids": {"$ne": payment_id}},
                {"$set": {"status": "paid", "paid_at": now_iso(), "updated_at": now_iso()},
                 "$addToSet": {"fulfilled_payment_ids": payment_id}},
            )
            await notify_many(
                await admin_user_ids(("super_admin", "admin_finance", "admin_support")),
                "service_order_paid", "Layanan baru sudah dibayar",
                f"Pesanan '{claimed.get('description')}' siap diproses.",
                "/admin/payments", {"payment_id": payment_id},
            )

        await db.payments.update_one({"id": payment_id}, {"$set": {
            "status": "paid",
            "fulfillment_status": "fulfilled",
            "fulfilled_at": now_iso(),
            "paid_at": claimed.get("paid_at") or now_iso(),
            "updated_at": now_iso(),
        }})
        await notify_many(
            await label_user_ids(claimed["label_id"]), "payment_paid", "Pembayaran berhasil",
            f"Pembayaran {claimed.get('description') or claimed['type']} telah dikonfirmasi Xendit.",
            claimed.get("return_path") or "/label/invoices", {"payment_id": payment_id},
        )
        await _send_receipt(claimed)
    except Exception as exc:
        logger.exception("[XENDIT] fulfillment failed payment=%s: %s", payment_id, exc)
        await db.payments.update_one({"id": payment_id}, {"$set": {
            "fulfillment_status": "failed", "fulfillment_error": type(exc).__name__, "updated_at": now_iso(),
        }})
        raise
    return await db.payments.find_one({"id": payment_id}, {"_id": 0})


async def reconcile_payment(payment: Dict[str, Any], remote: Dict[str, Any]) -> Dict[str, Any]:
    """Validate provider data, persist status, and fulfill COMPLETED payments."""
    if remote.get("reference_id") != payment.get("reference_id"):
        raise HTTPException(status_code=409, detail="Referensi pembayaran Xendit tidak cocok")
    if int(remote.get("amount") or 0) != int(payment.get("amount") or 0):
        raise HTTPException(status_code=409, detail="Nominal pembayaran Xendit tidak cocok")
    if remote.get("currency") != payment.get("currency", "IDR"):
        raise HTTPException(status_code=409, detail="Mata uang pembayaran Xendit tidak cocok")
    provider_status = str(remote.get("status") or "").upper()
    if provider_status not in LOCAL_STATUS:
        raise HTTPException(status_code=502, detail="Status pembayaran Xendit tidak dikenali")
    local_status = LOCAL_STATUS[provider_status]
    await db.payments.update_one({"id": payment["id"]}, {"$set": {
        "provider_status": provider_status,
        "status": local_status,
        "payment_request_id": remote.get("payment_request_id"),
        "payment_id_provider": remote.get("payment_id"),
        "last_provider_poll_at": now_iso(),
        "paid_at": now_iso() if provider_status == "COMPLETED" else payment.get("paid_at"),
        "updated_at": now_iso(),
    }})
    fresh = await db.payments.find_one({"id": payment["id"]}, {"_id": 0})
    if provider_status == "COMPLETED":
        fresh = await fulfill_payment(fresh)
    return fresh


async def poll_payment(payment: Dict[str, Any], *, force: bool = False) -> Dict[str, Any]:
    if payment.get("status") == "paid" and payment.get("fulfillment_status") == "fulfilled":
        return payment
    session_id = payment.get("xendit_session_id")
    if not session_id:
        return payment
    if not force and payment.get("last_provider_poll_at"):
        try:
            last = datetime.fromisoformat(str(payment["last_provider_poll_at"]).replace("Z", "+00:00"))
            if datetime.now(timezone.utc) - last < timedelta(seconds=3):
                return payment
        except Exception:
            pass
    remote = await get_xendit_session(session_id)
    return await reconcile_payment(payment, remote)
