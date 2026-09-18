"""Admin analytics — monthly aggregates over royalty_lines.

Why a separate file: the dashboard needs to slice 1M+ `royalty_lines` rows by
period × dimension (platform/country/track/artist/label) within ~500ms. Doing
that on every page load is impossible on Atlas (each aggregate ≈ 5-15s and the
CSOT cap would kill it anyway).

Architecture:
1. After every successful publish (`_publish_bg`) and after `admin_delete_import`,
   `recompute_monthly_analytics()` rebuilds the entire `monthly_analytics`
   collection from `royalty_lines`. The rebuild streams through Mongo via
   `$group` with `allowDiskUse=True` and runs on `db_bg` (no CSOT cap).
2. Each `monthly_analytics` document is a single (period, dimension, key) slice
   pre-aggregated, indexed by `(period, dim)`. Total docs ≈ 12 months × ~7
   dimensions × (per-dim cardinality, e.g. 200 platforms / 100 countries /
   50k tracks) ≈ ~50k-200k docs total (single-digit MB). Tiny.
3. `GET /api/admin/analytics/monthly?period_from=…&period_to=…&filters` reads
   from the cache — ~50ms even with 6 years of data.

Period axis: every line is grouped by its `period` field (string `YYYY-MM`,
derived from CSV "Reporting month" — what Believe calls "bulan laporan").
"""
import asyncio
import logging
from typing import Any, AsyncIterator, Dict, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from .deps import db, db_bg, logger, require_admin, require_super_admin, SUPER_ADMIN
from .analytics_eligibility import analytics_eligible_filter, ANALYTICS_MATCH_STATUSES, ANALYTICS_LINE_STATUSES
from .admin_permission_service import assert_admin_permission
from models import new_id, now_iso

analytics_r = APIRouter(prefix="/admin/analytics", tags=["admin-analytics"])

# Dimensions we pre-aggregate. Keep this list aligned with the dashboard UI.
# Phase 24: added `release` so the Release Management page can query the cache
# instead of running a fresh aggregate over royalty_lines on every page load.
DIMENSIONS = ["total", "platform", "country", "label", "artist", "track", "release"]

# Module-local guard so concurrent recomputes don't pile up.
_recompute_lock = asyncio.Lock()
_last_recompute_meta: Dict[str, Any] = {
    "finished_at": None,
    "duration_sec": None,
    "doc_count": 0,
    "running": False,
    "progress_pct": 0,
    "progress_phase": None,
    "job_id": None,
}


async def _stream_dim_aggregate(*, dim: str) -> AsyncIterator[Dict[str, Any]]:
    """Yield grouped documents without retaining a whole dimension in RAM.

    For `dim == "total"`, the group key is just `{period: $period}` and the doc
    represents a per-month roll-up.
    For all other dims, the group key is `(period, <dim_field>)` and the doc
    includes the dimension key + human-readable label.

    Only canonical analytics-eligible lines are counted (matched/manually_matched,
    published-onward status, non-staged) — identical to the live path so the
    cache can never diverge from a filtered aggregate.
    """
    dim_field_map = {
        "platform": "$platform",
        "country": "$country",
        "label": "$label_id",
        "artist": "$artist_id",
        "track": "$track_id",
        "release": "$release_id",
    }

    match_stage = {"$match": analytics_eligible_filter()}
    if dim == "total":
        group_id = {"period": "$period"}
    else:
        field = dim_field_map[dim]
        # Skip rows where the dimension key is null/missing (e.g. unmatched
        # tracks have no track_id) — they would all collapse onto one bogus
        # bucket otherwise.
        match_stage["$match"][dim_field_map[dim].lstrip("$")] = {"$ne": None}
        group_id = {"period": "$period", "key": field}

    pipeline = [
        match_stage,
        {"$group": {
            "_id": group_id,
            "revenue_eur": {"$sum": "$revenue_eur"},
            "revenue_idr": {"$sum": "$label_idr"},
            "quantity": {"$sum": "$quantity"},
            "lines_count": {"$sum": 1},
        }},
    ]

    async for r in db_bg.royalty_lines.aggregate(pipeline, allowDiskUse=True):
        period = r["_id"]["period"]
        if not isinstance(period, str) or len(period) != 7:
            continue  # malformed
        doc = {
            "period": period,
            "dim": dim,
            "revenue_eur": round(r.get("revenue_eur") or 0.0, 4),
            "revenue_idr": int(r.get("revenue_idr") or 0),
            "quantity": int(r.get("quantity") or 0),
            "lines_count": int(r.get("lines_count") or 0),
        }
        if dim != "total":
            doc["key"] = r["_id"].get("key")
        yield doc


