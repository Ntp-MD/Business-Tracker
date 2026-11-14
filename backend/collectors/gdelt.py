"""GDELT DOC 2.0 adapter. Public metadata only; no article body is fetched."""

from __future__ import annotations

import hashlib
import time
import urllib.parse
from datetime import datetime, timezone

from .contract import RawRecord
from .http import TransportError, fetch_json
from .registry import Connector

API = "https://api.gdeltproject.org/api/v2/doc/doc"
TIMESPAN = "1d"
MAX_RECORDS = 250
RETRY_SECONDS = 6
TIMEOUT_SECONDS = 30  # the public endpoint is slow under load; 15 s times out


def _fetch(url: str) -> dict:
    try:
        return fetch_json(url, timeout=TIMEOUT_SECONDS)
    except TransportError:
        # GDELT throttles bursts and drops slow connections; one retry rides out both
        # without masking a persistent failure.
        time.sleep(RETRY_SECONDS)
        return fetch_json(url, timeout=TIMEOUT_SECONDS)


def _seen(value: object) -> str | None:
    try:
        parsed = datetime.strptime(str(value or ""), "%Y%m%dT%H%M%SZ")
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc).isoformat()


def _query(keyword: str) -> str:
    """Exact-phrase search. Quotes inside the keyword are dropped so it cannot inject
    GDELT operators (sourcelang:, domain:, ...) into the query.

    A one-word keyword also uses GDELT's repeat operator so a page that merely mentions
    the token once (site metadata, boilerplate) does not count as coverage.
    """
    phrase = " ".join(keyword.split()).replace('"', "")
    query = f'"{phrase}"'
    if " " not in phrase:
        query += f' repeat2:"{phrase}"'
    return query


def fetch(keyword: str, limit: int, connector: Connector) -> list[RawRecord]:
    query = urllib.parse.urlencode(
        {
            "query": _query(keyword),
            "mode": "artlist",
            "format": "json",
            "maxrecords": min(max(limit, 1), MAX_RECORDS),
            "timespan": TIMESPAN,
            "sort": "hybridrel",
        }
    )
    payload = _fetch(f"{API}?{query}")
    records: list[RawRecord] = []
    for article in payload.get("articles") or []:
        url = str(article.get("url") or "").strip()
        if not url:
            continue
        domain = str(article.get("domain") or "").strip()
        records.append(
            RawRecord(
                source=connector.source,
                connector_id=connector.connector_id,
                source_item_id=hashlib.sha256(url.encode()).hexdigest(),
                url=url,
                title=str(article.get("title") or ""),
                author_id=domain or None,
                author_display=domain,
                published_at=_seen(article.get("seendate")),
                engagement={},
                numeric_signal=None,
                signal_unit=None,
                raw_source_ref={
                    "domain": domain,
                    "language": article.get("language"),
                    "sourcecountry": article.get("sourcecountry"),
                },
            )
        )
    return records
