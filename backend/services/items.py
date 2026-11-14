from __future__ import annotations

import io
import json
import re
import threading
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import runtime
from runtime import (
    APP_VERSION,
    EXPORT_FORMAT,
    EXPORT_VERSION,
    TRASH_RETENTION_DAYS,
    atomic_write,
    load_json,
    now_iso,
)

from services.sources import COLLECTORS, save_thumbnail, youtube_video_stats
from services.window import cutoff_iso, older_than

EN_STOP = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "are",
    "will",
    "have",
    "what",
    "when",
    "your",
    "you",
    "our",
    "into",
    "more",
    "than",
    "then",
    "them",
    "they",
    "about",
    "which",
    "their",
    "there",
}

SUGGESTIONS = [
    "30-sec clip: open on the pain behind {q}, demo the fix, close with one LINE CTA.",
    'SEO post: answer "{q}" in one clear headline + hashtags + a single CTA.',
    "3-part FAQ: three shorts answering the most-asked questions about {q}.",
]

DATED_SOURCES = {"youtube", "gnews", "tiktok"}  # ads are current by definition

ORGANIC_SOURCES = {
    "youtube",
    "gnews",
    "tiktok",
}  # same title = same content; ads may reuse copy

TRACKING_KEYS = (
    "utm_",
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "ref",
    "si",
    "feature",
    "share_",
    "is_from_webapp",
    "sender_device",
    "sender_web_id",
    "oc",
)

NEAR_DUP_THRESHOLD = 0.9

METRICS = {"views", "plays", "likes", "none"}


def infer_metric(source: str) -> str:
    if source == "youtube":
        return "views"
    if source == "tiktok":
        return "plays"
    if source == "ttads":
        return "likes"
    return "none"


def backfill_item(item: dict) -> bool:
    """Add views/metric/channel_url to items collected before these fields existed."""
    if not isinstance(item, dict):
        return False
    changed = False
    metric = item.get("metric")
    if metric not in METRICS:
        item["metric"] = infer_metric(str(item.get("source") or ""))
        changed = True
    if "views" not in item:
        score = int(item.get("score") or 0)
        item["views"] = score if item["metric"] in ("views", "plays") else None
        changed = True
    if "channel_url" not in item:
        author = str(item.get("author") or "")
        item["channel_url"] = (
            f"https://www.tiktok.com/@{author}" if item.get("source") == "tiktok" and author else ""
        )
        changed = True
    return changed


def migrate_items() -> bool:
    items = load_json(runtime.ITEMS_FILE, [])
    if not isinstance(items, list):
        return False
    changed = False
    for item in items:
        changed = backfill_item(item) or changed
    if changed:
        atomic_write(runtime.ITEMS_FILE, items)
    return changed


def canonical_url(url: str) -> str:
    """Stable identity for a link: drops tracking params, unifies share/short forms."""
    raw = (url or "").strip()
    if not raw:
        return ""
    try:
        parts = urllib.parse.urlsplit(raw)
    except ValueError:
        return raw
    host = (parts.hostname or "").lower()
    for prefix in ("www.", "m."):
        if host.startswith(prefix):
            host = host[len(prefix) :]
    path = re.sub(r"/+$", "", parts.path) or "/"
    query = [
        (k, v)
        for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=False)
        if not k.lower().startswith(TRACKING_KEYS)
    ]
    if host == "youtu.be":
        vid = path.strip("/").split("/")[0]
        if vid:
            return f"https://www.youtube.com/watch?v={vid}"
    if host == "youtube.com":
        qd = dict(query)
        if qd.get("v"):
            return f"https://www.youtube.com/watch?v={qd['v']}"
        m = re.match(r"/(?:shorts|live|embed)/([^/]+)", path)
        if m:
            return f"https://www.youtube.com/watch?v={m.group(1)}"
    if host == "facebook.com" and path.startswith("/ads/library"):
        qd = dict(query)
        if qd.get("id"):
            return f"https://www.facebook.com/ads/library/?id={qd['id']}"
    if host == "tiktok.com" or host.endswith(".tiktok.com"):
        m = re.search(r"/video/(\d+)", path)
        if m:
            return f"https://www.tiktok.com/video/{m.group(1)}"
    clean_query = urllib.parse.urlencode(sorted(query))
    return urllib.parse.urlunsplit(("https", host or parts.netloc.lower(), path, clean_query, ""))


