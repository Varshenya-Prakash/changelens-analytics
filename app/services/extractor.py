"""HTML parsing and text-extraction utilities.

Turns raw HTML into a normalized, comparable plain-text representation:
scripts/styles/nav/footer boilerplate removed, whitespace collapsed, and
known "noisy" fragments (timestamps, cookie banners, etc.) stripped out
before diffing.
"""

from __future__ import annotations

import hashlib
import re

from bs4 import BeautifulSoup

from app.core.config import get_settings

# Tags whose content never carries meaningful business signal.
BOILERPLATE_TAGS = ["script", "style", "noscript", "svg", "iframe"]
# Common structural containers that are frequently pure navigation/footer chrome.
LIKELY_BOILERPLATE_SELECTORS = [
    "nav",
    "footer",
    "[role=navigation]",
    ".cookie-banner",
    ".cookie-consent",
]


def extract_title_and_text(html: str) -> tuple[str | None, str]:
    """Parse raw HTML and return (title, cleaned visible body text)."""
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None

    for tag_name in BOILERPLATE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    for selector in LIKELY_BOILERPLATE_SELECTORS:
        for tag in soup.select(selector):
            tag.decompose()

    body = soup.body or soup
    text = body.get_text(separator="\n")
    text = normalize_whitespace(text)
    return title, text


def normalize_whitespace(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def strip_ignored_patterns(text: str) -> str:
    """Remove known-noisy fragments (timestamps, cookie banners, copyright)."""
    settings = get_settings()
    cleaned = text
    for pattern in settings.ignored_text_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    # Re-normalize after stripping in case whole lines became empty.
    return normalize_whitespace(cleaned)


def compute_content_hash(text: str) -> str:
    """Stable SHA-256 hash of the *comparison-ready* text (ignored patterns stripped)."""
    comparable = strip_ignored_patterns(text)
    return hashlib.sha256(comparable.encode("utf-8")).hexdigest()
