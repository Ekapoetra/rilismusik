"""Royalty CSV import & label/artist reports router."""
from fastapi import APIRouter, HTTPException, Request, Response, Depends, UploadFile, File, Form, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta, date
import os
import csv
import io
import shutil
import secrets

from .deps import (
    db, db_bg, logger, UPLOAD_DIR,
    get_current_user, require_label, require_artist, require_admin, require_super_admin,
    public_user, get_label_by_user, redact_label_for_self, LABEL_HIDDEN_FIELDS,
    log_activity, notify, notify_many, admin_user_ids, label_user_ids,
    LABEL_ROLE, ARTIST_ROLE, ADMIN_ROLES, SUPER_ADMIN,
)
from models import (
    RegisterLabelIn, LoginIn, ForgotPasswordIn, ResetPasswordIn, VerifyEmailIn,
    LabelProfileUpdate, BankAccountIn,
    ReleaseDraftIn, ReleaseSubmitConfirmation, AdminReleaseAction,
    ArtistIn, ArtistUpdateIn,
    CreateReleasePaymentIn,
    CMSUpdateIn, AdminUserCreateIn, LabelStatusUpdate,
    ExchangeRateIn, RoyaltyImportPublishIn, RoyaltyLineMatchIn,
    WithdrawRequestIn, WithdrawAdminAction,
    TicketCreateIn, TicketCommentIn, TicketAdminUpdateIn,
    ContractCreateIn, ContractExtendIn, ContractTerminateIn,
    BlacklistIn, NotificationMarkIn,
    CreateSubscriptionPaymentIn, CreateWamiOrderIn, AdminWamiUpdateIn,
    now_iso, new_id,
)
from auth_utils import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    set_auth_cookies, clear_auth_cookies, decode_token,
)
from royalty_utils import (
    parse_csv_bytes, detect_columns, parse_amount, normalize_header,
    parse_period_from_value, calculate_line, label_percentage_at,
    strip_sensitive, iter_csv_file,
)
from withdraw_utils import withdraw_window_state, jakarta_now, MIN_WITHDRAW_IDR
import storage_service

# =============================================================================
#                              ROYALTY (ADMIN + LABEL/ARTIST)
# =============================================================================
royalty_r = APIRouter(prefix="/royalty", tags=["royalty"])


def _norm_name(s: Optional[str]) -> str:
    """Fuzzy-match key: lowercase + trim + collapse whitespace.
    Used to match Believe CSV label/artist names that may differ in case or spacing.
    """
    if not s:
        return ""
    return " ".join(s.strip().lower().split())


def _match_line(row: Dict[str, Any], col_idx: Dict[str, Optional[int]], headers: List[str]) -> Dict[str, Any]:
    """Extract raw fields from a CSV row using detected columns."""
    def get(key: str) -> Optional[str]:
        idx = col_idx.get(key)
        if idx is None:
            return None
        # row dict keys are normalized headers
        h = normalize_header(headers[idx]) if idx < len(headers) else None
        return row.get(h) if h else None

    return {
        "isrc": (get("isrc") or "").strip() or None,
        "upc": (get("upc") or "").strip() or None,
        "track_title": (get("track_title") or "").strip() or None,
        "artist_name": (get("artist_name") or "").strip() or None,
        "release_title": (get("release_title") or "").strip() or None,
        "label_name": (get("label_name") or "").strip() or None,
        "platform": (get("platform") or "").strip() or None,
        "country": (get("country") or "").strip() or None,
        "quantity": int(parse_amount(get("quantity") or "0") or 0),
        "revenue_eur": parse_amount(get("revenue_eur") or "0"),
        # Admin-only / sensitive (will be stripped from label/artist responses)
        "gross_revenue_eur": parse_amount(get("gross_revenue_eur") or "0") or None,
        "unit_price_eur": parse_amount(get("unit_price_eur") or "0") or None,
        "mechanical_cost_eur": parse_amount(get("mechanical_cost_eur") or "0") or None,
        "client_share_rate": parse_amount(get("client_share_rate") or "0") or None,
        # Optional metadata
        "sales_type": (get("sales_type") or "").strip() or None,
        "subscription_type": (get("subscription_type") or "").strip() or None,
        "row_period": parse_period_from_value(get("period")),
    }


@royalty_r.post("/admin/imports")
async def admin_upload_royalty_csv(
    period: Optional[str] = Form(None),
    rate_eur_idr: float = Form(...),
    file: UploadFile = File(...),
    note: Optional[str] = Form(None),
    user: dict = Depends(require_admin),
):
    """Upload CSV royalti Believe.

    Untuk file kecil (<5000 baris): proses langsung, kembalikan hasil dengan
    counter matched/unmatched. Untuk file besar (>=5000 baris OR >5 MB): proses
    di background, kembalikan import_doc dengan status='processing' — frontend
    polling endpoint GET /royalty/admin/imports/{id} untuk progress real-time.

    Mendukung file hingga 200 MB (Believe royalty bulanan ~80 MB normal).
    Mendukung .csv dan .csv.gz.

    Period dapat dikosongkan — jika kolom 'Bulan Laporan' (atau period) ada di CSV,
    setiap baris akan menggunakan period-nya sendiri (multi-period import). Jika
    period diberikan, semua baris akan diforce ke period tersebut (single-month).
    """
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    if period:
        try:
            datetime.strptime(period, "%Y-%m")
        except Exception:
            raise HTTPException(status_code=400, detail="Format period harus YYYY-MM")
    if rate_eur_idr <= 0:
        raise HTTPException(status_code=400, detail="Kurs harus > 0")

    # ---- Stream file to disk in chunks (memory-safe for 80+ MB files) ----
    MAX_BYTES = 200 * 1024 * 1024  # 200 MB hard cap
    import_id = new_id()
    fname = file.filename or "upload.csv"
    ext = ".csv.gz" if fname.lower().endswith(".gz") else ".csv"
    target = UPLOAD_DIR / "csv" / f"{import_id}{ext}"
    total_size = 0
    with open(target, "wb") as f:
        while True:
            chunk = await file.read(1 * 1024 * 1024)  # 1 MB chunks
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > MAX_BYTES:
                f.close()
                target.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"File terlalu besar (>{MAX_BYTES // (1024*1024)} MB). Pecah jadi beberapa CSV.",
                )
            f.write(chunk)
    file_url = f"/api/files/csv/{target.name}"

    # ---- Quick header validation by peeking the first row ----
    headers: List[str] = []
    sample_rows: List[Dict[str, Any]] = []
    try:
        for hdrs, row_dict in iter_csv_file(str(target)):
            if row_dict is None:
                headers = hdrs
                continue
            sample_rows.append(row_dict)
            if len(sample_rows) >= 50:
                break
    except Exception as e:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Gagal membaca CSV: {e}")
    if not headers or not sample_rows:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="CSV kosong atau tidak terbaca")

    col_idx = detect_columns(headers)
    if col_idx["revenue_eur"] is None:
        raise HTTPException(status_code=400, detail="Kolom revenue/amount tidak ditemukan di CSV")
    if not period and col_idx.get("period") is None:
        raise HTTPException(
            status_code=400,
            detail="Period tidak diberikan dan kolom 'Bulan Laporan'/period tidak ditemukan di CSV. "
                   "Tambahkan kolom atau isi field period.",
        )

    # ---- Determine sync vs async based on file size ----
    # Files <= 5 MB → process synchronously (preserves existing API behavior
    # for small CSVs and pytest fixtures). Files > 5 MB → background.
    SYNC_THRESHOLD = 5 * 1024 * 1024
    process_async = total_size > SYNC_THRESHOLD

    fee_settings = await db.landing_settings.find_one({"key": "pricing"})
    fee_percent = float((fee_settings or {}).get("value", {}).get("distributor_fee_percent", 5) or 5)

    now = now_iso()
    import_doc = {
        "id": import_id,
        "period": period or "multi",
        "period_start": period,
        "period_end": period,
        "period_breakdown": {},
        "is_multi_period": False,
        "source": "believe",
        "filename": fname,
        "file_url": file_url,
        "file_size_bytes": total_size,
        "exchange_rate_eur_idr": rate_eur_idr,
        "fee_percent": fee_percent,
        "total_lines": 0,
        "processed_lines": 0,
        "progress_pct": 0,
        "matched_lines": 0,
        "unmatched_lines": 0,
        "invalid_period_rows": 0,
        "auto_created_labels": 0,
        "auto_created_releases": 0,
        "auto_created_tracks": 0,
        "total_revenue_eur": 0.0,
        "total_label_idr": 0,
        "status": "processing" if process_async else "pending_review",
        "error_message": None,
        "dana_received_at": None,
        "published_at": None,
        "uploaded_by": user["id"],
        "note": note,
        "started_at": now,
        "finished_at": None,
        "created_at": now,
        "updated_at": now,
    }
    await db.royalty_imports.insert_one(import_doc)

    if process_async:
        # Spawn background processing — return immediately
        import asyncio
        asyncio.create_task(_process_csv_import_bg(
            import_id=import_id,
            file_path=str(target),
            period=period,
            rate_eur_idr=rate_eur_idr,
            fee_percent=fee_percent,
            user_id=user["id"],
        ))
        await log_activity(user["id"], "upload_royalty_csv_async", "royalty", import_id, after={"size_mb": round(total_size / 1024 / 1024, 2)})
        import_doc.pop("_id", None)
        return import_doc

    # Sync path (small files) — process inline and update doc with final stats
    result = await _process_csv_import_inline(
        import_id=import_id,
        file_path=str(target),
        period=period,
        rate_eur_idr=rate_eur_idr,
        fee_percent=fee_percent,
    )
    await log_activity(
        user["id"], "upload_royalty_csv", "royalty", import_id,
        after={
            "period": result.get("period"),
            "matched": result.get("matched_lines"),
            "unmatched": result.get("unmatched_lines"),
            "multi_period": result.get("is_multi_period"),
            "auto_labels": result.get("auto_created_labels"),
            "auto_releases": result.get("auto_created_releases"),
            "auto_tracks": result.get("auto_created_tracks"),
        },
    )
    return result


