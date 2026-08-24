from __future__ import annotations

from datetime import UTC, datetime

from app.models import ChangeEvent, Site, Snapshot, TrackedPage


def _seed_alerts(db_session, count: int = 25):
    site = Site(
        name="Acme Corp", slug="acme-corp", sector="Consulting", base_url="https://example.com"
    )
    db_session.add(site)
    db_session.flush()
    page = TrackedPage(site_id=site.id, url="https://example.com/news", page_label="Newsroom")
    db_session.add(page)
    db_session.flush()

    events = []
    for i in range(count):
        snapshot = Snapshot(
            tracked_page_id=page.id,
            fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
            http_status=200,
            content_hash=f"hash-{i}",
            extracted_text=f"content {i}",
        )
        db_session.add(snapshot)
        db_session.flush()

        category = "Pricing / Commercial" if i % 2 == 0 else "Hiring / Careers"
        level = "high" if i % 3 == 0 else "low"
        event = ChangeEvent(
            tracked_page_id=page.id,
            current_snapshot_id=snapshot.id,
            status="new",
            change_magnitude=0.2,
            similarity_score=0.8,
            diff_summary=f"Change number {i}",
            primary_category=category,
            signal_score=70.0 if level == "high" else 20.0,
            signal_level=level,
        )
        db_session.add(event)
        events.append(event)
    db_session.commit()
    return site, page, events


def test_list_alerts_default_pagination(client, db_session):
    _seed_alerts(db_session, count=25)
    resp = client.get("/api/v1/alerts")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 25
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert len(body["items"]) == 20
    assert body["total_pages"] == 2


def test_list_alerts_second_page(client, db_session):
    _seed_alerts(db_session, count=25)
    resp = client.get("/api/v1/alerts", params={"page": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 5


def test_list_alerts_filter_by_category(client, db_session):
    _seed_alerts(db_session, count=10)
    resp = client.get("/api/v1/alerts", params={"category": "Pricing / Commercial"})
    assert resp.status_code == 200
    body = resp.json()
    assert all(item["primary_category"] == "Pricing / Commercial" for item in body["items"])


def test_list_alerts_filter_by_signal_level(client, db_session):
    _seed_alerts(db_session, count=10)
    resp = client.get("/api/v1/alerts", params={"signal_level": "high"})
    assert resp.status_code == 200
    body = resp.json()
    assert all(item["signal_level"] == "high" for item in body["items"])


def test_get_alert_detail(client, db_session):
    _site, _page, events = _seed_alerts(db_session, count=3)
    resp = client.get(f"/api/v1/alerts/{events[0].id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == events[0].id
    assert "scoring_explanation" in body


def test_get_alert_detail_404(client, db_session):
    resp = client.get("/api/v1/alerts/99999")
    assert resp.status_code == 404


def test_update_alert_status(client, db_session):
    _site, _page, events = _seed_alerts(db_session, count=3)
    event_id = events[0].id

    resp = client.patch(f"/api/v1/alerts/{event_id}/status", json={"status": "reviewed"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "reviewed"

    # Verify persisted.
    resp2 = client.get(f"/api/v1/alerts/{event_id}")
    assert resp2.json()["status"] == "reviewed"


def test_update_alert_status_rejects_invalid_value(client, db_session):
    _site, _page, events = _seed_alerts(db_session, count=1)
    resp = client.patch(
        f"/api/v1/alerts/{events[0].id}/status", json={"status": "not-a-real-status"}
    )
    assert resp.status_code == 422


def test_dashboard_summary_endpoint(client, db_session):
    _seed_alerts(db_session, count=5)
    resp = client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert "changes_last_30_days" in body
    assert "signal_to_noise_ratio" in body
