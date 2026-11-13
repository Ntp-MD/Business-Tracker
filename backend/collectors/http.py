"""Bounded HTTP helper for collectors: timeouts, size caps, safe hosts, JSON only."""

from __future__ import annotations

import ipaddress
import json
import urllib.request
from urllib.parse import urlparse

USER_AGENT = "TrendRailCollector/0.2 (+https://trendrail.vercel.app)"
MAX_BYTES = 2_000_000
TIMEOUT_SECONDS = 15


class TransportError(RuntimeError):
    """Transport-level failure; the gate reports this as transport_error."""


def _blocked_host(host: str | None) -> bool:
    if not host:
        return True
    name = host.lower()
    if name in {"localhost", "localhost.localdomain"}:
        return True
    try:
        address = ipaddress.ip_address(name)
    except ValueError:
        return False
    return address.is_private or address.is_loopback or address.is_link_local or address.is_reserved


def fetch_json(
    url: str,
    *,
    timeout: int = TIMEOUT_SECONDS,
    max_bytes: int = MAX_BYTES,
) -> dict:
    parsed = urlparse(url)
    if parsed.scheme not in {"https", "http"} or _blocked_host(parsed.hostname):
        raise TransportError("blocked URL")

    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if _blocked_host(urlparse(response.geturl()).hostname):
                raise TransportError("blocked redirect")
            if response.headers.get_content_type() != "application/json":
                raise TransportError("unexpected content type")
            body = response.read(max_bytes + 1)
    except TransportError:
        raise
    except Exception as exc:  # noqa: BLE001 - normalize urllib errors
        raise TransportError(str(exc)) from exc

    if len(body) > max_bytes:
        raise TransportError("response too large")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise TransportError("invalid JSON") from exc
    if not isinstance(payload, dict):
        raise TransportError("JSON root is not an object")
    return payload