# ============================================================
# Large-file Direct-to-R2 upload (bypasses ingress body limits)
# ============================================================
from pydantic import BaseModel, Field


class InitiateUploadIn(BaseModel):
    filename: str
    rate_eur_idr: float = Field(..., gt=0)
    period: Optional[str] = None
    note: Optional[str] = None
    file_size_bytes: Optional[int] = None  # client-reported, for capacity hints


@royalty_r.post("/admin/imports/initiate")
async def admin_initiate_large_upload(body: InitiateUploadIn, user: dict = Depends(require_admin)):
    """Step 1 of large-file upload: returns a presigned PUT URL so the browser
    can upload the CSV DIRECTLY to Cloudflare R2 — bypassing the Kubernetes
    ingress body-size limit (~100 MB default). Use for files > 50 MB.

    Flow: client calls this → uploads file with PUT to `presigned_put_url` →
    calls `/admin/imports/{import_id}/finalize` to trigger background processing.
    """
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    if body.period:
        try:
            datetime.strptime(body.period, "%Y-%m")
        except Exception:
            raise HTTPException(status_code=400, detail="Format period harus YYYY-MM")
    if not storage_service.is_configured():
        raise HTTPException(status_code=500, detail="Cloud storage belum dikonfigurasi")

    import_id = new_id()
    fname = body.filename or "upload.csv"
    ext = ".csv.gz" if fname.lower().endswith(".gz") else ".csv"
    r2_key = f"csv/{import_id}{ext}"
    content_type = "application/gzip" if ext == ".csv.gz" else "text/csv"

    # 2h TTL — accommodates very slow uploads on residential connections
    presigned_url = await storage_service.generate_presigned_put_url(
        key=r2_key, content_type=content_type, ttl=7200,
    )

    fee_settings = await db.landing_settings.find_one({"key": "pricing"})
    fee_percent = float((fee_settings or {}).get("value", {}).get("distributor_fee_percent", 5) or 5)

    now = now_iso()
    import_doc = {
        "id": import_id,
        "period": body.period or "multi",
        "period_start": body.period,
        "period_end": body.period,
        "period_breakdown": {},
        "is_multi_period": body.period is None,
        "source": "believe",
        "filename": fname,
        "file_url": f"/api/files/{r2_key}",
        "r2_key": r2_key,
        "file_size_bytes": body.file_size_bytes or 0,
        "exchange_rate_eur_idr": body.rate_eur_idr,
        "fee_percent": fee_percent,
        "total_lines": 0, "processed_lines": 0, "progress_pct": 0,
        "matched_lines": 0, "unmatched_lines": 0, "invalid_period_rows": 0,
        "auto_created_labels": 0, "auto_created_releases": 0, "auto_created_tracks": 0,
        "total_revenue_eur": 0.0, "total_label_idr": 0,
        "status": "awaiting_upload",
        "error_message": None, "dana_received_at": None, "published_at": None,
        "uploaded_by": user["id"], "note": body.note,
        "started_at": None, "finished_at": None,
        "created_at": now, "updated_at": now,
    }
    await db.royalty_imports.insert_one(import_doc)
    return {
        "import_id": import_id,
        "presigned_put_url": presigned_url,
        "r2_key": r2_key,
        "content_type": content_type,
        "expires_in": 7200,
    }


@royalty_r.post("/admin/imports/{import_id}/finalize")
async def admin_finalize_large_upload(import_id: str, user: dict = Depends(require_admin)):
    """Step 2 of large-file upload: called by the frontend after the PUT to
    R2 succeeds. Verifies the object exists, downloads it to a local staging
    file, and kicks off the existing background processor.
    """
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    imp = await db.royalty_imports.find_one({"id": import_id})
    if not imp:
        raise HTTPException(status_code=404, detail="Import tidak ditemukan")
    if imp.get("status") != "awaiting_upload":
        raise HTTPException(status_code=400, detail=f"Status import tidak valid untuk finalize: {imp.get('status')}")
    r2_key = imp.get("r2_key")
    if not r2_key:
        raise HTTPException(status_code=400, detail="Import doc tidak punya r2_key")

    # Verify the file actually landed in R2
    meta = await storage_service.head_object(key=r2_key)
    if not meta:
        raise HTTPException(status_code=400, detail="File belum berhasil di-upload ke R2 — coba lagi")
    file_size = int(meta.get("ContentLength", 0))

    # Stage to local disk so the existing streaming parser can read it
    ext = ".csv.gz" if r2_key.endswith(".gz") else ".csv"
    local_path = UPLOAD_DIR / "csv" / f"{import_id}{ext}"
    local_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        await storage_service.download_to_file(key=r2_key, local_path=str(local_path))
    except Exception as e:
        logger.exception("R2 download failed for %s: %s", import_id, e)
        await db.royalty_imports.update_one(
            {"id": import_id},
            {"$set": {"status": "error", "error_message": f"Gagal download dari R2: {e}", "finished_at": now_iso(), "updated_at": now_iso()}},
        )
        raise HTTPException(status_code=500, detail=f"Gagal download CSV dari R2: {e}")

    # Quick header validation
    headers_list: List[str] = []
    sample_rows: List[Dict[str, Any]] = []
    try:
        for hdrs, row_dict in iter_csv_file(str(local_path)):
            if row_dict is None:
                headers_list = hdrs
                continue
            sample_rows.append(row_dict)
            if len(sample_rows) >= 50:
                break
    except Exception as e:
        await db.royalty_imports.update_one(
            {"id": import_id},
            {"$set": {"status": "error", "error_message": f"Gagal membaca CSV: {e}", "finished_at": now_iso(), "updated_at": now_iso()}},
        )
        raise HTTPException(status_code=400, detail=f"Gagal membaca CSV: {e}")
    if not headers_list or not sample_rows:
        raise HTTPException(status_code=400, detail="CSV kosong atau tidak terbaca")
    col_idx = detect_columns(headers_list)
    if col_idx["revenue_eur"] is None:
        raise HTTPException(status_code=400, detail="Kolom revenue/amount tidak ditemukan di CSV")
    if not imp.get("period_start") and col_idx.get("period") is None:
        raise HTTPException(
            status_code=400,
            detail="Period tidak diberikan dan kolom 'Bulan Laporan'/period tidak ditemukan di CSV.",
        )

    now = now_iso()
    await db.royalty_imports.update_one(
        {"id": import_id},
        {"$set": {"status": "processing", "file_size_bytes": file_size, "started_at": now, "updated_at": now}},
    )
    import asyncio
    asyncio.create_task(_process_csv_import_bg(
        import_id=import_id,
        file_path=str(local_path),
        period=imp.get("period_start"),
        rate_eur_idr=imp["exchange_rate_eur_idr"],
        fee_percent=imp["fee_percent"],
        user_id=user["id"],
    ))
    await log_activity(user["id"], "finalize_royalty_import", "royalty", import_id,
                       after={"size_mb": round(file_size / 1024 / 1024, 2)})
    out = await db.royalty_imports.find_one({"id": import_id}, {"_id": 0})
    return out


