import support
import asyncio
import threading
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from cache_io import drain_cache_operations, run_cache_operation
from models import Location
import weather_service as service


class ShutdownTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancelled_caller_does_not_cancel_other_caller_fetch(self):
        mongo = object()
        collection = SimpleNamespace(database=SimpleNamespace(client=mongo), full_name="test.weather")
        location = Location(name="Test", latitude=0, longitude=0, timezone="UTC")
        start = date(2020, 1, 1)
        entered, release = asyncio.Event(), asyncio.Event()
        record = object()

        async def fetch(*args):
            entered.set()
            await release.wait()
            return record

        service.start_weather_fetches(mongo)
        with patch.object(service, "load_weather_year", return_value=None), patch.object(service, "missing_weather_periods", return_value=[]), patch.object(service, "_load_or_fetch_weather_window", side_effect=fetch) as worker:
            first = asyncio.create_task(service.get_weather_window(collection, None, location, start, start))
            await asyncio.wait_for(entered.wait(), 2)
            second = asyncio.create_task(service.get_weather_window(collection, None, location, start, start))
            await asyncio.sleep(0.02)
            first.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await first
            release.set()
            self.assertIs(await second, record)
            self.assertEqual(worker.call_count, 1)
        await service.shutdown_weather_fetches(mongo)
        self.assertFalse(any(key[0] == id(mongo) for key in service._inflight))

    async def test_shutdown_cancels_stalled_fetch_and_blocks_new_work(self):
        mongo = object()
        cancelled = asyncio.Event()

        async def stalled():
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        service.start_weather_fetches(mongo)
        task = asyncio.create_task(stalled())
        service._inflight[(id(mongo), "test", ())] = task
        await asyncio.sleep(0)
        await service.shutdown_weather_fetches(mongo, grace_seconds=0.01)
        self.assertTrue(cancelled.is_set())
        self.assertTrue(task.cancelled())
        service._inflight.pop((id(mongo), "test", ()), None)
        collection = SimpleNamespace(database=SimpleNamespace(client=mongo))
        location = Location(name="Test", latitude=0, longitude=0, timezone="UTC")
        with self.assertRaisesRegex(RuntimeError, "shutting down"):
            await service.get_weather_window(collection, None, location, date(2020, 1, 1), date(2020, 1, 1))

    async def test_cancelled_request_thread_finishes_before_shutdown_returns(self):
        entered, release, finished = threading.Event(), threading.Event(), threading.Event()

        def write():
            entered.set()
            release.wait(timeout=3)
            finished.set()

        caller = asyncio.create_task(run_cache_operation(write))
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait, 2))
            caller.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await caller
            draining = asyncio.create_task(drain_cache_operations())
            await asyncio.sleep(0.02)
            self.assertFalse(draining.done())
        finally:
            release.set()
        await asyncio.wait_for(draining, 2)
        self.assertTrue(finished.is_set())
