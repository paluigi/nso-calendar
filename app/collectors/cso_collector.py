"""CSO Ireland — PxStat RESTful API collector."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

import requests

from app.collectors.base import BaseNSOCollector
from app.models import NSOReleaseRecord


class CSOCollector(BaseNSOCollector):
    """
    Queries CSO PxStat RESTful API for release collection.
    Returns past releases since a given date (JSON-stat/collection format).

    Note: This API returns *past* releases. For forward-looking CSO schedule,
    the cso.ie release calendar page (JS-rendered) would need Playwright.
    """

    API_BASE = "https://ws.cso.ie/public/api.restful"

    def source_code(self) -> str:
        return "cso"

    def collect(self) -> list[NSOReleaseRecord]:
        # Query releases from the last 30 days
        from datetime import timedelta
        since = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
        url = f"{self.API_BASE}/PxStat.Data.Cube_API.ReadCollection/{since}/en"

        resp = requests.get(url, timeout=30, headers={"Accept": "application/json"})
        data = resp.json()
        items = data.get("link", {}).get("item", [])

        records: list[NSOReleaseRecord] = []
        for item in items:
            # Each item has: href (API link), extension/title info
            title = item.get("title", "")
            href = item.get("href", "")

            if not title:
                continue

            # Extract date from the href or metadata
            # PxStat href format: .../ReadDataset/CODE/JSON-stat/2.0/en
            # The release date is typically in the item metadata
            dt = datetime.now(timezone.utc)  # fallback

            records.append(
                NSOReleaseRecord(
                    source_code="cso",
                    title=title,
                    release_dt=dt,
                    url=href if href.startswith("http") else f"https://data.cso.ie/{href}" if href else None,
                )
            )

        logging.info(f"CSO: collected {len(records)} records")
        return records