# ============================================================
# Streaming CSV processor (shared by sync + async paths)
# ============================================================
async def _process_csv_import_inline(
    *, import_id: str, file_path: str, period: Optional[str],
    rate_eur_idr: float, fee_percent: float,
) -> Dict[str, Any]:
    """Process the CSV file at `file_path` row-by-row in batches.

    For each batch (BATCH_SIZE rows):
      - Auto-create new label / release / track if needed
      - Compute royalty per line
      - Flush new entities + lines to MongoDB
      - Update import_doc with progress

    Returns the final import_doc.
    """
    # Batch size for `insert_many`. 5,000 docs ≈ 4-8 MB per round trip — well
    # within MongoDB's 16 MB BSON limit and 100k bulk-op cap, while reducing
    # round-trip overhead ~2.5× vs the previous 2,000.
    BATCH_SIZE = 5000
    # How often to persist progress to `royalty_imports`. With BATCH_SIZE=5000
    # this means a progress update every 50k rows → ~20 updates for a 1M-row
    # CSV instead of 500, removing a major source of write contention.
    PROGRESS_EVERY_N_FLUSHES = 10

    # ---- Build lookup maps once (memory-friendly: 6K labels + 15K tracks ≈ 4 MB) ----
    # Route through db_bg — production has ~100k tracks already and the find()
    # cursor over the entire `tracks` collection would otherwise hit the 10s
    # CSOT cap on Atlas.
    labels: Dict[str, Dict[str, Any]] = {lab["id"]: lab async for lab in db_bg.labels.find({}, {"_id": 0})}
    labels_by_name = {_norm_name(lab.get("label_name")): lab for lab in labels.values()}
    pct_history: Dict[str, List[Dict[str, Any]]] = {}
    async for h in db_bg.royalty_percentage_history.find({}, {"_id": 0}):
        pct_history.setdefault(h["label_id"], []).append(h)
    all_tracks: Dict[str, Dict[str, Any]] = {}
    async for t in db_bg.tracks.find(
        {"isrc": {"$exists": True, "$ne": None}},
        {"_id": 0, "id": 1, "isrc": 1, "release_id": 1, "label_id": 1, "artist_id": 1, "track_title": 1, "artist_name": 1},
    ):
        if t.get("isrc"):
            all_tracks[(t["isrc"] or "").strip().upper()] = t
    all_releases_by_upc: Dict[str, Dict[str, Any]] = {}
    async for r in db_bg.releases.find(
        {"upc": {"$exists": True, "$ne": None}},
        {"_id": 0, "id": 1, "upc": 1, "label_id": 1, "release_title": 1},
    ):
        if r.get("upc"):
            all_releases_by_upc[(r["upc"] or "").strip().upper()] = r

    # ---- Streaming accumulators ----
    headers: List[str] = []
    col_idx: Optional[Dict[str, Optional[int]]] = None
    line_batch: List[Dict[str, Any]] = []
    new_label_batch: List[Dict[str, Any]] = []
    new_release_batch: List[Dict[str, Any]] = []
    new_track_batch: List[Dict[str, Any]] = []
    period_counts: Dict[str, int] = {}
    counters = {
        "matched": 0, "unmatched": 0, "invalid_period_rows": 0,
        "auto_labels": 0, "auto_releases": 0, "auto_tracks": 0,
        "total_revenue_eur": 0.0, "total_label_idr": 0, "total_lines": 0,
    }
    flush_counter = {"n": 0}
    now = now_iso()

    async def _flush(*, force_progress: bool = False):
        """Bulk-flush accumulated docs. All writes go through db_bg (CSOT-free).
        Progress is persisted every PROGRESS_EVERY_N_FLUSHES flushes OR when
        force_progress=True (used on final flush + auto-create snapshots).
        `ordered=False` lets MongoDB run the inserts in parallel and skip
        duplicate-key errors instead of aborting the whole batch.
        """
        if new_label_batch:
            await db_bg.labels.insert_many(new_label_batch, ordered=False)
            new_label_batch.clear()
        if new_release_batch:
            await db_bg.releases.insert_many(new_release_batch, ordered=False)
            new_release_batch.clear()
        if new_track_batch:
            await db_bg.tracks.insert_many(new_track_batch, ordered=False)
            new_track_batch.clear()
        if line_batch:
            await db_bg.royalty_lines.insert_many(line_batch, ordered=False)
            counters["total_lines"] += len(line_batch)
            line_batch.clear()
        flush_counter["n"] += 1
        # Throttled progress write (every N flushes, OR on demand).
        if force_progress or flush_counter["n"] % PROGRESS_EVERY_N_FLUSHES == 0:
            await db_bg.royalty_imports.update_one(
                {"id": import_id},
                {"$set": {
                    "total_lines": counters["total_lines"],
                    "processed_lines": counters["total_lines"],
                    "matched_lines": counters["matched"],
                    "unmatched_lines": counters["unmatched"],
                    "invalid_period_rows": counters["invalid_period_rows"],
                    "auto_created_labels": counters["auto_labels"],
                    "auto_created_releases": counters["auto_releases"],
                    "auto_created_tracks": counters["auto_tracks"],
                    "total_revenue_eur": round(counters["total_revenue_eur"], 4),
                    "total_label_idr": counters["total_label_idr"],
                    "period_breakdown": period_counts,
                    "updated_at": now_iso(),
                }},
            )

    for hdrs, row_dict in iter_csv_file(file_path):
        if row_dict is None:
            headers = hdrs
            col_idx = detect_columns(headers)
            continue

        raw = _match_line(row_dict, col_idx, headers)
        revenue_eur = raw["revenue_eur"]
        counters["total_revenue_eur"] += revenue_eur

        line_period = period or raw.get("row_period")
        if not line_period:
            counters["invalid_period_rows"] += 1
            continue
        period_counts[line_period] = period_counts.get(line_period, 0) + 1

        track = None
        release = None
        label_id = None
        match_by = None
        if raw["isrc"]:
            t = all_tracks.get(raw["isrc"].upper())
            if t:
                track = t
                label_id = t["label_id"]
                match_by = "isrc"
        if not label_id and raw["upc"]:
            r = all_releases_by_upc.get(raw["upc"].upper())
            if r:
                release = r
                label_id = r["label_id"]
                match_by = "upc"
        if not label_id and raw["label_name"]:
            lab = labels_by_name.get(_norm_name(raw["label_name"]))
            if lab:
                label_id = lab["id"]
                match_by = "label_name"

        # ---- Auto-create placeholders ----
        if not label_id and raw["label_name"]:
            new_label_id = new_id()
            new_label = {
                "id": new_label_id, "user_id": None,
                "label_name": raw["label_name"].strip(),
                "pic_name": None, "email": None, "whatsapp": None,
                "address": None, "city": None, "country": "Indonesia",
                "label_type": "label",
                "royalty_percentage_default": 60.0,
                "payment_type": "pay_per_release",
                "subscription_status": "inactive", "subscription_expires_at": None,
                "contract_status": "active", "account_status": "legacy_unclaimed",
                "bank_verified": False, "blacklisted": False,
                "balance_available_idr": 0, "balance_pending_idr": 0,
                "balance_withdraw_requested_idr": 0,
                "mda_accepted_at": None,
                "legacy_import": True, "auto_created_from": import_id,
                "created_at": now, "updated_at": now,
            }
            new_label_batch.append(new_label)
            labels[new_label_id] = new_label
            labels_by_name[_norm_name(new_label["label_name"])] = new_label
            label_id = new_label_id
            match_by = "auto_created_label"
            counters["auto_labels"] += 1

        if label_id and raw["isrc"] and not track:
            new_release_id = release["id"] if release else new_id()
            if not release:
                new_release = {
                    "id": new_release_id, "label_id": label_id,
                    "release_title": raw.get("release_title") or "Legacy Release",
                    "primary_artist": raw.get("artist_name") or "Unknown",
                    "isrc_release": None, "upc": raw["upc"],
                    "release_type": "single",
                    "release_date": (line_period + "-01") if line_period else "2021-01-01",
                    "status": "live", "cover_url": None,
                    "imported_legacy": True, "auto_created_from": import_id,
                    "created_at": now, "updated_at": now,
                }
                new_release_batch.append(new_release)
                counters["auto_releases"] += 1
                if raw["upc"]:
                    all_releases_by_upc[raw["upc"].upper()] = new_release
            new_track = {
                "id": new_id(), "release_id": new_release_id, "label_id": label_id,
                "artist_id": None,
                "track_title": raw.get("track_title") or "Legacy Track",
                "artist_name": raw.get("artist_name") or "Unknown",
                "isrc": raw["isrc"],
                "duration_sec": None, "composer": None, "audio_url": None,
                "imported_legacy": True, "auto_created_from": import_id,
                "created_at": now, "updated_at": now,
            }
            new_track_batch.append(new_track)
            all_tracks[raw["isrc"].upper()] = new_track
            track = new_track
            counters["auto_tracks"] += 1

        match_status = "matched" if label_id else "unmatched"
        if match_status == "matched":
            counters["matched"] += 1
            label = labels.get(label_id, {})
            default_pct = float(label.get("royalty_percentage_default", 60) or 60)
            history = pct_history.get(label_id, [])
            label_pct = label_percentage_at(history, default_pct, line_period)
            calc = calculate_line(revenue_eur, fee_percent, label_pct, rate_eur_idr)
            counters["total_label_idr"] += calc["label_idr"]
        else:
            counters["unmatched"] += 1
            label_pct = 0.0
            calc = calculate_line(revenue_eur, fee_percent, 0.0, rate_eur_idr)

        line_batch.append({
            "id": new_id(), "import_id": import_id, "period": line_period,
            "isrc": raw["isrc"], "upc": raw["upc"],
            "track_title_raw": raw["track_title"], "artist_name_raw": raw["artist_name"],
            "release_title_raw": raw["release_title"], "label_name_raw": raw["label_name"],
            "platform": raw["platform"], "country": raw["country"],
            "quantity": raw["quantity"], "revenue_eur": revenue_eur,
            "sales_type": raw.get("sales_type"),
            "subscription_type": raw.get("subscription_type"),
            "row_period": raw.get("row_period"),
            "gross_revenue_eur": raw.get("gross_revenue_eur"),
            "unit_price_eur": raw.get("unit_price_eur"),
            "mechanical_cost_eur": raw.get("mechanical_cost_eur"),
            "client_share_rate": raw.get("client_share_rate"),
            "track_id": track["id"] if track else None,
            "release_id": (track or release or {}).get("release_id") or (release or {}).get("id"),
            "label_id": label_id,
            "artist_id": track.get("artist_id") if track else None,
            "match_by": match_by,
            "label_percentage_applied": label_pct,
            "fee_percent_applied": fee_percent,
            "exchange_rate": rate_eur_idr,
            **calc,
            "match_status": match_status,
            "status": "draft",
            "created_at": now_iso(),
        })

        if len(line_batch) >= BATCH_SIZE:
            await _flush()

    # Final flush — force progress write so the UI sees the exact totals
    # (skip the redundant else-branch: an empty _flush() still writes progress).
    await _flush(force_progress=True)

    sorted_periods = sorted(period_counts.keys())
    is_multi_period = len(sorted_periods) > 1
    display_period = period if period else (sorted_periods[0] if len(sorted_periods) == 1 else "multi")

    await db.royalty_imports.update_one(
        {"id": import_id},
        {"$set": {
            "period": display_period,
            "period_start": sorted_periods[0] if sorted_periods else (period or None),
            "period_end": sorted_periods[-1] if sorted_periods else (period or None),
            "is_multi_period": is_multi_period,
            "progress_pct": 100,
            "status": "pending_review",
            "finished_at": now_iso(),
            "updated_at": now_iso(),
        }},
    )

    final = await db.royalty_imports.find_one({"id": import_id}, {"_id": 0})
    return final


