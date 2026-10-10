"""Offline production regressions. No live accounts, money, storage or emails."""
import asyncio
import gzip
import hashlib
import importlib
import io
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.update({"MONGO_URL": "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=100",
    "DB_NAME": "vercel_production_test", "UPLOAD_DIR": "/tmp/rilismusik/uploads", "RILISMUSIK_SERVERLESS_RUNTIME": "1", "JWT_SECRET": "unit-test-only-secret",
    "FRONTEND_URL": "https://preview.example.invalid", "SMTP_HOST": "smtp.example.invalid",
    "SMTP_PORT": "465", "SMTP_USER": "", "SMTP_PASSWORD": "", "SENDER_EMAIL": "test@example.invalid",
    "SENDER_NAME": "Test", "R2_ENDPOINT_URL": "", "R2_ACCESS_KEY_ID": "", "R2_SECRET_ACCESS_KEY": "", "R2_BUCKET": ""})
from mongomock_motor import AsyncMongoMockClient
from bson import json_util
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from fastapi.testclient import TestClient
import httpx
import background_runtime as runtime
import storage_service
import routes.deps as deps
from background_task_registry import TASKS
from vercel_production_app import app
from routes import direct_uploads as uploads, royalty, admin_analytics


class DurableJobTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = AsyncMongoMockClient().test
        self.objects = {}
        async def put(*, key, data, **kwargs): self.objects[key] = data
        async def get(*, key): return self.objects[key]
        self.patches = [patch.object(deps, 'db_bg', self.db),
            patch.object(storage_service, 'upload_bytes', side_effect=put),
            patch.object(storage_service, 'download_bytes', side_effect=get),
            patch('vercel.queue.send', new_callable=AsyncMock)]
        self.mocks = [p.start() for p in self.patches]
        self.send = self.mocks[-1]
    async def asyncTearDown(self):
        for p in reversed(self.patches): p.stop()

    async def test_dispatch_only_contains_task_id_and_done_is_not_reexecuted(self):
        task = await runtime.run_background(runtime.record_runtime_probe, deployment='test')
        self.assertEqual(self.send.call_args.args[1], {'task_id': task})
        await runtime.consume_task(task)
        await runtime.consume_task(task)
        doc = await self.db.serverless_tasks.find_one({'_id': task})
        self.assertEqual(doc['status'], 'done')
        self.assertEqual(doc['attempts'], 1)
        self.assertEqual((await self.db.serverless_probes.find_one({'_id': 'test'}))['status'], 'done')

    async def test_overlapping_delivery_retries_instead_of_acknowledging(self):
        task = await runtime.run_background(runtime.record_runtime_probe, deployment='test')
        await self.db.serverless_tasks.update_one({'_id': task}, {'$set': {'lease_until': time.time()+900}})
        with self.assertRaisesRegex(RuntimeError, 'leased'): await runtime.consume_task(task)
        self.assertIsNone(await self.db.serverless_probes.find_one({'_id': 'test'}))

    async def test_failed_dispatch_is_recovered_from_outbox(self):
        self.send.side_effect = RuntimeError('offline')
        with self.assertRaises(RuntimeError): await runtime.run_background(runtime.record_runtime_probe, deployment='test')
        doc = await self.db.serverless_tasks.find_one({})
        self.assertEqual(doc['status'], 'pending_dispatch')
        self.send.side_effect = None
        self.assertEqual(await runtime.recover_pending_dispatches(), 1)
        await runtime.consume_task(doc['_id'])
        self.assertEqual((await self.db.serverless_tasks.find_one({}))['status'], 'done')

    async def test_fast_consumer_completion_is_not_overwritten_by_publisher(self):
        async def fast_send(topic, payload, **kwargs):
            await runtime.consume_task(payload['task_id'])
            return 'message'
        self.send.side_effect = fast_send
        task = await runtime.run_background(runtime.record_runtime_probe, deployment='test')
        self.assertEqual((await self.db.serverless_tasks.find_one({'_id': task}))['status'], 'done')

    async def test_deterministic_dispatch_is_debounced(self):
        task = 'a'*32
        await asyncio.gather(*(runtime.run_background(runtime.record_runtime_probe, deployment='test', _dispatch_id=task) for _ in range(5)))
        self.assertEqual(await self.db.serverless_tasks.count_documents({}), 1)
        self.assertEqual(self.send.await_count, 1)

    async def test_retry_clears_lease_and_preserves_completion_boundary(self):
        task = await runtime.run_background(runtime.record_runtime_probe, deployment='test')
        with patch.object(runtime, 'record_runtime_probe', side_effect=runtime.JobContinuation('checkpoint')):
            with self.assertRaises(runtime.JobContinuation): await runtime.consume_task(task)
        doc = await self.db.serverless_tasks.find_one({'_id': task})
        self.assertEqual(doc['status'], 'retry'); self.assertNotIn('lease_until', doc)
        await runtime.consume_task(task)
        self.assertEqual((await self.db.serverless_tasks.find_one({'_id': task}))['attempts'], 2)

    async def test_task_registry_resolves_and_rejects_arbitrary_functions(self):
        for name in TASKS:
            module, function = name.split(':')
            self.assertTrue(asyncio.iscoroutinefunction(getattr(importlib.import_module(module), function)), name)
        with self.assertRaises(ValueError): await runtime.run_background(asyncio.sleep, 0)
        self.send.assert_not_awaited()

    async def test_schedule_never_seeds_preview_or_obsolete_deployment(self):
        import serverless_schedule as schedule
        with patch.dict(os.environ, {'VERCEL_ENV': 'preview', 'VERCEL_DEPLOYMENT_ID': 'preview'}), patch.object(schedule, 'send', new_callable=AsyncMock) as send:
            await schedule.seed_schedule('www.rilismusik.com'); send.assert_not_awaited()
        await self.db.serverless_schedule.insert_one({'_id': 'active', 'deployment': 'new'})
        with patch.dict(os.environ, {'VERCEL_DEPLOYMENT_ID': 'old'}), patch.object(schedule, 'send', new_callable=AsyncMock) as send:
            await schedule.process_tick({'deployment':'old'}); send.assert_not_awaited()

    async def test_analytics_only_one_instance_can_schedule_and_old_checkpoint_is_cleared(self):
        await self.db.rollup_health.insert_one({'id': 'monthly_analytics', 'running': False,
            'serverless_checkpoint': {'per_dim_counts': {'total': 5}}})
        with patch.object(admin_analytics, 'db_bg', self.db), patch.object(admin_analytics, 'run_background', new_callable=AsyncMock) as dispatch:
            results = await asyncio.gather(*(admin_analytics.schedule_monthly_analytics_recompute() for _ in range(3)))
        self.assertEqual(dispatch.await_count, 1)
        self.assertEqual(len({r['job_id'] for r in results}), 1)
        self.assertNotIn('serverless_checkpoint', await self.db.rollup_health.find_one({}))


class CsvContinuationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = AsyncMongoMockClient().test
        await self.db.labels.insert_one({'id':'label', 'label_name':'Test', 'royalty_percentage_default':60})
        await self.db.tracks.insert_one({'id':'track', 'isrc':'TEST00000001', 'label_id':'label', 'release_id':'release'})
        await self.db.royalty_imports.insert_one({'id':'import', 'status':'processing'})
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name)/'input.csv'
    async def asyncTearDown(self): self.directory.cleanup()
    def write_rows(self, count):
        self.path.write_text('Bulan laporan;ISRC;Pendapatan Bersih\n'+ '2026-09;TEST00000001;1\n'*count)
    async def run_csv(self):
        return await royalty._process_csv_import_inline(import_id='import', file_path=str(self.path), period=None, rate_eur_idr=20000, fee_percent=0)
    async def test_continuation_preserves_exact_rows_and_money(self):
        self.write_rows(5001)
        with patch.object(royalty, 'db_bg', self.db), patch.object(royalty, '_trigger_dashboard_recompute', new_callable=AsyncMock):
            with patch.object(royalty.time, 'monotonic', side_effect=[0, 1000]):
                with self.assertRaises(runtime.JobContinuation): await self.run_csv()
            self.assertEqual(await self.db.royalty_lines.count_documents({}), 4999)
            result = await self.run_csv()
        self.assertEqual(await self.db.royalty_lines.count_documents({}), 5001)
        self.assertEqual(result['total_lines'], 5001)
        self.assertEqual(result['total_label_idr'], 5001*12000)
        self.assertEqual(result['status'], 'pending_review')
        self.assertEqual(result['serverless_checkpoint']['source_row'], 5001)
    async def test_replay_after_uncheckpointed_flush_does_not_duplicate_revenue(self):
        self.write_rows(2)
        with patch.object(royalty, 'db_bg', self.db), patch.object(royalty, '_trigger_dashboard_recompute', new_callable=AsyncMock):
            await self.run_csv()
            await self.db.royalty_imports.update_one({'id':'import'}, {'$unset':{'serverless_checkpoint':''}})
            result = await self.run_csv()
        self.assertEqual(await self.db.royalty_lines.count_documents({}), 2)
        self.assertEqual(result['total_label_idr'], 24000)
    async def test_publish_interruption_between_balance_and_ledger_does_not_double_credit(self):
        await self.db.royalty_lines.insert_one({'id':'line', 'import_id':'import', 'label_id':'label', 'status':'draft', 'match_status':'matched', 'label_idr':12000})
        original = self.db.balance_transactions.update_one
        failed = False
        async def fail_once(*args, **kwargs):
            nonlocal failed
            if not failed:
                failed=True
                raise RuntimeError('interrupted after balance')
            return await original(*args, **kwargs)
        with patch.object(royalty, 'db_bg', self.db), patch.object(royalty, 'db', self.db), patch.object(royalty, 'log_activity', new_callable=AsyncMock), patch.object(royalty, 'notify_many', new_callable=AsyncMock), patch.object(royalty, 'label_user_ids', new_callable=AsyncMock, return_value=[]), patch.object(royalty, 'schedule_dashboard_recompute', new_callable=AsyncMock), patch.object(royalty, 'run_background', new_callable=AsyncMock), patch.object(royalty, '_trigger_dashboard_recompute', new_callable=AsyncMock):
            with patch.object(self.db.balance_transactions, 'update_one', side_effect=fail_once):
                await royalty._publish_bg(import_id='import', user_id='admin')
            await royalty._publish_bg(import_id='import', user_id='admin')
        self.assertEqual((await self.db.labels.find_one({'id':'label'}))['balance_pending_idr'], 12000)
        self.assertEqual(await self.db.balance_transactions.count_documents({'type':'royalty_pending'}), 1)


class UploadTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = AsyncMongoMockClient().test
        self.directory = tempfile.TemporaryDirectory()
        self.app = FastAPI()
        self.app.include_router(uploads.direct_upload_r, prefix='/api')
        self.user = {'id':'actor', 'role':'label'}
        self.app.dependency_overrides[deps.get_current_user] = lambda: self.user
        @self.app.post('/api/existing-upload')
        async def existing_upload(file: UploadFile = File(...), user=Depends(deps.get_current_user)):
            if user['role'] != 'label': raise HTTPException(403, 'label only')
            content = await file.read()
            if content != b'valid': raise HTTPException(400, 'invalid file content')
            return {'saved':len(content)}
        async def download(*, local_path, **kwargs): Path(local_path).write_bytes(b'valid')
        self.patches=[patch.object(uploads,'db',self.db),patch.object(uploads,'UPLOAD_DIR',Path(self.directory.name)),
            patch.object(storage_service,'head_object',new_callable=AsyncMock,return_value={'ContentLength':5}),
            patch.object(storage_service,'download_to_file',side_effect=download),patch.object(storage_service,'delete_object',new_callable=AsyncMock)]
        for p in self.patches:p.start()
        await self.db.direct_upload_sessions.insert_one({'_id':'a'*32,'actor_id':'actor','key':'direct-uploads/'+'a'*32+'/source',
            'target':'/existing-upload','size':5,'filename':'x','content_type':'application/octet-stream','fields':{},'query':{},'status':'uploading','expires_epoch':time.time()+600})
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),base_url='https://preview.example.invalid')
    async def asyncTearDown(self):
        await self.client.aclose()
        for p in reversed(self.patches):p.stop()
        self.directory.cleanup()
    async def test_finalization_uses_existing_validation_and_replay_is_safe(self):
        for _ in range(2):
            r=await self.client.post('/api/uploads/finalize',json={'upload_id':'a'*32})
            self.assertEqual(r.status_code,200);self.assertEqual(r.json(),{'saved':5})
    async def test_other_actor_cannot_finalize_or_read_upload_result(self):
        self.user['id']='other'
        r=await self.client.post('/api/uploads/finalize',json={'upload_id':'a'*32})
        self.assertEqual(r.status_code,404)
    async def test_existing_role_guard_is_preserved(self):
        self.user['role']='artist'
        r=await self.client.post('/api/uploads/finalize',json={'upload_id':'a'*32})
        self.assertEqual(r.status_code,403)
    async def test_existing_file_content_validation_is_preserved(self):
        async def bad(*,local_path,**kwargs):Path(local_path).write_bytes(b'bad!!')
        with patch.object(storage_service,'download_to_file',side_effect=bad):
            r=await self.client.post('/api/uploads/finalize',json={'upload_id':'a'*32})
        self.assertEqual(r.status_code,400)
    async def test_destination_cannot_be_an_external_service_or_nonupload_route(self):
        for target in ('https://evil.invalid','//evil.invalid','/auth/login','/../auth/login'):
            r=await self.client.post('/api/uploads/initiate',json={'target':target,'filename':'x','size':5})
            self.assertEqual(r.status_code,400)


