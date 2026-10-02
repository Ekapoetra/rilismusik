"""Contract tests without Mongo credentials: python -m unittest discover -s backend/tests -p test_prototype_v7.py"""
import importlib
import logging
import sys
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

PACKAGE = "_v7_contract_test_routes"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(Path(__file__).resolve().parents[1] / "routes")]
sys.modules[PACKAGE] = package


def permitted(user, permission):
    return user.get("role") == "super_admin" or permission in user.get("permissions", [])


def assert_permission(user, permission):
    if not permitted(user, permission):
        raise HTTPException(403, "denied")


deps = types.ModuleType(f"{PACKAGE}.deps")
deps.db = None
deps.require_admin = lambda: None
deps.has_permission = permitted
deps.assert_admin_permission = assert_permission
deps.logger = logging.getLogger("v7-tests")
sys.modules[deps.__name__] = deps
work = types.ModuleType(f"{PACKAGE}.work_service")
work.work_queue = AsyncMock()
sys.modules[work.__name__] = work
adapter = importlib.import_module(f"{PACKAGE}.prototype_v7")
contract = importlib.import_module(f"{PACKAGE}.v7_workflow")


def source(name):
    return next(spec for spec in contract.SOURCES if spec["source"] == name)


class PresentationTests(unittest.TestCase):
    def test_full_count_is_independent_of_preview_and_pagination(self):
        rows = [contract.presentation_row(source("releases"), {"id": str(i), "status": "submitted"}) for i in range(47)]
        items, summary, _ = contract.summarize(rows + rows[:2])
        self.assertEqual(summary["total"], 47)
        page = contract.page_rows(items, "all", 3, 20)
        self.assertEqual((len(page["items"]), page["total"], page["pages"]), (7, 47, 3))

    def test_waiting_is_a_subset_not_an_extra_total(self):
        rows = [contract.presentation_row(source("support_tickets"), {"id": status, "status": status})
                for status in ("open", "waiting_admin", "waiting_label", "in_progress", "submitted_to_believe", "done")]
        items, summary, _ = contract.summarize(rows)
        self.assertEqual(summary["total"], summary["new"] + summary["in_progress"])
        self.assertEqual((summary["total"], summary["waiting"]), (5, 2))
        self.assertEqual(contract.page_rows(items, "waiting", 1, 20)["total"], 2)

    def test_no_sensitive_sources_for_regular_admin(self):
        user = {"role": "admin_custom", "permissions": ["labels.view", "releases.view"]}
        allowed = {s["source"] for s in contract.SOURCES if contract.may_read_source(s, user, permitted)}
        self.assertEqual(allowed, {"releases"})

    def test_addon_permission_uses_the_existing_singular_key(self):
        self.assertTrue(contract.may_read_source(source("addon_orders"), {"permissions": ["addon.view"]}, permitted))
        self.assertFalse(contract.may_read_source(source("withdraw_requests"), {"permissions": ["payments.view"]}, permitted))

    def test_rows_do_not_return_bank_numbers_or_internal_notes(self):
        row = contract.presentation_row(source("bank_accounts"), {"id": "bank-1", "verified_status": "pending", "account_number": "secret", "internal_note": "private"})
        self.assertNotIn("secret", str(row))
        self.assertNotIn("private", str(row))

    def test_terminal_or_unidentified_records_are_omitted(self):
        self.assertIsNone(contract.presentation_row(source("releases"), {"id": "r1", "status": "live"}))
        self.assertIsNone(contract.presentation_row(source("releases"), {"status": "submitted"}))

    def test_unknown_progress_is_not_fabricated(self):
        row = contract.presentation_row(source("support_tickets"), {"id": "1", "status": "waiting_label"})
        self.assertIsNone(row["percent"])

    def test_identifiers_cannot_change_detail_route(self):
        row = contract.presentation_row(source("releases"), {"id": "x/../y?foo=1", "status": "submitted"})
        self.assertEqual(row["link"], "/admin/releases/x%2F..%2Fy%3Ffoo%3D1")


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_forbidden_before_any_data_read(self):
        with patch.object(adapter, "_read_source", new_callable=AsyncMock) as read:
            with self.assertRaises(HTTPException) as raised:
                await adapter.dashboard_v7(page=1, page_size=20, user={"permissions": []})
            self.assertEqual(raised.exception.status_code, 403)
            read.assert_not_called()

    async def test_queries_only_authorized_collections(self):
        user = {"role": "admin_custom", "permissions": ["dashboard.view", "support.view"]}
        with patch.object(adapter, "_read_source", new_callable=AsyncMock, return_value=[]) as read, patch.object(adapter, "work_queue", new_callable=AsyncMock) as queue:
            result = await adapter.dashboard_v7(page=1, page_size=20, user=user)
            self.assertEqual([call.args[0]["source"] for call in read.call_args_list], ["support_tickets"])
            queue.assert_not_called()
            self.assertIsNone(result["summary"]["completed_today"])

    async def test_database_failure_returns_unavailable_not_zero(self):
        with patch.object(adapter, "_read_source", new_callable=AsyncMock, side_effect=RuntimeError("offline")), self.assertLogs("v7-tests", level="ERROR"):
            with self.assertRaises(HTTPException) as raised:
                await adapter.dashboard_v7(page=1, page_size=20, user={"permissions": ["dashboard.view", "releases.view"]})
            self.assertEqual(raised.exception.status_code, 503)

    async def test_existing_ownership_and_wib_day_boundary(self):
        class FrozenDate(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 9, 20, 17, 30, tzinfo=timezone.utc)
        queue = AsyncMock(side_effect=[{"items": [{"work_type": "sensitive_approval"}], "is_manager": True}, {"items": [{"work_type": "release_review"}], "is_manager": True}])
        count = AsyncMock(return_value=7)
        database = types.SimpleNamespace(work_items=types.SimpleNamespace(count_documents=count))
        with patch.object(adapter, "work_queue", queue), patch.object(adapter, "_read_source", new_callable=AsyncMock, return_value=[]), patch.object(adapter, "db", database), patch.object(adapter, "datetime", FrozenDate):
            result = await adapter.dashboard_v7(page=1, page_size=20, user={"role": "super_admin"})
        self.assertEqual([c.kwargs["scope"] for c in queue.call_args_list], ["my", "team"])
        self.assertEqual(result["my_work"], [{"work_type": "sensitive_approval"}])
        self.assertEqual(result["team_work"], [{"work_type": "release_review"}])
        query = count.call_args.args[0]
        self.assertEqual(set(query["work_type"]["$in"]), {"sensitive_approval", "release_review"})
        self.assertEqual(query["completed_at"]["$gte"], "2026-09-20T17:00:00+00:00")
        self.assertEqual(result["summary"]["completed_today"], 7)


if __name__ == "__main__":
    unittest.main()
