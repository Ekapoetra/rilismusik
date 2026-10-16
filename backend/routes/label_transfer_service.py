"""Rename a label or move its catalog and unsettled royalties to another label.

Money rules (see memory/LABEL_TRANSFER_PRD.md):
- Only unsettled royalty lines move; paid history stays on the source label.
- A moved line whose period the target already settled (period <= target
  cutoff) is invisible to the target's FIFO balance, so its value is credited
  through the adjustment journal instead of being lost.
- Writes are ordered so an interrupted transfer can hide money until it is
  resumed, but never count it twice.
"""
import re
import secrets
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Literal, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from models import new_id, now_iso
from royalty_utils import label_name_key
from .admin_permission_service import has_permission
from .deps import db, db_bg, log_activity, logger, notify, notify_many
from .financial_lock import label_financial_lock
from .royalty_adjustment_balance import ADJUSTMENT_TYPE, adjustment_balances, refresh_balance_cache

MODES = ("rename", "merge", "releases", "sale")
SAME_ACCOUNT_MODES = ("merge", "releases")
LABEL_MODES = ("rename", "merge", "releases")
OPEN_STATUSES = ("pending", "approved", "applying", "failed")
UNSETTLED_LINE_STATUSES = ("draft", "pending", "available")
BUSY_IMPORT_STATUSES = ("processing", "publishing", "receiving", "deleting")
TRANSFER_SOURCE = "LABEL_TRANSFER"
_PERIOD = r"^\d{4}-(0[1-9]|1[0-2])$"
_CHUNK = 5000


class LabelTransferIn(BaseModel):
    mode: Literal["rename", "merge", "releases", "sale"]
    source_label_id: str = Field(min_length=1, max_length=100)
    target_label_id: Optional[str] = Field(default=None, max_length=100)
    new_name: Optional[str] = Field(default=None, max_length=120)
    release_ids: List[str] = Field(default_factory=list, max_length=5000)
    effective_period: Optional[str] = Field(default=None, pattern=_PERIOD)
    carry_balance: bool = True
    reason: str = Field(min_length=3, max_length=1000)
    reference: Optional[str] = Field(default=None, max_length=240)
    believe_confirmed: bool = False
    apply_now: bool = False


class LabelTransferDecisionIn(BaseModel):
    action: Literal["approve", "reject"]
    note: Optional[str] = Field(default=None, max_length=1000)
    believe_confirmed: bool = False


def _reference_id() -> str:
    return "LT-" + secrets.token_hex(4).upper()


def _actor_name(user: dict) -> str:
    return user.get("name") or user.get("role_name") or user.get("email") or user["id"]


def can_apply_directly(user: dict, mode: str) -> bool:
    # A sale always needs a second Super Admin; nobody applies it alone.
    return mode != "sale" and has_permission(user, "labels.transfer")


def can_decide(user: dict, transfer: dict) -> bool:
    if transfer["mode"] == "sale":
        return user.get("role") == "super_admin" and transfer["requested_by"] != user["id"]
    if not has_permission(user, "labels.transfer.approve"):
        return False
    return transfer["requested_by"] != user["id"] or has_permission(user, "labels.transfer")


async def _get_label(label_id: Optional[str], field: str = "Label") -> dict:
    label = await db.labels.find_one({"id": label_id}, {"_id": 0}) if label_id else None
    if not label:
        raise HTTPException(status_code=404, detail=f"{field} tidak ditemukan")
    return label


async def _name_taken(name: str, *, exclude_label_id: str) -> Optional[dict]:
    """Another label already answers to this name (primary name or alias)."""
    key = label_name_key(name)
    async for label in db.labels.find(
        {"id": {"$ne": exclude_label_id}}, {"_id": 0, "id": 1, "user_id": 1, "label_name": 1, "label_name_aliases": 1},
    ):
        names = [label.get("label_name")] + [alias.get("name") for alias in label.get("label_name_aliases") or []]
        if any(label_name_key(item) == key for item in names if item):
            return label
    return None


async def _open_transfer_for(label_ids: List[str]) -> Optional[dict]:
    return await db.label_transfers.find_one({
        "status": {"$in": list(OPEN_STATUSES)},
        "$or": [{"source_label_id": {"$in": label_ids}}, {"target_label_id": {"$in": label_ids}}],
    }, {"_id": 0, "id": 1, "reference_id": 1})


