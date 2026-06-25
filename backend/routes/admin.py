"""Admin console + blacklist router."""
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
#                                ADMIN
# =============================================================================
admin_r = APIRouter(prefix="/admin", tags=["admin"])


@admin_r.get("/dashboard")
async def admin_dashboard(user: dict = Depends(require_admin)):
    total_labels = await db.labels.count_documents({})
    total_artists = await db.artists.count_documents({})
    total_releases = await db.releases.count_documents({})
    pending_review = await db.releases.count_documents({"status": "under_review"})
    delivered = await db.releases.count_documents({"status": "delivered"})
    live = await db.releases.count_documents({"status": "live"})
    pending_invoices = await db.payments.count_documents({"status": "pending"})
    paid_invoices = await db.payments.count_documents({"status": "paid"})
    pending_withdraws = await db.withdraw_requests.count_documents({"status": "requested"})
    active_tickets = await db.support_tickets.count_documents({"status": {"$nin": ["done", "rejected"]}})
    active_subscriptions = await db.labels.count_documents({"subscription_status": "active"})
    suspended_labels = await db.labels.count_documents({"account_status": "suspended"})

    # total revenue EUR + IDR from royalty_lines
    revenue_pipeline = [
        {"$group": {"_id": None, "total_eur": {"$sum": "$revenue_eur"}, "total_idr": {"$sum": "$label_idr"}}},
    ]
    total_eur = 0
    total_idr = 0
    async for r in db.royalty_lines.aggregate(revenue_pipeline):
        total_eur = r.get("total_eur", 0)
        total_idr = r.get("total_idr", 0)

    last_csv = await db.royalty_imports.find_one({}, {"_id": 0}, sort=[("created_at", -1)])

    return {
        "total_labels": total_labels,
        "total_artists": total_artists,
        "total_releases": total_releases,
        "pending_review": pending_review,
        "delivered": delivered,
        "live": live,
        "pending_invoices": pending_invoices,
        "paid_invoices": paid_invoices,
        "pending_withdraws": pending_withdraws,
        "active_tickets": active_tickets,
        "active_subscriptions": active_subscriptions,
        "suspended_labels": suspended_labels,
        "total_revenue_eur": total_eur,
        "total_revenue_idr": total_idr,
        "last_csv_import": last_csv,
    }


