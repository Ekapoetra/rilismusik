"""In-app notifications router."""
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
#                              NOTIFICATIONS
# =============================================================================
notif_r = APIRouter(prefix="/notifications", tags=["notifications"])


@notif_r.get("/me")
async def my_notifications(user: dict = Depends(get_current_user), limit: int = 20, unread_only: bool = False):
    filt = {"user_id": user["id"]}
    if unread_only:
        filt["read_at"] = None
    items = await db.notifications.find(filt, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    unread = await db.notifications.count_documents({"user_id": user["id"], "read_at": None})
    return {"items": items, "unread_count": unread}


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


