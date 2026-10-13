import support
import unittest
from unittest.mock import patch

from scripts import manage_cache


class ScriptEntrypointTests(unittest.TestCase):
    def test_invalidation_preview_resolves_package_imports_without_deletion(self):
        argv = ["manage_cache", "invalidate", "--kind", "weather", "--year", "2020",
                "--latitude", "28.65", "--longitude", "77.23", "--timezone", "Asia/Kolkata"]
        with patch("sys.argv", argv), patch("builtins.print"), patch.object(manage_cache, "create_mongo_client") as create:
            database = create.return_value.__enter__.return_value.__getitem__.return_value
            collection = database.__getitem__.return_value
            collection.count_documents.return_value = 1
            self.assertEqual(manage_cache.main(), 0)
            self.assertEqual(collection.count_documents.call_count, 3)
            collection.delete_many.assert_not_called()

    def test_invalid_weather_scope_rejected_before_database_connection(self):
        argv = ["manage_cache", "invalidate", "--kind", "weather",
                "--latitude", "28.65", "--longitude", "77.23", "--timezone", "Asia/Kolkata"]
        with patch("sys.argv", argv), patch("builtins.print"), patch.object(manage_cache, "create_mongo_client") as create:
            self.assertEqual(manage_cache.main(), 1)
            create.assert_not_called()