async def _process_csv_import_bg(
    *, import_id: str, file_path: str, period: Optional[str],
    rate_eur_idr: float, fee_percent: float, user_id: str,
):
    """Background variant — catches and logs exceptions instead of letting them
    crash the event loop. Marks the import as 'error' on failure.
    """
    try:
        await _process_csv_import_inline(
            import_id=import_id, file_path=file_path, period=period,
            rate_eur_idr=rate_eur_idr, fee_percent=fee_percent,
        )
        await log_activity(
            user_id, "upload_royalty_csv_async_finished", "royalty", import_id,
        )
    except Exception as e:
        logger.exception("Background CSV import %s failed: %s", import_id, e)
        await db.royalty_imports.update_one(
            {"id": import_id},
            {"$set": {
                "status": "error",
                "error_message": str(e)[:500],
                "finished_at": now_iso(),
                "updated_at": now_iso(),
            }},
        )


@royalty_r.get("/admin/imports")
async def admin_list_imports(user: dict = Depends(require_admin)):
    items = await db.royalty_imports.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    # Compute live progress_pct on the fly for in-flight imports.
    for it in items:
        if it.get("status") == "processing" and it.get("total_lines"):
            it["progress_pct"] = min(99, int((it.get("processed_lines", 0) / max(it["total_lines"], 1)) * 100))
        elif it.get("status") == "publishing":
            it["progress_pct"] = it.get("publish_progress_pct") or 0
    return items


@royalty_r.get("/admin/imports/{import_id}")
async def admin_get_import(import_id: str, user: dict = Depends(require_admin)):
    """Get a single royalty_import doc + sample lines + per-label breakdown.

    For in-flight imports (status='processing' or 'publishing'), the frontend
    polls this and uses progress_pct to render a live progress bar.
    """
    imp = await db.royalty_imports.find_one({"id": import_id}, {"_id": 0})
    if not imp:
        raise HTTPException(status_code=404, detail="Import tidak ditemukan")
    if imp.get("status") == "processing" and imp.get("total_lines"):
        imp["progress_pct"] = min(99, int((imp.get("processed_lines", 0) / max(imp["total_lines"], 1)) * 100))
    elif imp.get("status") == "publishing":
        imp["progress_pct"] = imp.get("publish_progress_pct") or 0

    # Sample top-500 lines + per-label breakdown — both touch the multi-million
    # `royalty_lines` collection and would trip the 10s CSOT cap on production
    # Atlas. Use db_bg (uncapped client) for these reads.
    try:
        lines = await db_bg.royalty_lines.find({"import_id": import_id}, {"_id": 0}).sort("revenue_eur", -1).limit(500).to_list(500)
    except Exception as e:
        logger.warning("[ADMIN GET IMPORT] %s sample-lines query failed: %s", import_id, e)
        lines = []

    # per-label breakdown
    pipeline = [
        {"$match": {"import_id": import_id, "label_id": {"$ne": None}}},
        {"$group": {"_id": "$label_id", "total_idr": {"$sum": "$label_idr"}, "total_eur": {"$sum": "$revenue_eur"}, "lines": {"$sum": 1}}},
        {"$sort": {"total_idr": -1}},
    ]
    per_label = []
    try:
        async for r in db_bg.royalty_lines.aggregate(pipeline, allowDiskUse=True):
            label = await db.labels.find_one({"id": r["_id"]}, {"_id": 0, "label_name": 1, "id": 1})
            per_label.append({**r, "label": label})
    except Exception as e:
        logger.warning("[ADMIN GET IMPORT] %s per-label aggregate failed: %s", import_id, e)

    return {"import": imp, "lines": lines, "per_label": per_label}


