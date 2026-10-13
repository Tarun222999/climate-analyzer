import asyncio
import httpx

from datetime import datetime, timezone

from app.calculations.baseline import (
    BASELINE_END_YEAR,
    BASELINE_START_YEAR,
    calculate_baseline_threshold,
)
from app.storage.cache import load_baseline_threshold, save_baseline_threshold
from app.models import BaselineThreshold, Location
from app.services.weather_service import get_weather_year
from app.storage.cache_io import run_cache_operation


async def get_baseline_threshold(
    weather_collection,
    baseline_collection,
    client:httpx.AsyncClient,
    location:Location
) -> BaselineThreshold:
    cached = await run_cache_operation(
        load_baseline_threshold,baseline_collection,location
    )

    if cached is not None:
        return cached

    records = []

    for year in range(BASELINE_START_YEAR,BASELINE_END_YEAR +1):
        record = await get_weather_year(
            weather_collection,client,location,year
        )
        records.append(record)

    threshold = calculate_baseline_threshold(records)   
    first = records[0]


    baseline = BaselineThreshold(
        location=location,
        grid_latitude=first.grid_latitude,
        grid_longitude=first.grid_longitude,
        timezone=first.timezone,
        threshold_c=threshold,
        expected_days=sum(record.expected_days for record in records),
        valid_days=sum(record.valid_days for record in records),
        calculated_at=datetime.now(timezone.utc),
    )

    await run_cache_operation(
        save_baseline_threshold,baseline_collection,baseline
    )

    saved = await run_cache_operation(
        load_baseline_threshold,baseline_collection,location
    )

    if saved is None:
        raise RuntimeError("Baseline missing after cache write")
    return saved


