"""One-time ForexFactory backfill from June 2026 to current month."""
import asyncio
import logging

from app.database import async_session
from app.db_ops import upsert_ff_releases
from app.collectors.forexfactory_collector import ForexFactoryCollector


async def backfill_ff():
    logging.info("Starting ForexFactory backfill from June 2026...")
    collector = ForexFactoryCollector()
    records = collector.collect_initial_backfill()
    logging.info(f"Collected {len(records)} FF records from backfill")
    async with async_session() as session:
        count = await upsert_ff_releases(session, records)
    logging.info(f"Backfill complete: {count} records upserted to ff_releases")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    asyncio.run(backfill_ff())
