"""Destatis (Germany) — Annual release calendar via 13 topic facets."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from app.collectors.base import BaseNSOCollector
from app.models import NSOReleaseRecord


class DestatisCollector(BaseNSOCollector):
    """
    Scrapes the Destatis annual release calendar by iterating all 13 topic facets.
    Returns full-year schedule (confirmed Aug 2026 -> Jun 2027, 76 unique releases).
    """

    SEARCH_URL = "https://www.destatis.de/SiteGlobals/Forms/Suche/Termine/EN/Terminsuche_Formular.html"
    PUBLISH_TZ = ZoneInfo("Europe/Berlin")

    TOPICS = {
        "preise": "Prices",
        "industrie_verarbeitendes_gewerbe": "Industry, Manufacturing",
        "bauen": "Construction",
        "unternehmen": "Enterprises",
        "arbeitsmarkt": "Labour market",
        "aussenhandel": "Foreign Trade",
        "gross_einzelhandel": "Wholesale trade, retail trade",
        "verdienste": "Earnings",
        "dienstleistungen": "Services",
        "volkswirtschaftliche_gesamtrechnungen_inlandsprodukt": "National accounts, domestic product",
        "arbeits_lohnnebenkosten": "Labour costs, non-wage costs",
        "bevoelkerung": "Population",
        "verkehrsunfaelle": "Traffic accidents",
    }

    def source_code(self) -> str:
        return "destatis"

    def collect(self) -> list[NSOReleaseRecord]:
        all_records: list[NSOReleaseRecord] = []
        seen: set[tuple[str, datetime]] = set()

        for topic_key in self.TOPICS:
            try:
                records = self._fetch_topic(topic_key)
                for r in records:
                    key = (r.title, r.release_dt)
                    if key not in seen:
                        seen.add(key)
                        all_records.append(r)
            except Exception as e:
                logging.error(f"Destatis topic '{topic_key}' failed: {e}")

        return all_records

    def _fetch_topic(self, topic_key: str) -> list[NSOReleaseRecord]:
        params = {"submit": "x", "cl2Taxonomies_Themen_0": topic_key}
        resp = requests.get(
            self.SEARCH_URL,
            params=params,
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        records: list[NSOReleaseRecord] = []

        for result in soup.select("div.c-result--event-preview"):
            heading = result.select_one(".c-result__heading")
            title = heading.get_text(strip=True).rstrip("0123456789") if heading else ""
            if not title:
                continue

            metas = result.select(".c-result-meta__item")
            ref_period = ""
            issue_date_str = ""
            for m in metas:
                text = m.get_text(strip=True).replace("ICS/iCal", "").strip()
                if "Reporting period" in text:
                    ref_period = text.replace("Reporting period:", "").strip()
                elif "Date of issue" in text:
                    issue_date_str = text.replace("Date of issue:", "").strip()

            dt = self._parse_date(issue_date_str)

            records.append(
                NSOReleaseRecord(
                    source_code="destatis",
                    title=title,
                    release_dt=dt,
                    reference_period=ref_period or None,
                )
            )
        return records

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        """Parse '2026.08.14' or '2026.08.14 (deadline)' -> datetime at 08:00 CET."""
        match = re.search(r"(\d{4})\.(\d{2})\.(\d{2})", date_str)
        if not match:
            raise ValueError(f"Cannot parse Destatis date: {date_str}")
        y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
        return datetime(y, m, d, 8, 0, tzinfo=DestatisCollector.PUBLISH_TZ).astimezone(timezone.utc)