async def build_transfer_request(body: LabelTransferIn, *, actor: dict, actor_kind: Literal["label", "admin"]) -> dict:
    """Validate a request and return the transfer document (not yet stored)."""
    source = await _get_label(body.source_label_id, "Label asal")
    if source.get("merged_into_label_id"):
        raise HTTPException(status_code=409, detail="Label asal sudah digabung ke label lain")
    if actor_kind == "label":
        if body.mode not in LABEL_MODES:
            raise HTTPException(status_code=403, detail="Penjualan label hanya dapat diinput oleh admin")
        if source.get("user_id") != actor["id"]:
            raise HTTPException(status_code=403, detail="Label ini bukan milik akun Anda")
    doc: Dict[str, Any] = {
        "mode": body.mode, "source_label_id": source["id"], "source_label_name": source.get("label_name"),
        "source_user_id": source.get("user_id"), "target_label_id": None, "target_label_name": None,
        "target_user_id": None, "new_name": None, "release_ids": [],
        "effective_period": body.effective_period, "carry_balance": True,
        "reason": body.reason.strip(), "reference": (body.reference or "").strip() or None,
    }
    if body.mode == "rename":
        new_name = " ".join((body.new_name or "").split())
        if len(new_name) < 2:
            raise HTTPException(status_code=400, detail="Nama label baru minimal 2 karakter")
        if label_name_key(new_name) == label_name_key(source.get("label_name")):
            raise HTTPException(status_code=400, detail="Nama baru sama dengan nama sekarang")
        clash = await _name_taken(new_name, exclude_label_id=source["id"])
        if clash and not clash.get("user_id"):
            raise HTTPException(status_code=409, detail=f"Nama \"{new_name}\" sudah dipakai label lama yang belum diklaim. Klaim label itu ke akun ini lewat menu Migrasi, lalu gunakan mode Gabung.")
        if clash:
            raise HTTPException(status_code=409, detail=f"Nama \"{new_name}\" sudah dipakai label lain ({clash.get('label_name')})")
        doc["new_name"] = new_name
    else:
        if not body.target_label_id or body.target_label_id == source["id"]:
            raise HTTPException(status_code=400, detail="Pilih label tujuan yang berbeda dari label asal")
        target = await _get_label(body.target_label_id, "Label tujuan")
        if target.get("merged_into_label_id"):
            raise HTTPException(status_code=409, detail="Label tujuan sudah digabung ke label lain")
        same_account = bool(source.get("user_id")) and source.get("user_id") == target.get("user_id")
        if body.mode in SAME_ACCOUNT_MODES and not same_account:
            raise HTTPException(status_code=400, detail="Label tujuan harus berada di akun yang sama. Untuk label yang dijual ke akun lain, gunakan mode Penjualan.")
        if body.mode == "sale":
            if same_account:
                raise HTTPException(status_code=400, detail="Kedua label ada di akun yang sama — gunakan mode Gabung atau Pilih Rilisan")
            if not target.get("user_id"):
                raise HTTPException(status_code=400, detail="Label pembeli belum punya akun login")
            if not body.effective_period:
                raise HTTPException(status_code=400, detail="Isi bulan laporan mulai berlaku untuk penjualan")
            if len(doc["reference"] or "") < 3:
                raise HTTPException(status_code=400, detail="Isi nomor/rujukan dokumen jual-beli")
            doc["carry_balance"] = body.carry_balance
        if body.mode == "releases" and not body.release_ids:
            raise HTTPException(status_code=400, detail="Pilih minimal satu rilisan")
        if body.mode in ("releases", "sale") and body.release_ids:
            release_ids = list(dict.fromkeys(body.release_ids))
            owned = await db.releases.count_documents({"id": {"$in": release_ids}, "label_id": source["id"]})
            if owned != len(release_ids):
                raise HTTPException(status_code=400, detail="Ada rilisan yang bukan milik label asal")
            doc["release_ids"] = release_ids
        doc.update({"target_label_id": target["id"], "target_label_name": target.get("label_name"),
                    "target_user_id": target.get("user_id")})
    involved = [label_id for label_id in (doc["source_label_id"], doc["target_label_id"]) if label_id]
    existing = await _open_transfer_for(involved)
    if existing:
        raise HTTPException(status_code=409, detail=f"Masih ada perpindahan {existing.get('reference_id')} yang belum selesai untuk label ini")
    now = now_iso()
    doc.update({
        "id": new_id(), "reference_id": _reference_id(), "status": "pending",
        "requested_by": actor["id"], "requested_by_name": _actor_name(actor), "requested_by_kind": actor_kind,
        "requested_at": now, "believe_confirmed": bool(body.believe_confirmed),
        "decided_by": None, "decided_by_name": None, "decided_at": None, "decision_note": None,
        "plan": None, "result": None, "error": None, "updated_at": now,
    })
    return doc


