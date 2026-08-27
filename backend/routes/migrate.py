"""Bulk data migration endpoints (P0 — for initial production seed).

Four CSV-based imports + claim management:
  - Labels (legacy labels with no email, user_id=None, status='legacy_unclaimed')
  - Releases (legacy releases, imported_legacy=true, audio_url optional)
  - Tracks (legacy tracks, audio_url optional)
  - Withdraws (historical withdraw_requests + balance_transactions, silent — no notifications)
  - Claims (label registers with claim flag → admin links to legacy label_id)

Each import:
  - Idempotent by composite key (skips duplicates)
  - Returns a per-row report (success/error reason)
  - Counts: total_rows, inserted, skipped, errors
  - Caps file size to MAX_BULK_BYTES to protect server memory
"""
import io
import csv as csv_module
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Form
from fastapi.responses import StreamingResponse

from .deps import (
    db, db_bg, logger, UPLOAD_DIR,
    require_admin, require_super_admin, log_activity, notify,
)
from models import now_iso, new_id
from royalty_utils import normalize_label_match_name
from .royalty_recalculation import recalculate_label_unwithdrawn, trigger_royalty_caches
from .dashboard_cache import schedule_recompute as schedule_dashboard_recompute


migrate_r = APIRouter(prefix="/admin/migrate", tags=["admin-migrate"])

MAX_BULK_BYTES = 30 * 1024 * 1024  # 30 MB hard cap


# ----------------------------- helpers -----------------------------

