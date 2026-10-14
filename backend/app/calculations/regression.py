import numpy as np

from app.models import (
    AnnualHeatwaveMetrics,
    HeatwaveRegression,
    RegressionPoint,
)


def calculate_event_start_regression(
    annual: list[AnnualHeatwaveMetrics],
) -> HeatwaveRegression:
    years = [row.year for row in annual]
    if years != sorted(set(years)):
        raise ValueError("Annual years must be unique and ordered")

    usable = [
        row for row in annual
        if row.metrics_complete
        and type(row.events_starting_in_selection) is int
        and row.events_starting_in_selection >= 0
    ]
    years_used = [row.year for row in usable]

    if len(usable) < 10:
        return HeatwaveRegression(
            status="unavailable",
            reason="insufficient_complete_years",
            years_used=years_used,
            slope_events_per_year=None,
            change_per_decade=None,
            fitted_values=[],
        )

    x = np.array(years_used, dtype=float)
    y = np.array(
        [row.events_starting_in_selection for row in usable],
        dtype=float,
    )

    # Centering keeps the arithmetic stable while retaining actual year gaps.
    centered_x = x - x.mean()
    centered_y = y - y.mean()

    slope = float(
        np.dot(centered_x, centered_y)
        / np.dot(centered_x, centered_x)
    )
    fitted = y.mean() + slope * centered_x

    return HeatwaveRegression(
        status="available",
        reason=None,
        years_used=years_used,
        slope_events_per_year=slope,
        change_per_decade=slope * 10,
        fitted_values=[
            RegressionPoint(
                year=row.year,
                observed_event_starts=row.events_starting_in_selection,
                fitted_event_starts=float(value),
            )
            for row, value in zip(usable, fitted)
        ],
    )

    