async def _hydrate_labels(docs: List[Dict[str, Any]]) -> None:
    """Replace `key` (label_id/artist_id/track_id) with human-readable name.
    Lookups are batched in chunks of 200 to avoid huge `$in` queries.
    """
    by_dim: Dict[str, set] = {"label": set(), "artist": set(), "track": set(), "release": set()}
    for d in docs:
        if d.get("dim") in by_dim and d.get("key"):
            by_dim[d["dim"]].add(d["key"])

    label_names: Dict[str, str] = {}
    if by_dim["label"]:
        async for lab in db_bg.labels.find(
            {"id": {"$in": list(by_dim["label"])}},
            {"_id": 0, "id": 1, "label_name": 1},
        ):
            label_names[lab["id"]] = lab.get("label_name") or "(no name)"

    artist_names: Dict[str, str] = {}
    if by_dim["artist"]:
        async for art in db_bg.artists.find(
            {"id": {"$in": list(by_dim["artist"])}},
            {"_id": 0, "id": 1, "artist_name": 1},
        ):
            artist_names[art["id"]] = art.get("artist_name") or "(no name)"

    track_info: Dict[str, Dict[str, str]] = {}
    if by_dim["track"]:
        async for t in db_bg.tracks.find(
            {"id": {"$in": list(by_dim["track"])}},
            {"_id": 0, "id": 1, "track_title": 1, "artist_name": 1, "isrc": 1},
        ):
            track_info[t["id"]] = {
                "title": t.get("track_title") or "(untitled)",
                "artist_name": t.get("artist_name") or "",
                "isrc": t.get("isrc") or "",
            }

    release_info: Dict[str, Dict[str, str]] = {}
    if by_dim["release"]:
        async for rel in db_bg.releases.find(
            {"id": {"$in": list(by_dim["release"])}},
            {"_id": 0, "id": 1, "release_title": 1, "artist_name": 1, "upc": 1, "release_date": 1},
        ):
            release_info[rel["id"]] = {
                "title": rel.get("release_title") or "(untitled release)",
                "artist_name": rel.get("artist_name") or "",
                "upc": rel.get("upc") or "",
                "release_date": rel.get("release_date") or "",
            }

    for d in docs:
        if d["dim"] == "label" and d.get("key"):
            d["label_name"] = label_names.get(d["key"], "(unknown label)")
        elif d["dim"] == "artist" and d.get("key"):
            d["artist_name"] = artist_names.get(d["key"], "(unknown artist)")
        elif d["dim"] == "track" and d.get("key"):
            info = track_info.get(d["key"], {})
            d["track_title"] = info.get("title", "(unknown)")
            d["track_artist"] = info.get("artist_name", "")
            d["isrc"] = info.get("isrc", "")
        elif d["dim"] == "release" and d.get("key"):
            info = release_info.get(d["key"], {})
            d["release_title"] = info.get("title", "(unknown)")
            d["release_artist"] = info.get("artist_name", "")
            d["upc"] = info.get("upc", "")
            d["release_date"] = info.get("release_date", "")


