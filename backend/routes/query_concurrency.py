"""Small, bounded groups of independent reads; no caching of financial results."""
import asyncio


async def bounded_gather(*operations, limit=2):
    gate = asyncio.Semaphore(limit)

    async def run(operation):
        started = False
        try:
            async with gate:
                started = True
                return await operation
        finally:
            if not started and asyncio.iscoroutine(operation):
                operation.close()

    tasks = [asyncio.create_task(run(operation)) for operation in operations]
    try:
        return await asyncio.gather(*tasks)
    except BaseException:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
