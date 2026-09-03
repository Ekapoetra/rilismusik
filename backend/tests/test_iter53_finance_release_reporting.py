"""Iteration 53 — release ordering + finance reporting regression on public preview API."""
import os
import uuid
from datetime import datetime, timezone

import pymongo
import requests

from tests.support_config import FINANCE


# Modules/features under test: /api/admin/releases, /api/admin/payments/summary, /api/withdraw/admin, /api/withdraw/admin/summary
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


def _db():
    return pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _finance_headers() -> dict:
    login = requests.post(f"{API}/auth/login", json=FINANCE, timeout=30)
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_admin_releases_default_priority_status_and_recency_order():
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    label_id = f"iter53-label-{suffix}"
    now_iso = datetime.now(timezone.utc).isoformat()
    db.labels.insert_one({
        "id": label_id,
        "label_name": f"Iter53 Label {suffix}",
        "email": f"iter53-{suffix}@example.com",
        "created_at": now_iso,
        "updated_at": now_iso,
    })
    status_order = [
        "submitted",
        "awaiting_payment",
        "paid",
        "under_review",
        "need_revision",
        "approved",
        "delivered",
        "draft",
        "live",
    ]
    release_ids = []
    docs = []
    for index, status in enumerate(status_order):
        rid = f"iter53-release-{status}-{suffix}"
        release_ids.append(rid)
        docs.append({
            "id": rid,
            "label_id": label_id,
            "release_title": f"Iter53 {status} {suffix}",
            "status": status,
            "created_at": f"2096-09-{10 + index:02d}T00:00:00+00:00",
            "updated_at": f"2096-09-{10 + index:02d}T00:00:00+00:00",
            "submitted_at": f"2096-09-{10 + index:02d}T00:00:00+00:00",
        })
    # same-status recency check for submitted
    newest_submitted_id = f"iter53-release-submitted-newest-{suffix}"
    oldest_submitted_id = f"iter53-release-submitted-oldest-{suffix}"
    release_ids.extend([newest_submitted_id, oldest_submitted_id])
    docs.extend([
        {
            "id": newest_submitted_id,
            "label_id": label_id,
            "release_title": f"Iter53 submitted newest {suffix}",
            "status": "submitted",
            "created_at": "2096-09-28T00:00:00+00:00",
            "updated_at": "2096-09-28T00:00:00+00:00",
            "submitted_at": "2096-09-28T00:00:00+00:00",
        },
        {
            "id": oldest_submitted_id,
            "label_id": label_id,
            "release_title": f"Iter53 submitted oldest {suffix}",
            "status": "submitted",
            "created_at": "2096-09-01T00:00:00+00:00",
            "updated_at": "2096-09-01T00:00:00+00:00",
            "submitted_at": "2096-09-01T00:00:00+00:00",
        },
    ])
    unknown_id = f"iter53-release-unknown-{suffix}"
    release_ids.append(unknown_id)
    docs.append({
        "id": unknown_id,
        "label_id": label_id,
        "release_title": f"Iter53 unknown {suffix}",
        "status": "archived_unknown",
        "created_at": "2096-10-01T00:00:00+00:00",
        "updated_at": "2096-10-01T00:00:00+00:00",
        "submitted_at": "2096-10-01T00:00:00+00:00",
    })

    db.releases.insert_many(docs)
    try:
        response = requests.get(f"{API}/admin/releases", headers=_finance_headers(), timeout=30)
        assert response.status_code == 200, response.text
        rows = response.json()
        subset = [row for row in rows if row.get("id") in set(release_ids)]
        subset_ids = [row["id"] for row in subset]
        assert len(subset_ids) == len(release_ids)
        assert "_id" not in subset[0]

        assert subset_ids[0] == newest_submitted_id
        assert subset_ids[1] == release_ids[0]
        assert subset_ids[2] == oldest_submitted_id
        expected_rest = release_ids[1:9] + [unknown_id]
        assert subset_ids[3:] == expected_rest
    finally:
        db.releases.delete_many({"id": {"$in": release_ids}})
        db.labels.delete_many({"id": label_id})


