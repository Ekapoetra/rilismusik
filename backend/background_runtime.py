"""Dispatch durable work on Vercel; retain ordinary asyncio tasks elsewhere.

Only task IDs enter the queue. Arguments stay in the application's private R2
bucket, and MongoDB records dispatch, ownership and completion across retries.
"""
import asyncio
import gzip
import importlib
import os
import time
import uuid
from pathlib import Path

from bson import json_util
from pydantic import BaseModel
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from background_task_registry import TASKS


class JobContinuation(Exception):
    """A checkpoint was persisted; a fresh invocation should continue the job."""


def serverless_runtime() -> bool:
    return os.environ.get("RILISMUSIK_SERVERLESS_RUNTIME") == "1"


def _pack(value):
    if isinstance(value, BaseModel):
        if value.__class__.__module__ != "models" or value.__class__.__name__ != "ManualLegacyWithdrawIn":
            raise TypeError("Unsupported background argument model")
        return {"__rilismusik_model__": value.__class__.__name__, "value": value.model_dump(mode="json")}
    if isinstance(value, dict):
        return {key: _pack(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_pack(item) for item in value]
    return value


def _unpack(value):
    if isinstance(value, dict):
        if "__rilismusik_model__" in value:
            if value["__rilismusik_model__"] != "ManualLegacyWithdrawIn":
                raise ValueError("Unsupported background argument model")
            from models import ManualLegacyWithdrawIn
            return ManualLegacyWithdrawIn.model_validate(value["value"])
        return {key: _unpack(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_unpack(item) for item in value]
    return value


async def run_background(function, *args, **kwargs):
    if not serverless_runtime():
        return asyncio.create_task(function(*args, **kwargs))
    name = f"{function.__module__}:{function.__name__}"
    if name not in TASKS:
        raise ValueError("Unregistered background task")
    from routes.deps import db_bg, UPLOAD_DIR
    import storage_service
    from vercel.queue import send

    kwargs = dict(kwargs)
    task_id = kwargs.pop("_dispatch_id", None) or uuid.uuid4().hex
    existing = await db_bg.serverless_tasks.find_one({"_id": task_id})
    if existing:
        return task_id
    # CSV inputs already in R2 can be streamed by a different function instance.
    path = kwargs.get("file_path")
    if path and not str(path).startswith("r2://"):
        source = await db_bg.royalty_imports.find_one({"id": kwargs.get("import_id")}, {"r2_key": 1}) if kwargs.get("import_id") else None
        key = (source or {}).get("r2_key")
        if not key:
            local = Path(path).resolve()
            if not local.is_relative_to(UPLOAD_DIR.resolve()):
                raise ValueError("Background source is outside upload directory")
            key = f"background-inputs/{task_id}/{local.name}"
            with local.open("rb") as stream:
                await storage_service.upload_fileobj(key=key, fileobj=stream, content_type="application/octet-stream")
        kwargs["file_path"] = "r2://" + key
    payload_key = f"background-inputs/{task_id}/arguments.json.gz"
    payload = gzip.compress(json_util.dumps(_pack({"args": args, "kwargs": kwargs})).encode())
    await storage_service.upload_bytes(key=payload_key, data=payload, content_type="application/gzip")
    now = time.time()
    try:
        await db_bg.serverless_tasks.insert_one({
        "_id": task_id, "task": name, "payload_key": payload_key,
        "status": "pending_dispatch", "created_epoch": now, "updated_epoch": now,
        })
    except DuplicateKeyError:
        return task_id
    if name == "routes.royalty:_process_csv_import_bg" and kwargs.get("import_id"):
        await db_bg.royalty_imports.update_one({"id": kwargs["import_id"]}, {"$set": {"serverless_task_id": task_id}})
    topic = "rilismusik-emails" if function.__module__ == "email_service" else "rilismusik-jobs"
    try:
        message_id = await send(topic, {"task_id": task_id}, idempotency_key=task_id)
    except Exception:
        # Leave the outbox record recoverable; never report lost work as queued.
        await db_bg.serverless_tasks.update_one({"_id": task_id}, {"$set": {"dispatch_failed": True}})
        raise
    await db_bg.serverless_tasks.update_one({"_id": task_id, "status": "pending_dispatch"}, {"$set": {
        "status": "queued", "message_id": str(message_id) if message_id else None,
        "updated_epoch": time.time(),
    }})
    return task_id


async def recover_pending_dispatches():
    from routes.deps import db_bg
    from vercel.queue import send
    pending = await db_bg.serverless_tasks.find({"status": "pending_dispatch"}).limit(20).to_list(20)
    for document in pending:
        topic = "rilismusik-emails" if document["task"].startswith("email_service:") else "rilismusik-jobs"
        message_id = await send(topic, {"task_id": document["_id"]}, idempotency_key=document["_id"])
        await db_bg.serverless_tasks.update_one({"_id": document["_id"], "status": "pending_dispatch"}, {"$set": {
            "status": "queued", "message_id": str(message_id) if message_id else None,
            "updated_epoch": time.time(),
        }})
    return len(pending)


async def consume_task(task_id: str):
    from routes.deps import db_bg, logger
    import storage_service
    if not isinstance(task_id, str) or len(task_id) != 32 or any(c not in "0123456789abcdef" for c in task_id):
        raise ValueError("Invalid background task ID")
    document = await db_bg.serverless_tasks.find_one({"_id": task_id})
    if not document:
        raise ValueError("Background task is missing")
    if document.get("status") == "done":
        return
    owner = uuid.uuid4().hex
    now = time.time()
    claimed = await db_bg.serverless_tasks.find_one_and_update({
        "_id": task_id, "status": {"$ne": "done"},
        "$or": [{"lease_until": {"$lt": now}}, {"lease_until": {"$exists": False}}],
    }, {"$set": {"status": "running", "owner": owner, "lease_until": now + 900,
                  "updated_epoch": now}, "$inc": {"attempts": 1}}, return_document=ReturnDocument.AFTER)
    if not claimed:
        # An overlapping delivery must retry, rather than acknowledge unfinished work.
        raise RuntimeError("Background task is already leased")
    name = claimed["task"]
    if name not in TASKS:
        raise ValueError("Unregistered background task")
    started = time.perf_counter()
    try:
        payload = _unpack(json_util.loads(gzip.decompress(await storage_service.download_bytes(key=claimed["payload_key"]))))
        module, attribute = name.split(":", 1)
        function = getattr(importlib.import_module(module), attribute)
        async with asyncio.timeout(750):
            await function(*payload["args"], **payload["kwargs"])
        await db_bg.serverless_tasks.update_one({"_id": task_id, "owner": owner}, {"$set": {
            "status": "done", "updated_epoch": time.time(), "finished_epoch": time.time(),
        }, "$unset": {"lease_until": "", "owner": ""}})
        logger.info("serverless_task completed task=%s duration_s=%.3f", name, time.perf_counter() - started)
    except BaseException as error:
        # Errors are redelivered by Queues; keep only the error class, never arguments.
        await db_bg.serverless_tasks.update_one({"_id": task_id, "owner": owner}, {"$set": {
            "status": "retry", "error_type": type(error).__name__, "updated_epoch": time.time(),
        }, "$unset": {"lease_until": "", "owner": ""}})
        raise


async def record_runtime_probe(*, deployment: str):
    """Harmless deployment check: confirms a private queue consumer ran."""
    from routes.deps import db_bg
    await db_bg.serverless_probes.update_one({"_id": deployment},
        {"$set": {"status": "done", "completed_epoch": time.time()}}, upsert=True)
