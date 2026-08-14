"""Tests for models and dataclasses."""
import pytest
from datetime import datetime, timezone
from app.models import NSOReleaseRecord, FFReleaseRecord, make_uid


class TestNSOReleaseRecord:
    def test_source_uid_stable(self):
        dt = datetime(2026, 8, 14, 10, 0, tzinfo=timezone.utc)
        r1 = NSOReleaseRecord(source_code="istat", title="CPI", release_dt=dt)
        r2 = NSOReleaseRecord(source_code="istat", title="CPI", release_dt=dt)
        assert r1.source_uid == r2.source_uid

    def test_source_uid_different_code(self):
        dt = datetime(2026, 8, 14, 10, 0, tzinfo=timezone.utc)
        r1 = NSOReleaseRecord(source_code="istat", title="CPI", release_dt=dt)
        r2 = NSOReleaseRecord(source_code="ine", title="CPI", release_dt=dt)
        assert r1.source_uid != r2.source_uid

    def test_source_uid_different_title(self):
        dt = datetime(2026, 8, 14, 10, 0, tzinfo=timezone.utc)
        r1 = NSOReleaseRecord(source_code="istat", title="CPI", release_dt=dt)
        r2 = NSOReleaseRecord(source_code="istat", title="GDP", release_dt=dt)
        assert r1.source_uid != r2.source_uid

    def test_source_uid_different_dt(self):
        r1 = NSOReleaseRecord(source_code="istat", title="CPI",
                              release_dt=datetime(2026, 8, 14, 10, 0, tzinfo=timezone.utc))
        r2 = NSOReleaseRecord(source_code="istat", title="CPI",
                              release_dt=datetime(2026, 8, 15, 10, 0, tzinfo=timezone.utc))
        assert r1.source_uid != r2.source_uid


class TestFFReleaseRecord:
    def test_source_uid_stable(self):
        dt = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
        r1 = FFReleaseRecord(title="CPI m/m", release_dt=dt, impact="high")
        r2 = FFReleaseRecord(title="CPI m/m", release_dt=dt, impact="high")
        assert r1.source_uid == r2.source_uid

    def test_source_uid_includes_actual_changes(self):
        """UID should NOT change when actual value changes (same event, just updated)."""
        dt = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
        r1 = FFReleaseRecord(title="CPI m/m", release_dt=dt, impact="high", actual=None)
        r2 = FFReleaseRecord(title="CPI m/m", release_dt=dt, impact="high", actual="0.2%")
        assert r1.source_uid == r2.source_uid


class TestMakeUid:
    def test_make_uid_deterministic(self):
        uid1 = make_uid("istat", "CPI", "2026-08-14T10:00:00+00:00")
        uid2 = make_uid("istat", "CPI", "2026-08-14T10:00:00+00:00")
        assert uid1 == uid2

    def test_make_uid_64_chars(self):
        uid = make_uid("test")
        assert len(uid) == 64
