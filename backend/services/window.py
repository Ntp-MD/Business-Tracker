"""Fetch-window timestamp helpers shared by collectors and item services."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

AGE_UNITS = {
    "second": 0,
    "sec": 0,
    "minute": 0,
    "min": 0,
    "hour": 0,
    "hr": 0,
    "day": 1,
    "week": 7,
    "month": 30,
    "year": 365,
    "วินาที": 0,
    "วิ": 0,
    "นาที": 0,
    "ชั่วโมง": 0,
    "ชม": 0,
    "วัน": 1,
    "สัปดาห์": 7,
    "เดือน": 30,
    "ปี": 365,
}


def parse_age_days(text: str):
    """'2 days ago' / '3 สัปดาห์ที่แล้ว' -> 21 days. None when unparseable."""
    if not text:
        return None
    m = re.search(r"(\d+)\s*([A-Za-z\u0E00-\u0E7F]+)", str(text).lower())
    if not m:
        return None
    unit = m.group(2)
    for key, days in AGE_UNITS.items():
        if unit.startswith(key):
            return int(m.group(1)) * days
    return None


def iso_days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def cutoff_iso(max_age_days: int):
    if max_age_days <= 0:
        return None
    return iso_days_ago(max_age_days)


def older_than(published: str, cutoff) -> bool:
    """True only when both timestamps exist and published < cutoff."""
    if not cutoff or not published:
        return False
    try:
        dt = datetime.fromisoformat(published)
    except (TypeError, ValueError):
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt < datetime.fromisoformat(cutoff)
