"""Xendit Payment Sessions + idempotent local fulfillment.

This integration intentionally uses backend polling. Redirect return URLs are
navigation only and are never trusted as proof of payment.
"""
import asyncio
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from models import new_id, now_iso
from routes.deps import db, logger, notify_many
from email_service import send_admin_paid_payment_email, send_payment_receipt_email


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


async def admin_user_ids(roles: tuple[str, ...]) -> list[str]:
    users = await db.users.find(
        {"role": {"$in": list(roles)}, "status": {"$nin": ["disabled", "suspended"]}},
        {"_id": 0, "id": 1},
    ).to_list(1000)
    return [user["id"] for user in users if user.get("id")]


async def label_user_ids(label_id: str) -> list[str]:
    label = await db.labels.find_one({"id": label_id}, {"_id": 0, "user_id": 1})
    return [label["user_id"]] if label and label.get("user_id") else []


ADMIN_PAYMENT_ROLES = {
    "pay_per_release": ("super_admin", "admin_finance", "admin_release"),
    "annual_subscription": ("super_admin", "admin_finance"),
    "wami_addon": ("super_admin", "admin_finance", "admin_release"),
    "custom_service": ("super_admin", "admin_finance", "admin_support"),
}


def _admin_payment_instruction(payment_type: str) -> str:
    return {
        "pay_per_release": "Buka release dan lanjutkan proses distribusi.",
        "custom_service": "Tandai layanan sedang dikerjakan, lalu selesai setelah pekerjaan tuntas.",
        "wami_addon": "Buka WAMI dan lanjutkan proses pendaftaran.",
        "annual_subscription": "Langganan sudah aktif otomatis; tidak ada tindakan manual.",
    }.get(payment_type, "Tinjau detail pembayaran di dashboard admin.")


def _admin_payment_link(payment: Dict[str, Any]) -> str:
    if payment.get("type") == "pay_per_release" and payment.get("release_id"):
        return f"/admin/releases/{payment['release_id']}"
    if payment.get("type") == "wami_addon":
        return "/admin/wami"
    return f"/admin/payments?payment_id={payment['id']}"


async def _upsert_paid_notification(
    *, event_key: str, user_id: str, ntype: str, title: str, body: str,
    link: str, payment_id: str,
) -> None:
    await db.notifications.update_one(
        {"event_key": event_key},
        {"$setOnInsert": {
            "id": new_id(), "event_key": event_key, "user_id": user_id,
            "type": ntype, "title": title, "body": body, "link": link,
            "meta": {"payment_id": payment_id}, "read_at": None, "created_at": now_iso(),
        }},
        upsert=True,
    )


async def _send_email_once(event_key: str, recipient: str, sender) -> None:
    stale_before = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    try:
        claimed = await db.payment_notification_deliveries.find_one_and_update(
            {
                "event_key": event_key,
                "$or": [
                    {"status": {"$exists": False}}, {"status": "failed"},
                    {"status": "processing", "updated_at": {"$lt": stale_before}},
                ],
            },
            {"$set": {"status": "processing", "recipient": recipient, "updated_at": now_iso()},
             "$setOnInsert": {"event_key": event_key, "created_at": now_iso()}},
            upsert=True, return_document=ReturnDocument.AFTER, projection={"_id": 0},
        )
    except DuplicateKeyError:
        return
    if not claimed:
        return
    message_id = await sender()
    await db.payment_notification_deliveries.update_one(
        {"event_key": event_key},
        {"$set": {
            "status": "sent" if message_id else "failed",
            "message_id": message_id, "updated_at": now_iso(),
        }},
    )


@dataclass(frozen=True)
class PaymentCreateData:
    label_id: str
    payment_type: str
    amount: int
    description: str
    return_path: str = "/label/invoices"
    release_id: Optional[str] = None
    track_id: Optional[str] = None
    wami_order_id: Optional[str] = None
    tier: Optional[str] = None
    product_id: Optional[str] = None
    service_order_id: Optional[str] = None
    reference_id: Optional[str] = None
    line_items: Optional[List[Dict[str, Any]]] = None
    base_amount: Optional[int] = None
    addon_amount: Optional[int] = None
    addon_product_ids: Optional[List[str]] = None
    approval_required_before_payment: bool = False


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


