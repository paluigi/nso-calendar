"""CSO Ireland — PxStat RESTful API collector."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

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
        since = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
        url = f"{self.API_BASE}/PxStat.Data.Cube_API.ReadCollection/{since}/en"

        resp = requests.get(url, timeout=60, headers={"Accept": "application/json"})
        resp.raise_for_status()
        data = resp.json()
        items = data.get("link", {}).get("item", [])

        records: list[NSOReleaseRecord] = []
        seen: set[tuple[str, datetime]] = set()

        for item in items:
            # Items are per-dimension: title is in `label`, release timestamp
            # (ISO-8601, e.g. "2026-07-27T11:00:00Z") in `updated`.
            title = (item.get("label") or "").strip()
            updated = (item.get("updated") or "").strip()
            href = item.get("href") or ""

            if not title or not updated:
                continue

            dt = datetime.fromisoformat(updated.replace("Z", "+00:00")).astimezone(timezone.utc)

            key = (title, dt)
            if key in seen:
                continue
            seen.add(key)

            records.append(
                NSOReleaseRecord(
                    source_code="cso",
                    title=title,
                    release_dt=dt,
                    url=href if href.startswith("http") else None,
                )
            )

        logging.info(f"CSO: collected {len(records)} records")
        return records
