#!/usr/bin/env python3
"""social-tracker localhost server (ARCHITECTURE.md §9.2-9.4, YouTube slice).

Stdlib only. Binds 127.0.0.1:8000.
  GET /  -> app/dashboard.html (mockup, per spec)
  GET /dashboard-live.html -> app/dashboard-live.html (live, same static folder)
  GET /fonts/* -> assets/fonts/*     GET /assets/* -> assets/* (YT thumbnails)
  GET /api/summary?q=      -> analyze(q) JSON, read-only, never writes
  POST /api/fetch {q, sources?, mode?, max_age_days?} -> collect selected sources
                               -> merge disk -> analyze (writes); max_age_days=0 = all time
  POST /api/fetch {profile_id} -> collect every keyword x source in the
                               profile (sequential) -> merged -> per_keyword
  GET/POST/PUT/DELETE /api/profiles -> profile CRUD (data/profiles.json)
  POST /api/analyze {q}    -> analyze only (writes analysis.json)
Collect failures go into errors[] and never crash the server.
Only POST presses write to disk; GET endpoints never write.
"""
from __future__ import annotations

import threading
import json
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ElementTree
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"
DATA = ROOT / "data"
ASSETS = ROOT / "assets"
ITEMS_FILE = DATA / "items.json"
INDEX_FILE = DATA / "index.json"
ANALYSIS_FILE = DATA / "analysis.json"
PROFILES_FILE = DATA / "profiles.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
HOST, PORT = "127.0.0.1", 8000

EN_STOP = {"the", "and", "for", "with", "that", "this", "from", "are", "will",
           "have", "what", "when", "your", "you", "our", "into", "more", "than",
           "then", "them", "they", "about", "which", "their", "there"}
SUGGESTIONS = [
    "30-sec clip: open on the pain behind {q}, demo the fix, close with one LINE CTA.",
    "SEO post: answer \"{q}\" in one clear headline + hashtags + a single CTA.",
    "3-part FAQ: three shorts answering the most-asked questions about {q}.",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_data() -> None:
    DATA.mkdir(exist_ok=True)
    ASSETS.mkdir(exist_ok=True)
    for path, empty in ((ITEMS_FILE, []), (INDEX_FILE, {}), (ANALYSIS_FILE, {}), (PROFILES_FILE, [])):
        if not path.exists():
            path.write_text(json.dumps(empty, ensure_ascii=False), encoding="utf-8")
    for orphan in (DATA / "items.json.tmp", DATA / "index.json.tmp",
                   DATA / "analysis.json.tmp", DATA / "profiles.json.tmp"):
        orphan.unlink(missing_ok=True)


def atomic_write(path: Path, obj) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def load_json(path: Path, default):
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
AGE_UNITS = {"second": 0, "sec": 0, "minute": 0, "min": 0, "hour": 0, "hr": 0,
             "day": 1, "week": 7, "month": 30, "year": 365,
             "วินาที": 0, "วิ": 0, "นาที": 0, "ชั่วโมง": 0, "ชม": 0,
             "วัน": 1, "สัปดาห์": 7, "เดือน": 30, "ปี": 365}
GNEWS_WHEN = {7: "when:7d", 30: "when:30d", 365: "when:1y"}
YT_SP = {7: "EgIIAw==", 30: "EgIIBA==", 365: "EgIIBQ=="}  # week, month, year


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
    try:
        url = ("https://news.google.com/rss/search?q="
               + urllib.parse.quote_plus(query) + "&hl=th&gl=TH&ceid=TH:th")
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
        items.append({"url": link, "title": title, "body": title[:500],
                      "source": "gnews", "keyword": q, "author": "google-news",
                      "score": 0, "created": pub, "published": published,
                      "created_at": now_iso(), "asset": None})
        if len(items) >= 10:
            break
    return items, []


PW_SESSIONS = ROOT / "sessions"
PW_TIMEOUT_MS = 35000
PW_LIMIT = 12
PW_LOCK = threading.Lock()  # ทีละ 1 รอบ Playwright: กัน thread ชนกันและ profile dir ชนกัน


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
        return None, "playwright not installed — run: python -m pip install playwright && python -m playwright install chromium"
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
        return None, (f"{kind}: no login session — run `python pw_login.py {kind}`, "
                      "log in once in the opened browser, then fetch again")
    browser = playwright.chromium.launch_persistent_context(
        str(PW_SESSIONS / kind), headless=True,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        user_agent=UA, locale="th-TH", timezone_id="Asia/Bangkok", timeout=PW_TIMEOUT_MS)
    return browser, None


def _pw_public_context(playwright, kind: str):
    """browser + context สด public ไม่ต้อง login — ไม่แตะ profile dir (ไม่ชนกันหลายโปรเซส)"""
    try:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            timeout=PW_TIMEOUT_MS)
        ctx = browser.new_context(
            user_agent=UA, locale="en-US", timezone_id="Asia/Bangkok")
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
        page.goto("https://www.tiktok.com/search?q=" + urllib.parse.quote(q) + "&lang=en",
                  wait_until="domcontentloaded", timeout=PW_TIMEOUT_MS)
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
        for entry in (payload.get("data") or []):
            item = (entry or {}).get("item") or {}
            vid = str(item.get("id") or "")
            if not vid or vid in seen:
                continue
            seen.add(vid)
            published = ""
            ts = item.get("createTime")
            if ts:
                try:
                    published = datetime.fromtimestamp(int(ts), timezone.utc).isoformat()
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
            items.append({
                "url": f"https://www.tiktok.com/@{author}/video/{vid}" if author
                       else f"https://www.tiktok.com/video/{vid}",
                "title": desc[:500] or f"TikTok video {vid}",
                "body": desc[:500],
                "source": "tiktok",
                "keyword": q,
                "author": author,
                "score": score,
                "created": published,
                "published": published,
                "created_at": now_iso(),
                "asset": None,
            })
            if len(items) >= PW_LIMIT:
                return items
    return items


