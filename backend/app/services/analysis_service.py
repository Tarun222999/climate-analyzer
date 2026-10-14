from datetime import date, datetime, timedelta, timezone
from math import isfinite

import httpx
import asyncio

from app.services.baseline_service import get_baseline_threshold
from app.calculations.heatwaves import select_heatwaves
from app.models import (
    AnalysisRequest,
    AnalysisResult,
    AnnualHeatwaveMetrics,
    DailyTemperature,
    HeatwaveSummary,
    RollingHeatwaveMetrics,
    SelectedHeatwaveEvent,
)
from app.services.weather_service import get_weather_dates
from app.storage.cache_io import run_cache_operation
from app.storage.analysis_cache import load_analysis, save_analysis
from app.calculations.regression import calculate_event_start_regression


CONTEXT_PADDING_DAYS = 2
CONTEXT_CHUNK_DAYS = 30
MAX_CONTEXT_DAYS = 366


async def load_heatwave_context(
    collection,
    client: httpx.AsyncClient,
    request: AnalysisRequest,
    threshold_c: float,
    expected_grid: tuple | None = None,
) -> list[DailyTemperature]:
    if not isfinite(threshold_c) or not -100 <= threshold_c <= 70:
        raise ValueError("Invalid heatwave threshold")

    selection_start = date(request.start_year, 1, 1)
    selection_end = date(request.end_year, 12, 31)
    earliest = date(1950, 1, 1)
    latest = datetime.now(timezone.utc).date() - timedelta(days=5)

    if selection_end > latest:
        raise ValueError("Selected years exceed historical data availability")

    left_limit = max(
        earliest, selection_start - timedelta(days=MAX_CONTEXT_DAYS)
    )
    right_limit = min(
        latest, selection_end + timedelta(days=MAX_CONTEXT_DAYS)
    )

    start = max(
        left_limit, selection_start - timedelta(days=CONTEXT_PADDING_DAYS)
    )
    end = min(
        right_limit, selection_end + timedelta(days=CONTEXT_PADDING_DAYS)
    )

    days = await get_weather_dates(
        collection, client, request.location, start, end, expected_grid=expected_grid
    )

    def is_hot(day: DailyTemperature) -> bool:
        return (
            day.max_temperature_c is not None
            and day.max_temperature_c > threshold_c
        )

    while start > left_limit and all(
        is_hot(day) for day in days if day.date <= selection_start
    ):
        new_start = max(
            left_limit, start - timedelta(days=CONTEXT_CHUNK_DAYS)
        )
        extra = await get_weather_dates(
            collection, client, request.location,
            new_start, start - timedelta(days=1),
            expected_grid=expected_grid,
        )
        days = extra + days
        start = new_start

    while end < right_limit and all(
        is_hot(day) for day in days if day.date >= selection_end
    ):
        new_end = min(
            right_limit, end + timedelta(days=CONTEXT_CHUNK_DAYS)
        )
        extra = await get_weather_dates(
            collection, client, request.location,
            end + timedelta(days=1), new_end,
            expected_grid=expected_grid,
        )
        days.extend(extra)
        end = new_end

    return days



def calculate_heatwave_summary(
    events: list[SelectedHeatwaveEvent],
    selected_days: list[DailyTemperature],
    threshold_c: float,
    *,
    boundaries_complete: bool,
) -> HeatwaveSummary:
    if not selected_days:
        raise ValueError("Selected daily records are required")
    if not isfinite(threshold_c) or not -100 <= threshold_c <= 70:
        raise ValueError("Invalid heatwave threshold")

    
    for previous, current in zip(selected_days, selected_days[1:]):
        if (current.date - previous.date).days != 1:
            raise ValueError("Selected dates must be consecutive and ordered")

    selection_start = selected_days[0].date
    selection_end = selected_days[-1].date
    valid_days = sum(
        day.max_temperature_c is not None
        for day in selected_days
    )

    for event in events:
        if not (
            selection_start <= event.selected_start_date
            <= event.selected_end_date <= selection_end
        ):
            raise ValueError("Event portion lies outside the selection")


    complete = (
        valid_days == len(selected_days)
        and boundaries_complete
        and all(
            event.starts_before_selection is not None
            and event.ends_after_selection is not None
            for event in events
        )
    )


    peak = max(
        (event.peak_temperature_in_selection_c for event in events),
        default=None,
    )

    return HeatwaveSummary(
        events_starting_in_selection=(
            sum(event.starts_before_selection is False for event in events)
            if complete else None
        ),
        heatwave_days=(
            sum(event.days_in_selection for event in events)
            if complete else None
        ),
        longest_duration_in_selection_days=(
            max((event.days_in_selection for event in events), default=0)
            if complete else None
        ),
        peak_temperature_c=peak,
        peak_above_threshold_c=(
            peak - threshold_c if peak is not None else None
        ),
        expected_days=len(selected_days),
        valid_days=valid_days,
        metrics_complete=complete,
     )

    

