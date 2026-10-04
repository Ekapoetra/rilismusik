"""Private Vercel Queues subscribers, automatically discovered at build time."""
import os
from pathlib import Path
from tempfile import gettempdir

os.environ["RILISMUSIK_SERVERLESS_RUNTIME"] = "1"
os.environ["UPLOAD_DIR"] = str(Path(gettempdir()) / "rilismusik" / "uploads")

from vercel.queue import subscribe
from background_runtime import consume_task


@subscribe(topic="rilismusik-jobs", consumer_group="rilismusik-jobs", max_concurrency=1, retry_after=60)
async def process_job(payload: dict[str, str]) -> None:
    await consume_task(payload["task_id"])


@subscribe(topic="rilismusik-emails", consumer_group="rilismusik-emails", max_concurrency=4, retry_after=60)
async def process_email(payload: dict[str, str]) -> None:
    await consume_task(payload["task_id"])


@subscribe(topic="rilismusik-schedule", consumer_group="rilismusik-schedule", max_concurrency=1, retry_after=60)
async def process_schedule(payload: dict[str, str]) -> None:
    from serverless_schedule import process_tick
    await process_tick(payload)
