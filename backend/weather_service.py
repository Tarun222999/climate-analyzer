import asyncio
from datetime import datetime, timezone

import httpx

from cache import load_weather_year, save_weather_year,weather_key
from models import Location, WeatherYear
from weather import fetch_weather_payload, parse_weather_days


async def _load_or_fetch_weather_year(
    collection,
    client:httpx.AsyncClient,
    location:Location,
    year:int
) -> WeatherYear:

    cached = await asyncio.to_thread(
        load_weather_year,collection,location,year
    )

    if cached is not None:
        return cached

    payload = await fetch_weather_payload(client,location,year)
    days, invalid_dates = parse_weather_days(payload,year)

    record = WeatherYear(
        location=location,
        year=year,
        grid_latitude=payload["latitude"],
        grid_longitude=payload["longitude"],
        timezone=payload["timezone"],
        fetched_at=datetime.now(timezone.utc),
        days=days,
        invalid_dates=invalid_dates,
        expected_days=len(days),
        valid_days=sum(
            day.max_temperature_c is not None for day in days
        ),
    )

    await asyncio.to_thread(save_weather_year,collection,record)
    saved = await asyncio.to_thread(
        load_weather_year,collection,location,year
    )

    if saved is None:
        raise RuntimeError("Weather record missing after cache write")

    return saved;



_inflight : dict[tuple,asyncio.Task[WeatherYear]]={}

async def get_weather_year(
    collection,
    client:httpx.AsyncClient,
    location:Location,
    year:int
) -> WeatherYear :

    key = (
        id(collection.database.client),
        collection.full_name,
        tuple(weather_key(location,year).items()),
    )

    task = _inflight.get(key)

    if task is None:
        task = asyncio.create_task(
            _load_or_fetch_weather_year(
                collection,client,location,year
            )
        )
        _inflight[key]=task

        def cleanup(finished):
            if _inflight.get(key) is finished:
                del _inflight[key]

            if not finished.cancelled():
                finished.exception()
            
        task.add_done_callback(cleanup)

    return await asyncio.shield(task)