"""Xendit balance & payment reconciliation (PRD follow-up).

Compares the cash received in Xendit (successful incoming PAYMENT transactions)
against the payments marked 'paid' in our own `payments` collection for a date
range, and surfaces any variance. Uses the existing XENDIT_SECRET_KEY. Read-only.
"""
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from .deps import db, logger, require_admin
from .admin_permission_service import assert_admin_permission

xendit_recon_r = APIRouter(prefix="/admin/xendit", tags=["xendit-reconciliation"])

_TIMEOUT = float(os.environ.get("XENDIT_TIMEOUT_SECONDS", "15"))


def _base_url() -> str:
    return (os.environ.get("XENDIT_API_URL") or "https://api.xendit.co").rstrip("/")


def _secret() -> str:
    key = (os.environ.get("XENDIT_SECRET_KEY") or "").strip()
    if not key:
        raise HTTPException(status_code=503, detail="XENDIT_SECRET_KEY belum dikonfigurasi")
    return key


async def _xendit_get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(f"{_base_url()}{path}", params=params, auth=(_secret(), ""))
    try:
        body = resp.json()
    except ValueError:
        body = {"message": resp.text[:300]}
    if resp.is_error:
        code = (body or {}).get("error_code") or (body or {}).get("code") or str(resp.status_code)
        raise _Upstream(resp.status_code, code, (body or {}).get("message") or "Xendit error")
    return body


class _Upstream(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _finance_only(user: dict) -> None:
    # Reconciliation is a finance view; gate on payments.view (finance & super have it).
    assert_admin_permission(user, "payments.view")


@xendit_recon_r.get("/balance")
async def xendit_balance(user: dict = Depends(require_admin)):
    _finance_only(user)
    try:
        cash = await _xendit_get("/balance", {"account_type": "CASH", "currency": "IDR"})
        holding = None
        try:
            holding = (await _xendit_get("/balance", {"account_type": "HOLDING", "currency": "IDR"})).get("balance")
        except _Upstream:
            holding = None
        return {"available": True, "cash": int(cash.get("balance") or 0), "holding": (int(holding) if holding is not None else None)}
    except _Upstream as e:
        return {"available": False, "error_code": e.code, "message": e.message}


@xendit_recon_r.get("/reconciliation")
async def reconciliation(
    date_from: str = Query(..., description="YYYY-MM-DD (WIB)"),
    date_to: str = Query(..., description="YYYY-MM-DD (WIB)"),
    user: dict = Depends(require_admin),
):
    _finance_only(user)
    try:
        # Interpret dates as WIB day boundaries → UTC range [start, end).
        start_wib = datetime.fromisoformat(f"{date_from}T00:00:00+07:00")
        end_wib = datetime.fromisoformat(f"{date_to}T23:59:59+07:00")
    except ValueError:
        raise HTTPException(status_code=400, detail="Format tanggal harus YYYY-MM-DD")
    if end_wib < start_wib:
        raise HTTPException(status_code=400, detail="Tanggal akhir sebelum tanggal awal")
    start_utc, end_utc = start_wib.astimezone(timezone.utc), end_wib.astimezone(timezone.utc)

    # --- System side: payments marked paid in range (by paid_at) ---
    sys_cursor = db.payments.aggregate([
        {"$match": {"status": "paid", "paid_at": {"$gte": _iso_z(start_utc), "$lte": _iso_z(end_utc)}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
    ])
    sys_total, sys_count = 0, 0
    async for row in sys_cursor:
        sys_total, sys_count = int(row.get("total") or 0), int(row.get("count") or 0)

    # --- Xendit side: successful incoming PAYMENT transactions in range ---
    xendit: Dict[str, Any] = {"available": True, "payment_in_gross": 0, "payment_in_net": 0, "count": 0, "balance_cash": None}
    try:
        after_id, pages = None, 0
        gross = net = count = 0
        while pages < 100:
            pages += 1
            params = {
                "currency": "IDR", "types": "PAYMENT", "statuses": "SUCCESS", "limit": 50,
                "created[gte]": _iso_z(start_utc), "created[lte]": _iso_z(end_utc),
            }
            if after_id:
                params["after_id"] = after_id
            data = await _xendit_get("/transactions", params)
            rows = data.get("data") or []
            for it in rows:
                if it.get("cashflow") == "MONEY_IN":
                    gross += int(it.get("amount") or 0)
                    net += int(it.get("net_amount") or it.get("amount") or 0)
                    count += 1
            if data.get("has_more") and rows:
                after_id = rows[-1].get("id")
            else:
                break
        xendit.update({"payment_in_gross": gross, "payment_in_net": net, "count": count})
        try:
            bal = await _xendit_get("/balance", {"account_type": "CASH", "currency": "IDR"})
            xendit["balance_cash"] = int(bal.get("balance") or 0)
        except _Upstream:
            xendit["balance_cash"] = None
    except _Upstream as e:
        logger.warning("[XENDIT RECON] upstream error %s: %s", e.code, e.message)
        xendit = {"available": False, "error_code": e.code, "message": e.message}

    variance = None
    matched = None
    if xendit.get("available"):
        variance = int(xendit["payment_in_gross"]) - sys_total
        matched = variance == 0

    return {
        "range": {"from": date_from, "to": date_to},
        "system": {"paid_total_idr": sys_total, "count": sys_count},
        "xendit": xendit,
        "variance_idr": variance,
        "matched": matched,
    }