def norm_title(title: str) -> str:
    """Case/punctuation/space-insensitive title used for duplicate checks."""
    text = unicodedata.normalize("NFKC", title or "").casefold()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def title_trigrams(norm: str) -> set[str]:
    flat = norm.replace(" ", "")
    return {flat[i : i + 3] for i in range(len(flat) - 2)} if len(flat) >= 3 else {flat}


def near_dup(norm: str, pool: list[set[str]], threshold: float = NEAR_DUP_THRESHOLD) -> bool:
    if len(norm) < 20:
        return False
    grams = title_trigrams(norm)
    for other in pool:
        inter = len(grams & other)
        if not inter:
            continue
        union = len(grams) + len(other) - inter
        if union and inter / union >= threshold:
            return True
    return False


def merge_items(
    new_items: list, keyword: str = "", max_age_days: int = 0, fetch_thumbs: bool = True
) -> tuple[int, int, list[str]]:
    """Store new items with 3 dedup layers inside one keyword: canonical URL, title key,
    near-duplicate (organic only). Same URL under another keyword is allowed (coverage).
    Returns (added, skipped_duplicates, errors)."""
    errors: list[str] = []
    existing = load_json(runtime.ITEMS_FILE, [])
    if not isinstance(existing, list):
        existing = []
    if max_age_days > 0 and keyword:
        cutoff = cutoff_iso(max_age_days)
        existing = [
            i
            for i in existing
            if not (
                isinstance(i, dict)
                and i.get("keyword") == keyword
                and i.get("source") in DATED_SOURCES
                and older_than(i.get("published") or "", cutoff)
            )
        ]
    known_urls = {
        canonical_url(i.get("url") or "")
        for i in existing
        if isinstance(i, dict) and (not keyword or i.get("keyword") == keyword)
    }
    for item in existing:
        if isinstance(item, dict):
            if item.get("url") and not item.get("canonical_url"):
                item["canonical_url"] = canonical_url(item["url"])
            backfill_item(item)
    known_titles: set[tuple[str, str]] = set()
    title_pools: dict[str, list[set[str]]] = {}
    for item in existing:
        if not isinstance(item, dict) or item.get("source") not in ORGANIC_SOURCES:
            continue
        if keyword and item.get("keyword") != keyword:
            continue
        norm = norm_title(item.get("title") or "")
        if norm:
            known_titles.add((item["source"], norm))
            title_pools.setdefault(item["source"], []).append(title_trigrams(norm))
    added_items, skipped = [], 0
    for it in new_items:
        url_key = canonical_url(it.get("url") or "")
        norm = norm_title(it.get("title") or "") if it.get("source") in ORGANIC_SOURCES else ""
        if not url_key or url_key in known_urls:
            skipped += 1
            continue
        if norm and (it["source"], norm) in known_titles:
            skipped += 1
            continue
        if norm and near_dup(norm, title_pools.get(it["source"], [])):
            skipped += 1
            continue
        known_urls.add(url_key)
        it["canonical_url"] = url_key
        if norm:
            known_titles.add((it["source"], norm))
            title_pools.setdefault(it["source"], []).append(title_trigrams(norm))
        added_items.append(it)
    for it in added_items:
        if fetch_thumbs and it.get("source") == "youtube":
            qd = urllib.parse.parse_qs(
                urllib.parse.urlsplit(it.get("canonical_url") or it["url"]).query
            )
            vid = (qd.get("v") or [""])[0] or it["url"].split("v=", 1)[-1]
            if not save_thumbnail(vid):
                it["asset"] = None
                errors.append(f"youtube thumb {vid}: failed")
    atomic_write(runtime.ITEMS_FILE, existing + added_items)
    rebuild_index(existing + added_items)
    return len(added_items), skipped, errors


def top_terms(items: list) -> list:
    words = []
    for it in items:
        text = ((it.get("title") or "") + " " + (it.get("body") or "")).lower()
        for w in re.split(r"\s+", text):
            w = w.strip(".,:;()\"'[]*").strip()
            if len(w) >= 4 and w not in EN_STOP:
                words.append(w)
    return [[w, n] for w, n in Counter(words).most_common(12)]


