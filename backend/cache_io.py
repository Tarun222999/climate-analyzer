"""Keep synchronous MongoDB operations alive until safe client shutdown."""
import asyncio


_operations: set[asyncio.Task] = set()


async def run_cache_operation(function, *args):
    task = asyncio.create_task(asyncio.to_thread(function, *args))
    _operations.add(task)

    def finished(operation):
        _operations.discard(operation)
        if not operation.cancelled():
            operation.exception()

    task.add_done_callback(finished)
    # Cancelling a request cannot stop a running synchronous MongoDB call.
    # Retain it so shutdown can wait before closing its client.
    return await asyncio.shield(task)


async def drain_cache_operations():
    while _operations:
        await asyncio.gather(*tuple(_operations), return_exceptions=True)
