"""Pre-write quality gate: normalize, validate, dedupe, flag. No storage access."""

from __future__ import annotations

import hashlib
import html
import math
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .contract import (
    QUALITY_RULES_VERSION,
    CollectorRecord,
    GateOutcome,
    RawRecord,
    Rejection,
    utc_now,
)
from .http import _blocked_host
from .registry import Connector

TRACKING_PARAMS = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}

SPAM_PHRASES = (
    "casino bonus",
    "crypto giveaway",
    "earn money fast",
    "free followers",
    "viagra",
    "work from home and earn",
)

CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
HTML_TAG = re.compile(r"<[^>]+>")
SPACE = re.compile(r"\s+")


def clean_text(value: object) -> str:
    text = html.unescape(str(value or ""))
    text = HTML_TAG.sub(" ", text)
    text = CONTROL_CHARS.sub("", text)
    return SPACE.sub(" ", text).strip()


def canonicalize_url(value: str) -> str:
    parts = urlsplit(value.strip())
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("bad_url")
    if _blocked_host(parts.hostname):
        raise ValueError("bad_url")
    query = [
        (key, val)
        for key, val in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMS
    ]
    netloc = parts.hostname.lower()
    if parts.port and parts.port not in {80, 443}:
        netloc = f"{netloc}:{parts.port}"
    return urlunsplit(
        (parts.scheme.lower(), netloc, parts.path or "/", urlencode(sorted(query)), "")
    )


def detect_language(text: str) -> str:
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return "unknown"
    thai = sum(1 for char in letters if "\u0e00" <= char <= "\u0e7f")
    latin = sum(1 for char in letters if char.isascii())
    other = len(letters) - thai - latin
    if thai and thai >= latin:
        return "th"
    if latin and latin >= max(1, other):
        return "en"
    return "other"


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _valid_metric(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(value) and value >= 0


def _soft_flags(title: str) -> list[str]:
    flags: list[str] = []
    if len(title) < 15:
        flags.append("short_title")
    letters = [char for char in title if char.isalpha()]
    if len(letters) >= 10 and sum(char.isupper() for char in letters) / len(letters) > 0.7:
        flags.append("all_caps")
    return flags


def gate(
    raw_records: list[RawRecord], connector: Connector, *, now: datetime | None = None
) -> GateOutcome:
    now = now or utc_now()
    accepted: list[CollectorRecord] = []
    rejected: list[Rejection] = []
    quarantined: list[Rejection] = []
    duplicates = 0
    seen: set[str] = set()

    for raw in raw_records:
        source_item_id = clean_text(raw.source_item_id)
        if not source_item_id:
            rejected.append(Rejection(raw, "missing_identity"))
            continue
        if source_item_id in seen:
            duplicates += 1
            continue
        seen.add(source_item_id)

        title = clean_text(raw.title)
        if not title:
            rejected.append(Rejection(raw, "malformed"))
            continue

        try:
            canonical_url = canonicalize_url(raw.url)
        except ValueError:
            rejected.append(Rejection(raw, "bad_url"))
            continue

        published = parse_timestamp(raw.published_at)
        if raw.published_at and published is None:
            rejected.append(Rejection(raw, "malformed"))
            continue
        if published and published > now + timedelta(minutes=5):
            rejected.append(Rejection(raw, "out_of_window"))
            continue
        if published and published < now - timedelta(days=connector.max_age_days):
            rejected.append(Rejection(raw, "out_of_window"))
            continue

        language = detect_language(title)
        if language not in connector.languages:
            rejected.append(Rejection(raw, "unsupported_language"))
            continue

        lowered = title.lower()
        if any(phrase in lowered for phrase in SPAM_PHRASES):
            rejected.append(Rejection(raw, "spam"))
            continue

        metrics = [raw.numeric_signal, *raw.engagement.values()]
        if not all(_valid_metric(value) for value in metrics):
            rejected.append(Rejection(raw, "metric_invalid"))
            continue

        flags = _soft_flags(title)
        record = CollectorRecord(
            source=raw.source,
            connector_id=raw.connector_id,
            source_item_id=source_item_id,
            record_kind=connector.record_kind,
            content_type="story",
            url=raw.url,
            canonical_url=canonical_url,
            title=title,
            author_id=raw.author_id,
            author_display=clean_text(raw.author_display),
            language=language,
            published_at=published.isoformat() if published else None,
            observed_at=now.isoformat(),
            engagement=dict(raw.engagement),
            numeric_signal=raw.numeric_signal,
            signal_unit=raw.signal_unit,
            quality_score=max(40, 100 - 15 * len(flags)),
            quality_flags=flags,
            quality_rules_version=QUALITY_RULES_VERSION,
            content_hash=hashlib.sha256(f"{title}\n{canonical_url}".encode()).hexdigest(),
            raw_source_ref=dict(raw.raw_source_ref),
        )
        if flags:
            quarantined.append(Rejection(raw, "quarantine"))
        else:
            accepted.append(record)

    return GateOutcome(
        accepted=accepted,
        rejected=rejected,
        quarantined=quarantined,
        duplicates=duplicates,
    )
