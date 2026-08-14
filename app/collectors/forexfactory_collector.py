"""ForexFactory — Monthly calendar HTML scraper (EUR events only)."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from app.models import FFReleaseRecord


IMPACT_MAP = {
    "icon--ff-impact-red": "high",
    "icon--ff-impact-ora": "medium",
    "icon--ff-impact-yel": "low",
}
ET = ZoneInfo("America/New_York")
MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


class ForexFactoryCollector:
    """
    Scrapes ForexFactory monthly calendar pages.
    Backfill from June 2026; routine scrape covers (current month - 1) to (current month + 3).
    EUR events only.
    """

    BASE_URL = "https://www.forexfactory.com/calendar"
    BACKFILL_START = (2026, 6)    # June 2026
    LOOKBACK_MONTHS = 1
    LOOKAHEAD_MONTHS = 3

    def collect_initial_backfill(self) -> list[FFReleaseRecord]:
        """One-time: scrape from June 2026 to current month."""
        now = datetime.now(timezone.utc)
        months = self._month_range(
            self.BACKFILL_START[0], self.BACKFILL_START[1],
            now.year, now.month,
        )
        return self._scrape_months(months)

    def collect_routine(self) -> list[FFReleaseRecord]:
        """Weekly: scrape (current - 1) to (current + 3) months."""
        now = datetime.now(timezone.utc)
        start_y, start_m = self._shift_month(now.year, now.month, -self.LOOKBACK_MONTHS)
        end_y, end_m = self._shift_month(now.year, now.month, self.LOOKAHEAD_MONTHS)
        months = self._month_range(start_y, start_m, end_y, end_m)
        return self._scrape_months(months)

    def collect_month(self, year: int, month: int) -> list[FFReleaseRecord]:
        """Scrape a single month — useful for testing or manual backfill."""
        return self._scrape_months([(year, month)])

    # ── Internal methods ──────────────────────────────────

    def _scrape_months(self, months: list[tuple[int, int]]) -> list[FFReleaseRecord]:
        all_records: list[FFReleaseRecord] = []
        for year, month in months:
            month_name = datetime(year, month, 1).strftime("%b").lower()
            url = f"{self.BASE_URL}?month={month_name}.{year}"
            try:
                records = self._scrape_page(url, year)
                all_records.extend(records)
                logging.info(f"ForexFactory {month_name}.{year}: {len(records)} EUR events")
            except Exception as e:
                logging.error(f"ForexFactory scrape failed for {month_name}.{year}: {e}")
        return all_records

    def _scrape_page(self, url: str, year: int) -> list[FFReleaseRecord]:
        resp = requests.get(url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        })
        soup = BeautifulSoup(resp.text, "html.parser")
        records: list[FFReleaseRecord] = []
        current_date_str: str | None = None

        for row in soup.select("table.calendar__table tr"):
            # Track current date from header rows
            date_cell = row.select_one("td.calendar__date")
            if date_cell:
                match = re.search(r"([A-Z][a-z]{2}\s+\d+)", date_cell.get_text(strip=True))
                if match:
                    current_date_str = match.group(1).strip()

            # Only EUR events
            currency_cell = row.select_one("td.calendar__currency")
            event_cell = row.select_one("td.calendar__event")
            if not currency_cell or not event_cell:
                continue

            currency = currency_cell.get_text(strip=True)
            title = event_cell.get_text(strip=True)
            if currency != "EUR" or not title:
                continue

            # Impact
            impact = "low"
            impact_cell = row.select_one("td.calendar__impact")
            if impact_cell:
                span = impact_cell.find("span", class_=re.compile(r"icon--ff-impact"))
                if span:
                    for cls in span.get("class") or []:
                        if cls in IMPACT_MAP:
                            impact = IMPACT_MAP[cls]
                            break

            # Time + values
            time_val = self._cell_text(row, "calendar__time")
            actual = self._cell_text(row, "calendar__actual")
            forecast = self._cell_text(row, "calendar__forecast")
            previous = self._cell_text(row, "calendar__previous")

            release_dt = self._parse_datetime(current_date_str, time_val, year)

            records.append(
                FFReleaseRecord(
                    title=title,
                    release_dt=release_dt,
                    impact=impact,
                    actual=actual or None,
                    forecast=forecast or None,
                    previous=previous or None,
                    release_dt_orig=time_val or None,
                )
            )
        return records

    @staticmethod
    def _cell_text(row, cls: str) -> str:
        cell = row.select_one(f"td.{cls}")
        return cell.get_text(strip=True) if cell else ""

    @staticmethod
    def _parse_datetime(date_str: str | None, time_str: str | None, year: int) -> datetime:
        """Parse 'Aug 14' + '8:00am' -> UTC datetime. ET = America/New_York."""
        match = re.search(r"([A-Z][a-z]{2})\s+(\d+)", date_str or "")
        if not match:
            return datetime.now(timezone.utc)
        month = MONTHS.get(match.group(1), 1)
        day = int(match.group(2))

        if not time_str or time_str in ("Tentative", "All Day", ""):
            return datetime(year, month, day, 0, 0, tzinfo=ET).astimezone(timezone.utc)

        tm = re.match(r"(\d+):(\d+)\s*(am|pm)", time_str, re.IGNORECASE)
        if tm:
            h = int(tm.group(1))
            if tm.group(3).lower() == "pm" and h != 12:
                h += 12
            elif tm.group(3).lower() == "am" and h == 12:
                h = 0
            return datetime(year, month, day, h, int(tm.group(2)), tzinfo=ET).astimezone(timezone.utc)

        return datetime(year, month, day, 0, 0, tzinfo=ET).astimezone(timezone.utc)

    @staticmethod
    def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
        total = (year * 12 + (month - 1)) + delta
        return total // 12, total % 12 + 1

    @staticmethod
    def _month_range(y1: int, m1: int, y2: int, m2: int) -> list[tuple[int, int]]:
        months: list[tuple[int, int]] = []
        y, m = y1, m1
        while (y, m) <= (y2, m2):
            months.append((y, m))
            y, m = ForexFactoryCollector._shift_month(y, m, 1)
        return months
