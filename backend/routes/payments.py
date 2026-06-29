"""Payments (Xendit mock) router."""
from fastapi import APIRouter, HTTPException, Request, Response, Depends, UploadFile, File, Form, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta, date
import os
import csv
import io
import shutil
import secrets

from .deps import (
    db, logger, UPLOAD_DIR,
    get_current_user, require_label, require_artist, require_admin, require_super_admin,
    public_user, get_label_by_user, redact_label_for_self, LABEL_HIDDEN_FIELDS,
    log_activity, notify, notify_many, admin_user_ids, label_user_ids,
    LABEL_ROLE, ARTIST_ROLE, ADMIN_ROLES, SUPER_ADMIN,
)
from email_service import send_payment_receipt_email
from models import (
    RegisterLabelIn, LoginIn, ForgotPasswordIn, ResetPasswordIn, VerifyEmailIn,
    LabelProfileUpdate, BankAccountIn,
    ReleaseDraftIn, ReleaseSubmitConfirmation, AdminReleaseAction,
    ArtistIn, ArtistUpdateIn,
    CreateReleasePaymentIn,
    CMSUpdateIn, AdminUserCreateIn, LabelStatusUpdate,
    ExchangeRateIn, RoyaltyImportPublishIn, RoyaltyLineMatchIn,
    WithdrawRequestIn, WithdrawAdminAction,
    TicketCreateIn, TicketCommentIn, TicketAdminUpdateIn,
    ContractCreateIn, ContractExtendIn, ContractTerminateIn,
    BlacklistIn, NotificationMarkIn,
    CreateSubscriptionPaymentIn, CreateWamiOrderIn, AdminWamiUpdateIn,
    now_iso, new_id,
)
from auth_utils import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    set_auth_cookies, clear_auth_cookies, decode_token,
)
from royalty_utils import (
    parse_csv_bytes, detect_columns, parse_amount, normalize_header,
    parse_period_from_value, calculate_line, label_percentage_at,
    strip_sensitive,
)
from withdraw_utils import withdraw_window_state, jakarta_now, MIN_WITHDRAW_IDR

# =============================================================================
#                              PAYMENTS (MOCK XENDIT)
# =============================================================================
pay_r = APIRouter(prefix="/payments", tags=["payments"])


SUBSCRIPTION_PRICES = {"annual_normal": 350000, "annual_vip": 500000}
WAMI_ADDON_PRICE = 100000
WAMI_FREE_TIERS = ("annual_vip",)  # tiers that get WAMI for free


