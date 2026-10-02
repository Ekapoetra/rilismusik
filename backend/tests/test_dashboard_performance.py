"""Offline behavioral/financial regression checks against the pre-optimization code."""
import asyncio
import copy
import importlib
import inspect
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta, timezone

import test_vercel_preview  # Configures offline environment before real router imports.
from mongomock_motor import AsyncMongoMockClient
from pymongo.errors import BulkWriteError
from fastapi import HTTPException
from fastapi.testclient import TestClient
from routes import work_service as work, labels, dashboard_metrics as metrics, admin_analytics as analytics
from routes import balance_utils, royalty_adjustment_balance, revenue_rollup, releases, kyc_service
from routes.query_concurrency import bounded_gather
from routes.deps import require_super_admin
from vercel_app import app


def oracle(module):
    namespace = dict(module.__dict__)
    name = module.__name__.split('.')[-1]
    source = (Path(__file__).parent / 'fixtures' / f'{name}_baseline.py').read_text()
    exec(compile(source, f'{name}_baseline.py', 'exec'), namespace)
    return namespace


def args_for(function, **updates):
    values = {name: getattr(param.default, 'default', param.default) for name, param in inspect.signature(function).parameters.items()}
    values.update(updates)
    return values


class StableDB:
    # The mock returns a fresh collection wrapper per lookup; keep wrappers stable
    # so instrumentation observes the same objects as the real router.
    def __init__(self, db): self.db, self.collections = db, {}
    def __getitem__(self, name):
        if name not in self.collections: self.collections[name] = self.db[name]
        return self.collections[name]
    def __getattr__(self, name): return self[name]


class PerformanceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = StableDB(AsyncMongoMockClient(tz_aware=True).test)
        self.patches = [patch.object(module, name, self.db) for module, name in (
            (work, 'db'), (labels, 'db'), (metrics, 'db'), (analytics, 'db_bg'),
            (balance_utils, 'db_bg'), (royalty_adjustment_balance, 'db_bg'), (releases, 'db'))]
        for item in self.patches: item.start()
        self.addCleanup(lambda: [item.stop() for item in self.patches])
        self.user = {'id': 'u1', 'role': 'label', 'email': 'label@example.invalid', 'status': 'active'}
        self.label = {'id': 'l1', 'user_id': 'u1', 'last_withdrawn_period': '2026-02', 'account_status': 'active'}
        await self.db.labels.insert_many([self.label, {'id': 'other', 'user_id': 'u2', 'account_status': 'active'}])
        lines = [
            {'label_id': 'l1', 'period': '2026-01', 'status': 'available', 'label_idr': 9000},
            {'label_id': 'l1', 'period': '2026-03', 'status': 'pending', 'label_idr': 300},
            {'label_id': 'l1', 'period': '2026-04', 'status': 'available', 'label_idr': 1000},
            {'label_id': 'l1', 'period': '2026-05', 'status': 'available', 'label_idr': 500, 'legacy_settled': True},
            {'label_id': 'l1', 'period': '2026-06', 'status': 'withdrawn', 'label_idr': 700},
            {'label_id': 'other', 'period': '2026-04', 'status': 'available', 'label_idr': 8000},
        ]
        for index, line in enumerate(lines):
            line.update(id=f'line-{index}', revenue_eur=index + .125, quantity=index + 1, platform='spotify', country='ID', track_id=f't{index}', artist_id=f'a{index}', match_status='matched')
        await self.db.royalty_lines.insert_many(lines)
        await self.db.withdraw_requests.insert_many([
            {'id': 'w1', 'label_id': 'l1', 'status': 'requested', 'amount_idr': 200},
            {'id': 'w2', 'label_id': 'l1', 'status': 'approved', 'amount_idr': 100},
            {'id': 'old', 'label_id': 'l1', 'status': 'requested', 'amount_idr': 999, 'legacy_import': True},
            {'id': 'spent', 'label_id': 'l1', 'status': 'paid', 'amount_idr': 100, 'adjustment_amount_idr': 50},
        ])
        await self.db.balance_transactions.insert_one({'id': 'adj', 'label_id': 'l1', 'type': 'royalty_admin_adjustment', 'status': 'active', 'amount_idr': 150})
        await self.db.releases.insert_many([{'id': f'r{i}', 'label_id': 'l1', 'status': status, 'created_at': f'2026-09-{i+1:02}', 'release_title': f'R{i}'} for i, status in enumerate(['draft','approved','live','delivered','need_revision','unknown'])])
        await self.db.releases.insert_one({'id': 'private', 'label_id': 'other', 'status': 'live', 'created_at': '2026-10-01'})

    async def test_bounded_reads_limit_and_order(self):
        running = peak = 0
        async def read(index):
            nonlocal running, peak
            running += 1; peak = max(peak, running)
            await asyncio.sleep(.002); running -= 1
            return index
        self.assertEqual(await bounded_gather(*(read(i) for i in range(8))), list(range(8)))
        self.assertEqual(peak, 2)

    async def test_failed_read_cancels_pending_reads(self):
        canceled = asyncio.Event()
        async def fail():
            await asyncio.sleep(.001); raise ValueError('fixture')
        async def slow():
            try: await asyncio.sleep(10)
            finally: canceled.set()
        with self.assertRaises(ValueError): await bounded_gather(fail(), slow(), slow())
        self.assertTrue(canceled.is_set())

    async def test_label_dashboard_financial_and_counts_equal_baseline(self):
        baseline = oracle(labels)
        with patch.object(labels, 'get_label_by_user', AsyncMock(return_value=self.label)), patch.object(kyc_service, 'compute_kyc_state', AsyncMock(return_value={'is_verified': True})), patch('routes.deps.db_bg', self.db):
            baseline['get_label_by_user'] = labels.get_label_by_user
            before = await baseline['label_dashboard'](self.user)
            after = await labels.label_dashboard(self.user)
        self.assertEqual({key: value for key, value in after.items() if key != 'balance'}, before)
        self.assertEqual(after['balance']['balance_available_idr'], 800)  # 1000 + 150 - 50 - 200 - 100
        self.assertEqual(after['balance']['balance_pending_idr'], 300)
        self.assertEqual(after['balance']['active_withdraw_ids'], ['w1', 'w2'])
        self.assertEqual(after['stats']['last_month_revenue_idr'], 1000)
        self.assertEqual(after['stats']['total_releases'], 6)
        self.assertEqual(after['stats']['active_releases'], 3)

    async def test_multi_label_balance_isolation_and_cutoff(self):
        first, other = await bounded_gather(balance_utils.compute_label_balance_snapshot(label_id='l1', label=self.label), balance_utils.compute_label_balance_snapshot(label_id='other'))
        self.assertEqual(first['balance_available_idr'], 800)
        self.assertEqual(other['balance_available_idr'], 8000)
        self.assertEqual(first['balance_pending_idr'], 300)
        self.assertEqual(first['latest_report_period'], '2026-06')

    async def test_admin_live_analytics_matches_baseline(self):
        baseline = oracle(analytics)
        for filters in ({'label_id':'l1'}, {'artist_id':'a2'}, {'label_id':'other','period_from':'2026-03','period_to':'2026-06'}, {'platform':'missing'}):
            args = args_for(analytics.admin_monthly_analytics, user={'role':'super_admin'}, **filters)
            before = await baseline['admin_monthly_analytics'](**args)
            after = await analytics.admin_monthly_analytics(**args)
            self.assertEqual(after, before)

    async def test_admin_cache_analytics_matches_baseline(self):
        docs = []
        for period in ('2026-01','2026-03'):
            for dim in ('total','platform','country','label','artist','track'):
                docs.append({'period':period,'dim':dim,'key':dim,'revenue_eur':1.2,'revenue_idr':400,'lines_count':3,'quantity':6, 'label_name':'Label','artist_name':'Artist','track_title':'Track'})
        await self.db.monthly_analytics.insert_many(docs)
        baseline = oracle(analytics)
        for filters in ({}, {'period_from':'2026-03','period_to':'2026-04'}, {'period_from':'2099-01'}):
            args = args_for(analytics.admin_monthly_analytics, user={'role':'super_admin'}, **filters)
            self.assertEqual(await analytics.admin_monthly_analytics(**args), await baseline['admin_monthly_analytics'](**args))

    async def test_release_limit_skips_rollup_and_preserves_label_scope(self):
        with patch.object(releases, 'get_label_by_user', AsyncMock(return_value=self.label)), patch.object(revenue_rollup, 'rollup_revenue_by_id', AsyncMock()) as rollup:
            result = await releases.list_releases(**args_for(releases.list_releases, user=self.user, limit=5, include_revenue=False))
        self.assertEqual(len(result), 5)
        self.assertNotIn('private', [row['id'] for row in result])
        self.assertEqual([row['id'] for row in result], ['r5','r4','r3','r2','r1'])
        rollup.assert_not_called()

    async def test_release_default_still_includes_full_rollup(self):
        with patch.object(releases, 'get_label_by_user', AsyncMock(return_value=self.label)), patch.object(revenue_rollup, 'rollup_revenue_by_id', AsyncMock(return_value={'r1':{'revenue_idr':900}})) as rollup:
            result = await releases.list_releases(**args_for(releases.list_releases, user=self.user))
        self.assertEqual(len(result), 6); rollup.assert_awaited_once()
        self.assertEqual(next(row for row in result if row['id']=='r1')['revenue_idr'], 900)

    async def test_metric_failures_are_not_zero(self):
        with patch.object(self.db.labels, 'estimated_document_count', AsyncMock(side_effect=TimeoutError)):
            with self.assertRaises(HTTPException) as caught: await metrics._est('labels')
        self.assertEqual(caught.exception.status_code, 503)
        with patch.object(self.db.withdraw_requests, 'aggregate', side_effect=TimeoutError):
            with self.assertRaises(HTTPException): await metrics._sum_by_date('withdraw_requests', {}, 'paid_date', datetime.now(timezone.utc), datetime.now(timezone.utc))

    async def test_metrics_defaults_preserve_finance_and_permissions(self):
        baseline = oracle(metrics)
        now = datetime.now(timezone.utc).isoformat()
        await self.db.payments.insert_many([
            {'id':'x','provider':'xendit','status':'paid','amount':12000,'paid_at':now},
            {'id':'not-x','provider':'manual','status':'paid','amount':90000,'paid_at':now},
            {'id':'not-paid','provider':'xendit','status':'pending','amount':70000,'paid_at':now},
        ])
        async def date_sum(collection, match, date_field, cs, ce, field='amount_idr'):
            # mongomock does not implement $convert; its fixture uses known sums.
            return 150 if match.get('status') == 'paid' else 300
        baseline['_sum_by_date'] = date_sum
        with patch.object(metrics, '_sum_by_date', date_sum):
            for role, permissions in [('super_admin', []), ('admin_custom', []), ('admin_custom', ['withdraw.view'])]:
                user = {'role':role,'permissions':permissions}
                before = await baseline['dashboard_metrics'](period='month',user=user)
                after = await metrics.dashboard_metrics(period='month',include_money=True,user=user)
                self.assertEqual(after, before)
                self.assertEqual(after['sales_revenue']['value'], 12000)
                self.assertEqual('requested_withdrawal' in after, role == 'super_admin' or bool(permissions))

    async def test_work_bulk_failure_does_not_stamp_success(self):
        async def discover(kind):
            return [{'source':'releases','entity_id':'x','opened_at':'2026-01-01'}] if kind=='release_review' else []
        with patch.object(work, '_sources', discover), patch.object(self.db.work_items, 'bulk_write', AsyncMock(side_effect=TimeoutError)):
            with self.assertRaises(HTTPException) as caught: await work.reconcile_work(force=True)
        self.assertEqual(caught.exception.status_code, 503)
        state = await self.db.performance_state.find_one({})
        self.assertNotIn('last_success', state)
        self.assertNotIn('owner', state)

    async def test_light_metrics_does_not_compute_money_twice(self):
        with patch.object(metrics, '_sum', AsyncMock()) as sales, patch.object(metrics, '_withdrawal_total', AsyncMock()) as withdraws:
            result = await metrics.dashboard_metrics(period='month', include_money=False, user={'role':'super_admin'})
        sales.assert_not_called(); withdraws.assert_not_called()
        self.assertNotIn('sales_revenue', result)
        self.assertIn('royalty_income', result)

    async def test_work_settings_defaults_do_not_write_during_read(self):
        with patch.object(self.db.admin_ui_settings, 'update_one', AsyncMock()) as update:
            settings = await work.get_work_settings()
            self.assertEqual(settings['sla_days'], work.DEFAULT_SLA_DAYS)
            update.assert_not_called()
        await self.db.admin_ui_settings.insert_one({'key':'work_settings','sla_days':{'release_review':5}})
        self.assertEqual((await work.get_work_settings())['sla_days']['release_review'], 5)

    async def test_worker_mode_reads_projection_without_reconciliation(self):
        with patch.dict('os.environ', {'WORK_RECONCILE_ON_READ':'false'}), patch.object(work, 'reconcile_work', AsyncMock()) as reconcile:
            self.assertTrue((await work.work_read_synchronization())['synchronizing'])
            await self.db.performance_state.insert_one({'_id':work._LEASE_ID,'last_success':datetime.now(timezone.utc)})
            result = await work.work_read_synchronization()
            self.assertFalse(result['synchronizing']); self.assertTrue(result['worker_managed'])
            await self.db.performance_state.update_one({'_id':work._LEASE_ID}, {'$set':{'last_success':datetime.now(timezone.utc)-timedelta(minutes=10)}})
            self.assertTrue((await work.work_read_synchronization())['stale'])
            reconcile.assert_not_called()

    async def test_managed_worker_retries_failure_and_stops(self):
        spec = importlib.util.spec_from_file_location('work_projection_worker', Path(__file__).parents[1] / 'scripts' / 'work_projection_worker.py')
        worker = importlib.util.module_from_spec(spec); spec.loader.exec_module(worker)
        stop = asyncio.Event()
        calls = []
        async def check():
            calls.append(1)
            if len(calls)==1: raise ValueError('private connection details must not be logged')
            stop.set(); return {'synchronizing':False}
        with patch.object(work, 'reconcile_work', check), self.assertLogs('work-worker', level='INFO') as logs:
            await worker.run(0, stop)
        self.assertEqual(len(calls), 2)
        self.assertNotIn('private connection details', '\n'.join(logs.output))

    async def test_worker_mode_rejects_misconfiguration(self):
        with patch.dict('os.environ', {'WORK_RECONCILE_ON_READ':'maybe'}):
            with self.assertRaises(HTTPException): await work.work_read_synchronization()

    async def test_work_batches_1000_new_items_and_skips_existing(self):
        sources = [{'source':'releases','entity_id':str(i),'opened_at':'2026-01-01','ref':'R'} for i in range(1000)]
        async def discover(kind): return sources if kind == 'release_review' else []
        original_bulk = self.db.work_items.bulk_write
        with patch.object(work, '_sources', discover), patch.object(self.db.work_items, 'bulk_write', wraps=original_bulk) as bulk:
            await work.reconcile_work(force=True)
            self.assertEqual(bulk.await_count, 2)
            await work.reconcile_work(force=True)
            self.assertEqual(bulk.await_count, 2)
        self.assertEqual(await self.db.work_items.count_documents({'status':'open'}), 1000)

    async def test_work_duplicate_id_fencing_does_not_hide_other_write_errors(self):
        original = self.db.work_items.bulk_write
        async def discover(kind):
            return [{'source':'releases','entity_id':'race','opened_at':'2026-01-01'}] if kind=='release_review' else []
        async def committed_then_duplicate(writes, **kwargs):
            await original(writes, **kwargs)
            raise BulkWriteError({'writeErrors':[{'code':11000,'keyPattern':{'_id':1}}], 'writeConcernErrors':[]})
        with patch.object(work, '_sources', discover), patch.object(self.db.work_items, 'bulk_write', committed_then_duplicate):
            await work.reconcile_work(force=True)
        self.assertEqual(await self.db.work_items.count_documents({'status':'open'}), 1)
        for error in ({'code':11000,'keyPattern':{'dedupe_key':1}}, {'code':8}):
            async def new_source(kind):
                return [{'source':'releases','entity_id':'failure','opened_at':'2026-01-01'}] if kind=='release_review' else []
            with patch.object(work, '_sources', new_source), patch.object(self.db.work_items, 'bulk_write', AsyncMock(side_effect=BulkWriteError({'writeErrors':[error]}))):
                with self.assertRaises(BulkWriteError): await work.reconcile_work(force=True)

    async def test_work_identity_is_stable_across_failed_retry(self):
        async def discover(kind):
            return [{'source':'releases','entity_id':'stable','opened_at':'2026-01-01'}] if kind=='release_review' else []
        identities = []
        original = self.db.work_items.bulk_write
        async def failed(writes, **kwargs):
            identities.append(writes[0]._filter['_id'])
            raise TimeoutError()
        async def succeeded(writes, **kwargs):
            identities.append(writes[0]._filter['_id'])
            return await original(writes, **kwargs)
        with patch.object(work, '_sources', discover):
            with patch.object(self.db.work_items, 'bulk_write', failed):
                with self.assertRaises(HTTPException): await work.reconcile_work(force=True)
            with patch.object(self.db.work_items, 'bulk_write', succeeded): await work.reconcile_work(force=True)
        self.assertEqual(identities[0], identities[1])
        self.assertEqual(await self.db.work_items.count_documents({'status':'open'}), 1)

    async def test_work_completion_reopen_preserves_history_and_actor(self):
        state = [{'source':'releases','entity_id':'new','opened_at':'2026-01-01','ref':'R'}]
        async def discover(kind): return list(state) if kind == 'release_review' else []
        await self.db.users.insert_one({'id':'admin','name':'Admin','role':'super_admin'})
        with patch.object(work, '_sources', discover), patch.object(work, '_resolve_completion', AsyncMock(return_value=('admin','2026-10-01','approved'))):
            await work.reconcile_work(force=True)
            first = await self.db.work_items.find_one({'status':'open'})
            state.clear(); await work.reconcile_work(force=True)
            closed = await self.db.work_items.find_one({'id':first['id']})
            self.assertEqual(closed['status'], 'completed'); self.assertEqual(closed['completed_by_name'], 'Admin'); self.assertTrue(closed['completed_by_super'])
            state.append({'source':'releases','entity_id':'new','opened_at':'2026-02-01','ref':'R'})
            await work.reconcile_work(force=True)
        reopened = await self.db.work_items.find_one({'status':'open'})
        self.assertNotEqual(first['id'], reopened['id']); self.assertEqual(await self.db.work_items.count_documents({}), 2)

    async def test_work_lease_suppresses_concurrent_instances_and_success_stamp(self):
        entered, release = asyncio.Event(), asyncio.Event()
        async def discover(kind):
            if kind == 'release_review': entered.set(); await release.wait()
            return []
        with patch.object(work, '_sources', discover):
            leader = asyncio.create_task(work.reconcile_work(force=True)); await entered.wait()
            follower = await work.reconcile_work(force=True)
            self.assertTrue(follower['synchronizing']); self.assertIsNone(follower['last_success'])
            release.set(); await leader
            state = await self.db.performance_state.find_one({})
            self.assertNotIn('owner', state); self.assertIn('last_success', state)
            with patch.object(work, '_sources', AsyncMock()) as discover_again:
                self.assertFalse((await work.reconcile_work())['synchronizing']); discover_again.assert_not_called()

    async def test_work_failure_releases_lease_without_success(self):
        with patch.object(work, '_sources', AsyncMock(side_effect=ValueError('fixture'))):
            with self.assertRaises(ValueError): await work.reconcile_work(force=True)
        state = await self.db.performance_state.find_one({})
        self.assertNotIn('last_success', state); self.assertNotIn('owner', state)
        with patch.object(work, '_sources', AsyncMock(return_value=[])):
            self.assertFalse((await work.reconcile_work())['synchronizing'])

    async def test_expired_work_lease_can_be_recovered(self):
        await self.db.performance_state.insert_one({'_id':work._LEASE_ID, 'owner':'dead', 'lease_until':datetime.now(timezone.utc)-timedelta(seconds=1)})
        with patch.object(work, '_sources', AsyncMock(return_value=[])):
            self.assertFalse((await work.reconcile_work())['synchronizing'])

    async def test_work_scope_matches_baseline_and_combined_is_disjoint(self):
        await self.db.admin_roles.insert_one({'id':'release-role','key':'release-role','active':True,'permissions':['releases.review','releases.go_live']})
        await self.db.users.insert_one({'id':'staff','role':'admin_custom','admin_role_id':'release-role','status':'active'})
        baseline = oracle(work); baseline['reconcile_work'] = AsyncMock(); baseline['get_work_settings'] = work.get_work_settings
        for user in ({'role':'super_admin'}, {'role':'admin_custom','permissions':['work.view','releases.review']}, {'role':'admin_custom','permissions':['work.view','work.manage','support.view']}):
            with patch.object(work, 'reconcile_work', AsyncMock(return_value={'synchronizing':False})), patch.object(work, 'assert_admin_permission'), patch.object(work, 'has_permission', side_effect=lambda u,p: u['role']=='super_admin' or p in u.get('permissions',[])):
                baseline['assert_admin_permission'] = work.assert_admin_permission; baseline['has_permission'] = work.has_permission
                combined = await work.work_queue('all', user)
                self.assertTrue(set(row['work_type'] for row in combined['items']).isdisjoint(row['work_type'] for row in combined['team_items']))
                for scope in ('my','team'):
                    if scope == 'team' and not combined['is_manager']: continue
                    old = await baseline['work_queue'](scope, user)
                    new = await work.work_queue(scope, user)
                    self.assertEqual(new['items'], old['items'])
                    self.assertEqual(combined['items'] if scope=='my' else combined['team_items'], old['items'])
        with patch.object(work, 'reconcile_work', AsyncMock(return_value={})), patch.object(work, 'assert_admin_permission'):
            with self.assertRaises(HTTPException): await work.work_queue('team', {'role':'admin_custom','permissions':[]})