def _read_csv_bytes(content: bytes) -> List[Dict[str, str]]:
    """Read CSV (UTF-8 or UTF-8-BOM, comma/semicolon detect) into a list of dict rows."""
    if not content:
        return []
    if len(content) > MAX_BULK_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File terlalu besar (max {MAX_BULK_BYTES // (1024*1024)} MB). Pecah jadi beberapa CSV.",
        )
    # Strip UTF-8 BOM if present
    if content.startswith(b"\xef\xbb\xbf"):
        content = content[3:]
    text = content.decode("utf-8", errors="replace")
    # Detect delimiter on first non-empty line
    sniff_line = next((ln for ln in text.splitlines() if ln.strip()), "")
    delim = ";" if sniff_line.count(";") > sniff_line.count(",") else ","
    reader = csv_module.DictReader(io.StringIO(text), delimiter=delim)
    out: List[Dict[str, str]] = []
    for r in reader:
        clean: Dict[str, str] = {}
        for k, v in r.items():
            if k is None:
                # `DictReader` puts overflow cells under key=None as a list.
                # Skip silently — we don't have a header to map them to.
                continue
            if isinstance(v, list):
                v = ",".join(str(x) for x in v if x is not None)
            clean[(k or "").strip()] = (v or "").strip() if isinstance(v, str) else ""
        out.append(clean)
    return out


def _csv_response(rows: List[Dict[str, Any]], filename: str) -> StreamingResponse:
    """Stream a CSV of `rows` (list of dicts) back to the client."""
    if not rows:
        rows = [{"info": "No rows"}]
    output = io.StringIO()
    writer = csv_module.DictWriter(output, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _parse_iso_date(s: Optional[str]) -> Optional[str]:
    """Accept YYYY-MM-DD or DD/MM/YYYY or DD-MM-YYYY → return YYYY-MM-DD or None."""
    if not s or not s.strip():
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _parse_iso_dt(s: Optional[str]) -> Optional[str]:
    """Accept YYYY-MM-DD → return ISO datetime string. None if invalid."""
    d = _parse_iso_date(s)
    if not d:
        return None
    return f"{d}T00:00:00+00:00"


def _normalize_label_name(s: Optional[str]) -> str:
    """Aggressive normalization to match legacy CSV `nama_label` against current
    `labels.label_name`. Lowercases, strips quotes/punctuation/whitespace, drops
    leading 'PT '/'PT, '/'PT. ' prefixes, and collapses consecutive spaces.

    Examples:
      "PT, Enam Belas Record"  -> "enam belas record"
      "PT enam belas music"    -> "enam belas music"
      "f - audio"              -> "f audio"
      " F - Audio "            -> "f audio"
    """
    return normalize_label_match_name(s)


def _require_migrate_role(user: dict):
    """Only Super Admin can run bulk migration to prevent accidental data drift."""
    if user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Hanya Super Admin yang boleh menjalankan migrasi data.")


# ============================ TEMPLATES ============================

@migrate_r.get("/template/{kind}")
async def download_template(kind: str, user: dict = Depends(require_admin)):
    """Download a blank CSV template for `kind` ∈ {labels, releases, tracks, withdraws}."""
    templates = {
        "labels": [
            "label_name", "pic_name", "whatsapp", "address", "city", "country",
            "label_type", "payment_type", "subscription_tier", "subscription_expires_at",
            "account_status", "royalty_percentage_default", "notes",
        ],
        "releases": [
            "label_legacy_id", "label_name", "release_title", "primary_artist",
            "isrc_release", "upc", "release_type", "release_date",
            "status", "cover_url", "notes",
        ],
        "tracks": [
            "release_legacy_id", "release_isrc", "track_title", "artist_name",
            "isrc", "duration_sec", "composer", "audio_url",
        ],
        "withdraws": [
            "label_legacy_id", "label_name", "amount_idr", "request_date",
            "payment_date", "status", "bank_ref", "notes",
        ],
    }
    if kind not in templates:
        raise HTTPException(status_code=404, detail="Template tidak dikenal")
    sample_row = {col: "" for col in templates[kind]}
    return _csv_response([sample_row], f"template_{kind}.csv")


# ============================ LABELS ============================

@migrate_r.post("/labels")
async def bulk_import_labels(
    file: UploadFile = File(...),
    dry_run: bool = Form(False),
    user: dict = Depends(require_admin),
):
    """Bulk import legacy labels. user_id=None, account_status='legacy_unclaimed'.

    CSV columns (header row required):
        label_name (required, unique-ish — composite key with city)
        pic_name (required)
        whatsapp (required)
        address, city, country (optional, defaults to Indonesia)
        label_type: label | independent_artist (default 'label')
        payment_type: pay_per_release | annual_subscription (default 'pay_per_release')
        subscription_tier: annual_normal | annual_vip | (empty)
        subscription_expires_at: YYYY-MM-DD (empty if no subscription)
        account_status: active | suspended | legacy_unclaimed (default 'legacy_unclaimed')
        royalty_percentage_default: 0-100 (default 60)
        notes: free text
    """
    _require_migrate_role(user)
    content = await file.read()
    rows = _read_csv_bytes(content)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV kosong")

    report: List[Dict[str, Any]] = []
    inserted = 0
    skipped = 0
    errors = 0

    # Pre-fetch existing labels to detect duplicates
    existing = {}
    async for lab in db.labels.find({}, {"_id": 0, "id": 1, "label_name": 1, "city": 1}):
        key = ((lab.get("label_name") or "").strip().lower(), (lab.get("city") or "").strip().lower())
        existing[key] = lab["id"]

    now = now_iso()
    docs_to_insert: List[Dict[str, Any]] = []

    for i, r in enumerate(rows, start=2):  # row 1 is header
        label_name = (r.get("label_name") or "").strip()
        pic_name = (r.get("pic_name") or "").strip()
        whatsapp = (r.get("whatsapp") or "").strip()
        if not label_name or not pic_name or not whatsapp:
            errors += 1
            report.append({"row": i, "label_name": label_name, "status": "ERROR", "reason": "label_name, pic_name, whatsapp wajib diisi"})
            continue
        city = (r.get("city") or "").strip()
        key = (label_name.lower(), city.lower())
        if key in existing:
            skipped += 1
            report.append({"row": i, "label_name": label_name, "status": "SKIPPED", "reason": f"Sudah ada (id={existing[key]})"})
            continue

        # Validate subscription_tier
        tier = (r.get("subscription_tier") or "").strip() or None
        if tier and tier not in ("annual_normal", "annual_vip"):
            errors += 1
            report.append({"row": i, "label_name": label_name, "status": "ERROR", "reason": f"subscription_tier invalid: {tier}"})
            continue
        payment_type = (r.get("payment_type") or "").strip() or "pay_per_release"
        if payment_type not in ("pay_per_release", "annual_subscription"):
            errors += 1
            report.append({"row": i, "label_name": label_name, "status": "ERROR", "reason": f"payment_type invalid: {payment_type}"})
            continue
        sub_expires = _parse_iso_dt(r.get("subscription_expires_at"))
        sub_status = "active" if (sub_expires and tier) else "inactive"

        try:
            roy_pct = float(r.get("royalty_percentage_default") or 60)
            if not (0 <= roy_pct <= 100):
                raise ValueError("out of range")
        except Exception:
            errors += 1
            report.append({"row": i, "label_name": label_name, "status": "ERROR", "reason": "royalty_percentage_default harus 0-100"})
            continue

        label_id = new_id()
        doc = {
            "id": label_id,
            "user_id": None,  # Unclaimed — admin will link later via claim flow
            "label_name": label_name,
            "pic_name": pic_name,
            "email": None,  # Will be filled when label claims via /register
            "whatsapp": whatsapp,
            "address": (r.get("address") or "").strip() or None,
            "city": city or None,
            "country": (r.get("country") or "").strip() or "Indonesia",
            "label_type": (r.get("label_type") or "").strip() or "label",
            "royalty_percentage_default": roy_pct,
            "payment_type": payment_type,
            "subscription_status": sub_status,
            "subscription_tier": tier,
            "subscription_expires_at": sub_expires,
            "contract_status": "active",
            "account_status": (r.get("account_status") or "").strip() or "legacy_unclaimed",
            "bank_verified": False,
            "blacklisted": False,
            "balance_available_idr": 0,
            "balance_pending_idr": 0,
            "balance_withdraw_requested_idr": 0,
            "mda_accepted_at": None,  # Will be set on claim
            "legacy_import": True,
            "legacy_notes": (r.get("notes") or "").strip() or None,
            "created_at": now,
            "updated_at": now,
        }
        docs_to_insert.append(doc)
        existing[key] = label_id  # prevent in-file duplicates
        inserted += 1
        report.append({"row": i, "label_name": label_name, "status": "OK", "reason": f"id={label_id}"})

    if not dry_run and docs_to_insert:
        await db.labels.insert_many(docs_to_insert)
        await log_activity(user["id"], "bulk_import_labels", "migrate", None, after={"inserted": inserted, "skipped": skipped, "errors": errors})

    return {
        "dry_run": dry_run,
        "total_rows": len(rows),
        "inserted": inserted,
        "skipped": skipped,
        "errors": errors,
        "report": report[:1000],  # cap response size
    }


# ============================ RELEASES ============================

@migrate_r.post("/releases")
async def bulk_import_releases(
    file: UploadFile = File(...),
    dry_run: bool = Form(False),
    user: dict = Depends(require_admin),
):
    """Bulk import legacy releases. imported_legacy=true, audio validation bypassed."""
    _require_migrate_role(user)
    content = await file.read()
    rows = _read_csv_bytes(content)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV kosong")

    # Build label lookup by id AND lowercased name
    labels_by_id: Dict[str, dict] = {}
    labels_by_name: Dict[str, dict] = {}
    async for lab in db.labels.find({}, {"_id": 0, "id": 1, "label_name": 1}):
        labels_by_id[lab["id"]] = lab
        labels_by_name[(lab.get("label_name") or "").strip().lower()] = lab

    existing_isrcs = set()
    async for rl in db.releases.find({"isrc_release": {"$ne": None}}, {"_id": 0, "isrc_release": 1}):
        if rl.get("isrc_release"):
            existing_isrcs.add(rl["isrc_release"].strip().upper())
    existing_upcs = set()
    async for rl in db.releases.find({"upc": {"$ne": None}}, {"_id": 0, "upc": 1}):
        if rl.get("upc"):
            existing_upcs.add(rl["upc"].strip().upper())

    report: List[Dict[str, Any]] = []
    inserted = 0
    skipped = 0
    errors = 0
    docs_to_insert: List[Dict[str, Any]] = []
    now = now_iso()

    for i, r in enumerate(rows, start=2):
        title = (r.get("release_title") or "").strip()
        primary_artist = (r.get("primary_artist") or "").strip()
        if not title or not primary_artist:
            errors += 1
            report.append({"row": i, "release_title": title, "status": "ERROR", "reason": "release_title + primary_artist wajib"})
            continue

        # Match label by legacy id or name
        label_legacy_id = (r.get("label_legacy_id") or "").strip()
        label_name = (r.get("label_name") or "").strip()
        lab = None
        if label_legacy_id and label_legacy_id in labels_by_id:
            lab = labels_by_id[label_legacy_id]
        elif label_name:
            lab = labels_by_name.get(label_name.lower())
        if not lab:
            errors += 1
            report.append({"row": i, "release_title": title, "status": "ERROR", "reason": f"Label tidak ditemukan: {label_name or label_legacy_id}"})
            continue

        isrc_release = ((r.get("isrc_release") or "").strip().upper() or None)
        upc = ((r.get("upc") or "").strip().upper() or None)
        if isrc_release and isrc_release in existing_isrcs:
            skipped += 1
            report.append({"row": i, "release_title": title, "status": "SKIPPED", "reason": f"ISRC sudah ada: {isrc_release}"})
            continue
        if upc and upc in existing_upcs:
            skipped += 1
            report.append({"row": i, "release_title": title, "status": "SKIPPED", "reason": f"UPC sudah ada: {upc}"})
            continue

        release_type = (r.get("release_type") or "").strip() or "single"
        if release_type not in ("single", "ep", "album", "compilation"):
            errors += 1
            report.append({"row": i, "release_title": title, "status": "ERROR", "reason": f"release_type invalid: {release_type}"})
            continue

        release_date = _parse_iso_date(r.get("release_date")) or "2021-01-01"  # default for very old legacy
        status = (r.get("status") or "").strip() or "live"

        release_id = new_id()
        doc = {
            "id": release_id,
            "label_id": lab["id"],
            "release_title": title,
            "primary_artist": primary_artist,
            "isrc_release": isrc_release,
            "upc": upc,
            "release_type": release_type,
            "release_date": release_date,
            "status": status,  # 'live' for legacy; admin can override
            "cover_url": (r.get("cover_url") or "").strip() or None,
            "imported_legacy": True,
            "legacy_notes": (r.get("notes") or "").strip() or None,
            "created_at": now,
            "updated_at": now,
        }
        docs_to_insert.append(doc)
        if isrc_release:
            existing_isrcs.add(isrc_release)
        if upc:
            existing_upcs.add(upc)
        inserted += 1
        report.append({"row": i, "release_title": title, "status": "OK", "reason": f"id={release_id}, label={lab.get('label_name')}"})

    if not dry_run and docs_to_insert:
        # Chunk inserts to avoid > 16 MB batch limit
        for k in range(0, len(docs_to_insert), 1000):
            await db.releases.insert_many(docs_to_insert[k:k + 1000])
        await log_activity(user["id"], "bulk_import_releases", "migrate", None, after={"inserted": inserted, "skipped": skipped, "errors": errors})

    return {
        "dry_run": dry_run,
        "total_rows": len(rows),
        "inserted": inserted,
        "skipped": skipped,
        "errors": errors,
        "report": report[:1000],
    }


# ============================ TRACKS ============================

@migrate_r.post("/tracks")
async def bulk_import_tracks(
    file: UploadFile = File(...),
    dry_run: bool = Form(False),
    user: dict = Depends(require_admin),
):
    _require_migrate_role(user)
    content = await file.read()
    rows = _read_csv_bytes(content)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV kosong")

    # Build release lookup by id AND lowercased ISRC_release
    releases_by_id: Dict[str, dict] = {}
    releases_by_isrc: Dict[str, dict] = {}
    async for rl in db.releases.find({}, {"_id": 0, "id": 1, "label_id": 1, "isrc_release": 1, "release_title": 1, "primary_artist": 1}):
        releases_by_id[rl["id"]] = rl
        if rl.get("isrc_release"):
            releases_by_isrc[rl["isrc_release"].strip().upper()] = rl

    existing_isrcs = set()
    async for t in db.tracks.find({"isrc": {"$ne": None}}, {"_id": 0, "isrc": 1}):
        if t.get("isrc"):
            existing_isrcs.add(t["isrc"].strip().upper())

    report: List[Dict[str, Any]] = []
    inserted = 0
    skipped = 0
    errors = 0
    docs_to_insert: List[Dict[str, Any]] = []
    now = now_iso()

    for i, r in enumerate(rows, start=2):
        track_title = (r.get("track_title") or "").strip()
        if not track_title:
            errors += 1
            report.append({"row": i, "track_title": track_title, "status": "ERROR", "reason": "track_title wajib"})
            continue

        rel_legacy_id = (r.get("release_legacy_id") or "").strip()
        rel_isrc = (r.get("release_isrc") or "").strip().upper()
        rel = None
        if rel_legacy_id and rel_legacy_id in releases_by_id:
            rel = releases_by_id[rel_legacy_id]
        elif rel_isrc and rel_isrc in releases_by_isrc:
            rel = releases_by_isrc[rel_isrc]
        if not rel:
            errors += 1
            report.append({"row": i, "track_title": track_title, "status": "ERROR", "reason": f"Release tidak ditemukan: {rel_legacy_id or rel_isrc}"})
            continue

        isrc = ((r.get("isrc") or "").strip().upper() or None)
        if isrc and isrc in existing_isrcs:
            skipped += 1
            report.append({"row": i, "track_title": track_title, "status": "SKIPPED", "reason": f"ISRC sudah ada: {isrc}"})
            continue

        artist_name = (r.get("artist_name") or "").strip() or rel.get("primary_artist", "")
        duration_sec_raw = (r.get("duration_sec") or "").strip()
        duration_sec = None
        if duration_sec_raw:
            try:
                duration_sec = int(float(duration_sec_raw))
            except Exception:
                pass

        track_id = new_id()
        doc = {
            "id": track_id,
            "release_id": rel["id"],
            "label_id": rel["label_id"],
            "artist_id": None,  # Optional; admin can link to artist later
            "track_title": track_title,
            "artist_name": artist_name,
            "isrc": isrc,
            "duration_sec": duration_sec,
            "composer": (r.get("composer") or "").strip() or None,
            "audio_url": (r.get("audio_url") or "").strip() or None,
            "imported_legacy": True,
            "created_at": now,
            "updated_at": now,
        }
        docs_to_insert.append(doc)
        if isrc:
            existing_isrcs.add(isrc)
        inserted += 1
        report.append({"row": i, "track_title": track_title, "status": "OK", "reason": f"id={track_id}, release={rel.get('release_title')}"})

    if not dry_run and docs_to_insert:
        for k in range(0, len(docs_to_insert), 1000):
            await db.tracks.insert_many(docs_to_insert[k:k + 1000])
        await log_activity(user["id"], "bulk_import_tracks", "migrate", None, after={"inserted": inserted, "skipped": skipped, "errors": errors})

    return {
        "dry_run": dry_run,
        "total_rows": len(rows),
        "inserted": inserted,
        "skipped": skipped,
        "errors": errors,
        "report": report[:1000],
    }


# ============================ WITHDRAWS ============================

@migrate_r.post("/withdraws")
async def bulk_import_withdraws(
    file: UploadFile = File(...),
    dry_run: bool = Form(False),
    user: dict = Depends(require_admin),
):
    """Insert historical withdraw_requests + balance_transactions. NO notifications, NO balance mutation."""
    _require_migrate_role(user)
    content = await file.read()
    rows = _read_csv_bytes(content)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV kosong")

    labels_by_id: Dict[str, dict] = {}
    labels_by_name: Dict[str, dict] = {}
    async for lab in db.labels.find({}, {"_id": 0, "id": 1, "label_name": 1}):
        labels_by_id[lab["id"]] = lab
        labels_by_name[(lab.get("label_name") or "").strip().lower()] = lab

    report: List[Dict[str, Any]] = []
    inserted = 0
    errors = 0
    wd_docs: List[Dict[str, Any]] = []
    tx_docs: List[Dict[str, Any]] = []

    for i, r in enumerate(rows, start=2):
        label_legacy_id = (r.get("label_legacy_id") or "").strip()
        label_name = (r.get("label_name") or "").strip()
        lab = None
        if label_legacy_id and label_legacy_id in labels_by_id:
            lab = labels_by_id[label_legacy_id]
        elif label_name:
            lab = labels_by_name.get(label_name.lower())
        if not lab:
            errors += 1
            report.append({"row": i, "label_name": label_name, "status": "ERROR", "reason": "Label tidak ditemukan"})
            continue

        try:
            amount = int(float((r.get("amount_idr") or "0").replace(".", "").replace(",", "")))
            if amount <= 0:
                raise ValueError("must be > 0")
        except Exception:
            errors += 1
            report.append({"row": i, "label_name": label_name, "status": "ERROR", "reason": "amount_idr invalid"})
            continue

        req_date = _parse_iso_dt(r.get("request_date"))
        pay_date = _parse_iso_dt(r.get("payment_date"))
        if not req_date:
            errors += 1
            report.append({"row": i, "label_name": label_name, "status": "ERROR", "reason": "request_date wajib (YYYY-MM-DD)"})
            continue

        status_raw = (r.get("status") or "").strip().lower() or "paid"
        if status_raw not in ("paid", "cancelled", "rejected", "completed"):
            errors += 1
            report.append({"row": i, "label_name": label_name, "status": "ERROR", "reason": f"status invalid: {status_raw}"})
            continue
        # Normalise — old data may use "completed"
        if status_raw == "completed":
            status_raw = "paid"

        wd_id = new_id()
        wd_docs.append({
            "id": wd_id,
            "label_id": lab["id"],
            "amount_idr": amount,
            "status": status_raw,
            "bank_ref": (r.get("bank_ref") or "").strip() or None,
            "notes": (r.get("notes") or "").strip() or None,
            "requested_at": req_date,
            "paid_at": pay_date,
            "legacy_import": True,
            "created_at": req_date,  # back-date for history fidelity
            "updated_at": pay_date or req_date,
        })
        # Matching balance_transaction for accounting trail (does NOT mutate current balance)
        tx_docs.append({
            "id": new_id(),
            "label_id": lab["id"],
            "type": "withdraw_paid" if status_raw == "paid" else f"withdraw_{status_raw}",
            "amount_idr": -amount if status_raw == "paid" else 0,
            "reference_type": "withdraw_request",
            "reference_id": wd_id,
            "description": f"[Legacy] Withdraw {status_raw} — Rp {amount:,}".replace(",", "."),
            "legacy_import": True,
            "created_at": pay_date or req_date,
        })
        inserted += 1
        report.append({"row": i, "label_name": label_name, "status": "OK", "reason": f"withdraw_id={wd_id}, amount={amount}"})

    if not dry_run and wd_docs:
        await db.withdraw_requests.insert_many(wd_docs)
        await db.balance_transactions.insert_many(tx_docs)
        await log_activity(user["id"], "bulk_import_withdraws", "migrate", None, after={"inserted": inserted, "errors": errors})

    return {
        "dry_run": dry_run,
        "total_rows": len(rows),
        "inserted": inserted,
        "errors": errors,
        "report": report[:1000],
    }


# ============================ CLAIMS ============================

@migrate_r.get("/claims")
async def list_pending_claims(user: dict = Depends(require_admin)):
    """List label-claim requests awaiting admin link."""
    items = await db.users.find(
        {"role": "label", "claim_status": "pending_link"},
        {"_id": 0, "password_hash": 0},
    ).sort("created_at", -1).limit(500).to_list(500)
    return items


@migrate_r.post("/claims/{user_id}/link/{legacy_label_id}")
async def link_claim_to_legacy_label(user_id: str, legacy_label_id: str, user: dict = Depends(require_admin)):
    """Admin links a pending-claim user to an existing unclaimed legacy label."""
    if user.get("role") not in ("super_admin", "admin_release", "admin_support"):
        raise HTTPException(status_code=403, detail="Hanya Super Admin / Release / Support yang boleh link claim")
    u = await db.users.find_one({"id": user_id})
    if not u:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    if u.get("claim_status") != "pending_link":
        raise HTTPException(status_code=400, detail="User bukan pending claim")

    lab = await db.labels.find_one({"id": legacy_label_id})
    if not lab:
        raise HTTPException(status_code=404, detail="Legacy label tidak ditemukan")
    if lab.get("user_id"):
        raise HTTPException(status_code=400, detail="Label sudah di-claim oleh user lain")

    accepted_at = now_iso()
    await db.labels.update_one(
        {"id": legacy_label_id},
        {"$set": {
            "user_id": user_id,
            "email": u.get("email"),
            "account_status": "active",
            "mda_accepted_at": accepted_at,
            "claim_resolved_at": accepted_at,
            "claim_resolved_by": user["id"],
            "updated_at": accepted_at,
        }},
    )
    await db.users.update_one(
        {"id": user_id},
        {"$set": {
            "claim_status": "linked",
            "claim_linked_label_id": legacy_label_id,
            "claim_resolved_at": accepted_at,
            "updated_at": accepted_at,
        }},
    )

    # Auto-generate MDA PDF now (was skipped during register because no label existed yet)
    try:
        from .mda_generator import generate_mda_pdf_bytes
        import storage_service
        legal_setting = await db.landing_settings.find_one({"key": "legal_entity"}, {"_id": 0, "value": 1})
        legal_entity = (legal_setting or {}).get("value") or {}
        merged_label = {**lab, "email": u.get("email"), "pic_name": u.get("name"), "user_id": user_id}
        contract_id = new_id()
        pdf_bytes = generate_mda_pdf_bytes(merged_label, legal_entity)
        r2_key = f"contract/{contract_id}.pdf"
        await storage_service.upload_bytes(key=r2_key, data=pdf_bytes, content_type="application/pdf")
        file_url = f"/api/files/{r2_key}"
        await db.contracts.insert_one({
            "id": contract_id,
            "label_id": legacy_label_id,
            "label_name": lab.get("label_name"),
            "title": "Master Distribution Agreement",
            "kind": "mda",
            "file_url": file_url,
            "filename": f"MDA-{lab.get('label_name', '')[:20]}.pdf",
            "start_date": accepted_at[:10],
            "end_date": None,
            "is_lifetime": True,
            "status": "active",
            "notes": f"Auto-generated saat admin link claim oleh {user.get('email')}.",
            "accepted_at": accepted_at,
            "accepted_by_name": u.get("name"),
            "accepted_by_email": u.get("email"),
            "created_at": accepted_at,
            "updated_at": accepted_at,
            "created_by": user["id"],
        })
    except Exception as e:
        logger.warning("MDA generation on claim link failed: %s", e)

    await notify(
        user_id, "claim_linked",
        "Akun lama berhasil dihubungkan!",
        f"Admin telah menghubungkan akun Anda ke label '{lab.get('label_name')}'. Anda kini bisa melihat seluruh riwayat data.",
        "/label/dashboard", {"label_id": legacy_label_id},
    )
    await log_activity(
        user["id"], "link_claim", "migrate", user_id,
        before={"user_id": user_id, "label_id": None},
        after={"user_id": user_id, "label_id": legacy_label_id},
    )
    return {"ok": True, "user_id": user_id, "label_id": legacy_label_id}


@migrate_r.post("/claims/{user_id}/reject")
async def reject_claim(user_id: str, reason: str = Form(""), user: dict = Depends(require_admin)):
    if user.get("role") not in ("super_admin", "admin_release", "admin_support"):
        raise HTTPException(status_code=403, detail="Hanya Super Admin / Release / Support")
    u = await db.users.find_one({"id": user_id})
    if not u:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    if u.get("claim_status") != "pending_link":
        raise HTTPException(status_code=400, detail="User bukan pending claim")
    await db.users.update_one(
        {"id": user_id},
        {"$set": {
            "claim_status": "rejected",
            "claim_resolved_at": now_iso(),
            "claim_resolved_by": user["id"],
            "claim_reject_reason": reason,
            "updated_at": now_iso(),
        }},
    )
    await notify(
        user_id, "claim_rejected",
        "Permintaan claim ditolak",
        f"Admin menolak permintaan klaim akun lama Anda. Alasan: {reason or 'Tidak ada keterangan.'} Hubungi support untuk informasi lebih lanjut.",
        "/label/tickets", {},
    )
    return {"ok": True}


@migrate_r.get("/labels/unclaimed")
async def list_unclaimed_legacy_labels(q: str = "", user: dict = Depends(require_admin)):
    """List legacy labels waiting to be claimed (user_id is null)."""
    filt: Dict[str, Any] = {"user_id": None}
    if q:
        filt["label_name"] = {"$regex": q, "$options": "i"}
    items = await db.labels.find(filt, {"_id": 0}).sort("label_name", 1).limit(200).to_list(200)
    return items


# ===================================================================
# LEGACY WITHDRAW PERIOD-END MIGRATION (Phase 22 — for music_withdrawals.csv)
# ===================================================================
# This is a SEPARATE flow from /withdraws above. It maps the user's specific
# legacy CSV (columns: nama_label, period_start, period_end, amount,
# exchange_rate, status, …) into the modern FIFO system used by Phase 20.
#
# The ONLY two columns we treat as canonical are:
#   - `nama_label` → resolves to labels.id (fuzzy normalized)
#   - `period_end` → sets labels.last_withdrawn_period (MAX per label)
#
# Per user spec 2026-06-29: amount/dates are NOT important; we use period_end
# to determine the "everything up to here is already withdrawn" cutoff, then
# the modern FIFO logic handles future withdraws correctly.

@migrate_r.post("/withdraws-legacy-period")
async def bulk_import_withdraws_legacy_period(
    file: UploadFile = File(...),
    dry_run: bool = Form(True),
    create_history_docs: bool = Form(True),
    flip_royalty_lines: bool = Form(True),
    adjust_balances: bool = Form(True),
    user: dict = Depends(require_admin),
):
    """Queue legacy-withdraw analysis/commit and return without waiting.

    Both preview and commit run in background because preview itself aggregates
    millions of royalty rows and can exceed the ingress timeout.
    """
    _require_migrate_role(user)
    content = await file.read()
    rows = _read_csv_bytes(content)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV kosong")
    if not any("period_end" in row for row in rows[:5]):
        raise HTTPException(status_code=400, detail="Kolom 'period_end' tidak ditemukan di CSV")

    job_id = new_id()
    submitted_at = now_iso()
    await db_bg.migrate_jobs.insert_one({
        "id": job_id,
        "kind": "withdraws_legacy_period",
        "status": "queued",
        "dry_run": dry_run,
        "submitted_by": user["id"],
        "submitted_at": submitted_at,
        "updated_at": submitted_at,
        "progress_phase": "queued",
        "progress_labels_done": 0,
        "progress_labels_total": 0,
        "options": {
            "create_history_docs": create_history_docs,
            "flip_royalty_lines": flip_royalty_lines,
            "adjust_balances": adjust_balances,
        },
    })
    import asyncio
    asyncio.create_task(_run_legacy_withdraw_import_job(
        job_id=job_id,
        content=content,
        dry_run=dry_run,
        create_history_docs=create_history_docs,
        flip_royalty_lines=flip_royalty_lines,
        adjust_balances=adjust_balances,
        user=user,
    ))
    return {
        "job_id": job_id,
        "status": "queued",
        "dry_run": dry_run,
        "commit": {"applied": False, "queued": not dry_run, "job_id": job_id},
    }


async def _analyze_legacy_withdraw_import(
    *,
    job_id: str,
    content: bytes,
    dry_run: bool,
    create_history_docs: bool,
    flip_royalty_lines: bool,
    adjust_balances: bool,
    user: dict,
):
    """Build the preview and optionally queue the write phase.

    Per-row effect (when not dry_run):
      1. For each unique `nama_label` in the CSV:
         - Match against current `labels.label_name` (fuzzy: lower + strip
           punctuation/PT prefix).
         - Compute MAX(period_end) across all this label's CSV rows.
         - Update `labels.last_withdrawn_period = MAX(period_end)` only if
           the new value is later than the current one (idempotent).
      2. (if flip_royalty_lines) For every label with last_withdrawn_period
         set, mark ALL `royalty_lines` with period <= last_withdrawn_period
         AND status in ('pending','available') → status='withdrawn'.
      3. (if adjust_balances) Decrement labels.balance_pending_idr +
         balance_available_idr by the sum of the flipped lines.
      4. (if create_history_docs) Insert one `withdraw_requests` doc per CSV
         row with `legacy_import=true`, `status='paid'`, `period_start`,
         `period_end`, and (when present) amount in EUR + exchange_rate.
         Deduped by (label_id, legacy_trx_id).

    Returns a detailed dry-run report so admin can review BEFORE committing.
    """
    _require_migrate_role(user)
    rows = _read_csv_bytes(content)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV kosong")

    # Validate at least one required column is present
    if not any("period_end" in r for r in rows[:5]):
        raise HTTPException(status_code=400, detail="Kolom 'period_end' tidak ditemukan di CSV")

    # ---- Build label name index ----
    labels_by_norm: Dict[str, dict] = {}
    label_id_to_doc: Dict[str, dict] = {}
    async for lab in db_bg.labels.find({}, {"_id": 0, "id": 1, "label_name": 1, "last_withdrawn_period": 1, "balance_available_idr": 1, "balance_pending_idr": 1, "royalty_percentage_default": 1}):
        norm = _normalize_label_name(lab.get("label_name"))
        if norm:
            labels_by_norm.setdefault(norm, lab)  # keep first match on conflict
        label_id_to_doc[lab["id"]] = lab

    # ---- Group CSV rows per (normalized) label name ----
    per_label_csv: Dict[str, Dict[str, Any]] = {}
    unmatched_names: Dict[str, int] = {}  # raw name → row count
    parse_errors: List[Dict[str, Any]] = []

    def _is_valid_period(p: str) -> bool:
        return isinstance(p, str) and len(p) == 7 and p[4] == "-" and p[:4].isdigit() and p[5:7].isdigit()

    for i, r in enumerate(rows, start=2):
        raw_name = (r.get("nama_label") or r.get("label_name") or "").strip()
        p_end = (r.get("period_end") or "").strip()
        p_start = (r.get("period_start") or "").strip() or None
        trx_id = (r.get("trx_id") or "").strip() or None
        amount_eur = (r.get("amount") or "").strip()
        rate = (r.get("exchange_rate") or "").strip()
        if not raw_name or not p_end:
            parse_errors.append({"row": i, "reason": "nama_label / period_end kosong", "raw_name": raw_name, "period_end": p_end})
            continue
        if not _is_valid_period(p_end):
            parse_errors.append({"row": i, "reason": f"period_end format invalid (harus YYYY-MM): '{p_end}'", "raw_name": raw_name})
            continue
        norm = _normalize_label_name(raw_name)
        lab = labels_by_norm.get(norm)
        if not lab:
            unmatched_names[raw_name] = unmatched_names.get(raw_name, 0) + 1
            continue
        bucket = per_label_csv.setdefault(lab["id"], {
            "label_id": lab["id"],
            "label_name": lab["label_name"],
            "csv_raw_names": set(),
            "max_period_end": None,
            "min_period_start": None,
            "row_count": 0,
            "history_rows": [],
        })
        bucket["csv_raw_names"].add(raw_name)
        bucket["row_count"] += 1
        if bucket["max_period_end"] is None or p_end > bucket["max_period_end"]:
            bucket["max_period_end"] = p_end
        if p_start and _is_valid_period(p_start):
            if bucket["min_period_start"] is None or p_start < bucket["min_period_start"]:
                bucket["min_period_start"] = p_start
        if create_history_docs:
            try:
                amt_eur_f = float(amount_eur) if amount_eur else 0.0
            except ValueError:
                amt_eur_f = 0.0
            try:
                rate_f = float(rate) if rate else 0.0
            except ValueError:
                rate_f = 0.0
            bucket["history_rows"].append({
                "trx_id": trx_id,
                "period_start": p_start,
                "period_end": p_end,
                "amount_eur": round(amt_eur_f, 4),
                "exchange_rate": rate_f or None,
                "amount_idr": int(amt_eur_f * rate_f) if rate_f else 0,
                "request_date": (r.get("request_date") or "").strip() or None,
                "payment_date": (r.get("payment_date") or "").strip() or None,
                "row": i,
            })

    # ---- Compute what we would write ----
    label_summaries: List[Dict[str, Any]] = []
    total_labels_updated = 0
    total_lines_to_flip = 0
    total_history_to_insert = 0
    total_balance_pending_adj = 0
    total_balance_available_adj = 0
    active_withdraw_label_ids = set(await db_bg.withdraw_requests.distinct("label_id", {
        "status": {"$in": ["requested", "approved"]},
        "legacy_import": {"$ne": True},
    }))

    for label_id, bucket in per_label_csv.items():
        lab = label_id_to_doc[label_id]
        old_period = lab.get("last_withdrawn_period")
        new_period = bucket["max_period_end"]
        # idempotency — only advance forward
        will_update_period = (not old_period) or (new_period > old_period)

        # period_end is the final BULAN LAPORAN already settled in the old
        # system. Include draft rows too, so old-period CSVs uploaded before
        # publish can never become withdrawable later.
        effective_cutoff = max(filter(None, [old_period, new_period]))
        line_filter = {
            "label_id": label_id,
            "status": {"$in": ["draft", "pending", "available"]},
            "legacy_settled": {"$ne": True},
            "period": {"$lte": effective_cutoff},
        }
        lines_count = await db_bg.royalty_lines.count_documents(line_filter)

        # Sum the amounts so we can adjust balances correctly
        pending_sum = 0
        available_sum = 0
        if adjust_balances and lines_count > 0:
            pipe = [
                {"$match": line_filter},
                {"$group": {"_id": "$status", "total_idr": {"$sum": "$label_idr"}}},
            ]
            async for r in db_bg.royalty_lines.aggregate(pipe, allowDiskUse=True):
                if r["_id"] == "pending":
                    pending_sum = int(r["total_idr"] or 0)
                elif r["_id"] == "available":
                    available_sum = int(r["total_idr"] or 0)

        label_summaries.append({
            "label_id": label_id,
            "label_name": bucket["label_name"],
            "csv_names": sorted(bucket["csv_raw_names"]),
            "csv_row_count": bucket["row_count"],
            "old_last_withdrawn_period": old_period,
            "new_last_withdrawn_period": new_period if will_update_period else old_period,
            "period_will_advance": will_update_period,
            "period_range_in_csv": f"{bucket['min_period_start'] or '?'} – {bucket['max_period_end']}",
            "royalty_lines_to_flip": lines_count,
            "pending_to_subtract_idr": pending_sum,
            "available_to_subtract_idr": available_sum,
            "history_docs_to_insert": len(bucket["history_rows"]),
            "blocked_by_active_withdraw": label_id in active_withdraw_label_ids,
        })
        if will_update_period:
            total_labels_updated += 1
        total_lines_to_flip += lines_count
        total_history_to_insert += len(bucket["history_rows"])
        total_balance_pending_adj += pending_sum
        total_balance_available_adj += available_sum

    label_summaries.sort(key=lambda s: s["label_name"].lower())

    # ---- Apply if not dry-run (Phase 26: commit is now async to avoid the
    # 120s ingress timeout on production datasets of 3M+ royalty_lines) ----
    commit_meta: Dict[str, Any] = {"applied": False}
    if not dry_run and per_label_csv:
        blocked_labels = [
            bucket["label_name"] for label_id, bucket in per_label_csv.items()
            if label_id in active_withdraw_label_ids
        ]
        if blocked_labels:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Sinkronisasi ditahan: {len(blocked_labels)} label memiliki withdraw aktif. "
                    "Selesaikan atau tolak request tersebut terlebih dahulu."
                ),
            )
        # Reuse the request job created by the endpoint so the frontend only
        # needs to poll one id from analysis through commit completion.
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "processing",
                "progress_phase": "committing",
                "updated_at": now_iso(),
                "progress_labels_done": 0,
                "progress_labels_total": len(per_label_csv),
                "options": {
                "create_history_docs": create_history_docs,
                "flip_royalty_lines": flip_royalty_lines,
                "adjust_balances": adjust_balances,
                },
                "totals_preview": {
                    "labels_period_will_advance": total_labels_updated,
                    "royalty_lines_to_flip": total_lines_to_flip,
                    "history_docs_to_insert": total_history_to_insert if create_history_docs else 0,
                    "balance_pending_to_subtract": total_balance_pending_adj,
                    "balance_available_to_subtract": total_balance_available_adj,
                },
            }},
        )
        import asyncio
        asyncio.create_task(_commit_legacy_period_bg(
            job_id=job_id,
            per_label_csv=per_label_csv,
            label_id_to_doc=label_id_to_doc,
            create_history_docs=create_history_docs,
            flip_royalty_lines=flip_royalty_lines,
            adjust_balances=adjust_balances,
            user_id=user["id"],
        ))
        commit_meta = {"applied": False, "queued": True, "job_id": job_id}

    # Sort unmatched alphabetically for easier review
    unmatched_sorted = [
        {"name": k, "row_count": v} for k, v in sorted(unmatched_names.items(), key=lambda kv: kv[0].lower())
    ]

    return {
        "dry_run": dry_run,
        "job_id": job_id,
        "total_csv_rows": len(rows),
        "parse_errors": parse_errors[:200],
        "parse_error_count": len(parse_errors),
        "matched_labels": len(per_label_csv),
        "unmatched_label_count": len(unmatched_sorted),
        "unmatched_label_names": unmatched_sorted[:100],  # cap response
        "totals_preview": {
            "labels_period_will_advance": total_labels_updated,
            "royalty_lines_to_flip": total_lines_to_flip,
            "history_docs_to_insert": total_history_to_insert if create_history_docs else 0,
            "balance_pending_to_subtract": total_balance_pending_adj,
            "balance_available_to_subtract": total_balance_available_adj,
        },
        "label_summaries": label_summaries[:1000],
        "commit": commit_meta,
        "options": {
            "create_history_docs": create_history_docs,
            "flip_royalty_lines": flip_royalty_lines,
            "adjust_balances": adjust_balances,
        },
    }