@royalty_r.post("/admin/imports/{import_id}/line/{line_id}/match")
async def admin_manually_match_line(import_id: str, line_id: str, body: RoyaltyLineMatchIn, user: dict = Depends(require_admin)):
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    imp = await db.royalty_imports.find_one({"id": import_id})
    if not imp:
        raise HTTPException(status_code=404, detail="Import tidak ditemukan")
    if imp["status"] not in ("pending_review",):
        raise HTTPException(status_code=400, detail="Hanya bisa diubah saat status pending_review")
    line = await db.royalty_lines.find_one({"id": line_id, "import_id": import_id})
    if not line:
        raise HTTPException(status_code=404, detail="Line tidak ditemukan")
    if not body.track_id:
        raise HTTPException(status_code=400, detail="track_id wajib")
    track = await db.tracks.find_one({"id": body.track_id})
    if not track:
        raise HTTPException(status_code=404, detail="Track tidak ditemukan")
    label = await db.labels.find_one({"id": track["label_id"]}, {"_id": 0})
    history = await db.royalty_percentage_history.find({"label_id": track["label_id"]}, {"_id": 0}).to_list(500)
    # Use line's own period (supports multi-period imports); fall back to import.period
    line_period = line.get("period") or imp.get("period") or imp.get("period_start") or ""
    label_pct = label_percentage_at(history, float(label.get("royalty_percentage_default", 60) or 60), line_period)
    calc = calculate_line(line["revenue_eur"], imp["fee_percent"], label_pct, imp["exchange_rate_eur_idr"])
    new_total_label_idr = imp["total_label_idr"] - line.get("label_idr", 0) + calc["label_idr"]
    await db.royalty_lines.update_one({"id": line_id}, {"$set": {
        "track_id": track["id"],
        "release_id": track["release_id"],
        "label_id": track["label_id"],
        "artist_id": track.get("artist_id"),
        "label_percentage_applied": label_pct,
        **calc,
        "match_status": "manually_matched",
    }})
    await db.royalty_imports.update_one({"id": import_id}, {
        "$inc": {"matched_lines": 1, "unmatched_lines": -1 if line["match_status"] == "unmatched" else 0},
        "$set": {"total_label_idr": new_total_label_idr, "updated_at": now_iso()},
    })
    return await db.royalty_lines.find_one({"id": line_id}, {"_id": 0})


@royalty_r.post("/admin/imports/{import_id}/publish")
async def admin_publish_import(import_id: str, body: RoyaltyImportPublishIn, user: dict = Depends(require_admin)):
    """Publish CSV → moves all matched lines to status=pending and accumulates to
    `label.balance_pending_idr`. Runs in background (no timeout) and is fully
    idempotent — retrying is always safe.

    Status transitions: pending_review → publishing → published (or publish_error).
    """
    try:
        if user["role"] not in ("super_admin", "admin_finance"):
            raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
        imp = await db.royalty_imports.find_one({"id": import_id})
        if not imp:
            raise HTTPException(status_code=404, detail="Import tidak ditemukan")

        # Defensive: tolerate legacy docs that may be missing the `status` field
        status_val = imp.get("status", "pending_review")
        if status_val == "publishing":
            # Already running — return current doc so the frontend polls progress
            out = await db.royalty_imports.find_one({"id": import_id}, {"_id": 0})
            return out
        if status_val not in ("pending_review", "publish_error"):
            raise HTTPException(
                status_code=400,
                detail=f"Import status tidak valid untuk publish: {status_val}. Status valid: pending_review, publish_error.",
            )

        # Flip to 'publishing' atomically, reset progress
        now = now_iso()
        await db.royalty_imports.update_one(
            {"id": import_id},
            {"$set": {
                "status": "publishing",
                "publish_progress_pct": 0,
                "publish_started_at": now,
                "error_message": None,
                "updated_at": now,
            }},
        )
        import asyncio
        asyncio.create_task(_publish_bg(import_id=import_id, user_id=user["id"]))
        out = await db.royalty_imports.find_one({"id": import_id}, {"_id": 0})
        logger.info("[PUBLISH] %s queued for background by user %s", import_id, user["email"])
        return out
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[PUBLISH] %s endpoint crashed: %s", import_id, e)
        # Try to leave a useful error message on the import doc for the UI
        try:
            await db.royalty_imports.update_one(
                {"id": import_id},
                {"$set": {
                    "status": "publish_error",
                    "error_message": f"Publish endpoint crashed: {type(e).__name__}: {str(e)[:200]}",
                    "updated_at": now_iso(),
                }},
            )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Publish gagal: {type(e).__name__}: {str(e)[:200]}")


async def _publish_bg(*, import_id: str, user_id: str):
    """Background publish: idempotent, restart-safe, no ingress timeout.

    Runs on `db_bg` (the CSOT-uncapped Mongo client) because aggregating &
    updating millions of `royalty_lines` rows routinely exceeds the 10s
    `timeoutMS` enforced on the user-facing `db` client in production.

    Idempotency rules:
      - Skip a label if a `balance_transactions` row already exists for
        (label_id, type='royalty_pending', reference_id=import_id) — means we
        already credited that label in a previous (interrupted) run.
      - Use bulk `update_many` for the line-status flip — naturally idempotent.
      - Notifications are gated by the same balance_transactions check.
    """
    try:
        imp = await db_bg.royalty_imports.find_one({"id": import_id})
        if not imp:
            logger.error("[PUBLISH BG] import %s vanished", import_id)
            return
        period_label = (
            f"{imp.get('period_start')} s/d {imp.get('period_end')}"
            if imp.get("is_multi_period") else imp.get("period", "")
        )

        # 1) Aggregate per label (fast — Mongo does the heavy lifting)
        pipeline = [
            {"$match": {"import_id": import_id, "match_status": {"$in": ["matched", "manually_matched"]}}},
            {"$group": {"_id": "$label_id", "total_idr": {"$sum": "$label_idr"}}},
        ]
        per_label: List[Dict[str, Any]] = []
        async for r in db_bg.royalty_lines.aggregate(pipeline, allowDiskUse=True):
            if r.get("_id"):
                per_label.append(r)
        total_labels = max(len(per_label), 1)

        await db_bg.royalty_imports.update_one(
            {"id": import_id},
            {"$set": {"publish_progress_pct": 5, "updated_at": now_iso()}},
        )

        # 2) Credit each label (idempotent skip if already credited)
        credited: List[Dict[str, Any]] = []
        for i, r in enumerate(per_label):
            label_id = r["_id"]
            amount_idr = int(r["total_idr"])
            existing_tx = await db_bg.balance_transactions.find_one({
                "label_id": label_id,
                "type": "royalty_pending",
                "reference_type": "royalty_import",
                "reference_id": import_id,
            })
            if existing_tx:
                # Already credited in a previous run — count it but don't double-add
                continue
            await db_bg.labels.update_one(
                {"id": label_id},
                {"$inc": {"balance_pending_idr": amount_idr}, "$set": {"updated_at": now_iso()}},
            )
            await db_bg.balance_transactions.insert_one({
                "id": new_id(),
                "label_id": label_id,
                "type": "royalty_pending",
                "amount_idr": amount_idr,
                "reference_type": "royalty_import",
                "reference_id": import_id,
                "description": f"Royalti periode {period_label} ke saldo pending",
                "created_at": now_iso(),
            })
            credited.append(r)
            if (i + 1) % 5 == 0 or i == len(per_label) - 1:
                pct = 5 + int((i + 1) / total_labels * 70)
                await db_bg.royalty_imports.update_one(
                    {"id": import_id},
                    {"$set": {"publish_progress_pct": min(pct, 75), "updated_at": now_iso()}},
                )

        # 3) Flip royalty_lines status → 'pending' in CHUNKS to avoid MongoDB
        # cluster-level operation time limits (Atlas/serverless commonly enforce
        # maxTimeMS — code 50 'MaxTimeMSExpired' on huge update_many).
        # Idempotent: the filter excludes already-flipped lines. We paginate by
        # Mongo's native `_id` (always indexed) so each chunk hits an IXSCAN.
        CHUNK_SIZE = 2000
        base_filter = {
            "import_id": import_id,
            "match_status": {"$in": ["matched", "manually_matched"]},
            "status": {"$ne": "pending"},
        }
        last_oid = None
        total_flipped = 0
        while True:
            q = dict(base_filter)
            if last_oid is not None:
                q["_id"] = {"$gt": last_oid}
            batch = await db_bg.royalty_lines.find(q, {"_id": 1}).sort("_id", 1).limit(CHUNK_SIZE).to_list(CHUNK_SIZE)
            if not batch:
                break
            oids = [d["_id"] for d in batch]
            last_oid = oids[-1]
            await db_bg.royalty_lines.update_many({"_id": {"$in": oids}}, {"$set": {"status": "pending"}})
            total_flipped += len(oids)
            # Progress 75 → 95% during line flip
            line_pct = 75 + min(int(total_flipped / 220_000 * 20), 20)
            await db_bg.royalty_imports.update_one(
                {"id": import_id},
                {"$set": {"publish_progress_pct": min(line_pct, 95), "updated_at": now_iso()}},
            )
        logger.info("[PUBLISH BG] %s — flipped %d lines to pending in %d-row chunks",
                    import_id, total_flipped, CHUNK_SIZE)
        await db_bg.royalty_imports.update_one(
            {"id": import_id},
            {"$set": {"publish_progress_pct": 95, "updated_at": now_iso()}},
        )

        # 4) Notify each label (only newly-credited ones — avoids spam on retry)
        for r in credited:
            user_ids = await label_user_ids(r["_id"])
            amt = f"Rp {int(r['total_idr']):,}".replace(",", ".")
            try:
                await notify_many(
                    user_ids, "royalty_published",
                    f"Royalti periode {period_label} terbit",
                    f"{amt} masuk ke saldo pending. Lihat detail di dashboard.",
                    "/label/royalty",
                    {"period": imp.get("period"), "import_id": import_id},
                )
            except Exception as e:
                logger.warning("[PUBLISH BG] notify failed for label %s: %s", r["_id"], e)

        # 5) Done
        await db_bg.royalty_imports.update_one(
            {"id": import_id},
            {"$set": {
                "status": "published",
                "published_at": now_iso(),
                "publish_progress_pct": 100,
                "error_message": None,
                "updated_at": now_iso(),
            }},
        )
        await log_activity(user_id, "publish_royalty", "royalty", import_id,
                           after={"labels_credited": len(credited), "total_labels": total_labels})
        logger.info("[PUBLISH BG] %s DONE — %d/%d labels credited", import_id, len(credited), total_labels)

        # Best-effort: invalidate the dashboard revenue cache so admins see the
        # new totals immediately on next dashboard load instead of waiting 60s.
        try:
            from routes.admin import _recompute_revenue_cache  # lazy import to avoid cycle
            import asyncio as _aio
            _aio.create_task(_recompute_revenue_cache())
        except Exception:
            pass

        # Best-effort: rebuild the monthly_analytics cache so the dashboard's
        # charts reflect the just-published data. Heavy aggregate (1M+ rows on
        # production) — fire-and-forget so this BG task can finish.
        try:
            from routes.admin_analytics import recompute_monthly_analytics  # lazy
            import asyncio as _aio2
            _aio2.create_task(recompute_monthly_analytics())
        except Exception:
            pass

    except Exception as e:
        logger.exception("[PUBLISH BG] %s FAILED: %s", import_id, e)
        try:
            await db_bg.royalty_imports.update_one(
                {"id": import_id},
                {"$set": {
                    "status": "publish_error",
                    "error_message": f"Publish gagal: {str(e)[:300]}",
                    "updated_at": now_iso(),
                }},
            )
        except Exception as e2:
            # Last-ditch fallback via the foreground client (might still time
            # out, but we MUST try to surface the failure in the UI).
            logger.error("[PUBLISH BG] %s could not even persist publish_error via db_bg: %s", import_id, e2)
            try:
                await db.royalty_imports.update_one(
                    {"id": import_id},
                    {"$set": {
                        "status": "publish_error",
                        "error_message": f"Publish gagal: {str(e)[:300]}",
                        "updated_at": now_iso(),
                    }},
                )
            except Exception:
                pass


