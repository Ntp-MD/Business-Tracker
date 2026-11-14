"""Google News RSS adapter. Public feed metadata only; no article body is fetched.

Same feed and locale as the legacy `collect_gnews` collector, moved onto the collector
contract so the source has one pipeline. The feed's per-title script decides the language
through the quality gate; nothing is declared here.
"""

from __future__ import annotations

import hashlib
import urllib.parse
import urllib.request
from datetime import timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

from ..contract import RawRecord
from ..http import USER_AGENT, TransportError
from ..registry import Connector

FEED = "https://news.google.com/rss/search"
LOCALE = {"hl": "th", "gl": "TH", "ceid": "TH:th"}
TIMEOUT_SECONDS = 30
MAX_BYTES = 2_000_000


def _fetch(keyword: str) -> bytes:
    url = f"{FEED}?{urllib.parse.urlencode({**LOCALE, 'q': keyword})}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read(MAX_BYTES + 1)
    except Exception as exc:  # noqa: BLE001 - normalize transport failures
        raise TransportError(str(exc)) from exc
    if len(body) > MAX_BYTES:
        raise TransportError("response too large")
    return body


def _published(value: str) -> str | None:
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def fetch(keyword: str, limit: int, connector: Connector) -> list[RawRecord]:
    body = _fetch(keyword)
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError as exc:
        raise TransportError("invalid RSS") from exc

    records: list[RawRecord] = []
    seen: set[str] = set()
    for item in root.iter("item"):
        if len(records) >= limit:
            break
        url = (item.findtext("link") or "").strip()
        title = (item.findtext("title") or "").strip()
        if not url or not title or url in seen:
            continue
        seen.add(url)
        source_el = item.find("source")
        channel = (source_el.text or "").strip() if source_el is not None else ""
        channel_url = (source_el.get("url") or "").strip() if source_el is not None else ""
        records.append(
            RawRecord(
                source=connector.source,
                connector_id=connector.connector_id,
                source_item_id=hashlib.sha256(url.encode()).hexdigest(),
                url=url,
                title=title,
                author_id=channel_url or None,
                author_display=channel,
                published_at=_published(item.findtext("pubDate") or ""),
                engagement={},
                numeric_signal=None,
                signal_unit=None,
                raw_source_ref={"channel": channel, "channel_url": channel_url},
            )
        )
    return records