async def _run_legacy_withdraw_import_job(
    *,
    job_id: str,
    content: bytes,
    dry_run: bool,
    create_history_docs: bool,
    flip_royalty_lines: bool,
    adjust_balances: bool,
    user: dict,
):
    """Background wrapper for the expensive preview and optional commit."""
    try:
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "processing", "progress_phase": "analyzing", "updated_at": now_iso()}},
        )
        result = await _analyze_legacy_withdraw_import(
            job_id=job_id,
            content=content,
            dry_run=dry_run,
            create_history_docs=create_history_docs,
            flip_royalty_lines=flip_royalty_lines,
            adjust_balances=adjust_balances,
            user=user,
        )
        commit_queued = bool(result.get("commit", {}).get("queued"))
        if commit_queued:
            await db_bg.migrate_jobs.update_one(
                {"id": job_id},
                {"$set": {"preview_result": result, "updated_at": now_iso()}},
            )
        else:
            await db_bg.migrate_jobs.update_one(
                {"id": job_id},
                {"$set": {
                    "status": "done",
                    "progress_phase": "done",
                    "result": result,
                    "finished_at": now_iso(),
                    "updated_at": now_iso(),
                }},
            )
    except Exception as exc:
        logger.exception("[WITHDRAW IMPORT BG] job %s failed: %s", job_id, exc)
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "error",
                "progress_phase": "error",
                "error_message": f"{type(exc).__name__}: {str(exc)[:400]}",
                "finished_at": now_iso(),
                "updated_at": now_iso(),
            }},
        )


