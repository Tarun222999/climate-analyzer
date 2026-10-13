
from re import I
import httpx
import asyncio

from math import ceil
from datetime import date, timedelta,datetime, timezone
from pydantic import ValidationError
from models import DailyTemperature
from models import Location
from email.utils import parsedate_to_datetime
from usage import wait_for_usage


def parse_weather_days(
    payload:dict,year:int
)-> tuple[list[DailyTemperature],list[date]]:
    units = payload.get("daily_units")
    if not isinstance(units,dict):
        raise ValueError("Missing daily units")
    if units.get("temperature_2m_max") != "\u00b0C":
        raise ValueError("Expected Celsius temperatures")
    daily = payload.get("daily")

    if not isinstance(daily,dict):
        raise ValueError("Missing daily weather data")

    dates = daily.get("time")
    temperatures = daily.get("temperature_2m_max")
    if not isinstance(dates, list) or not isinstance(temperatures, list):
        raise ValueError("Expected date and temperature arrays")
    
    first_day = date(year,1,1)
    day_count = (date(year+1,1,1)-first_day).days

    expected_dates = [
        (first_day + timedelta(days=i)).isoformat()
        for i in range(day_count)
    ]

    if dates != expected_dates:
        raise ValueError("Expected every date in the year, in order")
    if len(temperatures) != day_count:
        raise ValueError("Date and temperature counts differ")
        

    days = []
    invalid_dates = []

    for day,temperature in zip(dates,temperatures):
        try:
            record = DailyTemperature(
                date=day,
                max_temperature_c=temperature,
            )
        except ValidationError:
           record = DailyTemperature(date=day, max_temperature_c=None)
           invalid_dates.append(record.date)

        days.append(record)
    
    return days,invalid_dates


def retry_after_seconds(
    value:str | None,
    now:datetime
) -> float | None:
    if value is None:
        return None
    value = value.strip()
    if value.isascii() and value.isdigit():
        return float(value)
    try:
        retry_at = parsedate_to_datetime(value)
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)
        return max(0.0, (retry_at - now).total_seconds())
    except (ValueError, TypeError, OverflowError):
        return None




_weather_slots = asyncio.Semaphore(2)


async def fetch_weather_payload(
    client: httpx.AsyncClient,
    location: Location,
    year: int,
) -> dict:
    params = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "start_date": f"{year}-01-01",
        "end_date": f"{year}-12-31",
        "daily": "temperature_2m_max",
        "models": "era5_land",
        "timezone": location.timezone,
        "temperature_unit": "celsius",
    }

    days_in_year = (date(year + 1, 1, 1) - date(year, 1, 1)).days
    request_cost = ceil(days_in_year / 14)

    for attempt in range(3):
        try:
            async with _weather_slots:
                await wait_for_usage(request_cost)
                response = await client.get(
                    "https://archive-api.open-meteo.com/v1/archive",
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            retryable = exc.response.status_code in {
                429, 500, 502, 503, 504
            }
            if not retryable or attempt == 2:
                raise

            delay = retry_after_seconds(
                exc.response.headers.get("Retry-After"),
                datetime.now(timezone.utc),
            )
            if delay is None:
                delay = float(2 ** attempt)

            # Stop rather than retry earlier than the server requested.
            if delay > 10:
                raise

        except httpx.TransportError:
            if attempt == 2:
                raise
            delay = float(2 ** attempt)

        else:
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Expected a weather response object")
            return payload

        await asyncio.sleep(delay)

    raise RuntimeError("Retry loop ended unexpectedly")