def summarize(doc: dict) -> str:
    if doc["mode"] == "rename":
        return f"Ganti nama {doc['source_label_name']} → {doc['new_name']}"
    scope = f"{len(doc['release_ids'])} rilisan" if doc.get("release_ids") else "semua rilisan"
    verb = {"merge": "Gabung", "releases": "Pindah", "sale": "Jual"}[doc["mode"]]
    return f"{verb} {scope} {doc['source_label_name']} → {doc['target_label_name']}"


async def _approver_ids(mode: str, exclude: str) -> List[str]:
    if mode == "sale":
        query: Dict[str, Any] = {"role": "super_admin"}
    else:
        role_ids = await db.admin_roles.distinct("id", {"permissions": "labels.transfer.approve", "active": {"$ne": False}})
        query = {"$or": [{"role": "super_admin"}, {"admin_role_id": {"$in": role_ids}}]}
    query["status"] = {"$nin": ["suspended", "disabled"]}
    return [user["id"] async for user in db.users.find(query, {"_id": 0, "id": 1}) if user["id"] != exclude]


async def notify_submitted(doc: dict) -> None:
    approvers = await _approver_ids(doc["mode"], doc["requested_by"])
    await notify_many(approvers, "label_transfer_request", "Permintaan Pindah Label",
                      f"{summarize(doc)} menunggu persetujuan ({doc['reference_id']}).",
                      link="/admin/label-transfers", meta={"transfer_id": doc["id"]})
    if doc["mode"] == "sale":
        # Both owners hear about a sale before anything moves, so a mistaken or
        # fraudulent request is caught while it is still pending.
        owners = [user_id for user_id in {doc.get("source_user_id"), doc.get("target_user_id")} if user_id]
        await notify_many(owners, "label_transfer_sale_pending", "Pengajuan Penjualan Label",
                          f"{summarize(doc)} sedang diproses admin ({doc['reference_id']}). Hubungi tim support jika ini tidak sesuai.",
                          link="/label/dashboard", meta={"transfer_id": doc["id"]})


async def _ensure_no_busy_work(label_ids: List[str]) -> None:
    active = await db.withdraw_requests.find_one({
        "label_id": {"$in": label_ids}, "status": {"$in": ["requested", "approved"]}, "legacy_import": {"$ne": True},
    }, {"_id": 0, "id": 1})
    if active:
        raise HTTPException(status_code=409, detail="Selesaikan atau tolak withdraw yang sedang diproses di label asal/tujuan terlebih dulu")
    recalculating = await db.labels.find_one({
        "id": {"$in": label_ids}, "royalty_recalculation_status": {"$in": ["queued", "processing"]},
    }, {"_id": 0, "id": 1})
    if recalculating:
        raise HTTPException(status_code=409, detail="Hitung ulang royalti label sedang berjalan. Coba lagi setelah selesai.")
    busy_import = await db.royalty_imports.find_one({"status": {"$in": list(BUSY_IMPORT_STATUSES)}}, {"_id": 0, "id": 1})
    if busy_import:
        raise HTTPException(status_code=409, detail="Ada import royalti yang sedang diproses. Coba lagi setelah selesai.")