async def recompute_monthly_analytics(*, job_id: Optional[str] = None, reason: str = "automatic") -> Dict[str, Any]:
    """Stream a complete rebuild into staging, then atomically swap it live."""
    async with _recompute_lock:
        t0 = datetime.now(timezone.utc)
        job_id = job_id or new_id()
        staging = f"monthly_analytics_staging_{job_id.replace('-', '')}"
        _last_recompute_meta.update({
            "running": True,
            "job_id": job_id,
            "progress_pct": 0,
            "progress_phase": "starting",
            "reason": reason,
        })
        await db_bg.rollup_health.update_one(
            {"id": "monthly_analytics"},
            {"$set": {
                "id": "monthly_analytics",
                "running": True,
                "job_id": job_id,
                "reason": reason,
                "progress_pct": 0,
                "progress_phase": "starting",
                "started_at": now_iso(),
                "updated_at": now_iso(),
                "last_error": None,
            }},
            upsert=True,
        )
        try:
            await db_bg.drop_collection(staging)
            total_docs = 0
            per_dim_counts: Dict[str, int] = {}
            source_periods: List[str] = []
            batch_size = 5000
            for dim_index, dim in enumerate(DIMENSIONS):
                phase = f"aggregating_{dim}"
                progress = int(dim_index / len(DIMENSIONS) * 85)
                _last_recompute_meta.update({"progress_phase": phase, "progress_pct": progress})
                await db_bg.rollup_health.update_one(
                    {"id": "monthly_analytics", "job_id": job_id},
                    {"$set": {"progress_phase": phase, "progress_pct": progress, "updated_at": now_iso()}},
                )
                batch: List[Dict[str, Any]] = []
                dim_count = 0
                async for doc in _stream_dim_aggregate(dim=dim):
                    batch.append(doc)
                    if dim == "total":
                        source_periods.append(doc["period"])
                    if len(batch) >= batch_size:
                        await _hydrate_labels(batch)
                        await db_bg[staging].insert_many(batch, ordered=False)
                        dim_count += len(batch)
                        total_docs += len(batch)
                        batch = []
                if batch:
                    await _hydrate_labels(batch)
                    await db_bg[staging].insert_many(batch, ordered=False)
                    dim_count += len(batch)
                    total_docs += len(batch)
                per_dim_counts[dim] = dim_count

            _last_recompute_meta.update({"progress_phase": "indexing", "progress_pct": 90})
            await db_bg.rollup_health.update_one(
                {"id": "monthly_analytics", "job_id": job_id},
                {"$set": {"progress_phase": "indexing", "progress_pct": 90, "doc_count": total_docs, "updated_at": now_iso()}},
            )
            if total_docs:
                await db_bg[staging].create_index([("period", 1), ("dim", 1)])
                await db_bg[staging].create_index([("dim", 1), ("revenue_idr", -1)])
                await db_bg[staging].create_index([("dim", 1), ("key", 1), ("period", 1)])
                # dropTarget keeps the old cache readable until this atomic swap.
                await db_bg[staging].rename("monthly_analytics", dropTarget=True)
            else:
                await db_bg.drop_collection("monthly_analytics")
            duration = (datetime.now(timezone.utc) - t0).total_seconds()
            _last_recompute_meta.update({
                "finished_at": now_iso(),
                "duration_sec": round(duration, 2),
                "doc_count": total_docs,
                "per_dim_counts": per_dim_counts,
                "last_error": None,
                "running": False,
                "progress_pct": 100,
                "progress_phase": "done",
                "source_period_min": min(source_periods) if source_periods else None,
                "source_period_max": max(source_periods) if source_periods else None,
            })
            # Persist health to Mongo so it survives pod restarts (and other
            # workers in a multi-replica deploy can read it). Stored as a
            # singleton doc with id='monthly_analytics'.
            try:
                await db_bg.rollup_health.update_one(
                    {"id": "monthly_analytics"},
                    {"$set": {
                        "id": "monthly_analytics",
                        "finished_at": _last_recompute_meta["finished_at"],
                        "duration_sec": _last_recompute_meta["duration_sec"],
                        "doc_count": _last_recompute_meta["doc_count"],
                        "per_dim_counts": per_dim_counts,
                        "running": False,
                        "job_id": job_id,
                        "progress_pct": 100,
                        "progress_phase": "done",
                        "source_period_min": _last_recompute_meta["source_period_min"],
                        "source_period_max": _last_recompute_meta["source_period_max"],
                        "last_error": None,
                        "updated_at": now_iso(),
                    }},
                    upsert=True,
                )
            except Exception:
                logger.warning("[ANALYTICS] failed to persist rollup_health doc")
            logger.info("[ANALYTICS] recompute done in %.2fs — %d docs across %d dims",
                        duration, total_docs, len(DIMENSIONS))
            return dict(_last_recompute_meta)
        except Exception as e:
            logger.exception("[ANALYTICS] recompute FAILED: %s", e)
            _last_recompute_meta["last_error"] = f"{type(e).__name__}: {str(e)[:300]}"
            # Persist failure too so admin UI can show it.
            try:
                await db_bg.rollup_health.update_one(
                    {"id": "monthly_analytics"},
                    {"$set": {
                        "id": "monthly_analytics",
                        "last_error": _last_recompute_meta["last_error"],
                        "last_error_at": now_iso(),
                        "running": False,
                        "job_id": job_id,
                        "progress_phase": "error",
                        "updated_at": now_iso(),
                    }},
                    upsert=True,
                )
            except Exception:
                pass
            await db_bg.drop_collection(staging)
            raise
        finally:
            _last_recompute_meta["running"] = False


async def _run_scheduled_recompute(*, job_id: str, reason: str) -> None:
    try:
        await recompute_monthly_analytics(job_id=job_id, reason=reason)
    except Exception:
        logger.exception("[ANALYTICS] scheduled rebuild %s failed", job_id)


