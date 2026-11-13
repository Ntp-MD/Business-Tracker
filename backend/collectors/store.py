"""Targeted collector persistence. Disabled unless COLLECTOR_WRITE_ENABLED=1.

No snapshot delete: records, item projections, links and state are upserted by
their stable keys. The migration in supabase/migrations/20261112010000_collectors.sql
must be applied first.

Repeat runs merge: record keywords are unioned, existing items refresh score/metric
only, trashed items are never relinked, and the first link keyword is kept.
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


def _in_list(values: list[str]) -> str:
    # shortcut: one filter per run; max_records caps a run at 100
    return "in.(" + ",".join(f"%22{quote(value, safe='')}%22" for value in values) + ")"


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


def _existing_records(user_id: str, connector: Connector, ids: list[str]) -> dict[str, list[str]]:
    rows = (
        db._request(
            "GET",
            "collector_records?select=source_item_id,keywords_matched"
            f"&user_id=eq.{quote(user_id)}"
            f"&source=eq.{quote(connector.source)}"
            f"&source_item_id={_in_list(ids)}",
        )
        or []
    )
    return {row["source_item_id"]: list(row.get("keywords_matched") or []) for row in rows}


def _existing_items(user_id: str, keyword: str, urls: list[str]) -> dict[str, dict]:
    rows = (
        db._request(
            "GET",
            "items?select=id,canonical_url,deleted_at"
            f"&user_id=eq.{quote(user_id)}"
            f"&keyword=eq.{quote(keyword)}"
            f"&canonical_url={_in_list(urls)}",
        )
        or []
    )
    return {row["canonical_url"]: row for row in rows}


def _record_row(record: CollectorRecord, user_id: str, keywords: list[str]) -> dict:
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
        "keywords_matched": keywords,
        "raw_source_ref": record.raw_source_ref,
        "quality_score": record.quality_score,
        "quality_flags": record.quality_flags,
        "quality_rules_version": record.quality_rules_version,
    }


def _metric(record: CollectorRecord) -> str | None:
    return record.signal_unit if record.signal_unit in {"views", "plays", "likes"} else None


def _item_row(record: CollectorRecord, user_id: str, keyword: str) -> dict:
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
        "metric": _metric(record),
        "views": None,
        "published": record.published_at,
    }


def _projection_row(record: CollectorRecord, user_id: str, keyword: str) -> dict:
    # Only mutable metric columns: never rewrite body/author/channel/archive/trash.
    return {
        "user_id": user_id,
        "keyword": keyword,
        "canonical_url": record.canonical_url,
        "score": int(record.numeric_signal or 0),
        "metric": _metric(record),
    }


def _write_state(
    connector: Connector,
    keyword: str,
    now: str,
    *,
    status: str,
    error: str | None = None,
    counters: dict | None = None,
    cursor: dict | None = None,
) -> None:
    row: dict = {
        "user_id": db.user_id(),
        "connector_id": connector.connector_id,
        "scope_key": scope_key(keyword),
        "last_run_at": now,
        "last_status": status,
        "last_error": error,
    }
    if counters is not None:
        row["counters"] = counters
    if cursor is not None:
        row["cursor"] = cursor
    _post("collector_state", [row], "user_id,connector_id,scope_key")


def _write_outcome(
    connector: Connector,
    keyword: str,
    now: str,
    *,
    ok: bool,
    error: str | None = None,
    counters: dict | None = None,
    cursor: dict | None = None,
) -> None:
    _write_state(
        connector,
        keyword,
        now,
        status="ok" if ok else "error",
        error=error,
        counters=counters,
        cursor=cursor,
    )
    _post(
        "source_status",
        [
            {
                "user_id": db.user_id(),
                "source": connector.source,
                "checked_at": now,
                "ok": ok,
                "count": (counters or {}).get("written", 0),
                "error": error,
            }
        ],
        "user_id,source",
    )


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
    try:
        written = _save_data(connector, keyword, records, counters, user)
    except Exception as exc:  # noqa: BLE001 - record the failure, then re-raise
        try:
            _write_outcome(connector, keyword, now, ok=False, error=str(exc)[:500])
        except Exception:  # noqa: BLE001 - status is best effort; keep the real error
            pass
        raise
    _write_outcome(connector, keyword, now, ok=True, counters=written, cursor=cursor or {})
    return written


def _save_data(
    connector: Connector,
    keyword: str,
    records: list[CollectorRecord],
    counters: dict,
    user: str,
) -> dict:
    ids = [record.source_item_id for record in records]
    existing_records = _existing_records(user, connector, ids) if ids else {}

    record_rows = []
    for record in records:
        prior = existing_records.get(record.source_item_id, [])
        keywords = list(dict.fromkeys([*prior, keyword]))
        record_rows.append(_record_row(record, user, keywords))
    saved_records = _post(
        "collector_records",
        record_rows,
        "user_id,source,source_item_id",
        "id,source_item_id",
    )
    record_ids = {row["source_item_id"]: row["id"] for row in saved_records}

    urls = list({record.canonical_url for record in records})
    existing_items = _existing_items(user, keyword, urls) if urls else {}
    trashed = {url for url, row in existing_items.items() if row.get("deleted_at")}

    new_rows: dict[str, dict] = {}
    for record in records:
        if record.canonical_url not in existing_items:
            new_rows.setdefault(record.canonical_url, _item_row(record, user, keyword))
    inserted_items = _post(
        "items",
        list(new_rows.values()),
        "user_id,keyword,canonical_url",
        "id,canonical_url",
        resolution="ignore-duplicates",
    )
    item_ids = {url: row["id"] for url, row in existing_items.items()}
    item_ids.update({row["canonical_url"]: row["id"] for row in inserted_items})

    projection: dict[str, dict] = {}
    for record in records:
        if record.canonical_url not in trashed:
            projection.setdefault(record.canonical_url, _projection_row(record, user, keyword))
    _post("items", list(projection.values()), "user_id,keyword,canonical_url")

    link_rows = []
    for record in records:
        if record.canonical_url in trashed:
            continue
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
    # ignore-duplicates keeps the first keyword that linked the item
    _post("collector_item_links", link_rows, "record_id,item_id", resolution="ignore-duplicates")

    written = {
        **counters,
        "written": len(saved_records),
        "inserted": len(records) - len(existing_records),
        "updated": len(existing_records),
    }
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
