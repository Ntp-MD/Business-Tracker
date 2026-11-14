"""Process-wide runtime state: paths, env, shared locks, progress, cancel, small file helpers."""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import db

ROOT = Path(__file__).resolve().parent.parent


STATIC = ROOT / "legacy"


APP = STATIC / "app"


LIVE = STATIC / "live"


DATA = ROOT / "data"


ASSETS = STATIC / "assets"


ITEMS_FILE = DATA / "items.json"


INDEX_FILE = DATA / "index.json"


ANALYSIS_FILE = DATA / "analysis.json"


PROFILES_FILE = DATA / "profiles.json"


SOURCE_LOG_FILE = DATA / "sources.json"


ARCHIVE_FILE = DATA / "archive.json"


TRASH_FILE = DATA / "trash.json"


APP_VERSION = "0.1"


EXPORT_FORMAT = "social-tracker.items"


EXPORT_VERSION = 1


TRASH_RETENTION_DAYS = 7  # 2.5 auto-purge: trash older than this is dropped at start + after delete


CANCEL_LOCK = threading.Lock()


CANCEL_EVENT = threading.Event()  # event of the fetch currently running


def new_fetch_cancel() -> threading.Event:
    """Fresh event per fetch: an old cancelled run keeps its set event, so it cannot resume."""
    global CANCEL_EVENT
    with CANCEL_LOCK:
        CANCEL_EVENT = threading.Event()
        return CANCEL_EVENT


def cancel_fetch() -> None:
    with CANCEL_LOCK:
        CANCEL_EVENT.set()


UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)


HOST = os.environ.get("HOST", "127.0.0.1")


PORT = int(os.environ.get("PORT", "8000"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_data() -> None:
    DATA.mkdir(exist_ok=True)
    ASSETS.mkdir(exist_ok=True)
    for path, empty in (
        (ITEMS_FILE, []),
        (INDEX_FILE, {}),
        (ANALYSIS_FILE, {}),
        (PROFILES_FILE, []),
        (SOURCE_LOG_FILE, {}),
        (ARCHIVE_FILE, []),
        (TRASH_FILE, []),
    ):
        if not path.exists():
            path.write_text(json.dumps(empty, ensure_ascii=False), encoding="utf-8")
    for orphan in (
        DATA / "items.json.tmp",
        DATA / "index.json.tmp",
        DATA / "analysis.json.tmp",
        DATA / "profiles.json.tmp",
        DATA / "sources.json.tmp",
        DATA / "archive.json.tmp",
        DATA / "trash.json.tmp",
    ):
        orphan.unlink(missing_ok=True)


def atomic_write(path: Path, obj) -> None:
    if db.save(path, obj):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    for attempt in range(6):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(0.15)


def load_json(path: Path, default):
    if db.configured():
        data = db.load(path, default)
        if data is not None:
            return data
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


PW_SESSIONS = ROOT / "sessions"


PW_TIMEOUT_MS = 35000


PW_LIMIT = 12


PW_LOCK = threading.Lock()  # ทีละ 1 รอบ Playwright: กัน thread ชนกันและ profile dir ชนกัน


PROGRESS_LOCK = threading.Lock()


PROGRESS = {
    "active": False,
    "keyword": "",
    "source": "",
    "stage": "",
    "done": 0,
    "total": 0,
    "started": 0.0,
    "updated": 0.0,
}


def progress_set(**kw):
    with PROGRESS_LOCK:
        PROGRESS.update(kw)
        PROGRESS["updated"] = time.time()


def progress_stage(stage: str):
    progress_set(stage=stage)


def progress_get() -> dict:
    with PROGRESS_LOCK:
        out = dict(PROGRESS)
    if out["active"]:
        now = time.time()
        out["elapsed"] = round(now - out["started"], 1)
        out["since_update"] = round(now - out["updated"], 1)
    return out
