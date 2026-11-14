#!/usr/bin/env python3
"""Logical Supabase backup: every app table as paginated JSON plus a manifest.

This is a PostgREST data export, not `pg_dump`: it preserves rows, not schema (schema is
in supabase/migrations) or Storage objects. Run it before schema changes, keep the output
outside the repo or in the ignored data/ folder, and never commit it.

Usage:
    python scripts/backup_supabase.py [--dir data/backups]

Env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_USER_ID (loaded from .env.local).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import db  # noqa: E402

TABLES = (
    "items",
    "collector_records",
    "collector_item_links",
    "collector_state",
    "source_status",
    "jobs",
    "profiles",
    "keyword_stats",
    "worker_status",
)
PAGE = 1000


def _page(table: str, offset: int, ordered: bool) -> list[dict]:
    query = f"{table}?select=*&limit={PAGE}&offset={offset}"
    if ordered:
        query += "&order=id.asc"
    return db._request("GET", query) or []


def dump_table(table: str) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    ordered = True
    while True:
        try:
            page = _page(table, offset, ordered)
        except Exception:  # noqa: BLE001 - tables without an `id` need the plain query
            if not ordered:
                raise
            ordered = False
            continue
        rows.extend(page)
        if len(page) < PAGE:
            return rows
        offset += PAGE


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export Supabase app tables to JSON.")
    parser.add_argument("--dir", type=Path, default=ROOT / "data" / "backups")
    args = parser.parse_args(argv)

    if not db.configured():
        print("Supabase is not configured (.env.local)", file=sys.stderr)
        return 1

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = args.dir / f"backup-{stamp}"
    target.mkdir(parents=True, exist_ok=True)

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "kind": "logical-postgrest-export",
        "tables": {},
        "notes": "Rows only; schema lives in supabase/migrations, Storage objects are not included.",
    }
    for table in TABLES:
        try:
            rows = dump_table(table)
        except Exception as exc:  # noqa: BLE001 - report the table, keep backing up
            print(f"{table}: FAILED {exc}", file=sys.stderr)
            manifest["tables"][table] = {"error": str(exc)[:300]}
            continue
        path = target / f"{table}.json"
        body = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        path.write_bytes(body)
        manifest["tables"][table] = {
            "rows": len(rows),
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
        }
        print(f"{table}: {len(rows)} rows", flush=True)

    (target / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"backup: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
