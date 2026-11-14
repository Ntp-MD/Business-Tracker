"""Collector worker: claims `collect` jobs and runs them in-process.

The legacy source fan-out and stats refresh stay in the Node worker for now; this worker
owns the collector jobs, so a collect no longer needs the local HTTP API hop. Claim,
lease, retry, cancellation, and progress mirror `apps/worker/src/job-runner.ts`.

Run from the repo root:  python -m backend.collectors.worker
One tick and exit:       python -m backend.collectors.worker --once
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import urllib.parse
from datetime import datetime, timedelta, timezone

try:  # running as `python -m backend.collectors.worker`
    from backend import db
    from backend.collectors import dry_run
    from backend.collectors.job import validate_collect_payload
    from backend.collectors.store import job_cancel_check, job_progress, writes_enabled
except ModuleNotFoundError:  # running from the backend directory
    import db

    from collectors import dry_run
    from collectors.job import validate_collect_payload
    from collectors.store import job_cancel_check, job_progress, writes_enabled

POLL_MS = int(os.environ.get("WORKER_POLL_MS") or 2000)
LEASE_MS = int(os.environ.get("WORKER_LEASE_MS") or 3_600_000)
MAX_ATTEMPTS = int(os.environ.get("WORKER_MAX_ATTEMPTS") or 3)
WORKER_ID = f"{os.environ.get('COMPUTERNAME') or 'worker'}-py-{os.getpid()}"
CANCELLED_NOTE = "cancelled; {written} written; rerun is safe"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _lease_until() -> str:
    return (datetime.now(timezone.utc) + timedelta(milliseconds=LEASE_MS)).isoformat()


def _user() -> str:
    return urllib.parse.quote(db.user_id())


def heartbeat() -> None:
    db._request(
        "POST",
        "worker_status",
        {"id": 1, "last_seen": _now(), "note": f"python-pid {os.getpid()}"},
        prefer="resolution=merge-duplicates",
    )


def _recover_expired() -> None:
    """Put collect jobs whose lease expired back in the queue."""
    now = urllib.parse.quote(_now())
    db._request(
        "PATCH",
        f"jobs?status=eq.running&kind=eq.collect&lease_until=lt.{now}&user_id=eq.{_user()}",
        {"status": "queued", "lease_owner": None, "lease_until": None, "started_at": None},
    )


def claim() -> dict | None:
    """Claim the oldest queued collect job for the owner, or None when idle."""
    _recover_expired()
    rows = (
        db._request(
            "GET",
            "jobs?status=eq.queued&kind=eq.collect&user_id=eq."
            f"{_user()}&order=created_at&limit=1&select=id,payload,attempts",
        )
        or []
    )
    if not rows:
        return None
    job = rows[0]
    claimed = (
        db._request(
            "PATCH",
            f"jobs?id=eq.{int(job['id'])}&status=eq.queued",
            {
                "status": "running",
                "started_at": _now(),
                "user_id": db.user_id(),
                "lease_owner": WORKER_ID,
                "lease_until": _lease_until(),
                "attempts": int(job.get("attempts") or 0) + 1,
            },
            prefer="return=representation",
        )
        or []
    )
    return claimed[0] if claimed else None


def _patch_job(job_id: int, body: dict) -> None:
    db._request("PATCH", f"jobs?id=eq.{int(job_id)}", body)


def cancelled(job_id: int, written: int = 0) -> None:
    _patch_job(
        job_id,
        {
            "status": "cancelled",
            "finished_at": _now(),
            "error": CANCELLED_NOTE.format(written=written)[:500],
            "lease_owner": None,
            "lease_until": None,
        },
    )


def run_job(job: dict) -> None:
    job_id = int(job["id"])
    attempts = int(job.get("attempts") or 1)
    payload = dict(job.get("payload") or {})
    payload["dry_run"] = not writes_enabled()
    try:
        validated = validate_collect_payload(payload)
        if job_cancel_check(job_id)():
            cancelled(job_id)
            return
        result = dry_run.run(
            validated["connector_id"],
            validated["scope"]["keyword"],
            validated["max_records"],
            dry_run.DEFAULT_REPORT_DIR,
            0,
            write=not validated["dry_run"],
            cancel_check=job_cancel_check(job_id),
            progress=job_progress(job_id),
        )
    except Exception as exc:  # noqa: BLE001 - mirror the Node runner: retry, then error
        message = str(exc)[:500]
        if attempts < MAX_ATTEMPTS:
            _patch_job(
                job_id,
                {
                    "status": "queued",
                    "started_at": None,
                    "error": message,
                    "lease_owner": None,
                    "lease_until": None,
                },
            )
        else:
            _patch_job(
                job_id,
                {
                    "status": "error",
                    "finished_at": _now(),
                    "error": message,
                    "lease_owner": None,
                    "lease_until": None,
                },
            )
        return

    if result.get("cancelled"):
        cancelled(job_id, int((result.get("counters") or {}).get("written") or 0))
        return
    _patch_job(
        job_id,
        {
            "status": "done",
            "finished_at": _now(),
            "progress": 4,
            "total": 4,
            "error": result.get("error"),
            "lease_owner": None,
            "lease_until": None,
        },
    )


def tick() -> bool:
    """Run one poll; returns True when a job was processed."""
    heartbeat()
    job = claim()
    if job is None:
        return False
    run_job(job)
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run collect jobs from Supabase in-process.")
    parser.add_argument("--once", action="store_true", help="run one tick and exit")
    args = parser.parse_args(argv)

    if not db.configured():
        print(
            "missing SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SUPABASE_USER_ID", file=sys.stderr
        )
        return 1
    print(
        f"collector worker {WORKER_ID}: collect jobs every {POLL_MS}ms; "
        f"writes {'on' if writes_enabled() else 'dry-run'}",
        flush=True,
    )
    if args.once:
        tick()
        return 0
    while True:
        try:
            tick()
        except Exception as exc:  # noqa: BLE001 - one bad poll must not kill the worker
            print(f"tick failed: {exc}", file=sys.stderr, flush=True)
        time.sleep(POLL_MS / 1000)


if __name__ == "__main__":
    raise SystemExit(main())
