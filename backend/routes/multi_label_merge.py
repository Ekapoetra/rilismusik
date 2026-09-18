"""Multi Label — Existing Account Merge Wizard (Super Admin).

Merges several existing single-label accounts into ONE primary Multi Label account:
one login, one responsible person (PIC), one payout bank, many labels. Labels are
NOT combined — only account ownership is unified. Old accounts are archived as
`merged` (login disabled), never deleted. Financial cutoffs stay per-label until the
first Multi Label withdrawal batch syncs them. Legacy balances are never surfaced.

State machine: draft → validated → committing → completed | failed. Idempotent.
"""
from typing import List, Optional
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from models import now_iso, new_id
from .deps import db, logger, require_admin, notify, admin_user_ids
from .admin_permission_service import assert_admin_permission
from .balance_utils import compute_labels_available_balances

merge_r = APIRouter(prefix="/admin/multi-label", tags=["multi-label-merge"])
ml_public_r = APIRouter(prefix="/multi-label", tags=["multi-label-public"])

MULTI_LABEL_PRICE = 1_500_000
MERGES = "multi_label_merges"


class MergeBankNew(BaseModel):
    bank_name: str
    account_number: str
    account_holder_name: str


class MergeIn(BaseModel):
    label_ids: List[str]
    primary_user_id: str
    responsible_name: str
    responsible_email: str
    responsible_whatsapp: str
    payout_bank_account_id: Optional[str] = None  # existing bank id, or None when new_bank set
    new_bank: Optional[MergeBankNew] = None
    confirm: Optional[bool] = False


async def _load_context(body: MergeIn):
    label_ids = list(dict.fromkeys(body.label_ids))
    if len(label_ids) < 2:
        raise HTTPException(400, "Pilih minimal 2 label untuk digabungkan")
    labels = await db.labels.find({"id": {"$in": label_ids}}, {"_id": 0}).to_list(500)
    if len(labels) != len(label_ids):
        raise HTTPException(404, "Sebagian label tidak ditemukan")
    owner_ids = list(dict.fromkeys([l.get("user_id") for l in labels if l.get("user_id")]))
    users = await db.users.find({"id": {"$in": owner_ids}}, {"_id": 0, "password_hash": 0}).to_list(500)
    users_by_id = {u["id"]: u for u in users}
    return label_ids, labels, owner_ids, users_by_id


async def _validate(body: MergeIn):
    label_ids, labels, owner_ids, users_by_id = await _load_context(body)
    errors = []
    # every owner account must exist and be active (not merged/suspended)
    for uid in owner_ids:
        u = users_by_id.get(uid)
        if not u:
            errors.append(f"Akun pemilik label {uid} tidak ditemukan")
        elif u.get("status") in {"merged", "suspended", "disabled"}:
            errors.append(f"Akun {u.get('email')} berstatus {u.get('status')}, tidak dapat digabung")
    # primary must be one of the owners
    if body.primary_user_id not in owner_ids:
        errors.append("Akun utama harus salah satu pemilik label yang dipilih")
    # duplicate label protection: none already owned by a DIFFERENT active multi_label account
    for l in labels:
        if l.get("subscription_tier") == "multi_label" and l.get("user_id") != body.primary_user_id:
            errors.append(f"Label {l.get('label_name')} sudah menjadi authority Multi Label akun lain")
    # no other in-flight merge touching these labels
    active = await db[MERGES].find_one({
        "status": {"$in": ["draft", "validated", "committing"]},
        "label_ids": {"$in": label_ids},
    }, {"_id": 0, "id": 1})
    if active:
        errors.append("Ada proses merge lain yang masih berjalan untuk label ini")
    # payout bank
    payout = None
    if body.payout_bank_account_id:
        payout = await db.bank_accounts.find_one({"id": body.payout_bank_account_id}, {"_id": 0})
        if not payout or payout.get("label_id") not in label_ids:
            errors.append("Rekening pencairan tidak valid (harus milik salah satu label terpilih)")
    elif not body.new_bank:
        errors.append("Pilih rekening pencairan atau tambahkan rekening baru")

    # combined eligible balance (legacy excluded by compute helper)
    balances = await compute_labels_available_balances(labels)
    combined = int(sum(balances.values()))
    preview = {
        "labels": [{
            "id": l["id"], "label_name": l.get("label_name"),
            "email": (users_by_id.get(l.get("user_id")) or {}).get("email"),
            "pic_name": l.get("pic_name"),
            "package": l.get("subscription_tier") or "pay_per_release",
            "subscription_expires_at": l.get("subscription_expires_at"),
            "last_withdrawn_period": l.get("last_withdrawn_period"),
            "available_idr": int(balances.get(l["id"], 0)),
        } for l in labels],
        "primary_user_id": body.primary_user_id,
        "primary_email": (users_by_id.get(body.primary_user_id) or {}).get("email"),
        "responsible": {"name": body.responsible_name, "email": body.responsible_email, "whatsapp": body.responsible_whatsapp},
        "payout_bank": payout or (body.new_bank.model_dump() if body.new_bank else None),
        "payout_is_new": body.payout_bank_account_id is None,
        "combined_balance_idr": combined,
        "package": "multi_label",
        "price_idr": MULTI_LABEL_PRICE,
        "label_count": len(labels),
    }
    return errors, preview, labels, users_by_id, payout