async def schedule_monthly_analytics_recompute(*, reason: str = "automatic") -> Dict[str, Any]:
    """Queue one rebuild per process and return immediately."""
    if _last_recompute_meta.get("running"):
        return dict(_last_recompute_meta)
    job_id = new_id()
    _last_recompute_meta.update({
        "running": True,
        "job_id": job_id,
        "progress_pct": 0,
        "progress_phase": "queued",
        "reason": reason,
    })
    await db_bg.rollup_health.update_one(
        {"id": "monthly_analytics"},
        {"$set": {
            "id": "monthly_analytics",
            "running": True,
            "job_id": job_id,
            "reason": reason,
            "progress_pct": 0,
            "progress_phase": "queued",
            "updated_at": now_iso(),
            "last_error": None,
        }},
        upsert=True,
    )
    asyncio.create_task(_run_scheduled_recompute(job_id=job_id, reason=reason))
    return dict(_last_recompute_meta)


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------

@analytics_r.post("/recompute")
async def admin_recompute_analytics(user: dict = Depends(require_super_admin)):
    """Queue a scalable rebuild and return before the ingress timeout."""
    already_running = bool(_last_recompute_meta.get("running"))
    meta = await schedule_monthly_analytics_recompute(reason=f"manual:{user['id']}")
    return {
        "ok": True,
        "queued": not already_running,
        "message": "Recompute already running" if already_running else "Recompute queued",
        "job_id": meta.get("job_id"),
        "meta": meta,
    }


@analytics_r.get("/status")
async def admin_analytics_status(user: dict = Depends(require_admin)):
    """Tiny status endpoint — used by the dashboard to show 'Last refreshed X
    minutes ago'. Falls back to the persisted `rollup_health` doc when this
    pod hasn't run a rebuild yet (e.g. after a fresh restart).
    """
    meta: Dict[str, Any] = {}
    try:
        health = await db.rollup_health.find_one({"id": "monthly_analytics"}, {"_id": 0})
        if health:
            meta.update(health)
            meta["from_persisted"] = True
    except Exception:
        pass
    # The local running state is newer than persisted state while the task is
    # being queued; otherwise persisted health wins across pod restarts.
    if _last_recompute_meta.get("running"):
        meta.update(_last_recompute_meta)
    elif not meta:
        meta.update(_last_recompute_meta)
    return {
        "running": bool(meta.get("running", False)),
        "job_id": meta.get("job_id"),
        "progress_pct": int(meta.get("progress_pct") or 0),
        "progress_phase": meta.get("progress_phase"),
        "finished_at": meta.get("finished_at"),
        "duration_sec": meta.get("duration_sec"),
        "doc_count": meta.get("doc_count", 0),
        "per_dim_counts": meta.get("per_dim_counts", {}),
        "last_error": meta.get("last_error"),
        "last_error_at": meta.get("last_error_at"),
        "source_period_min": meta.get("source_period_min"),
        "source_period_max": meta.get("source_period_max"),
    }


