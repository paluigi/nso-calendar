"""INSEE (France) — Rolling 2-week embargo calendar HTML scraper."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from app.collectors.base import BaseNSOCollector
from app.models import NSOReleaseRecord


class INSEECollector(BaseNSOCollector):
    """
    Scrapes INSEE embargo calendar (rolling 2-week schedule).
    URL: https://www.insee.fr/fr/information/5235017
    """

    CALENDAR_URL = "https://www.insee.fr/fr/information/5235017"
    TZ = ZoneInfo("Europe/Paris")

    # French month names -> month number
    MONTHS_FR = {
        "janvier": 1, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
        "juillet": 7, "août": 8, "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12,
    }

    def source_code(self) -> str:
        return "insee"

    def collect(self) -> list[NSOReleaseRecord]:
        resp = requests.get(
            self.CALENDAR_URL,
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        records: list[NSOReleaseRecord] = []

        # Parse the calendar tables: each week has a header "Semaine du DD au MM YYYY"
        # followed by rows with indicator name + "DD mois à HHhMM"
        # The page structure uses <table> elements with indicator rows
        current_year = datetime.now(timezone.utc).year

        # Find all tables that contain embargo data
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                if not cells:
                    continue

                # Extract text from all cells
                texts = [c.get_text(strip=True) for c in cells]
                combined = " ".join(texts)

                # Look for date patterns: "14 août à 8h45" or "DD mois à HHhMM"
                date_match = re.search(
                    r"(\d{1,2})\s+([a-zéûôà]+)\s+à\s+(\d+)h(\d{0,2})",
                    combined,
                    re.IGNORECASE,
                )
                if not date_match:
                    continue

                day = int(date_match.group(1))
                month_name = date_match.group(2).lower()
                hour = int(date_match.group(3))
                minute = int(date_match.group(4)) if date_match.group(4) else 0

                month = self.MONTHS_FR.get(month_name)
                if not month:
                    continue

                # Year: if month is in the past relative to now, it might be next year
                year = current_year
                if month < datetime.now(timezone.utc).month:
                    year += 1

                dt = datetime(year, month, day, hour, minute, tzinfo=self.TZ).astimezone(timezone.utc)

                # Title: first cell text (indicator name), stripping date/time portion
                title = texts[0] if texts else ""
                # Remove the date/time portion from title if present
                title = re.sub(r"\s*\d{1,2}\s+[a-zéûôà]+\s+à\s+.*$", "", title, flags=re.IGNORECASE).strip()
                # Also remove common prefixes
                title = re.sub(r"^INDICATEURS CONJONCTURELS\s*", "", title, flags=re.IGNORECASE).strip()

                if not title or len(title) < 5:
                    continue

                records.append(
                    NSOReleaseRecord(
                        source_code="insee",
                        title=title,
                        release_dt=dt,
                    )
                )

        logging.info(f"INSEE: collected {len(records)} records")
        return records
