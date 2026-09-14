"""Admin dashboard aggregation service."""
import asyncio

from .deps import db
from .dashboard_cache import get_stale_while_revalidate
from .payment_admin_service import count_actionable_payments


async def build_admin_dashboard() -> dict:
    count_queries = [
        db.labels.count_documents({}),
        db.artists.count_documents({}),
        db.releases.count_documents({}),
        db.releases.count_documents({"status": "under_review"}),
        db.releases.count_documents({"status": "delivered"}),
        db.releases.count_documents({"status": "live"}),
        db.payments.count_documents({"status": "pending"}),
        db.payments.count_documents({"status": "paid"}),
        db.withdraw_requests.count_documents({"status": "requested"}),
        db.support_tickets.count_documents({"status": {"$nin": ["done", "rejected"]}}),
        db.labels.count_documents({"subscription_status": "active"}),
        db.labels.count_documents({"account_status": "suspended"}),
        db.kyc_documents.count_documents({"status": "pending_review", "is_current": True}),
        db.wami_orders.count_documents({"status": {"$in": ["pending", "in_progress"]}}),
        db.service_orders.count_documents({"status": {"$in": ["paid", "in_progress"]}}),
    ]
    values, revenue, last_csv, actionable_payments = await asyncio.gather(
        asyncio.gather(*count_queries),
        get_stale_while_revalidate(),
        db.royalty_imports.find_one({}, {"_id": 0}, sort=[("created_at", -1)]),
        count_actionable_payments(),
    )
    keys = [
        "total_labels", "total_artists", "total_releases", "pending_review",
        "delivered", "live", "pending_invoices", "paid_invoices",
        "pending_withdraws", "active_tickets", "active_subscriptions", "suspended_labels",
        "pending_kyc",
        "pending_wami", "pending_custom_services",
    ]
    result = dict(zip(keys, values))
    result["pending_addons"] = result.get("pending_wami", 0) + result.get("pending_custom_services", 0)
    result.update({
        "total_revenue_eur": revenue["total_eur"],
        "total_revenue_idr": revenue["total_idr"],
        "total_label_withdrawn_idr": revenue["withdrawn_idr"],
        "total_label_unwithdrawn_idr": revenue["unwithdrawn_idr"],
        "revenue_cache_age_sec": revenue.get("age_sec"),
        "last_csv_import": last_csv,
        "actionable_payments": actionable_payments,
    })
    return result