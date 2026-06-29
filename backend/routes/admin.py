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
    db, db_bg, logger, UPLOAD_DIR,
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


# In-memory dashboard cache. Lifetime is module-local so it resets cleanly on
# every pod restart / hot reload. Re-aggregating ~1M royalty_lines on every
# dashboard load was the dominant latency in production (3-10s even with db_bg).
# Refresh strategy: stale-while-revalidate — if cache is older than
# DASHBOARD_REVENUE_TTL_SEC, recompute in the background but immediately serve
# the cached value to keep the UI responsive.
import time as _time
DASHBOARD_REVENUE_TTL_SEC = 60  # cache lifetime
_dashboard_revenue_cache: Dict[str, Any] = {"total_eur": 0, "total_idr": 0, "computed_at": 0.0, "refreshing": False}


async def _recompute_revenue_cache() -> None:
    """Recompute the (total_eur, total_idr) aggregate over royalty_lines and
    store in module-local + Mongo (`metrics_cache.dashboard_revenue`) so a
    fresh pod warm-start can pick it up without a 1M-row scan.
    """
    _dashboard_revenue_cache["refreshing"] = True
    try:
        pipeline = [
            {"$group": {"_id": None, "total_eur": {"$sum": "$revenue_eur"}, "total_idr": {"$sum": "$label_idr"}}},
        ]
        total_eur = 0
        total_idr = 0
        async for r in db_bg.royalty_lines.aggregate(pipeline, allowDiskUse=True):
            total_eur = r.get("total_eur", 0) or 0
            total_idr = r.get("total_idr", 0) or 0
        now_ts = _time.time()
        _dashboard_revenue_cache.update({"total_eur": total_eur, "total_idr": total_idr, "computed_at": now_ts})
        # Mongo persist (small upsert, safe via db_bg)
        try:
            await db_bg.metrics_cache.update_one(
                {"_id": "dashboard_revenue"},
                {"$set": {"total_eur": total_eur, "total_idr": total_idr, "computed_at": now_ts}},
                upsert=True,
            )
        except Exception as e:
            logger.warning("[DASHBOARD CACHE] mongo persist failed (non-fatal): %s", e)
    except Exception as e:
        logger.warning("[DASHBOARD CACHE] recompute failed (non-fatal): %s", e)
    finally:
        _dashboard_revenue_cache["refreshing"] = False


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

    # Revenue totals — served from cache (stale-while-revalidate). On a cold
    # cache we first warm from Mongo's `metrics_cache.dashboard_revenue` doc
    # (carried across restarts), then schedule an async refresh if needed.
    now_ts = _time.time()
    if _dashboard_revenue_cache["computed_at"] == 0.0:
        try:
            persisted = await db.metrics_cache.find_one({"_id": "dashboard_revenue"})
            if persisted:
                _dashboard_revenue_cache.update({
                    "total_eur": persisted.get("total_eur", 0) or 0,
                    "total_idr": persisted.get("total_idr", 0) or 0,
                    "computed_at": persisted.get("computed_at", 0) or 0,
                })
        except Exception as e:
            logger.warning("[DASHBOARD CACHE] mongo warm-load failed: %s", e)

    cache_age = now_ts - _dashboard_revenue_cache["computed_at"]
    if _dashboard_revenue_cache["computed_at"] == 0.0:
        # First-ever load: compute synchronously so the value isn't 0
        await _recompute_revenue_cache()
    elif cache_age > DASHBOARD_REVENUE_TTL_SEC and not _dashboard_revenue_cache["refreshing"]:
        # Stale → schedule background refresh and return cached value immediately
        import asyncio
        asyncio.create_task(_recompute_revenue_cache())

    total_eur = _dashboard_revenue_cache["total_eur"]
    total_idr = _dashboard_revenue_cache["total_idr"]

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
        "revenue_cache_age_sec": int(cache_age) if _dashboard_revenue_cache["computed_at"] else None,
        "last_csv_import": last_csv,
    }