def test_admin_payments_summary_counts_only_paid_with_paid_at_amount_and_rejects_invalid_period():
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    label_id = f"iter53-payment-label-{suffix}"
    now_iso = datetime.now(timezone.utc).isoformat()
    db.labels.insert_one({
        "id": label_id,
        "label_name": f"Iter53 Payment {suffix}",
        "email": f"iter53-payment-{suffix}@example.com",
        "created_at": now_iso,
        "updated_at": now_iso,
    })
    payment_ids = [
        f"iter53-pay-sep-100-{suffix}",
        f"iter53-pay-sep-50-{suffix}",
        f"iter53-pay-aug-70-{suffix}",
        f"iter53-pay-sep-pending-{suffix}",
        f"iter53-pay-sep-no-paid-at-{suffix}",
    ]
    docs = [
        {
            "id": payment_ids[0], "label_id": label_id, "status": "paid", "type": "custom_service",
            "amount": 100_000, "reference_id": payment_ids[0], "paid_at": "2099-09-10T10:00:00+07:00", "created_at": now_iso,
        },
        {
            "id": payment_ids[1], "label_id": label_id, "status": "paid", "type": "custom_service",
            "amount": 50_000, "reference_id": payment_ids[1], "paid_at": "2099-09-12T09:00:00+07:00", "created_at": now_iso,
        },
        {
            "id": payment_ids[2], "label_id": label_id, "status": "paid", "type": "custom_service",
            "amount": 70_000, "reference_id": payment_ids[2], "paid_at": "2099-08-05T11:00:00+07:00", "created_at": now_iso,
        },
        {
            "id": payment_ids[3], "label_id": label_id, "status": "pending", "type": "custom_service",
            "amount": 999_000, "reference_id": payment_ids[3], "paid_at": "2099-09-20T11:00:00+07:00", "created_at": now_iso,
        },
        {
            "id": payment_ids[4], "label_id": label_id, "status": "paid", "type": "custom_service",
            "amount": 777_000, "reference_id": payment_ids[4], "created_at": now_iso,
        },
    ]
    db.payments.insert_many(docs)
    try:
        headers = _finance_headers()
        summary = requests.get(
            f"{API}/admin/payments/summary",
            params={"year": 2099, "month": 9},
            headers=headers,
            timeout=30,
        )
        assert summary.status_code == 200, summary.text
        body = summary.json()
        assert body["selected"]["amount_idr"] == 150_000
        assert body["selected"]["count"] == 2
        assert body["year_total"]["amount_idr"] == 220_000
        assert body["year_total"]["count"] == 3
        assert len(body["monthly"]) == 12
        august = next(row for row in body["monthly"] if row["month"] == 8)
        assert august["amount_idr"] == 70_000
        assert august["count"] == 1
        assert 2099 in body["available_years"]

        bad_year = requests.get(
            f"{API}/admin/payments/summary",
            params={"year": 1999, "month": 9},
            headers=headers,
            timeout=30,
        )
        assert bad_year.status_code == 422
        bad_month = requests.get(
            f"{API}/admin/payments/summary",
            params={"year": 2099, "month": 13},
            headers=headers,
            timeout=30,
        )
        assert bad_month.status_code == 422
    finally:
        db.payments.delete_many({"id": {"$in": payment_ids}})
        db.labels.delete_many({"id": label_id})