async def create_payment_document(data: PaymentCreateData) -> Dict[str, Any]:
    payment_id = new_id()
    document = {
        "id": payment_id,
        "label_id": data.label_id,
        "release_id": data.release_id,
        "track_id": data.track_id,
        "wami_order_id": data.wami_order_id,
        "service_order_id": data.service_order_id,
        "product_id": data.product_id,
        "type": data.payment_type,
        "tier": data.tier,
        "description": data.description,
        "amount": int(data.amount),
        "currency": "IDR",
        "status": "pending",
        "provider": "xendit",
        "provider_status": None,
        "reference_id": data.reference_id or f"rm-{payment_id}",
        "xendit_invoice_url": None,
        "payment_request_id": None,
        "payment_id_provider": None,
        "fulfillment_status": "pending",
        "return_path": data.return_path,
        "paid_at": None,
        "expired_at": None,
        "last_provider_poll_at": None,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "line_items": data.line_items or [],
        "base_amount": data.base_amount,
        "addon_amount": data.addon_amount,
        "addon_product_ids": data.addon_product_ids or [],
        "approval_required_before_payment": data.approval_required_before_payment,
    }
    try:
        await db.payments.insert_one(document)
    except DuplicateKeyError:
        existing = await db.payments.find_one({"reference_id": document["reference_id"]}, {"_id": 0})
        if existing:
            return existing
        raise
    document.pop("_id", None)
    return document


def build_session_payload(payment: Dict[str, Any]) -> Dict[str, Any]:
    # Browser return URL only — not a callback/webhook. Keep it separate from
    # preview FRONTEND_URL so production payments always return to the live app.
    frontend_url = _required_env("XENDIT_RETURN_URL_BASE").rstrip("/")
    return_url = f"{frontend_url}{payment.get('return_path') or '/label/invoices'}?payment_id={payment['id']}"
    amount = int(payment["amount"])
    description = str(payment.get("description") or payment.get("type") or "Pembayaran RILIS MUSIK")[:255]
    configured_items = payment.get("line_items") or []
    items = [{
        "reference_id": str(item.get("reference_id") or payment["id"])[:255],
        "name": str(item.get("name") or description)[:255],
        "description": str(item.get("description") or item.get("name") or description)[:255],
        "type": "DIGITAL_SERVICE",
        "category": "MUSIC_DISTRIBUTION",
        "net_unit_amount": int(item.get("amount") or 0),
        "quantity": int(item.get("quantity") or 1),
    } for item in configured_items if int(item.get("amount") or 0) > 0]
    if not items:
        items = [{
            "reference_id": (payment.get("product_id") or payment.get("release_id") or payment["id"])[:255],
            "name": description,
            "description": description,
            "type": "DIGITAL_SERVICE",
            "category": "MUSIC_DISTRIBUTION",
            "net_unit_amount": amount,
            "quantity": 1,
        }]
    if sum(item["net_unit_amount"] * item["quantity"] for item in items) != amount:
        raise HTTPException(status_code=500, detail="Rincian invoice tidak sesuai dengan total pembayaran")
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
        "items": items,
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


def _extract_payment_method(payload: Dict[str, Any]) -> Optional[str]:
    sources = [
        payload.get("payment_method") if isinstance(payload.get("payment_method"), dict) else {},
        payload.get("payment_details") if isinstance(payload.get("payment_details"), dict) else {},
        payload,
    ]
    for source in sources:
        method = source.get("channel_code") or source.get("channel_category")
        if source is not payload:
            method = method or source.get("type")
        if method:
            return str(method)[:100]
    return None


