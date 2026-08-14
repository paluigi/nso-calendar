"""FastAPI application factory."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.api.routes import router


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: start scheduler. Shutdown: stop scheduler."""
    if settings.scheduler_enabled:
        from app.scheduler import start_scheduler, scheduler
        start_scheduler()
    yield
    if settings.scheduler_enabled:
        from app.scheduler import scheduler
        scheduler.shutdown(wait=False)


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

app.include_router(router)
