

from datetime import date, timedelta
from math import isfinite

from app.models import DailyTemperature, HeatwaveEvent, SelectedHeatwaveEvent

def detect_heatwaves(
    days:list[DailyTemperature],
    threshold_c:float
) -> list[HeatwaveEvent]:
    if not isfinite(threshold_c) or not -100 <= threshold_c <= 100:
        raise ValueError("Invalid heatwave threshold")
    events = []
    run: list[DailyTemperature] = []
    start_resolved = False


    def finish_run(end_resolved:bool) ->None:
        if len(run) >= 3:
            events.append(
                HeatwaveEvent(
                    observed_start_date=run[0].date,
                    observed_end_date=run[-1].date,
                    observed_duration_days=len(run),
                    peak_temperature_c=max(
                        day.max_temperature_c
                        for day in run
                        if day.max_temperature_c is not None
                    ),
                    start_boundary_resolved=start_resolved,
                    end_boundary_resolved=end_resolved,
                )
            )
        run.clear()

    #loop over every day
    for index, day in enumerate(days):
        previous = days[index-1] if index > 0 else None

        if previous is not None and day.date <= previous.date:
            raise ValueError("Dates must be unique and ordered")

        adjacent = (
            previous is not None
            and (day.date - previous.date).days ==1
        )

        #if there is no adjacent day current run records will form 
        #a heat wave if present
        if run and not adjacent:
            finish_run(False)

        temperature = day.max_temperature_c

        #if temp present check if comes under current run
        #else we may have a heat wave capture it
        if temperature is not None and temperature > threshold_c:
            if not run:
                start_resolved=(
                    adjacent
                    and previous is not None
                    and previous.max_temperature_c is not None
                    and previous.max_temperature_c <= threshold_c 
                )
            run.append(day)

        else:
            finish_run(temperature is not None)
    
    finish_run(False)
    return events;



def select_heatwaves(
    days: list[DailyTemperature],
    threshold_c: float,
    selection_start: date,
    selection_end: date,
) -> list[SelectedHeatwaveEvent]:
    if selection_end < selection_start:
        raise ValueError("Selection end must be at least selection start")

    events = detect_heatwaves(days, threshold_c)
    temperatures = {
        day.date: day.max_temperature_c
        for day in days
    }
    selected_events = []

    for event in events:
        # Keep only events that overlap the selected dates.
        start = max(event.observed_start_date, selection_start)
        end = min(event.observed_end_date, selection_end)

        if start > end:
            continue

        count = (end - start).days + 1
        selected_peak = max(
            temperatures[start + timedelta(days=i)]
            for i in range(count)
        )

        starts_before = (
            True
            if event.observed_start_date < selection_start
            else False if event.start_boundary_resolved else None
        )
        ends_after = (
            True
            if event.observed_end_date > selection_end
            else False if event.end_boundary_resolved else None
        )

        selected_events.append(
            SelectedHeatwaveEvent(
                **event.model_dump(),
                selected_start_date=start,
                selected_end_date=end,
                days_in_selection=count,
                peak_temperature_in_selection_c=selected_peak,
                full_duration_days=(
                    event.observed_duration_days
                    if event.start_boundary_resolved
                    and event.end_boundary_resolved
                    else None
                ),
                starts_before_selection=starts_before,
                ends_after_selection=ends_after,
            )
        )

    return selected_events