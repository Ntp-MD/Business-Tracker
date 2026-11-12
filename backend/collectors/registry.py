"""Connector allowlist. Only enabled connectors may be collected.

No adapter is enabled right now: Hacker News was removed on 2026-11-12. Future
adapters stay disabled until access, rights and quality rules are approved.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Connector:
    connector_id: str
    source: str
    scope: str
    record_kind: str
    enabled: bool
    dry_run: bool
    rights: str
    languages: tuple[str, ...] = ("th", "en")
    max_age_days: int = 90


CONNECTORS: dict[str, Connector] = {
    "google_trends_th": Connector(
        connector_id="google_trends_th",
        source="google_trends",
        scope="country",
        record_kind="signal",
        enabled=False,
        dry_run=True,
        rights="review",
    ),
    "gdelt_doc": Connector(
        connector_id="gdelt_doc",
        source="gdelt",
        scope="keyword",
        record_kind="content",
        enabled=False,
        dry_run=True,
        rights="review",
    ),
    "bluesky_search": Connector(
        connector_id="bluesky_search",
        source="bluesky",
        scope="keyword",
        record_kind="content",
        enabled=False,
        dry_run=True,
        rights="review",
    ),
    "youtube_search": Connector(
        connector_id="youtube_search",
        source="youtube",
        scope="keyword",
        record_kind="content",
        enabled=False,
        dry_run=True,
        rights="existing",
    ),
    "gnews_search": Connector(
        connector_id="gnews_search",
        source="gnews",
        scope="keyword",
        record_kind="content",
        enabled=False,
        dry_run=True,
        rights="existing",
    ),
    "tiktok_search": Connector(
        connector_id="tiktok_search",
        source="tiktok",
        scope="keyword",
        record_kind="content",
        enabled=False,
        dry_run=True,
        rights="existing",
    ),
    "fbads_library": Connector(
        connector_id="fbads_library",
        source="fbads",
        scope="keyword",
        record_kind="content",
        enabled=False,
        dry_run=True,
        rights="existing",
    ),
    "ttads_creative": Connector(
        connector_id="ttads_creative",
        source="ttads",
        scope="keyword",
        record_kind="content",
        enabled=False,
        dry_run=True,
        rights="existing",
    ),
}


def get_connector(connector_id: str) -> Connector:
    try:
        return CONNECTORS[connector_id]
    except KeyError as exc:
        raise ValueError(f"unknown connector: {connector_id}") from exc
