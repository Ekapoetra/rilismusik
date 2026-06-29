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
    if not s:
        return ""
    import re
    out = s.strip().lower()
    out = re.sub(r"^pt[\.\,]?\s+", "", out)  # drop "PT " / "PT, " / "PT. " prefix
    out = re.sub(r"[\.\,\;\:\!\?\(\)\[\]\{\}\"\'`]", " ", out)
    out = re.sub(r"[\-\_]", " ", out)
    out = re.sub(r"\s+", " ", out).strip()
    return out


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
    """Migrate `music_withdrawals.csv` (legacy schema) into the FIFO system.

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
    content = await file.read()
    rows = _read_csv_bytes(content)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV kosong")

    # Validate at least one required column is present
    if not any("period_end" in r for r in rows[:5]):
        raise HTTPException(status_code=400, detail="Kolom 'period_end' tidak ditemukan di CSV")

    # ---- Build label name index ----
    labels_by_norm: Dict[str, dict] = {}
    label_id_to_doc: Dict[str, dict] = {}
    async for lab in db.labels.find({}, {"_id": 0, "id": 1, "label_name": 1, "last_withdrawn_period": 1, "balance_available_idr": 1, "balance_pending_idr": 1}):
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

    for label_id, bucket in per_label_csv.items():
        lab = label_id_to_doc[label_id]
        old_period = lab.get("last_withdrawn_period")
        new_period = bucket["max_period_end"]
        # idempotency — only advance forward
        will_update_period = (not old_period) or (new_period > old_period)

        # Count royalty_lines that would be flipped (only those AFTER current
        # last_withdrawn_period and ≤ new_period that are still pending/available)
        line_filter = {
            "label_id": label_id,
            "status": {"$in": ["pending", "available"]},
            "period": {"$lte": new_period},
        }
        if old_period:
            line_filter["period"]["$gt"] = old_period
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
        })
        if will_update_period:
            total_labels_updated += 1
        total_lines_to_flip += lines_count
        total_history_to_insert += len(bucket["history_rows"])
        total_balance_pending_adj += pending_sum
        total_balance_available_adj += available_sum

    label_summaries.sort(key=lambda s: s["label_name"].lower())

    # ---- Apply if not dry-run ----
    commit_meta: Dict[str, Any] = {"applied": False}
    if not dry_run and per_label_csv:
        applied_period_updates = 0
        applied_lines_flipped = 0
        applied_history_inserted = 0
        applied_balance_pending = 0
        applied_balance_available = 0
        for label_id, bucket in per_label_csv.items():
            lab = label_id_to_doc[label_id]
            old_period = lab.get("last_withdrawn_period")
            new_period = bucket["max_period_end"]
            will_update_period = (not old_period) or (new_period > old_period)

            # 1) Update last_withdrawn_period
            if will_update_period:
                await db.labels.update_one(
                    {"id": label_id},
                    {"$set": {"last_withdrawn_period": new_period, "updated_at": now_iso()}},
                )
                applied_period_updates += 1

            # 2) Flip royalty_lines (chunked via db_bg, CSOT-safe)
            if flip_royalty_lines and will_update_period:
                line_filter = {
                    "label_id": label_id,
                    "status": {"$in": ["pending", "available"]},
                    "period": {"$lte": new_period},
                }
                if old_period:
                    line_filter["period"]["$gt"] = old_period
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
                    await db_bg.royalty_lines.update_many({"_id": {"$in": oids}}, {"$set": {"status": "withdrawn"}})
                    flipped += len(oids)
                applied_lines_flipped += flipped

                # 3) Balance adjustment
                if adjust_balances and (pending_sum > 0 or available_sum > 0):
                    await db.labels.update_one(
                        {"id": label_id},
                        {"$inc": {
                            "balance_pending_idr": -pending_sum,
                            "balance_available_idr": -available_sum,
                        }, "$set": {"updated_at": now_iso()}},
                    )
                    applied_balance_pending += pending_sum
                    applied_balance_available += available_sum

            # 4) Insert history withdraw_requests (deduped by legacy_trx_id)
            if create_history_docs:
                for hr in bucket["history_rows"]:
                    if hr.get("trx_id"):
                        # Skip if we already imported this exact trx_id for this label
                        existing = await db.withdraw_requests.find_one(
                            {"label_id": label_id, "legacy_trx_id": hr["trx_id"]},
                            {"_id": 0, "id": 1},
                        )
                        if existing:
                            continue
                    wd_id = new_id()
                    await db.withdraw_requests.insert_one({
                        "id": wd_id,
                        "label_id": label_id,
                        "amount_idr": hr["amount_idr"],
                        "amount_eur_legacy": hr.get("amount_eur"),
                        "exchange_rate_legacy": hr.get("exchange_rate"),
                        "status": "paid",
                        "request_date": hr.get("request_date") or now_iso(),
                        "approved_date": hr.get("payment_date") or hr.get("request_date") or now_iso(),
                        "paid_date": hr.get("payment_date") or hr.get("request_date") or now_iso(),
                        "approved_by": user["id"],
                        "paid_by": user["id"],
                        "bank_snapshot": None,
                        "payment_proof_url": None,
                        "payment_reference": hr.get("trx_id"),
                        "admin_note": "Legacy import dari music_withdrawals.csv",
                        "period_from": hr.get("period_start"),
                        "period_to": hr.get("period_end"),
                        "lines_count": 0,  # unknown for legacy rows
                        "legacy_import": True,
                        "legacy_trx_id": hr.get("trx_id"),
                        "created_at": now_iso(),
                        "updated_at": now_iso(),
                    })
                    applied_history_inserted += 1

        await log_activity(
            user["id"], "migrate_legacy_withdraws_period", "migrate", None,
            after={
                "labels_updated": applied_period_updates,
                "lines_flipped": applied_lines_flipped,
                "history_inserted": applied_history_inserted,
            },
        )
        commit_meta = {
            "applied": True,
            "labels_period_updated": applied_period_updates,
            "royalty_lines_flipped": applied_lines_flipped,
            "history_docs_inserted": applied_history_inserted,
            "balance_pending_subtracted": applied_balance_pending,
            "balance_available_subtracted": applied_balance_available,
        }

    # Sort unmatched alphabetically for easier review
    unmatched_sorted = [
        {"name": k, "row_count": v} for k, v in sorted(unmatched_names.items(), key=lambda kv: kv[0].lower())
    ]

    return {
        "dry_run": dry_run,
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