@admin_r.post("/dashboard/refresh-revenue")
async def admin_refresh_revenue(user: dict = Depends(require_admin)):
    """Force a sync recompute of the dashboard revenue totals.

    Restricted to **super_admin** and **admin_finance** roles only — recomputing
    is a heavy aggregate over 1M+ rows that should not be triggerable by
    release / marketing / support admins. Other admin roles get 403.

    Useful after a fresh CSV import / large publish — admin can hit this once
    to repopulate the cache without waiting for the 60s TTL.
    """
    if user.get("role") not in (SUPER_ADMIN, "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Super Admin atau Admin Finance yang bisa refresh revenue")
    await _recompute_revenue_cache()
    return {
        "ok": True,
        "total_eur": _dashboard_revenue_cache["total_eur"],
        "total_idr": _dashboard_revenue_cache["total_idr"],
        "computed_at": _dashboard_revenue_cache["computed_at"],
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
async def admin_list_releases(
    user: dict = Depends(require_admin),
    status: Optional[str] = None,
    q: Optional[str] = None,
    period_from: Optional[str] = Query(None, description="Inclusive YYYY-MM"),
    period_to: Optional[str] = Query(None, description="Inclusive YYYY-MM"),
):
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
    # Phase 21: rollup revenue per release from royalty_lines
    from .revenue_rollup import rollup_revenue_by_id
    rollup = await rollup_revenue_by_id(
        field="release_id",
        ids=[i["id"] for i in items],
        period_from=period_from,
        period_to=period_to,
    )
    for it in items:
        it["label_name"] = name_map.get(it["label_id"])
        r = rollup.get(it["id"], {})
        it["revenue_eur"] = r.get("revenue_eur", 0)
        it["revenue_idr"] = r.get("revenue_idr", 0)
        it["royalty_lines_count"] = r.get("lines", 0)
        it["last_active_period"] = r.get("last_period")
        it["first_active_period"] = r.get("first_period")
    return items


@admin_r.get("/artists")
async def admin_list_artists(
    user: dict = Depends(require_admin),
    q: Optional[str] = None,
    period_from: Optional[str] = Query(None, description="Inclusive YYYY-MM"),
    period_to: Optional[str] = Query(None, description="Inclusive YYYY-MM"),
):
    filt: Dict[str, Any] = {}
    if q:
        filt["artist_name"] = {"$regex": q, "$options": "i"}
    items = await db.artists.find(filt, {"_id": 0}).sort("created_at", -1).to_list(1000)
    label_ids = list({i["label_id"] for i in items if i.get("label_id")})
    labels = await db.labels.find({"id": {"$in": label_ids}}, {"_id": 0, "id": 1, "label_name": 1}).to_list(1000)
    name_map = {lab["id"]: lab["label_name"] for lab in labels}
    # Phase 21: rollup revenue per artist from royalty_lines
    from .revenue_rollup import rollup_revenue_by_id
    rollup = await rollup_revenue_by_id(
        field="artist_id",
        ids=[i["id"] for i in items],
        period_from=period_from,
        period_to=period_to,
    )
    for it in items:
        it["label_name"] = name_map.get(it["label_id"])
        r = rollup.get(it["id"], {})
        it["revenue_eur"] = r.get("revenue_eur", 0)
        it["revenue_idr"] = r.get("revenue_idr", 0)
        it["royalty_lines_count"] = r.get("lines", 0)
        it["last_active_period"] = r.get("last_period")
        it["first_active_period"] = r.get("first_period")
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
        from .mda_generator import generate_mda_pdf_bytes
        import storage_service
        legal_setting = await db.landing_settings.find_one({"key": "legal_entity"}, {"_id": 0, "value": 1})
        legal_entity = (legal_setting or {}).get("value") or {}
        merged = {**label, "user_id": user_id, "email": email_clean, "pic_name": pic, "whatsapp": wa or label.get("whatsapp")}
        contract_id = new_id()
        pdf_bytes = generate_mda_pdf_bytes(merged, legal_entity)
        r2_key = f"contract/{contract_id}.pdf"
        await storage_service.upload_bytes(key=r2_key, data=pdf_bytes, content_type="application/pdf")
        await db.contracts.insert_one({
            "id": contract_id,
            "label_id": label_id,
            "label_name": label.get("label_name"),
            "title": "Master Distribution Agreement",
            "kind": "mda",
            "file_url": f"/api/files/{r2_key}",
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



# ============================================================
# Phase 25 — Revoke account access & change email
# ============================================================
@admin_r.post("/labels/{label_id}/revoke-account")
async def admin_revoke_label_account(
    label_id: str,
    cascade_artists: bool = Form(False),
    reason: str = Form(""),
    user: dict = Depends(require_admin),
):
    """Revoke login access for a label's PIC user (and optionally cascade to
    artist sub-accounts) WITHOUT deleting label/release/royalty/contract data.

    The label's `user_id` is cleared so admin can later create a fresh account
    via `/labels/{id}/create-account` with a new email — exactly the "transfer
    ownership" workflow the user asked for.

    Steps:
      1. Lookup current user attached to the label.
      2. Increment `token_version` on that user → instantly invalidates all
         JWTs (refresh + access). The user remains in `users` collection
         (for audit) but with status='disabled'.
      3. Null out `labels.user_id` so the label is "free" to receive a new
         account.
      4. If `cascade_artists=true`, also disable + bump token_version of every
         artist user whose row references this label_id.
    """
    if user["role"] not in ("super_admin", "admin_support", "admin_release"):
        raise HTTPException(status_code=403, detail="Hanya Super Admin / Support / Release")

    label = await db.labels.find_one({"id": label_id})
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    current_user_id = label.get("user_id")
    if not current_user_id:
        raise HTTPException(status_code=400, detail="Label ini belum punya akun user — gunakan 'Buat Akun' untuk membuat.")

    target = await db.users.find_one({"id": current_user_id})
    if not target:
        # Stale ref — just clear and exit
        await db.labels.update_one({"id": label_id}, {"$set": {"user_id": None, "account_status": "no_account", "updated_at": now_iso()}})
        return {"ok": True, "label_id": label_id, "warning": "User account stale-reference dibersihkan."}

    # Disable + invalidate all sessions for the label PIC user
    await db.users.update_one(
        {"id": current_user_id},
        {"$set": {
            "status": "disabled",
            "disabled_at": now_iso(),
            "disabled_by": user["id"],
            "disabled_reason": reason or "Akses dicabut oleh admin",
            "updated_at": now_iso(),
        }, "$inc": {"token_version": 1}},
    )

    # Free up the label so admin can create a new account
    await db.labels.update_one(
        {"id": label_id},
        {"$set": {
            "user_id": None,
            "account_status": "no_account",
            "previous_account_email": target.get("email"),
            "previous_account_revoked_at": now_iso(),
            "updated_at": now_iso(),
        }},
    )

    cascade_count = 0
    if cascade_artists:
        # Find all artist users tied to this label
        artist_docs = await db.artists.find({"label_id": label_id}, {"_id": 0, "user_id": 1}).to_list(2000)
        artist_user_ids = [a["user_id"] for a in artist_docs if a.get("user_id")]
        if artist_user_ids:
            res = await db.users.update_many(
                {"id": {"$in": artist_user_ids}},
                {"$set": {
                    "status": "disabled",
                    "disabled_at": now_iso(),
                    "disabled_by": user["id"],
                    "disabled_reason": "Cascade dari label revoke",
                    "updated_at": now_iso(),
                }, "$inc": {"token_version": 1}},
            )
            cascade_count = res.modified_count

    await log_activity(
        user["id"], "revoke_label_account", "label", label_id,
        before={"user_id": current_user_id, "email": target.get("email")},
        after={"cascade_artists": cascade_artists, "artists_disabled": cascade_count, "reason": reason},
    )

    return {
        "ok": True,
        "label_id": label_id,
        "label_name": label.get("label_name"),
        "revoked_email": target.get("email"),
        "artists_disabled": cascade_count,
        "next_step": "Akun bisa dibuat ulang dengan email baru via 'Buat Akun' di Label Management.",
    }


@admin_r.post("/labels/{label_id}/change-email")
async def admin_change_label_email(
    label_id: str,
    new_email: str = Form(...),
    notify: bool = Form(True),
    user: dict = Depends(require_admin),
):
    """Change the email address of a label's PIC user account. Optionally
    sends notification to BOTH old and new email addresses so the label
    knows the change happened.

    Bumps `token_version` so all existing sessions on the old email are
    invalidated — the label must log in again with the new email.
    """
    if user["role"] not in ("super_admin", "admin_support", "admin_release"):
        raise HTTPException(status_code=403, detail="Hanya Super Admin / Support / Release")

    label = await db.labels.find_one({"id": label_id})
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    current_user_id = label.get("user_id")
    if not current_user_id:
        raise HTTPException(status_code=400, detail="Label belum punya akun — gunakan 'Buat Akun' dulu.")

    new_email_clean = (new_email or "").lower().strip()
    if not new_email_clean or "@" not in new_email_clean:
        raise HTTPException(status_code=400, detail="Email baru tidak valid")
    # Uniqueness check — except if same email
    existing = await db.users.find_one({"email": new_email_clean})
    if existing and existing.get("id") != current_user_id:
        raise HTTPException(status_code=409, detail="Email ini sudah dipakai akun lain")

    target = await db.users.find_one({"id": current_user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User account tidak ditemukan (stale ref)")
    old_email = target.get("email")
    if old_email == new_email_clean:
        raise HTTPException(status_code=400, detail="Email baru sama dengan email lama")

    # Update user + label rows; bump token_version to force re-login.
    await db.users.update_one(
        {"id": current_user_id},
        {"$set": {
            "email": new_email_clean,
            "email_changed_at": now_iso(),
            "email_changed_by": user["id"],
            "updated_at": now_iso(),
        }, "$inc": {"token_version": 1}},
    )
    await db.labels.update_one(
        {"id": label_id},
        {"$set": {"email": new_email_clean, "updated_at": now_iso()}},
    )

    notify_sent = {"old": False, "new": False}
    if notify:
        try:
            from email_service import send_email
            label_name = label.get("label_name", "label Anda")
            # Notify OLD email — security warning
            html_old = f"""
            <p>Hai Tim {label_name},</p>
            <p>Email akun login Anda di <b>RILIS MUSIK</b> baru saja diubah dari <b>{old_email}</b> menjadi <b>{new_email_clean}</b> oleh admin.</p>
            <p>Jika ini bukan Anda atau tidak sesuai kesepakatan, segera hubungi tim support RILIS MUSIK.</p>
            <p>Salam,<br/>Tim RILIS MUSIK</p>
            """
            try:
                await send_email(to=old_email, subject="Pemberitahuan: Email akun RILIS MUSIK Anda telah diubah", html=html_old)
                notify_sent["old"] = True
            except Exception as e:
                logger.warning("[CHANGE-EMAIL] notify old %s failed: %s", old_email, e)
            # Welcome NEW email
            html_new = f"""
            <p>Hai Tim {label_name},</p>
            <p>Akun RILIS MUSIK Anda kini terhubung dengan email <b>{new_email_clean}</b>.</p>
            <p>Silakan login menggunakan email ini. Password tidak berubah.</p>
            <p>Jika Anda belum punya akses atau password, hubungi admin RILIS MUSIK.</p>
            <p>Salam,<br/>Tim RILIS MUSIK</p>
            """
            try:
                await send_email(to=new_email_clean, subject="Selamat datang — email baru terhubung ke akun RILIS MUSIK", html=html_new)
                notify_sent["new"] = True
            except Exception as e:
                logger.warning("[CHANGE-EMAIL] notify new %s failed: %s", new_email_clean, e)
        except Exception as e:
            logger.exception("[CHANGE-EMAIL] notify wrapper failed: %s", e)

    await log_activity(
        user["id"], "change_label_email", "label", label_id,
        before={"email": old_email}, after={"email": new_email_clean, "notify_sent": notify_sent},
    )

    return {
        "ok": True,
        "label_id": label_id,
        "old_email": old_email,
        "new_email": new_email_clean,
        "notify_sent": notify_sent,
        "warning": "Semua sesi login lama akan terputus. Label harus login ulang.",
    }


# ============================================================
# DANGER: Full Production Reset (Super Admin only)
# ============================================================
@admin_r.post("/admin/danger/reset-all-data")
async def admin_reset_all_data(
    confirm: str = Form(...),
    delete_r2_files: bool = Form(True),
    user: dict = Depends(require_super_admin),
):
    """⚠️ DESTRUCTIVE: wipe ALL business data so the system can be tested
    from a clean slate. Preserves only:
      - Admin users (any role in ADMIN_ROLES + super_admin)
      - CMS landing settings (hero, pricing, FAQ, footer, legal entity)
      - Database indexes

    Deletes (across all 22 collections):
      - All non-admin users (labels & artists)
      - All labels, releases, tracks, artists
      - All royalty data (imports, lines, percentage history, balance txns)
      - All contracts, withdraws, tickets, comments
      - All payments, subscriptions, WAMI orders
      - All notifications, activity logs, login attempts
      - All email/password tokens, bank accounts
    Optionally deletes ALL files in the R2 bucket (cover/, audio/, contract/,
    ticket/, landing/, smoketest/) — pass `delete_r2_files=False` to keep them.

    Requires `confirm='RESET-ALL-DATA'` to proceed. Super Admin only.
    """
    if confirm != "RESET-ALL-DATA":
        raise HTTPException(
            status_code=400,
            detail="Konfirmasi tidak cocok. Ketik tepat: RESET-ALL-DATA",
        )

    report: Dict[str, int] = {}

    # 1) Wipe non-admin users (keep admins)
    res = await db.users.delete_many({"role": {"$nin": list(ADMIN_ROLES) + [SUPER_ADMIN]}})
    report["users_deleted_non_admin"] = res.deleted_count

    # 2) Wipe ALL business data
    business_collections = [
        "labels", "releases", "tracks", "artists", "bank_accounts",
        "royalty_imports", "royalty_lines", "royalty_percentage_history",
        "balance_transactions",
        "withdraw_requests",
        "contracts",
        "support_tickets", "ticket_comments",
        "payments",
        "wami_orders",
        "notifications", "activity_logs", "login_attempts",
        "email_verification_tokens", "password_reset_tokens",
    ]
    for col in business_collections:
        res = await db[col].delete_many({})
        report[col] = res.deleted_count

    # 3) Optionally wipe R2 bucket (all user-uploaded files)
    if delete_r2_files:
        try:
            import storage_service
            if storage_service.is_configured():
                client = storage_service._client()
                bucket = storage_service.R2_BUCKET
                deleted = 0
                # Paginate through all objects and delete in batches of 1000
                paginator = client.get_paginator("list_objects_v2")
                for page in paginator.paginate(Bucket=bucket):
                    objs = page.get("Contents") or []
                    if not objs:
                        continue
                    client.delete_objects(
                        Bucket=bucket,
                        Delete={"Objects": [{"Key": o["Key"]} for o in objs]},
                    )
                    deleted += len(objs)
                report["r2_objects_deleted"] = deleted
        except Exception as e:
            logger.exception("R2 cleanup during reset failed: %s", e)
            report["r2_cleanup_error"] = str(e)

    # 4) Re-seed defaults (idempotent)
    from .seed import seed_indexes_and_admins
    try:
        await seed_indexes_and_admins()
        report["reseed"] = "ok"
    except Exception as e:
        logger.exception("Reseed after reset failed: %s", e)
        report["reseed_error"] = str(e)

    await log_activity(user["id"], "danger_reset_all_data", "system", "global", after=report)
    logger.warning("[DANGER] Full data reset by super_admin %s: %s", user["email"], report)
    return {"ok": True, "report": report}