class MultiLabelRequestIn(BaseModel):
    name: str
    email: str
    whatsapp: str
    label_info: Optional[str] = ""
    message: Optional[str] = ""


@ml_public_r.post("/request")
async def submit_multi_label_request(body: MultiLabelRequestIn):
    """Public lead: prospective Multi Label customer requests activation from landing."""
    name = (body.name or "").strip()
    email = (body.email or "").strip().lower()
    whatsapp = (body.whatsapp or "").strip()
    if not name or not email or not whatsapp:
        raise HTTPException(400, "Nama, email, dan WhatsApp wajib diisi")
    doc = {
        "id": new_id(), "name": name, "email": email, "whatsapp": whatsapp,
        "label_info": (body.label_info or "").strip(), "message": (body.message or "").strip(),
        "status": "new", "created_at": now_iso(), "updated_at": now_iso(),
    }
    await db.multi_label_requests.insert_one(doc)
    try:
        for uid in await admin_user_ids():
            await notify(uid, "Permintaan Multi Label baru", f"{name} ({email}) mengajukan Multi Label.", "info", "/admin/multi-label")
    except Exception:
        logger.exception("multi label request notify failed")
    return {"ok": True}


@merge_r.get("/requests")
async def list_multi_label_requests(user: dict = Depends(require_admin)):
    assert_admin_permission(user, "labels.multi_label.view")
    rows = await db.multi_label_requests.find({}, {"_id": 0}).sort("created_at", -1).to_list(300)
    return {"requests": rows}


@merge_r.post("/requests/{req_id}/handle")
async def handle_multi_label_request(req_id: str, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "labels.multi_label.manage")
    r = await db.multi_label_requests.update_one({"id": req_id}, {"$set": {"status": "handled", "handled_by": user["id"], "updated_at": now_iso()}})
    if not r.matched_count:
        raise HTTPException(404, "Permintaan tidak ditemukan")
    return {"ok": True}


@merge_r.get("/candidates")
async def merge_candidates(q: str = Query(default=""), user: dict = Depends(require_admin)):
    assert_admin_permission(user, "labels.multi_label.manage")
    query = {}
    if q:
        import re
        rx = {"$regex": re.escape(q), "$options": "i"}
        query = {"$or": [{"label_name": rx}, {"email": rx}, {"pic_name": rx}, {"id": rx}]}
    labels = await db.labels.find(query, {"_id": 0}).sort("created_at", -1).to_list(300)
    owner_ids = list(dict.fromkeys([l.get("user_id") for l in labels if l.get("user_id")]))
    users = await db.users.find({"id": {"$in": owner_ids}}, {"_id": 0, "id": 1, "email": 1, "status": 1}).to_list(500)
    by_id = {u["id"]: u for u in users}
    out = []
    for l in labels:
        u = by_id.get(l.get("user_id")) or {}
        out.append({
            "label_id": l["id"], "label_name": l.get("label_name"),
            "user_id": l.get("user_id"), "email": u.get("email") or l.get("email"),
            "user_status": u.get("status"), "pic_name": l.get("pic_name"),
            "whatsapp": l.get("whatsapp"),
            "package": l.get("subscription_tier") or "pay_per_release",
            "subscription_expires_at": l.get("subscription_expires_at"),
            "already_merged": u.get("status") == "merged",
            "is_multi_label": l.get("subscription_tier") == "multi_label",
        })
    return {"candidates": out}


@merge_r.post("/merge/validate")
async def merge_validate(body: MergeIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "labels.multi_label.manage")
    errors, preview, *_ = await _validate(body)
    return {"ok": not errors, "errors": errors, "preview": preview}


