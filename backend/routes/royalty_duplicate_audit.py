"""Read-only duplicate royalty import audit with per-period and per-label impact."""
import asyncio
import hashlib
import json
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query

from models import new_id, now_iso
from .deps import db, db_bg, logger, require_admin


duplicate_audit_r = APIRouter(prefix="/royalty/admin/duplicate-audit", tags=["royalty-duplicate-audit"])
FINANCE_ROLES = ("super_admin", "admin_finance")
ACTIVE_STATUSES = ["queued", "processing"]


def _require_finance(user: dict) -> None:
    if user.get("role") not in FINANCE_ROLES:
        raise HTTPException(status_code=403, detail="Hanya Admin Finance / Super Admin")


def _fingerprint(item: dict) -> str:
    payload = {
        "total_lines": int(item.get("total_lines") or 0),
        "total_revenue_eur": round(float(item.get("total_revenue_eur") or 0), 6),
        "period_start": item.get("period_start"),
        "period_end": item.get("period_end"),
        "period_breakdown": sorted((item.get("period_breakdown") or {}).items()),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _filename_year_matches(item: dict) -> bool:
    years = re.findall(r"20\d{2}", str(item.get("filename") or ""))
    period_end = str(item.get("period_end") or item.get("period") or "")
    return bool(years and re.match(r"^20\d{2}", period_end) and years[-1] == period_end[:4])


def _canonical_score(item: dict) -> Tuple[int, str]:
    return (1 if _filename_year_matches(item) else 0, str(item.get("created_at") or ""))


def _safe_import(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "filename": item.get("filename"),
        "status": item.get("status"),
        "total_lines": int(item.get("total_lines") or 0),
        "matched_lines": int(item.get("matched_lines") or 0),
        "total_revenue_eur": round(float(item.get("total_revenue_eur") or 0), 6),
        "total_label_idr": int(item.get("total_label_idr") or 0),
        "exchange_rate_eur_idr": float(item.get("exchange_rate_eur_idr") or 0),
        "period_start": item.get("period_start"),
        "period_end": item.get("period_end"),
        "period_breakdown": item.get("period_breakdown") or {},
        "created_at": item.get("created_at"),
        "dana_received_at": item.get("dana_received_at"),
        "filename_year_matches_period": _filename_year_matches(item),
    }


async def _line_stats(import_ids: List[str]) -> List[dict]:
    return [item async for item in db_bg.royalty_lines.aggregate([
        {"$match": {"import_id": {"$in": import_ids}}},
        {"$group": {
            "_id": {
                "import_id": "$import_id",
                "period": {"$ifNull": ["$period", "(kosong)"]},
                "label_id": {"$ifNull": ["$label_id", "(kosong)"]},
                "status": {"$ifNull": ["$status", "(kosong)"]},
                "legacy_settled": {"$eq": ["$legacy_settled", True]},
            },
            "lines": {"$sum": 1},
            "revenue_eur": {"$sum": {"$ifNull": ["$revenue_eur", 0]}},
            "label_idr": {"$sum": {"$ifNull": ["$label_idr", 0]}},
        }},
    ], allowDiskUse=True)]


def _period_comparison(stats: List[dict], canonical_id: str, duplicate_id: str) -> dict:
    periods: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(
        lambda: defaultdict(lambda: {"lines": 0, "revenue_eur": 0.0})
    )
    for item in stats:
        key = item.get("_id") or {}
        import_id = key.get("import_id")
        if import_id not in (canonical_id, duplicate_id):
            continue
        period = str(key.get("period") or "(kosong)")
        periods[period][import_id]["lines"] += int(item.get("lines") or 0)
        periods[period][import_id]["revenue_eur"] += float(item.get("revenue_eur") or 0)
    rows = []
    exact = True
    for period in sorted(periods):
        canonical = periods[period][canonical_id]
        duplicate = periods[period][duplicate_id]
        line_difference = int(duplicate["lines"] - canonical["lines"])
        revenue_difference = duplicate["revenue_eur"] - canonical["revenue_eur"]
        matches = line_difference == 0 and abs(revenue_difference) < 0.000001
        exact = exact and matches
        rows.append({
            "period": period,
            "canonical_lines": int(canonical["lines"]),
            "duplicate_lines": int(duplicate["lines"]),
            "canonical_revenue_eur": round(canonical["revenue_eur"], 12),
            "duplicate_revenue_eur": round(duplicate["revenue_eur"], 12),
            "line_difference": line_difference,
            "revenue_difference_eur": round(revenue_difference, 12),
            "matches": matches,
        })
    return {"exact_period_match": exact, "periods": rows}


async def _duplicate_impact(stats: List[dict], duplicate_id: str) -> dict:
    label_ids = list({
        str((item.get("_id") or {}).get("label_id")) for item in stats
        if (item.get("_id") or {}).get("import_id") == duplicate_id
        and (item.get("_id") or {}).get("label_id") not in (None, "(kosong)")
    })
    labels = await db_bg.labels.find(
        {"id": {"$in": label_ids}},
        {"_id": 0, "id": 1, "label_name": 1, "last_withdrawn_period": 1},
    ).to_list(len(label_ids) or 1)
    labels_by_id = {item["id"]: item for item in labels}
    paid_labels = set(await db_bg.withdraw_requests.distinct("label_id", {
        "label_id": {"$in": label_ids}, "status": "paid",
    }))
    impacts: Dict[str, Dict[str, Any]] = {}
    for item in stats:
        key = item.get("_id") or {}
        if key.get("import_id") != duplicate_id:
            continue
        label_id = str(key.get("label_id") or "(kosong)")
        bucket = impacts.setdefault(label_id, {
            "label_id": label_id,
            "label_name": (labels_by_id.get(label_id) or {}).get("label_name") or "Tidak terhubung",
            "lines": 0,
            "revenue_eur": 0.0,
            "total_label_idr": 0,
            "active_balance_idr": 0,
            "historical_or_excluded_idr": 0,
            "has_paid_withdrawal": label_id in paid_labels,
        })
        period = str(key.get("period") or "")
        status = key.get("status")
        amount = int(item.get("label_idr") or 0)
        cutoff = (labels_by_id.get(label_id) or {}).get("last_withdrawn_period")
        is_active = (
            status in ("pending", "available")
            and not bool(key.get("legacy_settled"))
            and bool(re.fullmatch(r"\d{4}-\d{2}", period))
            and (not cutoff or period > cutoff)
        )
        bucket["lines"] += int(item.get("lines") or 0)
        bucket["revenue_eur"] += float(item.get("revenue_eur") or 0)
        bucket["total_label_idr"] += amount
        bucket["active_balance_idr" if is_active else "historical_or_excluded_idr"] += amount
    rows = list(impacts.values())
    for row in rows:
        row["revenue_eur"] = round(row["revenue_eur"], 12)
    rows.sort(key=lambda item: abs(item["total_label_idr"]), reverse=True)
    return {
        "affected_labels": len(rows),
        "labels_with_paid_withdrawal": sum(1 for row in rows if row["has_paid_withdrawal"]),
        "lines": sum(row["lines"] for row in rows),
        "revenue_eur": round(sum(row["revenue_eur"] for row in rows), 12),
        "total_label_idr": sum(row["total_label_idr"] for row in rows),
        "active_balance_idr": sum(row["active_balance_idr"] for row in rows),
        "historical_or_excluded_idr": sum(row["historical_or_excluded_idr"] for row in rows),
        "requires_paid_history_review": any(
            row["has_paid_withdrawal"] and row["historical_or_excluded_idr"] != 0 for row in rows
        ),
        "top_labels": rows[:100],
    }


async def _run_duplicate_audit(job_id: str) -> None:
    try:
        started_at = now_iso()
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "processing", "phase": "mencari_duplikat", "started_at": started_at, "updated_at": started_at}},
        )
        imports = await db_bg.royalty_imports.find(
            {"total_lines": {"$gt": 0}, "status": {"$nin": ["awaiting_upload", "error", "deleting"]}},
            {"_id": 0},
        ).to_list(100000)
        by_fingerprint: Dict[str, List[dict]] = defaultdict(list)
        for item in imports:
            by_fingerprint[_fingerprint(item)].append(item)
        groups = [items for items in by_fingerprint.values() if len(items) > 1]
        total_pairs = sum(len(items) - 1 for items in groups)
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {"phase": "menghitung_dampak", "progress_groups_total": total_pairs, "updated_at": now_iso()}},
        )
        await db_bg.royalty_duplicate_audit_rows.delete_many({"job_id": job_id})
        summary = {
            "duplicate_groups": len(groups),
            "duplicate_pairs": total_pairs,
            "exact_content_pairs": 0,
            "duplicate_lines": 0,
            "duplicate_revenue_eur": 0.0,
            "duplicate_label_idr": 0,
            "active_balance_impact_idr": 0,
            "historical_or_excluded_impact_idr": 0,
            "pairs_requiring_paid_history_review": 0,
        }
        done = 0
        for group_items in groups:
            ordered = sorted(group_items, key=_canonical_score, reverse=True)
            canonical = ordered[0]
            stats = await _line_stats([item["id"] for item in ordered])
            for duplicate in ordered[1:]:
                comparison = _period_comparison(stats, canonical["id"], duplicate["id"])
                impact = await _duplicate_impact(stats, duplicate["id"])
                row = {
                    "id": new_id(),
                    "job_id": job_id,
                    "fingerprint": _fingerprint(canonical),
                    "canonical_import": _safe_import(canonical),
                    "duplicate_import": _safe_import(duplicate),
                    "comparison": comparison,
                    "impact": impact,
                    "recommendation": (
                        "Tinjau salinan lama untuk diarsipkan; riwayat pembayaran harus diverifikasi lebih dulu."
                        if impact["requires_paid_history_review"]
                        else "Salinan lama dapat dipersiapkan untuk arsip setelah konfirmasi admin."
                    ),
                    "read_only": True,
                    "created_at": now_iso(),
                }
                await db_bg.royalty_duplicate_audit_rows.insert_one(row)
                done += 1
                summary["exact_content_pairs"] += 1 if comparison["exact_period_match"] else 0
                summary["duplicate_lines"] += impact["lines"]
                summary["duplicate_revenue_eur"] += impact["revenue_eur"]
                summary["duplicate_label_idr"] += impact["total_label_idr"]
                summary["active_balance_impact_idr"] += impact["active_balance_idr"]
                summary["historical_or_excluded_impact_idr"] += impact["historical_or_excluded_idr"]
                summary["pairs_requiring_paid_history_review"] += 1 if impact["requires_paid_history_review"] else 0
                await db_bg.migrate_jobs.update_one(
                    {"id": job_id},
                    {"$set": {"progress_groups_done": done, "updated_at": now_iso()}},
                )
        summary["duplicate_revenue_eur"] = round(summary["duplicate_revenue_eur"], 12)
        finished_at = now_iso()
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "done", "phase": "done", "summary": summary, "finished_at": finished_at, "updated_at": finished_at}},
        )
    except Exception as exc:
        logger.exception("[DUPLICATE AUDIT] job=%s failed: %s", job_id, exc)
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "error", "phase": "error", "error_message": f"{type(exc).__name__}: {str(exc)[:400]}", "finished_at": now_iso(), "updated_at": now_iso()}},
        )


