



from math import isfinite
from backend.models import DailyTemperature, HeatwaveEvent


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

