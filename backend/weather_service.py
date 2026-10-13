import asyncio
from datetime import date, datetime, timedelta, timezone
from operator import le
from cache_io import run_cache_operation

import httpx

from cache import load_weather_year, save_weather_year,weather_key
from models import DailyTemperature, Location, WeatherYear
from weather import fetch_weather_payload, parse_weather_days,parse_weather_window,fetch_weather_window_payload


async def _load_or_fetch_weather_year(
    collection,
    client:httpx.AsyncClient,
    location:Location,
    year:int
) -> WeatherYear:

    cached = await run_cache_operation(
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

    await run_cache_operation(save_weather_year,collection,record)
    saved = await run_cache_operation(
        load_weather_year,collection,location,year
    )

    if saved is None:
        raise RuntimeError("Weather record missing after cache write")

    return saved;



_inflight : dict[tuple,asyncio.Task[WeatherYear]]={}
_closing_clients: set[int] = set()


def start_weather_fetches(mongo_client):
    _closing_clients.discard(id(mongo_client))


async def shutdown_weather_fetches(mongo_client, grace_seconds=10.0):
    """Drain this client's shared fetches, then cancel remaining HTTP work."""
    client_id = id(mongo_client)
    _closing_clients.add(client_id)
    tasks = [task for key, task in tuple(_inflight.items()) if key[0] == client_id]
    if not tasks:
        return
    _, pending = await asyncio.wait(tasks, timeout=grace_seconds)
    for task in pending:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


async def get_weather_window(
    collection,
    client: httpx.AsyncClient,
    location: Location,
    start_date: date,
    end_date: date,
) -> WeatherYear:
    if end_date < start_date or start_date.year != end_date.year:
        raise ValueError("Expected an ordered window within one year")
    if id(collection.database.client) in _closing_clients:
        raise RuntimeError("Weather service is shutting down")
    key = (
        id(collection.database.client),
        collection.full_name,
        tuple(weather_key(location, start_date.year).items()),
    )
    while True:
        cached = await run_cache_operation(
            load_weather_year, collection, location, start_date.year
        )

        if cached is not None and not missing_weather_periods(
            cached, start_date, end_date
        ):
            return cached
        task = _inflight.get(key)
        if task is None:
            task = asyncio.create_task(
                _load_or_fetch_weather_window(
                    collection,client,location,start_date,end_date
                )
            )
            _inflight[key] = task
            def cleanup(finished):
                if _inflight.get(key) is finished:
                    del _inflight[key]
                if not finished.cancelled():
                    finished.exception()
            
            task.add_done_callback(cleanup)

        record = await asyncio.shield(task)

        if not missing_weather_periods(record, start_date, end_date):
            return record



async def get_weather_year(
    collection,
    client: httpx.AsyncClient,
    location: Location,
    year: int,
) -> WeatherYear:
    return await get_weather_window(
        collection,
        client,
        location,
        date(year, 1, 1),
        date(year, 12, 31),
    )

def missing_weather_periods(
    record: WeatherYear | None,
    start_date:date,
    end_date:date
) -> list[tuple[date,date]]:
    if end_date < start_date or start_date.year != end_date.year:
        raise ValueError("Expected an ordered window within one year")
    if record is None:
        return [(start_date,end_date)]
    if record.year != start_date.year:
        raise ValueError("Cache year does not match requested dates")
    
    if record.fetched_dates is None:
        return []

    fetched = set(record.fetched_dates)
    periods = []
    period_start = None

    for offset in range((end_date - start_date).days +1):
        current = start_date + timedelta(days=offset)

        if current not in fetched:
            if period_start is None:
                period_start = current
        elif period_start is not None:
            periods.append((period_start, current - timedelta(days=1)))
            period_start = None
    
    if period_start is not None:
        periods.append((period_start,end_date))

    return periods



def merge_weather_window(
    record: WeatherYear | None,
    location: Location,
    payload: dict,
    start_date: date,
    end_date: date,
) -> WeatherYear:
    if start_date.year != end_date.year:
        raise ValueError("Merge window must stay within one year")
    
    window_days, window_invalid = parse_weather_window(
        payload,start_date,end_date
    )

    year = start_date.year
    first = date(year,1,1)
    count = (date(year+1,1,1)- first).days

    grid = (
        payload.get("latitude"),
        payload.get("longitude"),
        payload.get("timezone"),
    )


    if record is not None:
        if weather_key(record.location, record.year) != weather_key(location, year):
            raise ValueError("Cache location or year does not match")
        if grid != (
            record.grid_latitude,
            record.grid_longitude,
            record.timezone,
        ):
            raise ValueError("Weather grid or timezone changed")

        days = list(record.days)
        fetched = (
            {day.date for day in days}
            if record.fetched_dates is None
            else set(record.fetched_dates)
        )
        invalid = set(record.invalid_dates)

    else:
        days = [
            DailyTemperature(
                date=first + timedelta(days=i),
                max_temperature_c=None,
            )
            for i in range(count)
        ]
        fetched = set()
        invalid = set()
    if any(day.date in fetched for day in window_days):
        raise ValueError("Merge must contain only unfetched dates")

    for day in window_days:
        days[(day.date - first).days]=day
        fetched.add(day.date)
    invalid.update(window_invalid)

    return WeatherYear(
        location=location,
        year=year,
        grid_latitude=grid[0],
        grid_longitude=grid[1],
        timezone=grid[2],
        fetched_at=datetime.now(timezone.utc),
        days=days,
        invalid_dates=sorted(invalid),
        fetched_dates=None if len(fetched) == count else sorted(fetched),
        expected_days=count,
        valid_days=sum(day.max_temperature_c is not None for day in days),
    )
    

async def _load_or_fetch_weather_window(
    collection,
    client: httpx.AsyncClient,
    location: Location,
    start_date: date,
    end_date: date
) -> WeatherYear:
     if end_date < start_date or start_date.year != end_date.year:
        raise ValueError("Expected an ordered window within one year")

     record = await run_cache_operation(
        load_weather_year, collection, location, start_date.year
     )

     for start,stop in missing_weather_periods(
        record,start_date,end_date
     ):
        payload = await fetch_weather_window_payload(
            client,location,start,stop
        )

        merged = merge_weather_window(
            record,location,payload,start,stop
        )

        await run_cache_operation(save_weather_year,collection,merged)

        record = await run_cache_operation(
            load_weather_year, collection, location, start_date.year
        )

        if record is None:
            raise RuntimeError("Weather record missing after cache write")

     if record is None:
        raise RuntimeError("Requested weather window was not loaded")
     return record




async def get_weather_dates(
    collection,
    client: httpx.AsyncClient,
    location: Location,
    start_date: date,
    end_date: date,
) -> list[DailyTemperature]:
    if end_date < start_date:
        raise ValueError("End date must not precede start date")

    days = []
    cursor = start_date

    while cursor <= end_date:
        stop = min(end_date, date(cursor.year, 12, 31))
        record = await get_weather_window(
            collection, client, location, cursor, stop
        )
        days.extend(
            day for day in record.days
            if cursor <= day.date <= stop
        )
        cursor = stop + timedelta(days=1)

    return days