@admin_r.get("/labels")
async def admin_list_labels(user: dict = Depends(require_admin), q: Optional[str] = None, status: Optional[str] = None):
    filt: Dict[str, Any] = {}
    if status:
        filt["account_status"] = status
    if q:
        filt["label_name"] = {"$regex": q, "$options": "i"}
    items = await db.labels.find(filt, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return items


@admin_r.get("/labels/{label_id}")
async def admin_get_label(label_id: str, user: dict = Depends(require_admin)):
    label = await db.labels.find_one({"id": label_id}, {"_id": 0})
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    bank = await db.bank_accounts.find_one({"label_id": label_id}, {"_id": 0})
    artists_count = await db.artists.count_documents({"label_id": label_id})
    releases_count = await db.releases.count_documents({"label_id": label_id})
    return {"label": label, "bank_account": bank, "artists_count": artists_count, "releases_count": releases_count}


@admin_r.patch("/labels/{label_id}")
async def admin_update_label(label_id: str, body: LabelStatusUpdate, user: dict = Depends(require_admin)):
    label = await db.labels.find_one({"id": label_id})
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    upd: Dict[str, Any] = {}
    if body.account_status is not None:
        upd["account_status"] = body.account_status
        if body.account_status == "blacklisted":
            upd["blacklisted"] = True
    if body.royalty_percentage_default is not None:
        # only super_admin or admin_finance
        if user["role"] not in ("super_admin", "admin_finance"):
            raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
        upd["royalty_percentage_default"] = body.royalty_percentage_default
        await db.royalty_percentage_history.insert_one({
            "id": new_id(),
            "label_id": label_id,
            "percentage": body.royalty_percentage_default,
            "effective_month": datetime.now(timezone.utc).strftime("%Y-%m"),
            "changed_by": user["id"],
            "changed_at": now_iso(),
            "reason": body.royalty_change_reason,
        })
    if upd:
        upd["updated_at"] = now_iso()
        await db.labels.update_one({"id": label_id}, {"$set": upd})
        await log_activity(user["id"], "update_label", "label", label_id, before=label, after=upd)
    return await db.labels.find_one({"id": label_id}, {"_id": 0})


@admin_r.get("/releases")
async def admin_list_releases(user: dict = Depends(require_admin), status: Optional[str] = None, q: Optional[str] = None):
    filt: Dict[str, Any] = {}
    if status:
        filt["status"] = status
    if q:
        filt["release_title"] = {"$regex": q, "$options": "i"}
    items = await db.releases.find(filt, {"_id": 0}).sort("created_at", -1).to_list(1000)
    # enrich with label_name
    label_ids = list({i["label_id"] for i in items})
    labels = await db.labels.find({"id": {"$in": label_ids}}, {"_id": 0, "id": 1, "label_name": 1}).to_list(1000)
    name_map = {lab["id"]: lab["label_name"] for lab in labels}
    for it in items:
        it["label_name"] = name_map.get(it["label_id"])
    return items


@admin_r.get("/artists")
async def admin_list_artists(user: dict = Depends(require_admin), q: Optional[str] = None):
    filt: Dict[str, Any] = {}
    if q:
        filt["artist_name"] = {"$regex": q, "$options": "i"}
    items = await db.artists.find(filt, {"_id": 0}).sort("created_at", -1).to_list(1000)
    label_ids = list({i["label_id"] for i in items})
    labels = await db.labels.find({"id": {"$in": label_ids}}, {"_id": 0, "id": 1, "label_name": 1}).to_list(1000)
    name_map = {lab["id"]: lab["label_name"] for lab in labels}
    for it in items:
        it["label_name"] = name_map.get(it["label_id"])
    return items


@admin_r.get("/payments")
async def admin_list_payments(user: dict = Depends(require_admin), status: Optional[str] = None, ptype: Optional[str] = None):
    filt: Dict[str, Any] = {}
    if status:
        filt["status"] = status
    if ptype:
        filt["type"] = ptype
    items = await db.payments.find(filt, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return items


@admin_r.get("/admin-users")
async def admin_list_admin_users(user: dict = Depends(require_super_admin)):
    items = await db.users.find({"role": {"$in": list(ADMIN_ROLES)}}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(500)
    return items


@admin_r.post("/admin-users")
async def admin_create_admin_user(body: AdminUserCreateIn, user: dict = Depends(require_super_admin)):
    email = body.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Email sudah terdaftar")
    user_id = new_id()
    doc = {
        "id": user_id,
        "name": body.name,
        "email": email,
        "password_hash": hash_password(body.password),
        "role": body.role,
        "email_verified_at": now_iso(),  # admins are auto-verified
        "status": "active",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.users.insert_one(doc)
    doc.pop("_id", None)
    doc.pop("password_hash", None)
    return doc


@admin_r.patch("/admin-users/{user_id}")
async def admin_update_admin_user(user_id: str, body: Dict[str, Any], user: dict = Depends(require_super_admin)):
    target = await db.users.find_one({"id": user_id})
    if not target or target.get("role") not in ADMIN_ROLES:
        raise HTTPException(status_code=404, detail="Admin user tidak ditemukan")
    upd = {}
    if "role" in body and body["role"] in ADMIN_ROLES:
        upd["role"] = body["role"]
    if "status" in body and body["status"] in ("active", "suspended"):
        upd["status"] = body["status"]
    if "name" in body:
        upd["name"] = body["name"]
    if "password" in body and body["password"]:
        upd["password_hash"] = hash_password(body["password"])
    if upd:
        upd["updated_at"] = now_iso()
        await db.users.update_one({"id": user_id}, {"$set": upd})
    return await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})


@admin_r.get("/activity-logs")
async def admin_activity_logs(user: dict = Depends(require_admin), limit: int = 200):
    items = await db.activity_logs.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return items



# =============================================================================
#                              BLACKLIST (Admin action)
# =============================================================================
@admin_r.post("/labels/{label_id}/blacklist")
async def admin_blacklist_label(label_id: str, body: BlacklistIn, user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin",):
        raise HTTPException(status_code=403, detail="Hanya Super Admin")
    label = await db.labels.find_one({"id": label_id})
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    await db.labels.update_one({"id": label_id}, {"$set": {
        "account_status": "blacklisted", "blacklisted": True,
        "blacklist_reason": body.reason, "blacklisted_at": now_iso(),
        "blacklisted_by": user["id"], "updated_at": now_iso(),
    }})
    await log_activity(user["id"], "blacklist_label", "label", label_id, after={"reason": body.reason})
    return {"ok": True}


@admin_r.post("/labels/{label_id}/unblacklist")
async def admin_unblacklist_label(label_id: str, user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin",):
        raise HTTPException(status_code=403, detail="Hanya Super Admin")
    label = await db.labels.find_one({"id": label_id}, {"_id": 0, "id": 1})
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    await db.labels.update_one({"id": label_id}, {"$set": {
        "account_status": "active", "blacklisted": False,
        "blacklist_reason": None, "updated_at": now_iso(),
    }})
    await log_activity(user["id"], "unblacklist_label", "label", label_id)
    return {"ok": True}


# ============================================================
# Create user account for an unclaimed legacy label
# ============================================================
@admin_r.post("/labels/{label_id}/create-account")
async def admin_create_label_account(
    label_id: str,
    email: str = Form(...),
    pic_name: Optional[str] = Form(None),
    whatsapp: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    user: dict = Depends(require_admin),
):
    """Admin creates a user account for a legacy/unclaimed label.

    - Auto-generates a 12-char password if `password` is not provided.
    - Auto-generates MDA PDF (lifetime contract).
    - Returns the plaintext password ONCE for the admin to share with the label.
    """
    if user["role"] not in ("super_admin", "admin_release", "admin_support"):
        raise HTTPException(status_code=403, detail="Hanya Super Admin / Release / Support")

    label = await db.labels.find_one({"id": label_id})
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    if label.get("user_id"):
        raise HTTPException(status_code=400, detail="Label ini sudah punya akun user")

    email_clean = (email or "").lower().strip()
    if not email_clean or "@" not in email_clean:
        raise HTTPException(status_code=400, detail="Email tidak valid")
    if await db.users.find_one({"email": email_clean}):
        raise HTTPException(status_code=409, detail="Email sudah terdaftar")

    # Generate 12-char password if not supplied
    if not password:
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
        password = "".join(secrets.choice(alphabet) for _ in range(12))
    elif len(password) < 8:
        raise HTTPException(status_code=400, detail="Password minimal 8 karakter")

    user_id = new_id()
    pic = (pic_name or label.get("pic_name") or label.get("label_name") or "").strip() or "Label PIC"
    wa = (whatsapp or label.get("whatsapp") or "").strip()
    now = now_iso()
    await db.users.insert_one({
        "id": user_id,
        "name": pic,
        "email": email_clean,
        "password_hash": hash_password(password),
        "role": "label",
        "email_verified_at": now,  # admin-created → assume verified
        "status": "active",
        "created_at": now,
        "updated_at": now,
        "created_by_admin": user["id"],
    })
    await db.labels.update_one(
        {"id": label_id},
        {"$set": {
            "user_id": user_id,
            "email": email_clean,
            "pic_name": pic,
            "whatsapp": wa or label.get("whatsapp"),
            "account_status": "active",
            "mda_accepted_at": now,
            "updated_at": now,
        }},
    )

    # Auto-generate MDA PDF
    try:
        from .mda_generator import generate_mda_pdf
        legal_setting = await db.landing_settings.find_one({"key": "legal_entity"}, {"_id": 0, "value": 1})
        legal_entity = (legal_setting or {}).get("value") or {}
        merged = {**label, "user_id": user_id, "email": email_clean, "pic_name": pic, "whatsapp": wa or label.get("whatsapp")}
        contract_id = new_id()
        pdf_path = UPLOAD_DIR / "contract" / f"{contract_id}.pdf"
        generate_mda_pdf(merged, legal_entity, pdf_path)
        await db.contracts.insert_one({
            "id": contract_id,
            "label_id": label_id,
            "label_name": label.get("label_name"),
            "title": "Master Distribution Agreement",
            "kind": "mda",
            "file_url": f"/api/files/contract/{contract_id}.pdf",
            "filename": f"MDA-{(label.get('label_name') or '')[:20]}.pdf",
            "start_date": now[:10],
            "end_date": None,
            "is_lifetime": True,
            "status": "active",
            "notes": f"Auto-generated saat admin {user.get('email')} membuat akun untuk legacy label.",
            "accepted_at": now,
            "accepted_by_name": pic,
            "accepted_by_email": email_clean,
            "created_at": now,
            "updated_at": now,
            "created_by": user["id"],
        })
    except Exception as e:
        logger.warning("MDA generation on admin create-account failed: %s", e)

    await log_activity(
        user["id"], "create_label_account", "label", label_id,
        after={"user_id": user_id, "email": email_clean, "label_name": label.get("label_name")},
    )
    return {
        "ok": True,
        "user_id": user_id,
        "email": email_clean,
        "password": password,  # plaintext — show ONCE to admin
        "label_id": label_id,
        "label_name": label.get("label_name"),
        "warning": "Password ini hanya ditampilkan SEKALI. Salin sekarang untuk dibagikan ke label.",
    }


