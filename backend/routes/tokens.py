"""Token wallet and release service modes (prototype V13, ANNEX-E).

A token is an optional second payment route next to rupiah: bought through Xendit at
a flat price, it never expires and cannot be withdrawn. Express and MAX releases are
paid with tokens per track; Standard keeps the package rules (Basic pays rupiah per
song, annual packages are free).

Wallets are one document per account (the label owner), so Multi Label accounts
share one balance. Every change applies through a single conditional update that
also records its idempotency key on the wallet, so a retried fulfillment or a
concurrent submit can never apply twice or overdraw. `token_ledger` keeps the
immutable history.
"""
import math
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from models import new_id, now_iso
from .deps import db, get_label_by_user, logger, require_label, require_super_admin

tokens_r = APIRouter(prefix="/tokens", tags=["tokens"])
admin_tokens_r = APIRouter(prefix="/admin/tokens", tags=["admin-tokens"])

WIB = ZoneInfo("Asia/Jakarta")
SERVICE_MODES = ("standard", "express", "max")
MODE_NAMES = {"standard": "Standar", "express": "Express", "max": "MAX"}
DEFAULT_SETTINGS: Dict[str, Any] = {
    "token_price_idr": 35000,
    # Tokens per track. Standard follows the package (rupiah per song or free).
    "mode_tokens": {"express": 2, "max": 3},
    # Earliest release date in working days (Mon-Fri) after submission.
    "lead_working_days": {"standard": 7, "express": 5, "max": 3},
}
MAX_PURCHASE = 500


async def token_settings() -> Dict[str, Any]:
    stored = await db.platform_settings.find_one({"key": "tokens"}, {"_id": 0}) or {}
    settings = {**DEFAULT_SETTINGS, **{k: v for k, v in stored.items() if k in DEFAULT_SETTINGS}}
    settings["mode_tokens"] = {**DEFAULT_SETTINGS["mode_tokens"], **(stored.get("mode_tokens") or {})}
    settings["lead_working_days"] = {**DEFAULT_SETTINGS["lead_working_days"], **(stored.get("lead_working_days") or {})}
    return settings


# ---------------- Release service modes ----------------

def earliest_release_date(mode: str, settings: Dict[str, Any], now: Optional[datetime] = None) -> Optional[date]:
    """Earliest digital release date for a mode, counted in WIB working days.

    MAX on a Friday follows the prototype: before 12:00 WIB the release may go out
    on Sunday; after 12:00 MAX is unavailable until Monday.
    """
    local = (now or datetime.now(timezone.utc)).astimezone(WIB)
    if mode == "max" and local.weekday() == 4:
        return None if local.hour >= 12 else local.date() + timedelta(days=2)
    remaining = int(settings["lead_working_days"].get(mode, 7))
    day = local.date()
    while remaining > 0:
        day += timedelta(days=1)
        if day.weekday() < 5:
            remaining -= 1
    return day


def validate_mode_release_date(release_date: Any, mode: str, settings: Dict[str, Any]) -> None:
    if mode not in SERVICE_MODES:
        raise HTTPException(status_code=400, detail="Mode rilis tidak dikenal")
    try:
        chosen = date.fromisoformat(str(release_date)[:10])
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Tanggal rilis digital tidak valid") from None
    first = earliest_release_date(mode, settings)
    if first is None:
        raise HTTPException(status_code=400, detail="Mode MAX tidak tersedia Jumat setelah pukul 12.00 WIB")
    if chosen < first:
        raise HTTPException(status_code=400, detail=f"Tanggal rilis untuk mode {MODE_NAMES[mode]} paling cepat {first.isoformat()}")


def mode_token_cost(mode: str, track_count: int, settings: Dict[str, Any]) -> int:
    if mode == "standard":
        return 0
    return int(settings["mode_tokens"][mode]) * max(1, int(track_count))


def token_covers_release(rel: Dict[str, Any]) -> bool:
    """Express/MAX releases paid with tokens need no rupiah invoice."""
    return rel.get("billing_flow") == "token" and rel.get("token_status") in ("reserved", "settled")


# ---------------- Wallet ----------------

async def account_id_for_label(label: Dict[str, Any]) -> str:
    return label.get("user_id") or f"label:{label['id']}"


async def wallet_balance(account_id: str) -> int:
    wallet = await db.token_wallets.find_one({"account_id": account_id}, {"_id": 0, "balance": 1})
    return int((wallet or {}).get("balance") or 0)


