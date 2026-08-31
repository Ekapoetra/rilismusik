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
    LabelProfileUpdate, BankAccountIn, BankAccountChangeRequestIn, BankAccountChangeActionIn,
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
from .admin_dashboard_service import build_admin_dashboard
from .admin_label_service import (
    change_label_email, create_label_account, revoke_label_account, update_label,
)
from .admin_reset_service import run_full_reset
from .dashboard_cache import recompute as recompute_dashboard_revenue, snapshot as dashboard_revenue_snapshot
from .bank_change_service import create_bank_change_request, review_bank_change_request

# =============================================================================
#                                ADMIN
# =============================================================================
admin_r = APIRouter(prefix="/admin", tags=["admin"])


@admin_r.get("/dashboard")
async def admin_dashboard(user: dict = Depends(require_admin)):
    return await build_admin_dashboard()


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
    await recompute_dashboard_revenue()
    cache = dashboard_revenue_snapshot()
    return {
        "ok": True,
        "total_eur": cache["total_eur"],
        "total_idr": cache["total_idr"],
        "computed_at": cache["computed_at"],
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
    from .balance_utils import compute_label_balance_snapshot
    balance = await compute_label_balance_snapshot(label_id=label_id, label=label)
    lifetime = {"royalty_idr": 0, "streams": 0, "first_period": None, "latest_period": None}
    async for row in db_bg.royalty_lines.aggregate([
        {"$match": {"label_id": label_id, "status": {"$in": ["pending", "available", "withdrawn"]}}},
        {"$group": {
            "_id": None,
            "royalty_idr": {"$sum": "$label_idr"},
            "streams": {"$sum": "$quantity"},
            "first_period": {"$min": "$period"},
            "latest_period": {"$max": "$period"},
        }},
    ], allowDiskUse=True):
        lifetime = {
            "royalty_idr": int(row.get("royalty_idr") or 0),
            "streams": int(row.get("streams") or 0),
            "first_period": row.get("first_period"),
            "latest_period": row.get("latest_period"),
        }
    withdrawn_paid = 0
    async for row in db_bg.withdraw_requests.aggregate([
        {"$match": {"label_id": label_id, "status": "paid"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount_idr"}}},
    ]):
        withdrawn_paid = int(row.get("total") or 0)
    financial_summary = {
        "total_royalty_idr": lifetime["royalty_idr"],
        "total_streams": lifetime["streams"],
        "withdrawn_paid_idr": withdrawn_paid,
        "withdraw_processing_idr": balance["balance_withdraw_requested_idr"],
        "available_idr": balance["balance_available_idr"],
        "pending_idr": balance["balance_pending_idr"],
        "total_unwithdrawn_idr": (
            balance["balance_pending_idr"]
            + balance["balance_available_idr"]
            + balance["balance_withdraw_requested_idr"]
        ),
        "first_period": lifetime["first_period"],
        "latest_period": lifetime["latest_period"],
        "last_withdrawn_period": balance["last_withdrawn_period"],
        "source": "royalty_lines_fifo",
    }
    return {
        "label": label,
        "bank_account": bank,
        "artists_count": artists_count,
        "releases_count": releases_count,
        "financial_summary": financial_summary,
    }


@admin_r.patch("/labels/{label_id}")
async def admin_update_label(label_id: str, body: LabelStatusUpdate, user: dict = Depends(require_admin)):
    return await update_label(label_id, body, user)


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
    items = await db.users.find(
        {"role": {"$in": list(ADMIN_ROLES)}, "status": {"$ne": "disabled"}},
        {"_id": 0, "password_hash": 0},
    ).sort("created_at", -1).to_list(500)
    return items


@admin_r.post("/admin-users")
async def admin_create_admin_user(body: AdminUserCreateIn, user: dict = Depends(require_super_admin)):
    email = body.email.lower().strip()
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing and not (existing.get("role") in ADMIN_ROLES and existing.get("status") == "disabled"):
        raise HTTPException(status_code=409, detail="Email sudah terdaftar")
    if existing:
        await db.users.update_one({"id": existing["id"]}, {
            "$set": {
                "name": body.name, "email": email, "password_hash": hash_password(body.password),
                "role": body.role, "status": "active", "updated_at": now_iso(),
            },
            "$inc": {"token_version": 1},
            "$unset": {"deleted_at": "", "deleted_by": ""},
        })
        await log_activity(user["id"], "restore_admin_user", "admin_user", existing["id"], after={"email": email, "role": body.role})
        return await db.users.find_one({"id": existing["id"]}, {"_id": 0, "password_hash": 0})
    user_id = new_id()
    doc = {
        "id": user_id,
        "name": body.name,
        "email": email,
        "password_hash": hash_password(body.password),
        "role": body.role,
        "email_verified_at": now_iso(),  # admins are auto-verified
        "status": "active",
        "token_version": 0,
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
    if user_id == user["id"] and body.get("status") == "suspended":
        raise HTTPException(status_code=400, detail="Anda tidak dapat menangguhkan akun sendiri")
    if target.get("role") == SUPER_ADMIN and body.get("role") not in (None, SUPER_ADMIN):
        active_supers = await db.users.count_documents({"role": SUPER_ADMIN, "status": {"$nin": ["disabled", "suspended"]}})
        if active_supers <= 1:
            raise HTTPException(status_code=400, detail="Minimal satu Super Admin aktif harus dipertahankan")
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
        update_doc: Dict[str, Any] = {"$set": upd}
        if "password_hash" in upd or upd.get("status") == "suspended":
            update_doc["$inc"] = {"token_version": 1}
        await db.users.update_one({"id": user_id}, update_doc)
    return await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})


@admin_r.delete("/admin-users/{user_id}")
async def admin_delete_admin_user(user_id: str, user: dict = Depends(require_super_admin)):
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Anda tidak dapat menghapus akun sendiri")
    target = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not target or target.get("role") not in ADMIN_ROLES or target.get("status") == "disabled":
        raise HTTPException(status_code=404, detail="Admin user tidak ditemukan")
    if target.get("role") == SUPER_ADMIN:
        active_supers = await db.users.count_documents({"role": SUPER_ADMIN, "status": {"$nin": ["disabled", "suspended"]}})
        if active_supers <= 1:
            raise HTTPException(status_code=400, detail="Super Admin terakhir tidak dapat dihapus")
    await db.users.update_one({"id": user_id}, {
        "$set": {"status": "disabled", "deleted_at": now_iso(), "deleted_by": user["id"], "updated_at": now_iso()},
        "$inc": {"token_version": 1},
    })
    await log_activity(user["id"], "delete_admin_user", "admin_user", user_id, before={"email": target.get("email"), "role": target.get("role")})
    return {"ok": True, "user_id": user_id}


@admin_r.get("/labels/{label_id}/bank-change-requests")
async def admin_list_bank_change_requests(label_id: str, user: dict = Depends(require_admin)):
    if user["role"] not in (SUPER_ADMIN, "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    return await db.bank_account_change_requests.find(
        {"label_id": label_id}, {"_id": 0},
    ).sort("created_at", -1).to_list(50)


@admin_r.post("/labels/{label_id}/bank-change-request")
async def admin_request_bank_change(
    label_id: str, body: BankAccountChangeRequestIn, user: dict = Depends(require_admin),
):
    if user["role"] not in (SUPER_ADMIN, "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    label = await db.labels.find_one({"id": label_id}, {"_id": 0})
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    document = await create_bank_change_request(
        label=label, payload=body.model_dump(), requester=user, approval_target="label",
    )
    await notify_many(
        await label_user_ids(label_id), "bank_change_requested",
        "Konfirmasi perubahan rekening",
        "Admin mengajukan perubahan data rekening. Tinjau dan setujui dari halaman Profil.",
        "/label/profile", {"request_id": document["id"], "label_id": label_id},
    )
    await log_activity(user["id"], "admin_request_bank_change", "bank_account", document["id"], after={"status": document["status"]})
    return document


@admin_r.post("/bank-account-change-requests/{request_id}/action")
async def admin_review_bank_change(
    request_id: str, body: BankAccountChangeActionIn, user: dict = Depends(require_admin),
):
    if user["role"] not in (SUPER_ADMIN, "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    document = await review_bank_change_request(
        request_id=request_id, action=body.action, note=body.note, reviewer=user,
        expected_status="pending_admin_approval",
    )
    await notify_many(
        await label_user_ids(document["label_id"]), "bank_change_reviewed",
        "Perubahan rekening diproses",
        f"Permintaan perubahan rekening Anda telah {body.action} oleh admin.",
        "/label/profile", {"request_id": request_id},
    )
    await log_activity(user["id"], f"admin_{body.action}_bank_change", "bank_account", request_id)
    return document


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
    return await create_label_account(
        label_id=label_id, email=email, pic_name=pic_name,
        whatsapp=whatsapp, password=password, user=user,
    )



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
    return await revoke_label_account(
        label_id=label_id, cascade_artists=cascade_artists,
        reason=reason, user=user,
    )


@admin_r.post("/labels/{label_id}/change-email")
async def admin_change_label_email(
    label_id: str,
    new_email: str = Form(...),
    send_notification: bool = Form(True, alias="notify"),
    user: dict = Depends(require_admin),
):
    return await change_label_email(
        label_id=label_id, new_email=new_email,
        send_notification=send_notification, user=user,
    )


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

    Phase 29.1 — async background job. On production the `royalty_lines`
    collection holds 3M+ rows: a synchronous `delete_many({})` through the
    CSOT-capped `db` client (timeoutMS=10000) fails mid-way and the 120s
    ingress timeout kills the request. This endpoint now returns a `job_id`
    immediately; the wipe runs in the background using `drop_collection`
    (instant regardless of row count) via `db_bg`, then re-seeds indexes +
    admins and clears all dashboard caches. Poll
    `GET /api/admin/migrate/jobs/{job_id}`.
    """
    if confirm != "RESET-ALL-DATA":
        raise HTTPException(
            status_code=400,
            detail="Konfirmasi tidak cocok. Ketik tepat: RESET-ALL-DATA",
        )
    job_id = new_id()
    await db.migrate_jobs.insert_one({
        "id": job_id,
        "kind": "reset_all_data",
        "status": "queued",
        "submitted_by": user["id"],
        "submitted_at": now_iso(),
        "updated_at": now_iso(),
        "options": {"delete_r2_files": bool(delete_r2_files)},
    })
    import asyncio as _aio
    _aio.create_task(run_full_reset(
        job_id=job_id, delete_r2_files=bool(delete_r2_files),
        user_id=user["id"], user_email=user["email"],
    ))
    return {"ok": True, "job_id": job_id, "status": "queued", "kind": "reset_all_data"}


