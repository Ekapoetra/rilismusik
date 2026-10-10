"""System115 — versioned system settings (draft → publish).

Two areas are live on main:

  content     Landing page key/value map. The published store stays the
              `landing_settings` collection (public GET /cms/landing and
              the MDA preview are untouched); this module adds the draft /
              history / audit layer on top.
  procedures  Operational knobs (reminder schedules, withdraw floor,
              daily release cap). The published value lives in this
              collection; consumers read it through procedures_config with
              DEFAULTS as fallback — no migration needed.

Every write is Super Admin only and carries optimistic concurrency
(version + draft_version), the same contract as prototype system115.
Every mutation — including the legacy direct PATCH /cms/landing — lands
in the area's history and in the `system_audit` collection with sensitive
values redacted.
"""
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from models import new_id, now_iso
from procedures_config import DEFAULTS as PROCEDURES_DEFAULTS, set_published as _set_published_cache
from .deps import db, require_super_admin

system_r = APIRouter(prefix="/admin/system", tags=["system"])

AREAS = ("content", "procedures")
_HISTORY_LIMIT = 50
_AUDIT_LIMIT = 200


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class DraftIn(BaseModel):
    value: Dict[str, Any]
    note: Optional[str] = Field(default=None, max_length=500)
    version: int
    draft_version: int


class DiscardIn(BaseModel):
    version: int
    draft_version: int


class RestoreIn(BaseModel):
    history_id: str
    version: int
    draft_version: int


class PublishIn(BaseModel):
    note: str = Field(min_length=3, max_length=500)
    version: int
    draft_version: int
    blocks: Optional[List[str]] = None  # content: publish a subset of keys


# ---------------------------------------------------------------------------
# Redaction + diff (port of prototype `safe()` / `changed()`)
# ---------------------------------------------------------------------------

_RE_SENSITIVE_KEY = re.compile(
    r"password|secret|token|document(image|pending)?|signature|stamp|ktp|"
    r"imageurl|storagekey|attachment|cover|audio|file|photo|logo|banner",
    re.I,
)
_RE_SENSITIVE_NUM = re.compile(r"^(number|nik|accountnumber|banknumber)$", re.I)


def _safe(value, key: str = ""):
    if _RE_SENSITIVE_KEY.search(key or ""):
        return "[Data dilindungi]"
    if _RE_SENSITIVE_NUM.search(key or ""):
        return "[Nomor dilindungi]"
    if isinstance(value, str) and value.startswith("data:"):
        return "[Berkas]"
    if isinstance(value, list):
        return [_safe(v) for v in value]
    if isinstance(value, dict):
        return {k: _safe(v, k) for k, v in value.items()}
    return value


def _changed(before, after, path: str = "") -> List[Dict[str, Any]]:
    """Field-level diff [{field, before, after}] — values already redacted."""
    if before == after:
        return []
    if isinstance(before, dict) and isinstance(after, dict):
        diff = []
        for key in set(before) | set(after):
            diff += _changed(before.get(key), after.get(key), f"{path}.{key}" if path else key)
        return diff
    return [{"field": path or "(root)", "before": _safe(before, path), "after": _safe(after, path)}]


# ---------------------------------------------------------------------------
# Validation per area
# ---------------------------------------------------------------------------

_INT_LIST_RULES = {
    "subscription_reminder_days": (1, 90),
    "contract_reminder_days": (1, 90),
    "payment_pending_reminder_hours": (1, 720),
}
_INT_RULES = {
    "withdraw_min_idr": (10_000, 100_000_000),
    "daily_release_limit": (1, 100),
}


def _validate(area: str, value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict) or not value:
        raise HTTPException(status_code=400, detail="Nilai pengaturan harus berupa objek tidak kosong")
    for key in value:
        if not isinstance(key, str) or not key.strip() or len(key) > 80 or key.startswith("_"):
            raise HTTPException(status_code=400, detail=f"Kunci tidak valid: {key!r}")
    if area == "procedures":
        unknown = set(value) - set(PROCEDURES_DEFAULTS)
        if unknown:
            raise HTTPException(status_code=400, detail=f"Kunci prosedur tidak dikenal: {sorted(unknown)}")
        for key, (lo, hi) in _INT_LIST_RULES.items():
            items = value.get(key)
            if items is None:
                continue
            if (not isinstance(items, list) or not items
                    or any(not isinstance(x, int) or isinstance(x, bool) or x < lo or x > hi for x in items)):
                raise HTTPException(status_code=400, detail=f"{key}: daftar bilangan {lo}-{hi} wajib")
            if len(set(items)) != len(items):
                raise HTTPException(status_code=400, detail=f"{key}: nilai duplikat")
        for key, (lo, hi) in _INT_RULES.items():
            item = value.get(key)
            if item is None:
                continue
            if not isinstance(item, int) or isinstance(item, bool) or item < lo or item > hi:
                raise HTTPException(status_code=400, detail=f"{key}: bilangan {lo}-{hi} wajib")
    return value