async def apply_tokens(*, account_id: str, label_id: Optional[str], tokens: int, kind: str, key: str,
                       ref_type: Optional[str] = None, ref_id: Optional[str] = None, note: Optional[str] = None,
                       actor_id: Optional[str] = None) -> bool:
    """Apply a signed token change exactly once. Returns False if already applied.

    Debits only succeed when the balance covers them (402 otherwise).
    """
    tokens = int(tokens)
    if tokens == 0:
        return False
    if await db.token_wallets.find_one({"account_id": account_id, "applied_keys": key}, {"_id": 1}):
        return False
    query: Dict[str, Any] = {"account_id": account_id, "applied_keys": {"$ne": key}}
    if tokens < 0:
        query["balance"] = {"$gte": -tokens}
    update = {"$inc": {"balance": tokens}, "$push": {"applied_keys": key}, "$set": {"updated_at": now_iso()}}
    try:
        result = await db.token_wallets.update_one(query, update, upsert=tokens > 0)
    except DuplicateKeyError:
        # A concurrent first credit created the wallet; retry once against it.
        result = await db.token_wallets.update_one(query, update)
    if not result.modified_count and not result.upserted_id:
        if await db.token_wallets.find_one({"account_id": account_id, "applied_keys": key}, {"_id": 1}):
            return False
        raise HTTPException(status_code=402, detail="Saldo token tidak cukup")
    entry = {"id": new_id(), "key": key, "account_id": account_id, "label_id": label_id, "kind": kind, "tokens": tokens,
             "ref_type": ref_type, "ref_id": ref_id, "note": note, "created_by": actor_id, "created_at": now_iso()}
    try:
        await db.token_ledger.insert_one(entry)
    except DuplicateKeyError:
        pass
    return True


async def reserve_release_tokens(rel: Dict[str, Any], label: Dict[str, Any], mode: str, track_count: int,
                                 settings: Dict[str, Any], actor_id: str) -> Dict[str, Any]:
    """Charge (or refund) the difference between the new cost and what is already reserved."""
    cost = mode_token_cost(mode, track_count, settings)
    held = int(rel.get("token_reserved") or 0) if rel.get("token_status") == "reserved" else 0
    delta = cost - held
    revision = int(rel.get("token_revision") or 0) + 1
    account_id = rel.get("token_account_id") or await account_id_for_label(label)
    if delta:
        await apply_tokens(account_id=account_id, label_id=label["id"], tokens=-delta,
                           kind="release_reserve" if delta > 0 else "release_refund",
                           key=f"release:{rel['id']}:{revision}", ref_type="release", ref_id=rel["id"],
                           note=f"{MODE_NAMES[mode]} · {track_count} lagu", actor_id=actor_id)
    return {"token_reserved": cost, "token_status": "reserved" if cost else None, "token_revision": revision,
            "token_account_id": account_id if cost else None}


async def undo_release_token_change(rel: Dict[str, Any], label: Dict[str, Any], token_fields: Dict[str, Any], actor_id: str) -> None:
    """Reverse a reservation whose release update lost a race (best effort)."""
    held = int(rel.get("token_reserved") or 0) if rel.get("token_status") == "reserved" else 0
    delta = int(token_fields.get("token_reserved") or 0) - held
    if not delta:
        return
    account_id = token_fields.get("token_account_id") or rel.get("token_account_id") or await account_id_for_label(label)
    try:
        await apply_tokens(account_id=account_id, label_id=label["id"], tokens=delta,
                           kind="release_refund" if delta > 0 else "release_reserve",
                           key=f"release:{rel['id']}:{token_fields['token_revision']}:undo", ref_type="release",
                           ref_id=rel["id"], note="Pengajuan dibatalkan sistem", actor_id=actor_id)
    except HTTPException:
        logger.exception("Token undo failed for release %s", rel["id"])


async def refund_release_tokens(rel: Dict[str, Any], actor_id: Optional[str], reason: str) -> Optional[Dict[str, Any]]:
    if rel.get("token_status") != "reserved" or not rel.get("token_reserved"):
        return None
    revision = int(rel.get("token_revision") or 0) + 1
    await apply_tokens(account_id=rel["token_account_id"], label_id=rel.get("label_id"), tokens=int(rel["token_reserved"]),
                       kind="release_refund", key=f"release:{rel['id']}:{revision}", ref_type="release", ref_id=rel["id"],
                       note=reason, actor_id=actor_id)
    return {"token_status": "refunded", "token_revision": revision}


