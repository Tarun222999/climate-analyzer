"""Bounded geocoding requests using the app's shared client and usage budget."""

import asyncio
from datetime import datetime, timezone

import httpx

from usage import wait_for_usage
from weather import retry_after_seconds


async def fetch_locations(
    client: httpx.AsyncClient,
    slots: asyncio.Semaphore,
    query: str,
) -> httpx.Response:
    for attempt in range(3):
        try:
            async with slots:
                await wait_for_usage(1, max_wait=1.0)
                response = await client.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": query, "count": 10, "language": "en"},
                    timeout=10.0,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise
            delay = retry_after_seconds(
                exc.response.headers.get("Retry-After"), datetime.now(timezone.utc)
            )
            if delay is None:
                delay = float(2 ** attempt)
            # Never retry sooner than requested; let the caller retry later.
            if delay > 2:
                raise
        except httpx.TransportError:
            if attempt == 2:
                raise
            delay = float(2 ** attempt)
        else:
            return response
        await asyncio.sleep(delay)

    raise RuntimeError("Geocoding retry loop ended unexpectedly")
