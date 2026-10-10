"""D1 — Token wallet endpoints: label wallet + super-admin manual credit."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .deps import (
    db, get_label_by_user, log_activity, require_label, require_super_admin,
)
from .entitlements import resolve_label_entitlements
from token_service import (
    credit_purchased, get_token_config, token_offer, wallet_state,
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
