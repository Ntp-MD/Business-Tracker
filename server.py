#!/usr/bin/env python3
"""social-tracker localhost server (ARCHITECTURE.md §9.2-9.4).

Stdlib only. Binds 127.0.0.1:8000.
  GET /  -> index.html (mockup)   GET /live/ -> live/index.html (real data)   /dashboard-live.html -> /live/
  GET /fonts/*, /assets/* -> static files (assets/*.jpg are YT thumbnails)
  GET /api/summary?q=      -> analyze(q) read-only
  GET /api/progress        -> fetch/refresh heartbeat (stage, elapsed, since_update)
  GET /api/status          -> disk usage, counts, last source result, sessions
  GET /api/export[.zip]    -> JSON envelope / zip with items.json + thumbnails
  POST /api/fetch          -> collect -> dedup per keyword -> analyze
  POST /api/refresh-stats  -> update views/plays/likes of existing items only
  POST /api/cancel         -> stop the current fetch before its next source
  POST /api/import         -> JSON/ZIP import (idempotent, schema-checked)
  POST /api/items          -> create one item
  PUT/DELETE /api/items    -> edit/delete one item (keyword + url identity)
  POST /api/clear[/-all]   -> clear one keyword / all collected data
  POST /api/prune          -> remove dated organic items older than N days
  GET/POST/PUT/DELETE /api/profiles -> profile CRUD (data/profiles.json)
  POST /api/analyze        -> analyze only
Collect failures go into errors[] and never crash the server.
Writes are button/API-triggered only; GET endpoints never write.
"""

from __future__ import annotations

import io
import json
import os
import re
import threading
import time
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ElementTree
import zipfile
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import uuid

import db

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"
LIVE = ROOT / "live"
DATA = ROOT / "data"
ASSETS = ROOT / "assets"
ITEMS_FILE = DATA / "items.json"
INDEX_FILE = DATA / "index.json"
ANALYSIS_FILE = DATA / "analysis.json"
PROFILES_FILE = DATA / "profiles.json"
SOURCE_LOG_FILE = DATA / "sources.json"
ARCHIVE_FILE = DATA / "archive.json"
TRASH_FILE = DATA / "trash.json"
APP_VERSION = "0.1V"
EXPORT_FORMAT = "social-tracker.items"
EXPORT_VERSION = 1
TRASH_RETENTION_DAYS = (
    7  # 2.5 auto-purge: trash older than this is dropped at start + after delete
)
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
HOST, PORT = "127.0.0.1", 8000

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


# ---------------- COLLECT: YouTube (§9.2) ----------------


def parse_views(text: str) -> int:
    # hl=th renders Thai: "การดู 109,674 ครั้ง" (no K/M suffix). Strip prefix
    # so the leading-number parse below works for both th and en output.
    t = (text or "").replace(",", "").strip().lower()
    if t.startswith("no views"):
        return 0
    t = re.sub(r"^\s*การ\s*ดู\s*", "", t)
    t = re.sub(r"\s*(ครั้ง|views?|viewers?)\s*$", "", t).strip()
    m = re.match(r"([\d.]+)\s*([kmb]?)", t)
    if not m:
        return 0
    mult = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}.get(m.group(2), 1)
    try:
        return int(float(m.group(1)) * mult)
    except ValueError:
        return 0


def _runs_text(node) -> str:
    if isinstance(node, dict):
        if "simpleText" in node:
            return str(node["simpleText"])
        runs = node.get("runs") or []
        return "".join(str(r.get("text", "")) for r in runs if isinstance(r, dict))
    return ""


# ---------------- FRESHNESS (fetch-time window) ----------------
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
GNEWS_WHEN = {
    1: "when:7d",
    3: "when:7d",
    7: "when:7d",
    15: "when:30d",
    30: "when:30d",
    365: "when:1y",
}
YT_SP = {
    1: "EgIIAw==",
    3: "EgIIAw==",
    7: "EgIIAw==",
    15: "EgIIBA==",
    30: "EgIIBA==",
    365: "EgIIBQ==",
}  # week, month, year


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


def collect_gnews(q: str, max_age_days: int = 0) -> tuple[list, list[str]]:
    """Google News RSS (stdlib). author=google-news, score=0. Never raises.
    max_age_days > 0 restricts results to that window (query operator + pubDate check)."""
    cutoff = cutoff_iso(max_age_days)
    when = GNEWS_WHEN.get(max_age_days, "")
    query = f"{q} {when}".strip()
    progress_stage("reading RSS")
    try:
        url = (
            "https://news.google.com/rss/search?q="
            + urllib.parse.quote_plus(query)
            + "&hl=th&gl=TH&ceid=TH:th"
        )
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
    except Exception as e:  # noqa: BLE001
        return [], [f"gnews: {e}"]
    try:
        root = ElementTree.fromstring(data)
    except Exception as e:  # noqa: BLE001
        return [], [f"gnews: RSS parse failed: {e}"]
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        if not title or not link:
            continue
        published = ""
        if pub:
            try:
                published = parsedate_to_datetime(pub).isoformat()
            except (TypeError, ValueError):
                published = ""
        if older_than(published, cutoff):
            continue
        source_el = item.find("source")
        channel_name = (source_el.text or "").strip() if source_el is not None else ""
        channel_url = (
            (source_el.get("url") or "").strip() if source_el is not None else ""
        )
        items.append(
            {
                "url": link,
                "title": title,
                "body": title[:500],
                "source": "gnews",
                "keyword": q,
                "author": channel_name or "google-news",
                "channel_url": channel_url,
                "score": 0,
                "views": None,
                "metric": "none",
                "created": pub,
                "published": published,
                "created_at": now_iso(),
                "asset": None,
            }
        )
        if len(items) >= 10:
            break
    return items, []


PW_SESSIONS = ROOT / "sessions"
PW_TIMEOUT_MS = 35000
PW_LIMIT = 12
PW_LOCK = threading.Lock()  # ทีละ 1 รอบ Playwright: กัน thread ชนกันและ profile dir ชนกัน

# สถานะ fetch ล่าสุด — ให้หน้าเว็บ poll รู้ว่าเซิร์ฟเวอร์ยังทำงาน ไม่ใช่ค้าง
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


class _PwPublicCtx:
    """public ไม่ต้อง profile ถาวร — new_context ใช้ user_data_dir ชั่วคราวใน RAM"""

    def __init__(self, browser, ctx):
        self._browser, self._ctx = browser, ctx

    def new_page(self):
        return self._ctx.new_page()

    def close(self):
        for closer in (self._ctx.close, self._browser.close):
            try:
                closer()
            except Exception:
                pass


