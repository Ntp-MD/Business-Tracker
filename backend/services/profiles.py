from __future__ import annotations

import threading

import runtime
from runtime import load_json, now_iso

from services.items import analyze, merge_items
from services.sources import COLLECTORS
from services.status import log_source


def load_profiles() -> list:
    data = load_json(runtime.PROFILES_FILE, [])
    return data if isinstance(data, list) else []


def validate_profile(name, keywords, sources):
    name = str(name or "").strip()
    cleaned_kw, seen = [], set()
    for kw in keywords or []:
        kw = str(kw).strip()
        if kw and kw not in seen:
            seen.add(kw)
            cleaned_kw.append(kw)
    cleaned_src, seen_s = [], set()
    for s in sources or []:
        s = str(s).strip().lower()
        if s and s not in seen_s:
            seen_s.add(s)
            cleaned_src.append(s)
    if not name:
        return None, "missing name"
    if not cleaned_kw:
        return None, "missing keywords"
    if not cleaned_src:
        cleaned_src = ["youtube"]
    return {"name": name, "keywords": cleaned_kw, "sources": cleaned_src}, None


def fetch_profile(
    prof: dict,
    mode: str = "public",
    max_age_days: int = 0,
    cancel: threading.Event | None = None,
) -> dict:
    """Run every keyword x source in the profile (manual trigger, sequential). mode=public|session for TikTok/FB."""
    total_added, total_skipped, all_errors, per_keyword = 0, 0, [], []
    cancelled = False
    cancel = cancel or threading.Event()
    kws = prof["keywords"]
    for i, kw in enumerate(kws):
        if cancel.is_set():
            cancelled = True
            break
        runtime.progress_set(keyword=kw, done=i, total=len(kws), source="", stage="next keyword")
        kw_new, kw_errors = [], []
        for src in prof["sources"]:
            if cancel.is_set():
                cancelled = True
                break
            fn = COLLECTORS.get(src)
            if fn is None:
                kw_errors.append(f"{kw} {src}: not implemented yet")
                continue
            runtime.progress_set(source=src, stage="starting")
            if src == "tiktok":
                items, errs = fn(kw, mode, max_age_days)
            else:
                items, errs = fn(kw, max_age_days)
            log_source(src, not errs, len(items), "; ".join(errs))
            kw_new += items
            kw_errors += errs
        if cancelled:
            break
        added, skipped, thumb_errors = merge_items(kw_new, kw, max_age_days)
        kw_errors += thumb_errors
        kw_out = analyze(kw, write=True)
        total_added += added
        total_skipped += skipped
        all_errors += [f"[{kw}] {e}" for e in kw_errors]
        per_keyword.append(
            {
                "keyword": kw,
                "added": added,
                "duplicates": skipped,
                "errors": kw_errors,
                "total": kw_out["total"],
                "by_source": kw_out["by_source"],
            }
        )
    return {
        "keyword": prof["name"],
        "per_keyword": per_keyword,
        "added": total_added,
        "duplicates": total_skipped,
        "errors": all_errors,
        "fetched_at": now_iso(),
        "max_age_days": max_age_days,
        "cancelled": cancelled,
    }