async def _commit_legacy_period_bg(
    *,
    job_id: str,
    per_label_csv: Dict[str, Dict[str, Any]],
    label_id_to_doc: Dict[str, Dict[str, Any]],
    create_history_docs: bool,
    flip_royalty_lines: bool,
    adjust_balances: bool,
    user_id: str,
):
    """Phase 26 — Commit the Phase 22 withdraw-FIFO migration in background.

    Identical writes to the synchronous version, but writes progress to the
    `migrate_jobs` doc so the admin UI can poll for status without hitting
    the 120s ingress timeout.
    """
    try:
        applied_period_updates = 0
        applied_lines_flipped = 0
        applied_history_inserted = 0
        applied_balance_pending = 0
        applied_balance_available = 0
        applied_recalculated_lines = 0
        applied_recalculation_pending_delta = 0
        applied_recalculation_available_delta = 0
        labels_done = 0
        labels_total = len(per_label_csv)

        for label_id, bucket in per_label_csv.items():
            lab = label_id_to_doc[label_id]
            old_period = lab.get("last_withdrawn_period")
            new_period = bucket["max_period_end"]
            will_update_period = (not old_period) or (new_period > old_period)
            effective_cutoff = max(filter(None, [old_period, new_period]))

            # 1) Store the synced cutoff. `period_end` is a reporting month,
            # never the calendar month when the withdrawal was requested/paid.
            label_set = {
                "legacy_withdraw_synced_at": now_iso(),
                "legacy_withdraw_period_end": effective_cutoff,
                "updated_at": now_iso(),
            }
            if will_update_period:
                label_set["last_withdrawn_period"] = new_period
                applied_period_updates += 1
            await db_bg.labels.update_one({"id": label_id}, {"$set": label_set})

            # 2) Flip royalty_lines (chunked via db_bg, CSOT-safe)
            if flip_royalty_lines:
                line_filter = {
                    "label_id": label_id,
                    "status": {"$in": ["draft", "pending", "available"]},
                    "legacy_settled": {"$ne": True},
                    "period": {"$lte": effective_cutoff},
                }
                # Compute sums BEFORE the flip so the balance adjust is correct
                pending_sum = 0
                available_sum = 0
                if adjust_balances:
                    pipe = [
                        {"$match": line_filter},
                        {"$group": {"_id": "$status", "total_idr": {"$sum": "$label_idr"}}},
                    ]
                    async for r in db_bg.royalty_lines.aggregate(pipe, allowDiskUse=True):
                        if r["_id"] == "pending":
                            pending_sum = int(r["total_idr"] or 0)
                        elif r["_id"] == "available":
                            available_sum = int(r["total_idr"] or 0)

                CHUNK = 5000
                last_oid = None
                flipped = 0
                while True:
                    q = dict(line_filter)
                    if last_oid is not None:
                        q["_id"] = {"$gt": last_oid}
                    batch = await db_bg.royalty_lines.find(q, {"_id": 1}).sort("_id", 1).limit(CHUNK).to_list(CHUNK)
                    if not batch:
                        break
                    oids = [d["_id"] for d in batch]
                    last_oid = oids[-1]
                    await db_bg.royalty_lines.update_many({"_id": {"$in": oids}}, {"$set": {
                        "status": "withdrawn",
                        "legacy_settled": True,
                        "legacy_settled_period_end": effective_cutoff,
                        "legacy_settled_at": now_iso(),
                    }})
                    flipped += len(oids)
                applied_lines_flipped += flipped

                # 3) Adjust balances by the pre-flip sums
                if adjust_balances and (pending_sum or available_sum):
                    await db_bg.labels.update_one(
                        {"id": label_id},
                        {"$inc": {
                            "balance_pending_idr": -pending_sum,
                            "balance_available_idr": -available_sum,
                        }, "$set": {"updated_at": now_iso()}},
                    )
                    applied_balance_pending += pending_sum
                    applied_balance_available += available_sum

            # 4) Recalculate ONLY the royalty that remains unsettled after the
            # legacy cutoff. This removes the old 5% fee and applies the label's
            # current percentage without requiring any CSV re-upload.
            if adjust_balances:
                recalc = await recalculate_label_unwithdrawn(
                    label_id=label_id,
                    percentage=float(lab.get("royalty_percentage_default", 60) or 60),
                )
                applied_recalculated_lines += int(recalc.get("lines_recalculated") or 0)
                applied_recalculation_pending_delta += int(recalc.get("pending_delta_idr") or 0)
                applied_recalculation_available_delta += int(recalc.get("available_delta_idr") or 0)

            # 5) Insert admin-only history docs (deduped by legacy_trx_id).
            # Phase 31.1 — nominal riwayat TIDAK memakai angka CSV. Dihitung
            # otomatis dari royalty_lines web: sum(label_idr) per segmen bulan
            # laporan. Baris di-sort by period_end; segmen row N = periode
            # (period_end row N-1, period_end row N].
            if create_history_docs:
                sorted_rows = sorted(bucket["history_rows"], key=lambda h: h.get("period_end") or "")
                prev_end = None
                for hr in sorted_rows:
                    seg_filter: Dict[str, Any] = {
                        "label_id": label_id,
                        "period": {"$lte": hr.get("period_end")},
                    }
                    if prev_end:
                        seg_filter["period"]["$gt"] = prev_end
                    seg_amount = 0
                    async for r in db_bg.royalty_lines.aggregate([
                        {"$match": seg_filter},
                        {"$group": {"_id": None, "total_idr": {"$sum": "$label_idr"}}},
                    ], allowDiskUse=True):
                        seg_amount = int(r["total_idr"] or 0)
                    seg_start = prev_end
                    prev_end = hr.get("period_end")

                    trx_id = hr.get("trx_id")
                    if trx_id:
                        exists = await db_bg.withdraw_requests.find_one(
                            {"label_id": label_id, "legacy_trx_id": trx_id},
                            {"_id": 0, "id": 1},
                        )
                        if exists:
                            continue
                    await db_bg.withdraw_requests.insert_one({
                        "id": new_id(),
                        "label_id": label_id,
                        "status": "paid",
                        "amount_idr": seg_amount,
                        "amount_eur_legacy": hr.get("amount_eur"),
                        "exchange_rate_legacy": hr.get("exchange_rate"),
                        "payment_method": hr.get("payment_method"),
                        "payment_reference": hr.get("trx_id"),
                        "admin_note": "Legacy import dari music_withdrawals.csv",
                        "period_from": hr.get("period_start") or seg_start,
                        "period_to": hr.get("period_end"),
                        "request_date": hr.get("request_date"),
                        "paid_date": hr.get("payment_date"),
                        "lines_count": 0,
                        "legacy_import": True,
                        "legacy_trx_id": hr.get("trx_id"),
                        "created_at": now_iso(),
                        "updated_at": now_iso(),
                    })
                    applied_history_inserted += 1

            # Progress write — every 10 labels (or when done) so admin sees movement
            labels_done += 1
            if labels_done % 10 == 0 or labels_done == labels_total:
                await db_bg.migrate_jobs.update_one(
                    {"id": job_id},
                    {"$set": {
                        "progress_labels_done": labels_done,
                        "progress_lines_flipped": applied_lines_flipped,
                        "progress_history_inserted": applied_history_inserted,
                        "updated_at": now_iso(),
                    }},
                )

        await log_activity(
            user_id, "migrate_legacy_withdraws_period", "migrate", None,
            after={
                "job_id": job_id,
                "labels_updated": applied_period_updates,
                "lines_flipped": applied_lines_flipped,
                "history_inserted": applied_history_inserted,
                "unwithdrawn_lines_recalculated": applied_recalculated_lines,
            },
        )
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "done",
                "finished_at": now_iso(),
                "updated_at": now_iso(),
                "progress_labels_done": labels_total,
                "result": {
                    "applied": True,
                    "labels_period_updated": applied_period_updates,
                    "royalty_lines_flipped": applied_lines_flipped,
                    "history_docs_inserted": applied_history_inserted,
                    "balance_pending_subtracted": applied_balance_pending,
                    "balance_available_subtracted": applied_balance_available,
                    "unwithdrawn_lines_recalculated": applied_recalculated_lines,
                    "recalculation_pending_delta": applied_recalculation_pending_delta,
                    "recalculation_available_delta": applied_recalculation_available_delta,
                },
            }},
        )
        await trigger_royalty_caches()
    except Exception as e:
        logger.exception("[WITHDRAW FIFO BG] job %s failed: %s", job_id, e)
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "error",
                "error_message": f"{type(e).__name__}: {str(e)[:400]}",
                "finished_at": now_iso(),
                "updated_at": now_iso(),
            }},
        )



