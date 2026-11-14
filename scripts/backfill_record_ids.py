#!/usr/bin/env python3
"""One-off: fill items.record_id for rows already linked through collector_item_links.

Idempotent; only touches rows whose record_id is still null. Run after applying
supabase/migrations/20261114000000_items_lineage.sql.

Usage:
    python scripts/backfill_record_ids.py [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import db  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill items.record_id from item links.")
    parser.add_argument("--dry-run", action="store_true", help="report without patching")
    args = parser.parse_args(argv)

    if not db.configured():
        print("Supabase is not configured (.env.local)", file=sys.stderr)
        return 1

    user = urllib.parse.quote(db.user_id())
    links = (
        db._request(
            "GET",
            f"collector_item_links?select=record_id,item_id&user_id=eq.{user}&order=record_id.asc",
        )
        or []
    )
    updated = 0
    for link in links:
        if args.dry_run:
            updated += 1
            continue
        db._request(
            "PATCH",
            f"items?id=eq.{urllib.parse.quote(str(link['item_id']))}"
            f"&user_id=eq.{user}&record_id=is.null",
            {"record_id": link["record_id"]},
        )
        updated += 1
    action = "would fill" if args.dry_run else "filled"
    print(f"links: {len(links)}; {action} record_id on up to {updated} items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