def _playwright():
    """Import Playwright lazily so the server also runs stdlib-only (YT/GNews)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return (
            None,
            "playwright not installed — run: python -m pip install playwright && python -m playwright install chromium",
        )
    return sync_playwright, None


@contextmanager
def _pw_locked():
    """ล็อกทั่วเซิร์ฟเวอร์ให้ทีละ 1 เลนส์ Playwright เท่านั้น"""
    with PW_LOCK:
        yield


def _pw_context(playwright, kind: str):
    """Start a persistent headless context for TikTok/Facebook.
    First run needs one headed login by the owner (stored in user_data_dir)."""
    if not (PW_SESSIONS / kind).exists():
        return None, (
            f"{kind}: no login session — run `python pw_login.py {kind}`, "
            "log in once in the opened browser, then fetch again"
        )
    browser = playwright.chromium.launch_persistent_context(
        str(PW_SESSIONS / kind),
        headless=True,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        user_agent=UA,
        locale="th-TH",
        timezone_id="Asia/Bangkok",
        timeout=PW_TIMEOUT_MS,
    )
    return browser, None


def _pw_public_context(playwright, kind: str):
    """browser + context สด public ไม่ต้อง login — ไม่แตะ profile dir (ไม่ชนกันหลายโปรเซส)"""
    try:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            timeout=PW_TIMEOUT_MS,
        )
        ctx = browser.new_context(
            user_agent=UA, locale="en-US", timezone_id="Asia/Bangkok"
        )
        return _PwPublicCtx(browser, ctx), None
    except Exception as e:  # noqa: BLE001
        return None, f"{kind}: public browser failed: {e}"


def _tiktok_search_json(page, q: str) -> list:
    """Search TikTok like a human and capture the page's own JSON (no API key)."""
    captured = []

    def on_response(resp):
        if "/api/search/general/full/" not in resp.url:
            return
        try:
            captured.append(resp.json())
        except Exception:  # noqa: BLE001
            pass

    page.on("response", on_response)
    try:
        page.goto(
            "https://www.tiktok.com/search?q=" + urllib.parse.quote(q) + "&lang=en",
            wait_until="domcontentloaded",
            timeout=PW_TIMEOUT_MS,
        )
        page.wait_for_timeout(5000)
        # accuracy over speed: scroll like a human so more items load
        for _ in range(3):
            page.mouse.wheel(0, 3500)
            page.wait_for_timeout(2000)
    finally:
        page.remove_listener("response", on_response)
    return captured


def _tiktok_items(captured: list, q: str, max_age_days: int) -> list:
    cutoff = cutoff_iso(max_age_days) if max_age_days > 0 else None
    items, seen = [], set()
    for payload in captured:
        for entry in payload.get("data") or []:
            item = (entry or {}).get("item") or {}
            vid = str(item.get("id") or "")
            if not vid or vid in seen:
                continue
            seen.add(vid)
            published = ""
            ts = item.get("createTime")
            if ts:
                try:
                    published = datetime.fromtimestamp(
                        int(ts), timezone.utc
                    ).isoformat()
                except (TypeError, ValueError, OverflowError, OSError):
                    published = ""
            if older_than(published, cutoff):
                continue
            author = str((item.get("author") or {}).get("uniqueId") or "")
            desc = str(item.get("desc") or "")
            try:
                score = int((item.get("stats") or {}).get("playCount") or 0)
            except (TypeError, ValueError):
                score = 0
            items.append(
                {
                    "url": f"https://www.tiktok.com/@{author}/video/{vid}"
                    if author
                    else f"https://www.tiktok.com/video/{vid}",
                    "title": desc[:500] or f"TikTok video {vid}",
                    "body": desc[:500],
                    "source": "tiktok",
                    "keyword": q,
                    "author": author,
                    "channel_url": f"https://www.tiktok.com/@{author}"
                    if author
                    else "",
                    "score": score,
                    "views": score,
                    "metric": "plays",
                    "created": published,
                    "published": published,
                    "created_at": now_iso(),
                    "asset": None,
                }
            )
            if len(items) >= PW_LIMIT:
                return items
    return items


def collect_tiktok(
    q: str, mode: str = "public", max_age_days: int = 0
) -> tuple[list, list[str]]:
    """TikTok search via Playwright (real browser, no API key). mode=public|session.
    Public mode reads the search page's own JSON and filters by createTime. Fail-soft; never raises."""
    sync_playwright, err = _playwright()
    if err:
        return [], [f"tiktok: {err}"]
    tag = "tiktok(public)" if mode != "session" else "tiktok(session)"
    last_err = None
    for attempt in range(2):
        try:
            progress_stage("opening browser (or waiting for browser queue)")
            with _pw_locked(), sync_playwright() as p:
                if mode == "session":
                    ctx, err = _pw_context(p, "tiktok")
                else:
                    ctx, err = _pw_public_context(p, "tiktok")
                if err:
                    return [], [err]
                try:
                    progress_stage("searching, waiting for results")
                    captured = _tiktok_search_json(ctx.new_page(), q)
                finally:
                    ctx.close()
            break
        except Exception as e:  # noqa: BLE001
            last_err = e
            if "Connection" not in str(e) and attempt == 1:
                break
    else:
        captured = []
    if last_err and not captured:
        return [], [f"{tag}: {last_err}"]
    items = _tiktok_items(captured, q, max_age_days)
    if items:
        return items, []
    raw = sum(len(p.get("data") or []) for p in captured)
    win = f" within {max_age_days}d" if max_age_days > 0 else ""
    if raw:
        return [], [f"{tag}: {raw} results, none{win}"]
    hint = (
        "blocked or login wall"
        if mode != "session"
        else "login expired or blocked — re-run pw_login.py"
    )
    return [], [f"{tag}: no videos{win} ({hint})"]


# ---------------- AD LIBRARIES (public pages, no login) ----------------

TTCC_PERIOD = {
    1: 7,
    3: 7,
    7: 7,
    15: 30,
    30: 30,
    365: 180,
}  # TikTok CC supports 7/30/180 days


def _parse_en_date(text: str) -> str:
    for fmt in ("%d %b %Y", "%d %B %Y"):
        try:
            return (
                datetime.strptime((text or "").strip(), fmt)
                .replace(tzinfo=timezone.utc)
                .isoformat()
            )
        except (TypeError, ValueError):
            continue
    return ""