# ─────────────────────────────────────────────────────────────────────────────
# Phase 23.2 — Backfill `royalty_lines.period` from `row_period`
#
# Background: prior to Phase 23.1 the CSV `Bulan Laporan` value was overridden
# by the form's `period` input for every row. That broke per-month grouping for
# Artist/Release/Label/Analytics views — yearly CSVs (2020-2024) ended up with
# all 12 months collapsed onto a single form-period.
#
# Lucky: each `royalty_lines` doc ALSO stores `row_period` (the raw CSV column
# value) untouched. This backfill flips `period = row_period` for every row
# where the two differ, then recomputes `royalty_imports.period_breakdown /
# period_start / period_end / is_multi_period / period` per affected import.
# ─────────────────────────────────────────────────────────────────────────────


async def _recompute_import_period_metadata(import_id: str) -> Dict[str, Any]:
    """Recompute period_breakdown + derived fields on a royalty_imports doc
    after its underlying royalty_lines have had their `period` field rewritten."""
    pipeline = [
        {"$match": {"import_id": import_id}},
        {"$group": {"_id": "$period", "n": {"$sum": 1}}},
    ]
    counts: Dict[str, int] = {}
    async for r in db_bg.royalty_lines.aggregate(pipeline, allowDiskUse=True):
        if r["_id"]:
            counts[r["_id"]] = int(r["n"])

    sorted_p = sorted(counts.keys())
    is_multi = len(sorted_p) > 1
    update = {
        "period_breakdown": counts,
        "period_start": sorted_p[0] if sorted_p else None,
        "period_end": sorted_p[-1] if sorted_p else None,
        "is_multi_period": is_multi,
        # Display period: "multi" for multi-period, single key for single-period
        "period": ("multi" if is_multi else (sorted_p[0] if sorted_p else None)),
        "updated_at": now_iso(),
    }
    await db_bg.royalty_imports.update_one({"id": import_id}, {"$set": update})
    return update


