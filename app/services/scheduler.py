"""Optional APScheduler-based background monitoring job.

Only started when `ENABLE_SCHEDULER=true`. Even then, each run defers to
`ENABLE_LIVE_MONITORING`: with live monitoring off the job runs harmlessly
and no-ops (the fetcher itself refuses to hit the network), so enabling the
scheduler alone is always safe.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import get_settings
from app.db.session import session_scope
from app.services.monitoring import run_monitoring

logger = logging.getLogger(__name__)


def _scheduled_job() -> None:
    settings = get_settings()
    if not settings.enable_live_monitoring:
        logger.debug("Scheduler tick skipped: ENABLE_LIVE_MONITORING is false.")
        return
    with session_scope() as db:
        run = run_monitoring(db)
        logger.info(
            "Scheduled monitoring run %s completed: %s succeeded, %s failed",
            run.id,
            run.pages_succeeded,
            run.pages_failed,
        )


def start_scheduler(interval_minutes: int = 60) -> BackgroundScheduler:
    """Create and start a background scheduler that periodically runs monitoring."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _scheduled_job,
        "interval",
        minutes=interval_minutes,
        id="sitetracker-monitoring",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    return scheduler