async def _resolve_provider_payment_metadata(remote: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    method = _extract_payment_method(remote)
    payment_id = remote.get("payment_id") or remote.get("latest_payment_id")
    request_id = remote.get("payment_request_id")
    if method or str(remote.get("status") or "").upper() != "COMPLETED" or not request_id:
        return method, payment_id
    try:
        payment_request = await _xendit_request("GET", f"/v3/payment_requests/{request_id}")
        method = _extract_payment_method(payment_request)
        payment_id = payment_request.get("latest_payment_id") or payment_id
        if payment_id:
            provider_payment = await _xendit_request("GET", f"/v3/payments/{payment_id}")
            method = _extract_payment_method(provider_payment) or method
    except Exception as exc:
        logger.warning(
            "[XENDIT] payment method lookup deferred request=%s error=%s",
            request_id, type(exc).__name__,
        )
    return method, payment_id


async def _send_receipt(payment: Dict[str, Any]) -> None:
    try:
        label = await db.labels.find_one(
            {"id": payment["label_id"]}, {"_id": 0, "label_name": 1, "user_id": 1},
        )
        user_doc = await db.users.find_one(
            {"id": (label or {}).get("user_id")}, {"_id": 0, "email": 1},
        )
        label_name = (label or {}).get("label_name") or "Label"
        description = payment.get("description") or payment["type"]
        amount = int(payment.get("amount") or 0)
        email_jobs = []
        if user_doc and user_doc.get("email"):
            recipient = user_doc["email"]
            email_jobs.append(_send_email_once(
                f"payment-paid:{payment['id']}:email:label:{recipient}", recipient,
                lambda recipient=recipient: send_payment_receipt_email(
                    to=recipient, label_name=label_name, description=description,
                    amount_idr=amount, invoice_id=payment["id"],
                ),
            ))
        roles = ADMIN_PAYMENT_ROLES.get(payment.get("type"), ("super_admin", "admin_finance"))
        admins = await db.users.find(
            {"role": {"$in": list(roles)}, "status": {"$nin": ["disabled", "suspended"]}},
            {"_id": 0, "id": 1, "email": 1},
        ).to_list(100)
        for admin in admins:
            if not admin.get("email"):
                continue
            recipient = admin["email"]
            email_jobs.append(_send_email_once(
                f"payment-paid:{payment['id']}:email:admin:{admin['id']}", recipient,
                lambda recipient=recipient: send_admin_paid_payment_email(
                    to=recipient, label_name=label_name, description=description,
                    amount_idr=amount, invoice_id=payment["id"], payment_type=payment["type"],
                    paid_at=payment.get("paid_at") or now_iso(),
                    instruction=_admin_payment_instruction(payment["type"]),
                ),
            ))
        if email_jobs:
            await asyncio.gather(*email_jobs)
    except Exception as exc:
        logger.warning("[XENDIT] payment email failed payment=%s error=%s", payment["id"], type(exc).__name__)


async def _dispatch_paid_notifications(payment: Dict[str, Any]) -> None:
    try:
        label = await db.labels.find_one(
            {"id": payment["label_id"]}, {"_id": 0, "label_name": 1, "user_id": 1},
        )
        label_name = (label or {}).get("label_name") or "Label"
        description = payment.get("description") or payment["type"]
        if label and label.get("user_id"):
            await _upsert_paid_notification(
                event_key=f"payment-paid:{payment['id']}:inapp:label:{label['user_id']}",
                user_id=label["user_id"], ntype="payment_paid", title="Pembayaran berhasil",
                body=f"Pembayaran {description} telah dikonfirmasi Xendit.",
                link=payment.get("return_path") or "/label/invoices", payment_id=payment["id"],
            )
        roles = ADMIN_PAYMENT_ROLES.get(payment.get("type"), ("super_admin", "admin_finance"))
        admin_ids = await admin_user_ids(roles)
        for admin_id in admin_ids:
            await _upsert_paid_notification(
                event_key=f"payment-paid:{payment['id']}:inapp:admin:{admin_id}",
                user_id=admin_id, ntype="admin_payment_paid",
                title="Pembayaran baru diterima",
                body=f"{label_name} membayar {description}. {_admin_payment_instruction(payment['type'])}",
                link=_admin_payment_link(payment), payment_id=payment["id"],
            )
        await _send_receipt(payment)
    except Exception as exc:
        logger.warning("[XENDIT] paid notification dispatch failed payment=%s error=%s", payment["id"], type(exc).__name__)


async def _claim_fulfillment(payment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    stale_before = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    return await db.payments.find_one_and_update(
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


async def _fulfill_release(payment: Dict[str, Any]) -> None:
    fulfilled_status = "paid" if payment.get("approval_required_before_payment") else "under_review"
    await db.releases.update_one(
        {"id": payment["release_id"], "fulfilled_payment_ids": {"$ne": payment["id"]}},
        {"$set": {"payment_status": "paid", "status": fulfilled_status, "updated_at": now_iso()},
         "$addToSet": {"fulfilled_payment_ids": payment["id"]},
         "$push": {"status_history": {
             "from": "awaiting_payment", "to": fulfilled_status, "changed_by": "xendit",
             "changed_at": now_iso(), "note": "Pembayaran dikonfirmasi Xendit",
         }}},
    )


def _subscription_expiry(label: Optional[Dict[str, Any]]) -> datetime:
    base = datetime.now(timezone.utc)
    raw = (label or {}).get("subscription_expires_at")
    if not raw:
        return base
    try:
        current = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return current if current > base else base
    except (TypeError, ValueError):
        return base


async def _fulfill_subscription(payment: Dict[str, Any]) -> None:
    label = await db.labels.find_one({"id": payment["label_id"]}, {"_id": 0})
    expiry = _subscription_expiry(label) + timedelta(days=365)
    await db.labels.update_one(
        {"id": payment["label_id"], "fulfilled_payment_ids": {"$ne": payment["id"]}},
        {"$set": {
            "subscription_status": "active", "subscription_expires_at": expiry.isoformat(),
            "payment_type": "annual_subscription",
            "subscription_tier": payment.get("tier") or "annual_vip", "updated_at": now_iso(),
        }, "$addToSet": {"fulfilled_payment_ids": payment["id"]}},
    )


async def _fulfill_wami(payment: Dict[str, Any]) -> None:
    await db.wami_orders.update_one(
        {"id": payment.get("wami_order_id"), "fulfilled_payment_ids": {"$ne": payment["id"]}},
        {"$set": {"status": "pending", "paid_at": now_iso(), "updated_at": now_iso()},
         "$addToSet": {"fulfilled_payment_ids": payment["id"]}},
    )


async def _fulfill_custom_service(payment: Dict[str, Any]) -> None:
    await db.service_orders.update_one(
        {"id": payment.get("service_order_id"), "fulfilled_payment_ids": {"$ne": payment["id"]}},
        {"$set": {"status": "paid", "paid_at": now_iso(), "updated_at": now_iso()},
         "$addToSet": {"fulfilled_payment_ids": payment["id"]}},
    )


FULFILLMENT_HANDLERS = {
    "pay_per_release": _fulfill_release,
    "annual_subscription": _fulfill_subscription,
    "wami_addon": _fulfill_wami,
    "custom_service": _fulfill_custom_service,
}


async def _apply_entitlement(payment: Dict[str, Any]) -> None:
    handler = FULFILLMENT_HANDLERS.get(payment["type"])
    if not handler:
        raise ValueError(f"Unsupported payment type: {payment['type']}")
    await handler(payment)


async def _finalize_fulfillment(payment: Dict[str, Any]) -> None:
    payment_id = payment["id"]
    await db.payments.update_one({"id": payment_id}, {"$set": {
        "status": "paid", "fulfillment_status": "fulfilled", "fulfilled_at": now_iso(),
        "paid_at": payment.get("paid_at") or now_iso(), "updated_at": now_iso(),
    }})
    finalized = {**payment, "status": "paid", "paid_at": payment.get("paid_at") or now_iso()}
    await _dispatch_paid_notifications(finalized)


async def _record_fulfillment_failure(payment_id: str, exc: Exception) -> None:
    logger.exception("[XENDIT] fulfillment failed payment=%s: %s", payment_id, exc)
    await db.payments.update_one({"id": payment_id}, {"$set": {
        "fulfillment_status": "failed", "fulfillment_error": type(exc).__name__, "updated_at": now_iso(),
    }})


async def fulfill_payment(payment: Dict[str, Any]) -> Dict[str, Any]:
    """Apply paid entitlements exactly once, safe across repeated polling."""
    if payment.get("fulfillment_status") == "fulfilled":
        await _dispatch_paid_notifications(payment)
        return payment
    claimed = await _claim_fulfillment(payment)
    if not claimed:
        return await db.payments.find_one({"id": payment["id"]}, {"_id": 0})
    try:
        await _apply_entitlement(claimed)
        await _finalize_fulfillment(claimed)
    except Exception as exc:
        await _record_fulfillment_failure(claimed["id"], exc)
        raise
    return await db.payments.find_one({"id": claimed["id"]}, {"_id": 0})


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
    payment_method, provider_payment_id = await _resolve_provider_payment_metadata(remote)
    await db.payments.update_one({"id": payment["id"]}, {"$set": {
        "provider_status": provider_status,
        "status": local_status,
        "payment_request_id": remote.get("payment_request_id"),
        "payment_id_provider": provider_payment_id,
        "payment_method": payment_method or payment.get("payment_method"),
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