@pay_r.post("/subscription")
async def create_subscription_invoice(body: CreateSubscriptionPaymentIn, user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    tier = body.tier or "annual_vip"
    if tier not in SUBSCRIPTION_PRICES:
        raise HTTPException(status_code=400, detail="Tier tidak valid")
    invoice_id = new_id()
    invoice = {
        "id": invoice_id,
        "label_id": label["id"],
        "release_id": None,
        "track_id": None,
        "type": "annual_subscription",
        "tier": tier,
        "xendit_invoice_id": f"mock_{invoice_id[:12]}",
        "xendit_invoice_url": f"/payments/mock-checkout/{invoice_id}",
        "amount": SUBSCRIPTION_PRICES[tier],
        "currency": "IDR",
        "status": "pending",
        "paid_at": None,
        "expired_at": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
        "created_at": now_iso(),
    }
    await db.payments.insert_one(invoice)
    invoice.pop("_id", None)
    return invoice


@pay_r.post("/wami")
async def create_wami_invoice(body: CreateWamiOrderIn, user: dict = Depends(require_label)):
    """Create Xendit invoice for WAMI registration of a single track (Rp 100.000/lagu)."""
    label = await get_label_by_user(user)
    # Find track + verify ownership
    track = await db.tracks.find_one({"id": body.track_id}, {"_id": 0})
    if not track:
        raise HTTPException(status_code=404, detail="Track tidak ditemukan")
    rel = await db.releases.find_one({"id": track.get("release_id")}, {"_id": 0})
    if not rel or rel.get("label_id") != label["id"]:
        raise HTTPException(status_code=403, detail="Track ini bukan milik Anda")
    # Eligibility: only when release is LIVE
    if rel.get("status") != "live":
        raise HTTPException(status_code=400, detail="Pendaftaran WAMI hanya dapat dilakukan setelah rilisan LIVE")
    # VIP gets WAMI free → no invoice needed; just create order with status=pending.
    # Must be an ACTIVE annual_vip subscription (expired VIPs pay normally).
    now_dt = datetime.now(timezone.utc)
    sub_expires_raw = label.get("subscription_expires_at")
    sub_active = label.get("subscription_status") == "active"
    if sub_active and sub_expires_raw:
        try:
            sub_active = datetime.fromisoformat(str(sub_expires_raw).replace("Z", "+00:00")) > now_dt
        except Exception:
            sub_active = False
    is_vip = (
        label.get("payment_type") == "annual_subscription"
        and label.get("subscription_tier") == "annual_vip"
        and sub_active
    )
    # Prevent duplicate active orders
    existing = await db.wami_orders.find_one({"track_id": body.track_id, "status": {"$nin": ["cancelled", "rejected"]}})
    if existing:
        raise HTTPException(status_code=400, detail="Track ini sudah memiliki pendaftaran WAMI aktif")

    order_id = new_id()
    order = {
        "id": order_id,
        "label_id": label["id"],
        "release_id": rel["id"],
        "release_title": rel.get("release_title"),
        "track_id": body.track_id,
        "track_title": track.get("track_title"),
        "isrc": track.get("isrc"),
        "is_free_vip": is_vip,
        "amount_idr": 0 if is_vip else WAMI_ADDON_PRICE,
        "status": "pending" if is_vip else "unpaid",
        "wami_reference": None,
        "admin_note": None,
        "paid_at": now_iso() if is_vip else None,
        "registered_at": None,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.wami_orders.insert_one(order)

    if is_vip:
        # VIP → no Xendit needed, just notify admins
        admin_ids = await admin_user_ids(("super_admin", "admin_release"))
        await notify_many(
            admin_ids, "wami_new",
            "WAMI baru (VIP — gratis)",
            f"{label.get('label_name')} mengajukan WAMI untuk '{track.get('track_title')}'.",
            "/admin/wami", {"wami_order_id": order_id},
        )
        order.pop("_id", None)
        return {"order": order, "invoice": None, "free_vip": True}

    # Non-VIP → Xendit invoice
    invoice_id = new_id()
    invoice = {
        "id": invoice_id,
        "label_id": label["id"],
        "release_id": rel["id"],
        "track_id": body.track_id,
        "type": "wami_addon",
        "wami_order_id": order_id,
        "xendit_invoice_id": f"mock_{invoice_id[:12]}",
        "xendit_invoice_url": f"/payments/mock-checkout/{invoice_id}",
        "amount": WAMI_ADDON_PRICE,
        "currency": "IDR",
        "status": "pending",
        "paid_at": None,
        "expired_at": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
        "created_at": now_iso(),
    }
    await db.payments.insert_one(invoice)
    order.pop("_id", None)
    invoice.pop("_id", None)
    return {"order": order, "invoice": invoice, "free_vip": False}


@pay_r.post("/mock-pay/{invoice_id}")
async def mock_pay(invoice_id: str, user: dict = Depends(get_current_user)):
    """MOCK: simulate Xendit payment success. Will be replaced with real webhook later."""
    inv = await db.payments.find_one({"id": invoice_id})
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice tidak ditemukan")

    # Label can only pay their own; admin/super_admin can simulate any
    if user["role"] == LABEL_ROLE:
        label = await get_label_by_user(user)
        if inv["label_id"] != label["id"]:
            raise HTTPException(status_code=403, detail="Bukan invoice Anda")
    elif user["role"] not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Tidak diperbolehkan")

    if inv["status"] == "paid":
        return {"ok": True, "already_paid": True}

    await db.payments.update_one({"id": invoice_id}, {"$set": {"status": "paid", "paid_at": now_iso()}})

    if inv["type"] == "pay_per_release":
        await db.releases.update_one(
            {"id": inv["release_id"]},
            {"$set": {"payment_status": "paid", "status": "under_review", "updated_at": now_iso()}},
        )
    elif inv["type"] == "annual_subscription":
        now = datetime.now(timezone.utc)
        expires = (now + timedelta(days=365)).isoformat()
        tier = inv.get("tier") or "annual_vip"
        await db.labels.update_one(
            {"id": inv["label_id"]},
            {"$set": {
                "subscription_status": "active",
                "subscription_expires_at": expires,
                "payment_type": "annual_subscription",
                "subscription_tier": tier,
                "updated_at": now_iso(),
            }},
        )
    elif inv["type"] == "wami_addon":
        # Mark WAMI order as pending (waiting for admin to process)
        await db.wami_orders.update_one(
            {"id": inv.get("wami_order_id")},
            {"$set": {"status": "pending", "paid_at": now_iso(), "updated_at": now_iso()}},
        )
        order = await db.wami_orders.find_one({"id": inv.get("wami_order_id")}, {"_id": 0})
        admin_ids = await admin_user_ids(("super_admin", "admin_release"))
        await notify_many(
            admin_ids, "wami_new",
            "WAMI baru — sudah dibayar",
            f"WAMI '{order.get('track_title')}' menunggu diproses.",
            "/admin/wami", {"wami_order_id": order["id"]},
        )

    await log_activity(user["id"], "mock_pay", "payment", invoice_id)
    # Send payment receipt email (best-effort, after side-effects)
    try:
        label = await db.labels.find_one({"id": inv["label_id"]}, {"_id": 0, "label_name": 1, "user_id": 1})
        if label and label.get("user_id"):
            user_doc = await db.users.find_one({"id": label["user_id"]}, {"_id": 0, "email": 1})
            if user_doc and user_doc.get("email"):
                await send_payment_receipt_email(
                    to=user_doc["email"],
                    label_name=label.get("label_name") or "Label",
                    description=inv.get("description") or inv.get("type") or "Pembayaran",
                    amount_idr=int(inv.get("amount_idr") or 0),
                    invoice_id=invoice_id,
                )
    except Exception as e:
        logger.exception("payment receipt email failed for %s: %s", invoice_id, e)
    return {"ok": True, "invoice": await db.payments.find_one({"id": invoice_id}, {"_id": 0})}


@pay_r.post("/webhook/xendit")
async def xendit_webhook(payload: Dict[str, Any], request: Request):
    """Real Xendit webhook (idempotent). Authenticated via the `x-callback-token`
    header which Xendit signs every callback with. The token must match
    `XENDIT_CALLBACK_TOKEN` from env (see Xendit Dashboard → Settings → Callbacks).

    Until LIVE Xendit is wired, the endpoint stays auth-locked: if
    `XENDIT_CALLBACK_TOKEN` is not configured we reject all incoming payloads to
    prevent unauthenticated payment-confirmation bypass (security audit SEC-001).
    """
    expected_token = os.environ.get("XENDIT_CALLBACK_TOKEN")
    if not expected_token:
        # Fail-closed: no token configured → webhook MUST not be reachable.
        logger.warning("[XENDIT] webhook called but XENDIT_CALLBACK_TOKEN not set — denying")
        raise HTTPException(status_code=503, detail="Webhook not configured")
    provided = request.headers.get("x-callback-token") or request.headers.get("X-CALLBACK-TOKEN")
    # Constant-time comparison to avoid timing attacks
    if not provided or not secrets.compare_digest(provided, expected_token):
        logger.warning("[XENDIT] webhook rejected: invalid x-callback-token from %s", request.client.host if request.client else "?")
        raise HTTPException(status_code=401, detail="Invalid callback token")

    invoice_id_external = payload.get("id") or payload.get("external_id")
    status = (payload.get("status") or "").lower()
    if not invoice_id_external:
        raise HTTPException(status_code=400, detail="Missing invoice id")
    inv = await db.payments.find_one({"xendit_invoice_id": invoice_id_external})
    if not inv:
        return {"ok": True, "ignored": True}
    if inv["status"] == "paid":
        return {"ok": True, "already_paid": True}
    if status == "paid":
        await db.payments.update_one({"id": inv["id"]}, {"$set": {"status": "paid", "paid_at": now_iso()}})
        if inv["type"] == "pay_per_release":
            await db.releases.update_one({"id": inv["release_id"]}, {"$set": {"payment_status": "paid", "status": "under_review", "updated_at": now_iso()}})
        elif inv["type"] == "annual_subscription":
            now = datetime.now(timezone.utc)
            tier = inv.get("tier") or "annual_vip"
            await db.labels.update_one({"id": inv["label_id"]}, {"$set": {
                "subscription_status": "active",
                "subscription_expires_at": (now + timedelta(days=365)).isoformat(),
                "payment_type": "annual_subscription",
                "subscription_tier": tier,
                "updated_at": now_iso(),
            }})
        elif inv["type"] == "wami_addon":
            await db.wami_orders.update_one(
                {"id": inv.get("wami_order_id")},
                {"$set": {"status": "pending", "paid_at": now_iso(), "updated_at": now_iso()}},
            )
    elif status in ("expired", "failed", "cancelled"):
        await db.payments.update_one({"id": inv["id"]}, {"$set": {"status": status}})
    return {"ok": True}