@merge_r.post("/merge/commit")
async def merge_commit(body: MergeIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "labels.multi_label.manage")
    if not body.confirm:
        raise HTTPException(400, "Konfirmasi diperlukan untuk menjalankan merge")
    errors, preview, labels, users_by_id, payout = await _validate(body)
    if errors:
        raise HTTPException(400, {"code": "MERGE_VALIDATION_FAILED", "errors": errors})

    label_ids = [l["id"] for l in labels]
    # Idempotency: authority already multi_label + all labels owned by primary → done.
    authority = next((l for l in labels if l.get("user_id") == body.primary_user_id), labels[0])
    if authority.get("subscription_tier") == "multi_label" and all(l.get("user_id") == body.primary_user_id for l in labels):
        existing = await db[MERGES].find_one({"label_ids": {"$all": label_ids}, "status": "completed"}, {"_id": 0})
        if existing:
            return {"ok": True, "merge": existing, "idempotent": True}

    merge_id = new_id()
    before = {l["id"]: {"user_id": l.get("user_id"), "tier": l.get("subscription_tier"),
                        "last_withdrawn_period": l.get("last_withdrawn_period")} for l in labels}
    merge_doc = {
        "id": merge_id, "status": "committing", "label_ids": label_ids,
        "primary_user_id": body.primary_user_id, "started_by": user["id"],
        "before": before, "created_at": now_iso(), "updated_at": now_iso(),
    }
    await db[MERGES].insert_one(merge_doc)

    try:
        now = now_iso()
        far = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        # 1) Reassign all labels to the primary account (labels themselves untouched otherwise).
        await db.labels.update_many({"id": {"$in": label_ids}},
                                    {"$set": {"user_id": body.primary_user_id, "updated_at": now}})
        # 2) Activate Multi Label entitlement on the authority (primary) label.
        await db.labels.update_one({"id": authority["id"]}, {"$set": {
            "payment_type": "annual_subscription", "subscription_tier": "multi_label",
            "subscription_status": "active", "subscription_expires_at": far,
            "multi_label_started_at": now, "updated_at": now,
        }, "$inc": {"package_revision": 1}})
        # 3) Payout bank → account level.
        if payout:
            payout_bank_id = payout["id"]
        else:
            payout_bank_id = new_id()
            await db.bank_accounts.insert_one({
                "id": payout_bank_id, "label_id": authority["id"],
                "bank_name": body.new_bank.bank_name, "account_number": body.new_bank.account_number,
                "account_holder_name": body.new_bank.account_holder_name,
                "verified_status": "pending",  # new bank must go through verify workflow
                "created_at": now, "updated_at": now,
            })
        # 4) Primary user becomes the account identity.
        await db.users.update_one({"id": body.primary_user_id}, {"$set": {
            "primary_label_id": authority["id"], "active_label_id": authority["id"],
            "payout_bank_account_id": payout_bank_id,
            "responsible_name": body.responsible_name, "responsible_email": body.responsible_email,
            "responsible_whatsapp": body.responsible_whatsapp,
            "multi_label_started_at": now, "updated_at": now,
        }})
        # 5) Archive old (non-primary) accounts as merged (login disabled, history intact).
        old_ids = list({before[lid]["user_id"] for lid in before
                        if before[lid]["user_id"] and before[lid]["user_id"] != body.primary_user_id})
        if old_ids:
            await db.users.update_many({"id": {"$in": old_ids}}, {"$set": {
                "status": "merged", "merged_into_user_id": body.primary_user_id,
                "merged_at": now, "merged_by": user["id"], "updated_at": now,
            }})
        # 6) Complete.
        after = {"authority_label_id": authority["id"], "payout_bank_account_id": payout_bank_id,
                 "archived_user_ids": old_ids, "combined_balance_idr": preview["combined_balance_idr"]}
        await db[MERGES].update_one({"id": merge_id}, {"$set": {
            "status": "completed", "after": after, "label_count": len(label_ids),
            "responsible": preview["responsible"], "completed_at": now, "updated_at": now,
        }})
    except Exception:
        logger.exception("Multi Label merge %s failed", merge_id)
        await db[MERGES].update_one({"id": merge_id}, {"$set": {"status": "failed", "updated_at": now_iso()}})
        raise HTTPException(500, {"code": "MERGE_FAILED", "merge_id": merge_id,
                                  "detail": "Merge gagal dan tidak diselesaikan. Hubungi engineering untuk recovery."})

    try:
        await notify(body.primary_user_id, "Multi Label berhasil diaktifkan",
                     f"{len(label_ids)} label kini dapat dikelola dalam satu akun.", "info", "/label/dashboard")
    except Exception:
        logger.exception("merge notify failed")

    merged = await db[MERGES].find_one({"id": merge_id}, {"_id": 0})
    return {"ok": True, "merge": merged}


@merge_r.get("/accounts")
async def multi_label_accounts(user: dict = Depends(require_admin)):
    assert_admin_permission(user, "labels.multi_label.view")
    authorities = await db.labels.find({"subscription_tier": "multi_label"}, {"_id": 0}).to_list(500)
    out = []
    for auth in authorities:
        uid = auth.get("user_id")
        u = await db.users.find_one({"id": uid}, {"_id": 0, "password_hash": 0}) or {}
        owned = await db.labels.find({"user_id": uid}, {"_id": 0}).to_list(200)
        balances = await compute_labels_available_balances(owned)
        payout = None
        if u.get("payout_bank_account_id"):
            payout = await db.bank_accounts.find_one({"id": u["payout_bank_account_id"]}, {"_id": 0})
        last_batch = await db["multi_label_withdraw_batches"].find_one({"user_id": uid}, {"_id": 0}, sort=[("created_at", -1)])
        out.append({
            "primary_user_id": uid, "primary_email": u.get("email"),
            "responsible": {"name": u.get("responsible_name"), "email": u.get("responsible_email"), "whatsapp": u.get("responsible_whatsapp")},
            "payout_bank": payout,
            "package": "multi_label", "expires_at": auth.get("subscription_expires_at"),
            "multi_label_started_at": auth.get("multi_label_started_at"),
            "labels": [{"id": l["id"], "label_name": l.get("label_name"), "available_idr": int(balances.get(l["id"], 0))} for l in owned],
            "label_count": len(owned),
            "aggregate_balance_idr": int(sum(balances.values())),
            "last_withdrawal": last_batch,
        })
    return {"accounts": out}
