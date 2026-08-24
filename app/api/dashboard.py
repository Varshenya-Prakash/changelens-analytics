from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.dashboard import DashboardSummaryOut, DashboardTrendsOut
from app.services import analytics

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryOut)
def dashboard_summary(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    stats = analytics.get_summary(db, days=days)
    return stats


@router.get("/trends", response_model=DashboardTrendsOut)
def dashboard_trends(days: int = Query(90, ge=1, le=365), db: Session = Depends(get_db)):
    return DashboardTrendsOut(
        daily_change_trend=analytics.get_daily_trend(db, days=days),
        category_trend=analytics.get_category_breakdown_over_time(db, days=days),
        signal_trend=analytics.get_signal_vs_noise_trend(db, days=days),
        leaderboard=analytics.get_leaderboard(db, days=days),
    )