# ---------------------------------------------------------------------------
# Store helpers
# ---------------------------------------------------------------------------

async def _area_doc(area: str) -> Dict[str, Any]:
    doc = await db.system_settings.find_one({"area": area}, {"_id": 0})
    if not doc:
        doc = {
            "area": area, "version": 0, "draft": None, "draft_version": 0,
            "base": 0, "history": [], "published": None,
            "applied_at": None, "applied_by": None, "note": None,
        }
    return doc


async def _landing_map() -> Dict[str, Any]:
    rows = await db.landing_settings.find({}, {"_id": 0}).to_list(500)
    return {r["key"]: r["value"] for r in rows}


async def _published(area: str, doc: Dict[str, Any]) -> Dict[str, Any]:
    if area == "content":
        return await _landing_map()
    merged = dict(PROCEDURES_DEFAULTS)
    merged.update(doc.get("published") or {})
    return merged


async def _audit(actor_id: str, kind: str, area: str, before, after, note: Optional[str] = None):
    await db.system_audit.insert_one({
        "id": "SYS-" + new_id()[:10].upper(),
        "actor": actor_id, "kind": kind, "area": area,
        "diff": _changed(before, after), "note": note or "",
        "at": now_iso(),
    })


def _concurrency(doc: Dict[str, Any], version: int, draft_version: int):
    if doc.get("version", 0) != version or doc.get("draft_version", 0) != draft_version:
        raise HTTPException(
            status_code=409,
            detail="Pengaturan telah berubah. Muat versi terbaru dan tinjau ulang.",
        )


def _summary(area: str, doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "area": area, "version": doc.get("version", 0),
        "has_draft": doc.get("draft") is not None,
        "draft_version": doc.get("draft_version", 0),
        "applied_at": doc.get("applied_at"), "applied_by": doc.get("applied_by"),
        "note": doc.get("note"),
    }


# ---------------------------------------------------------------------------
# Content-area publish plumbing (shared with the legacy PATCH /cms/landing)
# ---------------------------------------------------------------------------

async def _apply_content_map(actor_id: str, target: Dict[str, Any]):
    """Apply a full landing map onto `landing_settings` (upsert + delete)."""
    current = await _landing_map()
    for key, value in target.items():
        if current.get(key) != value:
            await db.landing_settings.update_one(
                {"key": key},
                {"$set": {"key": key, "value": value, "updated_by": actor_id, "updated_at": now_iso()}},
                upsert=True,
            )
    for key in set(current) - set(target):
        await db.landing_settings.delete_one({"key": key})


async def record_content_publish(actor_id: str, before_map: Dict[str, Any], after_map: Dict[str, Any],
                                 note: str, kind: str = "publish") -> None:
    """Version + audit a content change. Called by the versioned publish flow
    AND by the legacy PATCH /cms/landing so direct edits stay versioned."""
    doc = await _area_doc("content")
    entry = {
        "id": "VER-" + new_id()[:10].upper(), "version": doc.get("version", 0),
        "value": before_map, "at": doc.get("applied_at") or now_iso(),
        "actor": doc.get("applied_by"), "note": doc.get("note") or "Versi awal",
    }
    history = [entry] + (doc.get("history") or [])
    await db.system_settings.update_one(
        {"area": "content"},
        {"$set": {
            "area": "content", "version": doc.get("version", 0) + 1,
            "history": history[:_HISTORY_LIMIT],
            "applied_at": now_iso(), "applied_by": actor_id, "note": note,
            "updated_at": now_iso(),
        }},
        upsert=True,
    )
    await _audit(actor_id, kind, "content", before_map, after_map, note)


async def get_published_procedures() -> Dict[str, Any]:
    """Load published procedures into the sync cache; returns merged dict."""
    doc = await db.system_settings.find_one({"area": "procedures"}, {"_id": 0})
    merged = dict(PROCEDURES_DEFAULTS)
    merged.update((doc or {}).get("published") or {})
    _set_published_cache(merged)
    return merged


# ---------------------------------------------------------------------------
# Endpoints (Super Admin only — mirrors prototype guard)
# ---------------------------------------------------------------------------

@system_r.get("/areas")
async def list_areas(user: dict = Depends(require_super_admin)):
    docs = await db.system_settings.find({"area": {"$in": list(AREAS)}}, {"_id": 0, "history": 0, "draft": 0}).to_list(20)
    by_area = {d["area"]: d for d in docs}
    return {"areas": [_summary(a, by_area.get(a) or {"area": a}) for a in AREAS]}


@system_r.get("/{area}")
async def get_area(area: str, user: dict = Depends(require_super_admin)):
    if area not in AREAS:
        raise HTTPException(status_code=404, detail="Bagian konfigurasi tidak dikenal")
    doc = await _area_doc(area)
    return {
        **_summary(area, doc),
        "published": await _published(area, doc),
        "draft": doc.get("draft"),
        "draft_version": doc.get("draft_version", 0),
        "base": doc.get("base", 0),
        "history": doc.get("history") or [],
    }


