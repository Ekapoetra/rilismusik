"""Cross-worker, per-label lease for adjustment/withdrawal mutations."""
import asyncio
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from .deps import db


@asynccontextmanager
async def label_financial_lock(label_id: str):
    owner = str(uuid4())
    now = datetime.now(timezone.utc)
    try:
        lease = await db.financial_operation_locks.find_one_and_update(
            {"_id": label_id, "expires_at": {"$lte": now}},
            {"$set": {"owner": owner, "expires_at": now + timedelta(seconds=120)}},
            upsert=True, return_document=ReturnDocument.AFTER,
        )
    except DuplicateKeyError:
        raise HTTPException(409, "Operasi saldo label sedang berlangsung. Silakan coba lagi.")
    if not lease or lease.get("owner") != owner:
        raise HTTPException(409, "Operasi saldo label sedang berlangsung. Silakan coba lagi.")

    parent = asyncio.current_task()
    lost = False

    async def renew():
        nonlocal lost
        try:
            while True:
                await asyncio.sleep(20)
                result = await db.financial_operation_locks.update_one(
                    {"_id": label_id, "owner": owner},
                    {"$set": {"expires_at": datetime.now(timezone.utc) + timedelta(seconds=120)}},
                )
                if not result.matched_count:
                    raise RuntimeError("Financial lease lost")
        except asyncio.CancelledError:
            raise
        except Exception:
            lost = True
            parent.cancel()

    heartbeat = asyncio.create_task(renew())
    try:
        yield
    except asyncio.CancelledError:
        if lost:
            raise HTTPException(503, "Koneksi pencatatan saldo terputus. Periksa riwayat sebelum mencoba lagi.")
        raise
    finally:
        heartbeat.cancel()
        with suppress(asyncio.CancelledError):
            await heartbeat
        with suppress(Exception):
            await db.financial_operation_locks.delete_one({"_id": label_id, "owner": owner})