"""APScheduler integration — weekly collection job at Monday 07:00 UTC."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.database import async_session
from app.db_ops import upsert_nso_releases, upsert_ff_releases
from app.collectors.ics_collector import EurostatCollector, IstatCollector, INECollector
from app.collectors.destatis_collector import DestatisCollector
from app.collectors.insee_collector import INSEECollector
from app.collectors.cso_collector import CSOCollector
from app.collectors.forexfactory_collector import ForexFactoryCollector


scheduler = AsyncIOScheduler()


async def collect_all_nso():
    """Run all NSO collectors sequentially and upsert results."""
    nso_collectors = [
        EurostatCollector(),
        IstatCollector(),
        INECollector(),
        DestatisCollector(),
        INSEECollector(),
        CSOCollector(),
    ]

    for collector in nso_collectors:
        try:
            records = collector.collect()
            async with async_session() as session:
                count = await upsert_nso_releases(session, records)
            logging.info(f"{collector.__class__.__name__}: {len(records)} collected, {count} upserted")
        except Exception as e:
            logging.error(f"{collector.__class__.__name__} failed: {e}")


async def collect_ff():
    """Run ForexFactory routine scrape and upsert results."""
    try:
        collector = ForexFactoryCollector()
        records = collector.collect_routine()
        async with async_session() as session:
            count = await upsert_ff_releases(session, records)
        logging.info(f"ForexFactory: {len(records)} collected, {count} upserted")
    except Exception as e:
        logging.error(f"ForexFactory failed: {e}")


async def weekly_collect_all():
    """Monday 07:00 UTC — all sources."""
    logging.info("=== Weekly collection started ===")
    await collect_all_nso()
    await collect_ff()
    logging.info("=== Weekly collection completed ===")


def start_scheduler():
    """Start the scheduler with the weekly job."""
    if not settings.scheduler_enabled:
        logging.info("Scheduler disabled via config")
        return

    scheduler.add_job(
        weekly_collect_all,
        CronTrigger(day_of_week="mon", hour=7, minute=0, timezone="UTC"),
        id="weekly_collect_all",
        replace_existing=True,
    )
    scheduler.start()
    logging.info("Scheduler started: weekly collection at Monday 07:00 UTC")
