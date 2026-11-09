# AGENTS.md — Implementation brief, pairs with ARCHITECTURE.md

> Read `ARCHITECTURE.md` **fully** before writing any code — it is the build spec.
> This file is the binding layer: it tells you HOW you work, and where you must stop and ask.
> If anything here conflicts with ARCHITECTURE.md, **ARCHITECTURE.md wins** — then tell the owner it is inconsistent.
>
> **Scope: parts 2 + 3 only** — local run (no installer) and the collector → **JSON disk store** → analyze pipeline.
> Part 1 (mockup dashboard) stays as-is. Do not open or edit `dashboard.html`, `page-*.html`, `gen_page.py`, `DESGIN.md`, `fonts/`, `shots/` unless the owner explicitly asks.
>
> **Direction rev 3 (2026-11-13, owner-approved):** all data on disk — `data/items.json` + `data/index.json` + `data/analysis.json` + `data/profiles.json`. No SQLite. Thumbnails cached in `assets/`. Playwright + chromium approved for TikTok/FB session collectors. No installer — run `python server.py` locally.

---

## 0. Project in one line

Make Thai social trends turn into sellable content, with a free localhost tool — Collect fills the disk cache, Analyze reads it, a human picks the angle.

## 1. Authority and non-negotiables

You build exactly what ARCHITECTURE.md §9 specifies. You do **not**:

- add any dependency except approved `playwright` (+ chromium for TikTok/FB) — ARCHITECTURE §9.5 locks this
- touch the frontend, theme, logo, screenshots, or design system files (mock stays as-is)
- add IG/Trends RSS/Pantip/LINE integration of any kind
- make fetch automatic, add cron, auto-post, or multi-user/deploy
- create any database file — storage is JSON on disk only
- store images beyond YT `mqdefault.jpg` raw in `assets/` — no re-encode, no PNG, no base64 in JSON
- change the HTTP contract: `GET /api/summary?q=` · `POST /api/fetch` (+ `POST /api/analyze`, `GET/POST/PUT/DELETE /api/profiles`) without updating §9.5 first

You **may** decide (no need to ask): variable names, internal structure inside `server.py`, error-message wording, CSS of nothing (there is none), order of `collect()` jobs, logging format.

You **must ask** the owner before doing any of these:

- adding `pythainlp` or ANY package · deleting user files · changing source list
- switching YouTube scraping to Playwright or another method
- editing `ARCHITECTURE.md` §9.5 (decisions live there, not here)
- anything about business: keywords, KPI, LINE OA, content strategy (all §8, parked)

When in doubt: **stop and ask** — do not improvise around a constraint.

## 2. Tool ladder (use in this order)

1. Python stdlib (`urllib`, `xml.etree`, `json`, `http.server`, `re`, `collections`, `os`) — always preferred
2. Manual code around stdlib — fine
3. A new dependency — **ask first** (`playwright` already approved for TikTok/FB; anything else still needs approval)
4. Paid/keyed service — **not allowed now**; Phase 2-C only on explicit owner approval

Concrete mappings (do not substitute): RSS → `xml.etree` · YouTube → fixed-UA GET + regex `ytInitialData` + `json.loads` + recursive walk `depth > 14` · STORE → JSON merge on `url` (atomic `.tmp` + `os.replace()`) · ASSETS → `assets/{videoId}.jpg` · server → `BaseHTTPRequestHandler`, port 8000, localhost only, 404 for everything else.

## 3. Acceptance — the owner's clean-machine test (ARCHITECTURE §9.6)

Your work is done only when ALL pass on a machine with Python 3 and nothing else:

1. `python server.py` → open `http://127.0.0.1:8000/dashboard-live.html`; `data/` + `assets/` get created; no `.db` file appears
2. Type a keyword → press Fetch now (= Collect/gather, manual) → rows land in `data/items.json`; YT thumbnails in `assets/`
3. Summary shows `by_source`, `hot` item, `top_terms`; `data/index.json` written
4. Disconnect network or block YouTube → GNews still returns rows; UI shows `youtube: ...` in errors; app does not crash
5. Same keyword twice → item count unchanged (dedup verified)
6. Analyze → `data/analysis.json` written; renders advice inline
7. Delete `data/` + `assets/` → app re-creates them empty on next start, never crashes

"It compiles" does not pass. "Tests pass locally" does not pass. Only §9.6 passes.

## 4. Failure protocol

- A source returns an error → collect it into `errors[]`, continue with the other source, show the error in the UI JSON response
- Both sources fail → return the errors, never crash the server
- `data/` corrupt/inconsistent → delete `items.json`/`index.json`/`analysis.json` (or both folders), fetch fresh; tell the owner (it is a disposable cache)
- Partial write crash → `items.json.tmp` left behind; `items.json` stays intact; delete the orphan tmp on next start
- YouTube markup changed and `ytInitialData` regex fails → report immediately; do NOT silently switch methods
- Any doc/spec inconsistency → name it, ask, do not resolve silently

## 5. Communication format (how you report)

Use short Thai/English mixed updates, in this order:

1. **What you did** — one line per change
2. **How you verified** — the exact §9.6 steps run and result
3. **What is blocked** — list with the owner action needed
4. **What remains** — short checklist to full done

Never claim done before §9.6 passes in full. If only partial, say exactly which step failed.

## 6. Keep the doc alive

- Any decision change → edit `ARCHITECTURE.md §9.5` (this file points to it; it does not duplicate it)
- New failure discovered → add it to §4 (Failure protocol) or §5 (known fragility)
- Never let this file and ARCHITECTURE.md drift apart — ARCHITECTURE.md is truth, this file is the handle

## 7. Quick file map

| File | Your use |
|------|----------|
| `docs/ARCHITECTURE.md` | Read fully first; all decisions live here |
| `docs/AGENTS.md` (this file) | How you work; binding rules; all |
| `server.py` (repo root) | Only code you may create/replace; single file |
| `pw_login.py` (repo root) | One-time headed login into `sessions/` (TikTok/FB) |
| `social.db` | Legacy garbage from the old design — do not create; delete candidate if owner approves |
| `data/` · `assets/` | Created on first run; disposable — delete to reset |
| `app/dashboard.html`, `views/archive/page-*.html`, `gen_page.py` | Read-only context — never edit without explicit owner approval |
| `app/dashboard-live.html` | Live UI. `<head>` links the three CSS layers and carries the page layout in one `<style>` |
| `app/dashboard.html` | Mock. Uses the same three layers and its own inline layout `<style>` |
| `app/variables.css` | Tokens only: `@font-face` + CSS variables for light/dark |
| `app/base.css` | Global and tag defaults (appearance); no component classes |
| `app/component.css` | Reusable appearance classes; no layout properties |
| `docs/DESGIN.md`, `assets/fonts/`, `shots/`, `logo.svg` | Not yours, never touched |

## 8. First moves for the implementing session

1. Read `ARCHITECTURE.md` end to end (incl. §5 limits, §6 storage, §9 method)
2. Confirm no backend exists (owner deleted it) — rebuild, never "restore"
3. Confirm the owner said "go" — docs are locked first
4. Write `server.py` per §9.2–9.4 (COLLECT → disk JSON merge / ANALYZE)
5. No installer — owner runs `python server.py` locally
6. Run §9.6 checklist on a clean profile; report in the §5 format
