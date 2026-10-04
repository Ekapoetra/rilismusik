"""Private queue callback service. Vercel triggers make this function nonpublic."""
import threading
import logging
import traceback
from fastapi import FastAPI, HTTPException, Request
from vercel.queue import accept_and_handle, subscribe
import queue_worker

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
_handlers = {"rilismusik-jobs": queue_worker.process_job,
             "rilismusik-emails": queue_worker.process_email,
             "rilismusik-schedule": queue_worker.process_schedule}
_consumers = {}
_lock = threading.Lock()


def register_delivery_group(topic: str, group: str):
    # v2 triggers derive their consumer group from the deployed function. Keep
    # that identity intact for SDK acknowledgements and lease renewal.
    if topic not in _handlers or not group or len(group) > 256:
        raise HTTPException(400, "Invalid queue delivery")
    key = (topic, group)
    with _lock:
        if key not in _consumers:
            handler = _handlers[topic]
            async def receive(payload: dict[str, str]):
                await handler(payload)
            _consumers[key] = subscribe(topic=topic, consumer_group=group)(receive)


@app.post('/{path:path}')
async def callback(request: Request, path: str):
    try:
        register_delivery_group(request.headers.get('ce-vqsqueuename', ''),
                                request.headers.get('ce-vqsconsumergroup', ''))
        await accept_and_handle(await request.body(), request.headers, lease_duration=900)
    except Exception as error:
        # Log locations and exception class only: delivery bodies and credentials
        # must never be copied into runtime logs.
        frames = ','.join(f'{frame.name}:{frame.lineno}' for frame in traceback.extract_tb(error.__traceback__))
        logging.getLogger(__name__).error('queue_callback_failed type=%s frames=%s', type(error).__name__, frames)
        raise
    return {'ok': True}