def analyze(q: str, write: bool = False) -> dict:
    all_items = load_json(runtime.ITEMS_FILE, [])
    if not isinstance(all_items, list):
        all_items = []
    if q:
        items = [i for i in all_items if isinstance(i, dict) and i.get("keyword") == q]
    else:
        items = [i for i in all_items if isinstance(i, dict)]  # empty q = whole local store
    items.sort(key=lambda i: +i.get("score") or 0, reverse=True)
    by_source = dict(Counter(i.get("source") or "" for i in items))
    hot = items[0].get("title", "") if items else ""
    out = {
        "keyword": q,
        "total": len(items),
        "by_source": by_source,
        "items": items,
        "hot": hot,
        "top_terms": top_terms(items[:100]),
        "suggestions": ([s.format(q=q) for s in SUGGESTIONS] if q else []),
    }
    if write and q:
        prev = load_json(runtime.ANALYSIS_FILE, {})
        if not isinstance(prev, dict):
            prev = {}
        prev[q] = {k: v for k, v in out.items() if k != "items"}  # items already live in items.json
        atomic_write(runtime.ANALYSIS_FILE, prev)
    return out


def rebuild_index(items: list) -> None:
    by_keyword: dict[str, list] = {}
    for it in items:
        if isinstance(it, dict) and it.get("keyword"):
            by_keyword.setdefault(it["keyword"], []).append(it)
    index = {}
    for kw, kw_items in by_keyword.items():
        kw_items = sorted(kw_items, key=lambda i: +i.get("score") or 0, reverse=True)
        index[kw] = {
            "total": len(kw_items),
            "by_source": dict(Counter(i.get("source") or "" for i in kw_items)),
            "hot": kw_items[0].get("title", "") if kw_items else "",
            "top_terms": top_terms(kw_items[:100]),
        }
    atomic_write(runtime.INDEX_FILE, index)


def export_payload(q: str = "") -> dict:
    items = [i for i in load_json(runtime.ITEMS_FILE, []) if isinstance(i, dict)]
    archive = [a for a in load_archive() if isinstance(a, dict)]
    trash = [t for t in load_trash() if isinstance(t, dict)]
    if q:
        items = [i for i in items if i.get("keyword") == q]
        archive = [a for a in archive if a.get("keyword") == q]
        trash = [t for t in trash if t.get("keyword") == q]
    for item in items + archive + trash:
        if item.get("url") and not item.get("canonical_url"):
            item["canonical_url"] = canonical_url(item["url"])
    keywords = sorted({i.get("keyword") for i in items + archive + trash if i.get("keyword")})
    return {
        "format": EXPORT_FORMAT,
        "version": EXPORT_VERSION,
        "app_version": APP_VERSION,
        "exported_at": now_iso(),
        "keywords": keywords,
        "count": len(items),
        "items": items,
        "archive": archive,
        "trash": trash,
    }


