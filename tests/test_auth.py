from __future__ import annotations

from datetime import UTC

ADMIN_AUTH = ("test_admin", "test_password")
WRONG_AUTH = ("wrong_user", "wrong_password")


def test_settings_page_requires_auth(client, db_session):
    resp = client.get("/settings/sites")
    assert resp.status_code == 401


def test_settings_page_accessible_with_correct_auth(client, db_session):
    resp = client.get("/settings/sites", auth=ADMIN_AUTH)
    assert resp.status_code == 200


def test_settings_page_rejects_wrong_auth(client, db_session):
    resp = client.get("/settings/sites", auth=WRONG_AUTH)
    assert resp.status_code == 401


def test_create_site_api_requires_auth(client, db_session):
    resp = client.post(
        "/api/v1/sites",
        json={"name": "Acme Corp", "sector": "Consulting", "base_url": "https://example.com"},
    )
    assert resp.status_code == 401


def test_create_site_api_works_with_auth(client, db_session):
    resp = client.post(
        "/api/v1/sites",
        json={"name": "Acme Corp", "sector": "Consulting", "base_url": "https://example.com"},
        auth=ADMIN_AUTH,
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Acme Corp"


def test_monitor_run_api_requires_auth(client, db_session):
    resp = client.post("/api/v1/monitor/run")
    assert resp.status_code == 401


def test_monitor_run_api_works_with_auth(client, db_session):
    resp = client.post("/api/v1/monitor/run", auth=ADMIN_AUTH)
    assert resp.status_code == 200


def test_alert_status_update_remains_public(client, db_session):
    """Marking an alert reviewed/dismissed is a core interactive demo feature
    and is deliberately NOT behind auth, unlike site/page configuration."""
    from datetime import datetime

    from app.models import ChangeEvent, Site, Snapshot, TrackedPage

    site = Site(name="Acme", slug="acme", sector="Consulting", base_url="https://example.com")
    db_session.add(site)
    db_session.flush()
    page = TrackedPage(site_id=site.id, url="https://example.com/news", page_label="Newsroom")
    db_session.add(page)
    db_session.flush()
    snapshot = Snapshot(
        tracked_page_id=page.id,
        fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
        http_status=200,
        content_hash="h1",
        extracted_text="text",
    )
    db_session.add(snapshot)
    db_session.flush()
    event = ChangeEvent(
        tracked_page_id=page.id,
        current_snapshot_id=snapshot.id,
        status="new",
        diff_summary="test",
        primary_category="Other",
        signal_score=10.0,
        signal_level="low",
    )
    db_session.add(event)
    db_session.commit()

    resp = client.patch(f"/api/v1/alerts/{event.id}/status", json={"status": "reviewed"})
    assert resp.status_code == 200
