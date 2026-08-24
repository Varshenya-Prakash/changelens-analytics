"""Deterministic synthetic demo-data generator.

Everything here is fully synthetic/fixture content generated for portfolio
demonstration purposes. No live network access or scraping is used. Organization
names below are real public companies used only as realistic, low-risk labels
for demonstration targets (news/about/careers/pricing pages) -- no proprietary
content is reproduced; all page text is authored fixture copy.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

SEED = 20260818  # deterministic seed so demo data is reproducible

# --- 8 demo organizations across consulting, financial services, healthtech ---
ORGANIZATIONS = [
    {
        "name": "Meridian Consulting Group",
        "sector": "Consulting",
        "base_url": "https://www.example-meridian.com",
        "pages": ["news", "careers", "about"],
    },
    {
        "name": "Northgate Advisory Partners",
        "sector": "Consulting",
        "base_url": "https://www.example-northgate.com",
        "pages": ["news", "pricing"],
    },
    {
        "name": "Cascade Financial Group",
        "sector": "Financial Services",
        "base_url": "https://www.example-cascade.com",
        "pages": ["news", "pricing", "about"],
    },
    {
        "name": "Ironbridge Capital",
        "sector": "Financial Services",
        "base_url": "https://www.example-ironbridge.com",
        "pages": ["news", "careers"],
    },
    {
        "name": "Summit Wealth Partners",
        "sector": "Financial Services",
        "base_url": "https://www.example-summitwealth.com",
        "pages": ["pricing", "about"],
    },
    {
        "name": "Vantage Health Systems",
        "sector": "Healthcare / Healthtech",
        "base_url": "https://www.example-vantagehealth.com",
        "pages": ["news", "careers", "about"],
    },
    {
        "name": "Clearwell Diagnostics",
        "sector": "Healthcare / Healthtech",
        "base_url": "https://www.example-clearwell.com",
        "pages": ["news", "pricing"],
    },
    {
        "name": "Beacon Care Analytics",
        "sector": "Healthcare / Healthtech",
        "base_url": "https://www.example-beaconcare.com",
        "pages": ["news", "careers", "pricing"],
    },
]

PAGE_LABELS = {
    "news": "Newsroom",
    "careers": "Careers",
    "about": "About",
    "pricing": "Pricing",
}

# --- Fixture content blocks per category, used to build realistic synthetic snapshots ---
CATEGORY_SNIPPETS: dict[str, list[str]] = {
    "Pricing / Commercial": [
        "New pricing: our Growth plan now starts at $199 per month, billed annually.",
        "We've introduced a new Enterprise tier with custom quote-based pricing.",
        "Limited-time offer: 20% off your first year on all subscription plans.",
        "Updated billing: usage-based pricing now available for high-volume customers.",
    ],
    "Product Launch / Product Update": [
        "Introducing our new analytics module, now available in beta to all customers.",
        "Product update: version 4.2 rolls out improved reporting and a redesigned dashboard.",
        "We are excited to launch a new mobile app, now available on iOS and Android.",
        "New feature: real-time collaboration tools are now live for all workspace plans.",
    ],
    "Hiring / Careers": [
        "We're hiring! Open positions include Senior Data Engineer and Product Manager.",
        "Join our team: we are now hiring across engineering, sales, and customer success.",
        "New internship program launching this summer -- apply now for open positions.",
        "We've opened a new office and are actively recruiting for 15 open roles.",
    ],
    "Leadership / Executive": [
        "We are pleased to announce that Maria Chen has been appointed as our new Chief Executive Officer.",
        "Our board of directors has named James Whitfield as Chief Financial Officer, effective next quarter.",
        "After eight years leading the company, our CEO has announced plans to step down at year end.",
        "We've promoted our VP of Engineering to Chief Technology Officer as part of our executive team expansion.",
    ],
    "Funding / Financial Event": [
        "We are thrilled to announce a $40M Series B funding round led by a leading growth investor.",
        "Our latest quarterly earnings show revenue grew 28% year over year.",
        "The company has completed a new investment of $12M to accelerate product development.",
        "We are proud to share that our valuation has increased following our recent Series C round.",
    ],
    "Partnership / Acquisition": [
        "We are excited to announce a new strategic partnership with a leading technology provider.",
        "Today we announced that we have acquired a complementary analytics startup.",
        "Our companies have entered into a joint venture to expand into new markets.",
        "We've formed a strategic alliance to bring integrated solutions to our customers.",
    ],
    "PR / News / Thought Leadership": [
        "In the news: our latest report finds significant shifts in market demand this quarter.",
        "We published a new whitepaper on industry trends -- available for download today.",
        "Announced today: our CEO will be speaking at the upcoming industry summit.",
        "Check out our new podcast episode featuring insights from our leadership team.",
    ],
    "Regulatory / Compliance": [
        "We have achieved SOC 2 Type II certification, reflecting our commitment to data security.",
        "Our privacy policy update reflects new compliance requirements effective this quarter.",
        "We are now fully compliant with updated data protection regulations in all markets we serve.",
        "Our latest regulatory filing outlines our ongoing commitment to industry compliance standards.",
    ],
    "Customer / Case Study": [
        "New case study: see how one of our customers achieved 3x growth using our platform.",
        "Read our latest customer story featuring feedback from teams across the industry.",
        "We're proud to be trusted by leading organizations across multiple sectors.",
        "New testimonial: our client shares how our solution improved their success story.",
    ],
    "Layout / Cosmetic / Noise": [
        "We updated our footer links for easier navigation.",
        "Minor update: reorganized our site menu for improved usability.",
        "We fixed a small typo on this page.",
        "Updated the layout and spacing of this page for a cleaner look.",
    ],
}

BASE_PARAGRAPHS: dict[str, list[str]] = {
    "news": [
        "Welcome to our newsroom. Here you'll find the latest company announcements, press coverage, and updates.",
        "Stay up to date with everything happening across our organization.",
    ],
    "careers": [
        "We're building a team of talented people who care about doing great work.",
        "Explore open roles across engineering, sales, operations, and more.",
    ],
    "about": [
        "Founded with a mission to serve our customers with excellence, we've grown into an industry leader.",
        "Learn more about our story, our values, and the people behind our work.",
    ],
    "pricing": [
        "Choose the plan that's right for your team. All plans include core features and support.",
        "Flexible pricing designed to scale with your organization.",
    ],
}


@dataclass
class SnapshotSpec:
    tracked_page_key: str
    fetched_at: datetime
    text: str
    title: str
    change_category: str | None  # None for baseline/no-op snapshots


@dataclass
class SeedPlan:
    organizations: list[dict] = field(default_factory=list)
    snapshots_by_page: dict[str, list[SnapshotSpec]] = field(default_factory=dict)


def _page_key(org_name: str, page_type: str) -> str:
    return f"{org_name}::{page_type}"


def build_seed_plan(days: int = 90, min_events: int = 40) -> SeedPlan:
    """Build a deterministic plan of synthetic snapshots across all orgs/pages.

    Ensures at least `min_events` change events (i.e. >=2 distinct-content
    snapshots per some pages) and a realistic category mix over `days`.
    """
    rng = random.Random(SEED)
    now = datetime.now(UTC)
    start = now - timedelta(days=days)

    plan = SeedPlan(organizations=ORGANIZATIONS)

    category_cycle = list(CATEGORY_SNIPPETS.keys())
    rng.shuffle(category_cycle)
    cycle_idx = 0

    events_generated = 0

    for org in ORGANIZATIONS:
        for page_type in org["pages"]:
            key = _page_key(org["name"], page_type)
            plan.snapshots_by_page[key] = []

            base_text = " ".join(BASE_PARAGRAPHS[page_type])
            current_text = base_text
            # Baseline snapshot near the start of the window.
            baseline_time = start + timedelta(hours=rng.randint(0, 12))
            plan.snapshots_by_page[key].append(
                SnapshotSpec(
                    tracked_page_key=key,
                    fetched_at=baseline_time,
                    text=current_text,
                    title=f"{org['name']} — {PAGE_LABELS[page_type]}",
                    change_category=None,
                )
            )

            # Number of change points per page varies 4-8 across the window.
            num_changes = rng.randint(4, 8)
            timestamps = sorted(
                start + timedelta(days=rng.uniform(1, days - 1)) for _ in range(num_changes)
            )

            for ts in timestamps:
                category = category_cycle[cycle_idx % len(category_cycle)]
                cycle_idx += 1
                snippet = rng.choice(CATEGORY_SNIPPETS[category])
                # Roughly 1 in 6 changes is a pure duplicate check (no-op) to
                # exercise duplicate-snapshot handling; skip adding new text then.
                if rng.random() < 0.06:
                    plan.snapshots_by_page[key].append(
                        SnapshotSpec(
                            tracked_page_key=key,
                            fetched_at=ts,
                            text=current_text,
                            title=f"{org['name']} — {PAGE_LABELS[page_type]}",
                            change_category=None,
                        )
                    )
                    continue

                # Occasionally simulate a bigger content overhaul (e.g. a full
                # newsroom rewrite) so magnitude -- and therefore signal score --
                # varies realistically, producing some high/critical alerts.
                if rng.random() < 0.35:
                    extra_snippets = rng.sample(
                        CATEGORY_SNIPPETS[category], k=min(3, len(CATEGORY_SNIPPETS[category]))
                    )
                    other_cat = rng.choice([c for c in category_cycle if c != category])
                    extra_snippets += rng.sample(
                        CATEGORY_SNIPPETS[other_cat], k=min(2, len(CATEGORY_SNIPPETS[other_cat]))
                    )
                    snippet = snippet + "\n" + "\n".join(extra_snippets)
                elif rng.random() < 0.08:
                    # Rare "major overhaul": near-total rewrite of the page,
                    # producing a critical-level signal for demo variety.
                    current_text = ""
                    extra_snippets = [
                        s for terms in CATEGORY_SNIPPETS.values() for s in rng.sample(terms, k=1)
                    ]
                    snippet = snippet + "\n" + "\n".join(extra_snippets)

                current_text = f"{current_text}\n{snippet}"
                plan.snapshots_by_page[key].append(
                    SnapshotSpec(
                        tracked_page_key=key,
                        fetched_at=ts,
                        text=current_text,
                        title=f"{org['name']} — {PAGE_LABELS[page_type]}",
                        change_category=category,
                    )
                )
                events_generated += 1

            # A few extra untouched "still checking" snapshots near the end.
            tail_time = now - timedelta(hours=rng.randint(1, 48))
            plan.snapshots_by_page[key].append(
                SnapshotSpec(
                    tracked_page_key=key,
                    fetched_at=tail_time,
                    text=current_text,
                    title=f"{org['name']} — {PAGE_LABELS[page_type]}",
                    change_category=None,
                )
            )

    # Top up events if we're short of the minimum by adding more change points
    # to random pages (deterministically, using the same rng stream).
    attempts = 0
    keys = list(plan.snapshots_by_page.keys())
    while events_generated < min_events and attempts < 500:
        attempts += 1
        key = rng.choice(keys)
        specs = plan.snapshots_by_page[key]
        last_text = specs[-1].text
        category = category_cycle[cycle_idx % len(category_cycle)]
        cycle_idx += 1
        snippet = rng.choice(CATEGORY_SNIPPETS[category])
        new_text = f"{last_text}\n{snippet}"
        insert_time = specs[-1].fetched_at - timedelta(hours=rng.randint(1, 20))
        specs.insert(
            -1,
            SnapshotSpec(
                tracked_page_key=key,
                fetched_at=insert_time,
                text=new_text,
                title=specs[-1].title,
                change_category=category,
            ),
        )
        specs[-1].text = new_text  # propagate forward to the final snapshot too
        events_generated += 1

    # Ensure chronological order per page after any insertions.
    for specs in plan.snapshots_by_page.values():
        specs.sort(key=lambda s: s.fetched_at)

    return plan


def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
