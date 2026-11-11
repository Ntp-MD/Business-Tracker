# Social Tracker — How We Build It

> **Companion:** `AGENTS.md` — current operating brief. This file retains the original
> architecture/spec below for history; the **CURRENT** section here overrides stale parts.
>
> ## CURRENT (2026-11-11)
>
> - **Frontend:** `/` = mockup (`index.html`), `/live` = live (`live/index.html`) — always separate.
>   CSS in `assets/css/` (`variables`, `base`, `component`, `layout`, `layout-live`); no inline `<style>`.
> - **Runtime:** `server.py` (stdlib HTTP) + Playwright for TikTok / FB Ads / TikTok Ads.
>   Local URL: `http://127.0.0.1:8000/live/`. `HOST`/`PORT` can be set by the host.
> - **Storage:** Supabase via `db.py` when `.env.local` is configured (service role, server only);
>   otherwise local JSON (`data/*.json`) + `assets/` thumbnails. Tables: `items`, `profiles`,
>   `keyword_stats`, `source_status`; archive/trash are `archived_at` / `deleted_at`.
> - **Deploy:** Render API via `Dockerfile` + `render.yaml`; GitHub Pages/Vercel serve static
>   `/` and `/live`. `/live` needs `<meta name="api-base" content="https://api…">` + CORS
>   (`ALLOW_ORIGIN`). Without it, static preview disables Search Now.
> - **Auth/security:** service role only on server/worker; browser must use Supabase Auth + RLS.
> - **Next step:** `docs/MIGRATION-NEXT.md` (Next.js + TS worker) is gated; not started.
>
> The original 2026-11-06/13 decision text below is **historical**; where it conflicts
> (disk-only, no deploy, mock untouched), this header + `AGENTS.md` win.
>
> **Reading map:** current = this header, §2 stack table, §5 sources, §9.4–§9.7.
> Historical = §1, §3, §4, §6, §7, §8 (kept for decision history; do not implement from them).
>
> ---

> **Historical state (2026-11-06, revised):** owner changed the storage direction. **All data lives on disk**
> (JSON + cached image assets). No SQLite database file. **A lightweight stdlib-only localhost server
> stays** so the Dashboard buttons work. **No code is written yet** — docs lead, code follows.
> The mockup dashboard (`dashboard.html` + `page-*.html`) stays untouched; the HTTP contract
> (`GET /api/summary?q=` · `POST /api/fetch` · new `POST /api/analyze`) is preserved so mock goes live unchanged.
>
> **Target shape:** Dashboard → **Collect button** → server fetches YouTube + GNews → merges into
> `data/items.json` → writes `data/index.json` + `assets/{vid}.jpg` → dashboard re-reads → shows live data →
> **Analyze button** → server reads disk → writes `data/analysis.json` → recommendations render inline.
>
> **Main goal:** disk-store → live dashboard → analyze works for real (Thai keywords), before content strategy.
>
> **Decided 2026-11-06 (rev 2) — change here, not elsewhere:**
> installer = `setup.bat` unchanged · sources = YouTube + Google News TH unchanged · Thai `top_terms` = plain
> whitespace Counter unchanged · storage = disk JSON (`items.json` + `index.json` + `analysis.json`) ·
> YouTube thumbnails stored locally on disk · server = stdlib + Playwright (TikTok/FB only), port 8000 · mockup stays as-is · Playwright approved.
>
> **Rev 3 (2026-11-13, owner-approved):** no installer (run `python server.py` locally); sources = YouTube + GNews + TikTok/FB via Playwright session; profiles in `data/profiles.json`.

---

## 1. How the app works

> **HISTORICAL (2026-11-06).** Diagram/flows below describe the original disk-only build.
> Current runtime: `server.py` + `db.py` (Supabase when configured), with archive/trash and
> ads collectors. See the CURRENT header and `docs/AGENTS.md`.

### The shape

```
┌─────────────────────────────────────────────────────┐
│  Dashboard (dashboard.html) — localhost UI only      │
└──────────────┬───────────────────────▲──────────────┘
               │ POST /api/fetch       │ JSON (summary)
               ▼                       │
┌─────────────────────────────────────────────────────┐
│  server.py — stdlib only, one process                │
│                                                      │
│  ┌────────────┐   ┌────────────┐   ┌──────────────┐ │
│  │ COLLECT    │──▶│ STORE→disk │──▶│ ANALYZE      │ │
│  └────────────┘   └────────────┘   └──────────────┘ │
└─────────────────────────────────────────────────────┘
```