def collect_fbads(q: str, max_age_days: int = 0) -> tuple[list, list[str]]:
    """Meta Ad Library: active ads for a keyword (country TH), public page. Fail-soft.
    Ads are current by definition (active), so the freshness window is not applied."""
    sync_playwright, err = _playwright()
    if err:
        return [], [f"fbads: {err}"]
    raw, last_err = [], None
    for attempt in range(2):
        try:
            progress_stage("opening browser (or waiting for browser queue)")
            with _pw_locked(), sync_playwright() as p:
                ctx, err = _pw_public_context(p, "fbads")
                if err:
                    return [], [err]
                try:
                    page = ctx.new_page()
                    url = (
                        "https://www.facebook.com/ads/library/?active_status=active"
                        "&ad_type=all&country=TH&media_type=all&search_type=keyword_unordered"
                        "&q=" + urllib.parse.quote_plus(q)
                    )
                    progress_stage("loading ad library")
                    page.goto(url, wait_until="domcontentloaded", timeout=PW_TIMEOUT_MS)
                    progress_stage("waiting 12s for ads to render")
                    page.wait_for_timeout(12000)
                    progress_stage("scrolling for more ads")
                    for _ in range(3):
                        page.mouse.wheel(0, 3000)
                        page.wait_for_timeout(2500)
                    progress_stage("reading ad cards")
                    raw = page.evaluate("""() => {
                        const out = [], seen = new Set();
                        for (const el of document.querySelectorAll('div')) {
                            const t = el.innerText || '';
                            const m = t.match(/Library ID:\\s*(\\d+)/);
                            if (!m || seen.has(m[1]) || !/Sponsored/.test(t) || t.length > 1400) continue;
                            seen.add(m[1]);
                            const adv = (t.match(/See ad details\\s+([\\s\\S]{1,120}?)\\s+Sponsored/) || [])[1] || '';
                            const copy = ((t.split('Sponsored')[1] || '').split('Shop Now')[0] || '')
                                .replace(/\\s+/g, ' ').trim().slice(0, 300);
                            const started = (t.match(/Started running on ([0-9]{1,2} [A-Za-z]{3,} [0-9]{4})/) || [])[1] || '';
                            out.push({id: m[1], adv: adv.trim(), copy, started});
                        }
                        return out.slice(0, 20);
                    }""")
                finally:
                    ctx.close()
            last_err = None
            break
        except Exception as e:  # noqa: BLE001
            last_err = e
            raw = []
    if last_err is not None:
        return [], [f"fbads: {last_err}"]
    items = []
    for r in raw or []:
        adv = (r.get("adv") or "").strip()
        copy = (r.get("copy") or "").strip()
        if adv and copy:
            title = f"{adv}: {copy}"
        else:
            title = copy or adv or "Facebook ad"
        items.append(
            {
                "url": f"https://www.facebook.com/ads/library/?id={r['id']}",
                "title": title[:500],
                "body": copy,
                "source": "fbads",
                "keyword": q,
                "author": adv,
                "channel_url": "",
                "score": 0,
                "views": None,
                "metric": "none",
                "created": r.get("started") or "",
                "published": _parse_en_date(r.get("started") or ""),
                "created_at": now_iso(),
                "asset": None,
            }
        )
        if len(items) >= PW_LIMIT:
            break
    if items:
        return items, []
    return [], ["fbads: parsed 0 ads (page slow or markup changed — retry)"]


def collect_ttads(q: str, max_age_days: int = 0) -> tuple[list, list[str]]:
    """TikTok Creative Center Top Ads (TH, public, no login). Period = freshness window.
    Top Ads is not keyword-filtered; the keyword tab still groups the results. Fail-soft."""
    sync_playwright, err = _playwright()
    if err:
        return [], [f"ttads: {err}"]
    period = TTCC_PERIOD.get(max_age_days, 30)
    raw, last_err = [], None
    for attempt in range(2):
        try:
            progress_stage("opening browser (or waiting for browser queue)")
            with _pw_locked(), sync_playwright() as p:
                ctx, err = _pw_public_context(p, "ttads")
                if err:
                    return [], [err]
                try:
                    page = ctx.new_page()
                    url = (
                        "https://ads.tiktok.com/business/creativecenter/inspiration/topads/pc/en"
                        f"?period={period}&region=TH"
                    )
                    progress_stage("loading top ads")
                    page.goto(url, wait_until="domcontentloaded", timeout=PW_TIMEOUT_MS)
                    progress_stage("waiting 12s for cards to render")
                    page.wait_for_timeout(12000)
                    page.keyboard.press("Escape")  # promo modal blocks clicks
                    page.wait_for_timeout(1000)
                    progress_stage("reading ad cards")
                    raw = page.evaluate("""() => {
                        const out = [], seen = new Set();
                        for (const c of document.querySelectorAll('div[class*="TopadsVideoCard_card__"]')) {
                            const a = c.querySelector('a[href*="/topads/"]');
                            if (!a || seen.has(a.href)) continue;
                            seen.add(a.href);
                            out.push({url: a.href, text: (c.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 300)});
                        }
                        return out.slice(0, 20);
                    }""")
                finally:
                    ctx.close()
            last_err = None
            break
        except Exception as e:  # noqa: BLE001
            last_err = e
            raw = []
    if last_err is not None:
        return [], [f"ttads: {last_err}"]
    items = []
    for r in raw or []:
        text = r.get("text") or ""
        m = re.search(r"(\d+)\s+Likes?", text)
        score = int(m.group(1)) if m else 0
        title = text.split(" Likes")[0] if " Likes" in text else text
        title = re.sub(r"\s+\d+$", "", title).strip() or text[:80]
        items.append(
            {
                "url": r["url"],
                "title": title[:500],
                "body": text,
                "source": "ttads",
                "keyword": q,
                "author": "",
                "channel_url": "",
                "score": score,
                "views": None,
                "metric": "likes",
                "created": "",
                "published": "",
                "created_at": now_iso(),
                "asset": None,
            }
        )
        if len(items) >= PW_LIMIT:
            break
    if items:
        return items, []
    return [], ["ttads: parsed 0 ads (page slow or markup changed — retry)"]


