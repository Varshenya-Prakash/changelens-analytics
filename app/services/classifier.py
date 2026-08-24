"""Deterministic, rule-based classification of detected changes.

Each category is defined by a documented keyword/regex dictionary. We scan
both the added and removed text for matches, compute a confidence score per
category based on match density, and allow multiple categories per change.
The highest-confidence category becomes the `primary_category`.

This is intentionally deterministic (no ML) so results are explainable and
reproducible -- a good fit for a transparent competitive-intelligence tool.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Category name -> (keywords/phrases, weight hint used later by scoring).
# Keywords are matched case-insensitively as whole words/phrases.
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Pricing / Commercial": [
        "price",
        "pricing",
        "discount",
        "% off",
        "subscription",
        "plan starts at",
        "cost",
        "free trial",
        "tier",
        "billing",
        "per month",
        "per user",
        "quote",
    ],
    "Product Launch / Product Update": [
        "launch",
        "introducing",
        "new feature",
        "now available",
        "release",
        "product update",
        "unveil",
        "beta",
        "rolling out",
        "upgrade",
        "version",
    ],
    "Hiring / Careers": [
        "we're hiring",
        "we are hiring",
        "job opening",
        "open position",
        "careers",
        "join our team",
        "apply now",
        "now hiring",
        "internship",
        "recruiting",
    ],
    "Leadership / Executive": [
        "chief executive",
        "ceo",
        "cfo",
        "cto",
        "coo",
        "appoints",
        "appointed",
        "names new",
        "board of directors",
        "executive team",
        "steps down",
        "promoted to",
        "new hire as",
    ],
    "Funding / Financial Event": [
        "series a",
        "series b",
        "series c",
        "funding round",
        "raised $",
        "valuation",
        "ipo",
        "acquisition price",
        "quarterly earnings",
        "revenue grew",
        "investment of",
    ],
    "Partnership / Acquisition": [
        "partnership",
        "partners with",
        "acquires",
        "acquisition",
        "merger",
        "strategic alliance",
        "collaborat",
        "joint venture",
    ],
    "PR / News / Thought Leadership": [
        "press release",
        "in the news",
        "announced today",
        "op-ed",
        "whitepaper",
        "webinar",
        "podcast",
        "thought leadership",
        "insights",
        "report finds",
    ],
    "Regulatory / Compliance": [
        "compliance",
        "regulation",
        "regulatory",
        "gdpr",
        "hipaa",
        "sec filing",
        "audit",
        "certification",
        "soc 2",
        "privacy policy update",
    ],
    "Customer / Case Study": [
        "case study",
        "customer story",
        "testimonial",
        "client success",
        "trusted by",
        "our customers",
        "success story",
    ],
    "Layout / Cosmetic / Noise": [
        "cookie",
        "css",
        "layout updated",
        "typo fix",
        "minor update",
        "footer",
        "menu reorganized",
    ],
}

# Words/phrases that push a change toward "cosmetic" even if other keywords match.
COSMETIC_HINTS = ["typo", "css", "layout", "menu reorder", "footer link", "spacing", "alignment"]


@dataclass
class CategoryMatch:
    name: str
    confidence: float
    matched_terms: list[str]


def _count_matches(text_lower: str, terms: list[str]) -> list[str]:
    matched = []
    for term in terms:
        pattern = re.escape(term.lower())
        if re.search(pattern, text_lower):
            matched.append(term)
    return matched


def classify_change(added_text: str, removed_text: str) -> tuple[str, list[CategoryMatch], bool]:
    """Classify a change into one or more categories.

    Returns (primary_category_name, all_matches, is_cosmetic).
    """
    combined = f"{added_text}\n{removed_text}".lower()
    if not combined.strip():
        return "Other", [], False

    matches: list[CategoryMatch] = []
    for category, terms in CATEGORY_KEYWORDS.items():
        matched_terms = _count_matches(combined, terms)
        if not matched_terms:
            continue
        # Confidence: proportion of the category's keyword set that hit, with a
        # floor boost for any match at all, capped at 1.0.
        density = len(matched_terms) / max(len(terms), 1)
        confidence = round(min(0.35 + density * 1.5, 1.0), 3)
        matches.append(
            CategoryMatch(name=category, confidence=confidence, matched_terms=matched_terms)
        )

    if not matches:
        return "Other", [], False

    matches.sort(key=lambda m: m.confidence, reverse=True)
    primary = matches[0].name

    is_cosmetic = primary == "Layout / Cosmetic / Noise" or any(
        hint in combined for hint in COSMETIC_HINTS
    )

    return primary, matches, is_cosmetic
