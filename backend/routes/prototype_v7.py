"""V7 dashboard adapter over the existing MongoDB and permission model.

No connection string, separate database, migration, or financial mutation is added.
Counts cover every authorized matching record; only detail rows are paginated.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from .deps import db, require_admin, has_permission, assert_admin_permission, logger
from .work_service import work_queue
from .v7_workflow import SOURCES, may_read_source, presentation_row, summarize, page_rows

prototype_v7_r = APIRouter(prefix="/admin/dashboard", tags=["dashboard-v7"])


async def _read_source(spec):
    field = spec.get("status_field", "status")
    query = {field: {"$in": list(spec["statuses"])}, **spec.get("match", {})}
    projection = {"_id": 0, "id": 1, field: 1, "label_name": 1, "updated_at": 1, "created_at": 1}
    projection.update({name: 1 for name in spec["titles"]})
    rows = []
    async for doc in db[spec["source"]].find(query, projection):
        row = presentation_row(spec, doc)
        if row:
            rows.append(row)
    return rows


@prototype_v7_r.get("/v7")
async def dashboard_v7(
    bucket: Literal["all", "new", "in_progress", "waiting"] = "all",
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(require_admin),
):
    assert_admin_permission(user, "dashboard.view")
    allowed = [s for s in SOURCES if may_read_source(s, user, has_permission)]
    my_work = None
    team_work = None
    is_manager = False
    completed = None
    try:
        if has_permission(user, "work.view"):
            personal = await work_queue(scope="my", user=user)
            my_work = personal["items"]
            is_manager = personal["is_manager"]
            team_work = (await work_queue(scope="team", user=user))["items"] if is_manager else None
            work_types = list({r["work_type"] for r in my_work + (team_work or [])})
            now = datetime.now(timezone.utc)
            wib = timezone(timedelta(hours=7))
            start = now.astimezone(wib).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
            completed = await db.work_items.count_documents({
                "work_type": {"$in": work_types}, "status": "completed",
                "completed_at": {"$gte": start.isoformat(), "$lte": now.isoformat()},
            })
        grouped = await asyncio.gather(*(_read_source(spec) for spec in allowed))
    except Exception:
        logger.exception("Unable to assemble V7 dashboard")
        # An unavailable database is not a zero-work or zero-balance state.
        raise HTTPException(status_code=503, detail="Data dashboard belum dapat dimuat. Silakan coba lagi.")
    items, summary, categories = summarize([row for group in grouped for row in group], completed)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(), "scope": "authorized_records", "summary": summary,
        "details": page_rows(items, bucket, page, page_size), "categories": categories,
        "queue_preview": [r for r in items if r["bucket"] == "new"][:5],
        "in_progress_preview": [r for r in items if r["bucket"] == "in_progress"][:5],
        "my_work": my_work, "team_work": team_work, "is_manager": is_manager,
    }
