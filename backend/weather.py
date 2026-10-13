import httpx

from datetime import date, timedelta
from pydantic import ValidationError
from models import DailyTemperature
from models import Location

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






async def fetch_weather_payload(
    client:httpx.AsyncClient,
    location:Location,
    year:int
) -> dict:
    response = await client.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params = {
            "latitude":location.latitude,
            "longitude":location.longitude,
           "start_date": f"{year}-01-01",
            "end_date": f"{year}-12-31",
            "daily": "temperature_2m_max",
            "models": "era5_land",
            "timezone": location.timezone,
            "temperature_unit": "celsius",
        },
        timeout=30.0
    )

    response.raise_for_status()

    payload = response.json()

    if not isinstance(payload,dict):
        raise ValueError("Expected a weather response object")
    return payload