async def _catalog(doc: dict) -> Dict[str, List[str]]:
    query: Dict[str, Any] = {"label_id": doc["source_label_id"]}
    if doc.get("release_ids"):
        query["id"] = {"$in": doc["release_ids"]}
    release_ids = [item["id"] async for item in db.releases.find(query, {"_id": 0, "id": 1})]
    tracks = [item async for item in db_bg.tracks.find(
        {"release_id": {"$in": release_ids}, "label_id": doc["source_label_id"]},
        {"_id": 0, "id": 1, "isrc": 1, "artist_id": 1},
    )]
    upcs = [item["upc"].strip().upper() async for item in db.releases.find(
        {"id": {"$in": release_ids}, "upc": {"$nin": [None, ""]}}, {"_id": 0, "upc": 1},
    )]
    return {
        "release_ids": release_ids, "track_ids": [track["id"] for track in tracks],
        "isrcs": sorted({(track.get("isrc") or "").strip().upper() for track in tracks if track.get("isrc")}),
        "upcs": sorted(set(upcs)),
        "artist_ids": sorted({track["artist_id"] for track in tracks if track.get("artist_id")}),
    }


def _line_filter(doc: dict, source: dict, plan: dict) -> Dict[str, Any]:
    query: Dict[str, Any] = {
        "label_id": doc["source_label_id"], "status": {"$in": list(UNSETTLED_LINE_STATUSES)},
        "legacy_settled": {"$ne": True},
    }
    period: Dict[str, Any] = {"$type": "string"}
    if source.get("last_withdrawn_period"):
        period["$gt"] = source["last_withdrawn_period"]
    if doc["mode"] == "sale" and not doc.get("carry_balance"):
        period["$gte"] = doc["effective_period"]
    query["period"] = period
    if doc["mode"] != "merge":
        query["$or"] = [{"release_id": {"$in": plan["release_ids"]}}, {"track_id": {"$in": plan["track_ids"]}}]
    return query


async def build_plan(doc: dict) -> dict:
    """What a transfer will move, computed from live data. Raises when it is unsafe."""
    if doc["mode"] == "rename":
        return {"mode": "rename"}
    source = await _get_label(doc["source_label_id"], "Label asal")
    target = await _get_label(doc["target_label_id"], "Label tujuan")
    await _ensure_no_busy_work([source["id"], target["id"]])
    plan: Dict[str, Any] = await _catalog(doc)
    target_cutoff = target.get("last_withdrawn_period")
    totals = {"lines": 0, "pending_idr": 0, "available_idr": 0, "credit_idr": 0, "credit_lines": 0, "inflight_conflicts": 0}
    async for row in db_bg.royalty_lines.aggregate([
        {"$match": _line_filter(doc, source, plan)},
        {"$group": {"_id": {"status": "$status", "period": "$period"},
                    "amount": {"$sum": {"$ifNull": ["$label_idr", 0]}}, "count": {"$sum": 1}}},
    ], allowDiskUse=True):
        status, period = row["_id"]["status"], row["_id"]["period"]
        amount, count = int(row["amount"] or 0), int(row["count"] or 0)
        totals["lines"] += count
        totals["available_idr" if status == "available" else "pending_idr"] += amount
        if target_cutoff and period <= target_cutoff:
            if status == "available":
                totals["credit_idr"] += amount
                totals["credit_lines"] += count
            else:
                totals["inflight_conflicts"] += count
    if totals["inflight_conflicts"]:
        raise HTTPException(status_code=409, detail=f"Ada {totals['inflight_conflicts']} baris royalti yang belum dana diterima pada periode yang sudah ditarik label tujuan. Selesaikan import tersebut dulu.")
    adjustment_idr = 0
    if doc["mode"] == "merge":
        adjustment_idr = (await adjustment_balances([source["id"]]))[source["id"]]
        if adjustment_idr < 0:
            raise HTTPException(status_code=409, detail="Jurnal penyesuaian label asal tidak konsisten. Periksa riwayat Inject Saldo.")
    plan.update({
        "line_count": totals["lines"], "pending_idr": totals["pending_idr"], "available_idr": totals["available_idr"],
        "credit_idr": totals["credit_idr"], "credit_lines": totals["credit_lines"], "adjustment_idr": adjustment_idr,
        "source_cutoff": source.get("last_withdrawn_period"), "target_cutoff": target_cutoff,
        "built_at": now_iso(),
    })
    return plan


