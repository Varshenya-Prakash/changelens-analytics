from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db
from app.models import ChangeEvent, ChangeEventCategory, Site, TrackedPage
from app.schemas.change_event import (
    CategoryMatchOut,
    ChangeEventDetailOut,
    ChangeEventListItem,
    ChangeEventStatusUpdate,
)
from app.schemas.common import Page

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _base_query(db: Session):
    return (
        db.query(ChangeEvent, TrackedPage, Site)
        .join(TrackedPage, ChangeEvent.tracked_page_id == TrackedPage.id)
        .join(Site, TrackedPage.site_id == Site.id)
    )


def _to_list_item(event: ChangeEvent, page: TrackedPage, site: Site) -> ChangeEventListItem:
    return ChangeEventListItem(
        id=event.id,
        tracked_page_id=event.tracked_page_id,
        detected_at=event.detected_at,
        status=event.status,
        primary_category=event.primary_category,
        signal_score=event.signal_score,
        signal_level=event.signal_level,
        is_cosmetic=event.is_cosmetic,
        diff_summary=event.diff_summary,
        recommendation=event.recommendation,
        organization_name=site.name,
        page_label=page.page_label,
        page_url=page.url,
    )


@router.get("", response_model=Page[ChangeEventListItem])
def list_alerts(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = None,
    site_id: int | None = None,
    signal_level: str | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: str | None = None,
    sort: str = Query("signal_score_desc", pattern="^(signal_score_desc|detected_at_desc)$"),
):
    query = _base_query(db)

    if category:
        query = query.filter(ChangeEvent.primary_category == category)
    if site_id:
        query = query.filter(Site.id == site_id)
    if signal_level:
        query = query.filter(ChangeEvent.signal_level == signal_level)
    if status:
        query = query.filter(ChangeEvent.status == status)
    if date_from:
        query = query.filter(ChangeEvent.detected_at >= date_from)
    if date_to:
        query = query.filter(ChangeEvent.detected_at <= date_to)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Site.name.ilike(like),
                TrackedPage.url.ilike(like),
                ChangeEvent.diff_summary.ilike(like),
                ChangeEvent.added_text.ilike(like),
                ChangeEvent.removed_text.ilike(like),
            )
        )

    total = query.count()

    if sort == "signal_score_desc":
        query = query.order_by(ChangeEvent.signal_score.desc(), ChangeEvent.detected_at.desc())
    else:
        query = query.order_by(ChangeEvent.detected_at.desc())

    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    items = [_to_list_item(e, p, s) for e, p, s in rows]

    total_pages = max(1, (total + page_size - 1) // page_size)
    return Page(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)


@router.get("/{alert_id}", response_model=ChangeEventDetailOut)
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    row = (
        _base_query(db)
        .options(joinedload(ChangeEvent.category_links).joinedload(ChangeEventCategory.category))
        .filter(ChangeEvent.id == alert_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    event, page, site = row

    category_matches = [
        CategoryMatchOut(
            name=link.category.name, confidence=link.confidence, matched_terms=link.matched_terms
        )
        for link in event.category_links
    ]

    return ChangeEventDetailOut(
        id=event.id,
        tracked_page_id=event.tracked_page_id,
        detected_at=event.detected_at,
        status=event.status,
        primary_category=event.primary_category,
        signal_score=event.signal_score,
        signal_level=event.signal_level,
        is_cosmetic=event.is_cosmetic,
        diff_summary=event.diff_summary,
        recommendation=event.recommendation,
        organization_name=site.name,
        page_label=page.page_label,
        page_url=page.url,
        change_magnitude=event.change_magnitude,
        similarity_score=event.similarity_score,
        added_text=event.added_text,
        removed_text=event.removed_text,
        scoring_explanation=event.scoring_explanation,
        category_matches=category_matches,
        source_url=page.url,
    )


@router.patch("/{alert_id}/status", response_model=ChangeEventListItem)
def update_alert_status(
    alert_id: int, payload: ChangeEventStatusUpdate, db: Session = Depends(get_db)
):
    row = _base_query(db).filter(ChangeEvent.id == alert_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    event, page, site = row
    event.status = payload.status
    db.commit()
    db.refresh(event)
    return _to_list_item(event, page, site)
