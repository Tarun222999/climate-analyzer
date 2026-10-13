import support
import unittest
from datetime import date, datetime, timedelta, timezone

from pydantic import ValidationError

from app.services.analysis_service import (
    analyze_heatwave_selection, calculate_annual_metrics,
    calculate_rolling_averages, generate_heatwave_insights,
)
from app.calculations.baseline import calculate_baseline_threshold
from app.calculations.heatwaves import detect_heatwaves, select_heatwaves
from app.models import AnalysisRequest, AnnualHeatwaveMetrics, DailyTemperature, Location, WeatherYear
from app.services.weather import parse_weather_window


LOCATION = Location(name="Test", latitude=28.65, longitude=77.23, timezone="Asia/Kolkata")


class ClimateTests(unittest.TestCase):
    def days(self, values, first=date(2020, 1, 1)):
        return [DailyTemperature(date=first+timedelta(days=i), max_temperature_c=value) for i, value in enumerate(values)]

    def test_strict_threshold_missing_readings_and_cross_year_event(self):
        self.assertEqual(detect_heatwaves(self.days([40.0, 42.0, 42.0, 41.1, 42.0, 42.0, None, 42.0]), 41.1), [])
        events = detect_heatwaves(self.days([40.0, 42.0, 44.0, 43.0, 40.0], date(2019, 12, 29)), 41.1)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].observed_start_date, date(2019, 12, 30))
        self.assertEqual(events[0].observed_end_date, date(2020, 1, 1))
        self.assertTrue(events[0].start_boundary_resolved and events[0].end_boundary_resolved)
        selected = select_heatwaves(self.days([40.0, 45.0, 44.0, 43.0, 40.0], date(2019, 12, 29)), 41.1, date(2020, 1, 1), date(2020, 12, 31))[0]
        self.assertEqual(selected.days_in_selection, 1)
        self.assertEqual(selected.peak_temperature_in_selection_c, 43.0)
        self.assertEqual(selected.full_duration_days, 3)

    def test_window_preserves_missing_and_invalid_values_and_rejects_duplicate_dates(self):
        payload = {"daily_units": {"temperature_2m_max": "\u00b0C"}, "daily": {
            "time": ["2020-01-01", "2020-01-02", "2020-01-03"],
            "temperature_2m_max": [42.0, None, 100.0],
        }}
        days, invalid = parse_weather_window(payload, date(2020, 1, 1), date(2020, 1, 3))
        self.assertEqual([day.max_temperature_c for day in days], [42.0, None, None])
        self.assertEqual(invalid, [date(2020, 1, 3)])
        payload["daily"]["time"][1] = "2020-01-01"
        with self.assertRaises(ValueError):
            parse_weather_window(payload, date(2020, 1, 1), date(2020, 1, 3))

    def test_baseline_fixed_years_percentile_and_coverage(self):
        records = []
        for year in range(1991, 2021):
            first = date(year, 1, 1)
            count = (date(year+1, 1, 1)-first).days
            days = self.days([40.0]*count, first)
            records.append(WeatherYear(location=LOCATION, year=year, grid_latitude=28.7,
                grid_longitude=77.2, timezone="Asia/Kolkata", fetched_at=datetime.now(timezone.utc),
                days=days, invalid_dates=[], expected_days=count, valid_days=count))
        self.assertEqual(calculate_baseline_threshold(records), 40.0)
        with self.assertRaises(ValueError):
            calculate_baseline_threshold(records[:-1])
        for i in range(2):
            record = records[i]
            records[i] = WeatherYear.model_validate({**record.model_dump(), "valid_days": 0,
                "days": [day.model_copy(update={"max_temperature_c": None}) for day in record.days]})
        with self.assertRaises(ValueError):
            calculate_baseline_threshold(records)

    def test_annual_clipping_and_missing_year_exclusion(self):
        first, last = date(2018, 12, 30), date(2021, 1, 2)
        days = self.days([40.0]*((last-first).days+1), first)
        hot_start, hot_end = date(2019, 12, 30), date(2020, 1, 2)
        days = [day.model_copy(update={"max_temperature_c": 44.0}) if hot_start <= day.date <= hot_end else day for day in days]
        request = AnalysisRequest(location=LOCATION, start_year=2019, end_year=2020)
        summary, events = analyze_heatwave_selection(days, request, 41.1)
        annual = calculate_annual_metrics(days, request, 41.1)
        self.assertEqual([row.events_starting_in_selection for row in annual], [1, 0])
        self.assertEqual([row.heatwave_days for row in annual], [2, 2])
        self.assertEqual(summary.heatwave_days, 4)
        missing = [day.model_copy(update={"max_temperature_c": None}) if day.date == date(2020, 6, 1) else day for day in days]
        annual = calculate_annual_metrics(missing, request, 41.1)
        self.assertTrue(annual[0].metrics_complete)
        self.assertFalse(annual[1].metrics_complete)
        self.assertIsNone(annual[1].heatwave_days)

    def test_rolling_windows_and_zero_denominator_insights(self):
        annual = []
        for year in range(2000, 2010):
            count = 0 if year < 2005 else 4
            expected = (date(year+1, 1, 1)-date(year, 1, 1)).days
            annual.append(AnnualHeatwaveMetrics(year=year, events_starting_in_selection=count,
                heatwave_days=count*3, longest_duration_in_selection_days=3 if count else 0,
                peak_temperature_c=44.0 if count else None, peak_above_threshold_c=2.9 if count else None,
                expected_days=expected, valid_days=expected, metrics_complete=True))
        rolling = calculate_rolling_averages(annual)
        self.assertTrue(all(row.heatwave_days_average is None for row in rolling[:4]))
        self.assertEqual(rolling[-1].heatwave_days_average, 12.0)
        self.assertTrue(all("earlier average was zero" in text for text in generate_heatwave_insights(annual)))
        self.assertIn("at least 10", generate_heatwave_insights(annual[:9])[0])
        annual[-1] = AnnualHeatwaveMetrics.model_validate({**annual[-1].model_dump(), "metrics_complete": False,
            "valid_days": annual[-1].expected_days-1, "heatwave_days": None,
            "events_starting_in_selection": None, "longest_duration_in_selection_days": None})
        self.assertIsNone(calculate_rolling_averages(annual)[-1].heatwave_days_average)
        self.assertIn("unavailable", generate_heatwave_insights(annual)[0])