@migrate_r.post("/royalty/backfill-period-from-row")
async def backfill_royalty_period_from_row(
    dry_run: bool = Form(True),
    import_id: Optional[str] = Form(None),
    user: dict = Depends(require_super_admin),
):
    """Backfill `royalty_lines.period` from `row_period` for every row where
    the CSV's `Bulan Laporan` value differs from the currently-stored period.

    Mode:
      - dry_run=true  → preview only, no writes
      - dry_run=false → chunked update_many (10k _id batch) via db_bg, then
                        recompute royalty_imports metadata + invalidate caches

    Optional `import_id` scopes the operation to a single import. Omit for a
    full-database backfill.
    """
    # Build the match filter — rows where row_period exists AND differs from period
    base_match: Dict[str, Any] = {
        "row_period": {"$ne": None, "$exists": True},
        "$expr": {"$ne": ["$period", "$row_period"]},
    }
    if import_id:
        base_match["import_id"] = import_id
        # Ensure import exists before doing heavy reads
        imp_check = await db.royalty_imports.find_one({"id": import_id}, {"_id": 0, "id": 1})
        if not imp_check:
            raise HTTPException(status_code=404, detail=f"Import {import_id} tidak ditemukan")

    # Per-import preview aggregation: which imports have how many bad rows,
    # what their current vs new periods look like.
    preview_pipeline = [
        {"$match": base_match},
        {"$group": {
            "_id": "$import_id",
            "rows_to_fix": {"$sum": 1},
            "old_periods": {"$addToSet": "$period"},
            "new_periods": {"$addToSet": "$row_period"},
            "sample_pairs": {"$push": {"_id_str": "$id", "old": "$period", "new": "$row_period"}},
        }},
        {"$project": {
            "_id": 1,
            "rows_to_fix": 1,
            "old_periods": {"$slice": ["$old_periods", 20]},
            "new_periods": {"$slice": ["$new_periods", 20]},
        }},
        {"$sort": {"rows_to_fix": -1}},
    ]
    affected: List[Dict[str, Any]] = []
    total_rows_to_fix = 0
    async for row in db_bg.royalty_lines.aggregate(preview_pipeline, allowDiskUse=True):
        affected.append(row)
        total_rows_to_fix += int(row.get("rows_to_fix", 0))

    # Lookup import metadata for friendly display (filename, status, period_breakdown)
    affected_ids = [r["_id"] for r in affected if r.get("_id")]
    imp_meta_map: Dict[str, Dict[str, Any]] = {}
    if affected_ids:
        async for imp in db.royalty_imports.find(
            {"id": {"$in": affected_ids}},
            {"_id": 0, "id": 1, "filename": 1, "status": 1, "period": 1, "period_breakdown": 1,
             "period_start": 1, "period_end": 1, "is_multi_period": 1, "total_lines": 1},
        ):
            imp_meta_map[imp["id"]] = imp

    summary = []
    for row in affected:
        imp_id = row["_id"]
        meta = imp_meta_map.get(imp_id, {})
        summary.append({
            "import_id": imp_id,
            "filename": meta.get("filename"),
            "status": meta.get("status"),
            "total_lines": meta.get("total_lines"),
            "rows_to_fix": row["rows_to_fix"],
            "current_period_label": meta.get("period"),
            "current_period_breakdown": meta.get("period_breakdown") or {},
            "old_periods_in_lines": sorted(row.get("old_periods", [])),
            "new_periods_will_be": sorted(row.get("new_periods", [])),
        })

    response: Dict[str, Any] = {
        "dry_run": dry_run,
        "import_id_filter": import_id,
        "total_rows_to_fix": total_rows_to_fix,
        "imports_affected": len(summary),
        "summary": summary[:200],  # cap for response payload
    }

    if dry_run or total_rows_to_fix == 0:
        return response

    # ─── COMMIT PHASE ───────────────────────────────────────────────────────
    # Chunked _id-paginated update_many. We can't use a single update_many on
    # a million-row collection because Atlas server-side `maxTimeMS` kills it.
    # The pipeline syntax `[{$set: {period: "$row_period"}}]` does field-to-field
    # copy without round-tripping each value to Python.
    CHUNK = 10_000
    total_updated = 0
    seen_ids: set[str] = set()  # safety against infinite loop (shouldn't happen — filter excludes fixed rows)
    while True:
        batch = await db_bg.royalty_lines.find(
            base_match, {"_id": 1},
        ).limit(CHUNK).to_list(CHUNK)
        if not batch:
            break
        oids = [d["_id"] for d in batch]
        # Loop guard: if we keep seeing the same _ids without actually flipping
        # them, abort to avoid an infinite loop (would only happen if the
        # update silently fails on the server).
        new_ids = [str(o) for o in oids if str(o) not in seen_ids]
        if not new_ids:
            logger.warning("[BACKFILL PERIOD] no new ids in batch, aborting loop to be safe")
            break
        seen_ids.update(new_ids)
        res = await db_bg.royalty_lines.update_many(
            {"_id": {"$in": oids}},
            [{"$set": {"period": "$row_period", "updated_at": now_iso()}}],
        )
        total_updated += res.modified_count

    # Recompute import-level metadata for every affected import
    recomputed: List[Dict[str, Any]] = []
    for imp_id in affected_ids:
        try:
            new_meta = await _recompute_import_period_metadata(imp_id)
            recomputed.append({
                "import_id": imp_id,
                "filename": imp_meta_map.get(imp_id, {}).get("filename"),
                "new_period_breakdown": new_meta["period_breakdown"],
                "new_period_start": new_meta["period_start"],
                "new_period_end": new_meta["period_end"],
                "is_multi_period": new_meta["is_multi_period"],
                "display_period": new_meta["period"],
            })
        except Exception as e:
            logger.exception("[BACKFILL PERIOD] recompute import %s failed: %s", imp_id, e)
            recomputed.append({"import_id": imp_id, "error": str(e)[:200]})

    # Invalidate metrics + analytics caches in the background so charts refresh
    import asyncio as _aio
    try:
        schedule_dashboard_recompute()
    except Exception:
        pass
    try:
        from routes.admin_analytics import schedule_monthly_analytics_recompute
        _aio.create_task(schedule_monthly_analytics_recompute(reason="migration_complete"))
    except Exception:
        pass

    await log_activity(
        user["id"], "backfill_royalty_period_from_row", "royalty", import_id or "all",
        after={
            "total_rows_updated": total_updated,
            "imports_affected": len(affected_ids),
            "import_id_filter": import_id,
        },
    )

    response.update({
        "commit": {
            "applied": True,
            "rows_updated": total_updated,
            "imports_recomputed": len(recomputed),
        },
        "recomputed_imports": recomputed[:200],
    })
    return response



