"""D1 — Token wallet: second payment rail (optional, rupiah stays default).

Model (final owner decision):
  - Purchased tokens live on `labels.token_balance` — bought via a
    `token_purchase` Xendit invoice, never expire.
  - Paid packages grant a DAILY token quota (per-tier, super-configurable).
    Daily tokens are a counter, not a pool: `token_daily_date` (WIB) +
    `token_daily_used`; unused quota expires at day rollover.
  - Spend order: daily quota first (expires today anyway), then purchased.
  - Return rules: a release rejected/cancelled BEFORE reaching Believe
    returns both kinds; a Believe rejection returns PURCHASED tokens and
    BURNS daily tokens (member uses tomorrow's quota).
  - No replacement/compensation pool — removed by owner decision.

`token_ledger` is the immutable audit trail for every movement; each entry
records kind, source (purchased|daily), signed amount, resulting counters,
and the reference (payment/release/order) that caused it.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException
from pymongo import ReturnDocument

from models import new_id, now_iso
from routes.deps import db

WIB = timezone(timedelta(hours=7))

# Stored shape in system_settings area "token" (published value).
# Keys avoid the word "token" so the audit redactor does not mask the diff.
TOKEN_DEFAULTS: Dict[str, Any] = {
    # Purchase price per token (IDR). Members buy tokens at this flat price.
    "price_idr": 35_000,
    # Daily token quota per subscription tier (paid packages only).
    "daily_quota": {
        "pay_per_release": 0,
        "annual_normal": 6,
        "annual_vip": 10,
        "multi_label": 15,
    },
    # Token cost per service. Key "release_*" covers release submissions;
    # payment product ids / "wami_addon" can be added via config.
    "service_costs": {
        "release_single": 1,
        "release_ep": 5,
        "release_album": 6,
    },
}

MAX_TOKEN_PURCHASE = 500


# ---------------------------------------------------------------------------
# Config — lives in the versioned system_settings area "token" (System115).
# Only the PUBLISHED value is consumed; drafts never leak to members.
# ---------------------------------------------------------------------------

async def get_token_config() -> Dict[str, Any]:
    doc = await db.system_settings.find_one({"area": "token"}, {"_id": 0, "published": 1})
    value = (doc or {}).get("published") or {}
    return {
        "token_price_idr": int(value.get("price_idr") or TOKEN_DEFAULTS["price_idr"]),
        "daily_quota": {**TOKEN_DEFAULTS["daily_quota"], **(value.get("daily_quota") or {})},
        "service_tokens": {**TOKEN_DEFAULTS["service_costs"], **(value.get("service_costs") or {})},
    }


def service_token_cost(cfg: Dict[str, Any], service_key: str) -> Optional[int]:
    tokens = (cfg.get("service_tokens") or {}).get(service_key)
    return int(tokens) if isinstance(tokens, int) and tokens > 0 else None


def token_offer(cfg: Dict[str, Any], service_key: str, rupiah_price: int) -> Dict[str, Any]:
    """Token price for a service; offered ONLY when strictly cheaper than
    rupiah (auto-hide rule — token is the optional second rail)."""
    tokens = service_token_cost(cfg, service_key)
    cost = tokens * cfg["token_price_idr"] if tokens else None
    offered = bool(tokens and cost < rupiah_price)
    return {
        "service_key": service_key, "tokens": tokens or 0,
        "token_cost_idr": cost, "rupiah_price": rupiah_price,
        "offered": offered,
    }


# ---------------------------------------------------------------------------
# Wallet state
# ---------------------------------------------------------------------------

def jakarta_today() -> str:
    return datetime.now(WIB).date().isoformat()


def _label_tier(label: Dict[str, Any]) -> str:
    from routes.entitlements import resolve_label_entitlements
    return resolve_label_entitlements(label).get("package") or "pay_per_release"


def wallet_state(label: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    today = jakarta_today()
    quota = int((cfg["daily_quota"] or {}).get(_label_tier(label), 0))
    used = int(label.get("token_daily_used") or 0) if label.get("token_daily_date") == today else 0
    return {
        "token_balance": int(label.get("token_balance") or 0),
        "daily": {
            "date": today, "quota": quota, "used": used,
            "remaining": max(0, quota - used), "tier": _label_tier(label),
        },
        "token_price_idr": cfg["token_price_idr"],
    }


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------

async def _ledger(label_id: str, kind: str, source: str, amount: int,
                  balance_after: Optional[int], daily_used_after: Optional[int],
                  ref_type: Optional[str], ref_id: Optional[str],
                  note: Optional[str], actor_id: Optional[str] = None) -> None:
    await db.token_ledger.insert_one({
        "id": "TKN-" + new_id()[:10].upper(), "label_id": label_id,
        "kind": kind, "source": source, "amount": int(amount),
        "balance_after": balance_after, "daily_used_after": daily_used_after,
        "ref_type": ref_type, "ref_id": ref_id, "note": note or "",
        "actor": actor_id, "created_at": now_iso(),
    })


async def credit_purchased(label_id: str, count: int, ref_type: str, ref_id: str,
                           note: str, actor_id: Optional[str] = None,
                           kind: str = "purchase") -> Dict[str, Any]:
    """Credit purchased-pool tokens (invoice fulfillment / manual grant)."""
    label = await db.labels.find_one_and_update(
        {"id": label_id},
        {"$inc": {"token_balance": int(count)}, "$set": {"updated_at": now_iso()}},
        return_document=ReturnDocument.AFTER, projection={"_id": 0, "token_balance": 1},
    )
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    balance_after = int(label.get("token_balance") or 0)
    await _ledger(label_id, kind, "purchased", +int(count), balance_after, None,
                  ref_type, ref_id, note, actor_id)
    return {"token_balance": balance_after}


# ---------------------------------------------------------------------------
# Spend / refund / burn
# ---------------------------------------------------------------------------

async def spend_tokens(label_id: str, count: int, ref_type: str, ref_id: str,
                       note: str, cfg: Optional[Dict[str, Any]] = None) -> Dict[str, int]:
    """Consume tokens: daily quota first, then purchased. Conditional updates
    prevent overdraw under concurrency. Returns {"daily": d, "purchased": p}.
    """
    cfg = cfg or await get_token_config()
    label = await db.labels.find_one({"id": label_id}, {"_id": 0})
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    today = jakarta_today()
    quota = int((cfg["daily_quota"] or {}).get(_label_tier(label), 0))
    used = int(label.get("token_daily_used") or 0) if label.get("token_daily_date") == today else 0
    daily_part = min(max(0, quota - used), int(count))
    purchased_part = int(count) - daily_part
    balance = int(label.get("token_balance") or 0)
    if max(0, quota - used) + balance < count:
        raise HTTPException(status_code=409, detail="Saldo token tidak cukup")

    # 1) Daily counter (reset stale day first, then conditional increment).
    if daily_part:
        if label.get("token_daily_date") != today:
            await db.labels.update_one(
                {"id": label_id},
                {"$set": {"token_daily_date": today, "token_daily_used": 0}},
            )
        bumped = await db.labels.find_one_and_update(
            {"id": label_id, "token_daily_used": {"$lte": quota - daily_part},
             "token_daily_date": today},
            {"$inc": {"token_daily_used": daily_part}},
            return_document=ReturnDocument.AFTER, projection={"_id": 0, "token_daily_used": 1},
        )
        if not bumped:
            raise HTTPException(status_code=409, detail="Kuota token harian berubah — coba lagi")
        used_after = int(bumped.get("token_daily_used") or 0)
        await _ledger(label_id, "spend", "daily", -daily_part, None, used_after,
                      ref_type, ref_id, note)

    # 2) Purchased balance — conditional decrement; compensate daily on race.
    if purchased_part:
        dec = await db.labels.find_one_and_update(
            {"id": label_id, "token_balance": {"$gte": purchased_part}},
            {"$inc": {"token_balance": -purchased_part}, "$set": {"updated_at": now_iso()}},
            return_document=ReturnDocument.AFTER, projection={"_id": 0, "token_balance": 1},
        )
        if not dec:
            if daily_part:
                await db.labels.update_one(
                    {"id": label_id, "token_daily_date": today},
                    {"$inc": {"token_daily_used": -daily_part}},
                )
            raise HTTPException(status_code=409, detail="Saldo token berubah — coba lagi")
        await _ledger(label_id, "spend", "purchased", -purchased_part,
                      int(dec.get("token_balance") or 0), None, ref_type, ref_id, note)

    return {"daily": daily_part, "purchased": purchased_part}


async def refund_tokens(label_id: str, parts: Dict[str, int], ref_type: str,
                        ref_id: str, note: str) -> Dict[str, int]:
    """Return tokens per the spend breakdown {"daily","purchased"}.
    Purchased always returns to balance. Daily returns only while the same
    WIB day is still running (yesterday's quota is gone regardless).
    """
    out = {"daily": 0, "purchased": 0}
    if parts.get("purchased"):
        label = await db.labels.find_one_and_update(
            {"id": label_id},
            {"$inc": {"token_balance": int(parts["purchased"])}, "$set": {"updated_at": now_iso()}},
            return_document=ReturnDocument.AFTER, projection={"_id": 0, "token_balance": 1},
        )
        out["purchased"] = int(parts["purchased"])
        await _ledger(label_id, "refund", "purchased", +int(parts["purchased"]),
                      int((label or {}).get("token_balance") or 0), None,
                      ref_type, ref_id, note)
    if parts.get("daily"):
        today = jakarta_today()
        dec = await db.labels.find_one_and_update(
            {"id": label_id, "token_daily_date": today,
             "token_daily_used": {"$gte": int(parts["daily"])}},
            {"$inc": {"token_daily_used": -int(parts["daily"])}},
            return_document=ReturnDocument.AFTER, projection={"_id": 0, "token_daily_used": 1},
        )
        if dec is not None:
            out["daily"] = int(parts["daily"])
            await _ledger(label_id, "refund", "daily", +int(parts["daily"]), None,
                          int(dec.get("token_daily_used") or 0), ref_type, ref_id, note)
        else:
            # Day already rolled over — returning to an expired day is a no-op;
            # record it so the audit trail stays complete.
            await _ledger(label_id, "refund-skipped", "daily", 0, None, None,
                          ref_type, ref_id, "Kuota harian sudah berganti hari")
    return out


async def burn_tokens(label_id: str, daily_count: int, ref_type: str, ref_id: str,
                      note: str) -> None:
    """Burned daily tokens (Believe rejection). No balance change — the tokens
    were already consumed; this is purely the audit entry with the reason."""
    if daily_count:
        await _ledger(label_id, "burn", "daily", 0, None, None,
                      ref_type, ref_id, note)


async def fulfill_purchase(label_id: str, count: int, payment_id: str) -> Optional[int]:
    """Credit a paid token_purchase invoice exactly once. Returns the new
    purchased balance, or None when this payment was already fulfilled."""
    marked = await db.labels.find_one_and_update(
        {"id": label_id, "fulfilled_payment_ids": {"$ne": payment_id}},
        {"$inc": {"token_balance": int(count)},
         "$addToSet": {"fulfilled_payment_ids": payment_id},
         "$set": {"updated_at": now_iso()}},
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0, "token_balance": 1},
    )
    if marked is None:
        return None
    await _ledger(label_id, "purchase", "purchased", +int(count),
                  int(marked.get("token_balance") or 0), None,
                  "payment", payment_id, "Pembelian token via Xendit")
    return int(marked.get("token_balance") or 0)


# ---------------------------------------------------------------------------
# Paying an invoice with tokens (D1-b)
# ---------------------------------------------------------------------------

def service_key_for_release_type(release_type: Optional[str]) -> str:
    rt = (release_type or "single").lower()
    if rt == "album":
        return "release_album"
    if rt == "ep":
        return "release_ep"
    return "release_single"


async def service_key_for_payment(payment: Dict[str, Any]) -> Optional[str]:
    """Map a pending invoice to its token service key, or None when the
    payment type is not payable with tokens."""
    ptype = payment.get("type")
    if ptype == "pay_per_release":
        release = await db.releases.find_one(
            {"id": payment.get("release_id")}, {"_id": 0, "release_type": 1})
        return service_key_for_release_type((release or {}).get("release_type"))
    if ptype == "custom_service":
        return payment.get("product_id")
    if ptype in ("wami_addon", "release_shortfall"):
        return ptype
    return None  # token_purchase / annual_subscription / others


async def token_quote_for_payment(payment: Dict[str, Any],
                                  cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = cfg or await get_token_config()
    key = await service_key_for_payment(payment)
    if not key:
        return {"offered": False, "tokens": 0, "service_key": None}
    offer = token_offer(cfg, key, int(payment.get("amount") or 0))
    return offer


async def settle_release_tokens(release_id: str, outcome: str, note: str) -> int:
    """Apply the owner-decided token matrix to every token-paid invoice of a
    release. Returns the number of payments settled.

    outcome:
      "return"  — pre-Believe reject / label cancel: BOTH daily + purchased back
      "believe" — Believe-side failure/cancel: purchased back, daily burned
      "settled" — delivered/live/takedown: tokens stay consumed (audit only)
    """
    payments = await db.payments.find(
        {"release_id": release_id, "payment_method": "token_balance",
         "status": "paid", "token_settled": {"$exists": False}},
        {"_id": 0},
    ).to_list(50)
    for pay in payments:
        parts = pay.get("token_parts") or {}
        if outcome == "return":
            await refund_tokens(pay["label_id"], parts, "release", release_id, note)
        elif outcome == "believe":
            if parts.get("purchased"):
                await refund_tokens(pay["label_id"], {"purchased": parts["purchased"]},
                                    "release", release_id, note)
            if parts.get("daily"):
                await burn_tokens(pay["label_id"], parts["daily"],
                                  "release", release_id, note)
        await db.payments.update_one(
            {"id": pay["id"]},
            {"$set": {"token_settled": outcome, "token_settled_at": now_iso(),
                      "updated_at": now_iso()}},
        )
    return len(payments)