# ---------------- Label endpoints ----------------

def _mode_options(settings: Dict[str, Any], track_count: int) -> List[Dict[str, Any]]:
    options = []
    for mode in SERVICE_MODES:
        first = earliest_release_date(mode, settings)
        options.append({"id": mode, "name": MODE_NAMES[mode], "lead_working_days": int(settings["lead_working_days"][mode]),
                        "earliest_date": first.isoformat() if first else None, "available": first is not None,
                        "tokens_per_track": int(settings["mode_tokens"].get(mode, 0)), "tokens": mode_token_cost(mode, track_count, settings)})
    return options


@tokens_r.get("/me")
async def my_tokens(user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    account_id = await account_id_for_label(label)
    settings = await token_settings()
    ledger = await db.token_ledger.find({"account_id": account_id}, {"_id": 0, "key": 0}).sort("created_at", -1).to_list(50)
    return {"balance": await wallet_balance(account_id), "token_price_idr": int(settings["token_price_idr"]),
            "mode_tokens": settings["mode_tokens"], "max_purchase": MAX_PURCHASE, "ledger": ledger}


@tokens_r.get("/release-modes")
async def release_modes(tracks: int = Query(1, ge=1, le=200), user: dict = Depends(require_label)):
    label = await get_label_by_user(user)
    settings = await token_settings()
    return {"balance": await wallet_balance(await account_id_for_label(label)), "modes": _mode_options(settings, tracks)}


class TokenPurchaseIn(BaseModel):
    quantity: int = Field(ge=1, le=MAX_PURCHASE)


@tokens_r.post("/purchase")
async def purchase_tokens(body: TokenPurchaseIn, user: dict = Depends(require_label)):
    from payment_service import PaymentCreateData, create_payment_document
    label = await get_label_by_user(user)
    settings = await token_settings()
    price = int(settings["token_price_idr"])
    return await create_payment_document(PaymentCreateData(
        label_id=label["id"], payment_type="token_pack", amount=price * body.quantity,
        description=f"{body.quantity} token Rilis Musik", return_path="/label/invoices",
        line_items=[{"name": "Token Rilis Musik", "quantity": body.quantity, "amount": price}],
        token_quantity=body.quantity,
    ))


async def fulfill_token_pack(payment: Dict[str, Any]) -> None:
    """Payment fulfillment handler: credit the purchased tokens exactly once."""
    label = await db.labels.find_one({"id": payment["label_id"]}, {"_id": 0, "id": 1, "user_id": 1})
    if not label:
        raise ValueError("Label for token purchase not found")
    quantity = int(payment.get("token_quantity") or 0)
    if quantity <= 0:
        raise ValueError("Token purchase without quantity")
    await apply_tokens(account_id=await account_id_for_label(label), label_id=label["id"], tokens=quantity,
                       kind="purchase", key=f"purchase:{payment['id']}", ref_type="payment", ref_id=payment["id"],
                       note=payment.get("description"))


# ---------------- Super Admin endpoints ----------------

@admin_tokens_r.get("/settings")
async def get_token_settings(user: dict = Depends(require_super_admin)):
    from payment_service import payment_price
    settings = await token_settings()
    price = int(settings["token_price_idr"])
    services = [("pay_per_release", "Rilisan · per lagu"), ("album_package", "Paket album"), ("wami_addon", "Registrasi WAMI")]
    rows = []
    for code, name in services:
        rupiah = await payment_price(code)
        rows.append({"code": code, "name": name, "price_idr": rupiah})
    async for product in db.payment_products.find({"active": True}, {"_id": 0, "id": 1, "name": 1, "amount": 1}):
        rows.append({"code": product["id"], "name": product.get("name"), "price_idr": int(product.get("amount") or 0)})
    for row in rows:
        tokens = math.ceil(row["price_idr"] / price) if row["price_idr"] else 0
        diff = row["price_idr"] - tokens * price
        # Token is offered only when strictly cheaper than rupiah (prototype verdict104).
        row.update({"tokens": tokens, "token_cost_idr": tokens * price,
                    "verdict": "not_offered" if not tokens else "cheaper" if diff > 0 else "equal" if diff == 0 else "more_expensive"})
    return {**settings, "services": rows}


class TokenSettingsIn(BaseModel):
    token_price_idr: int = Field(ge=1000, le=10_000_000)
    mode_tokens: Dict[Literal["express", "max"], int]
    lead_working_days: Dict[Literal["standard", "express", "max"], int]


@admin_tokens_r.put("/settings")
async def update_token_settings(body: TokenSettingsIn, user: dict = Depends(require_super_admin)):
    tokens = {**DEFAULT_SETTINGS["mode_tokens"], **body.mode_tokens}
    days = {**DEFAULT_SETTINGS["lead_working_days"], **body.lead_working_days}
    if not 1 <= tokens["express"] <= tokens["max"] <= 100:
        raise HTTPException(status_code=400, detail="Token Express harus ≥1 dan tidak lebih dari MAX (maks 100)")
    if not 1 <= days["max"] <= days["express"] <= days["standard"] <= 60:
        raise HTTPException(status_code=400, detail="Hari kerja harus Standar ≥ Express ≥ MAX ≥ 1")
    before = await db.platform_settings.find_one({"key": "tokens"}, {"_id": 0})
    document = {"key": "tokens", "token_price_idr": body.token_price_idr, "mode_tokens": tokens, "lead_working_days": days,
                "updated_by": user["id"], "updated_at": now_iso()}
    await db.platform_settings.update_one({"key": "tokens"}, {"$set": document}, upsert=True)
    await db.platform_settings_history.insert_one({"id": new_id(), "key": "tokens", "before": before, "after": document, "created_at": now_iso()})
    return await get_token_settings(user)


@admin_tokens_r.get("/wallets")
async def token_wallets(user: dict = Depends(require_super_admin)):
    settings = await token_settings()
    wallets = await db.token_wallets.find({}, {"_id": 0, "applied_keys": 0}).sort("balance", -1).to_list(5000)
    owners = {item["id"]: item for item in await db.users.find({"id": {"$in": [w["account_id"] for w in wallets]}}, {"_id": 0, "id": 1, "name": 1, "email": 1}).to_list(5000)}
    labels: Dict[str, List[str]] = {}
    async for label in db.labels.find({"user_id": {"$in": list(owners)}}, {"_id": 0, "user_id": 1, "label_name": 1}):
        labels.setdefault(label["user_id"], []).append(label.get("label_name"))
    reserved: Dict[str, int] = {}
    async for row in db.releases.aggregate([
        {"$match": {"token_status": "reserved"}},
        {"$group": {"_id": "$token_account_id", "tokens": {"$sum": "$token_reserved"}}},
    ]):
        reserved[str(row["_id"])] = int(row.get("tokens") or 0)
    rows = [{"account_id": w["account_id"], "name": (owners.get(w["account_id"]) or {}).get("name"),
             "labels": labels.get(w["account_id"], []), "balance": int(w.get("balance") or 0),
             "reserved": reserved.get(w["account_id"], 0), "updated_at": w.get("updated_at")} for w in wallets]
    outstanding = sum(row["balance"] for row in rows)
    ledger = await db.token_ledger.find({}, {"_id": 0, "key": 0}).sort("created_at", -1).to_list(100)
    return {"token_price_idr": settings["token_price_idr"], "outstanding_tokens": outstanding,
            "reserved_tokens": sum(reserved.values()), "outstanding_value_idr": outstanding * int(settings["token_price_idr"]),
            "wallets": rows, "ledger": ledger}


class TokenAdjustIn(BaseModel):
    label_id: str
    tokens: int = Field(ge=-500, le=500)
    reason: str = Field(min_length=5, max_length=500)


@admin_tokens_r.post("/adjust")
async def adjust_tokens(body: TokenAdjustIn, user: dict = Depends(require_super_admin)):
    if body.tokens == 0:
        raise HTTPException(status_code=400, detail="Jumlah token tidak boleh 0")
    label = await db.labels.find_one({"id": body.label_id}, {"_id": 0, "id": 1, "user_id": 1})
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    account_id = await account_id_for_label(label)
    await apply_tokens(account_id=account_id, label_id=label["id"], tokens=body.tokens, kind="admin_adjust",
                       key=f"adjust:{new_id()}", note=body.reason.strip(), actor_id=user["id"])
    return {"account_id": account_id, "balance": await wallet_balance(account_id)}
