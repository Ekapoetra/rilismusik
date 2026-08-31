"""Phase 51 — admin dashboard total label share withdrawn/unwithdrawn split."""
import asyncio
import os
import uuid

from dotenv import load_dotenv


load_dotenv("/app/backend/.env", override=True)


def test_dashboard_cache_partitions_total_label_share_without_double_counting_legacy():
    from routes import dashboard_cache as module

    async def scenario():
        suffix = uuid.uuid4().hex[:10]
        label_id = f"phase51-label-{suffix}"
        line_ids = [f"phase51-{kind}-{suffix}" for kind in ("withdrawn", "legacy", "draft", "pending", "available")]
        before = await module.recompute()
        await module.db_bg.royalty_lines.insert_many([
            {"id": line_ids[0], "label_id": label_id, "status": "withdrawn", "legacy_settled": False, "label_idr": 100, "revenue_eur": 1},
            {"id": line_ids[1], "label_id": label_id, "status": "pending", "legacy_settled": True, "label_idr": 200, "revenue_eur": 2},
            {"id": line_ids[2], "label_id": label_id, "status": "draft", "legacy_settled": False, "label_idr": 300, "revenue_eur": 3},
            {"id": line_ids[3], "label_id": label_id, "status": "pending", "legacy_settled": False, "label_idr": 400, "revenue_eur": 4},
            {"id": line_ids[4], "label_id": label_id, "status": "available", "legacy_settled": False, "label_idr": 500, "revenue_eur": 5},
        ])
        try:
            after = await module.recompute()
            assert after["total_idr"] - before["total_idr"] == 1500
            assert after["withdrawn_idr"] - before["withdrawn_idr"] == 300
            assert after["unwithdrawn_idr"] - before["unwithdrawn_idr"] == 1200
            assert after["withdrawn_idr"] + after["unwithdrawn_idr"] == after["total_idr"]
            persisted = await module.db_bg.metrics_cache.find_one({"_id": "dashboard_revenue"}, {"_id": 0})
            assert persisted["withdrawn_idr"] == after["withdrawn_idr"]
            assert persisted["unwithdrawn_idr"] == after["unwithdrawn_idr"]
        finally:
            await module.db_bg.royalty_lines.delete_many({"id": {"$in": line_ids}})
            await module.recompute()

    asyncio.run(scenario())