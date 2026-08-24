from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.pages.router import pages_router

configure_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler
    logger.info("ChangeLens Analytics starting up (env=%s)", settings.app_env)
    if settings.enable_scheduler:
        from app.services.scheduler import start_scheduler  # noqa: PLC0415

        _scheduler = start_scheduler()
        logger.info("APScheduler monitoring job started.")
    if not settings.enable_live_monitoring:
        logger.info(
            "Live monitoring is DISABLED (ENABLE_LIVE_MONITORING=false). "
            "Dashboard is running on seeded demo data only."
        )
    yield
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)


app = FastAPI(
    title="ChangeLens Analytics",
    description=(
        "A change-intelligence dashboard prototype: what changed on a competitor's site, "
        "how frequently, whether it matters, and what to do about it."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(api_router)
app.include_router(pages_router)