# ─────────────────────────────────────────────────────────────────────────────
# Phase 26 — Materialize artists from royalty_lines
#
# Background: CSV ingestion auto-creates labels/releases/tracks but DOES NOT
# create artist documents (royalty.py line 626 hard-codes artist_id=None on
# auto-created tracks). After uploading yearly CSVs, the Artist Management
# page shows "Belum ada artist" because `db.artists` is empty.
#
# This tool scans `royalty_lines` for unique (artist_name_raw, label_id)
# combos, upserts into `artists`, then backfills `royalty_lines.artist_id`
# and `tracks.artist_id` via bulk_write. Idempotent — re-running only
# touches new (artist_name, label) combos that haven't been materialized yet.
# ─────────────────────────────────────────────────────────────────────────────

from bson import ObjectId  # type: ignore  # noqa: F401  (kept for potential future use)
import re


def _slug_artist(name: str) -> str:
    """Stable slug per artist name — used as dedupe key inside a single
    label. Strips whitespace + non-alphanumerics + lowercase."""
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower()).strip()


@migrate_r.post("/materialize-artists")
async def materialize_artists_from_royalty_lines(
    dry_run: bool = Form(True),
    limit_combos: int = Form(0),  # 0 = no limit
    user: dict = Depends(require_super_admin),
):
    """Phase 27 — async job pattern. Returns HTTP 200 immediately with
    `job_id`. The heavy aggregation + bulk upserts run via
    `_materialize_artists_bg`. Poll `GET /api/admin/migrate/jobs/{job_id}`
    for status + result.

    Why async? The dry-run alone aggregates royalty_lines by
    (label_id, artist_name_raw) which scans 3M+ rows on production and
    routinely exceeds the 120s ingress timeout.
    """
    job_id = new_id()
    await db.migrate_jobs.insert_one({
        "id": job_id,
        "kind": "materialize_artists",
        "status": "queued",
        "submitted_by": user["id"],
        "submitted_at": now_iso(),
        "updated_at": now_iso(),
        "options": {"dry_run": dry_run, "limit_combos": int(limit_combos or 0)},
    })
    import asyncio as _aio
    _aio.create_task(_materialize_artists_bg(
        job_id=job_id, dry_run=dry_run, limit_combos=int(limit_combos or 0),
        user_id=user["id"],
    ))
    return {"ok": True, "job_id": job_id, "status": "queued", "kind": "materialize_artists"}


