"""Hacker News search adapter (metadata only; no article bodies)."""

from __future__ import annotations

from urllib.parse import quote

from .contract import RawRecord
from .http import TransportError, fetch_json
from .registry import Connector

HN_ENDPOINT = "https://hn.algolia.com/api/v1/search_by_date"


def parse_hits(payload: dict, connector: Connector) -> list[RawRecord]:
    hits = payload.get("hits")
    if not isinstance(hits, list):
        raise TransportError("malformed HN response: hits")

    records: list[RawRecord] = []
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        source_item_id = str(hit.get("objectID") or "")
        external_url = hit.get("url") if isinstance(hit.get("url"), str) else ""
        discussion_url = f"https://news.ycombinator.com/item?id={quote(source_item_id)}"
        records.append(
            RawRecord(
                source=connector.source,
                connector_id=connector.connector_id,
                source_item_id=source_item_id,
                url=external_url or discussion_url,
                title=str(hit.get("title") or ""),
                author_id=str(hit.get("author") or "") or None,
                author_display=str(hit.get("author") or ""),
                published_at=str(hit.get("created_at") or "") or None,
                engagement={
                    "points": hit.get("points"),
                    "comments": hit.get("num_comments"),
                },
                numeric_signal=hit.get("points"),
                signal_unit="points",
                raw_source_ref={
                    "objectID": source_item_id,
                    "created_at": hit.get("created_at"),
                    "points": hit.get("points"),
                    "num_comments": hit.get("num_comments"),
                },
            )
        )
    return records


def fetch(keyword: str, limit: int = 50, connector: Connector | None = None) -> list[RawRecord]:
    if connector is None:
        raise ValueError("connector is required")
    url = f"{HN_ENDPOINT}?query={quote(keyword)}&tags=story&hitsPerPage={max(1, min(limit, 100))}"
    return parse_hits(fetch_json(url), connector)
