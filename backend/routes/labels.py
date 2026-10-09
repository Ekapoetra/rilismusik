"""Label profile & dashboard router."""
from .query_concurrency import bounded_gather
from fastapi import APIRouter, HTTPException, Request, Response, Depends, UploadFile, File, Form, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta, date
import os
import re
import csv
import io
import shutil
import secrets

from .deps import (
    db, logger, UPLOAD_DIR,
    get_current_user, require_label, require_artist, require_admin, require_super_admin,
    public_user, get_label_by_user, get_labels_for_user, account_entitlements, redact_label_for_self, LABEL_HIDDEN_FIELDS,
    log_activity, notify, notify_many, admin_user_ids, label_user_ids,
    LABEL_ROLE, ARTIST_ROLE, ADMIN_ROLES, SUPER_ADMIN,
)
from models import (
    RegisterLabelIn, LoginIn, ForgotPasswordIn, ResetPasswordIn, VerifyEmailIn,
    LabelProfileUpdate, LabelClaimRequestIn, BankAccountIn, BankAccountChangeRequestIn, BankAccountChangeActionIn,
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
from .bank_change_service import create_bank_change_request, review_bank_change_request

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
    from .kyc_service import compute_kyc_state
    from .entitlements import resolve_label_entitlements
    return {**redact_label_for_self(label), "entitlements": resolve_label_entitlements(label), "kyc": await compute_kyc_state(user=user, label=label)}


class ActiveLabelIn(BaseModel):
    label_id: str


@label_r.get("/account")
async def label_account(user: dict = Depends(require_label)):
    """Multi Label account summary: owned labels, active/primary, entitlements and
    account-level aggregated available balance (each child keeps its own cutoff)."""
    labels = await get_labels_for_user(user)
    if not labels:
        raise HTTPException(status_code=404, detail="Label belum diset")
    from .deps import _account_authority
    ent = await account_entitlements(user)
    is_multi = bool(ent.get("multi_label"))
    active = await get_label_by_user(user)
    authority = _account_authority(labels, user)
    balances = {}
    account_available = None
    if is_multi:
        from .balance_utils import compute_labels_available_balances
        balances = await compute_labels_available_balances(labels)
        account_available = int(sum(balances.values()))

    def _mini(lab):
        return {
            "id": lab["id"], "label_name": lab.get("label_name"),
            "logo_url": f"/api/files/{lab['logo_storage_key']}" if lab.get("logo_storage_key") else None,
            "available_idr": int(balances.get(lab["id"], 0)) if is_multi else None,
        }

    return {
        "is_multi_label": is_multi,
        "entitlements": ent,
        "active_label_id": active["id"],
        "primary_label_id": authority.get("id"),
        "labels": [_mini(lab) for lab in labels],
        "label_count": len(labels),
        "account_available_idr": account_available,
    }


@label_r.post("/active-label")
async def set_active_label(body: ActiveLabelIn, user: dict = Depends(require_label)):
    labels = await get_labels_for_user(user)
    if not any(lab["id"] == body.label_id for lab in labels):
        raise HTTPException(status_code=404, detail="Label tidak ditemukan pada akun ini")
    await db.users.update_one({"id": user["id"]}, {"$set": {"active_label_id": body.label_id, "updated_at": now_iso()}})
    return {"ok": True, "active_label_id": body.label_id}


@label_r.patch("/me")
async def label_update(body: LabelProfileUpdate, user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    upd = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    upd["updated_at"] = now_iso()
    identity_fields = {"label_name", "pic_name", "whatsapp", "address", "city"}
    identity_changed = any(
        key in upd and str(upd.get(key) or "").strip() != str(label.get(key) or "").strip()
        for key in identity_fields
    )
    update_doc: Dict[str, Any] = {"$set": upd}
    if label.get("kyc_status") == "verified" and identity_changed:
        upd["kyc_status"] = "incomplete"
        upd["kyc_rejection_reason"] = None
        update_doc["$unset"] = {"kyc_verified_at": "", "kyc_verified_by": ""}
    await db.labels.update_one({"id": label["id"]}, update_doc)
    updated = await db.labels.find_one({"id": label["id"]}, {"_id": 0})
    from .kyc_service import compute_kyc_state
    return {**redact_label_for_self(updated), "kyc": await compute_kyc_state(user=user, label=updated)}


@label_r.post("/claim-request")
async def label_claim_request(body: LabelClaimRequestIn, user: dict = Depends(require_label)):
    """Existing (non-claim) label account requests to claim a legacy label after registration."""
    if user.get("claim_status") in ("pending_link", "conflict", "linked"):
        raise HTTPException(status_code=400, detail="Permintaan klaim label sudah pernah diajukan untuk akun ini.")
    if not body.ownership_statement:
        raise HTTPException(status_code=400, detail="Pernyataan kepemilikan wajib dicentang sebelum mengajukan klaim.")
    label = await get_label_by_user(user)
    legacy_name = body.legacy_label_name.strip()
    now = now_iso()

    # Conflict detection: another account already claims the same legacy name.
    # All matching claims move to 'conflict' — only Super Admin resolves them.
    rivals = await db.users.find(
        {"role": "label", "id": {"$ne": user["id"]},
         "claim_status": {"$in": ["pending_link", "conflict"]},
         "$or": [
             {"claim_legacy_name_norm": legacy_name.lower()},
             {"claim_legacy_name": {"$regex": "^" + re.escape(legacy_name) + "$", "$options": "i"}},
         ]},
        {"_id": 0, "id": 1},
    ).to_list(50)
    status = "conflict" if rivals else "pending_link"
    if rivals:
        await db.users.update_many(
            {"id": {"$in": [r["id"] for r in rivals]}},
            {"$set": {"claim_status": "conflict", "updated_at": now}},
        )

    await db.users.update_one({"id": user["id"]}, {"$set": {
        "claim_status": status,
        "claim_legacy_name": legacy_name,
        "claim_legacy_name_norm": legacy_name.lower(),
        "claim_requested_at": now,
        "claim_label_name_new": label.get("label_name"),
        "claim_whatsapp": label.get("whatsapp"),
        "claim_statement_accepted_at": now,
        "claim_evidence_note": (body.evidence_note or "").strip() or None,
        "updated_at": now,
    }})
    admin_ids = await admin_user_ids(("super_admin", "admin_release", "admin_support"))
    conflict_note = " Ada klaim lain dengan nama yang sama — masuk daftar sengketa." if rivals else ""
    await notify_many(
        admin_ids, "claim_request", "Permintaan klaim akun lama",
        f"User {user.get('name')} ({user.get('email')}) mengaku punya label lama: '{legacy_name}'.{conflict_note} Tinjau di Admin → Migrasi → Claims.",
        "/admin/migrate?tab=claims", {"user_id": user["id"], "legacy_label_name": legacy_name},
    )
    await log_activity(user["id"], "claim_request", "label", user["id"],
                       after={"legacy_label_name": legacy_name, "conflict": bool(rivals)})
    return {"ok": True, "claim_pending": True, "claim_status": status, "claim_legacy_name": legacy_name}


@label_r.get("/dashboard")
async def label_dashboard(user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    from .balance_utils import compute_label_balance_snapshot
    async def release_statuses():
        return await db.releases.aggregate([
            {"$match": {"label_id": label["id"]}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]).to_list(None)
    balance, release_counts, total_tracks, total_artists, active_tickets, pending_invoices = await bounded_gather(
        compute_label_balance_snapshot(label_id=label["id"], label=label),
        release_statuses(),
        db.tracks.count_documents({"label_id": label["id"]}),
        db.artists.count_documents({"label_id": label["id"]}),
        db.support_tickets.count_documents({"label_id": label["id"], "status": {"$nin": ["done", "rejected"]}}),
        db.payments.count_documents({"label_id": label["id"], "status": "pending"}),
    )
    total_releases = sum(row["count"] for row in release_counts)
    active_releases = sum(row["count"] for row in release_counts if row["_id"] in {"approved", "delivered", "live"})

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
            **({"period": {"$gt": label.get("last_withdrawn_period")}} if label.get("last_withdrawn_period") else {}),
        }},
        {"$group": {"_id": "$period", "total": {"$sum": "$label_idr"}}},
        {"$sort": {"_id": -1}},
        {"$limit": 1},
    ]
    async for row in db_bg.royalty_lines.aggregate(pipeline, allowDiskUse=True):
        last_revenue = int(row.get("total") or 0)
        last_period = row.get("_id")
        break

    # Release pipeline counts (additive, non-destructive) for dashboard funnel.
    pipeline_counts = {"draft": 0, "review": 0, "delivered": 0, "live": 0}
    _bucket = {
        "draft": "draft",
        "submitted": "review", "under_review": "review", "awaiting_payment": "review",
        "paid": "review", "approved": "review", "need_revision": "review",
        "delivered": "delivered",
        "live": "live",
    }
    for row in release_counts:
        bucket = _bucket.get(row.get("_id"))
        if bucket:
            pipeline_counts[bucket] += int(row.get("count") or 0)

    # Releases that went live today (WIB) → celebratory banner on the label dashboard.
    from datetime import timedelta as _td
    today_wib = (datetime.now(timezone.utc) + _td(hours=7)).date().isoformat()
    live_today = []
    for r in await db.releases.find(
        {"label_id": label["id"], "status": "live", "live_at": {"$ne": None}},
        {"_id": 0, "id": 1, "release_title": 1, "primary_artist_name": 1, "artist_name": 1,
         "display_cover_url": 1, "cover_url": 1, "live_at": 1},
    ).sort("live_at", -1).to_list(20):
        live_at = str(r.get("live_at") or "")
        try:
            live_date = (datetime.fromisoformat(live_at.replace("Z", "+00:00")) + _td(hours=7)).date().isoformat()
        except Exception:
            continue
        if live_date == today_wib:
            live_today.append({
                "id": r["id"], "release_title": r.get("release_title"),
                "artist_name": r.get("primary_artist_name") or r.get("artist_name"),
                "cover_url": r.get("display_cover_url") or r.get("cover_url"),
            })

    from .kyc_service import compute_kyc_state
    return {
        "label": {**redact_label_for_self(label), "kyc": await compute_kyc_state(user=user, label=label)},
        "balance": balance,
        "pipeline": pipeline_counts,
        "live_today": live_today,
        "stats": {
            "balance_available_idr": balance["balance_available_idr"],
            "balance_pending_idr": balance["balance_pending_idr"],
            "balance_withdraw_requested_idr": balance["balance_withdraw_requested_idr"],
            "last_withdrawn_period": balance["last_withdrawn_period"],
            "latest_report_period": balance["latest_report_period"],
            "balance_source": "royalty_lines_and_adjustments",
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
        "bank_value": body.bank_value,
        "account_number": body.account_number,
        "account_holder_name": body.account_holder_name,
        "verified_status": "pending",
        "verified_by": None,
        "verified_at": None,
        "created_at": now_iso(),
    }
    await db.bank_accounts.insert_one(bank)
    bank.pop("_id", None)
    await notify_many(
        await admin_user_ids(("super_admin", "admin_finance")),
        "bank_account_new", "Rekening baru menunggu verifikasi",
        f"{label.get('label_name')} menambahkan rekening baru.",
        f"/admin/labels/{label['id']}", {"label_id": label["id"]},
    )
    return bank


@label_r.get("/bank-account/change-requests")
async def list_label_bank_change_requests(user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    return await db.bank_account_change_requests.find(
        {"label_id": label["id"]}, {"_id": 0},
    ).sort("created_at", -1).to_list(50)


@label_r.post("/bank-account/change-request")
async def request_bank_change(
    body: BankAccountChangeRequestIn, user: dict = Depends(require_label),
):
    label = await get_label_by_user(user)
    document = await create_bank_change_request(
        label=label, payload=body.model_dump(), requester=user, approval_target="admin",
    )
    await notify_many(
        await admin_user_ids(("super_admin", "admin_finance")),
        "bank_change_requested", "Perubahan rekening menunggu persetujuan",
        f"{label.get('label_name')} mengajukan perubahan rekening.",
        f"/admin/labels/{label['id']}", {"request_id": document["id"], "label_id": label["id"]},
    )
    await log_activity(user["id"], "request_bank_change", "bank_account", document["id"], after={"status": document["status"]})
    return document


@label_r.post("/bank-account/change-requests/{request_id}/action")
async def label_review_bank_change(
    request_id: str, body: BankAccountChangeActionIn, user: dict = Depends(require_label),
):
    label = await get_label_by_user(user)
    document = await review_bank_change_request(
        request_id=request_id, action=body.action, note=body.note, reviewer=user,
        expected_status="pending_label_approval", label_id=label["id"],
    )
    await notify_many(
        await admin_user_ids(("super_admin", "admin_finance")),
        "bank_change_reviewed", f"Perubahan rekening {body.action}",
        f"{label.get('label_name')} telah {body.action} perubahan rekening dari admin.",
        f"/admin/labels/{label['id']}", {"request_id": request_id, "label_id": label["id"]},
    )
    await log_activity(user["id"], f"label_{body.action}_bank_change", "bank_account", request_id)
    return document


@label_r.get("/invoices")
async def list_invoices(user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    items = await db.payments.find({"label_id": label["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return items


