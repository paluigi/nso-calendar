"""ICS feed collector for Eurostat, Istat, INE."""
from __future__ import annotations

import re
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

import icalendar
import requests

from app.collectors.base import BaseNSOCollector
from app.models import NSOReleaseRecord


class ICSCollector(BaseNSOCollector):
    """Fetches and parses iCalendar (.ics) feeds from NSO websites."""

    def __init__(
        self,
        code: str,
        feed_urls: list[str],
        default_tz: str = "UTC",
        default_hour: int = 9,
        timeout: int = 30,
    ):
        self._code = code
        self._urls = feed_urls
        self._tz = ZoneInfo(default_tz)
        self._hour = default_hour
        self._timeout = timeout

    def source_code(self) -> str:
        return self._code

    def collect(self) -> list[NSOReleaseRecord]:
        records: list[NSOReleaseRecord] = []
        for url in self._urls:
            try:
                resp = requests.get(
                    url,
                    timeout=self._timeout,
                    headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
                )
                resp.raise_for_status()
                # ICS feeds are UTF-8; requests falls back to latin-1 when the
                # Content-Type header carries no charset.
                cal = icalendar.Calendar.from_ical(resp.content)
                for event in cal.walk("VEVENT"):
                    dtstart = event.get("DTSTART")
                    if dtstart is None:
                        continue
                    dt = dtstart.dt

                    # Handle both date and datetime objects
                    if isinstance(dt, datetime):
                        if dt.tzinfo:
                            dt_utc = dt.astimezone(timezone.utc)
                        else:
                            dt_utc = dt.replace(tzinfo=self._tz).astimezone(timezone.utc)
                    else:
                        # date-only: apply default publish time
                        dt_utc = datetime.combine(
                            dt, time(self._hour, 0), tzinfo=self._tz
                        ).astimezone(timezone.utc)

                    summary = str(event.get("SUMMARY", "")).strip()
                    if not summary:
                        continue

                    description = str(event.get("DESCRIPTION", ""))
                    ref_period = self._extract_ref_period(description)

                    url_field = event.get("URL")
                    url_val = str(url_field) if url_field else None

                    records.append(
                        NSOReleaseRecord(
                            source_code=self._code,
                            title=summary,
                            release_dt=dt_utc,
                            reference_period=ref_period,
                            url=url_val,
                        )
                    )
            except Exception as e:
                import logging

                logging.error(f"ICSCollector [{self._code}] URL {url} failed: {e}")
        return records

    @staticmethod
    def _extract_ref_period(desc: str) -> str | None:
        """Try to extract reference period from ICS DESCRIPTION field."""
        # Italian: "Periodo di riferimento: Novembre 2025"
        match = re.search(
            r"[Rr]eference period:?\s*(.+?)(?:\\n|,|$)", desc
        )
        if match:
            return match.group(1).strip()
        match = re.search(
            r"[Pp]eriodo di riferimento:?\s*(.+?)(?:\\n|,|$)", desc
        )
        if match:
            return match.group(1).strip()
        return None


# ============================================================
# Source-specific instances
# ============================================================

class IstatCollector(ICSCollector):
    """Istat (Italy) — Google Calendar ICS feeds."""

    FEED_URLS = [
        "https://www.google.com/calendar/ical/4s57ih6d08n330qrm9ee575nog%40group.calendar.google.com/public/basic.ics",
    ]

    def __init__(self):
        super().__init__(
            code="istat",
            feed_urls=self.FEED_URLS,
            default_tz="Europe/Rome",
            default_hour=10,
        )


class INECollector(ICSCollector):
    """INE (Spain) — direct ICS feed (large feed, slow server: needs a long timeout)."""

    FEED_URL = "https://www.ine.es/dynt3/Calendario/en/calendario.ics"

    def __init__(self):
        super().__init__(
            code="ine",
            feed_urls=[self.FEED_URL],
            default_tz="Europe/Madrid",
            default_hour=9,
            timeout=90,
        )


class EurostatCollector(ICSCollector):
    """
    Eurostat — ICS feed behind the "Subscribe to iCalendar" page
    (https://ec.europa.eu/eurostat/subscribe/ics.format). An empty theme
    parameter returns all themes.
    """

    FEED_URLS = [
        "https://ec.europa.eu/eurostat/o/calendars/eventsIcal?theme=",
    ]

    def __init__(self):
        super().__init__(
            code="eurostat",
            feed_urls=self.FEED_URLS,
            default_tz="Europe/Luxembourg",
            default_hour=11,
        )
