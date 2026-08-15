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


async def _initial_nso_collection():
    """On first run (empty nso_releases), collect NSO data so a fresh
    deployment is not ForexFactory-only. Runs in the background — the
    weekly scheduler keeps it up to date afterwards."""
    from app.database import async_session
    from app.scheduler import collect_all_nso

    try:
        async with async_session() as session:
            count = (await session.execute(text("SELECT COUNT(*) FROM nso_releases"))).scalar()
        if count == 0:
            logging.info("nso_releases is empty — running initial NSO collection")
            await collect_all_nso()
            logging.info("Initial NSO collection finished")
        else:
            logging.info(f"nso_releases already populated ({count} rows) — skipping initial collection")
    except Exception as e:
        logging.error(f"Initial NSO collection failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: start scheduler (+ first-run NSO backfill). Shutdown: stop scheduler."""
    if settings.scheduler_enabled:
        from app.scheduler import start_scheduler, scheduler
        start_scheduler()
        asyncio.create_task(_initial_nso_collection())
    yield
    if settings.scheduler_enabled:
        from app.scheduler import scheduler
        scheduler.shutdown(wait=False)


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

app.include_router(router)