### How each piece works

| Piece | We use | Why this way |
|-------|--------|--------------|
| COLLECT | `urllib.request` + fixed UA; failures are caught per source and returned as `errors[]` | No deps, network problems never abort the rest |
| STORE | `data/items.json` merged by `url` + written atomically (tmp + rename) | Files are inspectable, diffable, resettable; no database |
| ASSETS | YouTube `mqdefault.jpg` → `assets/{videoId}.jpg` on every new YT item; assets never re-encoded | Owner wants images local; no conversion needed (source ~320px) |
| ANALYZE | `Counter` on words ≥ 4 chars; read from disk; output `data/analysis.json` | Zero deps; same accepted Thai limitation |
| SUGGEST | 3 fixed templates (30-sec + CTA / SEO hashtags / 3-part FAQ) | Free, offline, human picks the angle |
| SERVE | `BaseHTTPRequestHandler` static + API endpoints | No framework |

### How one Fetch round goes (step by step)

1. Browser posts `{q}` to `/api/fetch` (button: Collect)
2. `collect(q)` runs YouTube search page scrape, then Google News RSS parse
3. New items merge into `data/items.json` (skip URLs already present) → atomic write; YouTube thumbnails download to `assets/`
4. `data/index.json` rebuilt (per-keyword rollup); `analyze(q)` reads disk → `data/analysis.json`
5. Browser renders it

`POST /api/analyze {q}` = analyze only, no fetch (button: Analyze).

If a source dies mid-run → its message goes into `errors[]`, the run continues. The user sees which source worked and which did not.

### Rules we keep

- Localhost only — binds `127.0.0.1:8000`
- Stdlib only — no pip, no venv needed
- Manual only — no cron, no background jobs, no auto-fetch on start; **every disk write needs a button press**
- Collect writes `items.json` + `index.json` + `assets/`; Analyze writes `analysis.json`; Summary/GET never writes
- Idempotent — 3 dedup layers: canonical URL (tracking/share variants merged), title key (same source), near-duplicate title for organic sources (`youtube`/`gnews`/`tiktok`, trigram Jaccard ≥ 0.90)
- Disk is source of truth — no database; `data/` + `assets/` both disposable
- Suggest = template — AI is opt-in later, never required
- Mockup stays as-is — endpoints preserved; frontend edits only when owner explicitly asks

### How Phase 2 plugs in (when and if)

- New free sources → add one `collect()` job, same disk-merge pattern
- Playwright / paid APIs / AI → replace or wrap the same seams (COLLECT or ANALYZE), not the whole app

---

## 2. What we use

### The actual rebuild stack

| Layer | We use |
|-------|--------|
| Language | Python 3 (stdlib + `playwright` for TikTok/FB only) — `http.server`, `urllib`, `xml.etree`, `json`, `re`, `collections.Counter` |
| Storage | Local JSON **or Supabase** via `db.py` when env is configured — `items`, `profiles`, `keyword_stats`, `source_status`; local fallback `data/*.json`. No SQLite |
| Assets | `assets/{videoId}.jpg` — YT thumbnails; Supabase Storage `thumbnails` in remote mode |
| Frontend | `index.html` mock (`/`) + `live/index.html` live (`/live`) — separate; CSS in `assets/css/` |
| Sources | YouTube search (`ytInitialData`) · Google News RSS TH · TikTok (public Playwright) · FB Ad Library · TikTok Creative Center (fail-soft) |
| Runtime | `python server.py` → `http://127.0.0.1:8000/live/`; Render Docker for HTTPS API |
| Installer | none — `python server.py` locally; Render via `render.yaml`/Dockerfile |
| Repo/data | `data/` + `assets/` disposable; secrets in `.env.local` (gitignored) |

### Explicitly not used

- pip packages, venv, requirements.txt, npm, Docker, CI, `.env` files, config files
- Flask/FastAPI/Django — stdlib HTTP only
- SQLite / any database file — replaced by disk JSON (2026-11-06 rev 2)
- Case-study AI/LLM — template-only suggestions
- Paid APIs, keys, OAuth (Phase 2-C only if approved)

### Phase 2 pickoff (not now)

