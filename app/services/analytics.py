"""Aggregate analytics queries backing the dashboard and API.

Kept separate from the API layer so the same logic can be reused by the
CLI (e.g. for the action-plan report) and unit tested independently of
FastAPI.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import ChangeEvent, Site, TrackedPage


@dataclass
class SummaryStats:
    changes_last_30_days: int
    high_signal_changes: int
    signal_to_noise_ratio: float
    most_active_organization: str | None
    total_sites: int
    total_tracked_pages: int


def get_summary(db: Session, days: int = 30) -> SummaryStats:
    cutoff = datetime.now(UTC) - timedelta(days=days)

    recent_events = db.query(ChangeEvent).filter(ChangeEvent.detected_at >= cutoff).all()
    total = len(recent_events)
    high_signal = sum(1 for e in recent_events if e.signal_level in ("high", "critical"))
    noise = sum(1 for e in recent_events if e.signal_level == "noise")
    signal = total - noise
    ratio = round(signal / noise, 2) if noise > 0 else float(signal) if signal else 0.0

    most_active_row = (
        db.query(Site.name, func.count(ChangeEvent.id).label("cnt"))
        .join(TrackedPage, TrackedPage.site_id == Site.id)
        .join(ChangeEvent, ChangeEvent.tracked_page_id == TrackedPage.id)
        .filter(ChangeEvent.detected_at >= cutoff)
        .group_by(Site.name)
        .order_by(func.count(ChangeEvent.id).desc())
        .first()
    )

    return SummaryStats(
        changes_last_30_days=total,
        high_signal_changes=high_signal,
        signal_to_noise_ratio=ratio,
        most_active_organization=most_active_row[0] if most_active_row else None,
        total_sites=db.query(func.count(Site.id)).scalar() or 0,
        total_tracked_pages=db.query(func.count(TrackedPage.id)).scalar() or 0,
    )


def get_daily_trend(db: Session, days: int = 90) -> list[dict]:
    """Change frequency by day for the last N days."""
    cutoff = datetime.now(UTC) - timedelta(days=days)
    rows = (
        db.query(
            func.date(ChangeEvent.detected_at).label("day"),
            func.count(ChangeEvent.id).label("count"),
        )
        .filter(ChangeEvent.detected_at >= cutoff)
        .group_by("day")
        .order_by("day")
        .all()
    )
    return [{"date": str(r.day), "count": r.count} for r in rows]


def get_category_breakdown_over_time(db: Session, days: int = 90) -> list[dict]:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    rows = (
        db.query(
            func.date(ChangeEvent.detected_at).label("day"),
            ChangeEvent.primary_category,
            func.count(ChangeEvent.id).label("count"),
        )
        .filter(ChangeEvent.detected_at >= cutoff)
        .group_by("day", ChangeEvent.primary_category)
        .order_by("day")
        .all()
    )
    return [{"date": str(r.day), "category": r.primary_category, "count": r.count} for r in rows]


def get_signal_vs_noise_trend(db: Session, days: int = 90) -> list[dict]:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    rows = (
        db.query(
            func.date(ChangeEvent.detected_at).label("day"),
            ChangeEvent.signal_level,
            func.count(ChangeEvent.id).label("count"),
        )
        .filter(ChangeEvent.detected_at >= cutoff)
        .group_by("day", ChangeEvent.signal_level)
        .order_by("day")
        .all()
    )
    return [{"date": str(r.day), "signal_level": r.signal_level, "count": r.count} for r in rows]


def get_leaderboard(db: Session, days: int = 90, limit: int = 10) -> list[dict]:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    rows = (
        db.query(
            Site.id,
            Site.name,
            Site.slug,
            Site.sector,
            func.count(ChangeEvent.id).label("change_count"),
            func.avg(ChangeEvent.signal_score).label("avg_score"),
        )
        .join(TrackedPage, TrackedPage.site_id == Site.id)
        .join(ChangeEvent, ChangeEvent.tracked_page_id == TrackedPage.id)
        .filter(ChangeEvent.detected_at >= cutoff)
        .group_by(Site.id, Site.name, Site.slug, Site.sector)
        .order_by(func.count(ChangeEvent.id).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "site_id": r.id,
            "name": r.name,
            "slug": r.slug,
            "sector": r.sector,
            "change_count": r.change_count,
            "avg_signal_score": round(r.avg_score, 1) if r.avg_score else 0.0,
        }
        for r in rows
    ]


def get_recent_high_priority(db: Session, limit: int = 8) -> list[ChangeEvent]:
    return (
        db.query(ChangeEvent)
        .filter(ChangeEvent.signal_level.in_(["high", "critical"]))
        .order_by(ChangeEvent.detected_at.desc())
        .limit(limit)
        .all()
    )


def get_category_totals(db: Session, days: int = 90) -> list[dict]:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    rows = (
        db.query(ChangeEvent.primary_category, func.count(ChangeEvent.id).label("count"))
        .filter(ChangeEvent.detected_at >= cutoff)
        .group_by(ChangeEvent.primary_category)
        .order_by(func.count(ChangeEvent.id).desc())
        .all()
    )
    return [{"category": r.primary_category, "count": r.count} for r in rows]


def get_magnitude_vs_score(db: Session, days: int = 90, limit: int = 500) -> list[dict]:
    """Per-event (change_magnitude, signal_score) pairs for a scatter plot.

    Lets a viewer visually separate "big rewrite, low relevance" (cosmetic
    noise) from "small but pointed edit, high relevance" (e.g. a one-line
    pricing change) -- magnitude and signal score are deliberately not the
    same axis in this model.
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)
    rows = (
        db.query(
            ChangeEvent.change_magnitude,
            ChangeEvent.signal_score,
            ChangeEvent.primary_category,
            ChangeEvent.signal_level,
        )
        .filter(ChangeEvent.detected_at >= cutoff)
        .order_by(ChangeEvent.detected_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "magnitude": round(r.change_magnitude * 100, 1),
            "score": r.signal_score,
            "category": r.primary_category,
            "signal_level": r.signal_level,
        }
        for r in rows
    ]


def get_meaningful_change_pct(db: Session, days: int = 90) -> float:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    total = (
        db.query(func.count(ChangeEvent.id)).filter(ChangeEvent.detected_at >= cutoff).scalar() or 0
    )
    if total == 0:
        return 0.0
    meaningful = (
        db.query(func.count(ChangeEvent.id))
        .filter(ChangeEvent.detected_at >= cutoff, ChangeEvent.signal_level != "noise")
        .scalar()
        or 0
    )
    return round(100 * meaningful / total, 1)
