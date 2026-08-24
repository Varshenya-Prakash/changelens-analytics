"""Page-fetching layer.

Wraps httpx with a descriptive User-Agent, timeouts, retry/backoff, and a
per-domain politeness delay. Live network access is gated behind the
`ENABLE_LIVE_MONITORING` setting so the prototype never scrapes real sites
unless a developer explicitly opts in locally.

A Playwright-based fallback path is stubbed for JS-rendered pages
(`crawl_method="playwright"`); it is optional and only imported on demand so
the base install does not require a browser download.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Simple in-process per-domain last-fetch tracker for politeness delays.
_last_fetch_by_domain: dict[str, float] = {}


@dataclass
class FetchResult:
    url: str
    status_code: int | None
    html: str | None
    duration_ms: int
    error: str | None = None


def _respect_domain_delay(url: str) -> None:
    settings = get_settings()
    domain = urlparse(url).netloc
    last = _last_fetch_by_domain.get(domain)
    now = time.monotonic()
    if last is not None:
        elapsed = now - last
        wait_for = settings.per_domain_delay_seconds - elapsed
        if wait_for > 0:
            time.sleep(wait_for)
    _last_fetch_by_domain[domain] = time.monotonic()


def fetch_http(url: str) -> FetchResult:
    """Fetch a URL via plain HTTP(S) using httpx, with retries and backoff.

    Raises no exceptions; failures are captured in `FetchResult.error` so a
    monitoring batch can continue past individual page failures.
    """
    settings = get_settings()

    if not settings.enable_live_monitoring:
        return FetchResult(
            url=url,
            status_code=None,
            html=None,
            duration_ms=0,
            error=(
                "Live monitoring is disabled (ENABLE_LIVE_MONITORING=false). "
                "This is expected in the default demo configuration."
            ),
        )

    _respect_domain_delay(url)

    headers = {"User-Agent": settings.user_agent}
    attempt = 0
    last_error: str | None = None
    start = time.monotonic()

    while attempt <= settings.request_max_retries:
        try:
            with httpx.Client(
                timeout=settings.request_timeout_seconds, follow_redirects=True
            ) as client:
                response = client.get(url, headers=headers)
            duration_ms = int((time.monotonic() - start) * 1000)
            return FetchResult(
                url=url,
                status_code=response.status_code,
                html=response.text,
                duration_ms=duration_ms,
            )
        except httpx.HTTPError as exc:
            last_error = str(exc)
            attempt += 1
            backoff = 0.5 * (2**attempt)
            logger.warning("Fetch attempt %s failed for %s: %s", attempt, url, exc)
            time.sleep(backoff)

    duration_ms = int((time.monotonic() - start) * 1000)
    return FetchResult(
        url=url, status_code=None, html=None, duration_ms=duration_ms, error=last_error
    )


def fetch_playwright(url: str) -> FetchResult:
    """Fetch a JS-rendered page via Playwright (optional dependency).

    Only invoked when a TrackedPage's crawl_method is 'playwright' and live
    monitoring is enabled. Requires `pip install site-tracker-analytics[playwright]`
    and `playwright install chromium`.
    """
    settings = get_settings()
    if not settings.enable_live_monitoring:
        return FetchResult(
            url=url,
            status_code=None,
            html=None,
            duration_ms=0,
            error="Live monitoring is disabled (ENABLE_LIVE_MONITORING=false).",
        )

    _respect_domain_delay(url)
    start = time.monotonic()
    try:
        from playwright.sync_api import sync_playwright  # noqa: PLC0415
    except ImportError:
        return FetchResult(
            url=url,
            status_code=None,
            html=None,
            duration_ms=0,
            error="Playwright is not installed. Install the 'playwright' extra to enable JS rendering.",
        )

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(user_agent=settings.user_agent)
            response = page.goto(url, timeout=settings.request_timeout_seconds * 1000)
            html = page.content()
            status_code = response.status if response else None
            browser.close()
        duration_ms = int((time.monotonic() - start) * 1000)
        return FetchResult(url=url, status_code=status_code, html=html, duration_ms=duration_ms)
    except Exception as exc:  # noqa: BLE001
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.warning("Playwright fetch failed for %s: %s", url, exc)
        return FetchResult(
            url=url, status_code=None, html=None, duration_ms=duration_ms, error=str(exc)
        )


def fetch(url: str, crawl_method: str = "http") -> FetchResult:
    if crawl_method == "playwright":
        return fetch_playwright(url)
    return fetch_http(url)
