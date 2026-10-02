"""Authenticated, bounded, read-only diagnostics; never return source documents."""
import os
from fastapi import APIRouter, Depends, Query
from .deps import db, client, require_super_admin
from .query_concurrency import bounded_gather

performance_r = APIRouter(prefix="/admin", tags=["performance"])


def plan_summary(plan):
    stages, indexes = set(), set()
    def visit(value):
        if isinstance(value, dict):
            if value.get("stage"): stages.add(value["stage"])
            if value.get("indexName"): indexes.add(value["indexName"])
            for child in value.values(): visit(child)
        elif isinstance(value, list):
            for child in value: visit(child)
    visit(plan.get("queryPlanner", {}).get("winningPlan", {}))
    stats = plan.get("executionStats", {})
    return {"stages": sorted(stages), "indexes": sorted(indexes),
            **{key: stats.get(key) for key in ("nReturned", "executionTimeMillis", "totalKeysExamined", "totalDocsExamined")}}


@performance_r.get("/performance-check")
async def performance_check(include_explain: bool = Query(False), label_id: str | None = Query(None),
                            user: dict = Depends(require_super_admin)):
    async def indexes(name):
        try:
            rows = await db[name].list_indexes().to_list(None)
            return {"collection": name, "indexes": [{"name": row["name"], "key": dict(row["key"]),
                    "unique": bool(row.get("unique"))} for row in rows]}
        except Exception:
            return {"collection": name, "error": "Metadata indeks belum dapat dibaca."}
    names = ("work_items", "monthly_analytics", "royalty_lines", "releases", "activity_logs")
    result = {"vercel_region": os.environ.get("VERCEL_REGION") or "unknown",
              "atlas_region": "Periksa region cluster pada akun Atlas; tidak disimpulkan dari hostname.",
              "primary_max_pool_size": client.options.pool_options.max_pool_size,
              "collections": await bounded_gather(*(indexes(name) for name in names))}
    if include_explain:
        queries = {"work_open": ("work_items", {"status": "open"}),
                   "analytics_totals": ("monthly_analytics", {"dim": "total"})}
        if label_id:
            queries["label_royalty"] = ("royalty_lines", {"label_id": label_id, "status": {"$in": ["pending", "available"]}, "legacy_settled": {"$ne": True}})
        async def explain(name, collection, match):
            try:
                plan = await db.command({"explain": {"find": collection, "filter": match,
                                        "limit": 20, "maxTimeMS": 1500}, "verbosity": "executionStats"})
                return {"query": name, **plan_summary(plan)}
            except Exception:
                return {"query": name, "error": "Explain belum selesai atau izin tidak tersedia (batas 1500 ms)."}
        result["explain"] = await bounded_gather(*(explain(name, *query) for name, query in queries.items()))
        result["explain_scope"] = "Sampel find 20 dokumen, bukan benchmark agregasi finansial lengkap."
    return result
