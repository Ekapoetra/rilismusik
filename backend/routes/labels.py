"""Label profile & dashboard router."""
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
#                                LABEL
# =============================================================================
label_r = APIRouter(prefix="/label", tags=["label"])


@label_r.get("/me")
async def label_me(user: dict = Depends(require_label)):
    # Claim-pending users haven't been linked to a label yet — return a stub
    # that the frontend can use to show the "claim pending" state.
    if user.get("claim_status") == "pending_link":
        return {
            "claim_pending": True,
            "claim_legacy_name": user.get("claim_legacy_name"),
            "claim_label_name_new": user.get("claim_label_name_new"),
            "claim_requested_at": user.get("claim_requested_at"),
            "pic_name": user.get("name"),
            "email": user.get("email"),
        }
    label = await get_label_by_user(user)
    return redact_label_for_self(label)


@label_r.patch("/me")
async def label_update(body: LabelProfileUpdate, user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    upd = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    upd["updated_at"] = now_iso()
    await db.labels.update_one({"id": label["id"]}, {"$set": upd})
    updated = await db.labels.find_one({"id": label["id"]}, {"_id": 0})
    return redact_label_for_self(updated)


@label_r.get("/dashboard")
async def label_dashboard(user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    total_releases = await db.releases.count_documents({"label_id": label["id"]})
    active_releases = await db.releases.count_documents({"label_id": label["id"], "status": {"$in": ["approved", "delivered", "live"]}})
    total_tracks = await db.tracks.count_documents({"label_id": label["id"]})
    total_artists = await db.artists.count_documents({"label_id": label["id"]})
    active_tickets = await db.support_tickets.count_documents({"label_id": label["id"], "status": {"$nin": ["done", "rejected"]}})
    pending_invoices = await db.payments.count_documents({"label_id": label["id"], "status": "pending"})

    # Latest UNWITHDRAWN royalty only. Admin analytics keeps lifetime history,
    # so its cache cannot be reused for this customer-facing number.
    last_revenue = 0
    last_period = None
    from .deps import db_bg
    pipeline = [
        {"$match": {
            "label_id": label["id"],
            "status": {"$in": ["pending", "available"]},
            "legacy_settled": {"$ne": True},
        }},
        {"$group": {"_id": "$period", "total": {"$sum": "$label_idr"}}},
        {"$sort": {"_id": -1}},
        {"$limit": 1},
    ]
    async for row in db_bg.royalty_lines.aggregate(pipeline, allowDiskUse=True):
        last_revenue = int(row.get("total") or 0)
        last_period = row.get("_id")
        break

    return {
        "label": redact_label_for_self(label),
        "stats": {
            "balance_available_idr": label.get("balance_available_idr", 0),
            "balance_pending_idr": label.get("balance_pending_idr", 0),
            "balance_withdraw_requested_idr": label.get("balance_withdraw_requested_idr", 0),
            "last_month_revenue_idr": last_revenue,
            "last_month_period": last_period,
            "total_releases": total_releases,
            "active_releases": active_releases,
            "total_tracks": total_tracks,
            "total_artists": total_artists,
            "active_tickets": active_tickets,
            "pending_invoices": pending_invoices,
            "subscription_status": label.get("subscription_status"),
            "subscription_expires_at": label.get("subscription_expires_at"),
            "contract_status": label.get("contract_status"),
            "account_status": label.get("account_status"),
            "bank_verified": label.get("bank_verified", False),
            "payment_type": label.get("payment_type"),
        },
    }


@label_r.get("/bank-account")
async def get_bank(user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    bank = await db.bank_accounts.find_one({"label_id": label["id"]}, {"_id": 0})
    return bank or None


@label_r.post("/bank-account")
async def submit_bank(body: BankAccountIn, user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    existing = await db.bank_accounts.find_one({"label_id": label["id"]})
    if existing:
        raise HTTPException(status_code=409, detail="Rekening sudah pernah diinput. Hubungi admin untuk perubahan.")
    bank = {
        "id": new_id(),
        "label_id": label["id"],
        "bank_name": body.bank_name,
        "account_number": body.account_number,
        "account_holder_name": body.account_holder_name,
        "verified_status": "pending",
        "verified_by": None,
        "verified_at": None,
        "created_at": now_iso(),
    }
    await db.bank_accounts.insert_one(bank)
    bank.pop("_id", None)
    return bank


@label_r.get("/invoices")
async def list_invoices(user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    items = await db.payments.find({"label_id": label["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return items


