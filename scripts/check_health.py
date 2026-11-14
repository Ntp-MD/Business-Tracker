#!/usr/bin/env python3
"""Fail when deployed health endpoints are down, unhealthy, or the worker is stale.

Used by .github/workflows/health.yml. Override targets with HEALTH_URLS
(comma-separated) for local testing.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request

DEFAULT_URLS = (
    "https://trendrail.vercel.app/api/health,https://trendrail-live.vercel.app/api/health"
)


def check(url: str) -> None:
    """Fail on an unhealthy endpoint; a stopped local worker is a warning.

    The worker runs on the owner's PC and is expected to be offline sometimes, so it must
    not open a GitHub issue by itself. A failed fetch or ok=false still fails.
    """
    with urllib.request.urlopen(url, timeout=30) as response:
        data = json.load(response)

    if not data.get("ok"):
        raise RuntimeError(f"ok=false error={data.get('error')}")

    worker = data.get("worker")
    if worker is None and "trendrail.vercel.app" in url:
        print(f"warning {url}: worker status missing (local worker offline?)")
    elif worker and worker.get("stale"):
        print(f"warning {url}: worker stale last_seen={worker.get('lastSeen')}")

    print(json.dumps({"url": url, "ok": True, "worker": worker}))


def main() -> int:
    urls = [item.strip() for item in os.environ.get("HEALTH_URLS", DEFAULT_URLS).split(",")]
    failed = False
    for url in urls:
        if not url:
            continue
        try:
            check(url)
        except Exception as exc:  # noqa: BLE001 - report every failure, keep checking
            failed = True
            print(f"FAILED {url}: {exc}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
