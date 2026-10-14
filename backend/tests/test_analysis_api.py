import support
import asyncio
import unittest
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import httpx
from pymongo.errors import PyMongoError

from app.main import app
from app.models import AnalysisResult
from app.core.request_limits import RequestConcurrencyLimiter, RequestRateLimiter
from app.core.usage import UsageLimitError
from app.services.weather_service import shutdown_weather_fetches, start_weather_fetches


PAYLOAD = {
    "location": {"name": "Test", "latitude": 28.65, "longitude": 77.23, "timezone": "Asia/Kolkata"},
    "start_year": 2020, "end_year": 2020,
}


class AnalysisApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = support.MemoryDatabase()
        start_weather_fetches(self.db.client)
        app.state.weather_collection = self.db["weather_years"]
        app.state.baseline_collection = self.db["baseline_thresholds"]
        app.state.analysis_collection = self.db["analyses"]
        app.state.analysis_limiter = RequestRateLimiter(6, 60)
        app.state.location_limiter = RequestRateLimiter(30, 60)
        app.state.analysis_concurrency = RequestConcurrencyLimiter(2)
        self.calls = []
        self.bad_grid_year = None

        async def weather(request):
            self.calls.append(str(request.url))
            await asyncio.sleep(0.001)
            start = date.fromisoformat(request.url.params["start_date"])
            end = date.fromisoformat(request.url.params["end_date"])
            dates = [start + timedelta(days=i) for i in range((end-start).days+1)]
            return httpx.Response(200, json={
                "latitude": 28.7, "longitude": 78.0 if start.year == self.bad_grid_year else 77.2, "timezone": "Asia/Kolkata",
                "daily_units": {"temperature_2m_max": "\u00b0C"},
                "daily": {"time": [day.isoformat() for day in dates],
                          "temperature_2m_max": [43.0 if date(2020, 7, 1) <= day <= date(2020, 7, 3) else 40.0 for day in dates]},
            })

        self.provider = httpx.AsyncClient(transport=httpx.MockTransport(weather))
        app.state.http_client = self.provider
        self.api = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
        self.budget_patch = patch("app.services.weather.wait_for_usage", new_callable=AsyncMock)
        self.budget_patch.start()

    async def asyncTearDown(self):
        await shutdown_weather_fetches(self.db.client)
        await self.api.aclose()
        await self.provider.aclose()
        self.budget_patch.stop()

    async def test_cold_analysis_fetches_baseline_then_warm_hit_skips_all_work(self):
        response = await self.api.post("/api/analysis", json=PAYLOAD)
        self.assertEqual(response.status_code, 200, response.text)
        result = AnalysisResult.model_validate(response.json())
        self.assertEqual(result.baseline.threshold_c, 40.0)
        self.assertEqual(result.summary.events_starting_in_selection, 1)
        self.assertEqual(result.summary.heatwave_days, 3)
        self.assertEqual(result.summary.peak_temperature_c, 43.0)
        self.assertEqual(result.summary.valid_days, 366)
        self.assertEqual(len(self.calls), 31)  # 30 baseline years plus Jan 2021 context
        self.assertEqual(self.db["analyses"].count_documents({}), 1)
        with patch("app.services.analysis_service.build_analysis", new_callable=AsyncMock) as build:
            renamed = {**PAYLOAD, "location": {**PAYLOAD["location"], "name": "Renamed"}}
            warm = await self.api.post("/api/analysis", json=renamed)
            self.assertEqual(warm.status_code, 200)
            self.assertEqual(warm.json()["request"]["location"]["name"], "Renamed")
            self.assertEqual(warm.json()["calculated_at"], response.json()["calculated_at"])
            build.assert_not_awaited()
        self.assertEqual(len(self.calls), 31)

    async def test_concurrent_cold_analyses_share_missing_weather(self):
        first, second = await asyncio.gather(*(self.api.post("/api/analysis", json=PAYLOAD) for _ in range(2)))
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(len(self.calls), 31)
        self.assertEqual(len(set(self.calls)), 31)
        self.assertEqual(self.db["analyses"].count_documents({}), 1)
        self.assertEqual(app.state.analysis_concurrency.active, 0)

    async def test_changed_grid_cannot_be_mixed_with_baseline(self):
        self.bad_grid_year = 2021
        response = await self.api.post("/api/analysis", json=PAYLOAD)
        self.assertEqual(response.status_code, 502)
        self.assertEqual(self.db["analyses"].count_documents({}), 0)

    async def test_failures_validation_and_cors(self):
        for error, status in ((TimeoutError(), 504), (UsageLimitError(12.2), 503),
                              (PyMongoError("test"), 503), (ValueError("test"), 502)):
            with patch("app.api.routes.get_analysis", new_callable=AsyncMock, side_effect=error):
                response = await self.api.post("/api/analysis", json=PAYLOAD)
            self.assertEqual(response.status_code, status)
            self.assertEqual(app.state.analysis_concurrency.active, 0)
            if isinstance(error, UsageLimitError):
                self.assertEqual(response.headers["Retry-After"], "13")
        invalid = {**PAYLOAD, "end_year": 2019}
        with patch("app.api.routes.get_analysis", new_callable=AsyncMock) as build:
            self.assertEqual((await self.api.post("/api/analysis", json=invalid)).status_code, 422)
            build.assert_not_awaited()
        for origin, status in (("http://localhost:5173", 200), ("https://unlisted.example", 400)):
            response = await self.api.options("/api/analysis", headers={"Origin": origin, "Access-Control-Request-Method": "POST"})
            self.assertEqual(response.status_code, status)

    async def test_simultaneous_limit_and_failure_cleanup(self):
        entered, release = asyncio.Event(), asyncio.Event()
        active = 0

        async def stalled(*args):
            nonlocal active
            active += 1
            if active == 2:
                entered.set()
            await release.wait()
            raise TimeoutError()

        with patch("app.api.routes.get_analysis", side_effect=stalled):
            tasks = [asyncio.create_task(self.api.post("/api/analysis", json=PAYLOAD)) for _ in range(2)]
            try:
                await asyncio.wait_for(entered.wait(), 2)
                rejected = await self.api.post("/api/analysis", json=PAYLOAD)
                self.assertEqual(rejected.status_code, 503)
                self.assertEqual(rejected.headers["Retry-After"], "1")
            finally:
                release.set()
                results = await asyncio.gather(*tasks)
            self.assertTrue(all(result.status_code == 504 for result in results))
            self.assertEqual(app.state.analysis_concurrency.active, 0)

    async def test_incoming_rate_limit_blocks_before_analysis_work(self):
        with patch("app.api.routes.get_analysis", new_callable=AsyncMock, side_effect=TimeoutError()) as build:
            for _ in range(6):
                self.assertEqual((await self.api.post("/api/analysis", json=PAYLOAD)).status_code, 504)
            response = await self.api.post("/api/analysis", json=PAYLOAD)
            self.assertEqual(response.status_code, 429)
            self.assertEqual(build.await_count, 6)
            self.assertGreaterEqual(int(response.headers["Retry-After"]), 1)

    async def test_ten_year_response_contains_regression(self):
        payload = {**PAYLOAD, "start_year": 2011, "end_year": 2020}
        response = await self.api.post("/api/analysis", json=payload)
        self.assertEqual(response.status_code, 200, response.text)

        result = AnalysisResult.model_validate(response.json())
        trend = result.regression

        self.assertEqual(result.analysis_version, "analysis-v2")
        self.assertEqual(trend.status, "available")
        self.assertIsNone(trend.reason)
        self.assertEqual(trend.years_used, list(range(2011, 2021)))
        self.assertEqual(
            [point.year for point in trend.fitted_values], trend.years_used
        )

        # This fixture has zero starts until one event in 2020.
        self.assertEqual(
            [point.observed_event_starts for point in trend.fitted_values],
            [0] * 9 + [1],
        )
        self.assertAlmostEqual(trend.slope_events_per_year, 4.5 / 82.5)
        self.assertAlmostEqual(
            trend.change_per_decade, trend.slope_events_per_year * 10
        )
        self.assertEqual(len(self.calls), 31)

    async def test_old_analysis_cache_rebuilt_without_weather_fetches(self):
        initial = await self.api.post("/api/analysis", json=PAYLOAD)
        self.assertEqual(initial.status_code, 200, initial.text)
        calls_before = len(self.calls)
        baseline_before = self.db["baseline_thresholds"].find_one({})

        # Simulate an old stored response in this test's memory database.
        legacy = initial.json()
        legacy["analysis_version"] = "analysis-v1"
        legacy.pop("regression")

        analyses = self.db["analyses"]
        with analyses.lock:
            analyses.documents = [legacy]

        rebuilt = await self.api.post("/api/analysis", json=PAYLOAD)
        self.assertEqual(rebuilt.status_code, 200, rebuilt.text)
        result = rebuilt.json()

        self.assertEqual(result["analysis_version"], "analysis-v2")
        self.assertEqual(result["regression"]["status"], "unavailable")
        self.assertEqual(
            result["regression"]["reason"], "insufficient_complete_years"
        )
        self.assertIsNone(result["regression"]["slope_events_per_year"])
        self.assertEqual(result["regression"]["fitted_values"], [])
        self.assertEqual(len(self.calls), calls_before)
        self.assertEqual(
            self.db["baseline_thresholds"].find_one({}), baseline_before
        )
        self.assertEqual(
            analyses.count_documents({"analysis_version": "analysis-v1"}), 1
        )
        self.assertEqual(
            analyses.count_documents({"analysis_version": "analysis-v2"}), 1
        )

        with patch(
            "app.services.analysis_service.build_analysis", new_callable=AsyncMock
        ) as build:
            warm = await self.api.post("/api/analysis", json=PAYLOAD)
            self.assertEqual(warm.status_code, 200)
            self.assertEqual(warm.json(), result)
            build.assert_not_awaited()