@royalty_r.post("/admin/imports/{import_id}/mark-dana-received")
async def admin_mark_dana_received(import_id: str, user: dict = Depends(require_admin)):
    """Saat dana Believe masuk: pindahkan saldo pending → available."""
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    imp = await db.royalty_imports.find_one({"id": import_id})
    if not imp:
        raise HTTPException(status_code=404, detail="Import tidak ditemukan")
    if imp["status"] != "published":
        raise HTTPException(status_code=400, detail="Import harus dipublish terlebih dahulu")
    if imp.get("dana_received_at"):
        raise HTTPException(status_code=400, detail="Dana sudah ditandai diterima")

    pipeline = [
        {"$match": {"import_id": import_id, "status": "pending"}},
        {"$group": {"_id": "$label_id", "total_idr": {"$sum": "$label_idr"}}},
    ]
    period_label = (
        f"{imp.get('period_start')} s/d {imp.get('period_end')}"
        if imp.get("is_multi_period") else imp.get("period", "")
    )
    # Heavy aggregate + bulk update on millions of rows — route through db_bg
    # (uncapped Mongo client) to bypass the 10s CSOT cap that kills production.
    async for r in db_bg.royalty_lines.aggregate(pipeline, allowDiskUse=True):
        await db_bg.labels.update_one({"id": r["_id"]}, {"$inc": {
            "balance_pending_idr": -int(r["total_idr"]),
            "balance_available_idr": int(r["total_idr"]),
        }, "$set": {"updated_at": now_iso()}})
        await db_bg.balance_transactions.insert_one({
            "id": new_id(),
            "label_id": r["_id"],
            "type": "royalty_available",
            "amount_idr": int(r["total_idr"]),
            "reference_type": "royalty_import",
            "reference_id": import_id,
            "description": f"Dana royalti periode {period_label} diterima — saldo tersedia",
            "created_at": now_iso(),
        })

    # Chunked update_many over `_id` to avoid maxTimeMS on the cluster
    CHUNK_SIZE = 2000
    last_oid = None
    base_filter = {"import_id": import_id, "status": "pending"}
    total_flipped = 0
    while True:
        q = dict(base_filter)
        if last_oid is not None:
            q["_id"] = {"$gt": last_oid}
        batch = await db_bg.royalty_lines.find(q, {"_id": 1}).sort("_id", 1).limit(CHUNK_SIZE).to_list(CHUNK_SIZE)
        if not batch:
            break
        oids = [d["_id"] for d in batch]
        last_oid = oids[-1]
        await db_bg.royalty_lines.update_many({"_id": {"$in": oids}}, {"$set": {"status": "available"}})
        total_flipped += len(oids)
    logger.info("[MARK_DANA] %s — flipped %d lines pending→available", import_id, total_flipped)
    await db.royalty_imports.update_one({"id": import_id}, {"$set": {"status": "dana_received", "dana_received_at": now_iso(), "updated_at": now_iso()}})
    await log_activity(user["id"], "mark_dana_received", "royalty", import_id)
    return await db.royalty_imports.find_one({"id": import_id}, {"_id": 0})


@royalty_r.post("/admin/reset-demo-data")
async def admin_reset_demo_royalty_data(
    confirm: str = Form(...),
    user: dict = Depends(require_admin),
):
    """⚠️ DANGER ZONE — Wipe all royalty data (imports + lines + balance transactions)
    and reset every label's balance to zero. Used to clear dummy data before going live.
    Requires confirm='RESET' to proceed. Super Admin only.
    """
    if user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Hanya Super Admin")
    if confirm != "RESET":
        raise HTTPException(status_code=400, detail="Konfirmasi tidak cocok. Ketik 'RESET' untuk melanjutkan.")

    n_imports = (await db.royalty_imports.delete_many({})).deleted_count
    n_lines = (await db.royalty_lines.delete_many({})).deleted_count
    n_tx = (await db.balance_transactions.delete_many({"type": {"$in": ["royalty_pending", "royalty_available"]}})).deleted_count
    n_labels = (await db.labels.update_many({}, {"$set": {
        "balance_pending_idr": 0,
        "balance_available_idr": 0,
        "updated_at": now_iso(),
    }})).modified_count
    # Also delete uploaded CSV files
    csv_dir = UPLOAD_DIR / "csv"
    deleted_files = 0
    if csv_dir.exists():
        for p in csv_dir.iterdir():
            if p.is_file():
                try:
                    p.unlink()
                    deleted_files += 1
                except Exception:
                    pass
    await log_activity(user["id"], "reset_demo_royalty", "system", "all", after={
        "imports": n_imports, "lines": n_lines, "transactions": n_tx,
        "labels_reset": n_labels, "files_deleted": deleted_files,
    })
    return {
        "ok": True,
        "imports_deleted": n_imports,
        "lines_deleted": n_lines,
        "transactions_deleted": n_tx,
        "labels_reset": n_labels,
        "csv_files_deleted": deleted_files,
    }


# -------- LABEL royalty endpoints --------
@royalty_r.get("/months")
async def label_royalty_months(user: dict = Depends(get_current_user)):
    """List periods that have published royalty data visible to the current user."""
    if user["role"] == LABEL_ROLE:
        label = await get_label_by_user(user)
        filt = {"label_id": label["id"], "status": {"$in": ["pending", "available", "withdrawn"]}}
    elif user["role"] == ARTIST_ROLE:
        filt = {"artist_id": user["id"], "status": {"$in": ["pending", "available", "withdrawn"]}}
    elif user["role"] in ADMIN_ROLES:
        filt = {"status": {"$in": ["pending", "available", "withdrawn"]}}
    else:
        raise HTTPException(status_code=403, detail="Tidak diperbolehkan")
    months = await db.royalty_lines.distinct("period", filt)
    months.sort(reverse=True)
    return months


