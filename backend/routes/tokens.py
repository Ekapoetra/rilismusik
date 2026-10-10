"""D1 — Token wallet endpoints: label wallet + super-admin manual credit."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from models import now_iso
from .deps import (
    db, get_label_by_user, log_activity, require_admin, require_label,
    require_super_admin,
)
from .admin_permission_service import assert_admin_permission
from .entitlements import resolve_label_entitlements
from token_service import (
    credit_purchased, get_token_config, jakarta_today, token_offer,
    wallet_state,
)

router = APIRouter(tags=["tokens"])


class TokenGrantIn(BaseModel):
    label_id: str = Field(min_length=1)
    quantity: int = Field(ge=1, le=500)
    note: str = Field(min_length=3, max_length=500)


# ---------------------------------------------------------------------------
# Label wallet
# ---------------------------------------------------------------------------

@router.get("/token/wallet")
async def token_wallet(user=Depends(require_label)):
    label = await get_label_by_user(user)
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    cfg = await get_token_config()
    history = await db.token_ledger.find(
        {"label_id": label["id"]},
        {"_id": 0, "label_id": 0},
    ).sort("created_at", -1).to_list(50)
    return {**wallet_state(label, cfg), "ledger": history}


@router.get("/token/offer/{service_key}")
async def token_offer_check(service_key: str, rupiah: int = Query(ge=0), user=Depends(require_label)):
    """Token price for one service; offered only when strictly cheaper than
    the rupiah price (token is the optional second payment rail)."""
    await get_label_by_user(user)
    cfg = await get_token_config()
    return token_offer(cfg, service_key, int(rupiah))


@router.get("/token/config")
async def token_public_config(user=Depends(require_label)):
    """Label-facing config: prices + own tier quota (no edit surface)."""
    label = await get_label_by_user(user)
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    cfg = await get_token_config()
    tier = resolve_label_entitlements(label).get("package") or "pay_per_release"
    cfg["daily_quota"] = {tier: cfg["daily_quota"].get(tier, 0)}
    cfg["service_tokens"] = {k: v for k, v in cfg["service_tokens"].items() if v > 0}
    return cfg


# ---------------------------------------------------------------------------
# Super admin — manual credit (token CONFIG lives in /admin/system/token)
# ---------------------------------------------------------------------------

@router.post("/admin/token/grant")
async def admin_token_grant(payload: TokenGrantIn, admin=Depends(require_super_admin)):
    """Manual token credit (operational correction). Purchased pool; audited."""
    label = await db.labels.find_one({"id": payload.label_id}, {"_id": 0, "id": 1, "label_name": 1})
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    result = await credit_purchased(
        payload.label_id, payload.quantity, "admin_grant", admin["id"],
        payload.note, actor_id=admin["id"], kind="admin_grant",
    )
    await log_activity(
        admin["id"], "token_grant", "token", payload.label_id,
        after={"quantity": payload.quantity, "note": payload.note},
    )
    return {"granted": payload.quantity, "token_balance": result["token_balance"],
            "label": label.get("label_name")}


# ---------------------------------------------------------------------------
# Admin — token liability monitoring (D1-c)
# ---------------------------------------------------------------------------

@router.get("/admin/token/liability")
async def admin_token_liability(admin=Depends(require_admin)):
    """Token outstanding is a LIABILITY (redeemable services), not revenue.
    Purchased balances never expire; daily quota resets each WIB day."""
    assert_admin_permission(admin, "payments.view")
    cfg = await get_token_config()
    price = cfg["token_price_idr"]
    today = jakarta_today()
    labels = await db.labels.find(
        {"$or": [{"token_balance": {"$gt": 0}}, {"token_daily_used": {"$gt": 0}}]},
        {"_id": 0, "id": 1, "label_name": 1, "token_balance": 1,
         "token_daily_date": 1, "token_daily_used": 1},
    ).to_list(5000)
    outstanding = sum(int(l.get("token_balance") or 0) for l in labels)
    daily_used_today = sum(
        int(l.get("token_daily_used") or 0)
        for l in labels if l.get("token_daily_date") == today
    )
    holders = sorted(
        (l for l in labels if int(l.get("token_balance") or 0) > 0),
        key=lambda l: -int(l.get("token_balance") or 0),
    )
    # Sales vs redemption from payments (authoritative money trail).
    sold = redeemed_idr = redeemed_tokens = in_flight = 0
    async_pay = await db.payments.find(
        {"$or": [{"type": "token_purchase", "status": "paid"},
                 {"payment_method": "token_balance", "status": "paid"}]},
        {"_id": 0, "type": 1, "status": 1, "amount": 1, "token_quantity": 1,
         "token_cost": 1, "token_settled": 1},
    ).to_list(20000)
    for p in async_pay:
        if p.get("type") == "token_purchase":
            sold += int(p.get("token_quantity") or 0)
        else:
            redeemed_tokens += int(p.get("token_cost") or 0)
            redeemed_idr += int(p.get("amount") or 0)
            if not p.get("token_settled"):
                in_flight += 1
    return {
        "price_idr": price,
        "outstanding_tokens": outstanding,
        "liability_idr": outstanding * price,
        "sold_tokens": sold,
        "redeemed_tokens": redeemed_tokens,
        "redeemed_invoice_idr": redeemed_idr,
        "in_flight_token_invoices": in_flight,
        "daily_quota_used_today": daily_used_today,
        "top_wallets": [
            {"label_id": l["id"], "label_name": l.get("label_name"),
             "token_balance": int(l.get("token_balance") or 0)}
            for l in holders[:10]
        ],
        "generated_at": now_iso(),
    }
