from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.pages.router import pages_router
from app.pages.templating import templates

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
        "A data analytics platform: ingestion, diffing, classification, scoring, and "
        "visualization of website change-event data."
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


@app.exception_handler(StarletteHTTPException)
async def custom_404_handler(request: Request, exc: StarletteHTTPException):
    """Render the branded 404 page for any unmatched HTML route.

    JSON API routes (/api/*) and OpenAPI/docs routes keep their normal
    JSON/default error behavior -- only human-facing pages get the styled
    not-found page.
    """
    if exc.status_code == 404 and not request.url.path.startswith(
        ("/api/", "/docs", "/openapi.json", "/redoc")
    ):
        return templates.TemplateResponse(
            request,
            "not_found.html",
            {"message": "The page you're looking for doesn't exist or may have moved."},
            status_code=404,
        )
    from fastapi.exception_handlers import http_exception_handler  # noqa: PLC0415

    return await http_exception_handler(request, exc)
