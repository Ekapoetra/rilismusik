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
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from .deps import db, db_bg, logger, require_admin, require_super_admin, SUPER_ADMIN
from models import now_iso

analytics_r = APIRouter(prefix="/admin/analytics", tags=["admin-analytics"])

# Dimensions we pre-aggregate. Keep this list aligned with the dashboard UI.
# Phase 24: added `release` so the Release Management page can query the cache
# instead of running a fresh aggregate over royalty_lines on every page load.
DIMENSIONS = ["total", "platform", "country", "label", "artist", "track", "release"]

# Module-local guard so concurrent recomputes don't pile up.
_recompute_lock = asyncio.Lock()
_last_recompute_meta: Dict[str, Any] = {"finished_at": None, "duration_sec": None, "doc_count": 0, "running": False}


async def _stream_dim_aggregate(*, dim: str) -> List[Dict[str, Any]]:
    """Group `royalty_lines` by (period, <dim_field>). Returns a list of docs
    ready to insert into `monthly_analytics`.

    For `dim == "total"`, the group key is just `{period: $period}` and the doc
    represents a per-month roll-up.
    For all other dims, the group key is `(period, <dim_field>)` and the doc
    includes the dimension key + human-readable label.

    Includes filtering: only `match_status in ['matched','manually_matched']`
    lines are counted toward `revenue_eur`/`label_idr` since unmatched rows
    have unreliable label/artist FK and would otherwise pollute the totals.
    """
    dim_field_map = {
        "platform": "$platform",
        "country": "$country",
        "label": "$label_id",
        "artist": "$artist_id",
        "track": "$track_id",
        "release": "$release_id",
    }

    match_stage = {"$match": {"period": {"$ne": None, "$exists": True}}}
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

    docs: List[Dict[str, Any]] = []
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
        docs.append(doc)
    return docs


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


async def recompute_monthly_analytics() -> Dict[str, Any]:
    """Drop & rebuild the `monthly_analytics` collection. Idempotent + safe to
    schedule concurrently — only one rebuild runs at a time.
    """
    async with _recompute_lock:
        t0 = datetime.now(timezone.utc)
        _last_recompute_meta["running"] = True
        try:
            all_docs: List[Dict[str, Any]] = []
            for dim in DIMENSIONS:
                docs = await _stream_dim_aggregate(dim=dim)
                all_docs.extend(docs)
            # Resolve labels/artists/tracks to display names (one round trip per
            # collection, batched).
            await _hydrate_labels(all_docs)

            # Atomic swap: insert the new docs first into a staging collection,
            # then drop+rename. Avoids a window where the dashboard shows
            # half-recomputed data.
            staging = "monthly_analytics_staging"
            await db_bg.drop_collection(staging)
            if all_docs:
                # insert_many requires a stable _id; we leave Mongo to assign one
                await db_bg[staging].insert_many(all_docs, ordered=False)
                # Indexes for the dashboard's main query patterns:
                #   1) `(period, dim)` — full-month slice across all dims
                #   2) `(dim, revenue_idr -1)` — Top-N per dim
                #   3) `(dim, key, period)` — Phase 24: fast lookup per entity id
                #      (used by Artist/Release/Label Management list endpoints)
                await db_bg[staging].create_index([("period", 1), ("dim", 1)])
                await db_bg[staging].create_index([("dim", 1), ("revenue_idr", -1)])
                await db_bg[staging].create_index([("dim", 1), ("key", 1), ("period", 1)])
            await db_bg.drop_collection("monthly_analytics")
            if all_docs:
                # `rename` is atomic on the cluster but requires the target name
                # not to exist — we already dropped it above.
                await db_bg[staging].rename("monthly_analytics")
            duration = (datetime.now(timezone.utc) - t0).total_seconds()
            per_dim_counts: Dict[str, int] = {}
            for d in all_docs:
                per_dim_counts[d["dim"]] = per_dim_counts.get(d["dim"], 0) + 1
            _last_recompute_meta.update({
                "finished_at": now_iso(),
                "duration_sec": round(duration, 2),
                "doc_count": len(all_docs),
                "per_dim_counts": per_dim_counts,
                "last_error": None,
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
                        "last_error": None,
                        "updated_at": now_iso(),
                    }},
                    upsert=True,
                )
            except Exception:
                logger.warning("[ANALYTICS] failed to persist rollup_health doc")
            logger.info("[ANALYTICS] recompute done in %.2fs — %d docs across %d dims",
                        duration, len(all_docs), len(DIMENSIONS))
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
                        "updated_at": now_iso(),
                    }},
                    upsert=True,
                )
            except Exception:
                pass
            raise
        finally:
            _last_recompute_meta["running"] = False


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------

@analytics_r.post("/recompute")
async def admin_recompute_analytics(user: dict = Depends(require_super_admin)):
    """Force-rebuild the monthly_analytics cache from royalty_lines.

    Heavy operation — only super_admin. Triggered automatically post-publish
    and post-delete-import; this endpoint exists for manual recovery (e.g.
    after a hot data fix or migration).
    """
    if _last_recompute_meta.get("running"):
        return {"ok": False, "message": "Recompute already running", "meta": _last_recompute_meta}
    meta = await recompute_monthly_analytics()
    return {"ok": True, "meta": meta}


@analytics_r.get("/status")
async def admin_analytics_status(user: dict = Depends(require_admin)):
    """Tiny status endpoint — used by the dashboard to show 'Last refreshed X
    minutes ago'. Falls back to the persisted `rollup_health` doc when this
    pod hasn't run a rebuild yet (e.g. after a fresh restart).
    """
    meta = dict(_last_recompute_meta)
    if not meta.get("finished_at"):
        try:
            health = await db.rollup_health.find_one({"id": "monthly_analytics"}, {"_id": 0})
            if health:
                meta.update({
                    "finished_at": health.get("finished_at"),
                    "duration_sec": health.get("duration_sec"),
                    "doc_count": health.get("doc_count", 0),
                    "per_dim_counts": health.get("per_dim_counts", {}),
                    "last_error": health.get("last_error"),
                    "last_error_at": health.get("last_error_at"),
                    "from_persisted": True,
                })
        except Exception:
            pass
    return {
        "running": _last_recompute_meta.get("running", False),
        "finished_at": meta.get("finished_at"),
        "duration_sec": meta.get("duration_sec"),
        "doc_count": meta.get("doc_count", 0),
        "per_dim_counts": meta.get("per_dim_counts", {}),
        "last_error": meta.get("last_error"),
        "last_error_at": meta.get("last_error_at"),
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
        line_match: Dict[str, Any] = {"match_status": {"$in": ["matched", "manually_matched"]}}
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
    if not periods:
        # Cache cold — try a quick `distinct` on royalty_lines as fallback
        try:
            raw = await db_bg.royalty_lines.distinct("period")
            periods = sorted([p for p in raw if isinstance(p, str) and len(p) == 7])
        except Exception:
            pass
    return {"periods": periods, "min": periods[0] if periods else None, "max": periods[-1] if periods else None}