A = free sources (stdlib only) · B = Playwright (+pip) · C = Meta/TikTok keys (+token) · D = AI (+key, optional layer)

---

## 3. How the files are laid out

> **HISTORICAL (2026-11-06).** Current layout: `index.html` (mock), `live/index.html` (live),
> `assets/css/`, `assets/icons/`, `server.py`, `db.py`, `Dockerfile`, `render.yaml`.
> No `app/` folder anymore.

### Working layout (rebuild same way)

```
social-tracker/
├── app/
│   └── dashboard.html     # main view — mock kept as-is; goes live unchanged (endpoints preserved)
├── views/
│   └── archive/           # generated views for other pages (competitors, ads, calendar, crm, goals, reports, tasks)
├── docs/                  # ARCHITECTURE.md, AGENTS.md, DESGIN.md
├── assets/
│   └── fonts/             # self-hosted fonts (IBM Plex Sans Thai, LINE Seed) — served as-is
├── shots/                 # design verification, never served
├── data/                  # created on first run (items.json + index.json + analysis.json + profiles.json), disposable
├── server.py              # serves UI + /api/summary + /api/fetch + /api/analyze + /api/profiles; COLLECT/STORE→disk/ANALYZE here
├── pw_login.py            # one-time headed login for TikTok/FB sessions into sessions/ (machine-local)
└── gen_page.py            # one-shot generator of page-*.html — not part of runtime
```

### How we use each file

- `server.py` — change logic here only
- `data/` — delete folder to reset; it is not a source of truth, just a cache
- `assets/` — delete folder to reset cache; items.json still references them (broken img) until next Fetch re-downloads
- `shots/` — design verification, never served

### When we split (not now)

Split trigger: editing `server.py` breaks elsewhere, or 2+ people edit concurrently. Then `pkg/` with `collector.py`, `analyze.py`, `db.py`. Until then — stay flat, this file wins.

---

## 4. How we run it

> **HISTORICAL (2026-11-06).** Current run: `python server.py` → `/live/`; hosted API on
> Render; static `/` on Pages/Vercel. Verification lives in §9.6 and `docs/AGENTS.md`.

### Everyday loop

```
1. run `python server.py`       → open `http://127.0.0.1:8000/live/` manually
2. type a Thai keyword            → e.g. "เว็บขายของ" (placeholder until business keywords decided)
3. press **Fetch now (= Collect/gather)** → POST /api/fetch → pulls YouTube + GNews,
   merges into data/items.json, downloads thumbnails into assets/
4. summary loads automatically (GET /api/summary on open) and after each fetch → by_source, hot,
   top terms (the manual "Load from disk" button was removed 2026-11-13)
5. press **Analyze** → POST /api/analyze → writes data/analysis.json → read the advice inline
6. pick the angle by hand          → content made outside this tool
7. measure by hand                 → sales/LINE chats, adjust keyword
```

Rules: every step is manual — no auto-run anywhere; the same query twice returns near-identical rows; insights are raw material, never an answer. (Mock button labels keep their old names until owner approves a mock edit.)

### How we gate Phase 2

```
Run 2–4 weeks of real fetches
   ▼
The 5 open questions (§8) are answered
   ▼
The insights drove 1 real content cycle
   ▼