def preview_view(plan: dict) -> dict:
    """Plan without the long id lists, for UI previews."""
    view = {key: value for key, value in plan.items() if key not in {"release_ids", "track_ids", "isrcs", "upcs", "artist_ids"}}
    if plan.get("mode") != "rename":
        view.update({"release_count": len(plan.get("release_ids") or []), "track_count": len(plan.get("track_ids") or [])})
    return view


async def _move_chunked(collection, query: Dict[str, Any], update: Dict[str, Any]) -> int:
    moved = 0
    while True:
        batch = await collection.find(query, {"_id": 1}).limit(_CHUNK).to_list(_CHUNK)
        if not batch:
            return moved
        result = await collection.update_many({"_id": {"$in": [item["_id"] for item in batch]}}, update)
        moved += result.modified_count
        if result.modified_count == 0:
            return moved


async def _journal(entry_id: str, *, label_id: str, amount: int, doc: dict, actor: dict, description: str,
                   cutoff: Optional[str], kind: str) -> None:
    if not amount:
        return
    record = {
        "_id": entry_id, "id": entry_id, "label_id": label_id, "type": ADJUSTMENT_TYPE,
        "source": TRANSFER_SOURCE, "adjustment_type": TRANSFER_SOURCE, "amount_idr": amount, "currency": "IDR",
        "reason": description, "reference": doc["reference_id"], "legacy_period_to": cutoff or "",
        "legacy_balance_before_idr": 0, "balance_before_idr": 0, "balance_after_idr": 0,
        "status": "active", "created_by": actor["id"], "created_by_name": _actor_name(actor),
        "created_at": now_iso(), "reference_type": "label_transfer", "reference_id": doc["id"], "transfer_kind": kind,
        "description": description,
    }
    try:
        await db.balance_transactions.insert_one(record)
    except DuplicateKeyError:
        pass  # already written by an earlier attempt


async def _move_catalog(doc: dict, plan: dict, source: dict, actor: dict) -> Dict[str, int]:
    source_id, target_id = doc["source_label_id"], doc["target_label_id"]
    stamp = {"transferred_from_label_id": source_id, "label_transfer_id": doc["id"], "updated_at": now_iso()}
    # Lines first: an interruption here can only under-count the target.
    lines = await _move_chunked(db_bg.royalty_lines, _line_filter(doc, source, plan), {"$set": {"label_id": target_id}})
    releases = (await db.releases.update_many(
        {"id": {"$in": plan["release_ids"]}, "label_id": source_id}, {"$set": {"label_id": target_id, **stamp}},
    )).modified_count
    tracks = await _move_chunked(db_bg.tracks, {"release_id": {"$in": plan["release_ids"]}, "label_id": source_id},
                                 {"$set": {"label_id": target_id, **stamp}})
    artists = 0
    if doc["mode"] == "merge":
        artists = (await db.artists.update_many({"label_id": source_id}, {"$set": {"label_id": target_id, **stamp}})).modified_count
    for artist_id in plan["artist_ids"] if doc["mode"] != "merge" else []:
        # An artist follows only when none of its tracks stay behind; artist
        # logins never change hands in a sale.
        followed = 0
        if not await db_bg.tracks.find_one({"artist_id": artist_id, "label_id": source_id}, {"_id": 1}):
            query: Dict[str, Any] = {"id": artist_id, "label_id": source_id}
            if doc["mode"] == "sale":
                query["user_id"] = {"$in": [None, ""]}
            followed = (await db.artists.update_one(query, {"$set": {"label_id": target_id, **stamp}})).modified_count
        artists += followed
        if doc["mode"] == "sale" and not followed and not await db.artists.find_one({"id": artist_id, "label_id": target_id}, {"_id": 1}):
            # The seller's artist must not see the buyer's earnings; the next
            # import attaches the buyer's own artist record by name.
            await db_bg.tracks.update_many({"artist_id": artist_id, "label_id": target_id, "label_transfer_id": doc["id"]},
                                           {"$set": {"artist_id": None}})
    target_cutoff = plan.get("target_cutoff")
    await _journal(f"LT-{doc['id']}-settled", label_id=target_id, amount=plan["credit_idr"], doc=doc, actor=actor,
                   cutoff=target_cutoff, kind="settled_credit",
                   description=f"Royalti {doc['source_label_name']} periode ≤ {target_cutoff} yang dipindah ({doc['reference_id']})")
    if plan.get("adjustment_idr"):
        await _journal(f"LT-{doc['id']}-adj-out", label_id=source_id, amount=-plan["adjustment_idr"], doc=doc, actor=actor,
                       cutoff=None, kind="adjustment_move", description=f"Saldo penyesuaian dipindah ke {doc['target_label_name']} ({doc['reference_id']})")
        await _journal(f"LT-{doc['id']}-adj-in", label_id=target_id, amount=plan["adjustment_idr"], doc=doc, actor=actor,
                       cutoff=None, kind="adjustment_move", description=f"Saldo penyesuaian dari {doc['source_label_name']} ({doc['reference_id']})")
    return {"lines": lines, "releases": releases, "tracks": tracks, "artists": artists}


