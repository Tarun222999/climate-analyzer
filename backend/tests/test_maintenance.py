import support
import asyncio
import unittest
from unittest.mock import MagicMock

from app.storage.maintenance import invalidation_plan, invalidate_cache, monitor_storage, storage_report
from app.models import Location


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.location = Location(name="Delhi", latitude=28.65, longitude=77.23, timezone="Asia/Kolkata")

    def test_storage_uses_logical_data_plus_indexes_and_warns(self):
        database = MagicMock()
        database.command.return_value = {"dataSize": 75, "indexSize": 10, "storageSize": 20}
        report = storage_report(database, 100)
        self.assertEqual(report["logical_bytes"], 85)
        self.assertTrue(report["warning"])
        self.assertEqual(report["scope"], "configured_database_only")
        database.command.return_value = {}
        with self.assertRaises(ValueError):
            storage_report(database, 100)

    def test_invalidation_cascades_and_preserves_location_scope(self):
        plan = invalidation_plan(self.location, "weather", 2020)
        self.assertEqual([name for name, query in plan], ["analyses", "baseline_thresholds", "weather_years"])
        self.assertEqual(plan[-1][1]["year"], 2020)
        self.assertEqual(plan[0][1]["request.location.latitude"], 28.65)
        self.assertEqual([name for name, _ in invalidation_plan(self.location, "weather", 2021)], ["analyses", "weather_years"])
        self.assertEqual([name for name, _ in invalidation_plan(self.location, "baseline")], ["analyses", "baseline_thresholds"])
        with self.assertRaises(ValueError):
            invalidation_plan(self.location, "weather")

    def test_preview_does_not_delete_and_apply_uses_same_plan(self):
        database = MagicMock()
        database.__getitem__.return_value.count_documents.return_value = 3
        database.__getitem__.return_value.delete_many.return_value.deleted_count = 3
        preview = invalidate_cache(database, self.location, "weather", 2020)
        self.assertFalse(preview["applied"])
        database.__getitem__.return_value.delete_many.assert_not_called()
        applied = invalidate_cache(database, self.location, "weather", 2020, apply=True)
        self.assertTrue(applied["applied"])
        self.assertEqual(preview["documents"], applied["documents"])
        self.assertEqual(database.__getitem__.return_value.delete_many.call_count, 3)


class MonitorTests(unittest.IsolatedAsyncioTestCase):
    async def test_monitor_samples_then_stops_without_waiting_for_interval(self):
        database = MagicMock()
        database.command.return_value = {"dataSize": 1, "indexSize": 1}
        stop = asyncio.Event()
        task = asyncio.create_task(monitor_storage(database, 100, stop, interval_seconds=300))
        for _ in range(100):
            if database.command.called:
                break
            await asyncio.sleep(0.01)
        stop.set()
        await asyncio.wait_for(task, 2)
        database.command.assert_called_once_with("dbStats", scale=1)