@royalty_r.get("/summary")
async def label_royalty_summary(user: dict = Depends(get_current_user), period: Optional[str] = None):
    if user["role"] == LABEL_ROLE:
        label = await get_label_by_user(user)
        base = {"label_id": label["id"]}
    elif user["role"] == ARTIST_ROLE:
        base = {"artist_id": user["id"]}
    else:
        raise HTTPException(status_code=403, detail="Tidak diperbolehkan")
    if period:
        base["period"] = period

    pipeline = [
        {"$match": {**base, "status": {"$in": ["pending", "available", "withdrawn"]}}},
        {"$group": {
            "_id": None,
            "total_idr": {"$sum": "$label_idr"},
            "total_streams": {"$sum": "$quantity"},
            "total_lines": {"$sum": 1},
        }},
    ]
    summary = {"total_idr": 0, "total_streams": 0, "total_lines": 0}
    async for row in db.royalty_lines.aggregate(pipeline):
        summary = {"total_idr": row["total_idr"], "total_streams": row["total_streams"], "total_lines": row["total_lines"]}

    # per-platform
    by_platform = []
    async for row in db.royalty_lines.aggregate([
        {"$match": {**base, "status": {"$in": ["pending", "available", "withdrawn"]}}},
        {"$group": {"_id": "$platform", "total_idr": {"$sum": "$label_idr"}, "streams": {"$sum": "$quantity"}}},
        {"$sort": {"total_idr": -1}},
    ]):
        by_platform.append({"platform": row["_id"] or "Unknown", "total_idr": row["total_idr"], "streams": row["streams"]})

    by_country = []
    async for row in db.royalty_lines.aggregate([
        {"$match": {**base, "status": {"$in": ["pending", "available", "withdrawn"]}}},
        {"$group": {"_id": "$country", "total_idr": {"$sum": "$label_idr"}}},
        {"$sort": {"total_idr": -1}},
        {"$limit": 10},
    ]):
        by_country.append({"country": row["_id"] or "Unknown", "total_idr": row["total_idr"]})

    by_track = []
    async for row in db.royalty_lines.aggregate([
        {"$match": {**base, "status": {"$in": ["pending", "available", "withdrawn"]}}},
        {"$group": {"_id": {"track_id": "$track_id", "title": "$track_title_raw"}, "total_idr": {"$sum": "$label_idr"}, "streams": {"$sum": "$quantity"}}},
        {"$sort": {"total_idr": -1}},
        {"$limit": 15},
    ]):
        by_track.append({"track_id": row["_id"].get("track_id"), "title": row["_id"].get("title") or "Unknown", "total_idr": row["total_idr"], "streams": row["streams"]})

    return {"summary": summary, "by_platform": by_platform, "by_country": by_country, "by_track": by_track}


@royalty_r.get("/lines")
async def label_royalty_lines(
    user: dict = Depends(get_current_user),
    period: Optional[str] = None,
    platform: Optional[str] = None,
    country: Optional[str] = None,
    track_id: Optional[str] = None,
    artist_id: Optional[str] = None,
    limit: int = 500,
):
    filt: Dict[str, Any] = {"status": {"$in": ["pending", "available", "withdrawn"]}}
    if user["role"] == LABEL_ROLE:
        label = await get_label_by_user(user)
        filt["label_id"] = label["id"]
    elif user["role"] == ARTIST_ROLE:
        filt["artist_id"] = user["id"]
    elif user["role"] in ADMIN_ROLES:
        pass
    else:
        raise HTTPException(status_code=403, detail="Tidak diperbolehkan")
    if period:
        filt["period"] = period
    if platform:
        filt["platform"] = platform
    if country:
        filt["country"] = country
    if track_id:
        filt["track_id"] = track_id
    if artist_id:
        filt["artist_id"] = artist_id
    items = await db.royalty_lines.find(filt, {"_id": 0}).sort("label_idr", -1).limit(limit).to_list(limit)
    # Hide sensitive fields from label/artist responses
    if user["role"] in (LABEL_ROLE, ARTIST_ROLE):
        items = [strip_sensitive(it) for it in items]
    return items


@royalty_r.get("/export.csv")
async def label_royalty_export_csv(
    user: dict = Depends(get_current_user),
    period: Optional[str] = None,
):
    """Stream CSV export of royalty lines for the current label/period."""
    from fastapi.responses import StreamingResponse
    filt: Dict[str, Any] = {"status": {"$in": ["pending", "available", "withdrawn"]}}
    if user["role"] == LABEL_ROLE:
        label = await get_label_by_user(user)
        filt["label_id"] = label["id"]
    elif user["role"] == ARTIST_ROLE:
        filt["artist_id"] = user["id"]
    else:
        raise HTTPException(status_code=403, detail="Tidak diperbolehkan")
    if period:
        filt["period"] = period

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "period", "release_title", "track_title", "artist_name", "platform", "country",
        "isrc", "upc", "streams", "royalty_idr", "status",
    ])
    cursor = db.royalty_lines.find(filt, {"_id": 0}).sort("period", -1)
    async for it in cursor:
        writer.writerow([
            it.get("period"),
            it.get("release_title_raw"),
            it.get("track_title_raw"),
            it.get("artist_name_raw"),
            it.get("platform"),
            it.get("country"),
            it.get("isrc"),
            it.get("upc"),
            it.get("quantity"),
            it.get("label_idr"),
            it.get("status"),
        ])
    buf.seek(0)
    filename = f"royalty_{period or 'all'}.csv"
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


# ============================================================
# Recovery & Retry for interrupted background imports
# ============================================================
def _import_file_path(import_id: str, filename: Optional[str] = None) -> Optional[str]:
    """Locate the CSV file on disk for an import. Tries both .csv and .csv.gz."""
    base = UPLOAD_DIR / "csv"
    # Primary location uses the import id as filename (see upload handler)
    for ext in (".csv", ".csv.gz"):
        p = base / f"{import_id}{ext}"
        if p.exists():
            return str(p)
    return None


async def _ensure_local_csv(imp: dict) -> Optional[str]:
    """Return a local path to the CSV for this import, re-downloading from R2
    if needed. Returns None if neither disk nor R2 has the file.
    """
    import_id = imp["id"]
    local = _import_file_path(import_id, imp.get("filename"))
    if local:
        return local
    r2_key = imp.get("r2_key")
    if not r2_key:
        return None
    meta = await storage_service.head_object(key=r2_key)
    if not meta:
        return None
    ext = ".csv.gz" if r2_key.endswith(".gz") else ".csv"
    target = UPLOAD_DIR / "csv" / f"{import_id}{ext}"
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        await storage_service.download_to_file(key=r2_key, local_path=str(target))
        return str(target)
    except Exception as e:
        logger.warning("[ROYALTY] re-download from R2 failed for %s: %s", import_id, e)
        return None


async def _reset_import_for_retry(import_id: str) -> None:
    """Wipe partial side-effects of a previous failed/interrupted run so we can
    safely restart the processing without double-inserting rows.

    - Delete royalty_lines tied to this import
    - Delete auto-created labels/releases/tracks (only ones with auto_created_from=this import)
    - Reset counters on the import doc
    """
    await db.royalty_lines.delete_many({"import_id": import_id})
    await db.labels.delete_many({"auto_created_from": import_id})
    await db.releases.delete_many({"auto_created_from": import_id})
    await db.tracks.delete_many({"auto_created_from": import_id})
    await db.royalty_imports.update_one(
        {"id": import_id},
        {"$set": {
            "total_lines": 0,
            "processed_lines": 0,
            "progress_pct": 0,
            "matched_lines": 0,
            "unmatched_lines": 0,
            "invalid_period_rows": 0,
            "auto_created_labels": 0,
            "auto_created_releases": 0,
            "auto_created_tracks": 0,
            "total_revenue_eur": 0.0,
            "total_label_idr": 0,
            "period_breakdown": {},
            "status": "processing",
            "error_message": None,
            "finished_at": None,
            "updated_at": now_iso(),
        }},
    )


