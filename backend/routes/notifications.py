"""In-app notifications router."""
from fastapi import APIRouter, HTTPException, Request, Response, Depends, UploadFile, File, Form, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta, date
import os
import csv
import io
import shutil
import secrets
import re

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
from .admin_permission_service import assert_admin_permission

# =============================================================================
#                              NOTIFICATIONS
# =============================================================================
notif_r = APIRouter(prefix="/notifications", tags=["notifications"])


def _notification_filter(user_id: str, read_status: str, search: Optional[str], ntype: Optional[str], date_from: Optional[date], date_to: Optional[date]) -> Dict[str, Any]:
    filt: Dict[str, Any] = {"user_id": user_id}
    if read_status == "unread": filt["read_at"] = None
    elif read_status == "read": filt["read_at"] = {"$ne": None}
    if search:
        term = re.escape(search.strip())
        filt["$or"] = [{"title": {"$regex": term, "$options": "i"}}, {"body": {"$regex": term, "$options": "i"}}, {"type": {"$regex": term, "$options": "i"}}]
    if ntype: filt["type"] = ntype
    if date_from or date_to:
        created: Dict[str, str] = {}
        if date_from: created["$gte"] = f"{date_from.isoformat()}T00:00:00"
        if date_to: created["$lte"] = f"{date_to.isoformat()}T23:59:59.999999+00:00"
        filt["created_at"] = created
    return filt


def _priority_for_type(ntype: str) -> str:
    """Derive notification priority at read-time (no migration needed)."""
    t = (ntype or "").lower()
    urgent = ("urgent", "suspend", "security", "not_live", "reject", "takedown", "expired", "overdue", "fraud", "blacklist")
    important = ("withdraw", "payment", "kyc", "claim", "rate_change", "need_revision", "contract", "paid", "refund", "invoice")
    info = ("maintenance", "welcome", "info", "announcement")
    if any(k in t for k in urgent):
        return "urgent"
    if any(k in t for k in important):
        return "important"
    if any(k in t for k in info):
        return "info"
    return "normal"


async def _flag_stale(items: list) -> list:
    """Flag notifications whose linked ticket/release no longer exists and strip
    their link so clicking won't open a 'not found' page. Items are kept (PRD:
    read notifications are not deleted) but marked `stale`."""
    ticket_ids = {(i.get("meta") or {}).get("ticket_id") for i in items if (i.get("meta") or {}).get("ticket_id")}
    release_ids = {(i.get("meta") or {}).get("release_id") for i in items if (i.get("meta") or {}).get("release_id")}
    existing_t, existing_r = set(), set()
    if ticket_ids:
        async for d in db.support_tickets.find({"id": {"$in": list(ticket_ids)}}, {"_id": 0, "id": 1}):
            existing_t.add(d["id"])
    if release_ids:
        async for d in db.releases.find({"id": {"$in": list(release_ids)}}, {"_id": 0, "id": 1}):
            existing_r.add(d["id"])
    for i in items:
        m = i.get("meta") or {}
        stale = bool((m.get("ticket_id") and m["ticket_id"] not in existing_t)
                     or (m.get("release_id") and m["release_id"] not in existing_r))
        if stale:
            i["stale"] = True
            i["link"] = None
    return items


