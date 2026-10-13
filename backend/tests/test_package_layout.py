import support
import unittest
from pathlib import Path

from app.core.config import Settings
from app.main import app
from app import models
from app.services import baseline_service, weather, weather_service
from app.storage.analysis_cache import ANALYSIS_KEY_FIELDS, analysis_key


class PackageLayoutTests(unittest.TestCase):
    def test_env_file_still_resolves_to_backend_root(self):
        backend = Path(__file__).resolve().parents[1]
        self.assertEqual(Settings.model_config["env_file"], backend / ".env")

    def test_services_share_one_model_module(self):
        self.assertIs(baseline_service.Location, models.Location)
        self.assertIs(weather.Location, models.Location)
        self.assertIs(weather.DailyTemperature, models.DailyTemperature)
        self.assertIs(weather_service.WeatherYear, models.WeatherYear)

    def test_persisted_cache_paths_remain_compatible(self):
        request = models.AnalysisRequest(
            location=models.Location(name="Test", latitude=0, longitude=0, timezone="UTC"),
            start_year=2020, end_year=2020,
        )
        key = analysis_key(request)
        self.assertEqual(key["baseline.baseline_start_year"], 1991)
        self.assertEqual(key["baseline.baseline_end_year"], 2020)
        self.assertEqual(key["baseline.source"], "open-meteo")
        self.assertEqual(tuple(key), ANALYSIS_KEY_FIELDS)
        self.assertFalse(any(field.startswith("app.") for field in key))

    def test_router_preserves_api_paths_and_request_contract(self):
        schema = app.openapi()
        self.assertEqual(set(schema["paths"]), {
            "/api/health", "/api/locations", "/api/analysis",
        })
        self.assertEqual(schema["paths"]["/api/analysis"]["post"]["requestBody"]
                         ["content"]["application/json"]["schema"]["$ref"],
                         "#/components/schemas/AnalysisRequest")
        self.assertEqual(set(schema["components"]["schemas"]["AnalysisRequest"]["required"]),
                         {"location", "start_year", "end_year"})