@system_r.get("/{area}/audit")
async def get_audit(area: str, user: dict = Depends(require_super_admin)):
    if area not in AREAS:
        raise HTTPException(status_code=404, detail="Bagian konfigurasi tidak dikenal")
    rows = await db.system_audit.find({"area": area}, {"_id": 0}).sort("at", -1).to_list(_AUDIT_LIMIT)
    return {"entries": rows}


@system_r.post("/{area}/draft")
async def save_draft(area: str, body: DraftIn, user: dict = Depends(require_super_admin)):
    if area not in AREAS:
        raise HTTPException(status_code=404, detail="Bagian konfigurasi tidak dikenal")
    doc = await _area_doc(area)
    _concurrency(doc, body.version, body.draft_version)
    value = _validate(area, body.value)
    before = doc.get("draft")
    await db.system_settings.update_one(
        {"area": area},
        {"$set": {
            "area": area, "draft": value, "base": doc.get("version", 0),
            "updated_at": now_iso(),
        }, "$inc": {"draft_version": 1}},
        upsert=True,
    )
    await _audit(user["id"], "draft-save", area, before, value, body.note)
    return await get_area(area, user)


@system_r.post("/{area}/discard")
async def discard_draft(area: str, body: DiscardIn, user: dict = Depends(require_super_admin)):
    if area not in AREAS:
        raise HTTPException(status_code=404, detail="Bagian konfigurasi tidak dikenal")
    doc = await _area_doc(area)
    _concurrency(doc, body.version, body.draft_version)
    if doc.get("draft") is None:
        raise HTTPException(status_code=409, detail="Tidak ada draf")
    await db.system_settings.update_one(
        {"area": area},
        {"$set": {"draft": None, "updated_at": now_iso()}, "$inc": {"draft_version": 1}},
    )
    await _audit(user["id"], "draft-discard", area, doc.get("draft"), None, None)
    return await get_area(area, user)


@system_r.post("/{area}/restore")
async def restore_history(area: str, body: RestoreIn, user: dict = Depends(require_super_admin)):
    if area not in AREAS:
        raise HTTPException(status_code=404, detail="Bagian konfigurasi tidak dikenal")
    doc = await _area_doc(area)
    _concurrency(doc, body.version, body.draft_version)
    entry = next((h for h in (doc.get("history") or []) if h.get("id") == body.history_id), None)
    if not entry:
        raise HTTPException(status_code=404, detail="Versi tidak tersedia")
    await db.system_settings.update_one(
        {"area": area},
        {"$set": {"draft": entry.get("value"), "base": doc.get("version", 0), "updated_at": now_iso()},
         "$inc": {"draft_version": 1}},
    )
    await _audit(user["id"], "draft-restore", area, None, {"source": entry.get("id")}, None)
    return await get_area(area, user)


@system_r.post("/{area}/publish")
async def publish(area: str, body: PublishIn, user: dict = Depends(require_super_admin)):
    if area not in AREAS:
        raise HTTPException(status_code=404, detail="Bagian konfigurasi tidak dikenal")
    doc = await _area_doc(area)
    _concurrency(doc, body.version, body.draft_version)
    draft = doc.get("draft")
    if draft is None:
        raise HTTPException(status_code=409, detail="Simpan draf sebelum menerapkan")
    if doc.get("base", 0) != doc.get("version", 0):
        raise HTTPException(status_code=409, detail="Draf dibuat dari versi lama. Tinjau ulang.")

    published = await _published(area, doc)
    target = dict(draft)
    if area == "content" and body.blocks:
        # Partial publish: only the listed keys change; the rest of the
        # published map is preserved (prototype per-block publish).
        target = dict(published)
        for key in body.blocks:
            if key in draft:
                target[key] = draft[key]
            else:
                target.pop(key, None)
    target = _validate(area, target)
    diff = _changed(published, target)
    if not diff:
        raise HTTPException(status_code=409, detail="Belum ada perubahan untuk diterapkan")

    if area == "content":
        await _apply_content_map(user["id"], target)
        await record_content_publish(user["id"], published, target, body.note)
    else:
        history = [{
            "id": "VER-" + new_id()[:10].upper(), "version": doc.get("version", 0),
            "value": published, "at": doc.get("applied_at") or now_iso(),
            "actor": doc.get("applied_by"), "note": doc.get("note") or "Versi awal",
        }] + (doc.get("history") or [])
        await db.system_settings.update_one(
            {"area": area},
            {"$set": {
                "published": target, "version": doc.get("version", 0) + 1,
                "history": history[:_HISTORY_LIMIT], "applied_at": now_iso(),
                "applied_by": user["id"], "note": body.note, "updated_at": now_iso(),
            }},
            upsert=True,
        )
        _set_published_cache(target)
        await _audit(user["id"], "publish", area, published, target, body.note)

    # A published draft is consumed; version bump invalidates stale drafts.
    await db.system_settings.update_one(
        {"area": area}, {"$set": {"draft": None}, "$inc": {"draft_version": 1}},
    )
    return await get_area(area, user)
