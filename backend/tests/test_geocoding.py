import support
import asyncio
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.services.geocoding import fetch_locations
from app.main import app
from app.core.request_limits import RequestRateLimiter
from app.core.usage import UsageLimitError


class GeocodingTests(unittest.IsolatedAsyncioTestCase):
    async def test_api_validation_shared_client_and_budget(self):
        calls = []

        def provider(request):
            calls.append(request)
            return httpx.Response(200, json={"results": [{
                "id": 1273294, "name": "Delhi", "latitude": 28.65,
                "longitude": 77.23, "timezone": "Asia/Kolkata", "country": "India",
                "unneeded_metadata": "discarded",
            }]})

        app.state.location_limiter = RequestRateLimiter(30, 60)
        app.state.location_slots = asyncio.Semaphore(2)
        async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as shared:
            app.state.http_client = shared
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as api:
                with patch("app.services.geocoding.wait_for_usage", new_callable=AsyncMock) as budget:
                    response = await api.get("/api/locations", params={"query": " Delhi "})
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()[0]["country"], "India")
                    self.assertEqual(calls[0].url.params["name"], "Delhi")
                    budget.assert_awaited_once_with(1, max_wait=1.0)
                    for query in ("d", "  "):
                        self.assertEqual((await api.get("/api/locations", params={"query": query})).status_code, 422)
                    self.assertEqual(len(calls), 1)
                    budget.side_effect = UsageLimitError(12.2)
                    response = await api.get("/api/locations", params={"query": "Delhi"})
                    self.assertEqual(response.status_code, 503)
                    self.assertEqual(response.headers["Retry-After"], "13")
                    self.assertEqual(len(calls), 1)

    async def test_retries_charge_every_attempt_and_respect_server_delay(self):
        for statuses, retry_after, attempts in (([429, 200], "0", 2), ([503]*3, "0", 3), ([429], "30", 1), ([400], None, 1)):
            calls = []

            def provider(request):
                calls.append(request)
                return httpx.Response(statuses[min(len(calls)-1, len(statuses)-1)],
                                      headers={"Retry-After": retry_after} if retry_after else {}, json={})

            async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as client:
                with patch("app.services.geocoding.wait_for_usage", new_callable=AsyncMock) as budget, patch("app.services.geocoding.asyncio.sleep", new_callable=AsyncMock):
                    if statuses[-1] == 200:
                        self.assertEqual((await fetch_locations(client, asyncio.Semaphore(2), "Delhi")).status_code, 200)
                    else:
                        with self.assertRaises(httpx.HTTPStatusError):
                            await fetch_locations(client, asyncio.Semaphore(2), "Delhi")
                    self.assertEqual(len(calls), attempts)
                    self.assertEqual(budget.await_count, attempts)

    async def test_provider_concurrency_is_bounded(self):
        active = peak = 0

        async def provider(request):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1
            return httpx.Response(200, json={})

        async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as client:
            with patch("app.services.geocoding.wait_for_usage", new_callable=AsyncMock):
                slots = asyncio.Semaphore(2)
                await asyncio.gather(*(fetch_locations(client, slots, "Delhi") for _ in range(5)))
        self.assertEqual(peak, 2)
