"""Royalty CSV import & label/artist reports router."""
from fastapi import APIRouter, HTTPException, Request, Response, Depends, UploadFile, File, Form, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta, date
import os
import csv
import io
import shutil
import secrets
import tempfile
from pathlib import Path

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
    strip_sensitive, iter_csv_file, slug_artist,
)
from withdraw_utils import withdraw_window_state, jakarta_now, MIN_WITHDRAW_IDR
import storage_service
from .royalty_recalculation import close_stale_recalculation_jobs, run_global_recalculation_job
from .dashboard_cache import reset as reset_dashboard_revenue, schedule_recompute as schedule_dashboard_recompute

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

    Periode setiap baris selalu bersumber dari kolom `Bulan laporan`. Field
    `period` lama tetap diterima untuk kompatibilitas klien, tetapi tidak pernah
    dipakai sebagai fallback dan tidak dapat menimpa nilai CSV.
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

    # Legacy multipart compatibility for small files. Large imports use the
    # durable initiate → direct R2 PUT → finalize flow.
    MAX_BYTES = 10 * 1024 * 1024
    import_id = new_id()
    fname = file.filename or "upload.csv"
    ext = ".csv.gz" if fname.lower().endswith(".gz") else ".csv"
    content = await file.read(MAX_BYTES + 1)
    total_size = len(content)
    if total_size > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Upload multipart maksimal 10 MB. Gunakan upload langsung R2 untuk file besar.",
        )
    temporary = tempfile.NamedTemporaryFile(
        prefix=f"royalty-{import_id}-", suffix=ext, delete=False,
    )
    temporary.write(content)
    temporary.close()
    target = Path(temporary.name)

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
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Kolom revenue/amount tidak ditemukan di CSV")
    if col_idx.get("period") is None:
        target.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail="Kolom 'Bulan laporan' wajib ada di CSV. Kolom 'Bulan Penjualan' tidak dapat digunakan sebagai periode laporan.",
        )

    if not storage_service.is_configured():
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=503, detail="Cloud storage belum dikonfigurasi")
    r2_key = f"csv/{import_id}{ext}"
    try:
        await storage_service.upload_bytes(
            key=r2_key,
            data=content,
            content_type="application/gzip" if ext.endswith(".gz") else "text/csv",
        )
    except Exception:
        target.unlink(missing_ok=True)
        raise
    file_url = f"r2://{r2_key}"

    # ---- Determine sync vs async based on file size ----
    # Files <= 5 MB → process synchronously (preserves existing API behavior
    # for small CSVs and pytest fixtures). Files > 5 MB → background.
    SYNC_THRESHOLD = 5 * 1024 * 1024
    process_async = total_size > SYNC_THRESHOLD

    # Phase 32 — no separate distributor fee. Label share applies directly to
    # Believe's Pendapatan Bersih value.
    fee_percent = 0.0

    now = now_iso()
    import_doc = {
        "id": import_id,
        "period": "multi",
        "period_start": None,
        "period_end": None,
        "period_breakdown": {},
        "is_multi_period": False,
        "source": "believe",
        "filename": fname,
        "file_url": file_url,
        "r2_key": r2_key,
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
        "auto_created_artists": 0,
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
    try:
        result = await _process_csv_import_inline(
            import_id=import_id,
            file_path=str(target),
            period=period,
            rate_eur_idr=rate_eur_idr,
            fee_percent=fee_percent,
        )
    finally:
        target.unlink(missing_ok=True)
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
            "auto_artists": result.get("auto_created_artists"),
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


class RepairSourceInitiateIn(BaseModel):
    filename: str = Field(..., min_length=1, max_length=200)
    size_bytes: int = Field(..., gt=0, le=5 * 1024 * 1024 * 1024)


class RepairSourceFinalizeIn(BaseModel):
    upload_id: str = Field(..., min_length=1, max_length=100)


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

    fee_percent = 0.0

    now = now_iso()
    import_doc = {
        "id": import_id,
        "period": "multi",
        "period_start": None,
        "period_end": None,
        "period_breakdown": {},
        "is_multi_period": False,
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
    if col_idx.get("period") is None:
        raise HTTPException(
            status_code=400,
            detail="Kolom 'Bulan laporan' wajib ada di CSV. Kolom 'Bulan Penjualan' tidak dapat digunakan sebagai periode laporan.",
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
def _trigger_dashboard_recompute():
    """Phase 29 — fire-and-forget rebuild of the dashboard revenue cache +
    monthly_analytics rollup. Called right after an import finishes processing
    so Artist Management / Katalog / Analytics sync automatically without any
    manual tool."""
    import asyncio as _aio
    try:
        schedule_dashboard_recompute()
    except Exception:
        pass
    try:
        from routes.admin_analytics import schedule_monthly_analytics_recompute  # lazy
        _aio.create_task(schedule_monthly_analytics_recompute(reason="import_processed"))
    except Exception:
        pass


async def _process_csv_import_inline(
    *, import_id: str, file_path: str, period: Optional[str],
    rate_eur_idr: float, fee_percent: float, staged_replacement: bool = False,
) -> Dict[str, Any]:
    """Process the CSV file at `file_path` row-by-row in batches.

    For each batch (BATCH_SIZE rows):
      - Auto-create new label / release / track if needed
      - Compute royalty per line
      - Flush new entities + lines to MongoDB
      - Update import_doc with progress

    Returns the final import_doc.
    """
    # Old imports may still pass fee_percent=5 during retry. The fee has been
    # removed, so every processing path normalizes it to zero.
    fee_percent = 0.0

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
    # (label_id, name_slug) → artist doc. Used to auto-create artist sub-account
    # rows during ingestion so that "Materialize Artists" never has to run
    # after every CSV upload. Slugged blank/"Unknown" names are skipped.
    all_artists_by_key: Dict[tuple, Dict[str, Any]] = {}
    async for a in db_bg.artists.find(
        {}, {"_id": 0, "id": 1, "label_id": 1, "artist_name": 1, "name_slug": 1},
    ):
        slug = a.get("name_slug") or slug_artist(a.get("artist_name") or "")
        if slug:
            all_artists_by_key[(a.get("label_id"), slug)] = a

    # ---- Streaming accumulators ----
    headers: List[str] = []
    col_idx: Optional[Dict[str, Optional[int]]] = None
    line_batch: List[Dict[str, Any]] = []
    new_label_batch: List[Dict[str, Any]] = []
    new_release_batch: List[Dict[str, Any]] = []
    new_track_batch: List[Dict[str, Any]] = []
    new_artist_batch: List[Dict[str, Any]] = []
    period_counts: Dict[str, int] = {}
    counters = {
        "matched": 0, "unmatched": 0, "invalid_period_rows": 0,
        "auto_labels": 0, "auto_releases": 0, "auto_tracks": 0, "auto_artists": 0,
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
        if new_artist_batch:
            await db_bg.artists.insert_many(new_artist_batch, ordered=False)
            new_artist_batch.clear()
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
                    "auto_created_artists": counters["auto_artists"],
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

        # The CSV's `Bulan Laporan` column (raw["row_period"]) is the source of
        # truth — multi-period CSVs must keep each row's true period intact for
        # analytics, FIFO withdraw, and rollups to work correctly. There is no
        # fallback to Bulan Penjualan or the legacy form-period field.
        line_period = raw.get("row_period")
        if not line_period:
            counters["invalid_period_rows"] += 1
            continue
        counters["total_revenue_eur"] += revenue_eur
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
            # Unsettled royalties always follow the label's CURRENT share.
            # Percentage history is audit-only and no longer changes the rate
            # based on the reporting month.
            label_pct = default_pct
            calc = calculate_line(revenue_eur, fee_percent, label_pct, rate_eur_idr)
            counters["total_label_idr"] += calc["label_idr"]
        else:
            counters["unmatched"] += 1
            label_pct = 0.0
            calc = calculate_line(revenue_eur, fee_percent, 0.0, rate_eur_idr)

        # ---- Auto-create artist (Phase 28) ----
        # Resolve artist_id directly during ingestion so the Artist Management
        # page is populated immediately after publish — no need to run the
        # "Materialize Artists" tool manually afterwards. Skip for unmatched
        # rows (no label_id) and for blank/"Unknown" artist names.
        artist_id_for_line = track.get("artist_id") if track else None
        if label_id and not artist_id_for_line:
            a_slug = slug_artist(raw.get("artist_name") or "")
            if a_slug:
                a_key = (label_id, a_slug)
                existing_artist = all_artists_by_key.get(a_key)
                if existing_artist:
                    artist_id_for_line = existing_artist["id"]
                else:
                    new_artist = {
                        "id": new_id(),
                        "label_id": label_id,
                        "artist_name": (raw.get("artist_name") or "").strip(),
                        "name_slug": a_slug,
                        "status": "active",
                        "user_id": None,
                        "imported_legacy": True,
                        "auto_created_from_lines": True,
                        "auto_created_from": import_id,
                        "first_period": line_period,
                        "last_period": line_period,
                        "lifetime_lines": 0,
                        "lifetime_revenue_eur": 0,
                        "lifetime_label_idr": 0,
                        "created_at": now, "updated_at": now,
                    }
                    new_artist_batch.append(new_artist)
                    all_artists_by_key[a_key] = new_artist
                    artist_id_for_line = new_artist["id"]
                    counters["auto_artists"] += 1
                # Backfill the just-created track row with the resolved
                # artist_id (the track was added to new_track_batch above
                # with artist_id=None — we mutate before flush).
                if track and track.get("auto_created_from") == import_id and not track.get("artist_id"):
                    track["artist_id"] = artist_id_for_line

        legacy_cutoff = (labels.get(label_id, {}) if label_id else {}).get("last_withdrawn_period")
        legacy_settled = bool(legacy_cutoff and line_period and line_period <= legacy_cutoff)
        stored_match_status = "replacement_staged" if staged_replacement else match_status
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
            "artist_id": artist_id_for_line,
            "match_by": match_by,
            "label_percentage_applied": label_pct,
            "fee_percent_applied": 0.0,
            "exchange_rate": rate_eur_idr,
            **calc,
            "match_status": stored_match_status,
            "replacement_original_match_status": match_status if staged_replacement else None,
            "replacement_stage": staged_replacement,
            "status": "draft" if staged_replacement else ("withdrawn" if legacy_settled else "draft"),
            "legacy_settled": False if staged_replacement else legacy_settled,
            "legacy_settled_period_end": None if staged_replacement else (legacy_cutoff if legacy_settled else None),
            "legacy_settled_at": None if staged_replacement else (now_iso() if legacy_settled else None),
            "created_at": now_iso(),
        })

        if len(line_batch) >= BATCH_SIZE:
            await _flush()

    # Final flush — force progress write so the UI sees the exact totals
    # (skip the redundant else-branch: an empty _flush() still writes progress).
    await _flush(force_progress=True)

    sorted_periods = sorted(period_counts.keys())
    is_multi_period = len(sorted_periods) > 1
    # Derive display period strictly from valid `Bulan laporan` values.
    if sorted_periods:
        display_period = sorted_periods[0] if len(sorted_periods) == 1 else "multi"
    else:
        display_period = "invalid"

    # Route the final status flip through db_bg (CSOT-uncapped). Atlas can be
    # slow to ack this write while a 1M-row import is still settling indexes —
    # the 10s CSOT cap on `db` was causing imports to silently stay stuck at
    # `processing` even though all rows were inserted.
    await db_bg.royalty_imports.update_one(
        {"id": import_id},
        {"$set": {
            "period": display_period,
            "period_start": sorted_periods[0] if sorted_periods else None,
            "period_end": sorted_periods[-1] if sorted_periods else None,
            "is_multi_period": is_multi_period,
            "progress_pct": 100,
            "status": ("replacement_preview" if staged_replacement else "pending_review") if sorted_periods else "error",
            "error_message": None if sorted_periods else "Semua baris ditolak karena kolom 'Bulan laporan' kosong atau tidak valid.",
            "finished_at": now_iso(),
            "updated_at": now_iso(),
        }},
    )

    # Phase 29 — auto-sync: rebuild dashboard + analytics caches immediately
    # so Artis / Katalog / Label / Analytics pages show the new data without
    # waiting for publish or any manual tool.
    if not staged_replacement:
        _trigger_dashboard_recompute()

    final = await db_bg.royalty_imports.find_one({"id": import_id}, {"_id": 0})
    return final


async def _process_csv_import_bg(
    *, import_id: str, file_path: str, period: Optional[str],
    rate_eur_idr: float, fee_percent: float, user_id: str,
    staged_replacement: bool = False,
):
    """Background variant — catches and logs exceptions instead of letting them
    crash the event loop. Marks the import as 'error' on failure.
    """
    try:
        await _process_csv_import_inline(
            import_id=import_id, file_path=file_path, period=period,
            rate_eur_idr=rate_eur_idr, fee_percent=fee_percent,
            staged_replacement=staged_replacement,
        )
        await log_activity(
            user_id, "upload_royalty_csv_async_finished", "royalty", import_id,
        )
    except Exception as e:
        logger.exception("Background CSV import %s failed: %s", import_id, e)
        err_update = {
            "status": "error",
            "error_message": str(e)[:500],
            "finished_at": now_iso(),
            "updated_at": now_iso(),
        }
        # Try db_bg first (CSOT-uncapped); fall back to db so we always surface
        # the failure to the admin UI even if Atlas is throttling.
        try:
            await db_bg.royalty_imports.update_one({"id": import_id}, {"$set": err_update})
        except Exception:
            try:
                await db.royalty_imports.update_one({"id": import_id}, {"$set": err_update})
            except Exception as inner:
                logger.exception("Failed to record error_state for %s (both clients): %s", import_id, inner)
    finally:
        Path(file_path).unlink(missing_ok=True)


@royalty_r.get("/admin/imports")
async def admin_list_imports(user: dict = Depends(require_admin)):
    items = await db.royalty_imports.find({"replacement_stage": {"$ne": True}}, {"_id": 0}).sort("created_at", -1).to_list(500)
    # Compute live progress_pct on the fly for in-flight imports.
    for it in items:
        if it.get("status") == "processing" and it.get("total_lines"):
            it["progress_pct"] = min(99, int((it.get("processed_lines", 0) / max(it["total_lines"], 1)) * 100))
        elif it.get("status") == "publishing":
            it["progress_pct"] = it.get("publish_progress_pct") or 0
        elif it.get("status") == "receiving":
            it["progress_pct"] = it.get("receive_progress_pct") or 0
        elif it.get("status") == "deleting":
            # Surface deletion progress so admin can see movement on large imports.
            done = it.get("deletion_progress_lines", 0)
            total = it.get("total_lines") or 1
            it["progress_pct"] = min(99, int((done / max(total, 1)) * 100))
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
    elif imp.get("status") == "receiving":
        imp["progress_pct"] = imp.get("receive_progress_pct") or 0

    # Avoid repeating two multi-million-row reads every 3 seconds while the
    # receipt background job is already scanning and updating the same import.
    if imp.get("status") == "receiving":
        return {"import": imp, "lines": [], "per_label": []}

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
    # Use line's own period (supports multi-period imports); fall back to import.period
    line_period = line.get("period") or imp.get("period") or imp.get("period_start") or ""
    label_pct = float(label.get("royalty_percentage_default", 60) or 60)
    calc = calculate_line(line["revenue_eur"], 0.0, label_pct, imp["exchange_rate_eur_idr"])
    legacy_cutoff = label.get("last_withdrawn_period")
    legacy_settled = bool(legacy_cutoff and line_period and line_period <= legacy_cutoff)
    new_total_label_idr = imp["total_label_idr"] - line.get("label_idr", 0) + calc["label_idr"]
    await db.royalty_lines.update_one({"id": line_id}, {"$set": {
        "track_id": track["id"],
        "release_id": track["release_id"],
        "label_id": track["label_id"],
        "artist_id": track.get("artist_id"),
        "label_percentage_applied": label_pct,
        "fee_percent_applied": 0.0,
        **calc,
        "match_status": "manually_matched",
        "status": "withdrawn" if legacy_settled else "draft",
        "legacy_settled": legacy_settled,
        "legacy_settled_period_end": legacy_cutoff if legacy_settled else None,
        "legacy_settled_at": now_iso() if legacy_settled else None,
    }})
    await db.royalty_imports.update_one({"id": import_id}, {
        "$inc": {"matched_lines": 1, "unmatched_lines": -1 if line["match_status"] == "unmatched" else 0},
        "$set": {"total_label_idr": new_total_label_idr, "updated_at": now_iso()},
    })
    return await db.royalty_lines.find_one({"id": line_id}, {"_id": 0})


@royalty_r.post("/admin/recalculate-unwithdrawn")
async def admin_recalculate_all_unwithdrawn(user: dict = Depends(require_admin)):
    """Queue a no-fee recalculation for every unsettled royalty line.

    This is the one-time production migration path for historical CSV data;
    source revenue and exchange rates are reused, so no CSV re-upload is needed.
    """
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    await close_stale_recalculation_jobs()
    running = await db.migrate_jobs.find_one({
        "kind": "recalculate_all_unwithdrawn",
        "status": {"$in": ["queued", "processing"]},
    }, {"_id": 0, "id": 1, "status": 1})
    if running:
        return {"ok": True, "job_id": running["id"], "status": running["status"], "already_running": True}
    job_id = new_id()
    await db.migrate_jobs.insert_one({
        "id": job_id,
        "kind": "recalculate_all_unwithdrawn",
        "status": "queued",
        "submitted_by": user["id"],
        "submitted_at": now_iso(),
        "updated_at": now_iso(),
        "progress_labels_done": 0,
        "progress_labels_total": 0,
    })
    import asyncio
    asyncio.create_task(run_global_recalculation_job(job_id=job_id))
    await log_activity(user["id"], "recalculate_all_unwithdrawn", "royalty", job_id)
    return {"ok": True, "job_id": job_id, "status": "queued", "already_running": False}


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
            {"$match": {
                "import_id": import_id,
                "match_status": {"$in": ["matched", "manually_matched"]},
                "status": {"$in": ["draft", "pending"]},
                "legacy_settled": {"$ne": True},
            }},
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
            "status": "draft",
            "legacy_settled": {"$ne": True},
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
            schedule_dashboard_recompute()
        except Exception:
            pass

        # Best-effort: rebuild the monthly_analytics cache so the dashboard's
        # charts reflect the just-published data. Heavy aggregate (1M+ rows on
        # production) — fire-and-forget so this BG task can finish.
        try:
            from routes.admin_analytics import schedule_monthly_analytics_recompute  # lazy
            import asyncio as _aio2
            _aio2.create_task(schedule_monthly_analytics_recompute(reason=f"publish:{import_id}"))
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
    """Queue pending → available processing and return immediately."""
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    imp = await db.royalty_imports.find_one({"id": import_id}, {"_id": 0})
    if not imp:
        raise HTTPException(status_code=404, detail="Import tidak ditemukan")
    if imp.get("status") == "dana_received":
        return imp
    if imp.get("status") == "receiving":
        return imp
    if imp.get("status") not in ("published", "receive_error"):
        raise HTTPException(status_code=400, detail="Import harus berstatus Published terlebih dahulu")

    # Legacy production data can have dana_received_at set while the status is
    # still `published`. Reconcile completed rows instead of permanently
    # rejecting the action based on the stale timestamp.
    if imp.get("dana_received_at"):
        pending_lines = await db_bg.royalty_lines.count_documents({
            "import_id": import_id, "status": {"$in": ["draft", "pending"]},
        })
        if pending_lines == 0:
            reconciled_at = now_iso()
            await db_bg.royalty_imports.update_one(
                {"id": import_id, "status": {"$in": ["published", "receive_error"]}},
                {"$set": {
                    "status": "dana_received",
                    "receive_progress_pct": 100,
                    "status_reconciled_at": reconciled_at,
                    "updated_at": reconciled_at,
                }},
            )
            await log_activity(
                user["id"], "reconcile_dana_received_status", "royalty", import_id,
                after={"reason": "timestamp_present_no_draft_or_pending_lines"},
            )
            return await db_bg.royalty_imports.find_one({"id": import_id}, {"_id": 0})
        await db_bg.royalty_imports.update_one(
            {"id": import_id},
            {"$unset": {"dana_received_at": ""}, "$set": {"updated_at": now_iso()}},
        )

    queued_at = now_iso()
    queued = await db.royalty_imports.update_one(
        {"id": import_id, "status": {"$in": ["published", "receive_error"]}},
        {"$set": {
            "status": "receiving",
            "receive_progress_pct": 0,
            "receive_started_at": queued_at,
            "error_message": None,
            "updated_at": queued_at,
        }},
    )
    if queued.modified_count == 0:
        current = await db.royalty_imports.find_one({"id": import_id}, {"_id": 0})
        if current and current.get("status") == "receiving":
            return current
        raise HTTPException(status_code=409, detail="Status import berubah. Muat ulang lalu coba kembali.")

    import asyncio
    asyncio.create_task(_mark_dana_received_bg(import_id=import_id, user_id=user["id"]))
    return await db.royalty_imports.find_one({"id": import_id}, {"_id": 0})


async def _mark_dana_received_bg(*, import_id: str, user_id: str):
    """Move a published import to available without holding an HTTP request.

    A per-label marker makes balance changes idempotent even if the pod stops
    between the balance update and ledger insertion.
    """
    try:
        imp = await db_bg.royalty_imports.find_one({"id": import_id}, {"_id": 0})
        if not imp:
            return
        period_label = (
            f"{imp.get('period_start')} s/d {imp.get('period_end')}"
            if imp.get("is_multi_period") else imp.get("period", "")
        )
        pipeline = [
            {"$match": {
                "import_id": import_id,
                "status": {"$in": ["draft", "pending"]},
                "legacy_settled": {"$ne": True},
            }},
            {"$group": {
                "_id": {"label_id": "$label_id", "period": "$period"},
                "total_idr": {"$sum": "$label_idr"},
            }},
        ]
        period_rows = [
            row async for row in db_bg.royalty_lines.aggregate(pipeline, allowDiskUse=True)
            if (row.get("_id") or {}).get("label_id")
        ]
        label_ids = list({row["_id"]["label_id"] for row in period_rows})
        labels = await db_bg.labels.find(
            {"id": {"$in": label_ids}},
            {"_id": 0, "id": 1, "last_withdrawn_period": 1},
        ).to_list(len(label_ids) or 1)
        cutoff_by_label = {label["id"]: label.get("last_withdrawn_period") for label in labels}
        active_withdraw_ids = set(await db_bg.withdraw_requests.distinct("label_id", {
            "label_id": {"$in": label_ids},
            "status": {"$in": ["requested", "approved"]},
            "legacy_import": {"$ne": True},
        }))
        if active_withdraw_ids:
            raise RuntimeError(
                f"Penerimaan dana diblokir: {len(active_withdraw_ids)} label sedang memiliki withdraw aktif"
            )

        eligible_totals: Dict[str, int] = {}
        historical_labels = set()
        for row in period_rows:
            label_id = row["_id"]["label_id"]
            period = row["_id"].get("period")
            cutoff = cutoff_by_label.get(label_id)
            if cutoff and period and period <= cutoff:
                historical_labels.add(label_id)
                continue
            eligible_totals[label_id] = eligible_totals.get(label_id, 0) + int(row.get("total_idr") or 0)

        # Any historical pending rows are already covered by the label's FIFO
        # cutoff and must never be moved back into available balance.
        historical_flipped = 0
        for label_id in historical_labels:
            cutoff = cutoff_by_label[label_id]
            result = await db_bg.royalty_lines.update_many(
                {
                    "import_id": import_id,
                    "label_id": label_id,
                    "status": {"$in": ["draft", "pending"]},
                    "legacy_settled": {"$ne": True},
                    "period": {"$lte": cutoff},
                },
                {"$set": {
                    "status": "withdrawn",
                    "settled_by_period_cutoff": True,
                    "settled_by_period_cutoff_at": now_iso(),
                }},
            )
            historical_flipped += result.modified_count

        per_label = [{"_id": label_id, "total_idr": total} for label_id, total in eligible_totals.items()]
        total_labels = max(len(per_label), 1)
        await db_bg.royalty_imports.update_one(
            {"id": import_id}, {"$set": {"receive_progress_pct": 5, "updated_at": now_iso()}},
        )

        for index, row in enumerate(per_label):
            label_id = row["_id"]
            amount_idr = int(row.get("total_idr") or 0)
            existing_tx = await db_bg.balance_transactions.find_one({
                "label_id": label_id,
                "type": "royalty_available",
                "reference_type": "royalty_import",
                "reference_id": import_id,
            }, {"_id": 0, "id": 1})
            if existing_tx:
                await db_bg.labels.update_one(
                    {"id": label_id},
                    {"$addToSet": {"royalty_received_import_ids": import_id}, "$set": {"updated_at": now_iso()}},
                )
            else:
                await db_bg.labels.update_one(
                    {"id": label_id, "royalty_received_import_ids": {"$ne": import_id}},
                    {
                        "$inc": {
                            "balance_pending_idr": -amount_idr,
                            "balance_available_idr": amount_idr,
                        },
                        "$addToSet": {"royalty_received_import_ids": import_id},
                        "$set": {"updated_at": now_iso()},
                    },
                )
                await db_bg.balance_transactions.update_one(
                    {"id": f"royalty-available:{import_id}:{label_id}"},
                    {"$setOnInsert": {
                        "id": f"royalty-available:{import_id}:{label_id}",
                        "label_id": label_id,
                        "type": "royalty_available",
                        "amount_idr": amount_idr,
                        "reference_type": "royalty_import",
                        "reference_id": import_id,
                        "description": f"Dana royalti periode {period_label} diterima — saldo tersedia",
                        "created_at": now_iso(),
                    }},
                    upsert=True,
                )
            if (index + 1) % 5 == 0 or index == len(per_label) - 1:
                progress = 5 + int((index + 1) / total_labels * 70)
                await db_bg.royalty_imports.update_one(
                    {"id": import_id},
                    {"$set": {"receive_progress_pct": min(progress, 75), "updated_at": now_iso()}},
                )

        pending_filter = {
            "import_id": import_id,
            "status": {"$in": ["draft", "pending"]},
            "legacy_settled": {"$ne": True},
        }
        total_pending = await db_bg.royalty_lines.count_documents(pending_filter)
        chunk_size = 2000
        last_oid = None
        total_flipped = 0
        while True:
            query: Dict[str, Any] = dict(pending_filter)
            if last_oid is not None:
                query["_id"] = {"$gt": last_oid}
            batch = await db_bg.royalty_lines.find(query, {"_id": 1}).sort("_id", 1).limit(chunk_size).to_list(chunk_size)
            if not batch:
                break
            object_ids = [doc["_id"] for doc in batch]
            last_oid = object_ids[-1]
            await db_bg.royalty_lines.update_many(
                {"_id": {"$in": object_ids}}, {"$set": {"status": "available"}},
            )
            total_flipped += len(object_ids)
            line_progress = 75 + int(total_flipped / max(total_pending, 1) * 20)
            await db_bg.royalty_imports.update_one(
                {"id": import_id},
                {"$set": {"receive_progress_pct": min(line_progress, 95), "updated_at": now_iso()}},
            )

        finished_at = now_iso()
        await db_bg.royalty_imports.update_one(
            {"id": import_id},
            {"$set": {
                "status": "dana_received",
                "dana_received_at": finished_at,
                "receive_progress_pct": 100,
                "error_message": None,
                "updated_at": finished_at,
            }},
        )
        await log_activity(user_id, "mark_dana_received", "royalty", import_id, after={
            "lines_flipped": total_flipped,
            "historical_lines_settled": historical_flipped,
        })
        logger.info(
            "[MARK_DANA BG] %s complete — %d lines available, %d historical settled",
            import_id, total_flipped, historical_flipped,
        )
    except Exception as exc:
        logger.exception("[MARK_DANA BG] %s failed: %s", import_id, exc)
        await db_bg.royalty_imports.update_one(
            {"id": import_id},
            {"$set": {
                "status": "receive_error",
                "error_message": f"Penerimaan dana gagal: {type(exc).__name__}: {str(exc)[:300]}",
                "updated_at": now_iso(),
            }},
        )


@royalty_r.post("/admin/reset-demo-data")
async def admin_reset_demo_royalty_data(
    confirm: str = Form(...),
    user: dict = Depends(require_admin),
):
    """⚠️ DANGER ZONE — Wipe all royalty data (imports + lines + balance txns +
    auto-created labels/releases/tracks/artists) and reset label balances.

    Phase 29.1 — async background job. `delete_many({})` on 3M+ royalty_lines
    through the CSOT-capped `db` client fails on production. Now returns a
    `job_id` immediately; the wipe uses `drop_collection` via `db_bg`, clears
    dashboard caches, then rebuilds indexes. Poll
    `GET /api/admin/migrate/jobs/{job_id}`. Requires confirm='RESET'.
    """
    if user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Hanya Super Admin")
    if confirm != "RESET":
        raise HTTPException(status_code=400, detail="Konfirmasi tidak cocok. Ketik 'RESET' untuk melanjutkan.")

    job_id = new_id()
    await db.migrate_jobs.insert_one({
        "id": job_id,
        "kind": "reset_royalty_data",
        "status": "queued",
        "submitted_by": user["id"],
        "submitted_at": now_iso(),
        "updated_at": now_iso(),
    })
    import asyncio as _aio
    _aio.create_task(_reset_royalty_data_bg(job_id=job_id, user_id=user["id"]))
    return {"ok": True, "job_id": job_id, "status": "queued", "kind": "reset_royalty_data"}


async def _reset_royalty_data_bg(*, job_id: str, user_id: str):
    import asyncio as _aio

    async def _prog(phase: str):
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "running", "phase": phase, "updated_at": now_iso()}},
        )

    report: Dict[str, Any] = {}
    try:
        # 1) Drop royalty collections — instant regardless of row count
        await _prog("dropping_royalty_lines")
        try:
            report["lines_deleted"] = await db_bg.royalty_lines.estimated_document_count()
        except Exception:
            report["lines_deleted"] = 0
        await db_bg.drop_collection("royalty_lines")

        await _prog("dropping_royalty_imports")
        try:
            report["imports_deleted"] = await db_bg.royalty_imports.estimated_document_count()
        except Exception:
            report["imports_deleted"] = 0
        await db_bg.drop_collection("royalty_imports")

        # 2) Royalty balance transactions + auto-created entities from CSV imports
        await _prog("cleaning_entities")
        report["transactions_deleted"] = (await db_bg.balance_transactions.delete_many(
            {"type": {"$in": ["royalty_pending", "royalty_available"]}})).deleted_count
        report["auto_labels_deleted"] = (await db_bg.labels.delete_many(
            {"auto_created_from": {"$ne": None}})).deleted_count
        report["auto_releases_deleted"] = (await db_bg.releases.delete_many(
            {"auto_created_from": {"$ne": None}})).deleted_count
        report["auto_tracks_deleted"] = (await db_bg.tracks.delete_many(
            {"auto_created_from": {"$ne": None}})).deleted_count
        report["auto_artists_deleted"] = (await db_bg.artists.delete_many(
            {"auto_created_from": {"$ne": None}})).deleted_count

        # 3) Reset remaining label balances
        await _prog("resetting_balances")
        report["labels_reset"] = (await db_bg.labels.update_many({}, {"$set": {
            "balance_pending_idr": 0,
            "balance_available_idr": 0,
            "updated_at": now_iso(),
        }})).modified_count

        # 4) Clear dashboard/analytics caches so old totals disappear
        await _prog("clearing_caches")
        await db_bg.drop_collection("monthly_analytics")
        await db_bg.metrics_cache.delete_many({"_id": "dashboard_revenue"})
        try:
            reset_dashboard_revenue()
        except Exception:
            pass

        # 5) Local CSV staging files
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
        report["csv_files_deleted"] = deleted_files

        # 6) R2 csv/ staging objects (best-effort, blocking boto3 → thread)
        try:
            report["r2_csv_deleted"] = await _aio.to_thread(_wipe_r2_prefix_sync, "csv/")
        except Exception as e:
            report["r2_csv_error"] = str(e)

        # 7) Re-create indexes dropped along with the collections
        await _prog("reseeding_indexes")
        try:
            from .seed import seed_indexes_and_admins
            await seed_indexes_and_admins()
        except Exception as e:
            report["reseed_error"] = str(e)

        await log_activity(user_id, "reset_demo_royalty", "system", "all", after=report)
        _trigger_dashboard_recompute()
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "done", "phase": "done", "result": report,
                      "finished_at": now_iso(), "updated_at": now_iso()}},
        )
    except Exception as e:
        logger.exception("[RESET ROYALTY] FAILED: %s", e)
        try:
            await db_bg.migrate_jobs.update_one(
                {"id": job_id},
                {"$set": {"status": "error", "error_message": f"{type(e).__name__}: {str(e)[:300]}",
                          "result": report, "updated_at": now_iso()}},
            )
        except Exception:
            pass