def collect_tiktok(q: str, mode: str = "public", max_age_days: int = 0) -> tuple[list, list[str]]:
    """TikTok search via Playwright (real browser, no API key). mode=public|session.
    Public mode reads the search page's own JSON and filters by createTime. Fail-soft; never raises."""
    sync_playwright, err = _playwright()
    if err:
        return [], [f"tiktok: {err}"]
    tag = "tiktok(public)" if mode != "session" else "tiktok(session)"
    last_err = None
    for attempt in range(2):
        try:
            with _pw_locked(), sync_playwright() as p:
                if mode == "session":
                    ctx, err = _pw_context(p, "tiktok")
                else:
                    ctx, err = _pw_public_context(p, "tiktok")
                if err:
                    return [], [err]
                try:
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
    hint = "blocked or login wall" if mode != "session" else "login expired or blocked — re-run pw_login.py"
    return [], [f"{tag}: no videos{win} ({hint})"]


# ---------------- AD LIBRARIES (public pages, no login) ----------------

TTCC_PERIOD = {7: 7, 30: 30, 365: 180}  # TikTok CC supports 7/30/180 days


def _parse_en_date(text: str) -> str:
    for fmt in ("%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime((text or "").strip(), fmt).replace(
                tzinfo=timezone.utc).isoformat()
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
            with _pw_locked(), sync_playwright() as p:
                ctx, err = _pw_public_context(p, "fbads")
                if err:
                    return [], [err]
                try:
                    page = ctx.new_page()
                    url = ("https://www.facebook.com/ads/library/?active_status=active"
                           "&ad_type=all&country=TH&media_type=all&search_type=keyword_unordered"
                           "&q=" + urllib.parse.quote_plus(q))
                    page.goto(url, wait_until="domcontentloaded", timeout=PW_TIMEOUT_MS)
                    page.wait_for_timeout(12000)
                    for _ in range(3):
                        page.mouse.wheel(0, 3000)
                        page.wait_for_timeout(2500)
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
        items.append({
            "url": f"https://www.facebook.com/ads/library/?id={r['id']}",
            "title": title[:500], "body": copy, "source": "fbads",
            "keyword": q, "author": adv, "score": 0,
            "created": r.get("started") or "",
            "published": _parse_en_date(r.get("started") or ""),
            "created_at": now_iso(), "asset": None,
        })
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
            with _pw_locked(), sync_playwright() as p:
                ctx, err = _pw_public_context(p, "ttads")
                if err:
                    return [], [err]
                try:
                    page = ctx.new_page()
                    url = ("https://ads.tiktok.com/business/creativecenter/inspiration/topads/pc/en"
                           f"?period={period}&region=TH")
                    page.goto(url, wait_until="domcontentloaded", timeout=PW_TIMEOUT_MS)
                    page.wait_for_timeout(12000)
                    page.keyboard.press("Escape")  # promo modal blocks clicks
                    page.wait_for_timeout(1000)
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
        items.append({
            "url": r["url"], "title": title[:500], "body": text,
            "source": "ttads", "keyword": q, "author": "", "score": score,
            "created": "", "published": "", "created_at": now_iso(), "asset": None,
        })
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
    try:
        url = ("https://www.youtube.com/results?search_query="
               + urllib.parse.quote_plus(q) + "&hl=th"
               + ("&sp=" + urllib.parse.quote(sp, safe="") if sp else ""))
        req = urllib.request.Request(url, headers={
            "User-Agent": UA, "Accept-Language": "th-TH,th;q=0.9,en;q=0.8"})
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
        author = (_runs_text(r.get("owner", {}))
                  or _runs_text(r.get("longBylineText", {})) or "")
        body = _runs_text(r.get("descriptionSnippet", {}))[:500]
        pub_text = _runs_text(r.get("publishedTimeText", {})).strip()
        age = parse_age_days(pub_text)
        published = iso_days_ago(age) if age is not None else ""
        if older_than(published, cutoff):
            continue
        items.append({
            "url": f"https://www.youtube.com/watch?v={vid}",
            "title": title,
            "body": body,
            "source": "youtube",
            "keyword": q,
            "author": author,
            "score": parse_views(_runs_text(r.get("viewCountText", {}))),
            "created": pub_text,
            "published": published,
            "created_at": now_iso(),
            "asset": f"assets/{vid}.jpg",
        })
        if len(items) >= 12:
            break
    return items, errors