async def _materialize_artists_bg(
    *, job_id: str, dry_run: bool, limit_combos: int, user_id: str,
):
    """Phase 27 — background runner for Materialize Artists.

    Identical logic to the previous sync version but persists result to
    `migrate_jobs` instead of returning it. Updates progress_phase as it
    walks through the stages so admin UI can show meaningful progress.
    """
    try:
        await db_bg.migrate_jobs.update_one(
            {"id": job_id}, {"$set": {"status": "processing", "progress_phase": "aggregating", "updated_at": now_iso()}},
        )

        pipeline: List[Dict[str, Any]] = [
            {"$match": {
                "label_id": {"$ne": None},
                "artist_name_raw": {"$nin": [None, "", "Unknown", "unknown"]},
                "match_status": {"$in": ["matched", "manually_matched"]},
            }},
            {"$group": {
                "_id": {"label_id": "$label_id", "artist_name": "$artist_name_raw"},
                "lines": {"$sum": 1},
                "total_revenue_eur": {"$sum": "$revenue_eur"},
                "total_label_idr": {"$sum": "$label_idr"},
                "first_period": {"$min": "$period"},
                "last_period": {"$max": "$period"},
            }},
            {"$sort": {"total_label_idr": -1}},
        ]
        if limit_combos and limit_combos > 0:
            pipeline.append({"$limit": int(limit_combos)})

        combos: List[Dict[str, Any]] = []
        async for r in db_bg.royalty_lines.aggregate(pipeline, allowDiskUse=True):
            combos.append({
                "label_id": r["_id"]["label_id"],
                "artist_name": r["_id"]["artist_name"],
                "lines": int(r.get("lines") or 0),
                "total_revenue_eur": round(float(r.get("total_revenue_eur") or 0), 2),
                "total_label_idr": int(r.get("total_label_idr") or 0),
                "first_period": r.get("first_period"),
                "last_period": r.get("last_period"),
            })

        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {"progress_phase": "diffing", "progress_combos_found": len(combos), "updated_at": now_iso()}},
        )

        existing_by_key: Dict[str, str] = {}
        async for art in db_bg.artists.find(
            {}, {"_id": 0, "id": 1, "label_id": 1, "artist_name": 1, "name_slug": 1},
        ):
            slug = art.get("name_slug") or _slug_artist(art.get("artist_name") or "")
            existing_by_key[f"{art.get('label_id')}|{slug}"] = art["id"]

        new_artists: List[Dict[str, Any]] = []
        matched_artists: List[tuple] = []
        seen_keys: set = set()
        for combo in combos:
            slug = _slug_artist(combo["artist_name"])
            if not slug:
                continue
            key = f"{combo['label_id']}|{slug}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
            if key in existing_by_key:
                matched_artists.append((combo, existing_by_key[key]))
            else:
                new_artists.append({
                    "id": new_id(),
                    "label_id": combo["label_id"],
                    "artist_name": combo["artist_name"],
                    "name_slug": slug,
                    "status": "active",
                    "user_id": None,
                    "imported_legacy": True,
                    "auto_created_from_lines": True,
                    "first_period": combo["first_period"],
                    "last_period": combo["last_period"],
                    "lifetime_lines": combo["lines"],
                    "lifetime_revenue_eur": combo["total_revenue_eur"],
                    "lifetime_label_idr": combo["total_label_idr"],
                    "created_at": now_iso(),
                    "updated_at": now_iso(),
                })

        top_preview = sorted(new_artists, key=lambda a: a["lifetime_label_idr"], reverse=True)[:20]
        result: Dict[str, Any] = {
            "dry_run": dry_run,
            "combos_in_lines": len(combos),
            "artists_already_existed": len(matched_artists),
            "artists_to_create": len(new_artists),
            "top_preview": [
                {"artist_name": a["artist_name"], "label_id": a["label_id"],
                 "lines": a["lifetime_lines"], "revenue_eur": a["lifetime_revenue_eur"],
                 "label_idr": a["lifetime_label_idr"]}
                for a in top_preview
            ],
        }

        if not dry_run and new_artists:
            await db_bg.migrate_jobs.update_one(
                {"id": job_id},
                {"$set": {"progress_phase": "inserting_artists", "progress_total": len(new_artists), "updated_at": now_iso()}},
            )
            BATCH = 1000
            for i in range(0, len(new_artists), BATCH):
                await db_bg.artists.insert_many(new_artists[i:i + BATCH], ordered=False)

        lines_updated = 0
        tracks_updated = 0
        if not dry_run:
            await db_bg.migrate_jobs.update_one(
                {"id": job_id},
                {"$set": {"progress_phase": "backfilling_lines_and_tracks", "updated_at": now_iso()}},
            )
            full_mapping: Dict[tuple, str] = {}
            for a in new_artists:
                full_mapping[(a["label_id"], a["name_slug"])] = a["id"]
            for combo, art_id in matched_artists:
                full_mapping[(combo["label_id"], _slug_artist(combo["artist_name"]))] = art_id

            from pymongo import UpdateMany
            line_ops: List[UpdateMany] = []
            track_ops: List[UpdateMany] = []
            for idx, combo in enumerate(combos):
                slug = _slug_artist(combo["artist_name"])
                if not slug:
                    continue
                art_id = full_mapping.get((combo["label_id"], slug))
                if not art_id:
                    continue
                line_ops.append(UpdateMany(
                    {"label_id": combo["label_id"], "artist_name_raw": combo["artist_name"], "artist_id": None},
                    {"$set": {"artist_id": art_id}},
                ))
                track_ops.append(UpdateMany(
                    {"label_id": combo["label_id"], "artist_name": combo["artist_name"], "artist_id": None},
                    {"$set": {"artist_id": art_id}},
                ))
                if len(line_ops) >= 500:
                    res = await db_bg.royalty_lines.bulk_write(line_ops, ordered=False)
                    lines_updated += res.modified_count
                    line_ops = []
                    await db_bg.migrate_jobs.update_one(
                        {"id": job_id},
                        {"$set": {"progress_lines_updated": lines_updated, "progress_done": idx, "updated_at": now_iso()}},
                    )
                if len(track_ops) >= 500:
                    res = await db_bg.tracks.bulk_write(track_ops, ordered=False)
                    tracks_updated += res.modified_count
                    track_ops = []
            if line_ops:
                res = await db_bg.royalty_lines.bulk_write(line_ops, ordered=False)
                lines_updated += res.modified_count
            if track_ops:
                res = await db_bg.tracks.bulk_write(track_ops, ordered=False)
                tracks_updated += res.modified_count

            result["commit"] = {
                "applied": True,
                "artists_created": len(new_artists),
                "lines_updated": lines_updated,
                "tracks_updated": tracks_updated,
            }
            # Cache refresh
            import asyncio as _aio
            try:
                from routes.admin_analytics import schedule_monthly_analytics_recompute
                _aio.create_task(schedule_monthly_analytics_recompute(reason="backfill_complete"))
            except Exception:
                pass
            await log_activity(
                user_id, "materialize_artists", "artist", "bulk",
                after={"job_id": job_id, "artists_created": len(new_artists),
                       "lines_updated": lines_updated, "tracks_updated": tracks_updated},
            )

        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "done",
                "progress_phase": "done",
                "result": result,
                "finished_at": now_iso(),
                "updated_at": now_iso(),
            }},
        )
    except Exception as e:
        logger.exception("[MATERIALIZE ARTISTS BG] job %s failed: %s", job_id, e)
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "error",
                "error_message": f"{type(e).__name__}: {str(e)[:400]}",
                "finished_at": now_iso(),
                "updated_at": now_iso(),
            }},
        )


@migrate_r.post("/ensure-indexes")
async def ensure_indexes_now(user: dict = Depends(require_super_admin)):
    """Phase 27 — manual trigger for the startup ensure-indexes step.

    Useful when a deploy has been done but the pod may not have run startup
    yet, or after introducing new indexes in code. Idempotent."""
    from .seed import seed_indexes_and_admins
    # Pull out just the index portion by calling the seed function — it's
    # safe to re-run (admin upsert is idempotent, indexes are no-op if existing).
    import time as _t
    t0 = _t.time()
    await seed_indexes_and_admins()
    return {"ok": True, "duration_sec": round(_t.time() - t0, 2)}


# ─────────────────────────────────────────────────────────────────────────────
# Phase 26 — Async Withdraw FIFO migration (background pattern)
#
# The original Phase 22 endpoint times out on 120s ingress when the database
# holds 3M+ royalty_lines. Convert COMMIT mode to background: return a
# `migrate_jobs` document id and let the frontend poll for status.
# Dry-run mode stays synchronous since the user expects an immediate preview.
# ─────────────────────────────────────────────────────────────────────────────


@migrate_r.get("/jobs/{job_id}")
async def get_migrate_job_status(job_id: str, user: dict = Depends(require_admin)):
    """Poll status of a long-running migrate job."""
    job = await db.migrate_jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan")
    return job
