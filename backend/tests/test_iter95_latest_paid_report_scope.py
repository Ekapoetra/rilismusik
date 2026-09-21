"""Regression tests for the label royalty report scope after a paid withdrawal.

The report scope is intentionally different from the withdrawable-balance scope:
- legacy-settled Believe history stays hidden;
- only the latest paid non-legacy web withdrawal is re-exposed as withdrawn;
- current pending/available rows are visible only after last_withdrawn_period.
"""
import pytest

from routes import royalty


class _FakeWithdrawRequests:
    def __init__(self, result):
        self.result = result
        self.last_filter = None
        self.last_projection = None
        self.last_sort = None

    async def find_one(self, filt, projection=None, sort=None):
        self.last_filter = filt
        self.last_projection = projection
        self.last_sort = sort
        return self.result


class _FakeDB:
    def __init__(self, latest_paid):
        self.withdraw_requests = _FakeWithdrawRequests(latest_paid)


@pytest.mark.asyncio
async def test_label_report_scope_includes_latest_paid_web_withdrawal_and_post_cutoff_current(monkeypatch):
    latest_paid = {
        "period_from": "2026-05",
        "period_to": "2026-06",
        "paid_date": "2026-07-18T10:00:00+00:00",
        "created_at": "2026-07-01T10:00:00+00:00",
    }
    fake_db = _FakeDB(latest_paid)
    monkeypatch.setattr(royalty, "db", fake_db)

    scope = await royalty._label_customer_report_scope({
        "id": "label-1",
        "last_withdrawn_period": "2026-06",
    })

    assert scope["label_id"] == "label-1"
    assert len(scope["$or"]) == 2

    current, latest_withdrawn = scope["$or"]
    assert current == {
        "status": {"$in": ["pending", "available"]},
        "legacy_settled": {"$ne": True},
        "period": {"$gt": "2026-06"},
    }
    assert latest_withdrawn == {
        "status": "withdrawn",
        "legacy_settled": {"$ne": True},
        "period": {"$gte": "2026-05", "$lte": "2026-06"},
    }

    # The lookup itself must exclude legacy/history-only withdrawals.
    assert fake_db.withdraw_requests.last_filter["label_id"] == "label-1"
    assert fake_db.withdraw_requests.last_filter["status"] == "paid"
    assert fake_db.withdraw_requests.last_filter["legacy_import"] == {"$ne": True}
    assert fake_db.withdraw_requests.last_filter["adjustment_only"] == {"$ne": True}
    assert fake_db.withdraw_requests.last_sort == [
        ("paid_date", -1),
        ("created_at", -1),
    ]


@pytest.mark.asyncio
async def test_label_report_scope_without_web_paid_withdrawal_keeps_only_current_unsettled(monkeypatch):
    fake_db = _FakeDB(None)
    monkeypatch.setattr(royalty, "db", fake_db)

    scope = await royalty._label_customer_report_scope({
        "id": "label-2",
        "last_withdrawn_period": "2025-12",
    })

    assert scope == {
        "label_id": "label-2",
        "$or": [{
            "status": {"$in": ["pending", "available"]},
            "legacy_settled": {"$ne": True},
            "period": {"$gt": "2025-12"},
        }],
    }


@pytest.mark.asyncio
async def test_label_report_scope_without_any_cutoff_shows_all_current_unsettled(monkeypatch):
    fake_db = _FakeDB(None)
    monkeypatch.setattr(royalty, "db", fake_db)

    scope = await royalty._label_customer_report_scope({
        "id": "label-new",
        "last_withdrawn_period": None,
    })

    assert scope == {
        "label_id": "label-new",
        "$or": [{
            "status": {"$in": ["pending", "available"]},
            "legacy_settled": {"$ne": True},
        }],
    }