Only then: pick 2-A/B/C/D — otherwise stop
```

### What to do when errors show up

- One source error → keep the rest; the UI shows the message
- Same source dies repeatedly → remove/replace that job, keep the other
- Disk garbage → delete `data/` + `assets/`, fetch again
- Need a new keyword → edit in the UI, never in code

### Newcomer expectation

No auto-posting, no scheduling, no FB/TikTok/IG, no AI author, no deploy — one machine, localhost.

---

## 5. How each source helps us (and what it costs)

> Manual fetch = 1 call each per press; volume is irrelevant vs limits — the risk is drift/auth/format.

| Source | We use it for | Published limit / status (2026-11-06) |
|--------|---------------|----------------------------------------|
| **YouTube search** | Thai video trends, hot item by view count | No key/quota; unofficial HTML + `ytInitialData`; format may change without notice — fail-soft covers us |
| **Google News RSS TH** | Thai news coverage per keyword | Unofficial since 2011, no SLA; ~100 items cap; links are Google redirects; staleness in sampling |

Everything else stays out of parts 2–3:
- Google Trends RSS — separate daily-trends dashboard panel, not keyword search (§8.4) · Pantip — no official API, client-side render · Meta/TikTok — Phase 2-C only.

**Thai market keywords to track:** `เว็บร้านอาหาร` · `เว็บขายของ LINE` · `ระบบจอง` · `เว็บธุรกิจ` · `ค่า LINE OA` · `ธีมเว็บ` — replace after business questions answered (§8.1).

---

## 6. How we store the data

> **HISTORICAL (2026-11-06) — superseded.** Storage is local JSON **or** Supabase Postgres
> (`items`, `profiles`, `keyword_stats`, `source_status`) via `db.py`. No SQLite either way.
> Archive/trash are `archived_at` / `deleted_at`, not separate `archive.json` / `trash.json`
> files. Details: `docs/DB.md`.

> **Original rule (revised 2026-11-06):** **everything lives on disk** — JSON is the record, files are files.
> No database. All of it is disposable: delete `data/` + `assets/` to reset. Never base64/blob inside JSON.

### 6.1 `data/` layout (merged store)

```
data/
├── items.json      # every collected row, merged on url — source of truth
├── index.json      # derived per-keyword rollup — regenerated after each Collect/Analyze; never hand-edited
└── analysis.json   # last Analyze output per keyword (advice/directions to read)
```

`items.json` shape (array of objects):

| Field | What it holds | Why |
|--------|-----------|-----|
| `url` | direct link | original link, open in browser |
| `canonical_url` | normalized link | **dedup layer 1** — strips `utm_*`/`fbclid`/share params, unifies YouTube/TikTok/FB Ad URL forms |
| `title` | full title text | core content; layer 2 = exact normalized title per source, layer 3 = near-duplicate (trigram Jaccard ≥ 0.90, organic only) |
| `body` | first 500 chars max | copyright + bloat cap |
| `source` / `keyword` | `youtube` / `gnews`, search phrase | group/filter |
| `author` | YT channel or GNews publisher | credit/context |
| `score` | views (YouTube), plays (TikTok), likes (TikTok Ads) | ranking metric; 0 when the source exposes nothing |
| `views` | actual view/play count or null | source metric kept separately so ads likes are not called views |
| `metric` | `views` / `plays` / `likes` / `none` | UI label under each score |
| `channel_url` | creator/channel/publisher link | YouTube channel, TikTok `@user`, GNews publisher; empty when not exposed |
| `created` | raw date string (GNews RFC / YouTube empty) | raw kept |
| `created_at` | UTC ISO8601 | cross-source sort |
| `asset` | `"assets/{videoId}.jpg"` for YouTube items; empty for GNews | local thumbnail reference |

Merge rules (collect round):
1. read existing `items.json`; build `url` set
2. new items = parsed items whose `url` not in set (and not empty)
3. YouTube: download thumbnail `assets/{videoId}.jpg` (fail-soft; item kept, error noted)
4. append, write atomically (`items.json.tmp` → rename) — crash mid-write cannot corrupt the file
5. rebuild `index.json` (per keyword: `total`, `by_source`, `hot`, `top_terms`)

### 6.2 How images/assets work (revised 2026-11-06)

- **YouTube:** download `https://i.ytimg.com/vi/{videoId}/mqdefault.jpg` → `assets/{videoId}.jpg` — used as-is (source ~320 px, no re-encode/resize, stdlib has no image tools)
- **GNews:** no images in feed — never scraped
- **Format:** JPEG only, `assets/{videoId}.jpg` = the videoId from `url`; already-present files are kept (not re-downloaded)
- **Never** bytes or base64 inside `items.json`/`analysis.json`
- **PDPA (TH):** cache public video thumbnails only; never photos of private people; GNews same as before
- Delete `assets/` any time; `items.json` references may 404 until next Fetch re-downloads

### 6.3 Documents

- No full articles stored — `body` ≤ 500 chars, same rule as before
- Long-form snapshots are **not in scope**; if the owner later wants them, propose `data/docs/` markdown export — needs explicit sign-off (§8)

### 6.4 How disposal works

- `data/` + `assets/` = disposable cache; delete both to reset; no migration, no archive
- Need reports → export CSV/JSON from `items.json`, don't archive manually
- Exporting: `python -c "import json;print(json.dumps(json.load(open('data/items.json',encoding='utf-8')),ensure_ascii=False))"` or open the file directly

