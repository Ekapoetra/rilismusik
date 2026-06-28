"""CMS landing settings router."""
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
#                                CMS
# =============================================================================
cms_r = APIRouter(prefix="/cms", tags=["cms"])


@cms_r.get("/landing")
async def get_landing(user: Optional[dict] = None):
    """Public endpoint — returns all landing page settings as key/value map."""
    settings = await db.landing_settings.find({}, {"_id": 0}).to_list(500)
    result = {s["key"]: s["value"] for s in settings}
    return result


@cms_r.patch("/landing")
async def update_landing(body: CMSUpdateIn, user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_content"):
        raise HTTPException(status_code=403, detail="Hanya Admin Content/CMS atau Super Admin")
    for k, v in body.settings.items():
        await db.landing_settings.update_one(
            {"key": k},
            {"$set": {"key": k, "value": v, "updated_by": user["id"], "updated_at": now_iso()}},
            upsert=True,
        )
    await log_activity(user["id"], "update_landing", "cms", None, after=body.settings)
    settings = await db.landing_settings.find({}, {"_id": 0}).to_list(500)
    return {s["key"]: s["value"] for s in settings}


@cms_r.post("/landing/upload-image")
async def upload_landing_image(file: UploadFile = File(...), user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_content"):
        raise HTTPException(status_code=403, detail="Hanya Admin Content/CMS atau Super Admin")
    ext = (file.filename or "").lower().split(".")[-1]
    if ext not in ("jpg", "jpeg", "png", "webp", "svg"):
        raise HTTPException(status_code=400, detail="Format gambar tidak didukung")
    fid = new_id()
    import storage_service
    key = f"landing/{fid}.{ext}"
    img_bytes = await file.read()
    ct_map = {"svg": "image/svg+xml", "webp": "image/webp", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}
    await storage_service.upload_bytes(key=key, data=img_bytes, content_type=ct_map.get(ext, "image/jpeg"))
    return {"url": f"/api/files/{key}"}


@cms_r.get("/mda/preview")
async def mda_preview():
    """Public endpoint — generates and streams a sample MDA PDF with placeholder
    label data so prospective users can review the contract BEFORE registering.

    PDF is rendered in-memory each call (small file, rare op) — no disk write.
    """
    from .mda_generator import generate_mda_pdf_bytes
    legal_setting = await db.landing_settings.find_one({"key": "legal_entity"}, {"_id": 0, "value": 1})
    legal_entity = (legal_setting or {}).get("value") or {}
    sample_label = {
        "label_name": "[Nama Label Anda]",
        "pic_name": "[Nama PIC]",
        "email": "[email anda]",
        "whatsapp": "[WhatsApp]",
        "label_type": "label",
        "created_at": now_iso(),
    }
    pdf_bytes = generate_mda_pdf_bytes(sample_label, legal_entity)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="RILIS-MUSIK-MDA-Preview.pdf"'},
    )


