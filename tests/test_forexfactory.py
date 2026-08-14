"""Tests for ForexFactory collector."""
import pytest
from app.collectors.forexfactory_collector import ForexFactoryCollector


class TestForexFactoryCollector:
    def test_parse_datetime_regular(self):
        dt = ForexFactoryCollector._parse_datetime("Aug 14", "8:00am", 2026)
        assert dt.year == 2026
        assert dt.month == 8
        assert dt.day == 14
        # 8:00am ET = 12:00 UTC (EDT, UTC-4)
        assert dt.hour == 12

    def test_parse_datetime_pm(self):
        dt = ForexFactoryCollector._parse_datetime("Aug 14", "4:00pm", 2026)
        # 4:00pm ET = 20:00 UTC
        assert dt.hour == 20

    def test_parse_datetime_tentative(self):
        dt = ForexFactoryCollector._parse_datetime("Aug 14", "Tentative", 2026)
        assert dt.day == 14
        assert dt.hour == 4  # midnight ET = 4:00 UTC

    def test_parse_datetime_all_day(self):
        dt = ForexFactoryCollector._parse_datetime("Aug 14", "All Day", 2026)
        assert dt.day == 14

    def test_parse_datetime_12am(self):
        dt = ForexFactoryCollector._parse_datetime("Aug 14", "12:00am", 2026)
        assert dt.hour == 4  # midnight ET = 4:00 UTC

    def test_parse_datetime_12pm(self):
        dt = ForexFactoryCollector._parse_datetime("Aug 14", "12:00pm", 2026)
        assert dt.hour == 16  # noon ET = 16:00 UTC

    def test_parse_datetime_no_date(self):
        dt = ForexFactoryCollector._parse_datetime(None, "8:00am", 2026)
        # Should return current time as fallback
        assert dt is not None

    def test_shift_month_positive(self):
        assert ForexFactoryCollector._shift_month(2026, 1, 1) == (2026, 2)
        assert ForexFactoryCollector._shift_month(2026, 12, 1) == (2027, 1)
        assert ForexFactoryCollector._shift_month(2026, 6, 3) == (2026, 9)

    def test_shift_month_negative(self):
        assert ForexFactoryCollector._shift_month(2026, 2, -1) == (2026, 1)
        assert ForexFactoryCollector._shift_month(2026, 1, -1) == (2025, 12)

    def test_month_range(self):
        months = ForexFactoryCollector._month_range(2026, 6, 2026, 8)
        assert months == [(2026, 6), (2026, 7), (2026, 8)]

    def test_month_range_cross_year(self):
        months = ForexFactoryCollector._month_range(2026, 11, 2027, 2)
        assert months == [(2026, 11), (2026, 12), (2027, 1), (2027, 2)]

    def test_routine_month_range(self):
        """Verify the routine scrape covers 5 months (lookback 1 + current + lookahead 3)."""
        c = ForexFactoryCollector()
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        start_y, start_m = c._shift_month(now.year, now.month, -1)
        end_y, end_m = c._shift_month(now.year, now.month, 3)
        months = c._month_range(start_y, start_m, end_y, end_m)
        assert len(months) == 5
