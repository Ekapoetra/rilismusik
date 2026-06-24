"""Distribution contracts router."""
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
#                              CONTRACTS
# =============================================================================
contract_r = APIRouter(prefix="/contracts", tags=["contracts"])


def _contract_effective_status(c: Dict[str, Any]) -> str:
    """Compute effective status from stored status + dates.

    A null end_date means lifetime / no expiry — always 'active' unless
    explicitly terminated.
    """
    if c.get("status") == "terminated":
        return "terminated"
    end = c.get("end_date")
    if not end:  # lifetime contract
        return "active"
    today = datetime.now(timezone.utc).date().isoformat()
    if end < today:
        return "expired"
    # within 30 days?
    try:
        end_dt = datetime.strptime(end, "%Y-%m-%d").date()
        today_dt = datetime.now(timezone.utc).date()
        days_left = (end_dt - today_dt).days
        if 0 <= days_left <= 30:
            return "expiring_soon"
    except Exception:
        pass
    return "active"


def _enrich_contract(c: Dict[str, Any]) -> Dict[str, Any]:
    c["effective_status"] = _contract_effective_status(c)
    if not c.get("end_date"):
        c["days_left"] = None  # lifetime contract
        c["is_lifetime"] = True
        return c
    try:
        end_dt = datetime.strptime(c.get("end_date", ""), "%Y-%m-%d").date()
        today_dt = datetime.now(timezone.utc).date()
        c["days_left"] = (end_dt - today_dt).days
    except Exception:
        c["days_left"] = None
    c["is_lifetime"] = False
    return c


@contract_r.post("/admin/upload-pdf")
async def contract_upload_pdf(file: UploadFile = File(...), user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_release"):
        raise HTTPException(status_code=403, detail="Hanya Admin Release / Super Admin")
    ext = (file.filename or "").lower().rsplit(".", 1)[-1]
    if ext != "pdf":
        raise HTTPException(status_code=400, detail="File kontrak harus PDF")
    fid = new_id()
    target = UPLOAD_DIR / "contract" / f"{fid}.pdf"
    with open(target, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"url": f"/api/files/contract/{fid}.pdf", "filename": file.filename}


@contract_r.post("/admin")
async def contract_create(body: ContractCreateIn, user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_release"):
        raise HTTPException(status_code=403, detail="Hanya Admin Release / Super Admin")
    label = await db.labels.find_one({"id": body.label_id}, {"_id": 0, "id": 1, "label_name": 1, "user_id": 1})
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    if body.end_date and body.end_date <= body.start_date:
        raise HTTPException(status_code=400, detail="Tanggal berakhir harus setelah tanggal mulai")
    cid = new_id()
    doc = {
        "id": cid,
        "label_id": body.label_id,
        "label_name": label.get("label_name"),
        "file_url": body.file_url,
        "filename": body.filename,
        "start_date": body.start_date,
        "end_date": body.end_date,
        "notes": body.notes,
        "status": "active",
        "terminated_at": None,
        "terminated_reason": None,
        "created_by": user["id"],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.contracts.insert_one(doc)
    await log_activity(user["id"], "contract_create", "contract", cid, after={"label_id": body.label_id, "end_date": body.end_date})
    if label.get("user_id"):
        await notify(
            label["user_id"], "contract_created",
            "Kontrak baru ditambahkan",
            f"Kontrak berlaku {body.start_date} → {body.end_date}.",
            "/label/contract", {"contract_id": cid},
        )
    return _enrich_contract({k: v for k, v in doc.items() if k != "_id"})


@contract_r.get("/admin")
async def contract_list_admin(
    user: dict = Depends(require_admin),
    label_id: Optional[str] = None,
    status: Optional[str] = None,  # active|expiring_soon|expired|terminated
):
    filt: Dict[str, Any] = {}
    if label_id:
        filt["label_id"] = label_id
    items = await db.contracts.find(filt, {"_id": 0}).sort("created_at", -1).to_list(1000)
    items = [_enrich_contract(c) for c in items]
    if status:
        items = [c for c in items if c["effective_status"] == status]
    return items


@contract_r.get("/admin/{cid}")
async def contract_detail_admin(cid: str, user: dict = Depends(require_admin)):
    c = await db.contracts.find_one({"id": cid}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Kontrak tidak ditemukan")
    return _enrich_contract(c)


@contract_r.post("/admin/{cid}/extend")
async def contract_extend(cid: str, body: ContractExtendIn, user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_release"):
        raise HTTPException(status_code=403, detail="Hanya Admin Release / Super Admin")
    c = await db.contracts.find_one({"id": cid})
    if not c:
        raise HTTPException(status_code=404, detail="Kontrak tidak ditemukan")
    if body.new_end_date <= c["start_date"]:
        raise HTTPException(status_code=400, detail="Tanggal baru harus setelah tanggal mulai")
    await db.contracts.update_one({"id": cid}, {"$set": {
        "end_date": body.new_end_date, "status": "active", "terminated_at": None, "terminated_reason": None,
        "notes": body.notes or c.get("notes"), "updated_at": now_iso(),
    }})
    await log_activity(user["id"], "contract_extend", "contract", cid, after={"new_end_date": body.new_end_date})
    user_ids = await label_user_ids(c["label_id"])
    await notify_many(user_ids, "contract_extended", "Kontrak diperpanjang",
                      f"Berlaku hingga {body.new_end_date}.", "/label/contract", {"contract_id": cid})
    return _enrich_contract(await db.contracts.find_one({"id": cid}, {"_id": 0}))


@contract_r.post("/admin/{cid}/terminate")
async def contract_terminate(cid: str, body: ContractTerminateIn, user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_release"):
        raise HTTPException(status_code=403, detail="Hanya Admin Release / Super Admin")
    c = await db.contracts.find_one({"id": cid})
    if not c:
        raise HTTPException(status_code=404, detail="Kontrak tidak ditemukan")
    await db.contracts.update_one({"id": cid}, {"$set": {
        "status": "terminated", "terminated_at": now_iso(),
        "terminated_reason": body.reason, "updated_at": now_iso(),
    }})
    await log_activity(user["id"], "contract_terminate", "contract", cid, after={"reason": body.reason})
    user_ids = await label_user_ids(c["label_id"])
    await notify_many(user_ids, "contract_terminated", "Kontrak diakhiri",
                      f"Alasan: {body.reason}", "/label/contract", {"contract_id": cid})
    return _enrich_contract(await db.contracts.find_one({"id": cid}, {"_id": 0}))


@contract_r.get("/label")
async def contract_list_label(user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    items = await db.contracts.find({"label_id": label["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return [_enrich_contract(c) for c in items]


