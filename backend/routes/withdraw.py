"""Withdraw requests & admin actions router."""
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
from email_service import send_withdraw_paid_email
from models import (
    RegisterLabelIn, LoginIn, ForgotPasswordIn, ResetPasswordIn, VerifyEmailIn,
    LabelProfileUpdate, BankAccountIn,
    ReleaseDraftIn, ReleaseSubmitConfirmation, AdminReleaseAction,
    ArtistIn, ArtistUpdateIn,
    CreateReleasePaymentIn,
    CMSUpdateIn, AdminUserCreateIn, LabelStatusUpdate,
    ExchangeRateIn, RoyaltyImportPublishIn, RoyaltyLineMatchIn,
    WithdrawRequestIn, WithdrawAdminAction, ManualLegacyWithdrawIn,
    LegacyWithdrawPeriodPreviewIn, LegacyWithdrawPeriodCommitIn,
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
#                              WITHDRAW
# =============================================================================
withdraw_r = APIRouter(prefix="/withdraw", tags=["withdraw"])


def _require_finance_admin(user: dict) -> None:
    if user.get("role") not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")


# ---------------------------------------------------------------------------
# FIFO computation (Phase 20)
# ---------------------------------------------------------------------------
async def _compute_withdrawable(label_id: str) -> Dict[str, Any]:
    """Compute the withdrawable amount for a label using FIFO per-bulan-laporan.

    Rule (per user spec 2026-06-29):
      - Each withdraw consumes ALL `available` royalty_lines whose `period` >
        the label's `last_withdrawn_period` (or all if never withdrawn).
      - Force-full: the label can't pick a partial amount — it's withdraw-all-
        or-nothing for the eligible range.
      - "Bulan laporan" = `royalty_lines.period` (YYYY-MM, derived from CSV
        Believe "Reporting month").

    Returns:
      {
        withdrawable_idr: int,            # sum(label_idr) for eligible rows
        period_from: "YYYY-MM" | None,    # earliest eligible period
        period_to:   "YYYY-MM" | None,    # latest eligible period
        lines_count: int,
        last_withdrawn_period: "YYYY-MM" | None,  # for UI context
      }
    """
    from .balance_utils import compute_label_balance_snapshot
    snapshot = await compute_label_balance_snapshot(label_id=label_id)
    return {
        "withdrawable_idr": 0 if snapshot["has_active_withdraw"] else snapshot["balance_available_idr"],
        "period_from": None if snapshot["has_active_withdraw"] else snapshot["available_period_from"],
        "period_to": None if snapshot["has_active_withdraw"] else snapshot["available_period_to"],
        "lines_count": 0 if snapshot["has_active_withdraw"] else snapshot["available_lines"],
        "last_withdrawn_period": snapshot["last_withdrawn_period"],
        "latest_report_period": snapshot["latest_report_period"],
        "balance_pending_idr": snapshot["balance_pending_idr"],
        "balance_available_idr": snapshot["balance_available_idr"],
        "balance_withdraw_requested_idr": snapshot["balance_withdraw_requested_idr"],
        "has_active_withdraw": snapshot["has_active_withdraw"],
    }


@withdraw_r.get("/window")
async def get_window_state(user: dict = Depends(get_current_user)):
    return withdraw_window_state()


@withdraw_r.get("/label/computed")
async def label_computed_withdrawable(user: dict = Depends(require_label)):
    """Return the FIFO-computed withdrawable amount + period range for the
    current label. The label-side UI uses this to pre-fill the withdraw form
    (no manual amount input — force-full per spec).
    """
    label = await get_label_by_user(user)
    info = await _compute_withdrawable(label["id"])
    can_withdraw = info["withdrawable_idr"] >= MIN_WITHDRAW_IDR
    return {
        **info,
        "min_withdraw_idr": MIN_WITHDRAW_IDR,
        "can_withdraw": can_withdraw,
        "reason": None if can_withdraw else (
            "Masih ada withdraw yang sedang diproses"
            if info.get("has_active_withdraw") else
            "Belum ada royalti tersedia setelah penarikan terakhir"
            if info["lines_count"] == 0 else
            f"Total Rp {info['withdrawable_idr']:,} di bawah minimum Rp {MIN_WITHDRAW_IDR:,}"
        ),
    }


@withdraw_r.post("/label/request")
async def label_request_withdraw(user: dict = Depends(require_label)):
    """Withdraw FIFO (Phase 20). User cannot pick the amount — it's auto-
    computed from all `available` royalty_lines whose period > the label's
    last_withdrawn_period. Force-full per spec.
    """
    label = await get_label_by_user(user)
    state = withdraw_window_state()
    if not state["request_open"]:
        raise HTTPException(status_code=400, detail=f"Permintaan withdraw ditutup. {state['message']}")

    info = await _compute_withdrawable(label["id"])
    amount_idr = info["withdrawable_idr"]
    if amount_idr < MIN_WITHDRAW_IDR:
        if info["lines_count"] == 0:
            raise HTTPException(status_code=400, detail="Belum ada royalti tersedia untuk ditarik")
        raise HTTPException(
            status_code=400,
            detail=f"Total Rp {amount_idr:,.0f} di bawah minimum Rp {MIN_WITHDRAW_IDR:,.0f}. Tunggu periode laporan berikutnya.",
        )
    if not label.get("bank_verified"):
        bank = await db.bank_accounts.find_one({"label_id": label["id"]})
        if not bank:
            raise HTTPException(status_code=400, detail="Rekening bank belum diinput")
    bank = await db.bank_accounts.find_one({"label_id": label["id"]}, {"_id": 0})

    wd_id = new_id()
    # Move ALL of `balance_available_idr` into `balance_withdraw_requested_idr`
    # (since FIFO consumes every available line in the eligible range, the
    # available balance should equal the computed amount minus rounding).
    await db.labels.update_one({"id": label["id"]}, {"$inc": {
        "balance_available_idr": -amount_idr,
        "balance_withdraw_requested_idr": amount_idr,
    }, "$set": {"updated_at": now_iso()}})
    await db.balance_transactions.insert_one({
        "id": new_id(),
        "label_id": label["id"],
        "type": "withdraw_request",
        "amount_idr": -amount_idr,
        "reference_type": "withdraw",
        "reference_id": wd_id,
        "description": f"Withdraw diminta — periode {info['period_from']} s/d {info['period_to']}",
        "created_at": now_iso(),
    })
    wd = {
        "id": wd_id,
        "label_id": label["id"],
        "amount_idr": amount_idr,
        "status": "requested",
        "request_date": now_iso(),
        "approved_date": None,
        "paid_date": None,
        "approved_by": None,
        "paid_by": None,
        "bank_snapshot": bank,
        "payment_proof_url": None,
        "payment_reference": None,
        "admin_note": None,
        # Phase 20: track which months this withdraw consumes so admin
        # mark_paid can update last_withdrawn_period correctly and the label
        # UI can render the FIFO range.
        "period_from": info["period_from"],
        "period_to": info["period_to"],
        "lines_count": info["lines_count"],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.withdraw_requests.insert_one(wd)
    await log_activity(
        user["id"], "withdraw_request", "withdraw", wd_id,
        after={"amount_idr": amount_idr, "period_from": info["period_from"], "period_to": info["period_to"]},
    )
    wd.pop("_id", None)
    return wd


@withdraw_r.get("/label")
async def label_list_withdraws(user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    # Imported legacy history is retained for admin audit only. Its old amount
    # and exchange-rate basis can differ from the current system and must never
    # be shown to the customer.
    items = await db.withdraw_requests.find({
        "label_id": label["id"],
        "legacy_import": {"$ne": True},
    }, {"_id": 0}).sort("created_at", -1).to_list(500)
    return items


@withdraw_r.get("/admin")
async def admin_list_withdraws(
    user: dict = Depends(require_admin), status: Optional[str] = None,
    year: Optional[int] = Query(None, ge=2000, le=2100),
    month: Optional[int] = Query(None, ge=1, le=12),
):
    _require_finance_admin(user)
    filt: Dict[str, Any] = {}
    if (year is None) != (month is None):
        raise HTTPException(status_code=400, detail="Tahun dan bulan harus dipilih bersama")
    if year is not None and month is not None:
        from .finance_reporting import withdrawal_period_filter
        filt = withdrawal_period_filter(status=status, year=year, month=month)
    elif status:
        filt["status"] = status
    items = await db.withdraw_requests.find(filt, {"_id": 0}).sort("created_at", -1).to_list(500)
    # enrich with label_name
    label_ids = list({i["label_id"] for i in items})
    labels = await db.labels.find({"id": {"$in": label_ids}}, {"_id": 0, "id": 1, "label_name": 1}).to_list(1000)
    name_map = {lab["id"]: lab["label_name"] for lab in labels}
    for it in items:
        it["label_name"] = name_map.get(it["label_id"])
        it["legacy_editable"] = bool(
            it.get("legacy_import") is True and it.get("status") == "paid" and it.get("period_to")
        )
    return items


@withdraw_r.get("/admin/summary")
async def admin_withdraw_summary(
    year: int = Query(..., ge=2000, le=2100), month: int = Query(..., ge=1, le=12),
    user: dict = Depends(require_admin),
):
    _require_finance_admin(user)
    from .finance_reporting import withdrawal_cashflow_summary
    return await withdrawal_cashflow_summary(year=year, month=month)


@withdraw_r.post("/admin/legacy-manual/preview")
async def admin_preview_manual_legacy_withdraw(
    body: ManualLegacyWithdrawIn, user: dict = Depends(require_admin),
):
    _require_finance_admin(user)
    from .manual_legacy_withdrawal import preview_manual_legacy_withdrawal
    return await preview_manual_legacy_withdrawal(body)


@withdraw_r.post("/admin/legacy-manual")
async def admin_create_manual_legacy_withdraw(
    body: ManualLegacyWithdrawIn, user: dict = Depends(require_admin),
):
    _require_finance_admin(user)
    from .manual_legacy_withdrawal import queue_manual_legacy_withdrawal
    return await queue_manual_legacy_withdrawal(body, user)


@withdraw_r.post("/admin/{wd_id}/legacy-edit/preview")
async def admin_preview_legacy_withdraw_edit(
    wd_id: str, body: LegacyWithdrawPeriodPreviewIn, user: dict = Depends(require_admin),
):
    _require_finance_admin(user)
    from .legacy_withdraw_edit import build_legacy_withdraw_edit_preview
    return await build_legacy_withdraw_edit_preview(wd_id, body.period_to, user["id"])


@withdraw_r.post("/admin/{wd_id}/legacy-edit")
async def admin_commit_legacy_withdraw_edit(
    wd_id: str, body: LegacyWithdrawPeriodCommitIn, user: dict = Depends(require_admin),
):
    _require_finance_admin(user)
    from .legacy_withdraw_edit import queue_legacy_withdraw_edit
    return await queue_legacy_withdraw_edit(wd_id, body.preview_id, user)


@withdraw_r.post("/admin/{wd_id}/action")
async def admin_withdraw_action(wd_id: str, body: WithdrawAdminAction, user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    wd = await db.withdraw_requests.find_one({"id": wd_id})
    if not wd:
        raise HTTPException(status_code=404, detail="Withdraw tidak ditemukan")

    if body.action == "approve":
        if wd["status"] != "requested":
            raise HTTPException(status_code=400, detail="Hanya request yang bisa di-approve")
        await db.withdraw_requests.update_one({"id": wd_id}, {"$set": {
            "status": "approved", "approved_date": now_iso(), "approved_by": user["id"], "admin_note": body.note, "updated_at": now_iso(),
        }})
    elif body.action == "reject":
        if wd["status"] not in ("requested", "approved"):
            raise HTTPException(status_code=400, detail="Tidak bisa ditolak pada status saat ini")
        # refund balance
        await db.labels.update_one({"id": wd["label_id"]}, {"$inc": {
            "balance_available_idr": wd["amount_idr"],
            "balance_withdraw_requested_idr": -wd["amount_idr"],
        }, "$set": {"updated_at": now_iso()}})
        await db.balance_transactions.insert_one({
            "id": new_id(), "label_id": wd["label_id"], "type": "withdraw_refund",
            "amount_idr": wd["amount_idr"], "reference_type": "withdraw", "reference_id": wd_id,
            "description": f"Withdraw ditolak — refund ke saldo tersedia. {body.note or ''}",
            "created_at": now_iso(),
        })
        await db.withdraw_requests.update_one({"id": wd_id}, {"$set": {
            "status": "rejected", "admin_note": body.note, "updated_at": now_iso(),
        }})
    elif body.action == "mark_paid":
        if wd["status"] != "approved":
            raise HTTPException(status_code=400, detail="Hanya yang sudah approved bisa di-mark paid")
        # Finance dapat memproses kapan saja; window 15-20 hanya sebagai panduan operasional.
        await db.labels.update_one({"id": wd["label_id"]}, {"$inc": {
            "balance_withdraw_requested_idr": -wd["amount_idr"],
        }, "$set": {"updated_at": now_iso()}})
        await db.balance_transactions.insert_one({
            "id": new_id(), "label_id": wd["label_id"], "type": "withdraw_paid",
            "amount_idr": -wd["amount_idr"], "reference_type": "withdraw", "reference_id": wd_id,
            "description": f"Withdraw dibayar. Ref: {body.payment_reference or '-'}",
            "created_at": now_iso(),
        })

        # Phase 20: lock the FIFO window. Flip royalty_lines status
        # `available → withdrawn` for the period range captured at request
        # time, then bump labels.last_withdrawn_period so next withdraw
        # starts right after this period_to.
        period_from = wd.get("period_from")
        period_to = wd.get("period_to")
        if period_from and period_to:
            # Chunked update via db_bg (CSOT-safe). On a label with 100k+
            # lines per range a single update_many could exceed Atlas's
            # 50-second `maxTimeMS`, so we paginate by `_id`.
            CHUNK = 5000
            line_filter = {
                "label_id": wd["label_id"],
                "status": "available",
                "period": {"$gte": period_from, "$lte": period_to},
            }
            last_oid = None
            total_flipped = 0
            while True:
                q = dict(line_filter)
                if last_oid is not None:
                    q["_id"] = {"$gt": last_oid}
                batch = await db_bg.royalty_lines.find(q, {"_id": 1}).sort("_id", 1).limit(CHUNK).to_list(CHUNK)
                if not batch:
                    break
                oids = [d["_id"] for d in batch]
                last_oid = oids[-1]
                await db_bg.royalty_lines.update_many({"_id": {"$in": oids}}, {"$set": {"status": "withdrawn"}})
                total_flipped += len(oids)
            logger.info("[WITHDRAW] mark_paid wd=%s flipped %d lines available→withdrawn for %s..%s",
                        wd_id, total_flipped, period_from, period_to)
            # Update last_withdrawn_period so the next FIFO computation
            # starts strictly AFTER period_to.
            await db.labels.update_one(
                {"id": wd["label_id"]},
                {"$set": {"last_withdrawn_period": period_to, "updated_at": now_iso()}},
            )

        await db.withdraw_requests.update_one({"id": wd_id}, {"$set": {
            "status": "paid", "paid_date": now_iso(), "paid_by": user["id"],
            "payment_proof_url": body.payment_proof_url, "payment_reference": body.payment_reference,
            "admin_note": body.note, "updated_at": now_iso(),
        }})
    else:
        raise HTTPException(status_code=400, detail="Aksi tidak dikenal")

    await log_activity(user["id"], f"withdraw_{body.action}", "withdraw", wd_id)
    # Notify label
    wd = await db.withdraw_requests.find_one({"id": wd_id}, {"_id": 0})
    user_ids = await label_user_ids(wd["label_id"])
    titles = {
        "approve": ("Withdraw disetujui", "Permintaan withdraw Anda telah disetujui. Menunggu pembayaran."),
        "reject": ("Withdraw ditolak", f"Permintaan withdraw ditolak. Alasan: {body.note or 'Lihat detail'}"),
        "mark_paid": ("Withdraw dibayar ✓", "Pembayaran telah dilakukan. Cek bukti transfer di dashboard."),
    }
    if body.action in titles:
        title, msg = titles[body.action]
        await notify_many(user_ids, f"withdraw_{body.action}", title, msg, "/label/withdraw", {"withdraw_id": wd_id})
    # Send withdraw-paid email (best-effort)
    if body.action == "mark_paid":
        try:
            label = await db.labels.find_one({"id": wd["label_id"]}, {"_id": 0, "label_name": 1})
            bank = await db.bank_accounts.find_one({"label_id": wd["label_id"]}, {"_id": 0, "bank_name": 1, "account_number": 1}) or {}
            for uid in user_ids:
                u = await db.users.find_one({"id": uid}, {"_id": 0, "email": 1})
                if u and u.get("email"):
                    await send_withdraw_paid_email(
                        to=u["email"],
                        label_name=(label or {}).get("label_name") or "Label",
                        amount_idr=int(wd.get("amount_idr") or 0),
                        bank_name=bank.get("bank_name") or "—",
                        account_number=bank.get("account_number") or "—",
                    )
        except Exception as e:
            logger.exception("withdraw paid email failed for %s: %s", wd_id, e)
    return wd


@withdraw_r.post("/admin/upload-proof")
async def admin_upload_proof(file: UploadFile = File(...), user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    ext = (file.filename or "").lower().split(".")[-1]
    if ext not in ("jpg", "jpeg", "png", "pdf"):
        raise HTTPException(status_code=400, detail="Format harus JPG/PNG/PDF")
    fid = new_id()
    import storage_service
    key = f"contract/proof_{fid}.{ext}"
    proof_bytes = await file.read()
    ct = "application/pdf" if ext == "pdf" else ("image/png" if ext == "png" else "image/jpeg")
    await storage_service.upload_bytes(key=key, data=proof_bytes, content_type=ct)
    return {"url": f"/api/files/{key}"}


@withdraw_r.post("/admin/verify-bank/{label_id}")
async def admin_verify_bank(label_id: str, user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    bank = await db.bank_accounts.find_one({"label_id": label_id})
    if not bank:
        raise HTTPException(status_code=404, detail="Rekening tidak ditemukan")
    await db.bank_accounts.update_one({"label_id": label_id}, {"$set": {"verified_status": "verified", "verified_by": user["id"], "verified_at": now_iso()}})
    await db.labels.update_one({"id": label_id}, {"$set": {"bank_verified": True, "updated_at": now_iso()}})
    await log_activity(user["id"], "verify_bank", "label", label_id)
    return {"ok": True}