class PerformanceHttpTests(unittest.TestCase):
    def test_diagnostics_requires_super_admin_and_releases_validate_limit(self):
        client = TestClient(app)
        self.assertEqual(client.get('/api/admin/performance-check').status_code, 401)
        from routes.deps import require_kyc_for_label_user
        app.dependency_overrides[require_kyc_for_label_user] = lambda: {'role':'super_admin'}
        try:
            for limit in (0,501): self.assertEqual(client.get(f'/api/releases/?limit={limit}').status_code, 422)
        finally: app.dependency_overrides.pop(require_kyc_for_label_user, None)

    def test_diagnostics_returns_only_bounded_statistics(self):
        from routes import performance_diagnostics as diagnostics
        database = SimpleNamespace(command=AsyncMock(return_value={
            'queryPlanner': {'winningPlan': {'stage':'FETCH','inputStage': {'stage':'IXSCAN','indexName':'status_1'}}},
            'executionStats': {'nReturned':20,'executionTimeMillis':3,'totalKeysExamined':20,'totalDocsExamined':20},
            'private_document': {'password':'secret'},
        }))
        class MetadataDB:
            def __getitem__(self, name):
                return SimpleNamespace(list_indexes=lambda: SimpleNamespace(to_list=AsyncMock(return_value=[{'name':'_id_','key':{'_id':1},'unique':True}])))
            command = database.command
            performance_state = SimpleNamespace(find_one=AsyncMock(return_value={}))
        app.dependency_overrides[require_super_admin] = lambda: {'role':'super_admin'}
        try:
            with patch.object(diagnostics, 'db', MetadataDB()):
                response = TestClient(app).get('/api/admin/performance-check?include_explain=true&label_id=l1')
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('private_document', response.text); self.assertNotIn('secret', response.text)
            self.assertEqual(len(response.json()['explain']), 3)
            for call in database.command.await_args_list:
                self.assertEqual(call.args[0]['explain']['maxTimeMS'], 1500)
                self.assertEqual(call.args[0]['explain']['limit'], 20)
            self.assertEqual(response.json()['explain'][0]['indexes'], ['status_1'])
        finally: app.dependency_overrides.pop(require_super_admin, None)

    def test_api_timing_and_no_store(self):
        response = TestClient(app).get('/api/health')
        self.assertIn('app;dur=', response.headers['server-timing'])
        self.assertEqual(response.headers['cache-control'], 'no-store')


if __name__ == '__main__': unittest.main()
