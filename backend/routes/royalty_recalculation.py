"""Background recalculation for unsettled royalty lines.

The source revenue and import exchange rate stay immutable. Only royalty lines
that are not settled/withdrawn are recalculated with the label's CURRENT share.
"""
from typing import Any, Dict, Iterable, List

from .deps import db_bg, logger
from .dashboard_cache import schedule_recompute as schedule_dashboard_recompute
from models import new_id, now_iso


RECALCULABLE_STATUSES = ["draft", "pending", "available"]


def _line_filter(label_id: str) -> Dict[str, Any]:
    return {
        "label_id": label_id,
        "status": {"$in": RECALCULABLE_STATUSES},
        "legacy_settled": {"$ne": True},
        "revenue_eur": {"$exists": True, "$ne": None},
        "exchange_rate": {"$exists": True, "$ne": None},
    }


async def _sum_by_status(match: Dict[str, Any]) -> Dict[str, int]:
    totals = {"draft": 0, "pending": 0, "available": 0}
    async for row in db_bg.royalty_lines.aggregate([
        {"$match": match},
        {"$group": {"_id": "$status", "total": {"$sum": "$label_idr"}}},
    ], allowDiskUse=True):
        if row.get("_id") in totals:
            totals[row["_id"]] = int(row.get("total") or 0)
    return totals


def _chunks(values: List[str], size: int = 200) -> Iterable[List[str]]:
    for start in range(0, len(values), size):
        yield values[start:start + size]


async def _refresh_import_totals(import_ids: List[str]) -> None:
    clean_ids = [value for value in set(import_ids) if value]
    for batch_ids in _chunks(clean_ids):
        totals: Dict[str, int] = {}
        async for row in db_bg.royalty_lines.aggregate([
            {"$match": {"import_id": {"$in": batch_ids}}},
            {"$group": {"_id": "$import_id", "total": {"$sum": "$label_idr"}}},
        ], allowDiskUse=True):
            totals[row["_id"]] = int(row.get("total") or 0)
        for import_id in batch_ids:
            await db_bg.royalty_imports.update_one(
                {"id": import_id},
                {"$set": {
                    "total_label_idr": totals.get(import_id, 0),
                    "fee_percent": 0,
                    "updated_at": now_iso(),
                }},
            )


async def recalculate_label_unwithdrawn(
    *, label_id: str, percentage: float, job_id: str | None = None,
) -> Dict[str, Any]:
    """Recalculate one label's unsettled lines and adjust live balances by delta."""
    pct = max(0.0, min(100.0, float(percentage)))
    label = await db_bg.labels.find_one(
        {"id": label_id}, {"_id": 0, "last_withdrawn_period": 1},
    ) or {}
    match = _line_filter(label_id)
    if label.get("last_withdrawn_period"):
        match["period"] = {"$gt": label["last_withdrawn_period"]}
    total_lines = await db_bg.royalty_lines.count_documents(match)
    incomplete_filter = {
        "label_id": label_id,
        "status": {"$in": RECALCULABLE_STATUSES},
        "legacy_settled": {"$ne": True},
        "$or": [
            {"revenue_eur": {"$exists": False}}, {"revenue_eur": None},
            {"exchange_rate": {"$exists": False}}, {"exchange_rate": None},
        ],
    }
    if label.get("last_withdrawn_period"):
        incomplete_filter["period"] = {"$gt": label["last_withdrawn_period"]}
    skipped_incomplete = await db_bg.royalty_lines.count_documents(incomplete_filter)
    before = await _sum_by_status(match)
    import_ids = await db_bg.royalty_lines.distinct("import_id", match)

    if job_id:
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {"phase": "recalculating_lines", "progress_lines_total": total_lines, "updated_at": now_iso()}},
        )

    ratio = pct / 100.0
    revenue_expr = {"$ifNull": ["$revenue_eur", 0]}
    rate_expr = {"$ifNull": ["$exchange_rate", 0]}
    label_eur_expr = {"$round": [{"$multiply": [revenue_expr, ratio]}, 6]}
    distributor_eur_expr = {"$round": [{"$subtract": [revenue_expr, label_eur_expr]}, 6]}
    label_idr_expr = {"$convert": {
        "input": {"$round": [{"$multiply": [label_eur_expr, rate_expr]}, 0]},
        "to": "long", "onError": 0, "onNull": 0,
    }}
    distributor_idr_expr = {"$convert": {
        "input": {"$round": [{"$multiply": [distributor_eur_expr, rate_expr]}, 0]},
        "to": "long", "onError": 0, "onNull": 0,
    }}
    revenue_idr_expr = {"$convert": {
        "input": {"$round": [{"$multiply": [revenue_expr, rate_expr]}, 0]},
        "to": "long", "onError": 0, "onNull": 0,
    }}

    processed = 0
    last_oid = None
    chunk_size = 5000
    while True:
        query = dict(match)
        if last_oid is not None:
            query["_id"] = {"$gt": last_oid}
        batch = await db_bg.royalty_lines.find(query, {"_id": 1}).sort("_id", 1).limit(chunk_size).to_list(chunk_size)
        if not batch:
            break
        object_ids = [row["_id"] for row in batch]
        last_oid = object_ids[-1]
        await db_bg.royalty_lines.update_many(
            {"_id": {"$in": object_ids}},
            [{"$set": {
                "fee_eur": 0.0,
                "fee_percent_applied": 0.0,
                "net_eur": {"$round": [revenue_expr, 6]},
                "label_percentage_applied": pct,
                "label_eur": label_eur_expr,
                "distributor_eur": distributor_eur_expr,
                "label_idr": label_idr_expr,
                "distributor_idr": distributor_idr_expr,
                "revenue_idr": revenue_idr_expr,
                "royalty_recalculated_at": now_iso(),
            }}],
        )
        processed += len(object_ids)
        if job_id:
            await db_bg.migrate_jobs.update_one(
                {"id": job_id},
                {"$set": {"progress_lines_done": processed, "updated_at": now_iso()}},
            )

    after = await _sum_by_status(match)
    pending_delta = after["pending"] - before["pending"]
    available_delta = after["available"] - before["available"]
    balance_inc: Dict[str, int] = {}
    if pending_delta:
        balance_inc["balance_pending_idr"] = pending_delta
    if available_delta:
        balance_inc["balance_available_idr"] = available_delta
    label_update: Dict[str, Any] = {
        "royalty_recalculation_status": "done",
        "royalty_recalculated_at": now_iso(),
        "updated_at": now_iso(),
    }
    update_doc: Dict[str, Any] = {"$set": label_update}
    if balance_inc:
        update_doc["$inc"] = balance_inc
    await db_bg.labels.update_one({"id": label_id}, update_doc)

    for balance_name, delta in (("pending", pending_delta), ("available", available_delta)):
        if not delta:
            continue
        await db_bg.balance_transactions.insert_one({
            "id": new_id(),
            "label_id": label_id,
            "type": "royalty_recalculation_adjustment",
            "amount_idr": delta,
            "balance_bucket": balance_name,
            "reference_type": "royalty_recalculation",
            "reference_id": job_id,
            "description": f"Penyesuaian royalti ke bagian label {pct:g}%",
            "created_at": now_iso(),
        })

    await _refresh_import_totals(import_ids)
    return {
        "label_id": label_id,
        "percentage": pct,
        "lines_recalculated": processed,
        "lines_skipped_incomplete": skipped_incomplete,
        "pending_delta_idr": pending_delta,
        "available_delta_idr": available_delta,
        "imports_refreshed": len([value for value in set(import_ids) if value]),
    }