def collect_youtube(q: str, max_age_days: int = 0) -> tuple[list, list[str]]:
    """One YouTube search scrape. Returns (items, errors). Never raises.
    max_age_days > 0 adds the upload-date filter and drops older videos."""
    errors: list[str] = []
    cutoff = cutoff_iso(max_age_days)
    sp = YT_SP.get(max_age_days, "")
    progress_stage("searching")
    try:
        url = (
            "https://www.youtube.com/results?search_query="
            + urllib.parse.quote_plus(q)
            + "&hl=th"
            + ("&sp=" + urllib.parse.quote(sp, safe="") if sp else "")
        )
        req = urllib.request.Request(
            url,
            headers={"User-Agent": UA, "Accept-Language": "th-TH,th;q=0.9,en;q=0.8"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", "ignore")
    except Exception as e:  # noqa: BLE001 - fail-soft per spec
        return [], [f"youtube: {e}"]
    m = re.search(r"ytInitialData\s*=\s*(\{.*?\});</script>", html, re.S)
    if not m:
        return [], ["youtube: ytInitialData not found (markup changed?)"]
    try:
        data = json.loads(m.group(1))
    except Exception as e:  # noqa: BLE001
        return [], [f"youtube: ytInitialData parse failed: {e}"]

    renderers: list[dict] = []

    def walk(node, depth: int) -> None:
        if depth > 14:
            return
        if isinstance(node, dict):
            for key, val in node.items():
                if key == "videoRenderer" and isinstance(val, dict):
                    renderers.append(val)
                else:
                    walk(val, depth + 1)
        elif isinstance(node, list):
            for val in node:
                walk(val, depth + 1)

    walk(data, 0)
    items, seen = [], set()
    for r in renderers:
        vid = r.get("videoId") or ""
        if not vid or vid in seen:
            continue
        seen.add(vid)
        title = _runs_text(r.get("title", {})) or "Untitled"
        owner = r.get("ownerText") or r.get("longBylineText") or {}
        author = _runs_text(owner) or ""
        channel_url = ""
        runs = owner.get("runs") or []
        if runs:
            browse = (runs[0].get("navigationEndpoint") or {}).get(
                "browseEndpoint"
            ) or {}
            base = browse.get("canonicalBaseUrl") or ""
            cid = browse.get("browseId") or ""
            channel_url = (
                f"https://www.youtube.com{base}"
                if base
                else f"https://www.youtube.com/channel/{cid}"
                if cid
                else ""
            )
        body = _runs_text(r.get("descriptionSnippet", {}))[:500]
        pub_text = _runs_text(r.get("publishedTimeText", {})).strip()
        age = parse_age_days(pub_text)
        published = iso_days_ago(age) if age is not None else ""
        if older_than(published, cutoff):
            continue
        views = parse_views(_runs_text(r.get("viewCountText", {})))
        items.append(
            {
                "url": f"https://www.youtube.com/watch?v={vid}",
                "title": title,
                "body": body,
                "source": "youtube",
                "keyword": q,
                "author": author,
                "channel_url": channel_url,
                "score": views,
                "views": views,
                "metric": "views",
                "created": pub_text,
                "published": published,
                "created_at": now_iso(),
                "asset": f"assets/{vid}.jpg",
            }
        )
        if len(items) >= 12:
            break
    return items, errors


COLLECTORS = {
    "youtube": collect_youtube,
    "gnews": collect_gnews,
    "tiktok": collect_tiktok,
    "fbads": collect_fbads,
    "ttads": collect_ttads,
}


# ---------------- STORE: disk merge (§9.2/6.1) ----------------


def save_thumbnail(vid: str) -> bool:
    dest = ASSETS / f"{vid}.jpg"
    if dest.exists():
        return True
    try:
        req = urllib.request.Request(
            f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg", headers={"User-Agent": UA}
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
        dest.write_bytes(data)
        if db.configured():
            try:
                db.upload_asset(f"{vid}.jpg", data)
            except Exception as exc:  # noqa: BLE001 - thumbnail copy must not kill the fetch
                print(f"[db] thumbnail upload {vid}.jpg failed: {exc}")
        return True
    except Exception:  # noqa: BLE001 - fail-soft, item is kept
        return False


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
            f"https://www.tiktok.com/@{author}"
            if item.get("source") == "tiktok" and author
            else ""
        )
        changed = True
    return changed


def migrate_items() -> bool:
    items = load_json(ITEMS_FILE, [])
    if not isinstance(items, list):
        return False
    changed = False
    for item in items:
        changed = backfill_item(item) or changed
    if changed:
        atomic_write(ITEMS_FILE, items)
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
    return urllib.parse.urlunsplit(
        ("https", host or parts.netloc.lower(), path, clean_query, "")
    )


def norm_title(title: str) -> str:
    """Case/punctuation/space-insensitive title used for duplicate checks."""
    text = unicodedata.normalize("NFKC", title or "").casefold()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def title_trigrams(norm: str) -> set[str]:
    flat = norm.replace(" ", "")
    return {flat[i : i + 3] for i in range(len(flat) - 2)} if len(flat) >= 3 else {flat}


def near_dup(
    norm: str, pool: list[set[str]], threshold: float = NEAR_DUP_THRESHOLD
) -> bool:
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
    existing = load_json(ITEMS_FILE, [])
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
        norm = (
            norm_title(it.get("title") or "")
            if it.get("source") in ORGANIC_SOURCES
            else ""
        )
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
    atomic_write(ITEMS_FILE, existing + added_items)
    rebuild_index(existing + added_items)
    return len(added_items), skipped, errors


# ---------------- ANALYZE (§9.3) ----------------


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
    all_items = load_json(ITEMS_FILE, [])
    if not isinstance(all_items, list):
        all_items = []
    if q:
        items = [i for i in all_items if isinstance(i, dict) and i.get("keyword") == q]
    else:
        items = [
            i for i in all_items if isinstance(i, dict)
        ]  # empty q = whole local store
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
        prev = load_json(ANALYSIS_FILE, {})
        if not isinstance(prev, dict):
            prev = {}
        prev[q] = {
            k: v for k, v in out.items() if k != "items"
        }  # items already live in items.json
        atomic_write(ANALYSIS_FILE, prev)
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
    atomic_write(INDEX_FILE, index)


# ---------------- EXPORT / IMPORT / MAINTENANCE ----------------


def export_payload(q: str = "") -> dict:
    items = [i for i in load_json(ITEMS_FILE, []) if isinstance(i, dict)]
    archive = [a for a in load_archive() if isinstance(a, dict)]
    trash = [t for t in load_trash() if isinstance(t, dict)]
    if q:
        items = [i for i in items if i.get("keyword") == q]
        archive = [a for a in archive if a.get("keyword") == q]
        trash = [t for t in trash if t.get("keyword") == q]
    for item in items + archive + trash:
        if item.get("url") and not item.get("canonical_url"):
            item["canonical_url"] = canonical_url(item["url"])
    keywords = sorted(
        {i.get("keyword") for i in items + archive + trash if i.get("keyword")}
    )
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
            path = ASSETS / Path(asset).name
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
    if asset and not (ASSETS / Path(asset).name).is_file():
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
            atomic_write(ARCHIVE_FILE, archive)
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
            atomic_write(TRASH_FILE, trash)
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
            ASSETS.mkdir(exist_ok=True)
            for name in z.namelist():
                if not name.startswith("assets/") or not name.lower().endswith(".jpg"):
                    continue
                if ".." in name or not Path(name).name:
                    continue
                target = ASSETS / Path(name).name
                if not target.exists():
                    target.write_bytes(z.read(name))
    except (zipfile.BadZipFile, OSError, ValueError) as e:
        return {}, f"bad zip: {e}"
    return import_payload(payload)


def prune_old(days: int) -> dict:
    """Delete dated organic items older than N days across all keywords; ads stay."""
    if days <= 0:
        return {"removed": 0, "total": len(load_json(ITEMS_FILE, []))}
    cutoff = cutoff_iso(days)
    items = load_json(ITEMS_FILE, [])
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
        atomic_write(ITEMS_FILE, kept)
        rebuild_index(kept)
        analysis = load_json(ANALYSIS_FILE, {})
        if not isinstance(analysis, dict):
            analysis = {}
        for kw in affected:
            if kw and any(isinstance(i, dict) and i.get("keyword") == kw for i in kept):
                analysis[kw] = {
                    k: v for k, v in analyze(kw, write=False).items() if k != "items"
                }
            else:
                analysis.pop(kw, None)
        atomic_write(ANALYSIS_FILE, analysis)
        cleanup_orphan_assets(kept)
    return {"removed": removed, "total": len(kept), "days": days}


def _http_get(url: str, timeout: int = 25) -> str:
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept-Language": "th-TH,th;q=0.9,en;q=0.8"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "ignore")


def youtube_video_stats(vid: str) -> tuple[int | None, str, str]:
    """Fresh view count + channel from a watch page (fail-soft: (None, '', ''))."""
    try:
        html = _http_get(f"https://www.youtube.com/watch?v={vid}")
    except Exception:  # noqa: BLE001
        return None, "", ""
    views = None
    m = re.search(r'"viewCount":"(\d+)"', html)
    if m:
        views = int(m.group(1))
    cid = ""
    m = re.search(r'"channelId":"(UC[\w-]{10,})"', html)
    if m:
        cid = m.group(1)
    author = ""
    m = re.search(r'"author":"([^"]{1,200})"', html)
    if m:
        author = m.group(1)
    channel_url = f"https://www.youtube.com/channel/{cid}" if cid else ""
    return views, channel_url, author


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
    wanted = set(sources or ["youtube", "tiktok", "ttads"])
    all_items = load_json(ITEMS_FILE, [])
    if not isinstance(all_items, list):
        all_items = []
    target = [i for i in all_items if isinstance(i, dict) and i.get("keyword") == q]
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
            progress_set(source="youtube", stage=f"refreshing views {n}/{len(yt)}")
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
        progress_set(source=src, stage="refreshing stats")
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
            if (
                src == "tiktok"
                and not item.get("channel_url")
                and fresh_item.get("author")
            ):
                item["channel_url"] = f"https://www.tiktok.com/@{fresh_item['author']}"
            updated += 1
            touched.add(item.get("keyword"))

    atomic_write(ITEMS_FILE, all_items)
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
    items = load_json(ITEMS_FILE, [])
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
    atomic_write(ITEMS_FILE, items)
    rebuild_index(items)
    analyze(item["keyword"], write=True)
    if old_kw and old_kw != item["keyword"]:
        if any(isinstance(i, dict) and i.get("keyword") == old_kw for i in items):
            analyze(old_kw, write=True)
        else:
            analysis = load_json(ANALYSIS_FILE, {})
            if isinstance(analysis, dict):
                analysis.pop(old_kw, None)
                atomic_write(ANALYSIS_FILE, analysis)
    return {"item": item}, None


def delete_item(keyword: str, url: str) -> tuple[dict, str | None]:
    # 2.5 soft delete: move into trash (undo via /api/trash/restore)
    out = trash_items([{"keyword": keyword, "url": url}])
    if not out["trashed"]:
        return {}, "item not found"
    return {"removed": 1, "trashed": 1, "total": out["total"]}, None


def _analysis_sync(keywords: set[str]) -> None:
    analysis = load_json(ANALYSIS_FILE, {})
    if not isinstance(analysis, dict):
        analysis = {}
    items = load_json(ITEMS_FILE, [])
    for kw in keywords:
        if not kw:
            continue
        if any(isinstance(i, dict) and i.get("keyword") == kw for i in items):
            analysis[kw] = {
                k: v for k, v in analyze(kw, write=False).items() if k != "items"
            }
        else:
            analysis.pop(kw, None)
    atomic_write(ANALYSIS_FILE, analysis)


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
    data = load_json(ARCHIVE_FILE, [])
    return data if isinstance(data, list) else []


def archive_items(raw_items) -> dict:
    keys = _item_keys(raw_items)
    items = load_json(ITEMS_FILE, [])
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
        atomic_write(ITEMS_FILE, keep)
        atomic_write(ARCHIVE_FILE, archive)
        rebuild_index(keep)
        _analysis_sync(affected)
        cleanup_orphan_assets(keep)
    return {"archived": moved, "total_archive": len(archive), "total_items": len(keep)}


def restore_archived(raw_items) -> dict:
    keys = _item_keys(raw_items)
    items = load_json(ITEMS_FILE, [])
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
        atomic_write(ITEMS_FILE, items)
        atomic_write(ARCHIVE_FILE, keep)
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
            and (str(a.get("keyword") or ""), canonical_url(str(a.get("url") or "")))
            in keys
        )
    ]
    removed = len(archive) - len(kept)
    if removed:
        atomic_write(ARCHIVE_FILE, kept)
        cleanup_orphan_assets()
    return {"removed": removed, "total_archive": len(kept)}


