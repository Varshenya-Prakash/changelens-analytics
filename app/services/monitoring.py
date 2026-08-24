"""Monitoring pipeline orchestration.

Ties together fetch -> extract -> snapshot persistence -> diff -> classify
-> score -> ChangeEvent persistence. Designed to be called either for a
single TrackedPage (manual "check now") or across all active pages (a
scheduled/manual monitoring run).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import RAW_SNAPSHOTS_DIR, get_settings
from app.models import (
    ChangeCategory,
    ChangeEvent,
    ChangeEventCategory,
    MonitoringRun,
    Snapshot,
    TrackedPage,
)
from app.services import fetcher
from app.services.classifier import classify_change
from app.services.diff_engine import compute_diff
from app.services.extractor import compute_content_hash, extract_title_and_text
from app.services.scoring import recommendation_for, score_change

logger = logging.getLogger(__name__)


def _save_raw_html(tracked_page_id: int, html: str) -> str | None:
    if not html:
        return None
    RAW_SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
    path = RAW_SNAPSHOTS_DIR / f"page_{tracked_page_id}_{ts}.html"
    path.write_text(html, encoding="utf-8")
    return str(path)


def check_page(
    db: Session, page: TrackedPage
) -> tuple[Snapshot | None, ChangeEvent | None, str | None]:
    """Run the full pipeline for a single tracked page.

    Returns (snapshot, change_event_or_None, error_or_None). A snapshot is
    still returned for failed fetches so failures are auditable.
    """
    settings = get_settings()
    result = fetcher.fetch(page.url, crawl_method=page.crawl_method)

    if result.error and result.html is None:
        snapshot = Snapshot(
            tracked_page_id=page.id,
            http_status=result.status_code,
            content_hash="",
            extracted_text="",
            fetch_duration_ms=result.duration_ms,
            error_message=result.error,
        )
        db.add(snapshot)
        page.last_checked_at = datetime.now(UTC)
        db.flush()
        return snapshot, None, result.error

    title, text = extract_title_and_text(result.html or "")
    content_hash = compute_content_hash(text)

    previous = (
        db.query(Snapshot)
        .filter(Snapshot.tracked_page_id == page.id, Snapshot.error_message.is_(None))
        .order_by(Snapshot.fetched_at.desc())
        .first()
    )

    is_duplicate = previous is not None and previous.content_hash == content_hash
    if is_duplicate and not settings.store_duplicate_snapshots:
        page.last_checked_at = datetime.now(UTC)
        db.flush()
        return previous, None, None

    raw_path = _save_raw_html(page.id, result.html or "")
    snapshot = Snapshot(
        tracked_page_id=page.id,
        http_status=result.status_code,
        content_hash=content_hash,
        raw_html_path=raw_path,
        extracted_text=text,
        title=title,
        fetch_duration_ms=result.duration_ms,
        snapshot_metadata={"crawl_method": page.crawl_method},
    )
    db.add(snapshot)
    page.last_checked_at = datetime.now(UTC)
    db.flush()

    change_event = None
    if previous is not None and not is_duplicate:
        change_event = build_change_event(db, page, previous, snapshot)

    return snapshot, change_event, None


def build_change_event(
    db: Session, page: TrackedPage, previous: Snapshot, current: Snapshot
) -> ChangeEvent:
    """Run diff -> classify -> score and persist a ChangeEvent + category links."""
    diff = compute_diff(previous.extracted_text, current.extracted_text)
    primary_category, matches, is_cosmetic = classify_change(diff.added_text, diff.removed_text)
    scoring = score_change(
        change_magnitude=diff.change_magnitude,
        primary_category=primary_category,
        is_cosmetic=is_cosmetic,
    )
    recommendation = recommendation_for(primary_category, scoring.signal_level)

    event = ChangeEvent(
        tracked_page_id=page.id,
        previous_snapshot_id=previous.id,
        current_snapshot_id=current.id,
        status="new",
        change_magnitude=diff.change_magnitude,
        similarity_score=diff.similarity_score,
        added_text=diff.added_text,
        removed_text=diff.removed_text,
        diff_summary=diff.diff_summary,
        primary_category=primary_category,
        signal_score=scoring.signal_score,
        signal_level=scoring.signal_level,
        is_cosmetic=is_cosmetic,
        scoring_explanation=scoring.explanation,
        recommendation=recommendation,
    )
    db.add(event)
    db.flush()

    for match in matches:
        category = db.query(ChangeCategory).filter(ChangeCategory.name == match.name).first()
        if category is None:
            category = ChangeCategory(name=match.name, description="", default_weight=1.0)
            db.add(category)
            db.flush()
        db.add(
            ChangeEventCategory(
                change_event_id=event.id,
                category_id=category.id,
                confidence=match.confidence,
                matched_terms=match.matched_terms,
            )
        )

    db.flush()
    return event


def run_monitoring(db: Session, page_id: int | None = None) -> MonitoringRun:
    """Run the monitoring pipeline across all active pages, or a single page."""
    query = db.query(TrackedPage).filter(TrackedPage.is_active.is_(True))
    if page_id is not None:
        query = query.filter(TrackedPage.id == page_id)
    pages = query.all()

    run = MonitoringRun(status="running", pages_attempted=len(pages))
    db.add(run)
    db.flush()

    succeeded = 0
    failed = 0
    notes = []

    for page in pages:
        try:
            _, _, error = check_page(db, page)
            if error:
                failed += 1
                notes.append(f"page {page.id} ({page.page_label}): {error}")
            else:
                succeeded += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            notes.append(f"page {page.id} ({page.page_label}): unexpected error: {exc}")
            logger.exception("Unexpected error monitoring page %s", page.id)

    run.completed_at = datetime.now(UTC)
    run.status = "completed" if failed == 0 else ("failed" if succeeded == 0 else "completed")
    run.pages_succeeded = succeeded
    run.pages_failed = failed
    run.notes = "\n".join(notes)
    db.commit()
    return run
