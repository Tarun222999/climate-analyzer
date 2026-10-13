"""Storage monitoring and location-scoped cache invalidation."""
import asyncio
import logging
from math import isfinite

from pymongo.errors import PyMongoError

from cache_io import run_cache_operation
from models import Location

logger = logging.getLogger(__name__)


def storage_report(database, budget_bytes: int) -> dict:
    stats = database.command("dbStats", scale=1)
    sizes = [stats.get("dataSize"), stats.get("indexSize")]
    if any(not isinstance(value, (int, float)) or not isfinite(value) or value < 0 for value in sizes):
        raise ValueError("Storage statistics unavailable")
    logical_bytes = sum(sizes)
    percent = logical_bytes / budget_bytes * 100
    return {
        "scope": "configured_database_only",
        "data_bytes": sizes[0],
        "index_bytes": sizes[1],
        "logical_bytes": logical_bytes,
        "budget_bytes": budget_bytes,
        "utilization_percent": round(percent, 2),
        "warning": percent >= 80,
        "note": "Other cluster databases also consume quota; check Atlas Logical Size.",
    }


async def monitor_storage(database, budget_bytes, stop, interval_seconds=300):
    while not stop.is_set():
        try:
            report = await run_cache_operation(storage_report, database, budget_bytes)
            if report["warning"]:
                logger.warning("Cache database uses %.2f%% of its storage budget", report["utilization_percent"])
            else:
                logger.info("Cache database storage budget usage: %.2f%%", report["utilization_percent"])
        except (PyMongoError, ValueError) as exc:
            # Never put connection strings or raw driver errors in logs.
            logger.warning("Storage monitoring unavailable (%s)", type(exc).__name__)
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval_seconds)
        except TimeoutError:
            pass


def invalidation_plan(location: Location, kind: str, year: int | None = None):
    location_filter = {
        "location.latitude": location.latitude,
        "location.longitude": location.longitude,
        "location.timezone": location.timezone,
    }
    analyses_filter = {f"request.{key}": value for key, value in location_filter.items()}
    # Remove derived results first, then their inputs. All method versions
    # at this location are invalidated so older results cannot survive.
    plan = [("analyses", analyses_filter)]
    if kind == "baseline":
        plan.append(("baseline_thresholds", location_filter))
    elif kind == "weather":
        if year is None or not 1950 <= year <= 9998:
            raise ValueError("Weather invalidation requires a year from 1950 to 9998")
        if 1991 <= year <= 2020:
            plan.append(("baseline_thresholds", location_filter))
        plan.append(("weather_years", {**location_filter, "year": year}))
    elif kind != "analyses":
        raise ValueError("Unknown cache kind")
    return plan


def invalidate_cache(database, location, kind, year=None, apply=False):
    result = {}
    for collection, query in invalidation_plan(location, kind, year):
        if apply:
            result[collection] = database[collection].delete_many(query).deleted_count
        else:
            result[collection] = database[collection].count_documents(query)
    return {"applied": apply, "documents": result}
