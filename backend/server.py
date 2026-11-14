#!/usr/bin/env python3
"""TrendRail collector API and legacy static server — entrypoint.

Stdlib only. Binds 127.0.0.1:8000.

The HTTP handler lives in `api/server.py`; item, archive, profile, and status services in
`services/`; legacy source collectors in `services/sources.py`; process state (paths, env,
locks, progress, cancel) in `runtime.py`. This module keeps the documented
`python backend/server.py` command and re-exports the service surface the tests use.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import db
import runtime
from api.server import Handler, main
from runtime import (
    APP_VERSION,
    EXPORT_FORMAT,
    EXPORT_VERSION,
    HOST,
    PORT,
    TRASH_RETENTION_DAYS,
    atomic_write,
    load_json,
    now_iso,
)
from services.items import (
    archive_items,
    bulk_items,
    canonical_url,
    clear_all_data,
    clear_keyword,
    create_item,
    delete_item,
    export_payload,
    import_payload,
    load_archive,
    load_trash,
    merge_items,
    prune_old,
    purge_trash,
    refresh_stats,
    restore_archived,
    restore_trash,
    update_item,
)
from services.sources import youtube_video_stats
from services.status import keyword_list

__all__ = [
    "APP_VERSION",
    "EXPORT_FORMAT",
    "EXPORT_VERSION",
    "HOST",
    "Handler",
    "PORT",
    "TRASH_RETENTION_DAYS",
    "archive_items",
    "atomic_write",
    "bulk_items",
    "canonical_url",
    "clear_all_data",
    "clear_keyword",
    "create_item",
    "datetime",
    "db",
    "delete_item",
    "export_payload",
    "import_payload",
    "keyword_list",
    "load_archive",
    "load_json",
    "load_trash",
    "main",
    "merge_items",
    "now_iso",
    "prune_old",
    "purge_trash",
    "refresh_stats",
    "restore_archived",
    "restore_trash",
    "runtime",
    "timedelta",
    "timezone",
    "update_item",
    "youtube_video_stats",
]


if __name__ == "__main__":
    main()