async def run_label_recalculation_job(*, job_id: str, label_id: str, percentage: float) -> None:
    try:
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "processing", "started_at": now_iso(), "updated_at": now_iso()}},
        )
        result = await recalculate_label_unwithdrawn(
            label_id=label_id, percentage=percentage, job_id=job_id,
        )
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "done", "phase": "done", "result": result, "finished_at": now_iso(), "updated_at": now_iso()}},
        )
        await trigger_royalty_caches()
    except Exception as exc:
        logger.exception("[ROYALTY RECALC] label=%s job=%s failed: %s", label_id, job_id, exc)
        await db_bg.labels.update_one(
            {"id": label_id},
            {"$set": {"royalty_recalculation_status": "error", "updated_at": now_iso()}},
        )
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "error", "error_message": f"{type(exc).__name__}: {str(exc)[:400]}", "finished_at": now_iso(), "updated_at": now_iso()}},
        )


async def run_global_recalculation_job(*, job_id: str) -> None:
    try:
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "processing", "phase": "loading_labels", "started_at": now_iso(), "updated_at": now_iso()}},
        )
        label_ids = await db_bg.royalty_lines.distinct("label_id", {
            "status": {"$in": RECALCULABLE_STATUSES},
            "label_id": {"$ne": None},
            "legacy_settled": {"$ne": True},
        })
        labels = await db_bg.labels.find(
            {"id": {"$in": label_ids}}, {"_id": 0, "id": 1, "royalty_percentage_default": 1},
        ).to_list(len(label_ids) or 1)
        active_withdraw_label_ids = set(await db_bg.withdraw_requests.distinct("label_id", {
            "status": {"$in": ["requested", "approved"]},
            "legacy_import": {"$ne": True},
        }))
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {"progress_labels_total": len(labels), "progress_labels_done": 0, "updated_at": now_iso()}},
        )
        totals = {"labels_recalculated": 0, "lines_recalculated": 0, "lines_skipped_incomplete": 0,
                  "pending_delta_idr": 0, "available_delta_idr": 0, "labels_skipped_active_withdraw": 0}
        for index, label in enumerate(labels, start=1):
            if label["id"] in active_withdraw_label_ids:
                totals["labels_skipped_active_withdraw"] += 1
                continue
            result = await recalculate_label_unwithdrawn(
                label_id=label["id"],
                percentage=float(label.get("royalty_percentage_default", 60) or 60),
            )
            totals["labels_recalculated"] += 1
            for key in ("lines_recalculated", "lines_skipped_incomplete", "pending_delta_idr", "available_delta_idr"):
                totals[key] += int(result.get(key) or 0)
            if index % 5 == 0 or index == len(labels):
                await db_bg.migrate_jobs.update_one(
                    {"id": job_id},
                    {"$set": {"phase": "recalculating_labels", "progress_labels_done": index, "updated_at": now_iso()}},
                )
        await db_bg.royalty_imports.update_many({}, {"$set": {"fee_percent": 0, "updated_at": now_iso()}})
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "done", "phase": "done", "result": totals, "finished_at": now_iso(), "updated_at": now_iso()}},
        )
        await trigger_royalty_caches()
    except Exception as exc:
        logger.exception("[ROYALTY RECALC ALL] job=%s failed: %s", job_id, exc)
        await db_bg.migrate_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "error", "error_message": f"{type(exc).__name__}: {str(exc)[:400]}", "finished_at": now_iso(), "updated_at": now_iso()}},
        )


async def trigger_royalty_caches() -> None:
    import asyncio
    schedule_dashboard_recompute()
    try:
        from routes.admin_analytics import schedule_monthly_analytics_recompute
        asyncio.create_task(schedule_monthly_analytics_recompute(reason="royalty_recalculation"))
    except Exception as exc:
        logger.warning("[ROYALTY RECALC] analytics cache trigger failed: %s", exc)