# ---------------- TRASH (2.5 soft delete + undo) ----------------


def load_trash() -> list:
    data = load_json(TRASH_FILE, [])
    return data if isinstance(data, list) else []


def _trash_key(t) -> tuple[str, str]:
    return (str(t.get("keyword") or ""), canonical_url(str(t.get("url") or "")))


def trash_items(raw_items) -> dict:
    """Move matching active items into trash.json (soft delete). Returns trashed/total."""
    keys = _item_keys(raw_items)
    if not keys:
        return {"trashed": 0, "total": len(load_json(ITEMS_FILE, []))}
    items = load_json(ITEMS_FILE, [])
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
        atomic_write(ITEMS_FILE, keep)
        atomic_write(TRASH_FILE, trash)
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
    items = load_json(ITEMS_FILE, [])
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
        atomic_write(TRASH_FILE, keep)
        if restored:
            atomic_write(ITEMS_FILE, items)
            rebuild_index(items)
            _analysis_sync(affected)
    return {"restored": restored, "skipped": skipped, "total": len(keep)}


def purge_trash() -> int:
    """Drop trash older than TRASH_RETENTION_DAYS. Returns number removed."""
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=TRASH_RETENTION_DAYS)
    ).isoformat()
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
        atomic_write(TRASH_FILE, kept)
        cleanup_orphan_assets()
        print(
            f"trash: auto-purged {removed} item(s) older than {TRASH_RETENTION_DAYS}d"
        )
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
    items = load_json(ITEMS_FILE, [])
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
    atomic_write(ITEMS_FILE, keep)
    rebuild_index(keep)
    _analysis_sync(affected)
    cleanup_orphan_assets(keep)
    return {"changed": changed, "action": action, "total": len(keep)}, None


