from datetime import date


import numpy as np

from models import WeatherYear


BASELINE_START_YEAR = 1991
BASELINE_END_YEAR = 2020
BASELINE_PERCENTILE = 95
MIN_BASELINE_COVERAGE = 0.95


def calculate_baseline_threshold(records:list[WeatherYear]) -> float :
    expected_years = list(
        range(BASELINE_START_YEAR,BASELINE_END_YEAR+1)
    )

    if sorted(record.year for record in records) != expected_years:
        raise ValueError("Baseline requires each year from 1991 through 2020")
    
    locations_and_sources = {
        (
            record.location.latitude,
            record.location.longitude,
            record.location.timezone,
            record.grid_latitude,
            record.grid_longitude,
            record.timezone,
            record.source,
            record.dataset,
            record.temperature_unit,
        )
        for record in records
    }

    if len(locations_and_sources) != 1:
        raise ValueError("Baseline records must use one location and dataset")
    
    temperatures = [
       day.max_temperature_c
       for record in records
       for day in record.days
       if day.max_temperature_c is not None
    ]


    expected_days = (
        date(BASELINE_END_YEAR + 1, 1, 1)
        - date(BASELINE_START_YEAR, 1, 1)
    ).days

    if len(temperatures) / expected_days < MIN_BASELINE_COVERAGE:
        raise ValueError("Insufficient baseline data: require 95% coverage")

    return float(
        np.percentile(temperatures, BASELINE_PERCENTILE, method="linear")
    )

