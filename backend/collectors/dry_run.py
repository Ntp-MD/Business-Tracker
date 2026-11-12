"""Dry-run collector CLI: fetch, gate, report. Never writes to Postgres."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import hn
from .contract import QUALITY_RULES_VERSION, utc_now
from .quality import gate
from .registry import get_connector

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_DIR = ROOT / "data" / "reports"


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
    path.write_text(
        "\n".join(json.dumps(line, ensure_ascii=False) for line in lines) + "\n", encoding="utf-8"
    )
    print(f"report: {path} ({len(lines)} records)")


def run(
    connector_id: str,
    keyword: str,
    limit: int,
    report_dir: Path,
    show_sample: int,
) -> dict:
    connector = get_connector(connector_id)
    if not connector.enabled:
        raise SystemExit(f"connector disabled: {connector_id}")
    if not connector.dry_run:
        raise SystemExit(f"connector is not in dry-run mode: {connector_id}")

    fetched = hn.fetch(keyword, limit, connector)
    outcome = gate(fetched, connector)
    counters = outcome.counters(len(fetched))
    summary = {
        "connector_id": connector.connector_id,
        "source": connector.source,
        "keyword": keyword,
        "dry_run": True,
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
        description="Run one collector in dry-run mode (no DB writes)."
    )
    parser.add_argument("--connector", default="hn_search")
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--show-sample", type=int, default=0)
    args = parser.parse_args(argv)
    run(args.connector, args.keyword, args.limit, args.report_dir, args.show_sample)
    return 0


if __name__ == "__main__":
    sys.exit(main())