@analytics_r.get("/monthly")
async def admin_monthly_analytics(
    user: dict = Depends(require_admin),
    period_from: Optional[str] = Query(None, description="Inclusive — YYYY-MM"),
    period_to: Optional[str] = Query(None, description="Inclusive — YYYY-MM"),
    label_id: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    artist_id: Optional[str] = Query(None),
    track_id: Optional[str] = Query(None),
    top_n: int = Query(10, ge=1, le=50),
):
    """Single-call dashboard payload — KPI + monthly revenue + top-N per dim.

    When a `*_id` / dimension filter is given, the cached `monthly_analytics`
    collection no longer has the right pre-aggregation (it's grouped on the raw
    line), so we fall back to a live aggregate over `royalty_lines` (filtered,
    still fast thanks to compound indexes). For the un-filtered case the cache
    is used directly → ~50ms response.
    """
    # ---- Period sanity ----
    def _valid_period(p: Optional[str]) -> bool:
        if not p:
            return False
        if len(p) != 7 or p[4] != "-":
            return False
        try:
            int(p[:4])
            int(p[5:7])
            return True
        except ValueError:
            return False

    period_filter: Dict[str, Any] = {}
    if _valid_period(period_from):
        period_filter["$gte"] = period_from
    if _valid_period(period_to):
        period_filter["$lte"] = period_to

    has_runtime_filter = any([label_id, platform, country, artist_id, track_id])

    # ---- Slow path (live aggregate) — only when a filter is supplied ----
    if has_runtime_filter:
        line_match: Dict[str, Any] = analytics_eligible_filter()
        if period_filter:
            line_match["period"] = period_filter
        if label_id:
            line_match["label_id"] = label_id
        if platform:
            line_match["platform"] = platform
        if country:
            line_match["country"] = country
        if artist_id:
            line_match["artist_id"] = artist_id
        if track_id:
            line_match["track_id"] = track_id

        # KPI
        kpi_pipeline = [
            {"$match": line_match},
            {"$group": {
                "_id": None,
                "revenue_eur": {"$sum": "$revenue_eur"},
                "revenue_idr": {"$sum": "$label_idr"},
                "quantity": {"$sum": "$quantity"},
                "lines_count": {"$sum": 1},
                "distinct_platforms": {"$addToSet": "$platform"},
                "distinct_countries": {"$addToSet": "$country"},
                "distinct_tracks": {"$addToSet": "$track_id"},
                "distinct_artists": {"$addToSet": "$artist_id"},
                "distinct_labels": {"$addToSet": "$label_id"},
            }},
        ]
        kpi_doc = None
        async for r in db_bg.royalty_lines.aggregate(kpi_pipeline, allowDiskUse=True):
            kpi_doc = r

        # Monthly revenue
        monthly_pipeline = [
            {"$match": line_match},
            {"$group": {"_id": "$period", "revenue_eur": {"$sum": "$revenue_eur"}, "revenue_idr": {"$sum": "$label_idr"}}},
            {"$sort": {"_id": 1}},
        ]
        monthly = [
            {"period": r["_id"], "revenue_eur": round(r["revenue_eur"], 4), "revenue_idr": int(r["revenue_idr"])}
            async for r in db_bg.royalty_lines.aggregate(monthly_pipeline, allowDiskUse=True)
        ]

        async def _topn(group_field: str, hydrate_coll: Optional[str], hydrate_field: Optional[str]):
            pipeline = [
                {"$match": line_match},
                {"$group": {"_id": group_field, "revenue_eur": {"$sum": "$revenue_eur"}, "revenue_idr": {"$sum": "$label_idr"}, "lines": {"$sum": 1}}},
                {"$match": {"_id": {"$ne": None}}},
                {"$sort": {"revenue_idr": -1}},
                {"$limit": top_n},
            ]
            rows = [r async for r in db_bg.royalty_lines.aggregate(pipeline, allowDiskUse=True)]
            if hydrate_coll and hydrate_field and rows:
                ids = [r["_id"] for r in rows]
                names = {}
                async for d in db_bg[hydrate_coll].find({"id": {"$in": ids}}, {"_id": 0, "id": 1, hydrate_field: 1}):
                    names[d["id"]] = d.get(hydrate_field) or "(unknown)"
                for r in rows:
                    r["name"] = names.get(r["_id"], "(unknown)")
            else:
                for r in rows:
                    r["name"] = r["_id"]
            return [
                {"key": r["_id"], "name": r["name"], "revenue_eur": round(r["revenue_eur"], 4),
                 "revenue_idr": int(r["revenue_idr"]), "lines": int(r["lines"])}
                for r in rows
            ]

        top_platforms = await _topn("$platform", None, None)
        top_countries = await _topn("$country", None, None)
        top_labels = await _topn("$label_id", "labels", "label_name")
        top_artists = await _topn("$artist_id", "artists", "artist_name")
        top_tracks = await _topn("$track_id", "tracks", "track_title")

        kpi = {
            "total_revenue_eur": round((kpi_doc or {}).get("revenue_eur") or 0, 4),
            "total_revenue_idr": int((kpi_doc or {}).get("revenue_idr") or 0),
            "total_quantity": int((kpi_doc or {}).get("quantity") or 0),
            "total_lines": int((kpi_doc or {}).get("lines_count") or 0),
            "distinct_platforms": len([p for p in ((kpi_doc or {}).get("distinct_platforms") or []) if p]),
            "distinct_countries": len([p for p in ((kpi_doc or {}).get("distinct_countries") or []) if p]),
            "distinct_tracks": len([p for p in ((kpi_doc or {}).get("distinct_tracks") or []) if p]),
            "distinct_artists": len([p for p in ((kpi_doc or {}).get("distinct_artists") or []) if p]),
            "distinct_labels": len([p for p in ((kpi_doc or {}).get("distinct_labels") or []) if p]),
        }
        return {
            "source": "live",
            "filters": {
                "period_from": period_from, "period_to": period_to,
                "label_id": label_id, "platform": platform, "country": country,
                "artist_id": artist_id, "track_id": track_id,
            },
            "kpi": kpi,
            "monthly": monthly,
            "top_platforms": top_platforms,
            "top_countries": top_countries,
            "top_labels": top_labels,
            "top_artists": top_artists,
            "top_tracks": top_tracks,
        }

    # ---- Fast path (read from `monthly_analytics` cache) ----
    cache_match: Dict[str, Any] = {}
    if period_filter:
        cache_match["period"] = period_filter

    # KPI = sum total slice
    kpi_pipeline = [
        {"$match": {**cache_match, "dim": "total"}},
        {"$group": {
            "_id": None,
            "revenue_eur": {"$sum": "$revenue_eur"},
            "revenue_idr": {"$sum": "$revenue_idr"},
            "lines_count": {"$sum": "$lines_count"},
            "quantity": {"$sum": "$quantity"},
        }},
    ]
    kpi_doc = None
    async for r in db_bg.monthly_analytics.aggregate(kpi_pipeline):
        kpi_doc = r

    # Monthly revenue from `total` slice
    monthly_pipeline = [
        {"$match": {**cache_match, "dim": "total"}},
        {"$sort": {"period": 1}},
        {"$project": {"_id": 0, "period": 1, "revenue_eur": 1, "revenue_idr": 1}},
    ]
    monthly = [r async for r in db_bg.monthly_analytics.aggregate(monthly_pipeline)]

    # distinct counts derived from how many unique dim-keys appear in range
    async def _distinct_count(dim: str) -> int:
        pipe = [{"$match": {**cache_match, "dim": dim}}, {"$group": {"_id": "$key"}}, {"$count": "n"}]
        async for r in db_bg.monthly_analytics.aggregate(pipe):
            return int(r.get("n") or 0)
        return 0

    distinct_platforms = await _distinct_count("platform")
    distinct_countries = await _distinct_count("country")
    distinct_labels = await _distinct_count("label")
    distinct_artists = await _distinct_count("artist")
    distinct_tracks = await _distinct_count("track")

    async def _top_from_cache(dim: str, name_field: Optional[str]):
        pipe = [
            {"$match": {**cache_match, "dim": dim}},
            {"$group": {
                "_id": "$key",
                "revenue_eur": {"$sum": "$revenue_eur"},
                "revenue_idr": {"$sum": "$revenue_idr"},
                "lines": {"$sum": "$lines_count"},
                "name": {"$first": f"${name_field}"} if name_field else {"$first": "$key"},
            }},
            {"$sort": {"revenue_idr": -1}},
            {"$limit": top_n},
        ]
        return [
            {"key": r["_id"], "name": r.get("name") or r["_id"],
             "revenue_eur": round(r["revenue_eur"], 4),
             "revenue_idr": int(r["revenue_idr"]),
             "lines": int(r["lines"])}
            async for r in db_bg.monthly_analytics.aggregate(pipe)
        ]

    top_platforms = await _top_from_cache("platform", None)
    top_countries = await _top_from_cache("country", None)
    top_labels = await _top_from_cache("label", "label_name")
    top_artists = await _top_from_cache("artist", "artist_name")
    top_tracks = await _top_from_cache("track", "track_title")

    kpi = {
        "total_revenue_eur": round((kpi_doc or {}).get("revenue_eur") or 0, 4),
        "total_revenue_idr": int((kpi_doc or {}).get("revenue_idr") or 0),
        "total_quantity": int((kpi_doc or {}).get("quantity") or 0),
        "total_lines": int((kpi_doc or {}).get("lines_count") or 0),
        "distinct_platforms": distinct_platforms,
        "distinct_countries": distinct_countries,
        "distinct_tracks": distinct_tracks,
        "distinct_artists": distinct_artists,
        "distinct_labels": distinct_labels,
    }
    return {
        "source": "cache",
        "cache_meta": {
            "finished_at": _last_recompute_meta.get("finished_at"),
            "doc_count": _last_recompute_meta.get("doc_count", 0),
        },
        "filters": {
            "period_from": period_from, "period_to": period_to,
            "label_id": None, "platform": None, "country": None,
            "artist_id": None, "track_id": None,
        },
        "kpi": kpi,
        "monthly": monthly,
        "top_platforms": top_platforms,
        "top_countries": top_countries,
        "top_labels": top_labels,
        "top_artists": top_artists,
        "top_tracks": top_tracks,
    }


