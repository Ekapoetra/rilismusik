"""Admin console + blacklist router."""
from fastapi import APIRouter, HTTPException, Request, Response, Depends, UploadFile, File, Form, Query
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timezone, timedelta, date
import os
import csv
import io
import shutil
import secrets
import re
from pymongo.collation import Collation

from .deps import (
    db, db_bg, logger, UPLOAD_DIR,
    get_current_user, require_label, require_artist, require_admin, require_super_admin,
    assert_admin_permission,
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
from .dashboard_cache import recompute as recompute_dashboard_revenue, snapshot as dashboard_revenue_snapshot
from .bank_change_service import create_bank_change_request, review_bank_change_request
from .payment_admin_service import list_admin_payments
from .finance_reporting import payment_income_summary
from .release_deletion_service import ReleaseDeletionResult, delete_release_record

# =============================================================================
#                                ADMIN
# =============================================================================
admin_r = APIRouter(prefix="/admin", tags=["admin"])


@admin_r.get("/dashboard")
async def admin_dashboard(user: dict = Depends(require_admin)):
    return await build_admin_dashboard()


@admin_r.get("/action-center")
async def admin_action_center(user: dict = Depends(require_admin)):
    """Prioritized list of unresolved operational items for the Action Center."""
    import asyncio
    from .payment_admin_service import count_actionable_payments

    async def _oldest(coll, filt, field):
        doc = await db[coll].find_one(filt, {"_id": 0, field: 1}, sort=[(field, 1)])
        return doc.get(field) if doc else None

    counts = await asyncio.gather(
        db.releases.count_documents({"status": "under_review"}),
        db.kyc_documents.count_documents({"status": "pending_review", "is_current": True}),
        db.withdraw_requests.count_documents({"status": "requested"}),
        count_actionable_payments(),
        db.support_tickets.count_documents({"status": {"$nin": ["done", "rejected"]}}),
        db.users.count_documents({"role": "label", "claim_status": "pending_link"}),
    )
    oldest = await asyncio.gather(
        _oldest("releases", {"status": "under_review"}, "submitted_at"),
        _oldest("kyc_documents", {"status": "pending_review", "is_current": True}, "uploaded_at"),
        _oldest("withdraw_requests", {"status": "requested"}, "created_at"),
        _oldest("support_tickets", {"status": {"$nin": ["done", "rejected"]}}, "created_at"),
        _oldest("users", {"role": "label", "claim_status": "pending_link"}, "claim_requested_at"),
    )
    c_rel, c_kyc, c_wd, c_pay, c_tk, c_claim = counts
    o_rel, o_kyc, o_wd, o_tk, o_claim = oldest
    defs = [
        {"key": "withdrawals", "count": c_wd, "priority": "high", "permission": "withdraw.manage", "oldest_at": o_wd,
         "title": "Penarikan menunggu verifikasi", "cta": "Tinjau", "link": "/admin/withdraw", "icon": "Banknote",
         "description": f"{c_wd} permintaan penarikan dana perlu diverifikasi & dibayar."},
        {"key": "payments", "count": c_pay, "priority": "high", "permission": "payments.manage", "oldest_at": None,
         "title": "Pembayaran perlu ditindaklanjuti", "cta": "Proses", "link": "/admin/payments?needs_action=true", "icon": "CreditCard",
         "description": f"{c_pay} pembayaran menunggu tindakan operasional."},
        {"key": "releases", "count": c_rel, "priority": "normal", "permission": "releases.review", "oldest_at": o_rel,
         "title": "Rilisan menunggu review", "cta": "Review", "link": "/admin/releases?status=under_review", "icon": "Disc3",
         "description": f"{c_rel} rilisan siap diperiksa untuk distribusi."},
        {"key": "kyc", "count": c_kyc, "priority": "normal", "permission": "kyc.view", "oldest_at": o_kyc,
         "title": "Verifikasi Akun menunggu review", "cta": "Review", "link": "/admin/kyc", "icon": "ShieldCheck",
         "description": f"{c_kyc} identitas label perlu diperiksa."},
        {"key": "tickets", "count": c_tk, "priority": "normal", "permission": "support.view", "oldest_at": o_tk,
         "title": "Tiket bantuan aktif", "cta": "Buka", "link": "/admin/tickets", "icon": "MessageSquare",
         "description": f"{c_tk} tiket bantuan menunggu respons."},
        {"key": "claims", "count": c_claim, "priority": "normal", "permission": "migration.view", "oldest_at": o_claim,
         "title": "Klaim akun lama", "cta": "Tinjau", "link": "/admin/migrate?tab=claims", "icon": "DatabaseZap",
         "description": f"{c_claim} permintaan klaim label lama menunggu dihubungkan."},
    ]
    rank = {"critical": 0, "high": 1, "normal": 2, "low": 3}
    items = [d for d in defs if (d["count"] or 0) > 0]
    items.sort(key=lambda d: (rank.get(d["priority"], 9), d.get("oldest_at") or "9999"))
    return {"items": items}


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
async def admin_list_labels(
    user: dict = Depends(require_admin), q: Optional[str] = None, status: Optional[str] = None,
    sort_by: Literal["balance", "label", "email"] = "balance",
    sort_dir: Literal["asc", "desc"] = "desc",
):
    filt: Dict[str, Any] = {}
    if status:
        filt["account_status"] = status
    if q:
        filt["label_name"] = {"$regex": re.escape(q.strip()), "$options": "i"}
    result_limit = 200 if q else 1000
    sort_field = {"balance": "balance_available_idr", "label": "label_name", "email": "email"}[sort_by]
    direction = 1 if sort_dir == "asc" else -1
    sort_spec = [(sort_field, direction)]
    if sort_field != "label_name":
        sort_spec.append(("label_name", 1))
    cursor = db.labels.find(filt, {"_id": 0}).sort(sort_spec)
    if sort_by in {"label", "email"}:
        cursor = cursor.collation(Collation(locale="en", strength=2, numericOrdering=True))
    items = await cursor.to_list(result_limit)
    for item in items:
        item["stored_balance_available_idr"] = max(int(item.get("balance_available_idr") or 0), 0)
        item["balance_available_idr"] = item["stored_balance_available_idr"]
        item["logo_url"] = f"/api/files/{item['logo_storage_key']}" if item.get("logo_storage_key") else None
    return items


@admin_r.post("/labels/balance-refresh")
async def admin_start_label_balance_refresh(
    force: bool = False, user: dict = Depends(require_admin),
):
    from .label_balance_snapshot import start_label_balance_snapshot_refresh
    return await start_label_balance_snapshot_refresh(force=force, reason=f"admin_labels:{user['id']}")


@admin_r.get("/labels/balance-refresh/status")
async def admin_label_balance_refresh_status(user: dict = Depends(require_admin)):
    from .label_balance_snapshot import snapshot_status
    return await snapshot_status()


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
    from .royalty_adjustment_balance import ADJUSTMENT_TYPE
    adjustment_total = 0
    async for row in db_bg.balance_transactions.aggregate([
        {"$match": {"label_id": label_id, "type": ADJUSTMENT_TYPE, "status": "active"}},
        {"$group": {"_id": None, "amount": {"$sum": "$amount_idr"}}},
    ]):
        adjustment_total = int(row["amount"])
    financial_summary["total_royalty_idr"] += adjustment_total
    financial_summary["admin_adjustment_total_idr"] = adjustment_total
    financial_summary["source"] = "royalty_lines_and_adjustments"
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


from .label_package_service import LabelPackageUpdate, LabelPackageResult, change_label_package


@admin_r.patch("/labels/{label_id}/package", response_model=LabelPackageResult)
async def admin_update_label_package(label_id: str, body: LabelPackageUpdate, user: dict = Depends(require_admin)):
    return await change_label_package(label_id, body, user)


from .release_list_metadata import ReleaseListItem, enrich_release_list


@admin_r.get("/releases", response_model=List[ReleaseListItem])
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
    await enrich_release_list(db, items)
    status_order = [
        "submitted", "awaiting_payment", "paid", "under_review", "need_revision",
        "approved", "delivered", "draft", "live",
    ]
    status_rank = {value: index for index, value in enumerate(status_order)}
    items.sort(key=lambda item: item.get("submitted_at") or item.get("updated_at") or item.get("created_at") or "", reverse=True)
    items.sort(key=lambda item: status_rank.get(item.get("status"), len(status_order)))
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


@admin_r.delete("/releases/{release_id}", response_model=ReleaseDeletionResult)
async def admin_delete_release(release_id: str, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "releases.review")
    return await delete_release_record(release_id, user["id"])


@admin_r.get("/payments")
async def admin_list_payments(
    user: dict = Depends(require_admin), status: Optional[str] = None,
    ptype: Optional[str] = None, needs_action: bool = False,
):
    return await list_admin_payments(status=status, payment_type=ptype, needs_action=needs_action)


@admin_r.get("/payments/summary")
async def admin_payment_income_summary(
    year: int = Query(..., ge=2000, le=2100), month: int = Query(..., ge=1, le=12),
    user: dict = Depends(require_admin),
):
    return await payment_income_summary(year=year, month=month)


@admin_r.get("/admin-users")
async def admin_list_admin_users(user: dict = Depends(require_admin)):
    assert_admin_permission(user, "access.users.view")
    items = await db.users.find(
        {"$or": [{"role": {"$in": list(ADMIN_ROLES)}}, {"admin_role_id": {"$exists": True, "$ne": None}}], "status": {"$ne": "disabled"}},
        {"_id": 0, "password_hash": 0},
    ).sort("created_at", -1).to_list(500)
    role_ids = list({item.get("admin_role_id") or item.get("role") for item in items})
    roles = await db.admin_roles.find({"$or": [{"id": {"$in": role_ids}}, {"key": {"$in": role_ids}}]}, {"_id": 0}).to_list(500)
    role_map = {key: role for role in roles for key in (role.get("id"), role.get("key")) if key}
    for item in items:
        role = role_map.get(item.get("admin_role_id") or item.get("role")) or {}
        item["role_name"] = role.get("name") or item.get("role")
    return items


async def _resolve_admin_role(role_ref: Optional[str], actor: dict) -> Dict[str, Any]:
    ref = (role_ref or "admin_release").strip()
    role = await db.admin_roles.find_one({"$or": [{"id": ref}, {"key": ref}], "active": {"$ne": False}}, {"_id": 0})
    if not role:
        raise HTTPException(status_code=400, detail="Role admin tidak valid atau sedang nonaktif")
    if role.get("key") == SUPER_ADMIN and actor.get("role") != SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Hanya Super Admin yang dapat menetapkan role Super Admin")
    return {"role": role.get("key") if role.get("builtin") else "admin_custom", "admin_role_id": role["id"], "role_name": role.get("name")}


@admin_r.post("/admin-users")
async def admin_create_admin_user(body: AdminUserCreateIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "access.users.manage")
    email = body.email.lower().strip()
    assignment = await _resolve_admin_role(body.admin_role_id or body.role, user)
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing and not ((existing.get("role") in ADMIN_ROLES or existing.get("admin_role_id")) and existing.get("status") == "disabled"):
        raise HTTPException(status_code=409, detail="Email sudah terdaftar")
    if existing:
        await db.users.update_one({"id": existing["id"]}, {
            "$set": {
                "name": body.name, "email": email, "password_hash": hash_password(body.password),
                **assignment, "status": "active", "updated_at": now_iso(),
            },
            "$inc": {"token_version": 1},
            "$unset": {"deleted_at": "", "deleted_by": ""},
        })
        await log_activity(user["id"], "restore_admin_user", "admin_user", existing["id"], after={"email": email, **assignment})
        return await db.users.find_one({"id": existing["id"]}, {"_id": 0, "password_hash": 0})
    user_id = new_id()
    doc = {
        "id": user_id,
        "name": body.name,
        "email": email,
        "password_hash": hash_password(body.password),
        **assignment,
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
async def admin_update_admin_user(user_id: str, body: Dict[str, Any], user: dict = Depends(require_admin)):
    assert_admin_permission(user, "access.users.manage")
    target = await db.users.find_one({"id": user_id})
    if not target or not (target.get("role") in ADMIN_ROLES or target.get("admin_role_id")):
        raise HTTPException(status_code=404, detail="Admin user tidak ditemukan")
    upd = {}
    if user_id == user["id"] and body.get("status") == "suspended":
        raise HTTPException(status_code=400, detail="Anda tidak dapat menangguhkan akun sendiri")
    requested_role = body.get("admin_role_id") or body.get("role")
    role_assignment = await _resolve_admin_role(requested_role, user) if requested_role else None
    if target.get("role") == SUPER_ADMIN and role_assignment and role_assignment.get("role") != SUPER_ADMIN:
        active_supers = await db.users.count_documents({"role": SUPER_ADMIN, "status": {"$nin": ["disabled", "suspended"]}})
        if active_supers <= 1:
            raise HTTPException(status_code=400, detail="Minimal satu Super Admin aktif harus dipertahankan")
    if role_assignment:
        upd.update(role_assignment)
    if "status" in body and body["status"] in ("active", "suspended"):
        upd["status"] = body["status"]
    if "name" in body:
        upd["name"] = body["name"]
    if "password" in body and body["password"]:
        upd["password_hash"] = hash_password(body["password"])
    if upd:
        upd["updated_at"] = now_iso()
        update_doc: Dict[str, Any] = {"$set": upd}
        if "password_hash" in upd or upd.get("status") == "suspended" or role_assignment:
            update_doc["$inc"] = {"token_version": 1}
        await db.users.update_one({"id": user_id}, update_doc)
    return await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})


@admin_r.delete("/admin-users/{user_id}")
async def admin_delete_admin_user(user_id: str, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "access.users.manage")
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Anda tidak dapat menghapus akun sendiri")
    target = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not target or not (target.get("role") in ADMIN_ROLES or target.get("admin_role_id")) or target.get("status") == "disabled":
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
    user_ids = list({item.get("user_id") for item in items if item.get("user_id")})
    users = await db.users.find(
        {"id": {"$in": user_ids}},
        {"_id": 0, "id": 1, "name": 1, "username": 1},
    ).to_list(len(user_ids) or 1)
    user_names = {
        item["id"]: item.get("name") or item.get("username") or item["id"]
        for item in users
    }
    for item in items:
        actor_id = item.get("user_id")
        item["user_name"] = user_names.get(actor_id, actor_id or "Sistem")
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
    assert_admin_permission(user, "labels.manage")
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