def export_zip(payload: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("items.json", json.dumps(payload, ensure_ascii=False, indent=1))
        packed = set()
        for item in (
            list(payload["items"])
            + list(payload.get("archive") or [])
            + list(payload.get("trash") or [])
        ):
            asset = str(item.get("asset") or "")
            if not asset.startswith("assets/"):
                continue
            path = runtime.ASSETS / Path(asset).name
            if path.is_file() and asset not in packed:
                z.write(path, asset)
                packed.add(asset)
    return buf.getvalue()


def _clean_item(raw, fallback_keyword: str = "") -> dict | None:
    if not isinstance(raw, dict):
        return None
    url = str(raw.get("url") or "").strip()
    keyword = str(raw.get("keyword") or fallback_keyword).strip()
    if not url or not keyword:
        return None

    def text(key: str, limit: int) -> str:
        return str(raw.get(key) or "").strip()[:limit]

    try:
        score = int(raw.get("score") or 0)
    except (TypeError, ValueError):
        score = 0
    source = str(raw.get("source") or "").strip().lower() or "unknown"
    metric = str(raw.get("metric") or "")
    if metric not in METRICS:
        metric = infer_metric(source)
    views = raw.get("views")
    try:
        views = int(views) if views is not None else None
    except (TypeError, ValueError):
        views = None
    if views is None and metric in ("views", "plays"):
        views = score
    asset = str(raw.get("asset") or "").strip()
    if asset and not (runtime.ASSETS / Path(asset).name).is_file():
        asset = ""
    channel_url = text("channel_url", 300)
    if not channel_url and source == "tiktok" and text("author", 200):
        channel_url = f"https://www.tiktok.com/@{text('author', 200)}"
    return {
        "url": url,
        "canonical_url": canonical_url(url),
        "title": text("title", 500),
        "body": text("body", 500),
        "source": source,
        "keyword": keyword,
        "author": text("author", 200),
        "channel_url": channel_url,
        "score": score,
        "views": views,
        "metric": metric,
        "created": text("created", 100),
        "published": text("published", 100),
        "created_at": text("created_at", 60) or now_iso(),
        "asset": asset or None,
    }


def import_payload(obj) -> tuple[dict, str | None]:
    if not isinstance(obj, dict) or obj.get("format") != EXPORT_FORMAT:
        return {}, "not a social-tracker items export"
    try:
        version = int(obj.get("version") or 0)
    except (TypeError, ValueError):
        return {}, "bad version"
    if version > EXPORT_VERSION:
        return (
            {},
            f"export version {version} is newer than supported ({EXPORT_VERSION})",
        )
    raw_items = obj.get("items")
    raw_archive = obj.get("archive")
    if not isinstance(raw_items, list):
        raw_items = []
    cleaned = [c for c in (_clean_item(x) for x in raw_items) if c]
    if not cleaned and not isinstance(raw_archive, list):
        return {}, "no valid items"
    by_kw: dict[str, list] = {}
    for item in cleaned:
        by_kw.setdefault(item["keyword"], []).append(item)
    total_added = total_skipped = 0
    per_kw = {}
    for kw, items in by_kw.items():
        added, skipped, _ = merge_items(items, kw, 0, fetch_thumbs=False)
        analyze(kw, write=True)
        total_added += added
        total_skipped += skipped
        per_kw[kw] = {"added": added, "duplicates": skipped}
    archive_added = 0
    if isinstance(raw_archive, list):
        archive = load_archive()
        known = {
            (str(a.get("keyword") or ""), canonical_url(str(a.get("url") or "")))
            for a in archive
            if isinstance(a, dict)
        }
        for raw in raw_archive:
            item = _clean_item(raw)
            if not item:
                continue
            key = (item["keyword"], item["canonical_url"])
            if key in known:
                continue
            item["archived_at"] = str(raw.get("archived_at") or "") or now_iso()
            archive.append(item)
            known.add(key)
            archive_added += 1
        if archive_added:
            atomic_write(runtime.ARCHIVE_FILE, archive)
    trash_added = 0
    if isinstance(obj.get("trash"), list):
        trash = load_trash()
        known = {_trash_key(t) for t in trash if isinstance(t, dict)}
        for raw in obj["trash"]:
            item = _clean_item(raw)
            if not item:
                continue
            key = (item["keyword"], item["canonical_url"])
            if key in known:
                continue
            item["deleted_at"] = str(raw.get("deleted_at") or "") or now_iso()
            trash.append(item)
            known.add(key)
            trash_added += 1
        if trash_added:
            atomic_write(runtime.TRASH_FILE, trash)
    return {
        "added": total_added,
        "duplicates": total_skipped,
        "archived_added": archive_added,
        "trash_added": trash_added,
        "keywords": sorted(by_kw),
        "per_keyword": per_kw,
    }, None


def import_zip(raw: bytes) -> tuple[dict, str | None]:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            try:
                payload = json.loads(z.read("items.json").decode("utf-8"))
            except KeyError:
                return {}, "zip is missing items.json"
            runtime.ASSETS.mkdir(exist_ok=True)
            for name in z.namelist():
                if not name.startswith("assets/") or not name.lower().endswith(".jpg"):
                    continue
                if ".." in name or not Path(name).name:
                    continue
                target = runtime.ASSETS / Path(name).name
                if not target.exists():
                    target.write_bytes(z.read(name))
    except (zipfile.BadZipFile, OSError, ValueError) as e:
        return {}, f"bad zip: {e}"
    return import_payload(payload)


def prune_old(days: int) -> dict:
    """Delete dated organic items older than N days across all keywords; ads stay."""
    if days <= 0:
        return {"removed": 0, "total": len(load_json(runtime.ITEMS_FILE, []))}
    cutoff = cutoff_iso(days)
    items = load_json(runtime.ITEMS_FILE, [])
    if not isinstance(items, list):
        items = []
    kept, affected = [], set()
    for item in items:
        if (
            isinstance(item, dict)
            and item.get("source") in DATED_SOURCES
            and older_than(item.get("published") or "", cutoff)
        ):
            affected.add(item.get("keyword"))
        else:
            kept.append(item)
    removed = len(items) - len(kept)
    if removed:
        atomic_write(runtime.ITEMS_FILE, kept)
        rebuild_index(kept)
        analysis = load_json(runtime.ANALYSIS_FILE, {})
        if not isinstance(analysis, dict):
            analysis = {}
        for kw in affected:
            if kw and any(isinstance(i, dict) and i.get("keyword") == kw for i in kept):
                analysis[kw] = {k: v for k, v in analyze(kw, write=False).items() if k != "items"}
            else:
                analysis.pop(kw, None)
        atomic_write(runtime.ANALYSIS_FILE, analysis)
        cleanup_orphan_assets(kept)
    return {"removed": removed, "total": len(kept), "days": days}


def refresh_stats(
    q: str,
    sources: list | None = None,
    cancel: threading.Event | None = None,
    items: list | None = None,
) -> dict:
    """Re-read view/play/like counts for existing items of one keyword.
    YouTube reads each watch page; TikTok/TikTok Ads re-scrape the source page.
    Never adds items. Facebook Ads / Google News have no public view metric.
    When `items` (array {keyword,url}) is given, only those items are updated."""
    cancel = cancel or threading.Event()
    if q:
        wanted = set(sources or ["youtube", "tiktok", "ttads"])
    else:
        wanted = {"youtube"}  # keyword-less refresh: YouTube per-video stats only
    all_items = load_json(runtime.ITEMS_FILE, [])
    if not isinstance(all_items, list):
        all_items = []
    target = (
        [i for i in all_items if isinstance(i, dict)]
        if not q
        else [i for i in all_items if isinstance(i, dict) and i.get("keyword") == q]
    )
    if items:
        wanted_keys = _item_keys(items)
        target = [
            i
            for i in target
            if (
                str(i.get("keyword") or ""),
                canonical_url(str(i.get("url") or "")),
            )
            in wanted_keys
        ]
    if not target:
        return {"updated": 0, "total": 0, "errors": [], "sources": sorted(wanted)}
    updated, errors, touched = 0, [], set()
    cancelled = False

    if "youtube" in wanted:
        yt = [i for i in target if i.get("source") == "youtube"]
        for n, item in enumerate(yt, 1):
            if cancel.is_set():
                cancelled = True
                break
            vid = ""
            m = re.search(r"[?&]v=([\w-]+)", str(item.get("url") or ""))
            if m:
                vid = m.group(1)
            if not vid:
                continue
            runtime.progress_set(source="youtube", stage=f"refreshing views {n}/{len(yt)}")
            views, channel_url, author = youtube_video_stats(vid)
            if views is not None:
                item["views"] = views
                item["score"] = views
                item["metric"] = "views"
                updated += 1
                touched.add(item.get("keyword"))
            if channel_url and not item.get("channel_url"):
                item["channel_url"] = channel_url
            if author and not item.get("author"):
                item["author"] = author
        if cancelled:
            errors.append("youtube: cancelled")

    for src in ("tiktok", "ttads"):
        if src not in wanted or cancelled:
            continue
        fn = COLLECTORS.get(src)
        if fn is None:
            continue
        if cancel.is_set():
            cancelled = True
            break
        runtime.progress_set(source=src, stage="refreshing stats")
        try:
            fresh, errs = fn(q, "public", 0) if src == "tiktok" else fn(q, 0)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{src}: {e}")
            continue
        errors += errs
        by_url = {}
        for item in fresh:
            key = canonical_url(item.get("url") or "")
            if key:
                by_url[key] = item
        for item in target:
            if item.get("source") != src:
                continue
            fresh_item = by_url.get(canonical_url(item.get("url") or ""))
            if not fresh_item:
                continue
            score = int(fresh_item.get("score") or 0)
            item["score"] = score
            item["views"] = score if src == "tiktok" else None
            item["metric"] = "plays" if src == "tiktok" else "likes"
            if src == "tiktok" and not item.get("channel_url") and fresh_item.get("author"):
                item["channel_url"] = f"https://www.tiktok.com/@{fresh_item['author']}"
            updated += 1
            touched.add(item.get("keyword"))

    atomic_write(runtime.ITEMS_FILE, all_items)
    rebuild_index(all_items)
    for kw in touched:
        if kw:
            analyze(kw, write=True)
    return {
        "updated": updated,
        "total": len(target),
        "errors": errors,
        "sources": sorted(wanted),
        "cancelled": cancelled,
    }


def create_item(payload: dict) -> tuple[dict, str | None]:
    item = _clean_item(payload)
    if not item:
        return {}, "url and keyword are required"
    added, skipped, errors = merge_items([item], item["keyword"], 0, fetch_thumbs=False)
    if added:
        analyze(item["keyword"], write=True)
    return {"added": added, "duplicates": skipped, "item": item, "errors": errors}, None


def _find_item(items: list, keyword: str, url: str):
    key = canonical_url(url)
    for idx, item in enumerate(items):
        if (
            isinstance(item, dict)
            and item.get("keyword") == keyword
            and canonical_url(item.get("url") or "") == key
        ):
            return idx, item
    return None, None


def update_item(keyword: str, url: str, patch: dict) -> tuple[dict, str | None]:
    items = load_json(runtime.ITEMS_FILE, [])
    if not isinstance(items, list):
        items = []
    idx, item = _find_item(items, keyword, url)
    if item is None:
        return {}, "item not found"
    old_kw = item.get("keyword")
    for field, limit in (
        ("title", 500),
        ("body", 500),
        ("author", 200),
        ("channel_url", 300),
        ("created", 100),
        ("published", 100),
    ):
        if field in patch:
            item[field] = str(patch.get(field) or "").strip()[:limit]
    if "keyword" in patch:
        new_kw = str(patch.get("keyword") or "").strip()
        if not new_kw:
            return {}, "keyword cannot be empty"
        item["keyword"] = new_kw
    if "score" in patch:
        try:
            score = max(0, int(patch.get("score") or 0))
        except (TypeError, ValueError):
            return {}, "bad score"
        item["score"] = score
        if item.get("metric") in ("views", "plays"):
            item["views"] = score
    if "views" in patch:
        try:
            views = int(patch.get("views"))
        except (TypeError, ValueError):
            return {}, "bad views"
        item["views"] = views
        if item.get("metric") in ("views", "plays"):
            item["score"] = views
    if "metric" in patch and patch.get("metric") in METRICS:
        item["metric"] = patch["metric"]
    backfill_item(item)
    items[idx] = item
    atomic_write(runtime.ITEMS_FILE, items)
    rebuild_index(items)
    analyze(item["keyword"], write=True)
    if old_kw and old_kw != item["keyword"]:
        if any(isinstance(i, dict) and i.get("keyword") == old_kw for i in items):
            analyze(old_kw, write=True)
        else:
            analysis = load_json(runtime.ANALYSIS_FILE, {})
            if isinstance(analysis, dict):
                analysis.pop(old_kw, None)
                atomic_write(runtime.ANALYSIS_FILE, analysis)
    return {"item": item}, None


def delete_item(keyword: str, url: str) -> tuple[dict, str | None]:
    # 2.5 soft delete: move into trash (undo via /api/trash/restore)
    out = trash_items([{"keyword": keyword, "url": url}])
    if not out["trashed"]:
        return {}, "item not found"
    return {"removed": 1, "trashed": 1, "total": out["total"]}, None


def _analysis_sync(keywords: set[str]) -> None:
    analysis = load_json(runtime.ANALYSIS_FILE, {})
    if not isinstance(analysis, dict):
        analysis = {}
    items = load_json(runtime.ITEMS_FILE, [])
    for kw in keywords:
        if not kw:
            continue
        if any(isinstance(i, dict) and i.get("keyword") == kw for i in items):
            analysis[kw] = {k: v for k, v in analyze(kw, write=False).items() if k != "items"}
        else:
            analysis.pop(kw, None)
    atomic_write(runtime.ANALYSIS_FILE, analysis)


def _item_keys(raw_items) -> set[tuple[str, str]]:
    keys = set()
    for raw in raw_items or []:
        if not isinstance(raw, dict):
            continue
        keyword = str(raw.get("keyword") or "").strip()
        url = str(raw.get("url") or "").strip()
        if keyword and url:
            keys.add((keyword, canonical_url(url)))
    return keys


def load_archive() -> list:
    data = load_json(runtime.ARCHIVE_FILE, [])
    return data if isinstance(data, list) else []


def archive_items(raw_items) -> dict:
    keys = _item_keys(raw_items)
    items = load_json(runtime.ITEMS_FILE, [])
    if not isinstance(items, list):
        items = []
    archive = load_archive()
    known = {
        (str(a.get("keyword") or ""), canonical_url(str(a.get("url") or "")))
        for a in archive
        if isinstance(a, dict)
    }
    keep, affected, moved = [], set(), 0
    for item in items:
        if not isinstance(item, dict):
            keep.append(item)
            continue
        key = (
            str(item.get("keyword") or ""),
            canonical_url(str(item.get("url") or "")),
        )
        if key in keys:
            affected.add(key[0])
            moved += 1
            if key not in known:
                saved = dict(item)
                saved["archived_at"] = now_iso()
                archive.append(saved)
                known.add(key)
        else:
            keep.append(item)
    if moved:
        atomic_write(runtime.ITEMS_FILE, keep)
        atomic_write(runtime.ARCHIVE_FILE, archive)
        rebuild_index(keep)
        _analysis_sync(affected)
        cleanup_orphan_assets(keep)
    return {"archived": moved, "total_archive": len(archive), "total_items": len(keep)}


def restore_archived(raw_items) -> dict:
    keys = _item_keys(raw_items)
    items = load_json(runtime.ITEMS_FILE, [])
    if not isinstance(items, list):
        items = []
    archive = load_archive()
    active = {
        (str(i.get("keyword") or ""), canonical_url(str(i.get("url") or "")))
        for i in items
        if isinstance(i, dict)
    }
    keep, affected, restored, skipped = [], set(), 0, 0
    for item in archive:
        if not isinstance(item, dict):
            continue
        key = (
            str(item.get("keyword") or ""),
            canonical_url(str(item.get("url") or "")),
        )
        if key not in keys:
            keep.append(item)
            continue
        if key in active:
            skipped += 1
            keep.append(item)  # still archived so it is not lost
            continue
        restored_item = {k: v for k, v in item.items() if k != "archived_at"}
        items.append(restored_item)
        active.add(key)
        affected.add(key[0])
        restored += 1
    if restored:
        atomic_write(runtime.ITEMS_FILE, items)
        atomic_write(runtime.ARCHIVE_FILE, keep)
        rebuild_index(items)
        _analysis_sync(affected)
    return {"restored": restored, "skipped": skipped, "total_archive": len(keep)}


def delete_archived(raw_items) -> dict:
    keys = _item_keys(raw_items)
    archive = load_archive()
    kept = [
        a
        for a in archive
        if not (
            isinstance(a, dict)
            and (str(a.get("keyword") or ""), canonical_url(str(a.get("url") or ""))) in keys
        )
    ]
    removed = len(archive) - len(kept)
    if removed:
        atomic_write(runtime.ARCHIVE_FILE, kept)
        cleanup_orphan_assets()
    return {"removed": removed, "total_archive": len(kept)}


def load_trash() -> list:
    data = load_json(runtime.TRASH_FILE, [])
    return data if isinstance(data, list) else []


def _trash_key(t) -> tuple[str, str]:
    return (str(t.get("keyword") or ""), canonical_url(str(t.get("url") or "")))


def trash_items(raw_items) -> dict:
    """Move matching active items into trash.json (soft delete). Returns trashed/total."""
    keys = _item_keys(raw_items)
    if not keys:
        return {"trashed": 0, "total": len(load_json(runtime.ITEMS_FILE, []))}
    items = load_json(runtime.ITEMS_FILE, [])
    if not isinstance(items, list):
        items = []
    trash = load_trash()
    known = {_trash_key(t) for t in trash if isinstance(t, dict)}
    keep, affected, trashed = [], set(), 0
    for item in items:
        if not isinstance(item, dict):
            keep.append(item)
            continue
        key = (
            str(item.get("keyword") or ""),
            canonical_url(str(item.get("url") or "")),
        )
        if key not in keys:
            keep.append(item)
            continue
        affected.add(key[0])
        if key not in known:
            saved = dict(item)
            saved["deleted_at"] = now_iso()
            trash.append(saved)
            known.add(key)
        trashed += 1
    if trashed:
        atomic_write(runtime.ITEMS_FILE, keep)
        atomic_write(runtime.TRASH_FILE, trash)
        rebuild_index(keep)
        _analysis_sync(affected)
        cleanup_orphan_assets(keep)
        purge_trash()  # 2.5 auto-purge expired trash after each delete
    return {"trashed": trashed, "total": len(keep)}


def restore_trash(raw_items) -> dict:
    """Move requested trashed items back into active items (skip + drop conflicts)."""
    keys = _item_keys(raw_items)
    if not keys:
        return {"restored": 0, "skipped": 0, "total": len(load_trash())}
    items = load_json(runtime.ITEMS_FILE, [])
    if not isinstance(items, list):
        items = []
    active = {
        (str(i.get("keyword") or ""), canonical_url(str(i.get("url") or "")))
        for i in items
        if isinstance(i, dict)
    }
    trash = load_trash()
    keep, affected, restored, skipped = [], set(), 0, 0
    for t in trash:
        if not isinstance(t, dict):
            continue
        key = _trash_key(t)
        if key not in keys:
            keep.append(t)
            continue
        if key in active:
            skipped += 1
            continue  # already active: drop the trashed copy
        item = {k: v for k, v in t.items() if k != "deleted_at"}
        items.append(item)
        active.add(key)
        affected.add(key[0])
        restored += 1
    if restored or skipped:
        atomic_write(runtime.TRASH_FILE, keep)
        if restored:
            atomic_write(runtime.ITEMS_FILE, items)
            rebuild_index(items)
            _analysis_sync(affected)
    return {"restored": restored, "skipped": skipped, "total": len(keep)}


def purge_trash() -> int:
    """Drop trash older than TRASH_RETENTION_DAYS. Returns number removed."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=TRASH_RETENTION_DAYS)).isoformat()
    trash = load_trash()
    kept, removed = [], 0
    for t in trash:
        if not isinstance(t, dict):
            continue
        deleted_at = t.get("deleted_at") or ""
        if deleted_at and deleted_at < cutoff:
            removed += 1
        else:
            kept.append(t)
    if removed:
        atomic_write(runtime.TRASH_FILE, kept)
        cleanup_orphan_assets()
        print(f"trash: auto-purged {removed} item(s) older than {TRASH_RETENTION_DAYS}d")
    return removed


def bulk_items(action: str, raw_items, to_keyword: str = "") -> tuple[dict, str | None]:
    keys = _item_keys(raw_items)
    if not keys:
        return {}, "no items selected"
    if action == "move" and not to_keyword.strip():
        return {}, "missing target keyword"
    if action == "delete":
        # 2.5 soft delete: move into trash (undo via /api/trash/restore)
        out = trash_items(raw_items)
        return {
            "changed": out["trashed"],
            "trashed": out["trashed"],
            "total": out["total"],
        }, None
    items = load_json(runtime.ITEMS_FILE, [])
    if not isinstance(items, list):
        items = []
    keep, affected, changed = [], set(), 0
    for item in items:
        if not isinstance(item, dict):
            keep.append(item)
            continue
        key = (
            str(item.get("keyword") or ""),
            canonical_url(str(item.get("url") or "")),
        )
        if key not in keys:
            keep.append(item)
            continue
        changed += 1
        if action == "move":
            affected.add(str(item.get("keyword") or ""))
            item["keyword"] = to_keyword.strip()
            affected.add(item["keyword"])
        else:  # delete
            affected.add(key[0])
            continue
        keep.append(item)
    if not changed:
        return {}, "item not found"
    atomic_write(runtime.ITEMS_FILE, keep)
    rebuild_index(keep)
    _analysis_sync(affected)
    cleanup_orphan_assets(keep)
    return {"changed": changed, "action": action, "total": len(keep)}, None


def clear_all_data() -> dict:
    """Wipe collected data + archive + trash + thumbnails. Profiles (user presets) are kept."""
    items = load_json(runtime.ITEMS_FILE, [])
    count = len(items) if isinstance(items, list) else 0
    archived = len(load_archive())
    trashed = len(load_trash())
    atomic_write(runtime.ITEMS_FILE, [])
    atomic_write(runtime.ARCHIVE_FILE, [])
    atomic_write(runtime.TRASH_FILE, [])
    atomic_write(runtime.INDEX_FILE, {})
    atomic_write(runtime.ANALYSIS_FILE, {})
    atomic_write(runtime.SOURCE_LOG_FILE, {})
    removed_assets = cleanup_orphan_assets([])
    return {
        "removed": count,
        "archived": archived,
        "trashed": trashed,
        "assets": removed_assets,
        "profiles_kept": True,
    }


def clear_keyword(q: str) -> dict:
    items = load_json(runtime.ITEMS_FILE, [])
    if not isinstance(items, list):
        items = []
    kept = [i for i in items if not (isinstance(i, dict) and i.get("keyword") == q)]
    removed = len(items) - len(kept)
    if removed:
        atomic_write(runtime.ITEMS_FILE, kept)
        rebuild_index(kept)
        cleanup_orphan_assets(kept)
    # a keyword with 0 fetched items still has an analysis row: drop it too
    analysis = load_json(runtime.ANALYSIS_FILE, {})
    if isinstance(analysis, dict) and q in analysis:
        analysis.pop(q, None)
        atomic_write(runtime.ANALYSIS_FILE, analysis)
    return {"removed": removed, "total": len(kept)}


def cleanup_orphan_assets(items: list | None = None) -> int:
    if items is None:
        items = load_json(runtime.ITEMS_FILE, [])
    pool = list(items) if isinstance(items, list) else []
    pool += [a for a in load_archive() if isinstance(a, dict)]
    pool += [t for t in load_trash() if isinstance(t, dict)]
    used = {Path(str(i.get("asset"))).name for i in pool if i.get("asset")}
    removed = 0
    if runtime.ASSETS.is_dir():
        for path in runtime.ASSETS.glob("*.jpg"):
            if path.name not in used:
                try:
                    path.unlink()
                    removed += 1
                except OSError:
                    pass
    return removed
