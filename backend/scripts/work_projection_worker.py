"""Managed worker for the durable MongoDB work projection (no HTTP/background tasks).

Run under a process supervisor/container with restart enabled. Only MONGO_URL
and DB_NAME are required. A crashed process leaves a recoverable expiring lease;
the next process rediscovering source state resumes idempotently.
"""
import argparse
import asyncio
import logging
import os
from pathlib import Path
import signal
import sys
from tempfile import gettempdir


async def run(interval, stop):
    from routes.work_service import reconcile_work
    logger = logging.getLogger("work-worker")
    while not stop.is_set():
        try:
            result = await reconcile_work()
            logger.info("projection checked synchronizing=%s", result["synchronizing"])
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            # Do not print exception text: driver errors may contain connection info.
            logger.error("projection failed error_type=%s; retry scheduled", type(exc).__name__)
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except TimeoutError:
            pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, choices=range(8, 301), metavar="8..300", default=15)
    args = parser.parse_args()
    if not os.environ.get("MONGO_URL") or not os.environ.get("DB_NAME"):
        parser.error("Isi MONGO_URL dan DB_NAME pada environment worker.")
    os.environ.setdefault("UPLOAD_DIR", str(Path(gettempdir()) / "rilismusik-worker"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    async def managed():
        from routes.deps import client, client_bg
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)
        try:
            await run(args.interval, stop)
        finally:
            client.close()
            client_bg.close()
    asyncio.run(managed())


if __name__ == "__main__":
    main()
