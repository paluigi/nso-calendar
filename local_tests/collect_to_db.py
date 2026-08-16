"""Run all NSO collectors and upsert results into the local database.

Uses DATABASE_URL from .env (default: postgresql+asyncpg://nso:nso_dev@localhost:5432/nso_calendar).
Requires the compose db service to be running.

Usage (from repo root):
    .venv/bin/python local_tests/collect_to_db.py
"""
from __future__ import annotations

import asyncio
import logging

from app.collectors.ics_collector import EurostatCollector, IstatCollector, INECollector
from app.collectors.destatis_collector import DestatisCollector
from app.collectors.insee_collector import INSEECollector
from app.collectors.cso_collector import CSOCollector
from app.database import async_session
from app.db_ops import upsert_nso_releases

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

COLLECTORS = [
    EurostatCollector,
    IstatCollector,
    INECollector,
    DestatisCollector,
    INSEECollector,
    CSOCollector,
]


async def main() -> None:
    for cls in COLLECTORS:
        collector = cls()
        try:
            records = collector.collect()
            async with async_session() as session:
                count = await upsert_nso_releases(session, records)
            print(f"{cls.__name__}: {len(records)} collected, {count} upserted")
        except Exception as e:
            print(f"{cls.__name__} FAILED: {e}")


if __name__ == "__main__":
    asyncio.run(main())
