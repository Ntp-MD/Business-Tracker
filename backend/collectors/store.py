"""Targeted collector persistence. Disabled unless COLLECTOR_WRITE_ENABLED=1.

No snapshot delete: records, item projections, links and state are upserted by
their stable keys. The migration in supabase/migrations/20261112010000_collectors.sql
must be applied first.
"""

from __future__ import annotations

import os
from urllib.parse import quote

try:  # running as `python backend/server.py` or importing `collectors.*`
    import db
except ModuleNotFoundError:  # running as `python -m backend.collectors.dry_run`
    from backend import db

from .contract import CollectorRecord, utc_now
from .registry import Connector

WRITE_ENV = "COLLECTOR_WRITE_ENABLED"


def writes_enabled() -> bool:
    return (os.environ.get(WRITE_ENV) or "0").strip().lower() in {"1", "true", "yes"}


def scope_key(keyword: str) -> str:
    return f"keyword:{keyword}"


def _post(
    table: str,
    rows: list[dict],
    on_conflict: str,
    select: str = "",
    resolution: str = "merge-duplicates",
) -> list[dict]:
    if not rows:
        return []
    path = f"{table}?on_conflict={quote(on_conflict)}"
    if select:
        path += f"&select={select}"
    return (
        db._request(
            "POST",
            path,
            rows,
            prefer=f"resolution={resolution},return=representation",
        )
        or []
    )


def _find_item_id(user_id: str, keyword: str, canonical_url: str) -> str | None:
    rows = (
        db._request(
            "GET",
            "items?select=id,canonical_url"
            f"&user_id=eq.{quote(user_id)}"
            f"&keyword=eq.{quote(keyword)}"
            f"&canonical_url=eq.{quote(canonical_url, safe='')}"
            "&limit=1",
        )
        or []
    )
    return rows[0]["id"] if rows else None


def _record_exists(user_id: str, connector: Connector, source_item_id: str) -> bool:
    rows = (
        db._request(
            "GET",
            "collector_records?select=id"
            f"&user_id=eq.{quote(user_id)}"
            f"&source=eq.{quote(connector.source)}"
            f"&source_item_id=eq.{quote(source_item_id, safe='')}"
            "&limit=1",
        )
        or []
    )
    return bool(rows)


def _record_row(record: CollectorRecord, user_id: str, keyword: str) -> dict:
    return {
        "user_id": user_id,
        "source": record.source,
        "connector_id": record.connector_id,
        "source_item_id": record.source_item_id,
        "record_kind": record.record_kind,
        "content_type": record.content_type,
        "url": record.url,
        "canonical_url": record.canonical_url,
        "title": record.title,
        "author_id": record.author_id,
        "author_display": record.author_display,
        "language": record.language,
        "published_at": record.published_at,
        "observed_at": record.observed_at,
        "engagement": record.engagement,
        "numeric_signal": record.numeric_signal,
        "signal_unit": record.signal_unit,
        "keywords_matched": [keyword],
        "raw_source_ref": record.raw_source_ref,
        "quality_score": record.quality_score,
        "quality_flags": record.quality_flags,
        "quality_rules_version": record.quality_rules_version,
    }


def _item_row(record: CollectorRecord, user_id: str, keyword: str) -> dict:
    metric = "points" if record.signal_unit == "points" else None
    return {
        "user_id": user_id,
        "keyword": keyword,
        "source": record.source,
        "url": record.url,
        "canonical_url": record.canonical_url,
        "title": record.title,
        "body": "",
        "author": record.author_display,
        "channel_url": "",
        "score": int(record.numeric_signal or 0),
        "metric": metric,
        "views": None,
        "published": record.published_at,
    }


def save_accepted(
    connector: Connector,
    keyword: str,
    records: list[CollectorRecord],
    counters: dict,
    cursor: dict | None = None,
) -> dict:
    if not writes_enabled():
        raise RuntimeError(f"collector writes disabled (set {WRITE_ENV}=1)")
    if not db.configured():
        raise RuntimeError("Supabase is not configured")

    user = db.user_id()
    now = utc_now().isoformat()

    existing_records = sum(
        1 for record in records if _record_exists(user, connector, record.source_item_id)
    )

    record_rows = [_record_row(record, user, keyword) for record in records]
    saved_records = _post(
        "collector_records",
        record_rows,
        "user_id,source,source_item_id",
        "id,source_item_id",
    )
    record_ids = {row["source_item_id"]: row["id"] for row in saved_records}

    item_ids: dict[str, str] = {}
    for record in records:
        existing = _find_item_id(user, keyword, record.canonical_url)
        if existing:
            item_ids[record.canonical_url] = existing
            continue
        saved = _post(
            "items",
            [_item_row(record, user, keyword)],
            "user_id,keyword,canonical_url",
            "id,canonical_url",
            resolution="ignore-duplicates",
        )
        if saved:
            item_ids[record.canonical_url] = saved[0]["id"]
        else:
            fallback = _find_item_id(user, keyword, record.canonical_url)
            if fallback:
                item_ids[record.canonical_url] = fallback

    link_rows = []
    for record in records:
        record_id = record_ids.get(record.source_item_id)
        item_id = item_ids.get(record.canonical_url)
        if record_id and item_id:
            link_rows.append(
                {
                    "user_id": user,
                    "record_id": record_id,
                    "item_id": item_id,
                    "keyword": keyword,
                    "connector_id": connector.connector_id,
                }
            )
    _post("collector_item_links", link_rows, "record_id,item_id")

    written = {
        **counters,
        "written": len(saved_records),
        "inserted": len(records) - existing_records,
        "updated": existing_records,
    }
    state = {
        "user_id": user,
        "connector_id": connector.connector_id,
        "scope_key": scope_key(keyword),
        "cursor": cursor or {},
        "last_run_at": now,
        "last_status": "ok",
        "last_error": None,
        "counters": written,
    }
    _post("collector_state", [state], "user_id,connector_id,scope_key")
    return written


def load_state(connector_id: str, keyword: str) -> dict | None:
    if not db.configured():
        return None
    user = db.user_id()
    rows = (
        db._request(
            "GET",
            "collector_state?select=*"
            f"&user_id=eq.{quote(user)}"
            f"&connector_id=eq.{quote(connector_id)}"
            f"&scope_key=eq.{quote(scope_key(keyword))}"
            "&limit=1",
        )
        or []
    )
    return rows[0] if rows else None