def clear_all_data() -> dict:
    """Wipe collected data + archive + trash + thumbnails. Profiles (user presets) are kept."""
    items = load_json(ITEMS_FILE, [])
    count = len(items) if isinstance(items, list) else 0
    archived = len(load_archive())
    trashed = len(load_trash())
    atomic_write(ITEMS_FILE, [])
    atomic_write(ARCHIVE_FILE, [])
    atomic_write(TRASH_FILE, [])
    atomic_write(INDEX_FILE, {})
    atomic_write(ANALYSIS_FILE, {})
    atomic_write(SOURCE_LOG_FILE, {})
    removed_assets = cleanup_orphan_assets([])
    return {
        "removed": count,
        "archived": archived,
        "trashed": trashed,
        "assets": removed_assets,
        "profiles_kept": True,
    }


def clear_keyword(q: str) -> dict:
    items = load_json(ITEMS_FILE, [])
    if not isinstance(items, list):
        items = []
    kept = [i for i in items if not (isinstance(i, dict) and i.get("keyword") == q)]
    removed = len(items) - len(kept)
    if removed:
        atomic_write(ITEMS_FILE, kept)
        rebuild_index(kept)
        cleanup_orphan_assets(kept)
    # a keyword with 0 fetched items still has an analysis row: drop it too
    analysis = load_json(ANALYSIS_FILE, {})
    if isinstance(analysis, dict) and q in analysis:
        analysis.pop(q, None)
        atomic_write(ANALYSIS_FILE, analysis)
    return {"removed": removed, "total": len(kept)}


def cleanup_orphan_assets(items: list | None = None) -> int:
    if items is None:
        items = load_json(ITEMS_FILE, [])
    pool = list(items) if isinstance(items, list) else []
    pool += [a for a in load_archive() if isinstance(a, dict)]
    pool += [t for t in load_trash() if isinstance(t, dict)]
    used = {Path(str(i.get("asset"))).name for i in pool if i.get("asset")}
    removed = 0
    if ASSETS.is_dir():
        for path in ASSETS.glob("*.jpg"):
            if path.name not in used:
                try:
                    path.unlink()
                    removed += 1
                except OSError:
                    pass
    return removed


def log_source(src: str, ok: bool, count: int, error: str = "") -> None:
    log = load_json(SOURCE_LOG_FILE, {})
    if not isinstance(log, dict):
        log = {}
    log[src] = {"at": now_iso(), "ok": ok, "count": count, "error": error[:300]}
    atomic_write(SOURCE_LOG_FILE, log)


def status_payload() -> dict:
    items = load_json(ITEMS_FILE, [])
    if not isinstance(items, list):
        items = []
    data_bytes = (
        sum(p.stat().st_size for p in DATA.glob("*.json") if p.is_file())
        if DATA.is_dir()
        else 0
    )
    assets = list(ASSETS.glob("*.jpg")) if ASSETS.is_dir() else []
    return {
        "app_version": APP_VERSION,
        "backend": "supabase" if db.configured() else "json",
        "items": len(items),
        "archived": len(load_archive()),
        "keywords": len(
            {
                i.get("keyword")
                for i in items
                if isinstance(i, dict) and i.get("keyword")
            }
        ),
        "data_bytes": data_bytes,
        "assets": len(assets),
        "assets_bytes": sum(p.stat().st_size for p in assets),
        "trash_count": len(load_trash()),
        "sources": load_json(SOURCE_LOG_FILE, {}),
        "sessions": {
            k: (ROOT / "sessions" / k).is_dir() for k in ("tiktok", "facebook")
        },
    }


def keyword_list() -> dict:
    """2.6 keyword suggestions: count + last fetch date, from items + archive."""
    pool = [i for i in load_json(ITEMS_FILE, []) if isinstance(i, dict)]
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


# ---------------- PROFILES (§9.3 profiles) ----------------


def load_profiles() -> list:
    data = load_json(PROFILES_FILE, [])
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
        progress_set(
            keyword=kw, done=i, total=len(kws), source="", stage="next keyword"
        )
        kw_new, kw_errors = [], []
        for src in prof["sources"]:
            if cancel.is_set():
                cancelled = True
                break
            fn = COLLECTORS.get(src)
            if fn is None:
                kw_errors.append(f"{kw} {src}: not implemented yet")
                continue
            progress_set(source=src, stage="starting")
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


# ---------------- SERVE (§9.4) ----------------

CTYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".json": "application/json; charset=utf-8",
}


def _write(handler, data: bytes) -> None:
    try:
        handler.wfile.write(data)
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
        pass  # client cancelled/closed the tab


ALLOW_ORIGIN = lambda: (os.environ.get("ALLOW_ORIGIN") or "").strip()


def _cors(handler) -> None:
    origin = ALLOW_ORIGIN()
    if origin:
        handler.send_header("Access-Control-Allow-Origin", origin)
        handler.send_header("Vary", "Origin")


def _send(handler, path: Path, ctype: str | None = None) -> None:
    if not path.is_file():
        _send_json(handler, {"error": "not found"}, 404)
        return
    data = path.read_bytes()
    handler.send_response(200)
    _cors(handler)
    handler.send_header(
        "Content-Type", ctype or CTYPES.get(path.suffix, "application/octet-stream")
    )
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    _write(handler, data)


def _send_bytes(handler, data: bytes, ctype: str) -> None:
    handler.send_response(200)
    _cors(handler)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    _write(handler, data)


def _redirect(handler, to: str) -> None:
    handler.send_response(302)
    _cors(handler)
    handler.send_header("Location", to)
    handler.send_header("Content-Length", "0")
    handler.end_headers()


def _send_json(handler, obj, status: int = 200) -> None:
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    _cors(handler)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    _write(handler, data)


def _send_download(handler, data: bytes, ctype: str, filename: str) -> None:
    handler.send_response(200)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Content-Disposition", f'attachment; filename="{filename}"')
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    _write(handler, data)