def test_withdraw_admin_summary_pending_and_outgoing_are_date_scoped_correctly():
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    label_id = f"iter53-withdraw-label-{suffix}"
    now_iso = datetime.now(timezone.utc).isoformat()
    db.labels.insert_one({
        "id": label_id,
        "label_name": f"Iter53 Withdraw {suffix}",
        "email": f"iter53-withdraw-{suffix}@example.com",
        "created_at": now_iso,
        "updated_at": now_iso,
    })
    ids = [
        f"iter53-wd-req-20-{suffix}",
        f"iter53-wd-app-30-{suffix}",
        f"iter53-wd-paid-sep-40-{suffix}",
        f"iter53-wd-rej-10-{suffix}",
        f"iter53-wd-paid-aug-60-{suffix}",
    ]
    db.withdraw_requests.insert_many([
        {"id": ids[0], "label_id": label_id, "status": "requested", "amount_idr": 20_000, "request_date": "2098-09-03T00:00:00+07:00", "created_at": now_iso, "updated_at": now_iso},
        {"id": ids[1], "label_id": label_id, "status": "approved", "amount_idr": 30_000, "request_date": "2098-09-04T00:00:00+07:00", "created_at": now_iso, "updated_at": now_iso},
        {"id": ids[2], "label_id": label_id, "status": "paid", "amount_idr": 40_000, "request_date": "2098-08-30T00:00:00+07:00", "paid_date": "2098-09-05T00:00:00+07:00", "created_at": now_iso, "updated_at": now_iso},
        {"id": ids[3], "label_id": label_id, "status": "rejected", "amount_idr": 10_000, "request_date": "2098-09-06T00:00:00+07:00", "created_at": now_iso, "updated_at": now_iso},
        {"id": ids[4], "label_id": label_id, "status": "paid", "amount_idr": 60_000, "request_date": "2098-09-01T00:00:00+07:00", "paid_date": "2098-08-25T00:00:00+07:00", "created_at": now_iso, "updated_at": now_iso},
    ])
    try:
        response = requests.get(
            f"{API}/withdraw/admin/summary",
            params={"year": 2098, "month": 9},
            headers=_finance_headers(),
            timeout=30,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["pending"]["amount_idr"] == 50_000
        assert body["pending"]["count"] == 2
        assert body["outgoing"]["amount_idr"] == 40_000
        assert body["outgoing"]["count"] == 1
        assert body["year_total"]["outgoing_idr"] == 100_000
        august = next(row for row in body["monthly"] if row["month"] == 8)
        assert august["outgoing_idr"] == 60_000
        assert 2098 in body["available_years"]
    finally:
        db.withdraw_requests.delete_many({"id": {"$in": ids}})
        db.labels.delete_many({"id": label_id})


def test_withdraw_admin_list_filters_paid_by_paid_date_and_requires_year_month_pair():
    db = _db()
    suffix = uuid.uuid4().hex[:8]
    label_id = f"iter53-wd-list-label-{suffix}"
    now_iso = datetime.now(timezone.utc).isoformat()
    db.labels.insert_one({
        "id": label_id,
        "label_name": f"Iter53 Withdraw List {suffix}",
        "email": f"iter53-withdraw-list-{suffix}@example.com",
        "created_at": now_iso,
        "updated_at": now_iso,
    })
    ids = {
        "requested_sep": f"iter53-wd-list-requested-sep-{suffix}",
        "approved_sep": f"iter53-wd-list-approved-sep-{suffix}",
        "paid_sep": f"iter53-wd-list-paid-sep-{suffix}",
        "paid_aug": f"iter53-wd-list-paid-aug-{suffix}",
    }
    db.withdraw_requests.insert_many([
        {"id": ids["requested_sep"], "label_id": label_id, "status": "requested", "amount_idr": 20_000, "request_date": "2097-09-03T00:00:00+07:00", "created_at": now_iso, "updated_at": now_iso},
        {"id": ids["approved_sep"], "label_id": label_id, "status": "approved", "amount_idr": 30_000, "request_date": "2097-09-05T00:00:00+07:00", "created_at": now_iso, "updated_at": now_iso},
        {"id": ids["paid_sep"], "label_id": label_id, "status": "paid", "amount_idr": 40_000, "request_date": "2097-08-25T00:00:00+07:00", "paid_date": "2097-09-06T00:00:00+07:00", "created_at": now_iso, "updated_at": now_iso},
        {"id": ids["paid_aug"], "label_id": label_id, "status": "paid", "amount_idr": 60_000, "request_date": "2097-09-02T00:00:00+07:00", "paid_date": "2097-08-28T00:00:00+07:00", "created_at": now_iso, "updated_at": now_iso},
    ])
    try:
        headers = _finance_headers()
        combined = requests.get(
            f"{API}/withdraw/admin",
            params={"year": 2097, "month": 9},
            headers=headers,
            timeout=30,
        )
        assert combined.status_code == 200, combined.text
        combined_ids = {row["id"] for row in combined.json()}
        assert ids["requested_sep"] in combined_ids
        assert ids["approved_sep"] in combined_ids
        assert ids["paid_sep"] in combined_ids
        assert ids["paid_aug"] not in combined_ids

        paid_only = requests.get(
            f"{API}/withdraw/admin",
            params={"status": "paid", "year": 2097, "month": 9},
            headers=headers,
            timeout=30,
        )
        assert paid_only.status_code == 200, paid_only.text
        paid_ids = {row["id"] for row in paid_only.json()}
        assert paid_ids == {ids["paid_sep"]}

        requested_only = requests.get(
            f"{API}/withdraw/admin",
            params={"status": "requested", "year": 2097, "month": 9},
            headers=headers,
            timeout=30,
        )
        assert requested_only.status_code == 200, requested_only.text
        requested_ids = {row["id"] for row in requested_only.json()}
        assert requested_ids == {ids["requested_sep"]}

        invalid_pair = requests.get(
            f"{API}/withdraw/admin",
            params={"year": 2097},
            headers=headers,
            timeout=30,
        )
        assert invalid_pair.status_code == 400
    finally:
        db.withdraw_requests.delete_many({"id": {"$in": list(ids.values())}})
        db.labels.delete_many({"id": label_id})
