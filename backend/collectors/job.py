"""Validation for the `collect` job payload. No storage access."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .registry import Connector, get_connector
from .store import writes_enabled

ALLOWED_FIELDS = {
    "connector_id",
    "scope",
    "mode",
    "dry_run",
    "max_records",
    "quality_rules_version",
}
ALLOWED_MODES = {"manual", "scheduled"}


def validate_collect_payload(
    payload: Any, connector_lookup: Callable[[str], Connector] = get_connector
) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    unknown = set(payload) - ALLOWED_FIELDS
    if unknown:
        raise ValueError(f"unknown payload fields: {', '.join(sorted(unknown))}")

    connector_id = str(payload.get("connector_id") or "").strip()
    connector = connector_lookup(connector_id)
    if not connector.enabled:
        raise ValueError(f"connector disabled: {connector_id}")
    if connector.scope != "keyword":
        raise ValueError(f"connector scope not supported yet: {connector.scope}")

    scope = payload.get("scope")
    if not isinstance(scope, dict):
        raise ValueError("scope must be an object")
    keyword = str(scope.get("keyword") or "").strip()
    if not keyword or len(keyword) > 120:
        raise ValueError("scope.keyword is required (max 120 chars)")

    mode = str(payload.get("mode") or "manual")
    if mode not in ALLOWED_MODES:
        raise ValueError(f"unknown mode: {mode}")

    dry_run = payload.get("dry_run", True)
    if not isinstance(dry_run, bool):
        raise ValueError("dry_run must be a boolean")
    if not dry_run and not writes_enabled():
        raise ValueError("collector writes are disabled; run with dry_run=true")

    try:
        max_records = int(payload.get("max_records", 50))
    except (TypeError, ValueError) as exc:
        raise ValueError("max_records must be an integer") from exc
    if max_records < 1 or max_records > 100:
        raise ValueError("max_records must be between 1 and 100")

    return {
        "connector_id": connector_id,
        "scope": {"keyword": keyword},
        "mode": mode,
        "dry_run": dry_run,
        "max_records": max_records,
        "quality_rules_version": payload.get("quality_rules_version"),
    }