def _resolve(base: Path, rel: str) -> Path | None:
    path = (base / rel).resolve()
    try:
        path.relative_to(base.resolve())
    except ValueError:
        return None
    return path


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silenced per spec
        pass

    def do_OPTIONS(self):  # noqa: N802
        self.send_response(204)
        _cors(self)
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)
        if path in ("/", "/index.html"):
            _send(self, ROOT / "index.html")
        elif path in ("/live", "/live/", "/live/index.html"):
            _send(self, LIVE / "index.html")
        elif path in ("/dashboard-live.html", "/dashboard.html"):
            _redirect(self, "/live/")
        elif path == "/app/dashboard.html":
            _redirect(self, "/")
        elif path == "/api/summary":
            q = urllib.parse.parse_qs(parsed.query).get("q", [""])[0]
            _send_json(self, analyze(q, write=False))
        elif path == "/api/profiles":
            _send_json(self, load_profiles())
        elif path == "/api/progress":
            _send_json(self, progress_get())
        elif path == "/api/status":
            _send_json(self, status_payload())
        elif path == "/api/archive":
            _send_json(self, load_archive())
        elif path == "/api/trash":
            _send_json(self, load_trash())
        elif path == "/api/keywords":
            _send_json(self, keyword_list())
        elif path in ("/api/export", "/api/export.zip"):
            q = (urllib.parse.parse_qs(parsed.query).get("q", [""])[0] or "").strip()
            payload = export_payload(q)
            stamp = datetime.now().strftime("%Y%m%d")
            if path.endswith(".zip"):
                data = export_zip(payload)
                _send_download(
                    self, data, "application/zip", f"social-tracker-{stamp}.zip"
                )
            else:
                data = json.dumps(payload, ensure_ascii=False, indent=1).encode("utf-8")
                _send_download(
                    self,
                    data,
                    "application/json; charset=utf-8",
                    f"social-tracker-{stamp}.json",
                )
        elif path.startswith("/fonts/"):
            rel = path[len("/fonts/") :]
            found = _resolve(ASSETS / "fonts", rel)
            _send(self, found) if found else _send_json(
                self, {"error": "not found"}, 404
            )
        elif path.startswith("/assets/"):
            rel = path[len("/assets/") :]
            name = Path(rel).name
            if db.configured() and "/" not in rel and name.lower().endswith(".jpg"):
                try:
                    data = db.fetch_asset(name)
                except Exception as exc:  # noqa: BLE001 - served below from the disk cache
                    print(f"[db] asset {name} failed: {exc}")
                    data = None
                if data:
                    _send_bytes(self, data, "image/jpeg")
                    return
                if db.strict():
                    _send_json(self, {"error": "not found"}, 404)
                    return
            found = _resolve(ASSETS, rel)
            _send(self, found) if found else _send_json(
                self, {"error": "not found"}, 404
            )
        elif path.startswith("/app/"):
            found = _resolve(APP, path[len("/app/") :])
            _send(self, found) if found else _send_json(
                self, {"error": "not found"}, 404
            )
        else:
            found = _resolve(ROOT, path.lstrip("/"))
            if found is not None and found.is_file():
                _send(self, found)
            else:
                _send_json(self, {"error": "not found"}, 404)

    def do_POST(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        raw_body = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw_body.decode("utf-8") or "{}")
        except Exception:
            body = {}
        q = str(body.get("q") or "").strip()
        try:
            max_age_days = int(body.get("max_age_days") or 0)
        except (TypeError, ValueError):
            _send_json(self, {"error": "bad max_age_days"}, 400)
            return
        if max_age_days < 0 or max_age_days > 3650:
            _send_json(self, {"error": "bad max_age_days"}, 400)
            return
        if parsed.path == "/api/import":
            try:
                result, err = (
                    import_zip(raw_body)
                    if raw_body[:2] == b"PK"
                    else import_payload(body)
                )
            except Exception as e:  # noqa: BLE001 - always answer the client
                _send_json(self, {"error": f"import failed: {e}"}, 500)
                return
            if err:
                _send_json(self, {"error": err}, 400)
                return
            _send_json(self, result)
        elif parsed.path == "/api/cancel":
            cancel_fetch()
            progress_stage("cancel requested")
            _send_json(self, {"cancelled": True})
        elif parsed.path == "/api/refresh-stats":
            if not q:
                _send_json(self, {"error": "missing q"}, 400)
                return
            raw_sources = body.get("sources")
            sources = (
                [str(s).strip().lower() for s in raw_sources if str(s).strip()]
                if isinstance(raw_sources, list)
                else ["youtube", "tiktok", "ttads"]
            )
            cancel = new_fetch_cancel()
            progress_set(
                active=True,
                keyword=q,
                source="",
                stage="refresh stats",
                done=0,
                total=len(sources),
                started=time.time(),
                updated=time.time(),
            )
            try:
                out = refresh_stats(q, sources, cancel, body.get("items"))
                out["keyword"] = q
                _send_json(self, out)
            except Exception as e:  # noqa: BLE001
                _send_json(self, {"error": f"refresh failed: {e}"}, 500)
            finally:
                progress_set(active=False, stage="done")
        elif parsed.path == "/api/trash/restore":
            raw = body.get("items")
            if not isinstance(raw, list) or not raw:
                _send_json(self, {"error": "missing items"}, 400)
                return
            _send_json(self, restore_trash(raw))
        elif parsed.path == "/api/items":
            result, err = create_item(
                body.get("item") if isinstance(body.get("item"), dict) else body
            )
            if err:
                _send_json(self, {"error": err}, 400)
                return
            _send_json(self, result, 201)
        elif parsed.path == "/api/items/bulk":
            action = str(body.get("action") or "").strip().lower()
            if action not in ("delete", "move"):
                _send_json(self, {"error": "bad action"}, 400)
                return
            result, err = bulk_items(
                action, body.get("items"), str(body.get("to_keyword") or "")
            )
            if err:
                _send_json(self, {"error": err}, 400)
                return
            _send_json(self, result)
        elif parsed.path == "/api/archive":
            raw = body.get("items")
            if not isinstance(raw, list) or not raw:
                _send_json(self, {"error": "missing items"}, 400)
                return
            _send_json(self, archive_items(raw))
        elif parsed.path == "/api/archive/restore":
            raw = body.get("items")
            if not isinstance(raw, list) or not raw:
                _send_json(self, {"error": "missing items"}, 400)
                return
            _send_json(self, restore_archived(raw))
        elif parsed.path == "/api/clear-all":
            _send_json(self, clear_all_data())
        elif parsed.path == "/api/clear":
            if not q:
                _send_json(self, {"error": "missing q"}, 400)
                return
            _send_json(self, clear_keyword(q))
        elif parsed.path == "/api/prune":
            try:
                days = int(body.get("days") or 0)
            except (TypeError, ValueError):
                days = 0
            if days <= 0:
                _send_json(self, {"error": "bad days"}, 400)
                return
            _send_json(self, prune_old(days))
        elif parsed.path == "/api/profiles":
            prof, err = validate_profile(
                body.get("name"), body.get("keywords"), body.get("sources")
            )
            if err:
                _send_json(self, {"error": err}, 400)
                return
            prof.update(
                {
                    "id": str(uuid.uuid4()),
                    "created_at": now_iso(),
                    "updated_at": now_iso(),
                }
            )
            profiles = load_profiles()
            profiles.append(prof)
            atomic_write(PROFILES_FILE, profiles)
            _send_json(self, prof, 201)
        elif parsed.path == "/api/fetch" and str(body.get("profile_id") or "").strip():
            pid = str(body["profile_id"]).strip()
            prof = next((p for p in load_profiles() if p.get("id") == pid), None)
            if not prof:
                _send_json(self, {"error": "profile not found"}, 404)
                return
            mode = str(body.get("mode") or "public").strip().lower()
            if mode not in ("public", "session"):
                _send_json(self, {"error": "bad mode (public|session)"}, 400)
                return
            cancel = new_fetch_cancel()
            progress_set(
                active=True,
                keyword=prof["keywords"][0],
                source="",
                stage="queue",
                done=0,
                total=len(prof["keywords"]),
                started=time.time(),
                updated=time.time(),
            )
            try:
                out = fetch_profile(prof, mode, max_age_days, cancel)
                kw0 = prof["keywords"][0]
                progress_set(source="analysis", stage="scoring items")
                out.update(analyze(kw0, write=False))
                out["per_keyword"] = out.get("per_keyword", [])
                out["mode"] = mode
                _send_json(self, out)
            finally:
                progress_set(active=False, stage="done")
        elif parsed.path == "/api/fetch":
            if not q:
                _send_json(self, {"error": "missing q"}, 400)
                return
            raw_sources = body.get("sources")
            if raw_sources is None:
                sources = ["youtube"]
            else:
                sources = [
                    str(s).strip().lower() for s in raw_sources if str(s).strip()
                ]
            if not sources:
                _send_json(self, {"error": "no source selected"}, 400)
                return
            mode = str(body.get("mode") or "public").strip().lower()
            if mode not in ("public", "session"):
                _send_json(self, {"error": "bad mode (public|session)"}, 400)
                return
            new_items, errors = [], []
            cancel = new_fetch_cancel()
            cancelled = False
            progress_set(
                active=True,
                keyword=q,
                source="",
                stage="queue",
                done=0,
                total=len(sources),
                started=time.time(),
                updated=time.time(),
            )
            try:
                for i, src in enumerate(sources):
                    if cancel.is_set():
                        cancelled = True
                        break
                    fn = COLLECTORS.get(src)
                    if fn is None:
                        errors.append(f"{src}: not implemented yet")
                        continue
                    progress_set(
                        source=src, stage="starting", done=i, total=len(sources)
                    )
                    if src == "tiktok":
                        items, errs = fn(q, mode, max_age_days)
                    else:
                        items, errs = fn(q, max_age_days)
                    log_source(src, not errs, len(items), "; ".join(errs))
                    new_items += items
                    errors += errs
                progress_set(source="disk", stage="saving items")
                added, skipped, thumb_errors = merge_items(new_items, q, max_age_days)
                errors += thumb_errors
                progress_set(source="analysis", stage="scoring items")
                out = analyze(q, write=True)
                out.update(
                    {
                        "added": added,
                        "duplicates": skipped,
                        "errors": errors,
                        "fetched_at": now_iso(),
                        "mode": mode,
                        "max_age_days": max_age_days,
                        "cancelled": cancelled,
                    }
                )
                _send_json(self, out)
            finally:
                progress_set(active=False, stage="done")
        elif parsed.path == "/api/analyze":
            if not q:
                _send_json(self, {"error": "missing q"}, 400)
                return
            _send_json(
                self, {"analysis": analyze(q, write=True), "fetched_at": now_iso()}
            )
        else:
            _send_json(self, {"error": "not found"}, 404)

    def do_PUT(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except Exception:
            body = {}
        if parsed.path == "/api/items":
            result, err = update_item(
                str(body.get("keyword") or ""),
                str(body.get("url") or ""),
                body.get("patch") if isinstance(body.get("patch"), dict) else body,
            )
            if err:
                _send_json(self, {"error": err}, 400)
                return
            _send_json(self, result)
            return
        if parsed.path != "/api/profiles":
            _send_json(self, {"error": "not found"}, 404)
            return
        profiles = load_profiles()
        pid = str(body.get("id") or "").strip()
        idx = next((i for i, p in enumerate(profiles) if p.get("id") == pid), None)
        if idx is None:
            _send_json(self, {"error": "profile not found"}, 404)
            return
        cur = profiles[idx]
        prof, err = validate_profile(
            body.get("name", cur["name"]),
            body.get("keywords", cur["keywords"]),
            body.get("sources", cur["sources"]),
        )
        if err:
            _send_json(self, {"error": err}, 400)
            return
        prof.update(
            {
                "id": pid,
                "created_at": cur.get("created_at", now_iso()),
                "updated_at": now_iso(),
            }
        )
        profiles[idx] = prof
        atomic_write(PROFILES_FILE, profiles)
        _send_json(self, prof)

    def do_DELETE(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except Exception:
            body = {}
        if parsed.path == "/api/items":
            result, err = delete_item(
                str(body.get("keyword") or ""), str(body.get("url") or "")
            )
            if err:
                _send_json(self, {"error": err}, 404 if "not found" in err else 400)
                return
            _send_json(self, result)
            return
        if parsed.path == "/api/archive":
            result = delete_archived(body.get("items") or [])
            _send_json(self, result)
            return
        if parsed.path == "/api/trash":
            # 2.5 manual purge all trash
            trash = load_trash()
            atomic_write(TRASH_FILE, [])
            cleanup_orphan_assets()
            _send_json(self, {"purged": len(trash)})
            return
        if parsed.path != "/api/profiles":
            _send_json(self, {"error": "not found"}, 404)
            return
        pid = str(body.get("id") or "").strip()
        profiles = load_profiles()
        kept = [p for p in profiles if p.get("id") != pid]
        if len(kept) == len(profiles):
            _send_json(self, {"error": "profile not found"}, 404)
            return
        atomic_write(PROFILES_FILE, kept)
        _send_json(self, {"ok": True})


def main() -> None:
    ensure_data()
    migrate_items()
    purge_trash()  # 2.5 auto-purge expired trash on server start
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(
        f"social-tracker on http://{HOST}:{PORT}  (mock: /, live: /live/)"
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
