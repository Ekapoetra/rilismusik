"""Artists (label sub-accounts) router."""
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
    require_kyc_for_label_user,
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
#                              ARTISTS
# =============================================================================
artist_r = APIRouter(prefix="/artists", tags=["artists"])


@artist_r.get("/")
async def list_artists(
    user: dict = Depends(require_label),
    period_from: Optional[str] = Query(None, description="Inclusive YYYY-MM"),
    period_to: Optional[str] = Query(None, description="Inclusive YYYY-MM"),
):
    label = await get_label_by_user(user)
    items = await db.artists.find({"label_id": label["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)
    # Label-facing artist income is unsettled only. Lifetime rollups include
    # withdrawn rows and must remain admin-only.
    artist_ids = [item["id"] for item in items]
    line_filter: Dict[str, Any] = {
        "label_id": label["id"],
        "artist_id": {"$in": artist_ids},
        "status": {"$in": ["pending", "available"]},
        "legacy_settled": {"$ne": True},
    }
    period_query: Dict[str, str] = {}
    if label.get("last_withdrawn_period"):
        period_query["$gt"] = label["last_withdrawn_period"]
    if period_from:
        period_query["$gte"] = max(period_from, label.get("last_withdrawn_period") or period_from)
    if period_to:
        period_query["$lte"] = period_to
    if period_query:
        line_filter["period"] = period_query
    rollup: Dict[str, Dict[str, Any]] = {}
    if artist_ids:
        async for row in db_bg.royalty_lines.aggregate([
            {"$match": line_filter},
            {"$group": {
                "_id": "$artist_id",
                "revenue_eur": {"$sum": "$revenue_eur"},
                "revenue_idr": {"$sum": "$label_idr"},
                "lines": {"$sum": 1},
                "first_period": {"$min": "$period"},
                "last_period": {"$max": "$period"},
            }},
        ], allowDiskUse=True):
            if row.get("_id"):
                rollup[row["_id"]] = row
    for it in items:
        r = rollup.get(it["id"], {})
        it["revenue_eur"] = r.get("revenue_eur", 0)
        it["revenue_idr"] = r.get("revenue_idr", 0)
        it["royalty_lines_count"] = r.get("lines", 0)
        it["last_active_period"] = r.get("last_period")
        it["first_active_period"] = r.get("first_period")
        it["revenue_scope"] = "unwithdrawn"
    return items


@artist_r.post("/")
async def create_artist(body: ArtistIn, user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    email = body.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Email sudah terdaftar")

    user_id = new_id()
    artist_id = new_id()
    user_doc = {
        "id": user_id,
        "name": body.artist_name,
        "email": email,
        "password_hash": hash_password(body.password),
        "role": ARTIST_ROLE,
        "email_verified_at": None,
        "status": "active",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.users.insert_one(user_doc)

    default_visibility = {
        "show_amount": True,
        "show_percentage": False,
        "show_per_song": True,
        "show_monthly_history": True,
    }
    visibility = {**default_visibility, **(body.visibility_settings or {})}
    artist_doc = {
        "id": artist_id,
        "label_id": label["id"],
        "user_id": user_id,
        "artist_name": body.artist_name,
        "email": email,
        "whatsapp": body.whatsapp,
        "visibility_settings": visibility,
        "status": "active",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.artists.insert_one(artist_doc)
    artist_doc.pop("_id", None)
    return artist_doc


@artist_r.get("/{artist_id}")
async def get_artist(artist_id: str, user: dict = Depends(require_kyc_for_label_user)):
    artist = await db.artists.find_one({"id": artist_id}, {"_id": 0})
    if not artist:
        raise HTTPException(status_code=404, detail="Artist tidak ditemukan")
    if user["role"] == LABEL_ROLE:
        label = await get_label_by_user(user)
        if artist["label_id"] != label["id"]:
            raise HTTPException(status_code=403, detail="Bukan artist Anda")
    elif user["role"] == ARTIST_ROLE:
        if artist["user_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Bukan akun Anda")
    return artist


@artist_r.patch("/{artist_id}")
async def update_artist(artist_id: str, body: ArtistUpdateIn, user: dict = Depends(require_label)):
    artist = await db.artists.find_one({"id": artist_id})
    if not artist:
        raise HTTPException(status_code=404, detail="Artist tidak ditemukan")
    label = await get_label_by_user(user)
    if artist["label_id"] != label["id"]:
        raise HTTPException(status_code=403, detail="Bukan artist Anda")
    upd = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    upd["updated_at"] = now_iso()
    await db.artists.update_one({"id": artist_id}, {"$set": upd})
    return await db.artists.find_one({"id": artist_id}, {"_id": 0})


