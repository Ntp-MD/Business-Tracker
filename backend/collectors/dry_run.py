"""Dry-run collector CLI: fetch, gate, report. Never writes to Postgres."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .contract import QUALITY_RULES_VERSION, utc_now
from .quality import gate
from .registry import get_connector

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_DIR = ROOT / "data" / "reports"

# No adapters after the Hacker News removal. A future adapter registers here only
# after its access/rights/quality review.
ADAPTERS: dict[str, object] = {}


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def write_report(path: Path, outcome) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[dict] = []
    for record in outcome.accepted:
        lines.append(
            {
                "status": "accepted",
                "url_sha256": _url_hash(record.url),
                "source_item_id": record.source_item_id,
                "language": record.language,
                "flags": record.quality_flags,
            }
        )
    for rejection in outcome.rejected:
        lines.append(
            {
                "status": "rejected",
                "reason": rejection.reason,
                "url_sha256": _url_hash(rejection.raw.url),
                "source_item_id": rejection.raw.source_item_id,
            }
        )
    for quarantine in outcome.quarantined:
        lines.append(
            {
                "status": "quarantined",
                "reason": quarantine.reason,
                "url_sha256": _url_hash(quarantine.raw.url),
                "source_item_id": quarantine.raw.source_item_id,
            }
        )
    # Append: same-day runs must not overwrite earlier evidence.
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(json.dumps(line, ensure_ascii=False) for line in lines) + "\n")
    print(f"report: {path} ({len(lines)} records)")


def run(
    connector_id: str,
    keyword: str,
    limit: int,
    report_dir: Path,
    show_sample: int,
    *,
    write: bool = False,
    item_keyword: str | None = None,
) -> dict:
    connector = get_connector(connector_id)
    if not connector.enabled:
        raise SystemExit(f"connector disabled: {connector_id}")
    adapter = ADAPTERS.get(connector.connector_id)
    if adapter is None:
        raise SystemExit(f"no adapter for connector: {connector_id}")
    if not connector.dry_run:
        raise SystemExit(f"connector is not in dry-run mode: {connector_id}")

    save_accepted = None
    if write:
        from .store import save_accepted as save
        from .store import writes_enabled

        if not writes_enabled():
            raise SystemExit("collector writes disabled (set COLLECTOR_WRITE_ENABLED=1)")
        save_accepted = save

    fetched = adapter.fetch(keyword, limit, connector)
    outcome = gate(fetched, connector)
    counters = outcome.counters(len(fetched))
    projection_keyword = item_keyword or keyword
    if save_accepted is not None:
        counters = save_accepted(connector, projection_keyword, outcome.accepted, counters)

    summary = {
        "connector_id": connector.connector_id,
        "source": connector.source,
        "keyword": keyword,
        "item_keyword": projection_keyword,
        "dry_run": not write,
        "quality_rules_version": QUALITY_RULES_VERSION,
        "at": utc_now().isoformat(),
        "counters": counters,
    }
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    write_report(report_dir / f"collector-{connector_id}-{day}.jsonl", outcome)
    print(json.dumps(summary, ensure_ascii=False))

    for record in outcome.accepted[:show_sample]:
        print(
            f"sample: {record.source_item_id} | {record.language} | {record.title} | {record.canonical_url}"
        )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run one collector; dry-run by default, --write persists accepted records."
    )
    parser.add_argument("--connector", required=True)
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--item-keyword", help="items.keyword projection (defaults to --keyword)")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--show-sample", type=int, default=0)
    parser.add_argument("--write", action="store_true", help="persist accepted records")
    args = parser.parse_args(argv)
    run(
        args.connector,
        args.keyword,
        args.limit,
        args.report_dir,
        args.show_sample,
        write=args.write,
        item_keyword=args.item_keyword,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
