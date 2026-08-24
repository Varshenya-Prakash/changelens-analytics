from __future__ import annotations

from datetime import UTC, datetime

from app.models import ChangeEvent, Site, Snapshot, TrackedPage
from app.services.extractor import compute_content_hash
from app.services.monitoring import build_change_event


def _make_site_and_page(db_session):
    site = Site(
        name="Acme Corp", slug="acme-corp", sector="Consulting", base_url="https://example.com"
    )
    db_session.add(site)
    db_session.flush()
    page = TrackedPage(site_id=site.id, url="https://example.com/news", page_label="Newsroom")
    db_session.add(page)
    db_session.flush()
    return site, page


def test_duplicate_content_hash_is_detected(db_session):
    """Two snapshots with identical comparable text should hash identically,
    which is what the monitoring pipeline uses to skip persisting duplicates."""
    text = "Welcome to our newsroom. Nothing has changed here."
    hash_a = compute_content_hash(text)
    hash_b = compute_content_hash(text)
    assert hash_a == hash_b


def test_end_to_end_fixture_pipeline_creates_change_event(db_session):
    """fixture snapshots -> diff -> classify -> score -> ChangeEvent, using the
    same build_change_event() function the live monitoring pipeline calls."""
    site, page = _make_site_and_page(db_session)

    old_text = "Welcome to our newsroom. Stay up to date with company news."
    new_text = old_text + "\nWe are excited to announce a new Series B funding round of $40M."

    previous = Snapshot(
        tracked_page_id=page.id,
        fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
        http_status=200,
        content_hash=compute_content_hash(old_text),
        extracted_text=old_text,
        title="Acme Corp — Newsroom",
    )
    db_session.add(previous)
    db_session.flush()

    current = Snapshot(
        tracked_page_id=page.id,
        fetched_at=datetime(2026, 1, 2, tzinfo=UTC),
        http_status=200,
        content_hash=compute_content_hash(new_text),
        extracted_text=new_text,
        title="Acme Corp — Newsroom",
    )
    db_session.add(current)
    db_session.flush()

    event = build_change_event(db_session, page, previous, current)
    db_session.commit()

    assert event.id is not None
    assert event.primary_category == "Funding / Financial Event"
    assert "Series B" in event.added_text
    assert event.signal_score > 0
    assert event.signal_level in ("low", "medium", "high", "critical")
    assert event.status == "new"
    assert len(event.category_links) >= 1

    stored = db_session.query(ChangeEvent).filter(ChangeEvent.id == event.id).first()
    assert stored is not None
    assert stored.tracked_page_id == page.id


def test_no_op_change_produces_no_meaningful_diff(db_session):
    """Identical text before/after should yield a change event with zero
    magnitude and full similarity -- i.e. the pipeline doesn't fabricate signal."""
    site, page = _make_site_and_page(db_session)
    text = "Static content that never changes."

    previous = Snapshot(
        tracked_page_id=page.id,
        fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
        http_status=200,
        content_hash=compute_content_hash(text),
        extracted_text=text,
    )
    db_session.add(previous)
    db_session.flush()

    current = Snapshot(
        tracked_page_id=page.id,
        fetched_at=datetime(2026, 1, 2, tzinfo=UTC),
        http_status=200,
        content_hash=compute_content_hash(text),
        extracted_text=text,
    )
    db_session.add(current)
    db_session.flush()

    event = build_change_event(db_session, page, previous, current)
    assert event.change_magnitude == 0.0
    assert event.signal_level == "noise"