def _alias(name: str, doc: dict, **extra: Any) -> dict:
    return {"name": name, "until": now_iso(), "transfer_id": doc["id"], "reference_id": doc["reference_id"], **extra}


async def _apply_labels(doc: dict, actor: dict) -> None:
    source_id = doc["source_label_id"]
    if doc["mode"] == "rename":
        await db.labels.update_one({"id": source_id}, {
            "$set": {"label_name": doc["new_name"], "updated_at": now_iso()},
            "$push": {"label_name_aliases": _alias(doc["source_label_name"], doc)},
        })
        return
    if doc["mode"] == "merge":
        await db.labels.update_one({"id": source_id}, {"$set": {
            "merged_into_label_id": doc["target_label_id"], "merged_into_label_name": doc["target_label_name"],
            "merged_at": now_iso(), "merged_by_transfer_id": doc["id"], "updated_at": now_iso(),
        }})
        await db.labels.update_one({"id": doc["target_label_id"]}, {
            "$push": {"label_name_aliases": _alias(doc["source_label_name"], doc, from_label_id=source_id)},
            "$set": {"updated_at": now_iso()},
        })
        await db.users.update_many({"active_label_id": source_id}, {"$set": {"active_label_id": doc["target_label_id"]}})


async def _notify_owners(doc: dict) -> None:
    owners = [user_id for user_id in {doc.get("source_user_id"), doc.get("target_user_id")} if user_id]
    for user_id in owners:
        await notify(user_id, "label_transfer_done", "Perpindahan Label Selesai",
                     f"{summarize(doc)} sudah diterapkan ({doc['reference_id']}).", link="/label/dashboard",
                     meta={"transfer_id": doc["id"]})


async def apply_transfer(transfer_id: str, actor: dict) -> dict:
    """Apply an approved transfer. Safe to call again after an interruption."""
    doc = await db.label_transfers.find_one(
        {"id": transfer_id, "status": {"$in": ["approved", "failed", "applying"]}}, {"_id": 0},
    )
    if not doc:
        raise HTTPException(status_code=409, detail="Perpindahan tidak dalam status siap diterapkan")
    label_ids = sorted({label_id for label_id in (doc["source_label_id"], doc.get("target_label_id")) if label_id})
    async with AsyncExitStack() as stack:
        # Holding both financial leases first means a concurrent second attempt
        # is refused here and never touches this attempt's status.
        for label_id in label_ids:
            await stack.enter_async_context(label_financial_lock(label_id))
        await db.label_transfers.update_one({"id": doc["id"]}, {"$set": {
            "status": "applying", "applied_by": actor["id"], "error": None, "updated_at": now_iso(),
        }})
        try:
            moved = await _apply_locked(doc, label_ids, actor)
        except HTTPException as exc:
            await _mark_failed(doc, exc.detail, label_ids)
            raise
        except Exception as exc:
            logger.exception("[LABEL-TRANSFER] apply failed id=%s", doc["id"])
            await _mark_failed(doc, str(exc), label_ids)
            raise HTTPException(status_code=500, detail="Perpindahan terhenti di tengah jalan. Data aman; klik Lanjutkan untuk meneruskan.") from exc
    result = {**moved, "completed_at": now_iso()}
    await db.label_transfers.update_one({"id": doc["id"]}, {"$set": {"status": "completed", "result": result, "updated_at": now_iso()}})
    for label_id in label_ids:
        await refresh_balance_cache(label_id)
    await _refresh_analytics()
    await log_activity(actor["id"], f"label_transfer_{doc['mode']}", "label", doc["source_label_id"],
                       before={"label_name": doc["source_label_name"]},
                       after={"transfer_id": doc["id"], "target_label_id": doc.get("target_label_id"),
                              "new_name": doc.get("new_name"), **result})
    await _notify_owners(doc)
    return await get_transfer(doc["id"])


