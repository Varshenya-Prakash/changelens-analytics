"""Server-rendered dashboard pages (Jinja2 + HTMX/vanilla JS + Chart.js).

These routes render HTML for humans; the JSON API under /api/v1 (see
app/api/) is the machine-readable counterpart used by the same underlying
services.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db
from app.core.auth import require_admin_auth
from app.core.config import get_settings
from app.models import ChangeEvent, ChangeEventCategory, Site, TrackedPage
from app.pages.templating import templates
from app.services import analytics
from app.services.classifier import CATEGORY_KEYWORDS
from app.services.monitoring import check_page, run_monitoring
from app.services.scoring import CATEGORY_WEIGHTS

pages_router = APIRouter()

ALL_CATEGORIES = sorted(CATEGORY_KEYWORDS.keys())
SIGNAL_LEVELS = ["critical", "high", "medium", "low", "noise"]


@pages_router.get("/")
def overview(
    request: Request,
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
    organization: str | None = None,
    sector: str | None = None,
    category: str | None = None,
    signal_level: str | None = None,
):
    summary = analytics.get_summary(db, days=days)
    daily_trend = analytics.get_daily_trend(db, days=days)
    category_trend = analytics.get_category_breakdown_over_time(db, days=days)
    signal_trend = analytics.get_signal_vs_noise_trend(db, days=days)
    leaderboard = analytics.get_leaderboard(db, days=days)
    category_totals = analytics.get_category_totals(db, days=days)
    scatter_data = analytics.get_magnitude_vs_score(db, days=days)

    alerts_query = (
        db.query(ChangeEvent, TrackedPage, Site)
        .join(TrackedPage, ChangeEvent.tracked_page_id == TrackedPage.id)
        .join(Site, TrackedPage.site_id == Site.id)
        .filter(ChangeEvent.signal_level.in_(["high", "critical"]))
    )
    if organization:
        alerts_query = alerts_query.filter(Site.name == organization)
    if sector:
        alerts_query = alerts_query.filter(Site.sector == sector)
    if category:
        alerts_query = alerts_query.filter(ChangeEvent.primary_category == category)
    if signal_level:
        alerts_query = alerts_query.filter(ChangeEvent.signal_level == signal_level)

    recent_alerts = alerts_query.order_by(ChangeEvent.detected_at.desc()).limit(8).all()

    sectors = [row[0] for row in db.query(Site.sector).distinct().order_by(Site.sector).all()]
    organizations = [row[0] for row in db.query(Site.name).distinct().order_by(Site.name).all()]

    return templates.TemplateResponse(
        request,
        "overview.html",
        {
            "active_nav": "overview",
            "summary": summary,
            "daily_trend": daily_trend,
            "category_trend": category_trend,
            "signal_trend": signal_trend,
            "leaderboard": leaderboard,
            "category_totals": category_totals,
            "scatter_data": scatter_data,
            "recent_alerts": recent_alerts,
            "sectors": sectors,
            "organizations": organizations,
            "categories": ALL_CATEGORIES,
            "signal_levels": SIGNAL_LEVELS,
            "filters": {
                "days": days,
                "organization": organization or "",
                "sector": sector or "",
                "category": category or "",
                "signal_level": signal_level or "",
            },
        },
    )


@pages_router.get("/alerts")
def alert_feed(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    category: str | None = None,
    site_id: int | None = None,
    signal_level: str | None = None,
    status: str | None = None,
    search: str | None = None,
):
    page_size = 15
    query = (
        db.query(ChangeEvent, TrackedPage, Site)
        .join(TrackedPage, ChangeEvent.tracked_page_id == TrackedPage.id)
        .join(Site, TrackedPage.site_id == Site.id)
    )
    if category:
        query = query.filter(ChangeEvent.primary_category == category)
    if site_id:
        query = query.filter(Site.id == site_id)
    if signal_level:
        query = query.filter(ChangeEvent.signal_level == signal_level)
    if status:
        query = query.filter(ChangeEvent.status == status)
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
    query = query.order_by(ChangeEvent.signal_score.desc(), ChangeEvent.detected_at.desc())
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    total_pages = max(1, (total + page_size - 1) // page_size)

    sites = db.query(Site).order_by(Site.name).all()

    return templates.TemplateResponse(
        request,
        "alerts.html",
        {
            "active_nav": "alerts",
            "rows": rows,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "sites": sites,
            "categories": ALL_CATEGORIES,
            "signal_levels": SIGNAL_LEVELS,
            "filters": {
                "category": category or "",
                "site_id": site_id or "",
                "signal_level": signal_level or "",
                "status": status or "",
                "search": search or "",
            },
        },
    )


@pages_router.get("/alerts/{alert_id}")
def alert_detail(request: Request, alert_id: int, db: Session = Depends(get_db)):
    row = (
        db.query(ChangeEvent, TrackedPage, Site)
        .join(TrackedPage, ChangeEvent.tracked_page_id == TrackedPage.id)
        .join(Site, TrackedPage.site_id == Site.id)
        .options(joinedload(ChangeEvent.category_links).joinedload(ChangeEventCategory.category))
        .filter(ChangeEvent.id == alert_id)
        .first()
    )
    if row is None:
        return templates.TemplateResponse(
            request,
            "not_found.html",
            {"message": f"Alert {alert_id} not found."},
            status_code=404,
        )
    event, page, site = row
    return templates.TemplateResponse(
        request,
        "alert_detail.html",
        {
            "active_nav": "alerts",
            "event": event,
            "page": page,
            "site": site,
            "category_weight": CATEGORY_WEIGHTS.get(
                event.primary_category, CATEGORY_WEIGHTS["Other"]
            ),
        },
    )


@pages_router.post("/alerts/{alert_id}/status")
def update_alert_status_page(alert_id: int, status: str = Form(...), db: Session = Depends(get_db)):
    event = db.query(ChangeEvent).filter(ChangeEvent.id == alert_id).first()
    if event is not None and status in ("new", "reviewed", "dismissed"):
        event.status = status
        db.commit()
    return RedirectResponse(url=f"/alerts/{alert_id}", status_code=303)


@pages_router.get("/sites/{slug}")
def site_detail(request: Request, slug: str, db: Session = Depends(get_db)):
    site = db.query(Site).options(joinedload(Site.tracked_pages)).filter(Site.slug == slug).first()
    if site is None:
        return templates.TemplateResponse(
            request,
            "not_found.html",
            {"message": f"Organization '{slug}' not found."},
            status_code=404,
        )

    page_ids = [p.id for p in site.tracked_pages]
    events = (
        (
            db.query(ChangeEvent)
            .filter(ChangeEvent.tracked_page_id.in_(page_ids))
            .order_by(ChangeEvent.detected_at.desc())
            .limit(500)
            .all()
        )
        if page_ids
        else []
    )

    # SQLite returns naive datetimes even for timezone-aware columns, so compare
    # using a naive UTC cutoff to avoid tz-aware/naive comparison errors.
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=90)
    recent_events = [
        e
        for e in events
        if (e.detected_at.replace(tzinfo=None) if e.detected_at.tzinfo else e.detected_at) >= cutoff
    ]

    category_counts: dict[str, int] = {}
    for e in recent_events:
        category_counts[e.primary_category] = category_counts.get(e.primary_category, 0) + 1

    avg_score = (
        round(sum(e.signal_score for e in recent_events) / len(recent_events), 1)
        if recent_events
        else 0.0
    )

    daily_counts: dict[str, int] = {}
    for e in recent_events:
        day = e.detected_at.date().isoformat()
        daily_counts[day] = daily_counts.get(day, 0) + 1
    trend = [{"date": d, "count": c} for d, c in sorted(daily_counts.items())]

    return templates.TemplateResponse(
        request,
        "site_detail.html",
        {
            "active_nav": "sites",
            "site": site,
            "recent_events": events[:25],
            "category_counts": sorted(category_counts.items(), key=lambda kv: kv[1], reverse=True),
            "avg_score": avg_score,
            "total_changes_90d": len(recent_events),
            "trend": trend,
        },
    )


@pages_router.get("/settings/sites")
def settings_sites(
    request: Request, db: Session = Depends(get_db), _user: str = Depends(require_admin_auth)
):
    sites = db.query(Site).options(joinedload(Site.tracked_pages)).order_by(Site.name).all()
    settings = get_settings()
    return templates.TemplateResponse(
        request,
        "settings_sites.html",
        {
            "active_nav": "settings",
            "sites": sites,
            "live_monitoring_enabled": settings.enable_live_monitoring,
            "message": request.query_params.get("message"),
            "message_type": request.query_params.get("message_type", "success"),
        },
    )


@pages_router.post("/settings/sites/{site_id}/pages/{page_id}/toggle")
def toggle_page_active(
    site_id: int,
    page_id: int,
    db: Session = Depends(get_db),
    _user: str = Depends(require_admin_auth),
):
    tp = (
        db.query(TrackedPage)
        .filter(TrackedPage.id == page_id, TrackedPage.site_id == site_id)
        .first()
    )
    if tp is None:
        return RedirectResponse(
            url="/settings/sites?message=Tracked+page+not+found&message_type=error", status_code=303
        )
    tp.is_active = not tp.is_active
    db.commit()
    state = "enabled" if tp.is_active else "disabled"
    return RedirectResponse(
        url=f"/settings/sites?message=Page+{state}+successfully&message_type=success",
        status_code=303,
    )


@pages_router.post("/settings/sites/{site_id}/pages/{page_id}/check-now")
def check_page_now(
    site_id: int,
    page_id: int,
    db: Session = Depends(get_db),
    _user: str = Depends(require_admin_auth),
):
    tp = (
        db.query(TrackedPage)
        .filter(TrackedPage.id == page_id, TrackedPage.site_id == site_id)
        .first()
    )
    if tp is None:
        return RedirectResponse(
            url="/settings/sites?message=Tracked+page+not+found&message_type=error", status_code=303
        )
    _snapshot, _event, error = check_page(db, tp)
    db.commit()
    if error:
        return RedirectResponse(
            url=f"/settings/sites?message=Check+failed:+{error}&message_type=error", status_code=303
        )
    return RedirectResponse(
        url="/settings/sites?message=Check+completed+successfully&message_type=success",
        status_code=303,
    )


@pages_router.post("/settings/sites/{site_id}/pages")
def add_tracked_page(
    site_id: int,
    url: str = Form(...),
    page_label: str = Form(...),
    crawl_method: str = Form("http"),
    crawl_interval_minutes: int = Form(720),
    db: Session = Depends(get_db),
    _user: str = Depends(require_admin_auth),
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if site is None:
        return RedirectResponse(
            url="/settings/sites?message=Organization+not+found&message_type=error", status_code=303
        )
    if not url.startswith(("http://", "https://")):
        return RedirectResponse(
            url="/settings/sites?message=URL+must+start+with+http://+or+https://&message_type=error",
            status_code=303,
        )
    db.add(
        TrackedPage(
            site_id=site.id,
            url=url,
            page_label=page_label,
            crawl_method=crawl_method,
            crawl_interval_minutes=crawl_interval_minutes,
            is_active=True,
        )
    )
    db.commit()
    return RedirectResponse(
        url="/settings/sites?message=Tracked+page+added+successfully&message_type=success",
        status_code=303,
    )


@pages_router.post("/monitor/run")
def trigger_monitor_run_page(
    db: Session = Depends(get_db), _user: str = Depends(require_admin_auth)
):
    run = run_monitoring(db)
    return RedirectResponse(
        url=(
            f"/settings/sites?message=Monitoring+run+completed:+{run.pages_succeeded}"
            f"+succeeded,+{run.pages_failed}+failed&message_type=success"
        ),
        status_code=303,
    )


@pages_router.get("/action-plan")
def action_plan(request: Request, db: Session = Depends(get_db)):
    leaderboard = analytics.get_leaderboard(db, days=90, limit=5)
    category_totals = analytics.get_category_totals(db, days=90)
    meaningful_pct = analytics.get_meaningful_change_pct(db, days=90)
    high_signal_examples = (
        db.query(ChangeEvent, TrackedPage, Site)
        .join(TrackedPage, ChangeEvent.tracked_page_id == TrackedPage.id)
        .join(Site, TrackedPage.site_id == Site.id)
        .filter(ChangeEvent.signal_level.in_(["high", "critical"]))
        .order_by(ChangeEvent.signal_score.desc())
        .limit(5)
        .all()
    )
    dominant_category = category_totals[0]["category"] if category_totals else "N/A"

    return templates.TemplateResponse(
        request,
        "action_plan.html",
        {
            "active_nav": "action-plan",
            "leaderboard": leaderboard,
            "category_totals": category_totals,
            "meaningful_pct": meaningful_pct,
            "high_signal_examples": high_signal_examples,
            "dominant_category": dominant_category,
        },
    )


@pages_router.get("/faq")
def faq(request: Request):
    return templates.TemplateResponse(request, "faq.html", {"active_nav": "faq"})


@pages_router.get("/about")
def about(request: Request):
    return templates.TemplateResponse(request, "about.html", {"active_nav": "about"})


@pages_router.get("/contact")
def contact(request: Request):
    return templates.TemplateResponse(request, "contact.html", {"active_nav": "contact"})


@pages_router.get("/robots.txt")
def robots_txt():
    settings = get_settings()
    content = f"User-agent: *\nAllow: /\nDisallow: /settings/\n\nSitemap: {settings.site_url}/sitemap.xml\n"
    return Response(content=content, media_type="text/plain")


@pages_router.get("/sitemap.xml")
def sitemap_xml(db: Session = Depends(get_db)):
    settings = get_settings()
    static_paths = [
        "/",
        "/alerts",
        "/action-plan",
        "/faq",
        "/about",
        "/contact",
    ]
    site_slugs = [row[0] for row in db.query(Site.slug).all()]
    urls = static_paths + [f"/sites/{slug}" for slug in site_slugs]
    body = "\n".join(f"  <url><loc>{settings.site_url}{path}</loc></url>" for path in urls)
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}\n</urlset>\n'
    return Response(content=xml, media_type="application/xml")