COLLECTORS = {"youtube": collect_youtube, "gnews": collect_gnews,
              "tiktok": collect_tiktok,
              "fbads": collect_fbads, "ttads": collect_ttads}


# ---------------- STORE: disk merge (§9.2/6.1) ----------------

def save_thumbnail(vid: str) -> bool:
    dest = ASSETS / f"{vid}.jpg"
    if dest.exists():
        return True
    try:
        req = urllib.request.Request(
            f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
            headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as resp:
            dest.write_bytes(resp.read())
        return True
    except Exception:  # noqa: BLE001 - fail-soft, item is kept
        return False


DATED_SOURCES = {"youtube", "gnews", "tiktok"}  # ads are current by definition


def merge_items(new_items: list, keyword: str = "", max_age_days: int = 0) -> tuple[int, list[str]]:
    errors: list[str] = []
    existing = load_json(ITEMS_FILE, [])
    if not isinstance(existing, list):
        existing = []
    if max_age_days > 0 and keyword:
        cutoff = cutoff_iso(max_age_days)
        existing = [i for i in existing if not (
            isinstance(i, dict) and i.get("keyword") == keyword
            and i.get("source") in DATED_SOURCES
            and older_than(i.get("published") or "", cutoff))]
    known = {i.get("url") for i in existing if isinstance(i, dict) and i.get("url")}
    added_items = []
    for it in new_items:
        if not it.get("url") or it["url"] in known:
            continue
        known.add(it["url"])
        added_items.append(it)
    for it in added_items:
        if it.get("source") == "youtube":
            vid = it["url"].split("v=", 1)[-1]
            if not save_thumbnail(vid):
                it["asset"] = None
                errors.append(f"youtube thumb {vid}: failed")
    atomic_write(ITEMS_FILE, existing + added_items)
    rebuild_index(existing + added_items)
    return len(added_items), errors


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
    items = [i for i in all_items if isinstance(i, dict) and i.get("keyword") == q]
    items.sort(key=lambda i: (+i.get("score") or 0), reverse=True)
    by_source = dict(Counter(i.get("source") or "" for i in items))
    hot = items[0].get("title", "") if items else ""
    out = {
        "keyword": q,
        "total": len(items),
        "by_source": by_source,
        "items": items,
        "hot": hot,
        "top_terms": top_terms(items[:100]),
        "suggestions": [s.format(q=q) for s in SUGGESTIONS],
    }
    if write and q:
        prev = load_json(ANALYSIS_FILE, {})
        if not isinstance(prev, dict):
            prev = {}
        prev[q] = out
        atomic_write(ANALYSIS_FILE, prev)
    return out


def rebuild_index(items: list) -> None:
    by_keyword: dict[str, list] = {}
    for it in items:
        if isinstance(it, dict) and it.get("keyword"):
            by_keyword.setdefault(it["keyword"], []).append(it)
    index = {}
    for kw, kw_items in by_keyword.items():
        kw_items = sorted(kw_items, key=lambda i: (+i.get("score") or 0), reverse=True)
        index[kw] = {
            "total": len(kw_items),
            "by_source": dict(Counter(i.get("source") or "" for i in kw_items)),
            "hot": kw_items[0].get("title", "") if kw_items else "",
            "top_terms": top_terms(kw_items[:100]),
        }
    atomic_write(INDEX_FILE, index)


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


def fetch_profile(prof: dict, mode: str = "public", max_age_days: int = 0) -> dict:
    """Run every keyword x source in the profile (manual trigger, sequential). mode=public|session for TikTok/FB."""
    total_added, all_errors, per_keyword = 0, [], []
    for kw in prof["keywords"]:
        kw_new, kw_errors = [], []
        for src in prof["sources"]:
            fn = COLLECTORS.get(src)
            if fn is None:
                kw_errors.append(f"{kw} {src}: not implemented yet")
                continue
            if src == "tiktok":
                items, errs = fn(kw, mode, max_age_days)
            else:
                items, errs = fn(kw, max_age_days)
            kw_new += items
            kw_errors += errs
        added, thumb_errors = merge_items(kw_new, kw, max_age_days)
        kw_errors += thumb_errors
        kw_out = analyze(kw, write=True)
        total_added += added
        all_errors += [f"[{kw}] {e}" for e in kw_errors]
        per_keyword.append({"keyword": kw, "added": added, "errors": kw_errors,
                            "total": kw_out["total"], "by_source": kw_out["by_source"]})
    return {"keyword": prof["name"], "per_keyword": per_keyword,
            "added": total_added, "errors": all_errors, "fetched_at": now_iso(),
            "max_age_days": max_age_days}


# ---------------- SERVE (§9.4) ----------------

CTYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
          ".svg": "image/svg+xml", ".jpg": "image/jpeg", ".png": "image/png",
          ".webp": "image/webp", ".woff2": "font/woff2", ".ttf": "font/ttf",
          ".json": "application/json; charset=utf-8"}