@royalty_r.post("/admin/imports/{import_id}/retry")
async def admin_retry_import(import_id: str, user: dict = Depends(require_admin)):
    """Manually re-trigger background processing for a stuck (processing) or failed (error) import.

    Only Super Admin / Admin Finance. The original uploaded CSV file must still
    exist on disk — otherwise we return 400 and the admin must re-upload.
    """
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    imp = await db.royalty_imports.find_one({"id": import_id})
    if not imp:
        raise HTTPException(status_code=404, detail="Import tidak ditemukan")
    if imp["status"] not in ("processing", "error"):
        raise HTTPException(status_code=400, detail=f"Retry hanya untuk status processing/error (status saat ini: {imp['status']})")

    file_path = await _ensure_local_csv(imp)
    if not file_path:
        await db.royalty_imports.update_one(
            {"id": import_id},
            {"$set": {
                "status": "error",
                "error_message": "File CSV hilang dari disk dan tidak ada di R2. Silakan upload ulang.",
                "finished_at": now_iso(),
                "updated_at": now_iso(),
            }},
        )
        raise HTTPException(status_code=400, detail="File CSV asli tidak ditemukan. Upload ulang.")

    await _reset_import_for_retry(import_id)
    import asyncio
    asyncio.create_task(_process_csv_import_bg(
        import_id=import_id,
        file_path=file_path,
        period=imp.get("period_start") if imp.get("is_multi_period") is False else None,
        rate_eur_idr=imp["exchange_rate_eur_idr"],
        fee_percent=imp["fee_percent"],
        user_id=user["id"],
    ))
    await log_activity(user["id"], "retry_royalty_import", "royalty", import_id)
    return {"ok": True, "import_id": import_id, "status": "processing"}


@royalty_r.delete("/admin/imports/{import_id}")
async def admin_delete_import(import_id: str, user: dict = Depends(require_super_admin)):
    """Permanently delete a royalty import that hasn't been published or had its
    funds released. Allowed statuses:
      - awaiting_upload (no file uploaded yet)
      - processing (in-flight CSV parser)
      - error (CSV parsing failed)
      - publish_error (background publish failed)
      - pending_review (parsed, but admin hasn't published yet)

    REFUSED for `published` / `publishing` / `dana_received` — those have
    `balance_transactions` and label balances tied to them. Reversing those
    would require a separate explicit refund flow (out of scope here).

    Cleans up:
      - All `royalty_lines` for this import (chunked via db_bg)
      - Any auto-created labels/releases/tracks marked `auto_created_from=this_id`
      - The uploaded CSV file on disk + R2 object (best effort)
      - The `royalty_imports` doc itself
    """
    imp = await db.royalty_imports.find_one({"id": import_id})
    if not imp:
        raise HTTPException(status_code=404, detail="Import tidak ditemukan")

    DELETABLE_STATUSES = {"awaiting_upload", "processing", "error", "publish_error", "pending_review"}
    status_val = imp.get("status")
    if status_val not in DELETABLE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Tidak bisa hapus import dengan status '{status_val}'. "
                "Import yang sudah published/dana_received mempengaruhi saldo label. "
                "Status yang bisa dihapus: " + ", ".join(sorted(DELETABLE_STATUSES))
            ),
        )

    # 1) Reset all derived data (lines, auto-created entities). Uses db (delete_many)
    # for tracks/releases/labels — small filtered sets. Lines deletion via db_bg
    # in case the CSV did manage to insert millions of rows before failing.
    n_lines = (await db_bg.royalty_lines.delete_many({"import_id": import_id})).deleted_count
    n_labels = (await db.labels.delete_many({"auto_created_from": import_id})).deleted_count
    n_releases = (await db.releases.delete_many({"auto_created_from": import_id})).deleted_count
    n_tracks = (await db.tracks.delete_many({"auto_created_from": import_id})).deleted_count

    # 2) Cleanup R2 object + local CSV (best effort — never block the delete)
    r2_key = imp.get("r2_key")
    if r2_key:
        try:
            await storage_service.delete_object(key=r2_key)
        except Exception as e:
            logger.warning("[ROYALTY DELETE] R2 cleanup failed for %s: %s", import_id, e)
    local_csv = imp.get("file_path")
    if local_csv:
        try:
            from pathlib import Path as _P
            _P(local_csv).unlink(missing_ok=True)
        except Exception as e:
            logger.warning("[ROYALTY DELETE] local file cleanup failed for %s: %s", import_id, e)

    # 3) Drop the import doc
    await db.royalty_imports.delete_one({"id": import_id})

    await log_activity(
        user["id"], "delete_royalty_import", "royalty", import_id,
        before={"period": imp.get("period") or imp.get("period_start"), "status": status_val},
        after={"lines_deleted": n_lines, "auto_labels_deleted": n_labels,
               "auto_releases_deleted": n_releases, "auto_tracks_deleted": n_tracks},
    )

    # Best-effort cache refresh — revenue totals may have shifted.
    try:
        from routes.admin import _recompute_revenue_cache  # lazy import
        import asyncio as _aio
        _aio.create_task(_recompute_revenue_cache())
    except Exception:
        pass

    # Also rebuild analytics cache (monthly chart cache lives separate from the
    # revenue total cache).
    try:
        from routes.admin_analytics import recompute_monthly_analytics  # lazy
        import asyncio as _aio2
        _aio2.create_task(recompute_monthly_analytics())
    except Exception:
        pass

    return {
        "ok": True,
        "import_id": import_id,
        "lines_deleted": n_lines,
        "auto_labels_deleted": n_labels,
        "auto_releases_deleted": n_releases,
        "auto_tracks_deleted": n_tracks,
    }


async def resume_interrupted_imports():
    """Called on backend startup. For every royalty_import stuck in 'processing'
    or 'publishing' (hot-reload or pod restart killed the task), either:
      - Resume CSV processing if the CSV file is still on disk/R2; or
      - Resume publish — fully idempotent so re-running is safe.
      - Mark as 'error' / 'publish_error' if recovery is impossible.
    """
    import asyncio
    try:
        # 1) Resume stuck CSV processing
        stuck_processing = await db.royalty_imports.find(
            {"status": "processing"},
            {"_id": 0, "id": 1, "filename": 1, "exchange_rate_eur_idr": 1,
             "fee_percent": 1, "period": 1, "period_start": 1, "is_multi_period": 1,
             "uploaded_by": 1, "r2_key": 1},
        ).to_list(100)
    except Exception as e:
        logger.exception("resume_interrupted_imports: cannot query imports: %s", e)
        return

    if stuck_processing:
        logger.info("resume_interrupted_imports: found %d stuck processing import(s)", len(stuck_processing))
    for imp in stuck_processing:
        import_id = imp["id"]
        file_path = await _ensure_local_csv(imp)
        if not file_path:
            await db.royalty_imports.update_one(
                {"id": import_id},
                {"$set": {
                    "status": "error",
                    "error_message": "Container restart — file CSV asli hilang dari disk & R2. Upload ulang.",
                    "finished_at": now_iso(),
                    "updated_at": now_iso(),
                }},
            )
            logger.warning("resume_interrupted_imports: %s marked as error (file missing both disk + R2)", import_id)
            continue
        # Wipe partial inserts then re-spawn background task
        await _reset_import_for_retry(import_id)
        # Use period only if the import was a single-period upload
        period = None
        if imp.get("is_multi_period") is False and imp.get("period_start"):
            period = imp["period_start"]
        asyncio.create_task(_process_csv_import_bg(
            import_id=import_id,
            file_path=file_path,
            period=period,
            rate_eur_idr=imp["exchange_rate_eur_idr"],
            fee_percent=imp["fee_percent"],
            user_id=imp.get("uploaded_by") or "system",
        ))
        logger.info("resume_interrupted_imports: %s resumed from %s", import_id, file_path)

    # 2) Resume stuck publish (idempotent — safe to re-run)
    try:
        stuck_publishing = await db.royalty_imports.find(
            {"status": "publishing"},
            {"_id": 0, "id": 1, "uploaded_by": 1},
        ).to_list(100)
    except Exception as e:
        logger.exception("resume_interrupted_imports: cannot query publishing: %s", e)
        return
    if stuck_publishing:
        logger.info("resume_interrupted_imports: found %d stuck publishing import(s)", len(stuck_publishing))
        for imp in stuck_publishing:
            asyncio.create_task(_publish_bg(
                import_id=imp["id"],
                user_id=imp.get("uploaded_by") or "system",
            ))
            logger.info("resume_interrupted_imports: %s publish resumed", imp["id"])
