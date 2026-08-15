"""FastAPI application factory."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.config import settings
from app.api.routes import router


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


async def _initial_backfill():
    """On first run (empty tables), collect NSO and ForexFactory data so a
    fresh deployment is fully populated. Runs in the background — the
    weekly scheduler keeps data up to date afterwards."""
    from app.collectors.forexfactory_collector import ForexFactoryCollector
    from app.database import async_session
    from app.db_ops import upsert_ff_releases
    from app.scheduler import collect_all_nso

    try:
        async with async_session() as session:
            nso_count = (await session.execute(text("SELECT COUNT(*) FROM nso_releases"))).scalar()
            ff_count = (await session.execute(text("SELECT COUNT(*) FROM ff_releases"))).scalar()

        if nso_count == 0:
            logging.info("nso_releases is empty — running initial NSO collection")
            await collect_all_nso()
        else:
            logging.info(f"nso_releases already populated ({nso_count} rows) — skipping NSO backfill")

        if ff_count == 0:
            logging.info("ff_releases is empty — running ForexFactory backfill")
            records = ForexFactoryCollector().collect_initial_backfill()
            async with async_session() as session:
                count = await upsert_ff_releases(session, records)
            logging.info(f"ForexFactory backfill finished: {count} records upserted")
        else:
            logging.info(f"ff_releases already populated ({ff_count} rows) — skipping FF backfill")
    except Exception as e:
        logging.error(f"Initial backfill failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: start scheduler (+ first-run backfill). Shutdown: stop scheduler."""
    if settings.scheduler_enabled:
        from app.scheduler import start_scheduler, scheduler
        start_scheduler()
        asyncio.create_task(_initial_backfill())
    yield
    if settings.scheduler_enabled:
        from app.scheduler import scheduler
        scheduler.shutdown(wait=False)


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

app.include_router(router)
