"""Tests for Destatis collector."""
import pytest
from datetime import datetime, timezone
from app.collectors.destatis_collector import DestatisCollector


class TestDestatisCollector:
    def test_parse_date_simple(self):
        dt = DestatisCollector._parse_date("2026.08.14")
        assert dt.year == 2026
        assert dt.month == 8
        assert dt.day == 14
        # 08:00 Berlin = 06:00 UTC (CEST, UTC+2)
        assert dt.hour == 6

    def test_parse_date_with_deadline(self):
        dt = DestatisCollector._parse_date("2026.08.14 (deadline)")
        assert dt.year == 2026
        assert dt.day == 14

    def test_parse_date_winter(self):
        """Winter: CET = UTC+1, so 08:00 CET = 07:00 UTC."""
        dt = DestatisCollector._parse_date("2026.12.18")
        assert dt.hour == 7  # winter time

    def test_parse_date_invalid(self):
        with pytest.raises(ValueError):
            DestatisCollector._parse_date("invalid date")

    def test_source_code(self):
        c = DestatisCollector()
        assert c.source_code() == "destatis"

    def test_topics_count(self):
        assert len(DestatisCollector.TOPICS) == 13