async def _apply_locked(doc: dict, label_ids: List[str], actor: dict) -> Dict[str, int]:
    moved: Dict[str, int] = {}
    if doc["mode"] != "rename":
        stored = await db.label_transfers.find_one({"id": doc["id"]}, {"_id": 0, "plan": 1})
        plan = (stored or {}).get("plan")
        if plan:
            await _ensure_no_busy_work(label_ids)
        else:
            # Close withdrawals on both labels before checking, so none can slip
            # in between the check and the move. The flag stays until the move
            # completes; nothing is stored or moved if planning fails.
            await db.labels.update_many({"id": {"$in": label_ids}}, {"$set": {"transfer_in_progress_id": doc["id"]}})
            plan = await build_plan(doc)
            await db.label_transfers.update_one({"id": doc["id"]}, {"$set": {"plan": plan}})
        source = await _get_label(doc["source_label_id"], "Label asal")
        if plan.get("source_cutoff") != source.get("last_withdrawn_period"):
            raise HTTPException(status_code=409, detail="Periode withdraw label asal berubah sejak perpindahan dimulai. Hubungi tim teknis.")
        moved = await _move_catalog(doc, plan, source, actor)
    await _apply_labels(doc, actor)
    await db.labels.update_many({"id": {"$in": label_ids}}, {"$unset": {"transfer_in_progress_id": ""}})
    return moved


async def _mark_failed(doc: dict, error: Any, label_ids: List[str]) -> None:
    stored = await db.label_transfers.find_one({"id": doc["id"]}, {"_id": 0, "plan": 1})
    # Nothing moves before a plan is stored, so such a transfer stays approved.
    status = "failed" if (stored or {}).get("plan") else "approved"
    detail = error if isinstance(error, str) else str(error)
    await db.label_transfers.update_one({"id": doc["id"]}, {"$set": {"status": status, "error": detail, "updated_at": now_iso()}})
    if status == "approved":
        await db.labels.update_many({"id": {"$in": label_ids}}, {"$unset": {"transfer_in_progress_id": ""}})


async def _refresh_analytics() -> None:
    try:
        from background_runtime import run_background
        from .admin_analytics import schedule_monthly_analytics_recompute
        from .dashboard_cache import schedule_recompute
        await run_background(schedule_monthly_analytics_recompute, reason="label_transfer")
        await schedule_recompute()
    except Exception:
        logger.exception("[LABEL-TRANSFER] analytics refresh scheduling failed")


async def get_transfer(transfer_id: str) -> dict:
    doc = await db.label_transfers.find_one({"id": transfer_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Perpindahan tidak ditemukan")
    return serialize(doc)


def serialize(doc: dict) -> dict:
    plan = doc.get("plan")
    return {**doc, "summary": summarize(doc), "plan": preview_view(plan) if plan else None}


def sale_routes(transfers: List[dict]) -> Dict[tuple, List[tuple]]:
    """(match_by, code) → [(effective_period, seller_label_id)] in effective order."""
    routes: Dict[tuple, List[tuple]] = {}
    for doc in transfers:
        plan = doc.get("plan") or {}
        for kind, codes in (("isrc", plan.get("isrcs") or []), ("upc", plan.get("upcs") or [])):
            for code in codes:
                routes.setdefault((kind, code), []).append((doc["effective_period"], doc["source_label_id"]))
    for entries in routes.values():
        entries.sort()
    return routes


def owner_for_period(routes: Dict[tuple, List[tuple]], match_by: str, code: Optional[str], period: str) -> Optional[str]:
    """Seller who owned a sold track/release for a reporting period, if any."""
    for effective_period, seller in routes.get((match_by, (code or "").strip().upper()), []):
        if period < effective_period:
            return seller
    return None


def valid_period(value: Optional[str]) -> bool:
    return bool(value and re.match(_PERIOD, value))