def heatwave_boundaries_complete(
    days: list[DailyTemperature],
    threshold_c: float,
    selection_start: date,
    selection_end: date,
) -> bool:
    if selection_end < selection_start:
        raise ValueError("Invalid selection")
    if not isfinite(threshold_c) or not -100 <= threshold_c <= 70:
        raise ValueError("Invalid heatwave threshold")
    if not days:
        raise ValueError("Weather context is required")

    for previous, current in zip(days, days[1:]):
        if (current.date - previous.date).days != 1:
            raise ValueError("Context dates must be consecutive and ordered")

    if days[0].date > selection_start or days[-1].date < selection_end:
        raise ValueError("Context must cover the selection")

    def is_hot(day: DailyTemperature) -> bool:
        return (
            day.max_temperature_c is not None
            and day.max_temperature_c > threshold_c
        )

    def is_cool(day: DailyTemperature) -> bool:
        return (
            day.max_temperature_c is not None
            and day.max_temperature_c <= threshold_c
        )

    index = 0
    while index < len(days):
        if not is_hot(days[index]):
            index += 1
            continue

        start = index
        while index < len(days) and is_hot(days[index]):
            index += 1
        end = index - 1

        if (
            days[end].date < selection_start
            or days[start].date > selection_end
        ):
            continue

        left_known = start > 0 and is_cool(days[start - 1])
        right_known = index < len(days) and is_cool(days[index])

        if end - start + 1 < 3:
            # A short run could continue through an unknown boundary.
            if not (left_known and right_known):
                return False
        else:
            # Unknown boundaries outside the selection do not change
            # this event's selected dates or its starting-year count.
            if days[start].date >= selection_start and not left_known:
                return False
            if days[end].date <= selection_end and not right_known:
                return False

    return True


def analyze_heatwave_selection(
    days: list[DailyTemperature],
    request: AnalysisRequest,
    threshold_c: float,
) -> tuple[HeatwaveSummary, list[SelectedHeatwaveEvent]]:
    start = date(request.start_year, 1, 1)
    end = date(request.end_year, 12, 31)

    boundaries_complete = heatwave_boundaries_complete(
        days, threshold_c, start, end
    )

    events = select_heatwaves(
        days, threshold_c, start, end
    )

    selected_days = [
        day for day in days
        if start <= day.date <= end
    ]

    summary = calculate_heatwave_summary(
        events,
        selected_days,
        threshold_c,
        boundaries_complete=boundaries_complete,
    )

    return summary, events


def calculate_annual_metrics(
    days: list[DailyTemperature],
    request: AnalysisRequest,
    threshold_c: float,
) -> list[AnnualHeatwaveMetrics]:
    annual = []

    for year in range(request.start_year, request.end_year + 1):
        year_request = AnalysisRequest(
            location=request.location,
            start_year=year,
            end_year=year,
        )

        summary, _ = analyze_heatwave_selection(
            days, year_request, threshold_c
        )

        annual.append(
            AnnualHeatwaveMetrics(
                year=year,
                **summary.model_dump(),
            )
        )

    return annual