def _wipe_r2_prefix_sync(prefix: str) -> int:
    """Blocking R2 prefix wipe — run via asyncio.to_thread."""
    import storage_service
    if not storage_service.is_configured():
        return 0
    client = storage_service._client()
    bucket = storage_service.R2_BUCKET
    deleted = 0
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        objs = page.get("Contents") or []
        if not objs:
            continue
        client.delete_objects(Bucket=bucket, Delete={"Objects": [{"Key": o["Key"]} for o in objs]})
        deleted += len(objs)
    return deleted


# -------- LABEL royalty endpoints --------
@royalty_r.get("/months")
async def label_royalty_months(user: dict = Depends(get_current_user)):
    """List periods that have published royalty data visible to the current user."""
    if user["role"] == LABEL_ROLE:
        label = await get_label_by_user(user)
        filt = {"label_id": label["id"], "status": {"$in": ["pending", "available"]}, "legacy_settled": {"$ne": True}}
    elif user["role"] == ARTIST_ROLE:
        filt = {"artist_id": user["id"], "status": {"$in": ["pending", "available"]}, "legacy_settled": {"$ne": True}}
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
        base = {"label_id": label["id"], "legacy_settled": {"$ne": True}}
    elif user["role"] == ARTIST_ROLE:
        base = {"artist_id": user["id"], "legacy_settled": {"$ne": True}}
    else:
        raise HTTPException(status_code=403, detail="Tidak diperbolehkan")
    if period:
        base["period"] = period

    pipeline = [
        {"$match": {**base, "status": {"$in": ["pending", "available"]}}},
        {"$group": {
            "_id": None,
            "total_idr": {"$sum": "$label_idr"},
            "total_streams": {"$sum": "$quantity"},
            "total_lines": {"$sum": 1},
        }},
    ]
    summary = {"total_idr": 0, "total_streams": 0, "total_lines": 0}
    async for row in db_bg.royalty_lines.aggregate(pipeline, allowDiskUse=True):
        summary = {"total_idr": row["total_idr"], "total_streams": row["total_streams"], "total_lines": row["total_lines"]}

    # per-platform
    by_platform = []
    async for row in db_bg.royalty_lines.aggregate([
        {"$match": {**base, "status": {"$in": ["pending", "available"]}}},
        {"$group": {"_id": "$platform", "total_idr": {"$sum": "$label_idr"}, "streams": {"$sum": "$quantity"}}},
        {"$sort": {"total_idr": -1}},
    ], allowDiskUse=True):
        by_platform.append({"platform": row["_id"] or "Unknown", "total_idr": row["total_idr"], "streams": row["streams"]})

    by_country = []
    async for row in db_bg.royalty_lines.aggregate([
        {"$match": {**base, "status": {"$in": ["pending", "available"]}}},
        {"$group": {"_id": "$country", "total_idr": {"$sum": "$label_idr"}}},
        {"$sort": {"total_idr": -1}},
        {"$limit": 10},
    ], allowDiskUse=True):
        by_country.append({"country": row["_id"] or "Unknown", "total_idr": row["total_idr"]})

    by_track = []
    async for row in db_bg.royalty_lines.aggregate([
        {"$match": {**base, "status": {"$in": ["pending", "available"]}}},
        {"$group": {"_id": {"track_id": "$track_id", "title": "$track_title_raw"}, "total_idr": {"$sum": "$label_idr"}, "streams": {"$sum": "$quantity"}}},
        {"$sort": {"total_idr": -1}},
        {"$limit": 15},
    ], allowDiskUse=True):
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
    filt: Dict[str, Any] = {"status": {"$in": ["pending", "available"]}, "legacy_settled": {"$ne": True}}
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
    filt: Dict[str, Any] = {"status": {"$in": ["pending", "available"]}, "legacy_settled": {"$ne": True}}
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
    repair_source = imp.get("repair_source") or {}
    r2_key = repair_source.get("object_key") or imp.get("r2_key")
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

    Heavy deletes (royalty_lines may be 1M+ rows for a stuck import) go
    through db_bg to avoid the 10s CSOT timeout that was causing Retry to
    silently hang in production.

    - Delete royalty_lines tied to this import
    - Delete auto-created labels/releases/tracks (only ones with auto_created_from=this import)
    - Reset counters on the import doc
    """
    # royalty_lines may be 1M+ rows — must use db_bg + chunked deletes by _id
    # to avoid both CSOT timeout AND the maxTimeMS server-side cap.
    CHUNK = 5000
    while True:
        batch = await db_bg.royalty_lines.find(
            {"import_id": import_id}, {"_id": 1},
        ).limit(CHUNK).to_list(CHUNK)
        if not batch:
            break
        oids = [d["_id"] for d in batch]
        await db_bg.royalty_lines.delete_many({"_id": {"$in": oids}})
    await db_bg.labels.delete_many({"auto_created_from": import_id})
    await db_bg.releases.delete_many({"auto_created_from": import_id})
    await db_bg.tracks.delete_many({"auto_created_from": import_id})
    await db_bg.artists.delete_many({"auto_created_from": import_id})
    await db_bg.royalty_imports.update_one(
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
            "auto_created_artists": 0,
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


@royalty_r.post("/admin/imports/{import_id}/repair-reporting-period")
async def admin_repair_reporting_period(import_id: str, user: dict = Depends(require_admin)):
    """Re-read the retained source CSV and repair periods from `Bulan laporan`.

    The job validates that every source row has a valid reporting month and
    that the source-row count exactly matches stored lines before changing any
    data. Amounts, balances, and line statuses are untouched.
    """
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    imp = await db.royalty_imports.find_one({"id": import_id}, {"_id": 0})
    if not imp:
        raise HTTPException(status_code=404, detail="Import tidak ditemukan")
    if imp.get("status") in ("awaiting_upload", "processing", "publishing", "receiving", "deleting"):
        raise HTTPException(status_code=409, detail="Tunggu proses import aktif selesai sebelum memperbaiki periode")
    if imp.get("period_repair_status") == "processing" and imp.get("period_repair_job_id"):
        return {
            "ok": True,
            "job_id": imp["period_repair_job_id"],
            "status": "processing",
            "already_running": True,
        }

    job_id = new_id()
    started_at = now_iso()
    await db_bg.migrate_jobs.insert_one({
        "id": job_id,
        "kind": "repair_reporting_period",
        "status": "queued",
        "import_id": import_id,
        "submitted_by": user["id"],
        "submitted_at": started_at,
        "updated_at": started_at,
        "progress_phase": "queued",
        "progress_rows_done": 0,
        "progress_rows_total": 0,
    })
    await db_bg.royalty_imports.update_one(
        {"id": import_id},
        {"$set": {
            "period_repair_status": "processing",
            "period_repair_job_id": job_id,
            "period_repair_progress_pct": 0,
            "period_repair_error": None,
            "updated_at": started_at,
        }},
    )
    import asyncio
    asyncio.create_task(_repair_reporting_period_bg(
        import_id=import_id, job_id=job_id, user_id=user["id"],
    ))
    return {"ok": True, "job_id": job_id, "status": "queued", "already_running": False}


@royalty_r.post("/admin/imports/{import_id}/repair-source/initiate")
async def admin_initiate_repair_source_upload(
    import_id: str,
    body: RepairSourceInitiateIn,
    user: dict = Depends(require_admin),
):
    """Issue a short-lived direct-to-R2 URL for a missing original CSV."""
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    imp = await db.royalty_imports.find_one({"id": import_id}, {"_id": 0, "id": 1, "status": 1})
    if not imp:
        raise HTTPException(status_code=404, detail="Import tidak ditemukan")
    if imp.get("status") in ("awaiting_upload", "processing", "publishing", "receiving", "deleting"):
        raise HTTPException(status_code=409, detail="Tunggu proses import aktif selesai")
    filename = body.filename.strip()
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File sumber wajib berformat .csv")
    if not storage_service.is_configured():
        raise HTTPException(status_code=500, detail="Cloud storage belum dikonfigurasi")

    upload_id = new_id()
    object_key = f"csv-repair/{import_id}/{upload_id}.csv"
    content_type = "text/csv"
    ttl_seconds = 900
    upload_url = await storage_service.generate_presigned_put_url(
        key=object_key, content_type=content_type, ttl=ttl_seconds,
    )
    created_at = datetime.now(timezone.utc)
    expires_at = created_at + timedelta(seconds=ttl_seconds)
    await db_bg.royalty_import_repair_uploads.insert_one({
        "id": upload_id,
        "import_id": import_id,
        "object_key": object_key,
        "filename": filename,
        "expected_size": body.size_bytes,
        "content_type": content_type,
        "status": "pending",
        "created_by": user["id"],
        "created_at": created_at.isoformat(),
        "expires_at": expires_at.isoformat(),
    })
    return {
        "upload_id": upload_id,
        "upload_url": upload_url,
        "content_type": content_type,
        "expires_in": ttl_seconds,
    }


@royalty_r.post("/admin/imports/{import_id}/repair-source/finalize")
async def admin_finalize_repair_source_upload(
    import_id: str,
    body: RepairSourceFinalizeIn,
    user: dict = Depends(require_admin),
):
    """Validate the R2 object, attach it, then queue period repair."""
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    pending = await db_bg.royalty_import_repair_uploads.find_one({
        "id": body.upload_id,
        "import_id": import_id,
        "status": "pending",
    }, {"_id": 0})
    if not pending:
        raise HTTPException(status_code=404, detail="Upload sumber pengganti tidak ditemukan atau sudah difinalisasi")
    if datetime.fromisoformat(pending["expires_at"]) < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="URL upload kedaluwarsa. Minta URL baru.")

    metadata = await storage_service.head_object(key=pending["object_key"])
    if not metadata:
        raise HTTPException(status_code=400, detail="File belum berhasil di-upload ke R2")
    actual_size = int(metadata.get("ContentLength", 0))
    if actual_size != int(pending["expected_size"]):
        raise HTTPException(
            status_code=400,
            detail=f"Ukuran file R2 tidak cocok: diterima {actual_size}, seharusnya {pending['expected_size']}",
        )

    finalized_at = now_iso()
    attached = await db_bg.royalty_imports.update_one(
        {"id": import_id},
        {"$set": {
            "repair_source": {
                "object_key": pending["object_key"],
                "filename": pending["filename"],
                "size_bytes": actual_size,
                "content_type": pending["content_type"],
                "etag": metadata.get("ETag"),
                "uploaded_at": finalized_at,
                "uploaded_by": user["id"],
            },
            "period_repair_status": None,
            "period_repair_error": None,
            "updated_at": finalized_at,
        }},
    )
    if attached.matched_count != 1:
        raise HTTPException(status_code=404, detail="Import tidak ditemukan")
    await db_bg.royalty_import_repair_uploads.update_one(
        {"id": body.upload_id, "status": "pending"},
        {"$set": {"status": "finalized", "finalized_at": finalized_at}},
    )
    # Remove any stale local copy so the repair job must download the newly
    # finalized R2 replacement instead of reusing an older failed source.
    for extension in (".csv", ".csv.gz"):
        stale_path = UPLOAD_DIR / "csv" / f"{import_id}{extension}"
        stale_path.unlink(missing_ok=True)
    queued = await admin_repair_reporting_period(import_id=import_id, user=user)
    return {**queued, "upload_id": body.upload_id, "source_attached": True}


async def _recompute_import_stats_from_lines(import_id: str) -> Dict[str, Any]:
    """Recompute import-level counters from the actual royalty_lines collection.

    Used by both force-finalize and the watchdog. Returns a dict ready to be
    `$set` on the royalty_imports doc. Uses db_bg (CSOT-uncapped) because the
    aggregation may scan up to 1M rows.
    """
    pipeline = [
        {"$match": {"import_id": import_id}},
        {"$group": {
            "_id": None,
            "total_lines": {"$sum": 1},
            "matched_lines": {"$sum": {"$cond": [{"$eq": ["$match_status", "matched"]}, 1, 0]}},
            "unmatched_lines": {"$sum": {"$cond": [{"$eq": ["$match_status", "unmatched"]}, 1, 0]}},
            "total_revenue_eur": {"$sum": {"$ifNull": ["$revenue_eur", 0]}},
            "total_label_idr": {"$sum": {"$ifNull": ["$label_idr", 0]}},
        }},
    ]
    agg = await db_bg.royalty_lines.aggregate(pipeline, allowDiskUse=True).to_list(1)
    stats = agg[0] if agg else {}

    # Period breakdown
    period_pipeline = [
        {"$match": {"import_id": import_id}},
        {"$group": {"_id": "$period", "n": {"$sum": 1}}},
    ]
    period_counts: Dict[str, int] = {}
    async for r in db_bg.royalty_lines.aggregate(period_pipeline, allowDiskUse=True):
        if r["_id"]:
            period_counts[r["_id"]] = r["n"]

    sorted_periods = sorted(period_counts.keys())
    is_multi_period = len(sorted_periods) > 1

    # Auto-created entity counters (counted directly from collections)
    auto_labels_n = await db_bg.labels.count_documents({"auto_created_from": import_id})
    auto_releases_n = await db_bg.releases.count_documents({"auto_created_from": import_id})
    auto_tracks_n = await db_bg.tracks.count_documents({"auto_created_from": import_id})
    auto_artists_n = await db_bg.artists.count_documents({"auto_created_from": import_id})

    return {
        "total_lines": int(stats.get("total_lines", 0)),
        "processed_lines": int(stats.get("total_lines", 0)),
        "matched_lines": int(stats.get("matched_lines", 0)),
        "unmatched_lines": int(stats.get("unmatched_lines", 0)),
        "total_revenue_eur": round(float(stats.get("total_revenue_eur", 0)), 4),
        "total_label_idr": int(stats.get("total_label_idr", 0)),
        "period_breakdown": period_counts,
        "period_start": sorted_periods[0] if sorted_periods else None,
        "period_end": sorted_periods[-1] if sorted_periods else None,
        "is_multi_period": is_multi_period,
        "auto_created_labels": auto_labels_n,
        "auto_created_releases": auto_releases_n,
        "auto_created_tracks": auto_tracks_n,
        "auto_created_artists": auto_artists_n,
        "progress_pct": 100,
    }


async def _repair_reporting_period_bg(*, import_id: str, job_id: str, user_id: str):
    """Safely rewrite only period metadata from the retained source CSV."""
    try:
        imp = await db_bg.royalty_imports.find_one({"id": import_id}, {"_id": 0})
        if not imp:
            raise RuntimeError("Import tidak ditemukan")
        file_path = await _ensure_local_csv(imp)
        if not file_path:
            raise RuntimeError("CSV asli tidak tersedia di disk maupun R2; upload ulang diperlukan")

        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "processing", "progress_phase": "validating_source", "updated_at": now_iso()}},
        )
        headers: List[str] = []
        column_map: Optional[Dict[str, Optional[int]]] = None
        source_rows = 0
        invalid_rows = 0
        source_period_counts: Dict[str, int] = {}
        for current_headers, row in iter_csv_file(file_path):
            if row is None:
                headers = current_headers
                column_map = detect_columns(headers)
                if column_map.get("period") is None:
                    raise RuntimeError("Kolom 'Bulan laporan' tidak ditemukan di CSV asli")
                continue
            source_rows += 1
            period_value = _match_line(row, column_map, headers).get("row_period")
            if not period_value:
                invalid_rows += 1
                continue
            source_period_counts[period_value] = source_period_counts.get(period_value, 0) + 1

        stored_rows = await db_bg.royalty_lines.count_documents({"import_id": import_id})
        if invalid_rows:
            raise RuntimeError(
                f"Reparasi dibatalkan: {invalid_rows} baris memiliki Bulan laporan kosong/tidak valid. "
                "Gunakan upload ulang agar baris tersebut dapat ditolak dengan benar."
            )
        if source_rows != stored_rows:
            raise RuntimeError(
                f"Reparasi dibatalkan: jumlah baris CSV ({source_rows}) tidak sama dengan royalty_lines ({stored_rows})"
            )

        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "progress_phase": "updating_periods",
                "progress_rows_total": stored_rows,
                "source_period_breakdown": source_period_counts,
                "updated_at": now_iso(),
            }},
        )

        csv_iterator = iter(iter_csv_file(file_path))
        csv_headers, first_row = next(csv_iterator)
        if first_row is not None:
            raise RuntimeError("Header CSV tidak terbaca")
        csv_columns = detect_columns(csv_headers)
        batch_size = 5000
        last_oid = None
        updated_rows = 0
        while True:
            query: Dict[str, Any] = {"import_id": import_id}
            if last_oid is not None:
                query["_id"] = {"$gt": last_oid}
            line_batch = await db_bg.royalty_lines.find(query, {"_id": 1}).sort("_id", 1).limit(batch_size).to_list(batch_size)
            if not line_batch:
                break
            grouped_ids: Dict[str, List[Any]] = {}
            for line in line_batch:
                _, source_row = next(csv_iterator)
                period_value = _match_line(source_row, csv_columns, csv_headers)["row_period"]
                grouped_ids.setdefault(period_value, []).append(line["_id"])
            for period_value, object_ids in grouped_ids.items():
                await db_bg.royalty_lines.update_many(
                    {"_id": {"$in": object_ids}},
                    {"$set": {"period": period_value, "row_period": period_value}},
                )
            last_oid = line_batch[-1]["_id"]
            updated_rows += len(line_batch)
            progress = min(90, 10 + int(updated_rows / max(stored_rows, 1) * 80))
            await db_bg.migrate_jobs.update_one(
                {"id": job_id},
                {"$set": {"progress_rows_done": updated_rows, "progress_pct": progress, "updated_at": now_iso()}},
            )
            await db_bg.royalty_imports.update_one(
                {"id": import_id},
                {"$set": {"period_repair_progress_pct": progress, "updated_at": now_iso()}},
            )

        stats = await _recompute_import_stats_from_lines(import_id)
        sorted_periods = sorted((stats.get("period_breakdown") or {}).keys())
        display_period = sorted_periods[0] if len(sorted_periods) == 1 else "multi"
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {"progress_phase": "queueing_analytics", "progress_pct": 95, "updated_at": now_iso()}},
        )
        # Analytics rebuild is a separate resumable background job. Period
        # repair must not remain stuck/failed merely because a 3M-row rollup is
        # still running or the pod restarts during that rollup.
        from routes.admin_analytics import schedule_monthly_analytics_recompute
        analytics_meta = await schedule_monthly_analytics_recompute(
            reason=f"period_repair:{import_id}",
        )

        finished_at = now_iso()
        await db_bg.royalty_imports.update_one(
            {"id": import_id},
            {"$set": {
                **stats,
                "period": display_period,
                "period_repair_status": "done",
                "period_repair_progress_pct": 100,
                "period_repaired_at": finished_at,
                "period_repair_error": None,
                "updated_at": finished_at,
            }},
        )
        result = {
            "import_id": import_id,
            "rows_updated": updated_rows,
            "period_breakdown": stats.get("period_breakdown") or {},
            "period_start": stats.get("period_start"),
            "period_end": stats.get("period_end"),
            "analytics_rebuild_queued": True,
            "analytics_job_id": analytics_meta.get("job_id"),
        }
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "done",
                "progress_phase": "done",
                "progress_pct": 100,
                "progress_rows_done": updated_rows,
                "result": result,
                "finished_at": finished_at,
                "updated_at": finished_at,
            }},
        )
        await log_activity(user_id, "repair_reporting_period", "royalty", import_id, after=result)
    except Exception as exc:
        logger.exception("[PERIOD REPAIR] %s failed: %s", import_id, exc)
        error_message = f"{type(exc).__name__}: {str(exc)[:400]}"
        failed_at = now_iso()
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "error",
                "progress_phase": "error",
                "error_message": error_message,
                "finished_at": failed_at,
                "updated_at": failed_at,
            }},
        )
        await db_bg.royalty_imports.update_one(
            {"id": import_id},
            {"$set": {
                "period_repair_status": "error",
                "period_repair_error": error_message,
                "updated_at": failed_at,
            }},
        )


@royalty_r.post("/admin/imports/{import_id}/force-finalize")
async def admin_force_finalize_import(import_id: str, user: dict = Depends(require_admin)):
    """Force-transition a stuck `processing` import to `pending_review` by
    recomputing import-level counters from the actual royalty_lines rows.

    Use case: a Believe CSV import got 1M rows inserted but the final
    status-flip `update_one` timed out on Atlas. The import is functionally
    complete but stays at status='processing' indefinitely, blocking publish.

    Safe to run multiple times — purely a derived recompute, no row inserts.
    """
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Super Admin / Admin Finance")
    imp = await db.royalty_imports.find_one({"id": import_id})
    if not imp:
        raise HTTPException(status_code=404, detail="Import tidak ditemukan")
    if imp.get("status") not in ("processing", "error"):
        raise HTTPException(
            status_code=400,
            detail=f"Force-finalize hanya untuk status processing / error (status saat ini: {imp.get('status')}).",
        )

    stats = await _recompute_import_stats_from_lines(import_id)
    if stats["total_lines"] == 0:
        # No rows ever made it into Mongo — mark as error so admin can re-upload.
        await db_bg.royalty_imports.update_one(
            {"id": import_id},
            {"$set": {
                "status": "error",
                "error_message": "Force-finalize: 0 royalty_lines ditemukan untuk import ini. Silakan retry atau upload ulang.",
                "finished_at": now_iso(),
                "updated_at": now_iso(),
            }},
        )
        await log_activity(user["id"], "force_finalize_royalty_import_empty", "royalty", import_id, after={"total_lines": 0})
        return {"ok": False, "import_id": import_id, "status": "error", "total_lines": 0,
                "detail": "Tidak ada baris royalti — sudah ditandai sebagai error."}

    update_doc = {
        **stats,
        "status": "pending_review",
        "error_message": None,
        "finished_at": now_iso(),
        "updated_at": now_iso(),
        # Preserve display_period: if single, use it; otherwise 'multi'
        "period": (stats["period_start"] if stats["period_start"] == stats["period_end"] else "multi"),
    }
    await db_bg.royalty_imports.update_one({"id": import_id}, {"$set": update_doc})
    await log_activity(
        user["id"], "force_finalize_royalty_import", "royalty", import_id,
        after={"total_lines": stats["total_lines"], "matched_lines": stats["matched_lines"]},
    )
    _trigger_dashboard_recompute()
    return {"ok": True, "import_id": import_id, "status": "pending_review", **stats}


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

    DELETABLE_STATUSES = {"awaiting_upload", "processing", "error", "publish_error", "pending_review", "deleting"}
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

    # Flip status to 'deleting' immediately so the UI can render a spinner +
    # block other actions on this row. The heavy cleanup (1M+ row deletions)
    # runs in a background task — returns 202 to avoid the 60s ingress timeout
    # that was making the Hapus button silently fail in production.
    await db_bg.royalty_imports.update_one(
        {"id": import_id},
        {"$set": {
            "status": "deleting",
            "deletion_started_at": now_iso(),
            "deletion_started_by": user["id"],
            "previous_status": status_val,
            "updated_at": now_iso(),
        }},
    )

    import asyncio
    asyncio.create_task(_delete_import_bg(import_id=import_id, user_id=user["id"]))

    return Response(
        status_code=202,
        content='{"ok":true,"import_id":"' + import_id + '","status":"deleting","detail":"Deletion dijadwalkan di background. Refresh untuk melihat progress."}',
        media_type="application/json",
    )


async def _delete_import_bg(*, import_id: str, user_id: str):
    """Background heavy-deletion for `admin_delete_import`. Chunks the
    royalty_lines wipe through db_bg + paginated _id so we never blow past
    server-side maxTimeMS on a 1M-row delete.
    """
    try:
        imp = await db_bg.royalty_imports.find_one({"id": import_id})
        if not imp:
            logger.warning("[ROYALTY DELETE BG] %s vanished mid-delete", import_id)
            return

        # 1) Chunked delete of royalty_lines (the heavy part)
        CHUNK = 5000
        n_lines = 0
        while True:
            batch = await db_bg.royalty_lines.find(
                {"import_id": import_id}, {"_id": 1},
            ).limit(CHUNK).to_list(CHUNK)
            if not batch:
                break
            oids = [d["_id"] for d in batch]
            res = await db_bg.royalty_lines.delete_many({"_id": {"$in": oids}})
            n_lines += res.deleted_count
            # progress write so the admin sees movement
            await db_bg.royalty_imports.update_one(
                {"id": import_id},
                {"$set": {"deletion_progress_lines": n_lines, "updated_at": now_iso()}},
            )

        # 2) Auto-created entities (small filtered sets — use db_bg for consistency)
        n_labels = (await db_bg.labels.delete_many({"auto_created_from": import_id})).deleted_count
        n_releases = (await db_bg.releases.delete_many({"auto_created_from": import_id})).deleted_count
        n_tracks = (await db_bg.tracks.delete_many({"auto_created_from": import_id})).deleted_count
        n_artists = (await db_bg.artists.delete_many({"auto_created_from": import_id})).deleted_count

        # 3) R2 + local CSV cleanup (best-effort)
        r2_key = imp.get("r2_key")
        if r2_key:
            try:
                await storage_service.delete_object(key=r2_key)
            except Exception as e:
                logger.warning("[ROYALTY DELETE BG] R2 cleanup failed for %s: %s", import_id, e)
        local_csv = imp.get("file_path")
        if local_csv:
            try:
                from pathlib import Path as _P
                _P(local_csv).unlink(missing_ok=True)
            except Exception as e:
                logger.warning("[ROYALTY DELETE BG] local file cleanup failed for %s: %s", import_id, e)

        # 4) Drop the import doc itself
        await db_bg.royalty_imports.delete_one({"id": import_id})

        await log_activity(
            user_id, "delete_royalty_import", "royalty", import_id,
            before={"period": imp.get("period") or imp.get("period_start"),
                    "status": imp.get("previous_status")},
            after={"lines_deleted": n_lines, "auto_labels_deleted": n_labels,
                   "auto_releases_deleted": n_releases, "auto_tracks_deleted": n_tracks,
                   "auto_artists_deleted": n_artists},
        )

        # 5) Best-effort cache refresh
        try:
            schedule_dashboard_recompute()
        except Exception:
            pass
        try:
            from routes.admin_analytics import schedule_monthly_analytics_recompute
            import asyncio as _aio2
            _aio2.create_task(schedule_monthly_analytics_recompute(reason=f"delete_import:{import_id}"))
        except Exception:
            pass

        logger.info("[ROYALTY DELETE BG] %s complete — %d lines, %d labels, %d releases, %d tracks",
                    import_id, n_lines, n_labels, n_releases, n_tracks)
    except Exception as e:
        logger.exception("[ROYALTY DELETE BG] %s failed: %s", import_id, e)
        # Surface the failure on the import doc so the admin sees what went wrong
        try:
            await db_bg.royalty_imports.update_one(
                {"id": import_id},
                {"$set": {
                    "status": "error",
                    "error_message": f"Deletion gagal: {type(e).__name__}: {str(e)[:300]}",
                    "updated_at": now_iso(),
                }},
            )
        except Exception:
            pass


async def resume_interrupted_imports():
    """Called on backend startup. For every royalty_import stuck in 'processing',
    'publishing', or 'receiving' (hot-reload or pod restart killed the task), either:
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
             "uploaded_by": 1, "r2_key": 1, "replacement_stage": 1},
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
            staged_replacement=bool(imp.get("replacement_stage")),
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

    # 3) Resume stuck dana-received processing (idempotent per label).
    try:
        stuck_receiving = await db.royalty_imports.find(
            {"status": "receiving"},
            {"_id": 0, "id": 1, "uploaded_by": 1},
        ).to_list(100)
    except Exception as exc:
        logger.exception("resume_interrupted_imports: cannot query receiving: %s", exc)
        return
    for imp in stuck_receiving:
        asyncio.create_task(_mark_dana_received_bg(
            import_id=imp["id"],
            user_id=imp.get("uploaded_by") or "system",
        ))
        logger.info("resume_interrupted_imports: %s dana-received resumed", imp["id"])

    # 4) Reconcile legacy imports where dana_received_at exists but the status
    # remained Published. This is the exact inconsistent production state that
    # previously made the button return "Dana sudah ditandai diterima" forever.
    try:
        stale_received = await db.royalty_imports.find(
            {
                "status": {"$in": ["published", "receive_error"]},
                "dana_received_at": {"$exists": True, "$ne": None},
            },
            {"_id": 0, "id": 1, "uploaded_by": 1},
        ).to_list(500)
    except Exception as exc:
        logger.exception("resume_interrupted_imports: cannot query stale received: %s", exc)
        stale_received = []
    for imp in stale_received:
        pending_lines = await db_bg.royalty_lines.count_documents({
            "import_id": imp["id"], "status": {"$in": ["draft", "pending"]},
        })
        if pending_lines == 0:
            await db_bg.royalty_imports.update_one(
                {"id": imp["id"], "status": {"$in": ["published", "receive_error"]}},
                {"$set": {
                    "status": "dana_received",
                    "receive_progress_pct": 100,
                    "status_reconciled_at": now_iso(),
                    "updated_at": now_iso(),
                }},
            )
            logger.info("resume_interrupted_imports: %s stale received status reconciled", imp["id"])
        else:
            await db_bg.royalty_imports.update_one(
                {"id": imp["id"], "status": {"$in": ["published", "receive_error"]}},
                {
                    "$unset": {"dana_received_at": ""},
                    "$set": {
                        "status": "receiving",
                        "receive_progress_pct": 0,
                        "receive_started_at": now_iso(),
                        "updated_at": now_iso(),
                    },
                },
            )
            asyncio.create_task(_mark_dana_received_bg(
                import_id=imp["id"],
                user_id=imp.get("uploaded_by") or "system",
            ))
            logger.info("resume_interrupted_imports: %s stale received processing resumed", imp["id"])

    # 5) Resume interrupted reporting-period repairs. Re-running is safe: each
    # batch writes the same period values and validates the source first.
    try:
        stuck_repairs = await db.royalty_imports.find(
            {"period_repair_status": "processing"},
            {"_id": 0, "id": 1, "period_repair_job_id": 1, "uploaded_by": 1},
        ).to_list(100)
    except Exception as exc:
        logger.exception("resume_interrupted_imports: cannot query period repairs: %s", exc)
        stuck_repairs = []
    for imp in stuck_repairs:
        repair_job_id = imp.get("period_repair_job_id") or new_id()
        await db_bg.migrate_jobs.update_one(
            {"id": repair_job_id},
            {"$set": {
                "id": repair_job_id,
                "kind": "repair_reporting_period",
                "status": "queued",
                "import_id": imp["id"],
                "progress_phase": "resuming",
                "updated_at": now_iso(),
            }},
            upsert=True,
        )
        await db_bg.royalty_imports.update_one(
            {"id": imp["id"]},
            {"$set": {"period_repair_job_id": repair_job_id, "updated_at": now_iso()}},
        )
        asyncio.create_task(_repair_reporting_period_bg(
            import_id=imp["id"],
            job_id=repair_job_id,
            user_id=imp.get("uploaded_by") or "system",
        ))
        logger.info("resume_interrupted_imports: %s period repair resumed", imp["id"])

    # 6) Resume a killed Analytics rebuild, or automatically rebuild when the
    # source has a newer max month than the live cache.
    try:
        health = await db.rollup_health.find_one({"id": "monthly_analytics"}, {"_id": 0}) or {}
        source_latest = await db_bg.royalty_lines.find_one(
            {"period": {"$type": "string"}}, {"_id": 0, "period": 1}, sort=[("period", -1)],
        )
        cache_latest = await db_bg.monthly_analytics.find_one(
            {"dim": "total"}, {"_id": 0, "period": 1}, sort=[("period", -1)],
        )
        source_max = (source_latest or {}).get("period")
        cache_max = (cache_latest or {}).get("period")
        if health.get("running") or (source_max and source_max != cache_max):
            from routes.admin_analytics import schedule_monthly_analytics_recompute
            await schedule_monthly_analytics_recompute(
                reason="startup_resume" if health.get("running") else f"startup_period_drift:{cache_max}->{source_max}",
            )
            logger.info("resume_interrupted_imports: analytics rebuild queued (%s -> %s)", cache_max, source_max)
    except Exception as exc:
        logger.exception("resume_interrupted_imports: analytics recovery check failed: %s", exc)
