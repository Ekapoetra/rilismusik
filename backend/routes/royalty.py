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
    db, logger, UPLOAD_DIR,
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
    strip_sensitive,
)
from withdraw_utils import withdraw_window_state, jakarta_now, MIN_WITHDRAW_IDR

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
    """Upload CSV royalti Believe. Hanya menyimpan + parsing + matching. Belum mempengaruhi saldo.

    Period dapat dikosongkan — jika kolom 'Bulan Laporan' (atau period) ada di CSV,
    setiap baris akan menggunakan period-nya sendiri (multi-period import). Jika
    period diberikan, semua baris akan diforce ke period tersebut (single-month).
    """
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    # validate period if provided
    if period:
        try:
            datetime.strptime(period, "%Y-%m")
        except Exception:
            raise HTTPException(status_code=400, detail="Format period harus YYYY-MM")
    if rate_eur_idr <= 0:
        raise HTTPException(status_code=400, detail="Kurs harus > 0")

    content = await file.read()
    headers, rows = parse_csv_bytes(content)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV kosong atau tidak terbaca")
    col_idx = detect_columns(headers)
    if col_idx["revenue_eur"] is None:
        raise HTTPException(status_code=400, detail="Kolom revenue/amount tidak ditemukan di CSV")

    # If period not provided, the CSV MUST have a period column with valid values
    if not period and col_idx.get("period") is None:
        raise HTTPException(
            status_code=400,
            detail="Period tidak diberikan dan kolom 'Bulan Laporan'/period tidak ditemukan di CSV. "
                   "Tambahkan kolom atau isi field period.",
        )

    import_id = new_id()
    # save file
    target = UPLOAD_DIR / "csv" / f"{import_id}.csv"
    with open(target, "wb") as f:
        f.write(content)
    file_url = f"/api/files/csv/{import_id}.csv"

    # cache fee + percent history
    fee_settings = await db.landing_settings.find_one({"key": "pricing"})
    fee_percent = float((fee_settings or {}).get("value", {}).get("distributor_fee_percent", 5) or 5)

    # Pre-fetch all labels + tracks for matching
    all_tracks = {}
    async for t in db.tracks.find({"isrc": {"$exists": True, "$ne": None}}, {"_id": 0, "id": 1, "isrc": 1, "release_id": 1, "label_id": 1, "artist_id": 1, "track_title": 1, "artist_name": 1}):
        if t.get("isrc"):
            all_tracks[(t["isrc"] or "").strip().upper()] = t

    all_releases_by_upc = {}
    async for r in db.releases.find({"upc": {"$exists": True, "$ne": None}}, {"_id": 0, "id": 1, "upc": 1, "label_id": 1, "release_title": 1}):
        if r.get("upc"):
            all_releases_by_upc[(r["upc"] or "").strip().upper()] = r

    # Pre-fetch all labels' percentage history
    labels = {lab["id"]: lab async for lab in db.labels.find({}, {"_id": 0})}
    labels_by_name = {_norm_name(lab.get("label_name")): lab for lab in labels.values()}
    pct_history: Dict[str, List[Dict[str, Any]]] = {}
    async for h in db.royalty_percentage_history.find({}, {"_id": 0}):
        pct_history.setdefault(h["label_id"], []).append(h)

    total_revenue_eur = 0.0
    total_label_idr = 0
    matched = 0
    unmatched = 0
    invalid_period_rows = 0
    line_docs: List[Dict[str, Any]] = []
    period_counts: Dict[str, int] = {}  # period -> row count
    auto_created_labels = 0
    auto_created_releases = 0
    auto_created_tracks = 0
    new_label_docs: List[Dict[str, Any]] = []
    new_release_docs: List[Dict[str, Any]] = []
    new_track_docs: List[Dict[str, Any]] = []
    now = now_iso()

    for row in rows:
        raw = _match_line(row, col_idx, headers)
        revenue_eur = raw["revenue_eur"]
        total_revenue_eur += revenue_eur

        # Determine line period: explicit form override > row's own period
        line_period = period or raw.get("row_period")
        if not line_period:
            invalid_period_rows += 1
            continue
        period_counts[line_period] = period_counts.get(line_period, 0) + 1

        track = None
        release = None
        label_id = None
        match_by = None
        # Try ISRC match
        if raw["isrc"]:
            t = all_tracks.get(raw["isrc"].upper())
            if t:
                track = t
                label_id = t["label_id"]
                match_by = "isrc"
        # Try UPC match
        if not label_id and raw["upc"]:
            r = all_releases_by_upc.get(raw["upc"].upper())
            if r:
                release = r
                label_id = r["label_id"]
                match_by = "upc"
        # Fallback: fuzzy match by label name
        if not label_id and raw["label_name"]:
            lab = labels_by_name.get(_norm_name(raw["label_name"]))
            if lab:
                label_id = lab["id"]
                match_by = "label_name"

        # ---- Auto-create legacy entities if still unmatched ----
        # We create a placeholder Label (legacy_unclaimed) when CSV mentions a brand
        # new label_name. If ISRC is present, we also create a placeholder Release+Track.
        # This lets admin "Buatkan Akun" later for the label and see the catalog populated.
        if not label_id and raw["label_name"]:
            new_label_id = new_id()
            new_label = {
                "id": new_label_id,
                "user_id": None,
                "label_name": raw["label_name"].strip(),
                "pic_name": None,
                "email": None,
                "whatsapp": None,
                "address": None,
                "city": None,
                "country": "Indonesia",
                "label_type": "label",
                "royalty_percentage_default": 60.0,
                "payment_type": "pay_per_release",
                "subscription_status": "inactive",
                "subscription_expires_at": None,
                "contract_status": "active",
                "account_status": "legacy_unclaimed",
                "bank_verified": False,
                "blacklisted": False,
                "balance_available_idr": 0,
                "balance_pending_idr": 0,
                "balance_withdraw_requested_idr": 0,
                "mda_accepted_at": None,
                "legacy_import": True,
                "auto_created_from": import_id,
                "created_at": now,
                "updated_at": now,
            }
            new_label_docs.append(new_label)
            labels[new_label_id] = new_label
            labels_by_name[_norm_name(new_label["label_name"])] = new_label
            label_id = new_label_id
            match_by = "auto_created_label"
            auto_created_labels += 1

        if label_id and raw["isrc"] and not track:
            # Auto-create release + track (placeholder for legacy catalog)
            new_release_id = release["id"] if release else new_id()
            if not release:
                new_release = {
                    "id": new_release_id,
                    "label_id": label_id,
                    "release_title": raw.get("release_title") or "Legacy Release",
                    "primary_artist": raw.get("artist_name") or "Unknown",
                    "isrc_release": None,
                    "upc": raw["upc"],
                    "release_type": "single",
                    "release_date": (line_period + "-01") if line_period else "2021-01-01",
                    "status": "live",
                    "cover_url": None,
                    "imported_legacy": True,
                    "auto_created_from": import_id,
                    "created_at": now,
                    "updated_at": now,
                }
                new_release_docs.append(new_release)
                auto_created_releases += 1
                if raw["upc"]:
                    all_releases_by_upc[raw["upc"].upper()] = new_release
            new_track = {
                "id": new_id(),
                "release_id": new_release_id,
                "label_id": label_id,
                "artist_id": None,
                "track_title": raw.get("track_title") or "Legacy Track",
                "artist_name": raw.get("artist_name") or "Unknown",
                "isrc": raw["isrc"],
                "duration_sec": None,
                "composer": None,
                "audio_url": None,
                "imported_legacy": True,
                "auto_created_from": import_id,
                "created_at": now,
                "updated_at": now,
            }
            new_track_docs.append(new_track)
            all_tracks[raw["isrc"].upper()] = new_track
            track = new_track
            auto_created_tracks += 1

        match_status = "matched" if label_id else "unmatched"
        if match_status == "matched":
            matched += 1
            label = labels.get(label_id, {})
            default_pct = float(label.get("royalty_percentage_default", 60) or 60)
            history = pct_history.get(label_id, [])
            label_pct = label_percentage_at(history, default_pct, line_period)
            calc = calculate_line(revenue_eur, fee_percent, label_pct, rate_eur_idr)
            total_label_idr += calc["label_idr"]
        else:
            unmatched += 1
            label_pct = 0.0
            calc = calculate_line(revenue_eur, fee_percent, 0.0, rate_eur_idr)

        line_docs.append({
            "id": new_id(),
            "import_id": import_id,
            "period": line_period,
            "isrc": raw["isrc"],
            "upc": raw["upc"],
            "track_title_raw": raw["track_title"],
            "artist_name_raw": raw["artist_name"],
            "release_title_raw": raw["release_title"],
            "label_name_raw": raw["label_name"],
            "platform": raw["platform"],
            "country": raw["country"],
            "quantity": raw["quantity"],
            "revenue_eur": revenue_eur,
            "sales_type": raw.get("sales_type"),
            "subscription_type": raw.get("subscription_type"),
            "row_period": raw.get("row_period"),
            # admin-only sensitive fields:
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

    if line_docs:
        await db.royalty_lines.insert_many(line_docs)
    if new_label_docs:
        for k in range(0, len(new_label_docs), 1000):
            await db.labels.insert_many(new_label_docs[k:k + 1000])
    if new_release_docs:
        for k in range(0, len(new_release_docs), 1000):
            await db.releases.insert_many(new_release_docs[k:k + 1000])
    if new_track_docs:
        for k in range(0, len(new_track_docs), 1000):
            await db.tracks.insert_many(new_track_docs[k:k + 1000])

    # Determine aggregate period info
    sorted_periods = sorted(period_counts.keys())
    is_multi_period = len(sorted_periods) > 1
    display_period = period if period else (sorted_periods[0] if len(sorted_periods) == 1 else "multi")

    import_doc = {
        "id": import_id,
        "period": display_period,
        "period_start": sorted_periods[0] if sorted_periods else (period or None),
        "period_end": sorted_periods[-1] if sorted_periods else (period or None),
        "period_breakdown": period_counts,
        "is_multi_period": is_multi_period,
        "source": "believe",
        "filename": file.filename,
        "file_url": file_url,
        "exchange_rate_eur_idr": rate_eur_idr,
        "fee_percent": fee_percent,
        "total_lines": len(line_docs),
        "matched_lines": matched,
        "unmatched_lines": unmatched,
        "invalid_period_rows": invalid_period_rows,
        "auto_created_labels": auto_created_labels,
        "auto_created_releases": auto_created_releases,
        "auto_created_tracks": auto_created_tracks,
        "total_revenue_eur": round(total_revenue_eur, 4),
        "total_label_idr": total_label_idr,
        "status": "pending_review",
        "dana_received_at": None,
        "published_at": None,
        "uploaded_by": user["id"],
        "note": note,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.royalty_imports.insert_one(import_doc)
    await log_activity(
        user["id"], "upload_royalty_csv", "royalty", import_id,
        after={
            "period": display_period, "matched": matched, "unmatched": unmatched,
            "multi_period": is_multi_period,
            "auto_labels": auto_created_labels,
            "auto_releases": auto_created_releases,
            "auto_tracks": auto_created_tracks,
        },
    )
    import_doc.pop("_id", None)
    return import_doc


@royalty_r.get("/admin/imports")
async def admin_list_imports(user: dict = Depends(require_admin)):
    items = await db.royalty_imports.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return items


@royalty_r.get("/admin/imports/{import_id}")
async def admin_get_import(import_id: str, user: dict = Depends(require_admin)):
    imp = await db.royalty_imports.find_one({"id": import_id}, {"_id": 0})
    if not imp:
        raise HTTPException(status_code=404, detail="Import tidak ditemukan")
    lines = await db.royalty_lines.find({"import_id": import_id}, {"_id": 0}).sort("revenue_eur", -1).limit(500).to_list(500)

    # per-label breakdown
    pipeline = [
        {"$match": {"import_id": import_id, "label_id": {"$ne": None}}},
        {"$group": {"_id": "$label_id", "total_idr": {"$sum": "$label_idr"}, "total_eur": {"$sum": "$revenue_eur"}, "lines": {"$sum": 1}}},
        {"$sort": {"total_idr": -1}},
    ]
    per_label = []
    async for r in db.royalty_lines.aggregate(pipeline):
        label = await db.labels.find_one({"id": r["_id"]}, {"_id": 0, "label_name": 1, "id": 1})
        per_label.append({**r, "label": label})

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
    """Publish CSV → moves all matched lines to status=pending and accumulates to label.balance_pending_idr."""
    if user["role"] not in ("super_admin", "admin_finance"):
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")
    imp = await db.royalty_imports.find_one({"id": import_id})
    if not imp:
        raise HTTPException(status_code=404, detail="Import tidak ditemukan")
    if imp["status"] != "pending_review":
        raise HTTPException(status_code=400, detail="Import sudah dipublish atau status tidak valid")

    # Aggregate per label & notify
    pipeline = [
        {"$match": {"import_id": import_id, "match_status": {"$in": ["matched", "manually_matched"]}}},
        {"$group": {"_id": "$label_id", "total_idr": {"$sum": "$label_idr"}}},
    ]
    per_label = []
    period_label = (
        f"{imp.get('period_start')} s/d {imp.get('period_end')}"
        if imp.get("is_multi_period") else imp.get("period", "")
    )
    async for r in db.royalty_lines.aggregate(pipeline):
        per_label.append(r)
        await db.labels.update_one({"id": r["_id"]}, {"$inc": {"balance_pending_idr": int(r["total_idr"])}, "$set": {"updated_at": now_iso()}})
        await db.balance_transactions.insert_one({
            "id": new_id(),
            "label_id": r["_id"],
            "type": "royalty_pending",
            "amount_idr": int(r["total_idr"]),
            "reference_type": "royalty_import",
            "reference_id": import_id,
            "description": f"Royalti periode {period_label} ke saldo pending",
            "created_at": now_iso(),
        })

    await db.royalty_lines.update_many(
        {"import_id": import_id, "match_status": {"$in": ["matched", "manually_matched"]}},
        {"$set": {"status": "pending"}},
    )
    await db.royalty_imports.update_one({"id": import_id}, {"$set": {"status": "published", "published_at": now_iso(), "updated_at": now_iso()}})
    await log_activity(user["id"], "publish_royalty", "royalty", import_id)
    # Notify each label with a personalized amount
    for r in per_label:
        user_ids = await label_user_ids(r["_id"])
        amt = f"Rp {int(r['total_idr']):,}".replace(",", ".")
        await notify_many(
            user_ids, "royalty_published",
            f"Royalti periode {period_label} terbit",
            f"{amt} masuk ke saldo pending. Lihat detail di dashboard.",
            "/label/royalty", {"period": imp.get("period"), "import_id": import_id},
        )
    return await db.royalty_imports.find_one({"id": import_id}, {"_id": 0})


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
    async for r in db.royalty_lines.aggregate(pipeline):
        await db.labels.update_one({"id": r["_id"]}, {"$inc": {
            "balance_pending_idr": -int(r["total_idr"]),
            "balance_available_idr": int(r["total_idr"]),
        }, "$set": {"updated_at": now_iso()}})
        await db.balance_transactions.insert_one({
            "id": new_id(),
            "label_id": r["_id"],
            "type": "royalty_available",
            "amount_idr": int(r["total_idr"]),
            "reference_type": "royalty_import",
            "reference_id": import_id,
            "description": f"Dana royalti periode {period_label} diterima — saldo tersedia",
            "created_at": now_iso(),
        })

    await db.royalty_lines.update_many({"import_id": import_id, "status": "pending"}, {"$set": {"status": "available"}})
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


