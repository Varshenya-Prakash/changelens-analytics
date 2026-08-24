"""Command-line entry points for ChangeLens Analytics.

Usage:
    python -m app.cli seed-demo-data
    python -m app.cli generate-demo-events
    python -m app.cli run-monitor [--page-id N]
    python -m app.cli reset-demo-data
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from datetime import UTC, datetime

from app.core.config import RAW_SNAPSHOTS_DIR, get_settings
from app.core.logging_config import configure_logging
from app.db.session import session_scope
from app.models import ChangeEvent, MonitoringRun, Site, Snapshot, TrackedPage
from app.services.extractor import compute_content_hash
from app.services.monitoring import build_change_event, run_monitoring
from app.services.seed_data import PAGE_LABELS, build_seed_plan

logger = logging.getLogger(__name__)


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "site"


def cmd_seed_demo_data(_args: argparse.Namespace) -> None:
    """Create 8 organizations, 12-20 tracked pages, 100+ snapshots, and 35+
    change events across a deterministic 90-day synthetic timeline."""
    plan = build_seed_plan(days=90, min_events=55)

    with session_scope() as db:
        existing = db.query(Site).count()
        if existing:
            print(
                f"Seed data already present ({existing} sites). Run 'reset-demo-data' first to re-seed."
            )
            return

        site_by_name: dict[str, Site] = {}
        page_by_key: dict[str, TrackedPage] = {}

        for org in plan.organizations:
            site = Site(
                name=org["name"],
                slug=slugify(org["name"]),
                sector=org["sector"],
                base_url=org["base_url"],
                is_active=True,
            )
            db.add(site)
            db.flush()
            site_by_name[org["name"]] = site

            for page_type in org["pages"]:
                tracked_page = TrackedPage(
                    site_id=site.id,
                    url=f"{org['base_url']}/{page_type}",
                    page_label=PAGE_LABELS[page_type],
                    crawl_method="http",
                    crawl_interval_minutes=720,
                    is_active=True,
                )
                db.add(tracked_page)
                db.flush()
                page_by_key[f"{org['name']}::{page_type}"] = tracked_page

        db.flush()

        total_snapshots = 0
        total_events = 0

        for key, specs in plan.snapshots_by_page.items():
            page = page_by_key[key]
            previous_snapshot: Snapshot | None = None

            for spec in specs:
                content_hash = compute_content_hash(spec.text)
                if previous_snapshot is not None and previous_snapshot.content_hash == content_hash:
                    # Duplicate content: skip persisting a new snapshot, mirroring
                    # real pipeline behaviour (store_duplicate_snapshots=false).
                    page.last_checked_at = spec.fetched_at
                    continue

                snapshot = Snapshot(
                    tracked_page_id=page.id,
                    fetched_at=spec.fetched_at,
                    http_status=200,
                    content_hash=content_hash,
                    raw_html_path=None,
                    extracted_text=spec.text,
                    title=spec.title,
                    snapshot_metadata={"source": "synthetic-demo-fixture"},
                    fetch_duration_ms=120,
                )
                db.add(snapshot)
                db.flush()
                total_snapshots += 1
                page.last_checked_at = spec.fetched_at

                if previous_snapshot is not None:
                    event = build_change_event(db, page, previous_snapshot, snapshot)
                    event.detected_at = spec.fetched_at
                    total_events += 1

                previous_snapshot = snapshot

        # Backfill a monitoring run record so /settings shows realistic history.
        run = MonitoringRun(
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            status="completed",
            pages_attempted=len(page_by_key),
            pages_succeeded=len(page_by_key),
            pages_failed=0,
            notes="Initial demo-data seed run (synthetic fixtures, no live network access).",
        )
        db.add(run)

        db.commit()

        print(
            f"Seeded {len(site_by_name)} organizations, {len(page_by_key)} tracked pages, "
            f"{total_snapshots} snapshots, {total_events} change events."
        )


def cmd_generate_demo_events(_args: argparse.Namespace) -> None:
    """Append a fresh batch of synthetic change events on top of existing seed data,
    useful for demoing an incremental monitoring run without full re-seed."""
    with session_scope() as db:
        pages = db.query(TrackedPage).all()
        if not pages:
            print("No tracked pages found. Run 'seed-demo-data' first.")
            return

        import random

        from app.services.seed_data import CATEGORY_SNIPPETS

        rng = random.Random()
        created = 0
        for page in pages:
            last_snapshot = (
                db.query(Snapshot)
                .filter(Snapshot.tracked_page_id == page.id)
                .order_by(Snapshot.fetched_at.desc())
                .first()
            )
            if last_snapshot is None or rng.random() < 0.4:
                continue  # not every page gets a new event each run

            category = rng.choice(list(CATEGORY_SNIPPETS.keys()))
            snippet = rng.choice(CATEGORY_SNIPPETS[category])
            new_text = f"{last_snapshot.extracted_text}\n{snippet}"
            new_hash = compute_content_hash(new_text)
            if new_hash == last_snapshot.content_hash:
                continue

            snapshot = Snapshot(
                tracked_page_id=page.id,
                fetched_at=datetime.now(UTC),
                http_status=200,
                content_hash=new_hash,
                extracted_text=new_text,
                title=last_snapshot.title,
                snapshot_metadata={"source": "synthetic-demo-fixture-incremental"},
                fetch_duration_ms=110,
            )
            db.add(snapshot)
            db.flush()
            build_change_event(db, page, last_snapshot, snapshot)
            page.last_checked_at = snapshot.fetched_at
            created += 1

        db.commit()
        print(f"Generated {created} new synthetic change events.")


def cmd_run_monitor(args: argparse.Namespace) -> None:
    settings = get_settings()
    if not settings.enable_live_monitoring:
        print(
            "ENABLE_LIVE_MONITORING is false: this will run the pipeline but every "
            "fetch will no-op safely (no real network requests)."
        )
    with session_scope() as db:
        run = run_monitoring(db, page_id=args.page_id)
        print(
            f"Monitoring run {run.id}: status={run.status}, "
            f"attempted={run.pages_attempted}, succeeded={run.pages_succeeded}, failed={run.pages_failed}"
        )
        if run.notes:
            print("Notes:\n" + run.notes)


def cmd_reset_demo_data(_args: argparse.Namespace) -> None:
    with session_scope() as db:
        db.query(ChangeEvent).delete()
        db.query(Snapshot).delete()
        db.query(TrackedPage).delete()
        db.query(Site).delete()
        db.query(MonitoringRun).delete()
        db.commit()

    import shutil

    if RAW_SNAPSHOTS_DIR.exists():
        shutil.rmtree(RAW_SNAPSHOTS_DIR)
    print("All demo data has been reset.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli", description="ChangeLens Analytics CLI"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("seed-demo-data", help="Seed deterministic synthetic demo data.")
    sub.add_parser("generate-demo-events", help="Append additional synthetic change events.")

    run_monitor_parser = sub.add_parser("run-monitor", help="Run the monitoring pipeline.")
    run_monitor_parser.add_argument(
        "--page-id", type=int, default=None, help="Only monitor a single tracked page."
    )

    sub.add_parser("reset-demo-data", help="Delete all sites/pages/snapshots/events.")

    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args(argv)

    handlers = {
        "seed-demo-data": cmd_seed_demo_data,
        "generate-demo-events": cmd_generate_demo_events,
        "run-monitor": cmd_run_monitor,
        "reset-demo-data": cmd_reset_demo_data,
    }
    handlers[args.command](args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
