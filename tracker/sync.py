from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from .classroom import authorize, fetch_assignments
from .notion import NotionClient
from .status import calculate_status

DEFAULT_TIMEZONE = "America/New_York"


def run(dry_run: bool = False) -> tuple[int, int, list[str]]:
    root = Path(os.getenv("TRACKER_CONFIG_DIR", ".")).expanduser().resolve()
    load_dotenv(root / ".env")
    timezone_name = os.getenv("TRACKER_TIMEZONE", DEFAULT_TIMEZONE)
    timezone = ZoneInfo(timezone_name)
    due_soon_days = int(os.getenv("DUE_SOON_DAYS", "3"))
    if due_soon_days < 0:
        raise ValueError("DUE_SOON_DAYS must be zero or greater.")
    token = os.getenv("NOTION_TOKEN")
    data_source_id = os.getenv("NOTION_DATA_SOURCE_ID")
    if not token or not data_source_id:
        raise RuntimeError("Set NOTION_TOKEN and NOTION_DATA_SOURCE_ID in .env first.")

    credentials = authorize(root / "credentials.json", root / "token.json")
    assignments, warnings = fetch_assignments(credentials, timezone_name)
    notion = NotionClient(token, data_source_id)
    existing = notion.existing_assignments()
    now = datetime.now(timezone)
    created = updated = 0

    seen = set()
    for assignment in assignments:
        if assignment.key in seen:
            continue
        seen.add(assignment.key)
        status = calculate_status(assignment, now, due_soon_days)
        properties = notion.properties(assignment, status, now)
        page_id = existing.get(assignment.key)
        if dry_run:
            print(
                f"{'UPDATE' if page_id else 'CREATE'} [{status}] {assignment.course_name}: {assignment.title}"
            )
        elif page_id:
            notion.update(page_id, properties)
            updated += 1
        else:
            existing[assignment.key] = notion.create(properties)
            created += 1

    return created, updated, warnings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync Google Classroom assignments to Notion."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview without changing Notion."
    )
    args = parser.parse_args()
    try:
        created, updated, warnings = run(dry_run=args.dry_run)
    except (RuntimeError, ValueError, OSError, KeyError) as error:
        print(f"Sync failed: {error}", file=sys.stderr)
        raise SystemExit(1) from None
    for warning in warnings:
        print(f"Warning: {warning}")
    if args.dry_run:
        print("Preview complete; Notion was not changed.")
    else:
        print(f"Sync complete: {created} created, {updated} updated.")


if __name__ == "__main__":
    main()
