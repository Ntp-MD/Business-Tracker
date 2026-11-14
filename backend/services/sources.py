"""Legacy source collectors (YouTube, GNews, TikTok, FB Ads, TikTok Ads).

Moved out of server.py unchanged; the new collector framework ports these sources one by
one. Every function is fail-soft and reports through progress stages.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ElementTree
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import db
import runtime

from services.window import cutoff_iso, iso_days_ago, older_than, parse_age_days

TTCC_PERIOD = {
    1: 7,
    3: 7,
    7: 7,
    15: 30,
    30: 30,
    365: 180,
}  # TikTok CC supports 7/30/180 days


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


def collect_gnews(q: str, max_age_days: int = 0) -> tuple[list, list[str]]:
    """Google News RSS (stdlib). author=google-news, score=0. Never raises.
    max_age_days > 0 restricts results to that window (query operator + pubDate check)."""
    cutoff = cutoff_iso(max_age_days)
    when = GNEWS_WHEN.get(max_age_days, "")
    query = f"{q} {when}".strip()
    runtime.progress_stage("reading RSS")
    try:
        url = (
            "https://news.google.com/rss/search?q="
            + urllib.parse.quote_plus(query)
            + "&hl=th&gl=TH&ceid=TH:th"
        )
        req = urllib.request.Request(url, headers={"User-Agent": runtime.UA})
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
        channel_url = (source_el.get("url") or "").strip() if source_el is not None else ""
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
                "created_at": runtime.now_iso(),
                "asset": None,
            }
        )
        if len(items) >= 10:
            break
    return items, []


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
    with runtime.PW_LOCK:
        yield


def _pw_context(playwright, kind: str):
    """Start a persistent headless context for TikTok/Facebook.
    First run needs one headed login by the owner (stored in user_data_dir)."""
    if not (runtime.PW_SESSIONS / kind).exists():
        return None, (
            f"{kind}: no login session — run `python backend/pw_login.py {kind}`, "
            "log in once in the opened browser, then fetch again"
        )
    browser = playwright.chromium.launch_persistent_context(
        str(runtime.PW_SESSIONS / kind),
        headless=True,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        user_agent=runtime.UA,
        locale="th-TH",
        timezone_id="Asia/Bangkok",
        timeout=runtime.PW_TIMEOUT_MS,
    )
    return browser, None


def _pw_public_context(playwright, kind: str):
    """browser + context สด public ไม่ต้อง login — ไม่แตะ profile dir (ไม่ชนกันหลายโปรเซส)"""
    try:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            timeout=runtime.PW_TIMEOUT_MS,
        )
        ctx = browser.new_context(user_agent=runtime.UA, locale="en-US", timezone_id="Asia/Bangkok")
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
            timeout=runtime.PW_TIMEOUT_MS,
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
                    "channel_url": f"https://www.tiktok.com/@{author}" if author else "",
                    "score": score,
                    "views": score,
                    "metric": "plays",
                    "created": published,
                    "published": published,
                    "created_at": runtime.now_iso(),
                    "asset": None,
                }
            )
            if len(items) >= runtime.PW_LIMIT:
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
            runtime.progress_stage("opening browser (or waiting for browser queue)")
            with _pw_locked(), sync_playwright() as p:
                if mode == "session":
                    ctx, err = _pw_context(p, "tiktok")
                else:
                    ctx, err = _pw_public_context(p, "tiktok")
                if err:
                    return [], [err]
                try:
                    runtime.progress_stage("searching, waiting for results")
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
        else "login expired or blocked — re-run backend/pw_login.py"
    )
    return [], [f"{tag}: no videos{win} ({hint})"]


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
            runtime.progress_stage("opening browser (or waiting for browser queue)")
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
                    runtime.progress_stage("loading ad library")
                    page.goto(url, wait_until="domcontentloaded", timeout=runtime.PW_TIMEOUT_MS)
                    runtime.progress_stage("waiting 12s for ads to render")
                    page.wait_for_timeout(12000)
                    runtime.progress_stage("scrolling for more ads")
                    for _ in range(3):
                        page.mouse.wheel(0, 3000)
                        page.wait_for_timeout(2500)
                    runtime.progress_stage("reading ad cards")
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
                "created_at": runtime.now_iso(),
                "asset": None,
            }
        )
        if len(items) >= runtime.PW_LIMIT:
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
            runtime.progress_stage("opening browser (or waiting for browser queue)")
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
                    runtime.progress_stage("loading top ads")
                    page.goto(url, wait_until="domcontentloaded", timeout=runtime.PW_TIMEOUT_MS)
                    runtime.progress_stage("waiting 12s for cards to render")
                    page.wait_for_timeout(12000)
                    page.keyboard.press("Escape")  # promo modal blocks clicks
                    page.wait_for_timeout(1000)
                    runtime.progress_stage("reading ad cards")
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
                "created_at": runtime.now_iso(),
                "asset": None,
            }
        )
        if len(items) >= runtime.PW_LIMIT:
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
    runtime.progress_stage("searching")
    try:
        url = (
            "https://www.youtube.com/results?search_query="
            + urllib.parse.quote_plus(q)
            + "&hl=th"
            + ("&sp=" + urllib.parse.quote(sp, safe="") if sp else "")
        )
        req = urllib.request.Request(
            url,
            headers={"User-Agent": runtime.UA, "Accept-Language": "th-TH,th;q=0.9,en;q=0.8"},
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
            browse = (runs[0].get("navigationEndpoint") or {}).get("browseEndpoint") or {}
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
                "created_at": runtime.now_iso(),
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


def save_thumbnail(vid: str) -> bool:
    dest = runtime.ASSETS / f"{vid}.jpg"
    if dest.exists():
        return True
    try:
        req = urllib.request.Request(
            f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg", headers={"User-Agent": runtime.UA}
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


def _http_get(url: str, timeout: int = 25) -> str:
    req = urllib.request.Request(
        url, headers={"User-Agent": runtime.UA, "Accept-Language": "th-TH,th;q=0.9,en;q=0.8"}
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
