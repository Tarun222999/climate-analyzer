import support
import unittest
from datetime import date

from app.calculations.regression import calculate_event_start_regression
from app.models import AnnualHeatwaveMetrics, HeatwaveRegression


def annual_row(year, count, complete=True):
    expected = (date(year + 1, 1, 1) - date(year, 1, 1)).days
    return AnnualHeatwaveMetrics(
        year=year,
        events_starting_in_selection=count,
        heatwave_days=count * 3 if count is not None else None,
        longest_duration_in_selection_days=3 if count else 0,
        peak_temperature_c=44.0 if count else None,
        peak_above_threshold_c=2.9 if count else None,
        expected_days=expected,
        valid_days=expected if complete else expected - 1,
        metrics_complete=complete,
    )


class RegressionTests(unittest.TestCase):
    def test_increasing_and_decreasing_counts(self):
        for direction in (1, -1):
            with self.subTest(direction=direction):
                rows = [
                    annual_row(2000 + i, i * 2 if direction == 1 else 18 - i * 2)
                    for i in range(10)
                ]
                trend = calculate_event_start_regression(rows)
                self.assertEqual(trend.status, "available")
                self.assertAlmostEqual(trend.slope_events_per_year, direction * 2)
                self.assertAlmostEqual(trend.change_per_decade, direction * 20)
                for point, row in zip(trend.fitted_values, rows):
                    self.assertAlmostEqual(
                        point.fitted_event_starts, row.events_starting_in_selection
                    )

    def test_constant_counts_produce_flat_trend(self):
        trend = calculate_event_start_regression([
            annual_row(year, 3) for year in range(2000, 2010)
        ])
        self.assertEqual(trend.status, "available")
        self.assertEqual(trend.slope_events_per_year, 0.0)
        self.assertTrue(all(
            point.fitted_event_starts == 3.0 for point in trend.fitted_values
        ))
        self.assertEqual(
            HeatwaveRegression.model_validate_json(trend.model_dump_json()), trend
        )

    def test_insufficient_years_return_no_fitted_results(self):
        for count in (0, 9):
            with self.subTest(count=count):
                trend = calculate_event_start_regression([
                    annual_row(2000 + i, 3) for i in range(count)
                ])
                self.assertEqual(trend.status, "unavailable")
                self.assertEqual(trend.reason, "insufficient_complete_years")
                self.assertIsNone(trend.slope_events_per_year)
                self.assertIsNone(trend.change_per_decade)
                self.assertEqual(trend.fitted_values, [])

    def test_incomplete_and_null_count_years_are_excluded(self):
        rows = [annual_row(year, 3) for year in range(2000, 2012)]
        rows[2] = annual_row(2002, 99, complete=False)
        rows[5] = annual_row(2005, None, complete=False)
        trend = calculate_event_start_regression(rows)
        self.assertEqual(len(trend.years_used), 10)
        self.assertNotIn(2002, trend.years_used)
        self.assertNotIn(2005, trend.years_used)
        self.assertEqual(trend.slope_events_per_year, 0.0)

    def test_actual_year_distances_preserved(self):
        years = list(range(2000, 2020, 2))
        trend = calculate_event_start_regression([
            annual_row(year, year - 2000) for year in years
        ])
        self.assertAlmostEqual(trend.slope_events_per_year, 1.0)
        self.assertEqual(trend.years_used, years)
        self.assertEqual([point.year for point in trend.fitted_values], years)

    def test_duplicate_or_unordered_years_rejected(self):
        for years in ([2000, 2000], [2001, 2000]):
            with self.subTest(years=years):
                with self.assertRaises(ValueError):
                    calculate_event_start_regression([
                        annual_row(year, 3) for year in years
                    ])