def calculate_rolling_averages(
    annual: list[AnnualHeatwaveMetrics],
) -> list[RollingHeatwaveMetrics]:
    years = [row.year for row in annual]
    if years != sorted(set(years)):
        raise ValueError("Annual years must be unique and ordered")

    rolling = []

    for index, row in enumerate(annual):
        window = annual[max(0, index - 4):index + 1]

        available = (
            len(window) == 5
            and [item.year for item in window]
            == list(range(row.year - 4, row.year + 1))
            and all(item.metrics_complete for item in window)
        )

        rolling.append(
            RollingHeatwaveMetrics(
                year=row.year,
                events_starting_average=(
                    sum(item.events_starting_in_selection for item in window) / 5
                    if available else None
                ),
                heatwave_days_average=(
                    sum(item.heatwave_days for item in window) / 5
                    if available else None
                ),
                longest_duration_average_days=(
                    sum(
                        item.longest_duration_in_selection_days
                        for item in window
                    ) / 5
                    if available else None
                ),
            )
        )

    return rolling



def generate_heatwave_insights(
    annual: list[AnnualHeatwaveMetrics],
) -> list[str]:
    years = [row.year for row in annual]
    if years != sorted(set(years)):
        raise ValueError("Annual years must be unique and ordered")

    if len(annual) < 10:
        return [
            "Select at least 10 years to compare two separate five-year periods."
        ]

    earlier = annual[:5]
    later = annual[-5:]

    for period in (earlier, later):
        if (
            [row.year for row in period]
            != list(range(period[0].year, period[0].year + 5))
            or not all(row.metrics_complete for row in period)
        ):
            return [
                "Five-year comparison unavailable: a comparison period "
                "contains missing years or incomplete metrics."
            ]

    insights = []

    for field, label in (
        ("events_starting_in_selection", "heatwave starts"),
        ("heatwave_days", "heatwave days"),
    ):
        earlier_average = sum(getattr(row, field) for row in earlier) / 5
        later_average = sum(getattr(row, field) for row in later) / 5
        difference = later_average - earlier_average

        message = (
            f"Average annual {label}: "
            f"{earlier_average:.2f} in {earlier[0].year}-{earlier[-1].year}, "
            f"versus {later_average:.2f} in {later[0].year}-{later[-1].year}. "
            f"Change: {difference:+.2f} per year."
        )

        if earlier_average == 0:
            message += (
                " Percentage change is unavailable because "
                "the earlier average was zero."
            )
        else:
            percent = difference / earlier_average * 100
            message += f" Percentage change: {percent:+.1f}%."

        insights.append(message)

    return insights

async def build_analysis(
    weather_collection,
    baseline_collection,
    client: httpx.AsyncClient,
    request: AnalysisRequest,
) -> AnalysisResult:
    baseline = await get_baseline_threshold(
        weather_collection,
        baseline_collection,
        client,
        request.location,
    )

    days = await load_heatwave_context(
        weather_collection,
        client,
        request,
        baseline.threshold_c,
        expected_grid=(
            baseline.grid_latitude, baseline.grid_longitude, baseline.timezone,
            baseline.source, baseline.dataset, baseline.temperature_unit,
        ),
    )

    summary, events = analyze_heatwave_selection(
        days, request, baseline.threshold_c
    )
    annual = calculate_annual_metrics(
        days, request, baseline.threshold_c
    )

    return AnalysisResult(
        request=request,
        baseline=baseline,
        summary=summary,
        annual=annual,
        rolling_averages=calculate_rolling_averages(annual),
        regression=calculate_event_start_regression(annual),
        events=events,
        insights=generate_heatwave_insights(annual),
        calculated_at=datetime.now(timezone.utc),
    )


async def get_analysis(
    weather_collection,
    baseline_collection,
    analysis_collection,
    client: httpx.AsyncClient,
    request: AnalysisRequest,
) -> AnalysisResult:
    cached = await run_cache_operation(
        load_analysis, analysis_collection, request
    )

    if cached is None:
        result = await build_analysis(
            weather_collection,
            baseline_collection,
            client,
            request,
        )

        stored = await run_cache_operation(
            save_analysis, analysis_collection, result
        )

        if not stored:
            return result

        cached = await run_cache_operation(
            load_analysis, analysis_collection, request
        )
        if cached is None:
            raise RuntimeError("Analysis missing after cache write")

    # The cache identifies locations by coordinates and timezone.
    # Return the display name supplied in this request.
    return AnalysisResult.model_validate({
        **cached.model_dump(),
        "request": request.model_dump(),
    })