class R2StreamingTests(unittest.TestCase):
    def test_plain_and_compressed_sources_stream_and_close(self):
        from botocore.response import StreamingBody
        from royalty_utils import iter_csv_file
        from unittest.mock import MagicMock
        content = 'Bulan laporan;Nama Label;Pendapatan Bersih\n2026-09;Musik é;1\n'.encode()
        for suffix, data in (('.csv', content), ('.csv.gz', gzip.compress(content))):
            raw = io.BytesIO(data)
            body = StreamingBody(raw, len(data))
            client = MagicMock(); client.get_object.return_value = {'Body':body}
            with patch.object(storage_service, '_client', return_value=client):
                rows=list(iter_csv_file('r2://source'+suffix))
            self.assertEqual(rows[1][1]['nama label'], 'Musik é')
            self.assertTrue(raw.closed)


class QueueServiceTests(unittest.TestCase):
    def test_provider_group_with_encoded_underscores_matches_real_sdk(self):
        import queue_app
        from vercel.queue._internal.push import parse_push_delivery_metadata
        from vercel.queue._internal.subscribers import infer_subscriber_transport
        group = 'queue-jobs_Sfastapi'
        queue_app.register_delivery_group('rilismusik-jobs', group)
        metadata = parse_push_delivery_metadata({'ce-type':'com.vercel.queue.v2beta',
            'ce-vqsqueuename':'rilismusik-jobs', 'ce-vqsconsumergroup':group,
            'ce-vqsmessageid':'offline-test', 'ce-vqsregion':'iad1'})
        self.assertIsNotNone(infer_subscriber_transport(metadata))

    def test_private_callback_passes_receipt_to_sdk(self):
        import queue_app
        with patch.object(queue_app, 'accept_and_handle', new_callable=AsyncMock) as handle, TestClient(queue_app.app) as client:
            result = client.post('/callback', content=b'{"opaque":"callback"}', headers={'ce-vqsreceipthandle':'test-receipt', 'ce-vqsqueuename':'rilismusik-jobs', 'ce-vqsconsumergroup':'test-group'})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(handle.call_args.args[0], b'{"opaque":"callback"}')
        self.assertEqual(handle.call_args.args[1]['ce-vqsreceipthandle'], 'test-receipt')
        self.assertEqual(handle.call_args.kwargs['lease_duration'], 900)
    def test_queue_configuration_is_separate_from_public_api(self):
        import json
        configuration = json.loads((Path(__file__).resolve().parents[2]/'vercel.json').read_text())
        names = {'queue-jobs','queue-emails','queue-schedule'}
        if not names <= set(configuration.get('services', {})):
            self.skipTest('branch ini memakai layout deploy non-produksi (prototype preview)')
        triggers=[]
        for name in names:
            service=configuration['services'][name]
            self.assertEqual(service['entrypoint'], 'queue_app:app')
            configured=service['functions']['queue_app.py']['experimentalTriggers']
            self.assertEqual(len(configured), 1)
            triggers.extend(configured)
        self.assertEqual({t['topic'] for t in triggers}, {'rilismusik-jobs','rilismusik-emails','rilismusik-schedule'})
        self.assertTrue(all(t['type']=='queue/v2beta' for t in triggers))
        self.assertFalse(any(r['destination'].get('service') in names for r in configuration['rewrites']))


class ProductionRouteTests(unittest.TestCase):
    def test_writes_reach_existing_authentication_without_preview_503(self):
        with patch('serverless_schedule.seed_schedule',new_callable=AsyncMock), TestClient(app) as client:
            for path in ('/api/payments/subscription','/api/royalty/admin/imports/initiate','/api/uploads/initiate'):
                response=client.post(path,json={})
                self.assertEqual(response.status_code,401,path)
            self.assertEqual(client.post('/api/auth/register',json={}).status_code,422)