@analytics_r.get("/periods")
async def admin_analytics_periods(user: dict = Depends(require_admin)):
    """Return the list of available periods (YYYY-MM) so the dashboard
    period-range pickers can populate min/max + a sorted dropdown.
    """
    periods: List[str] = []
    async for r in db_bg.monthly_analytics.aggregate([
        {"$match": {"dim": "total"}},
        {"$group": {"_id": "$period"}},
        {"$sort": {"_id": 1}},
    ]):
        if r.get("_id"):
            periods.append(r["_id"])
    # Always merge source periods. A stale cache must not hide a newly imported
    # month (the production symptom was June 2026 hidden behind May 2026).
    try:
        raw = await db_bg.royalty_lines.distinct("period")
        periods = sorted(set(periods).union({
            p for p in raw
            if isinstance(p, str) and len(p) == 7 and p[4] == "-" and p[:4].isdigit()
            and p[5:].isdigit() and 1 <= int(p[5:]) <= 12
        }))
    except Exception:
        pass
    return {"periods": periods, "min": periods[0] if periods else None, "max": periods[-1] if periods else None}



@analytics_r.get("/audit")
async def admin_analytics_audit(
    user: dict = Depends(require_admin),
    period_from: Optional[str] = Query(None, description="Inclusive YYYY-MM"),
    period_to: Optional[str] = Query(None, description="Inclusive YYYY-MM"),
    dup_limit: int = Query(50, ge=1, le=200),
):
    """READ-ONLY reconciliation & duplicate audit.

    Per reporting month it compares: raw (no eligibility) vs canonical-eligible
    vs the `monthly_analytics` cache, lists contributing imports, flags periods
    fed by >1 import (overlap), and reports identical business-rows appearing in
    DIFFERENT imports (duplicate suspects). NEVER mutates data.
    """
    assert_admin_permission(user, "analytics.manage")
    prange: Dict[str, Any] = {}
    if period_from:
        prange["$gte"] = period_from
    if period_to:
        prange["$lte"] = period_to
    period_match = {"period": prange} if prange else {"period": {"$ne": None, "$exists": True}}
    eligible_match = analytics_eligible_filter(dict(period_match) if prange else None)

    # 1) raw (all lines, no eligibility) per period
    raw_by_period: Dict[str, Dict[str, Any]] = {}
    async for r in db_bg.royalty_lines.aggregate([
        {"$match": period_match},
        {"$group": {"_id": "$period", "idr": {"$sum": "$label_idr"}, "lines": {"$sum": 1}}},
    ], allowDiskUse=True):
        if isinstance(r["_id"], str):
            raw_by_period[r["_id"]] = {"raw_idr": int(r.get("idr") or 0), "raw_lines": int(r.get("lines") or 0)}

    # 2) canonical-eligible per period
    elig_by_period: Dict[str, Dict[str, Any]] = {}
    async for r in db_bg.royalty_lines.aggregate([
        {"$match": eligible_match},
        {"$group": {"_id": "$period", "idr": {"$sum": "$label_idr"}, "eur": {"$sum": "$revenue_eur"}, "lines": {"$sum": 1}}},
    ], allowDiskUse=True):
        if isinstance(r["_id"], str):
            elig_by_period[r["_id"]] = {"eligible_idr": int(r.get("idr") or 0), "eligible_eur": round(r.get("eur") or 0, 2), "eligible_lines": int(r.get("lines") or 0)}

    # 3) cache (monthly_analytics dim=total) per period
    cache_by_period: Dict[str, Dict[str, Any]] = {}
    cache_match = {"dim": "total"}
    if prange:
        cache_match["period"] = prange
    async for r in db_bg.monthly_analytics.aggregate([
        {"$match": cache_match},
        {"$group": {"_id": "$period", "idr": {"$sum": "$revenue_idr"}, "lines": {"$sum": "$lines_count"}}},
    ]):
        if isinstance(r["_id"], str):
            cache_by_period[r["_id"]] = {"cache_idr": int(r.get("idr") or 0), "cache_lines": int(r.get("lines") or 0)}

    # 4) imports contributing per period (all lines + eligible subset)
    imports_by_period: Dict[str, List[Dict[str, Any]]] = {}
    import_ids: set = set()
    async for r in db_bg.royalty_lines.aggregate([
        {"$match": period_match},
        {"$group": {
            "_id": {"period": "$period", "import_id": "$import_id"},
            "lines": {"$sum": 1},
            "eligible_lines": {"$sum": {"$cond": [{"$and": [
                {"$in": ["$match_status", ANALYTICS_MATCH_STATUSES]},
                {"$in": ["$status", ANALYTICS_LINE_STATUSES]},
                {"$ne": ["$replacement_stage", True]},
            ]}, 1, 0]}},
            "eligible_idr": {"$sum": {"$cond": [{"$and": [
                {"$in": ["$match_status", ANALYTICS_MATCH_STATUSES]},
                {"$in": ["$status", ANALYTICS_LINE_STATUSES]},
                {"$ne": ["$replacement_stage", True]},
            ]}, "$label_idr", 0]}},
        }},
    ], allowDiskUse=True):
        period = r["_id"].get("period")
        imp = r["_id"].get("import_id")
        if not isinstance(period, str):
            continue
        import_ids.add(imp)
        imports_by_period.setdefault(period, []).append({
            "import_id": imp, "lines": int(r.get("lines") or 0),
            "eligible_lines": int(r.get("eligible_lines") or 0),
            "eligible_idr": int(r.get("eligible_idr") or 0),
        })

    # hydrate import filename + status
    imp_meta: Dict[str, Dict[str, Any]] = {}
    if import_ids:
        async for d in db_bg.royalty_imports.find({"id": {"$in": list(import_ids)}}, {"_id": 0, "id": 1, "filename": 1, "status": 1}):
            imp_meta[d["id"]] = {"filename": d.get("filename"), "import_status": d.get("status")}

    # assemble per-period rows
    all_periods = sorted(set(raw_by_period) | set(elig_by_period) | set(cache_by_period))
    periods_out: List[Dict[str, Any]] = []
    overlaps: List[Dict[str, Any]] = []
    for p in all_periods:
        raw = raw_by_period.get(p, {})
        elig = elig_by_period.get(p, {})
        cache = cache_by_period.get(p, {})
        imps = imports_by_period.get(p, [])
        for it in imps:
            it.update(imp_meta.get(it["import_id"], {"filename": None, "import_status": None}))
        imps.sort(key=lambda x: x["eligible_idr"], reverse=True)
        eligible_idr = elig.get("eligible_idr", 0)
        cache_idr = cache.get("cache_idr", 0)
        periods_out.append({
            "period": p,
            "raw_idr": raw.get("raw_idr", 0), "raw_lines": raw.get("raw_lines", 0),
            "eligible_idr": eligible_idr, "eligible_eur": elig.get("eligible_eur", 0), "eligible_lines": elig.get("eligible_lines", 0),
            "cache_idr": cache_idr, "cache_lines": cache.get("cache_lines", 0),
            "diff_cache_vs_eligible_idr": eligible_idr - cache_idr,
            "import_count": len(imps),
            "imports": imps,
        })
        contributing = [it for it in imps if it["eligible_lines"] > 0]
        if len(contributing) > 1:
            overlaps.append({"period": p, "import_count": len(contributing),
                             "imports": [{"import_id": it["import_id"], "filename": it["filename"], "eligible_lines": it["eligible_lines"], "eligible_idr": it["eligible_idr"]} for it in contributing]})

    # 5) duplicate suspects — identical eligible business-rows across DIFFERENT imports
    dup_suspects: List[Dict[str, Any]] = []
    async for r in db_bg.royalty_lines.aggregate([
        {"$match": eligible_match},
        {"$group": {
            "_id": {
                "period": "$period", "platform": "$platform", "country": "$country",
                "isrc": "$isrc", "sales_type": "$sales_type", "subscription_type": "$subscription_type",
                "quantity": "$quantity", "revenue_eur": "$revenue_eur", "track_id": "$track_id",
            },
            "count": {"$sum": 1},
            "import_ids": {"$addToSet": "$import_id"},
            "idr": {"$sum": "$label_idr"}, "eur": {"$sum": "$revenue_eur"},
        }},
        {"$match": {"count": {"$gt": 1}, "import_ids.1": {"$exists": True}}},
        {"$sort": {"idr": -1}},
        {"$limit": dup_limit},
    ], allowDiskUse=True):
        k = r["_id"]
        dup_suspects.append({
            "period": k.get("period"), "platform": k.get("platform"), "country": k.get("country"),
            "isrc": k.get("isrc"), "sales_type": k.get("sales_type"), "subscription_type": k.get("subscription_type"),
            "quantity": k.get("quantity"), "revenue_eur": k.get("revenue_eur"),
            "count": int(r.get("count") or 0), "import_ids": r.get("import_ids") or [],
            "idr": int(r.get("idr") or 0), "eur": round(r.get("eur") or 0, 2),
        })

    return {
        "generated_at": now_iso(),
        "filters": {"period_from": period_from, "period_to": period_to},
        "eligibility": {"match_status": ANALYTICS_MATCH_STATUSES, "status": ANALYTICS_LINE_STATUSES, "exclude_replacement_stage": True},
        "note": "READ-ONLY audit. 'raw' = semua baris; 'eligible' = definisi kanonik Analytics; 'cache' = monthly_analytics. Duplicate suspect hanya indikasi (baris identik di import berbeda) — belum tentu duplikat sebenarnya.",
        "cache_source_meta": {
            "source_period_min": _last_recompute_meta.get("source_period_min"),
            "source_period_max": _last_recompute_meta.get("source_period_max"),
            "finished_at": _last_recompute_meta.get("finished_at"),
        },
        "periods": periods_out,
        "overlaps": overlaps,
        "duplicate_suspects": dup_suspects,
    }
