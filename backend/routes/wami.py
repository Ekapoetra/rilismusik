"""WAMI registration orders router."""
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
#                              WAMI ORDERS
# =============================================================================
wami_r = APIRouter(prefix="/wami", tags=["wami"])


@wami_r.get("/label")
async def label_list_wami(user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    items = await db.wami_orders.find({"label_id": label["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return items


@wami_r.get("/admin")
async def admin_list_wami(user: dict = Depends(require_admin), status: Optional[str] = None):
    filt: Dict[str, Any] = {}
    if status:
        filt["status"] = status
    items = await db.wami_orders.find(filt, {"_id": 0}).sort("created_at", -1).to_list(500)
    label_ids = list({i["label_id"] for i in items})
    labels = await db.labels.find({"id": {"$in": label_ids}}, {"_id": 0, "id": 1, "label_name": 1, "user_id": 1}).to_list(1000)
    name_map = {lab["id"]: lab["label_name"] for lab in labels}
    for it in items:
        it["label_name"] = name_map.get(it["label_id"])
    return items


@wami_r.post("/admin/{order_id}/status")
async def admin_update_wami(order_id: str, body: AdminWamiUpdateIn, user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_release"):
        raise HTTPException(status_code=403, detail="Hanya Admin Release / Super Admin")
    order = await db.wami_orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order tidak ditemukan")
    upd: Dict[str, Any] = {"status": body.status, "updated_at": now_iso()}
    if body.note is not None:
        upd["admin_note"] = body.note
    if body.wami_reference is not None:
        upd["wami_reference"] = body.wami_reference
    if body.status == "registered":
        upd["registered_at"] = now_iso()
    await db.wami_orders.update_one({"id": order_id}, {"$set": upd})
    # Notify label
    user_ids = await label_user_ids(order["label_id"])
    titles = {
        "in_progress": ("WAMI sedang diproses", f"Pendaftaran WAMI '{order.get('track_title')}' sedang diproses."),
        "registered": ("WAMI berhasil terdaftar ✓", f"'{order.get('track_title')}' telah terdaftar di LMKN/WAMI."),
        "rejected": ("WAMI ditolak", f"Pendaftaran '{order.get('track_title')}' ditolak. {body.note or ''}"),
        "cancelled": ("WAMI dibatalkan", f"Pendaftaran '{order.get('track_title')}' dibatalkan."),
    }
    if body.status in titles:
        title, msg = titles[body.status]
        await notify_many(user_ids, f"wami_{body.status}", title, msg, "/label/wami", {"wami_order_id": order_id})
    await log_activity(user["id"], f"wami_{body.status}", "wami", order_id, after={"status": body.status})
    return await db.wami_orders.find_one({"id": order_id}, {"_id": 0})


