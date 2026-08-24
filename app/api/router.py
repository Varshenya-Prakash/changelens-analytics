from fastapi import APIRouter

from app.api import alerts, dashboard, monitor, sites

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(dashboard.router)
api_router.include_router(alerts.router)
api_router.include_router(sites.router)
api_router.include_router(monitor.router)
