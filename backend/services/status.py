from __future__ import annotations

import db
import runtime
from runtime import APP_VERSION, DATA, ROOT, atomic_write, load_json, now_iso

from services.items import load_archive, load_trash


def log_source(src: str, ok: bool, count: int, error: str = "") -> None:
    log = load_json(runtime.SOURCE_LOG_FILE, {})
    if not isinstance(log, dict):
        log = {}
    log[src] = {"at": now_iso(), "ok": ok, "count": count, "error": error[:300]}
    atomic_write(runtime.SOURCE_LOG_FILE, log)


def status_payload() -> dict:
    items = load_json(runtime.ITEMS_FILE, [])
    if not isinstance(items, list):
        items = []
    data_bytes = (
        sum(p.stat().st_size for p in DATA.glob("*.json") if p.is_file()) if DATA.is_dir() else 0
    )
    assets = list(runtime.ASSETS.glob("*.jpg")) if runtime.ASSETS.is_dir() else []
    return {
        "app_version": APP_VERSION,
        "backend": "supabase" if db.configured() else "json",
        "items": len(items),
        "archived": len(load_archive()),
        "keywords": len(
            {i.get("keyword") for i in items if isinstance(i, dict) and i.get("keyword")}
        ),
        "data_bytes": data_bytes,
        "assets": len(assets),
        "assets_bytes": sum(p.stat().st_size for p in assets),
        "trash_count": len(load_trash()),
        "sources": load_json(runtime.SOURCE_LOG_FILE, {}),
        "sessions": {k: (ROOT / "sessions" / k).is_dir() for k in ("tiktok", "facebook")},
    }


def keyword_list() -> dict:
    """2.6 keyword suggestions: count + last fetch date, from items + archive."""
    pool = [i for i in load_json(runtime.ITEMS_FILE, []) if isinstance(i, dict)]
    pool += [a for a in load_archive() if isinstance(a, dict)]
    agg: dict[str, dict] = {}
    for item in pool:
        kw = str(item.get("keyword") or "").strip()
        if not kw:
            continue
        entry = agg.setdefault(kw, {"keyword": kw, "count": 0, "last_at": ""})
        entry["count"] += 1
        at = str(item.get("created_at") or item.get("archived_at") or "")
        if at and at > entry["last_at"]:
            entry["last_at"] = at
    return {"keywords": sorted(agg.values(), key=lambda k: (-k["count"], k["keyword"]))}
