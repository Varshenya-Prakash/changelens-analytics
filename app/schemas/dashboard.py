from __future__ import annotations

from pydantic import BaseModel


class DashboardSummaryOut(BaseModel):
    changes_last_30_days: int
    high_signal_changes: int
    signal_to_noise_ratio: float
    most_active_organization: str | None
    total_sites: int
    total_tracked_pages: int


class TrendPointOut(BaseModel):
    date: str
    count: int


class CategoryTrendPointOut(BaseModel):
    date: str
    category: str
    count: int


class SignalTrendPointOut(BaseModel):
    date: str
    signal_level: str
    count: int


class LeaderboardEntryOut(BaseModel):
    site_id: int
    name: str
    slug: str
    sector: str
    change_count: int
    avg_signal_score: float


class DashboardTrendsOut(BaseModel):
    daily_change_trend: list[TrendPointOut]
    category_trend: list[CategoryTrendPointOut]
    signal_trend: list[SignalTrendPointOut]
    leaderboard: list[LeaderboardEntryOut]
