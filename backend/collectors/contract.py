"""Shared collector contracts. Stdlib only; no storage access lives here."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

QUALITY_RULES_VERSION = "2026-11-12.1"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class RawRecord:
    source: str
    connector_id: str
    source_item_id: str
    url: str
    title: str
    author_id: str | None = None
    author_display: str = ""
    published_at: str | None = None
    engagement: dict[str, Any] = field(default_factory=dict)
    numeric_signal: float | None = None
    signal_unit: str | None = None
    raw_source_ref: dict[str, Any] = field(default_factory=dict)


@dataclass
class CollectorRecord:
    source: str
    connector_id: str
    source_item_id: str
    record_kind: str
    content_type: str
    url: str
    canonical_url: str
    title: str
    author_id: str | None
    author_display: str
    language: str
    published_at: str | None
    observed_at: str
    engagement: dict[str, Any]
    numeric_signal: float | None
    signal_unit: str | None
    quality_score: int
    quality_flags: list[str]
    quality_rules_version: str
    content_hash: str
    raw_source_ref: dict[str, Any]


@dataclass
class Rejection:
    raw: RawRecord
    reason: str


@dataclass
class GateOutcome:
    accepted: list[CollectorRecord]
    rejected: list[Rejection]
    quarantined: list[Rejection]
    duplicates: int

    def counters(self, fetched: int) -> dict[str, Any]:
        by_reason: dict[str, int] = {}
        for item in self.rejected:
            by_reason[item.reason] = by_reason.get(item.reason, 0) + 1
        return {
            "fetched": fetched,
            "parsed": fetched,
            "accepted": len(self.accepted),
            "rejected": by_reason,
            "rejected_total": len(self.rejected),
            "duplicates": self.duplicates,
            "quarantined": len(self.quarantined),
            "inserted": 0,
            "updated": 0,
        }