async def _notification_page(filt: Dict[str, Any], page: int, limit: int) -> Dict[str, Any]:
    total = await db.notifications.count_documents(filt)
    items = await db.notifications.find(filt, {"_id": 0}).sort("created_at", -1).skip((page - 1) * limit).limit(limit).to_list(limit)
    items = await _flag_stale(items)
    for i in items:
        i["priority"] = _priority_for_type(i.get("type"))
    return {"items": items, "total": total, "page": page, "limit": limit, "pages": max(1, (total + limit - 1) // limit)}


@notif_r.get("/me")
async def my_notifications(
    user: dict = Depends(get_current_user), limit: int = Query(20, ge=1, le=100), page: int = Query(1, ge=1),
    unread_only: bool = False, read_status: str = Query("all", pattern="^(all|unread|read)$"),
    q: Optional[str] = Query(None, max_length=120), ntype: Optional[str] = Query(None, max_length=100),
    date_from: Optional[date] = None, date_to: Optional[date] = None,
):
    effective_status = "unread" if unread_only else read_status
    filt = _notification_filter(user["id"], effective_status, q, ntype, date_from, date_to)
    result = await _notification_page(filt, page, limit)
    filt = {"user_id": user["id"]}
    unread = await db.notifications.count_documents({"user_id": user["id"], "read_at": None})
    result["unread_count"] = unread
    result["types"] = sorted(await db.notifications.distinct("type", {"user_id": user["id"]}))
    return result


@notif_r.get("/admin/log")
async def admin_notification_log(
    user: dict = Depends(require_admin), scope: str = Query("mine", pattern="^(mine|all)$"),
    limit: int = Query(25, ge=1, le=100), page: int = Query(1, ge=1),
    read_status: str = Query("all", pattern="^(all|unread|read)$"), q: Optional[str] = Query(None, max_length=120),
    ntype: Optional[str] = Query(None, max_length=100), date_from: Optional[date] = None, date_to: Optional[date] = None,
):
    assert_admin_permission(user, "notifications.view")
    if scope == "all" and user.get("assigned_role", user.get("role")) != SUPER_ADMIN and user.get("role") != SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Hanya Super Admin yang dapat melihat notifikasi seluruh admin")
    if scope == "mine":
        filt = _notification_filter(user["id"], read_status, q, ntype, date_from, date_to)
        admin_ids = [user["id"]]
    else:
        admins = await db.users.find(
            {"$or": [{"role": {"$in": list(ADMIN_ROLES)}}, {"admin_role_id": {"$exists": True, "$ne": None}}]},
            {"_id": 0, "id": 1, "name": 1, "email": 1},
        ).to_list(5000)
        admin_ids = [item["id"] for item in admins]
        filt = _notification_filter("__all_admins__", read_status, q, ntype, date_from, date_to)
        filt["user_id"] = {"$in": admin_ids}
    result = await _notification_page(filt, page, limit)
    recipient_ids = list({item.get("user_id") for item in result["items"] if item.get("user_id")})
    recipients = await db.users.find({"id": {"$in": recipient_ids}}, {"_id": 0, "id": 1, "name": 1, "email": 1}).to_list(5000)
    recipient_map = {item["id"]: item for item in recipients}
    for item in result["items"]:
        item["recipient"] = recipient_map.get(item.get("user_id"))
        item["is_mine"] = item.get("user_id") == user["id"]
    result["unread_count"] = await db.notifications.count_documents({"user_id": user["id"], "read_at": None})
    result["types"] = sorted(await db.notifications.distinct("type", {"user_id": {"$in": admin_ids}}))
    result["scope"] = scope
    return result


@notif_r.post("/mark-read/{nid}")
async def mark_read(nid: str, user: dict = Depends(get_current_user)):
    n = await db.notifications.find_one({"id": nid})
    if not n or n["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Notifikasi tidak ditemukan")
    await db.notifications.update_one({"id": nid}, {"$set": {"read_at": now_iso()}})
    return {"ok": True}


@notif_r.post("/mark-all-read")
async def mark_all_read(user: dict = Depends(get_current_user)):
    res = await db.notifications.update_many(
        {"user_id": user["id"], "read_at": None},
        {"$set": {"read_at": now_iso()}},
    )
    return {"ok": True, "updated": res.modified_count}


@notif_r.post("/admin/cleanup-stale")
async def cleanup_stale_notifications(user: dict = Depends(require_super_admin)):
    """One-time maintenance: delete notifications whose linked ticket/release no
    longer exists so history stays tidy. Super Admin only."""
    deleted = 0
    scanned = 0
    batch = 1000
    cursor = db.notifications.find(
        {"$or": [{"meta.ticket_id": {"$ne": None}}, {"meta.release_id": {"$ne": None}}]},
        {"_id": 0, "id": 1, "meta": 1},
    )
    stale_ids: list = []
    buf: list = []

    async def flush(items):
        nonlocal deleted
        ticket_ids = {(i.get("meta") or {}).get("ticket_id") for i in items if (i.get("meta") or {}).get("ticket_id")}
        release_ids = {(i.get("meta") or {}).get("release_id") for i in items if (i.get("meta") or {}).get("release_id")}
        existing_t, existing_r = set(), set()
        if ticket_ids:
            async for d in db.support_tickets.find({"id": {"$in": list(ticket_ids)}}, {"_id": 0, "id": 1}):
                existing_t.add(d["id"])
        if release_ids:
            async for d in db.releases.find({"id": {"$in": list(release_ids)}}, {"_id": 0, "id": 1}):
                existing_r.add(d["id"])
        dead = []
        for i in items:
            m = i.get("meta") or {}
            if (m.get("ticket_id") and m["ticket_id"] not in existing_t) or (m.get("release_id") and m["release_id"] not in existing_r):
                dead.append(i["id"])
        if dead:
            res = await db.notifications.delete_many({"id": {"$in": dead}})
            deleted += res.deleted_count

    async for n in cursor:
        scanned += 1
        buf.append(n)
        if len(buf) >= batch:
            await flush(buf); buf = []
    if buf:
        await flush(buf)
    await log_activity(user["id"], "cleanup_stale_notifications", "notification", None, after={"scanned": scanned, "deleted": deleted})
    return {"ok": True, "scanned": scanned, "deleted": deleted}