@duplicate_audit_r.post("/preview")
async def start_duplicate_audit(user: dict = Depends(require_admin)):
    _require_finance(user)
    active = await db.migrate_jobs.find_one(
        {"kind": "royalty_duplicate_audit", "status": {"$in": ACTIVE_STATUSES}}, {"_id": 0},
    )
    if active:
        return {"job_id": active["id"], "status": active["status"], "already_running": True}
    job_id = new_id()
    submitted_at = now_iso()
    await db_bg.migrate_jobs.insert_one({
        "id": job_id, "kind": "royalty_duplicate_audit", "status": "queued",
        "submitted_by": user["id"], "submitted_at": submitted_at, "updated_at": submitted_at,
        "phase": "queued", "progress_groups_done": 0, "progress_groups_total": 0,
    })
    asyncio.create_task(_run_duplicate_audit(job_id))
    return {"job_id": job_id, "status": "queued", "already_running": False}


@duplicate_audit_r.get("/jobs/{job_id}")
async def get_duplicate_audit_job(job_id: str, user: dict = Depends(require_admin)):
    _require_finance(user)
    job = await db.migrate_jobs.find_one(
        {"id": job_id, "kind": "royalty_duplicate_audit"}, {"_id": 0},
    )
    if not job:
        raise HTTPException(status_code=404, detail="Audit duplikat tidak ditemukan")
    return job


@duplicate_audit_r.get("/jobs/{job_id}/rows")
async def get_duplicate_audit_rows(
    job_id: str, user: dict = Depends(require_admin),
    page: int = Query(default=1, ge=1), limit: int = Query(default=20, ge=1, le=100),
):
    _require_finance(user)
    query = {"job_id": job_id}
    total = await db.royalty_duplicate_audit_rows.count_documents(query)
    rows = await db.royalty_duplicate_audit_rows.find(query, {"_id": 0}).sort(
        "impact.revenue_eur", -1,
    ).skip((page - 1) * limit).limit(limit).to_list(limit)
    return {"items": rows, "total": total, "page": page, "limit": limit, "read_only": True}


async def resume_duplicate_audit_jobs() -> None:
    jobs = await db_bg.migrate_jobs.find(
        {"kind": "royalty_duplicate_audit", "status": {"$in": ACTIVE_STATUSES}},
        {"_id": 0, "id": 1},
    ).to_list(10)
    for job in jobs:
        asyncio.create_task(_run_duplicate_audit(job["id"]))