What we deliberately do NOT do: FTS5, indexes, migrations, base64 blobs, second store — YAGNI at this size.

---

## 7. How trends look and where our content goes (still DRAFT until business is settled)

> Assumption (unconfirmed): ITOPPLUS = Thai web/theme company for Thai SMEs. If the business differs, replace the examples — the direction holds.

### Root causes to plan around

1. Algorithm pays for watch time → short video wins
2. Thai users search on social → decision layer is TikTok/YouTube
3. Trust shifts to real people → micro/nano creators outsell polished ads
4. AI floods volume → wins go to authentic, verifiable content

### Thai market shape (2026)

Flow: **Facebook → TikTok (hook) → YouTube (trust) → LINE (close)**. LINE 56M · TikTok 56.6M (TH #1 SEA TikTok Shop) · FB 51.5M · YT 47.2M. Search is in structural decline.

### How our content should flow

1. Short video 30–45 s, 2–3/week (demo/before-after/owner POV)
2. YouTube 1 episode/week (comparison/test content)
3. Every clip CTA by LINE OA — never feed-selling
4. Social proof monthly
5. AI drafts, human speaks
6. Stop: generic tips, cross-post identical, hard sell, faceless AI

### What we stop expecting

Volume ≠ reach; paid-first loses to organic proof; template "engagement" is a grid, not verdict.

### Keyword/SME angle for the tracker

`เว็บขายของ` · `ระบบจอง` · `Line OA` · `ธีมเว็บ` · `เว็บร้านอาหาร` — replace once §8.1 answered.

### Funnel → tool mapping

Discovery (TikTok/FB) → views · Trust (YouTube) → views/comments · Close (LINE OA) → manual count · Loop back → tracker picks winners.

---

## 8. What stays parked as questions

> Main goal = collector → disk store → analysis works for real. Everything below waits.

### 8.1 Business definition (blocks keyword choice, not code)
1. What does ITOPPLUS actually sell — boxed themes / custom / SaaS?
2. Customer segment + area?
3. First 3–5 Thai SME keywords?

### 8.2 Measurement
4. 2 KPIs (e.g. qualified LINE chats/week, views/clip)?
5. Baseline today?

### 8.3 Execution / funnel
6. Who owns the whole loop?
7. LINE OA + per-clip CTA tag — when?
8. First content cycle, measured by hand?

### 8.4 Already decided (this file, §9) — do not re-ask
- pythainlp → **no**, Thai top_terms stays broken by choice
- thumbnails → **stored locally** (`assets/{videoId}.jpg`, YT `mqdefault` as-is) — changed 2026-11-06 rev 2 (owner wants images on disk)
- `created_at` → **added** at rebuild · `image_url` → replaced by `asset` field pointing to local file
- YouTube parser → **kept with fail-soft**, not replaced
- storage → **disk JSON** (`items` / `index` / `analysis`) — changed 2026-11-06 rev 2; SQLite rejected

### 8.5 Later (after 8.1–8.3)
9. Phase 2 direction: A/B/C/D · 10. FB/TikTok metrics sheet or paid APIs? · 11. PDPA consent for client photos? · 12. Wider rollout? · 13. `data/docs/` long-form snapshot export — needs owner sign-off

### 8.6 Hard constraints
- No code until §9 approved (all live in this file)
- Rebuild = stdlib only, single `server.py`, Thai sources, manual fetch, fail-soft
- Disk store = the contract: no database file at any point — JSON merge only, atomic rename
- `dashboard.html` + `page-*.html` call `GET /api/summary`, `POST /api/fetch`, now also `POST /api/analyze` — mock stays unedited; it goes live unchanged
- Assets live under `assets/`; GNews gets no images ever; thumbnail downloads are fail-soft

---

## 9. How we build parts 2 + 3 (the method)

> Scope: **part 2 = local run (no installer) · part 3 = connect source → disk store → analyze.**
> Part 1 (mockup dashboard) stays as-is. All decisions below are locked as of 2026-11-06 (rev 2) — change here, not elsewhere.

> **No code yet** — this spec exists first; rebuild happens only on owner's go.

### 9.1 How the server starts (no installer)

**Use:** run `python server.py` directly (run from repo root). Owner dropped the installer; keep it dropped. First run creates `data/` + empty `items.json`/`index.json`/`analysis.json`/`profiles.json` and `assets/` — nothing else. `sessions/` (TikTok/FB login profiles) created by first `pw_login.py` run.

**Steps the owner runs:**
1. (once) `python -m pip install playwright` + `python -m playwright install chromium` — needed only for TikTok/FB collectors; YouTube/GNews work without
2. `python server.py` → open `http://127.0.0.1:8000/live/` in the browser

### 9.2 How fetching works (COLLECT)

**Use:** Python stdlib only.

**YouTube path:**

1. `GET https://www.youtube.com/results?search_query={q}&hl=th` with fixed UA header (`Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...`) — same class of public access as Google News RSS; no key
2. Response (~1.5 MB) → regex `ytInitialData\s*=\s*(\{.*?\});</script>` → `json.loads`
3. Recursive walk (`depth > 14` guard) for dict keys `videoRenderer`
4. From each renderer: `title.runs[0].text` or `simpleText`; `viewCountText.simpleText` → digits → `score`; `videoId` → `https://www.youtube.com/watch?v=...`; `ownerText`/`longBylineText` → `author`
5. Limit 12 items per fetch

**Google News RSS path:**

1. `GET https://news.google.com/rss/search?q={q}&hl=th&gl=TH&ceid=TH:th`
2. `xml.etree.ElementTree` parse → `.//item` (take 10) → `title`, `link`, `pubDate`
3. Stored with `author="google-news"`, `score=0`

**Putting it together (disk merge):**

- Read `data/items.json` → map URLs already present
- `save()` = skip empty `url`; skip known `url`; append new objects; write atomically (`.tmp` then `os.replace()`)
- YouTube items: fetch `assets/{videoId}.jpg` (same id as the `url` suffix); failure → keep item, add `asset: null`, log into `errors[]`
- Each source wrapped in `try/except` → error goes to `errors[]`, the other source continues
- Re-pressing Collect adds nothing new (URL dedup)
- Rebuild `data/index.json` after every round (per keyword rollup)

### 9.3 How analysis works

- `analyze(q)` reads `data/items.json`, filters `keyword == q`, orders by `score DESC` (limit 100)
- `Counter` over `title + body`, lowercased, splits on whitespace, strips `.,:;()"'[]*`, keeps words ≥ 4 chars not in English stopword set — **Thai phrases remain unbroken, inflating counts; accepted for now**
- Returns `by_source`, `hot` (highest-score item title), `top_terms`, 3 template suggestions
- Output is written to `data/analysis.json` (for reload/history) and also returned to the browser

### 9.4 How the server serves it

- `BaseHTTPRequestHandler`, fixed port 8000, localhost only
- `GET /` → `index.html` (mock), `/live/` → `live/index.html` (live); `/assets/*` and `/fonts/*` static; `/dashboard-live.html` redirects to `/live/`; path traversal guarded
- `GET /api/summary?q=` → `analyze(q)` JSON (UTF-8 `ensure_ascii=False`; reads disk, no fetch). Omit `q` → returns the whole local store (All items view on first open)
- `GET /api/progress` → live fetch heartbeat: `{active, keyword, source, stage, elapsed, since_update}`; collectors push stage strings while running (browser open → page load → wait → read). The loading modal polls it every 1.5 s: the stage line proves the server is moving, and > 60 s without a stage update (or 4 failed polls) turns it into a "not responding" warning. Read-only, never writes
- `POST /api/fetch` → `collect(q)` → `analyze(q)` → JSON with `added`, `duplicates`, `errors`, `cancelled`, `fetched_at` (button: Search Now)
- `POST /api/cancel` → asks the running fetch to stop before the next source/keyword; current collector finishes, partial results are saved
- `GET /api/export[?q=]` → JSON envelope `{format, version, app_version, exported_at, keywords, count, items}` as a download
- `GET /api/export.zip[?q=]` → zip with `items.json` + referenced `assets/*.jpg`
- `POST /api/import` → JSON envelope or zip body; validates `format`/`version`, canonical dedup per keyword, rebuilds index/analysis; returns `{added, duplicates, keywords, per_keyword}`
- `GET /api/status` → `{app_version, items, archived, trash_count, keywords, data_bytes, assets, assets_bytes, sources, sessions}`; `sources` holds last success/error per collector
- `GET /api/archive` → archived items (`archived_at` preserved)
- `POST /api/archive {items:[{keyword,url}]}` → move active items to `data/archive.json` (bulk)
- `POST /api/archive/restore {items}` → move archived items back to active (skips URL conflicts)
- `DELETE /api/archive {items}` → permanently delete archived items + unused thumbnails
- `POST /api/items/bulk {action:"delete"|"move", items, to_keyword?}` → bulk delete/move active items
- `POST /api/items` → create a manual/imported item (`url` + `keyword` required); dedup rules apply; returns `{added, duplicates, item}`
- `PUT /api/items {keyword, url, patch}` → edit title/body/author/channel/keyword/score/views/metric of one item; rebuilds index/analysis
- `DELETE /api/items {keyword, url}` → delete one item + its unused thumbnail; rebuilds index/analysis
- `POST /api/clear-all` → wipe items/index/analysis/source-log and all thumbnails; **profiles are kept**
- `POST /api/clear {q}` → deletes one keyword's items + analysis entry, removes unreferenced thumbnails; returns `{removed, total}`
- `POST /api/refresh-stats {q, sources?, items?}` → re-reads view/play/like counts for existing items only (YouTube watch page per item, TikTok/TikTok Ads re-scrape); `items` limits to selected rows; never adds items; returns `{updated, total, errors, cancelled}`
- `POST /api/prune {days}` → deletes dated organic items older than N days across all keywords (ads stay), refreshes index/analysis, removes orphan thumbnails
- `POST /api/analyze` → `analyze(q)` only, no fetch (button: Analyze); JSON with `analysis`, `fetched_at`
- Only POST presses write to disk; GET endpoints never write; no auto-run on server start
- 404 for anything else; `log_message` silenced

### 9.5 Decisions — locked 2026-11-06, updated 2026-11-11 (Supabase + deploy)

| What | We use / do | Locked because |
|------|-------------|----------------|
| Installer | **none** — owner runs locally only: `python server.py` (one command) | installer decision removed (owner), installer must not reappear without sign-off |
| Sources | YouTube (stdlib scrape) + Google News TH (stdlib RSS) + TikTok via Playwright, 2 modes: `public` (no login, works) vs `session` (logged-in profile in `sessions/`, optional); ad libraries: FB Ad Library (keyword, TH, active) + TikTok Creative Center Top Ads (TH, period) — public pages, no login | Thai market, free, no key; Facebook organic dropped (owner 2026-11-13): login wall, no dates |
| Freshness | `POST /api/fetch` takes `max_age_days` (UI: 1 / 3 / 7 / 15 / 30 / ทั้งหมด, default 30; 1/3 map to the nearest supported 7d source window, then prune by real date). YouTube adds upload-date `sp` + parses `publishedTimeText`; GNews adds `when:` + filters `pubDate`; TikTok reads `createTime` from the search page's own JSON; TikTok Ads uses the page's period filter (7/30/180d); prune applies only to dated organic sources (`youtube`/`gnews`/`tiktok`) — ads stay because active ads are current by definition | owner: content must be recent, not "all years"; search engines block automation (tested Google/Bing/DDG/Brave/Mojeek), so use platform pages instead |
| Profiles | keyword profiles stored on disk: `data/profiles.json` (name + keywords[] + sources[]); `/api/profiles` CRUD; `POST /api/fetch` accepts `profile_id` + `mode` (`public`\|`session` for TikTok/FB) (collects every keyword × source sequentially, dedup by canonical URL + title layers); UI: picker + mode in fetch strip, manage in Settings, per-keyword tabs, Top items table has per-platform tabs and filters rows | multi-keyword preset, no DB, no new deps |
| Thai top terms | plain Counter, broken output accepted | avoid adding pythainlp until needed |
| Storage | **local JSON or Supabase** — local: `data/items.json` (dedup per keyword: canonical URL + title key + near-dup, atomic rename) + `archive.json` + `trash.json` + `index.json` + `analysis.json` + `sources.json`. Supabase mode via `db.py` (PostgREST) writes `items/profiles/keyword_stats/source_status`; service role server-only | local-first, cloud when configured; inspectable/resettable; no SQLite |
| Archive | per-item/ bulk bookmark: `archived_at` (Supabase) or `archive.json`; restore or delete permanently; thumbnails kept until deleted | user wants a "keep for later" store |
| Backup | JSON export/import + zip with thumbnails, schema `social-tracker.items` v1; import idempotent | data must survive disk loss/machine moves |
| Cancel | loading modal stop button → `POST /api/cancel`; server stops before next source | profile runs can take 10–15 min |
| Ads page | unlocked, renders `fbads` + `ttads` items; other 6 menu items locked | ads data already fetched |
| Local CRUD | profiles + items create/edit/delete; recent keywords; export/import/clear/prune. derived stats never edited directly | manage data without hand-editing JSON |
| Frontend | `index.html` mock (`/`) and `live/index.html` live (`/live`) — **separate**; both maintained; CSS in `assets/css/` (no inline style) | owner wants distinct mock/live |
| Tests | stdlib `unittest` in `tests/`; forced local adapter so tests never touch Supabase | regression safety |
| Thumbnails | local `assets/{videoId}.jpg` or Supabase Storage `thumbnails`; raw `mqdefault.jpg` | owner wants cached images |
| Fragility | collectors fail-soft; YouTube/GNews stdlib keep working; Playwright errors surface in UI | resilience |
| Config | `.env.local` optional: Supabase URL/service role/user id, `SUPABASE_STRICT`, `ALLOW_ORIGIN`; `HOST`/`PORT` env | local + hosted |
| Dependencies | Python stdlib + `playwright`/chromium (TikTok/FB/TT Ads); Supabase via REST adapter | no SDK/npm in current app |
| Deploy | local `python server.py`; Render Docker (`Dockerfile`, `render.yaml`); GitHub Pages static `/` + guarded `/live` with `api-base` | owner chose hosted API + static frontend |
| Runtime | local + Render; Search Now requires Chromium; not available on Pages/Vercel serverless | known platform limit |

**If a decision changes:** edit §9.5 here — nothing else in the codebase is allowed to drift from it.

### 9.6 How we verify (done when all are true on a clean Windows + Python 3)

1. `python server.py` → open `http://127.0.0.1:8000/live/` manually; local mode creates `data/` + `assets/`; Supabase mode (`.env.local`) writes remote tables instead
2. Type keyword → Search Now → rows land in `data/items.json` **or Supabase `items`** (same canonical URL/title not duplicated); thumbnails appear locally or in Storage
3. Summary shows `by_source`, hot item, top terms; `data/index.json` / `keyword_stats` written
4. Kill YouTube (disconnect network) → Search Now still returns GNews rows; `errors` shows `youtube: ...`; app never crashes
5. Search the same keyword twice → `total` unchanged and the response reports `duplicates` (dedup works)
6. Press Analyze → `data/analysis.json` / `keyword_stats` summary written (no items copy); advice renders inline
7. Delete `data/` + `assets/` (local mode) → app starts and re-creates them; Supabase mode still reads remote
8. Export JSON + ZIP → re-import both → `added` 0, `duplicates` = item count (idempotent); files download with content-disposition
9. Start a profile fetch → press Stop → response has `cancelled: true`; later sources do not run; partial results stay
10. Settings → disk usage matches files; clear a test keyword → only that keyword's items disappear, orphan thumbnails removed
11. Add item → edit title/score → delete → All items reflects each step; Clear all wipes items/analysis/thumbnails but keeps profiles
12. Select 2 items → Archive → Archive page shows them, active count drops → Restore → active count returns; bulk Move/Delete works
13. `python -m unittest discover -s tests -t .` passes; tests never touch Supabase
14. GitHub Pages `/live` without `api-base` shows static preview (no JSON parse error); with a valid API base, read/CRUD work

### 9.7 What is not in parts 2 + 3

- IG · Trends RSS · Pantip · LINE (no public trend surface)
- Browser sessions (`sessions/`) are machine-local only; gitignored, never committed
- SQLite files — local JSON or Supabase Postgres only
- Re-encoding/resizing images — raw `mqdefault.jpg` only (needs owner sign-off to add image libs)
- Long-form snapshots (`data/docs/`) — needs owner sign-off
- LINE OA wiring, KPI tracking, content strategy (parked §8)
- `pythainlp`, npm, Docker, config files, `.env`
- Any edits to `dashboard.html`, `page-*.html`, `gen_page.py`, `DESGIN.md`, `fonts/`, `shots/` (mock kept as-is; edits only on explicit owner request)
- Any new docs beyond this file