def _send(handler, path: Path, ctype: str | None = None) -> None:
    if not path.is_file():
        _send_json(handler, {"error": "not found"}, 404)
        return
    data = path.read_bytes()
    handler.send_response(200)
    handler.send_header("Content-Type", ctype or CTYPES.get(path.suffix, "application/octet-stream"))
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def _send_json(handler, obj, status: int = 200) -> None:
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


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

    def do_GET(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)
        if path == "/":
            _send(self, APP / "dashboard.html")
        elif path == "/api/summary":
            q = urllib.parse.parse_qs(parsed.query).get("q", [""])[0]
            _send_json(self, analyze(q, write=False))
        elif path == "/api/profiles":
            _send_json(self, load_profiles())
        elif path.startswith("/fonts/"):
            rel = path[len("/fonts/"):]
            found = _resolve(ASSETS / "fonts", rel)
            _send(self, found) if found else _send_json(self, {"error": "not found"}, 404)
        elif path.startswith("/assets/"):
            rel = path[len("/assets/"):]
            found = _resolve(ASSETS, rel)
            _send(self, found) if found else _send_json(self, {"error": "not found"}, 404)
        elif path.startswith("/app/"):
            found = _resolve(APP, path[len("/app/"):])
            _send(self, found) if found else _send_json(self, {"error": "not found"}, 404)
        else:
            found = _resolve(APP, path.lstrip("/"))
            if found is not None:
                _send(self, found)
            else:
                _send_json(self, {"error": "not found"}, 404)

    def do_POST(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
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
        if parsed.path == "/api/profiles":
            prof, err = validate_profile(body.get("name"), body.get("keywords"), body.get("sources"))
            if err:
                _send_json(self, {"error": err}, 400)
                return
            prof.update({"id": f"p{int(datetime.now(timezone.utc).timestamp() * 1000):x}",
                         "created_at": now_iso(), "updated_at": now_iso()})
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
            out = fetch_profile(prof, mode, max_age_days)
            kw0 = prof["keywords"][0]
            out.update(analyze(kw0, write=False))
            out["per_keyword"] = out.get("per_keyword", [])
            out["mode"] = mode
            _send_json(self, out)
        elif parsed.path == "/api/fetch":
            if not q:
                _send_json(self, {"error": "missing q"}, 400)
                return
            raw_sources = body.get("sources")
            if raw_sources is None:
                sources = ["youtube"]
            else:
                sources = [str(s).strip().lower() for s in raw_sources if str(s).strip()]
            if not sources:
                _send_json(self, {"error": "no source selected"}, 400)
                return
            mode = str(body.get("mode") or "public").strip().lower()
            if mode not in ("public", "session"):
                _send_json(self, {"error": "bad mode (public|session)"}, 400)
                return
            new_items, errors = [], []
            for src in sources:
                fn = COLLECTORS.get(src)
                if fn is None:
                    errors.append(f"{src}: not implemented yet")
                    continue
                if src == "tiktok":
                    items, errs = fn(q, mode, max_age_days)
                else:
                    items, errs = fn(q, max_age_days)
                new_items += items
                errors += errs
            added, thumb_errors = merge_items(new_items, q, max_age_days)
            errors += thumb_errors
            out = analyze(q, write=True)
            out.update({"added": added, "errors": errors, "fetched_at": now_iso(),
                        "mode": mode, "max_age_days": max_age_days})
            _send_json(self, out)
        elif parsed.path == "/api/analyze":
            if not q:
                _send_json(self, {"error": "missing q"}, 400)
                return
            _send_json(self, {"analysis": analyze(q, write=True),
                              "fetched_at": now_iso()})
        else:
            _send_json(self, {"error": "not found"}, 404)

    def do_PUT(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except Exception:
            body = {}
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
        prof, err = validate_profile(body.get("name", cur["name"]),
                                     body.get("keywords", cur["keywords"]),
                                     body.get("sources", cur["sources"]))
        if err:
            _send_json(self, {"error": err}, 400)
            return
        prof.update({"id": pid, "created_at": cur.get("created_at", now_iso()),
                     "updated_at": now_iso()})
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
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"social-tracker on http://{HOST}:{PORT}  (mock: /, live: /dashboard-live.html)")
    server.serve_forever()


if __name__ == "__main__":
    main()
