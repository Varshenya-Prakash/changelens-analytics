from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.auth import require_admin_auth
from app.models import TrackedPage
from app.services.monitoring import check_page, run_monitoring

router = APIRouter(tags=["monitoring"])


class MonitorRunOut(BaseModel):
    id: int
    status: str
    pages_attempted: int
    pages_succeeded: int
    pages_failed: int
    notes: str


class PageMonitorOut(BaseModel):
    tracked_page_id: int
    snapshot_id: int | None
    change_event_id: int | None
    error: str | None


@router.post("/pages/{page_id}/monitor", response_model=PageMonitorOut)
def monitor_single_page(
    page_id: int, db: Session = Depends(get_db), _user: str = Depends(require_admin_auth)
):
    page = db.query(TrackedPage).filter(TrackedPage.id == page_id).first()
    if page is None:
        raise HTTPException(status_code=404, detail=f"Tracked page {page_id} not found")
    snapshot, change_event, error = check_page(db, page)
    db.commit()
    return PageMonitorOut(
        tracked_page_id=page_id,
        snapshot_id=snapshot.id if snapshot else None,
        change_event_id=change_event.id if change_event else None,
        error=error,
    )


@router.post("/monitor/run", response_model=MonitorRunOut)
def trigger_monitor_run(
    page_id: int | None = None,
    db: Session = Depends(get_db),
    _user: str = Depends(require_admin_auth),
):
    run = run_monitoring(db, page_id=page_id)
    return MonitorRunOut(
        id=run.id,
        status=run.status,
        pages_attempted=run.pages_attempted,
        pages_succeeded=run.pages_succeeded,
        pages_failed=run.pages_failed,
        notes=run.notes,
    )
