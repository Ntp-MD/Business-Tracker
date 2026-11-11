# Migration Plan — Next.js + Supabase + TypeScript worker

> **Status (2026-11-11): Phase 0–2 done.** Baseline frozen, npm workspaces scaffolded,
> Supabase read layer live in `apps/web`. Legacy `/` + `/live/` still the deployed app.
> Phase 3 (read-only UI) is next.
>
> Goal: move from Python `server.py` + static HTML to a stack that fits Vercel/Supabase,
> while **keeping `/` = mockup and `/live/` = live separate at all times**. `server.py`
> stays as the local YouTube/GNews collector; the worker handles only Playwright sources.
>
> Every phase must pass its gate before the next; no new features during the migration
> until parity is complete.

---

## 0. Locked decisions

| Topic | Decision |
|---|---|
| Framework | Next.js (App Router) + TypeScript |
| Frontend host | Vercel (replaces GitHub Pages at cutover; Pages is fallback until then) |
| Data/Auth/Storage | Supabase (Postgres + Storage). RLS stays in schema; **no end-user auth yet** (single owner) |
| Web → data | Browser calls Next routes; Next server holds the service role key. Browser never gets it |
| Worker | Node + TypeScript + Playwright, **runs local**, polls Supabase `jobs`; Playwright sources only |
| Sources split | YouTube + GNews stay in `server.py`; TikTok / FB Ads / TikTok Ads go through the worker |
| Playwright login | TikTok / FB Ads / TikTok Ads require a collector session; UI disables them + explains when missing |
| Routes | `/` = mockup, `/live` = live; never merge |
| Mock | sample/fixture only; never calls Supabase/worker |
| Search Now | enqueue `jobs` row; local worker claims it. Nothing Playwright runs in Vercel |
| Secrets | `SUPABASE_SERVICE_ROLE_KEY` stays on server/worker; never in a browser bundle |
| Storage writes | Automatic: `server.py`/worker upsert to Supabase and upload thumbnails on every collect. No manual import (one-time script only for old local data) |
| Legacy | keep `index.html` + `live/index.html` until Phase 7; keep `server.py` after that as collector |

---

## 1. Rails (guard rails)

1. **One page per PR** — never port several pages in one PR
2. **No redesign** — CSS/layout must match; change only what is specified
3. **Parity before new features** — new features go to the backlog, never interleaved
4. **Mock is truly separate** — no import from `apps/web/lib/supabase` in the mock route
5. **Legacy still runs** — every phase must keep `/` and `/live/` working
6. **Every phase has a rollback** — feature flag or revert commit
7. **No service key in browser** — grep before every merge
8. **No Playwright in Vercel functions** — worker only
9. **Service key stays server-side** — Python/Next server only; browser talks to our routes.
   RLS remains in the schema for future real auth, but is not the current access path
10. **Every phase needs:** unit test + Playwright screenshot 1440/390 + parity checklist

---

## 2. Current baseline (before starting)

- Live: `/live/` uses `server.py` + `data/*.json` or Supabase via `db.py`
- Mock: `/` uses built-in sample data; no network calls
- CSS: `assets/css/variables|base|component|layout|layout-live.css`; no inline `<style>`
- Icons: `assets/icons/*.png` (platform icons only)
- Server: `server.py` (~2.7k lines) + `db.py` adapter; collectors + API
- Tests: `tests/test_core.py` 17 tests; forced local adapter (never touches Supabase)
- Deploy: `Dockerfile` + `render.yaml` (Render API), GitHub Pages static + static guard
- Latest QOL: filter/sort/pager/CRUD/bulk/archive/trash/toast/undo complete in live
- **No Next/Vercel/worker yet** — all of that is the goal of this plan

**Baseline actions (Phase 0)**
- Tag the current commit: `git tag pre-next-migration`
- Export backup: `GET /api/export.zip`, store outside the repo
- Capture screenshots of every `/live/` + `/` page (1440/390)
- Record the feature inventory from §4
- Do not edit code before the baseline is complete

**Exit gate 0:** tag, backup, screenshots, inventory all present

**Baseline captured (2026-11-11)**
- Tag: `pre-next-migration` (annotated, pushed) at commit `54bd389`
- Backup: `export.zip` — 2,136,137 bytes, 139 entries (items + thumbnails), stored outside the repo
  in `%TEMP%\opencode\st-baseline-20261111\`
- Screenshots: 50 PNGs = 8 live pages + 8 mock pages × 1440×900 / 390×844; 0 console errors
- Snapshot: 314 live items, 0 archived, 0 trashed, 5 sources; mock sample set separate (`index.html`)
- Live pages in baseline: overview, sources, terms, ideas, items, archive, ads, settings
  (locked: crm, competitors, calendar, tasks, reports, goals)
- Capture script: `python scripts/capture_baseline.py [--base …] [--out baseline-shots]`

---

## 3. Target structure

Scaffold commands (Phase 1): `npm install` → `npm run build` (Next + worker) →
`npm run typecheck` (shared + worker). Legacy `python server.py` is unaffected.

Next server env (Vercel + local dev): `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.
They are read only on the server; never prefix with `NEXT_PUBLIC_`.

```
apps/web/                    Next.js + TypeScript (Vercel)
  app/(mock)/page.tsx        mockup  /
  app/live/…                 live    /live
  components/…               shared UI
  lib/supabase/browser.ts    anon client
  lib/supabase/server.ts     server client (cookies)
  lib/api/legacy.ts          adapter over the legacy API during migration
  middleware.ts              auth guard /live

apps/worker/                 Node 22 + TS + Playwright
  src/collectors/youtube.ts
  src/collectors/gnews.ts
  src/collectors/tiktok.ts
  src/collectors/fbads.ts
  src/collectors/ttads.ts
  src/jobs.ts                claim/run/update jobs
  src/index.ts               poll loop

packages/shared/             types + zod
  src/item.ts, profile.ts, job.ts

supabase/migrations/…        schema/RLS
vercel.json                  root/rewrites (if needed)
render.yaml                  worker service
```

---

## 4. Feature inventory (parity checklist)

### Live `/live`
- [ ] Fetch strip: profile, keyword, sources, mode, fresh
- [ ] Search Now: start job, queued/running progress, cancel, errors, worker offline state
- [ ] Worker-offline hint: says the job is queued in Supabase, why (worker runs on the owner's PC), and how to start it (exact command)
- [ ] Playwright sources (TikTok / FB Ads / TikTok Ads): disabled + "login required" when no session
- [ ] Overview: KPI, top items, terms, ideas, charts
- [ ] Sources: cards, counts, last error/log
- [ ] Terms: list/detail
- [ ] Ideas: cards/tabs
- [ ] All items: filters (platform/date/text), sort, pager, CSV
- [ ] Items CRUD: add/edit/delete, bulk move/delete
- [ ] Archive: tabs, multi-select, restore, delete permanently
- [ ] Trash: restore/purge
- [ ] Ads: collected ads + counts
- [ ] Settings: profiles CRUD, sources toggles, keywords, export/import,
      disk status, clear/prune, theme, sessions
- [ ] Patch notes/version
- [ ] Locked pages behavior
- [ ] Responsive 390/768/1440
- [ ] Reduced motion / focus traps / aria

### Mock `/`
- [ ] Every page has samples matching the current app
- [ ] No network/Supabase calls
- [ ] Mock buttons work in memory
- [ ] Route separate from live

**Rule:** any page that is not at parity yet keeps the legacy UI behind a feature flag; never remove the old one.

---

## 5. Data/API mapping

| Legacy | New | Notes |
|---|---|---|
| `POST /api/fetch` | `jobs` table + worker | web creates job; worker claims it |
| `GET /api/progress` | `jobs` row / Realtime | polling first |
| `POST /api/cancel` | `jobs.cancel_requested` | worker checks before the next source |
| `GET /api/summary?q=` | Supabase query + `keyword_stats` | or RPC `summary(q)` |
| `GET /api/status` | counts + `source_status` | one RPC / several queries |
| `/api/profiles` CRUD | Next route → Supabase table | server-side service role |
| `/api/items` CRUD | Next route → Supabase `items` | soft delete/archive, server-side |
| `/api/archive` | `items.archived_at` | |
| `/api/trash` | `items.deleted_at` | purge after 7 days |
| `/api/refresh-stats` | `jobs` kind=`refresh_views` | worker |
| `/api/export/import` | browser + Supabase Storage/JSON | |
| `GET /api/keywords` | view/query | |
| `GET /assets/*.jpg` | Next asset route → Supabase Storage | `asset_path` keeps its current value |

**Never** expose the service role to the browser; every write goes through a Next route or the worker.

---

## 6. Worker design (performance)

- Runs **locally** (owner PC) next to `server.py`; polls Supabase. No worker on Vercel.
- Scope: TikTok / FB Ads / TikTok Ads only — YouTube + GNews stay in `server.py`.
- `jobs` table: `id, kind, status(queued|running|done|error|cancelled), payload jsonb, progress, total, error, created_at, started_at, finished_at`
- Worker polls every 2s, claims atomically:
  `update jobs set status='running', started_at=now() where id = (select id ... for update skip locked limit 1) returning *`
- 1 job = 1 keyword/source set; results written to `items`/`source_status`
- Concurrency starts at 1 (Playwright is heavy), raise to 2 once sessions are separate
- Cancel: `cancel_requested=true`; worker checks between sources
- Retry: transient errors twice, with backoff
- Progress: update `progress/total`; a heartbeat row lets the UI show "worker offline"
- Offline UX: Search Now still creates the job; UI shows "queued — worker offline" plus a
  hint (why: worker runs on the owner's PC; how: start command + `pw_login.py` for sessions).
  Never fake progress or silently drop the job.
- Session login: Playwright profile in local `sessions/`; missing session = job refused with a clear error, UI disables those sources
- If the owner's PC is off: jobs stay `queued`; UI says so instead of pretending to run

---

## 7. Phases + gates

### Phase 0 — Freeze baseline
**Work:** tag, backup, screenshots, inventory
**Gate:** §2 complete; no code touched

### Phase 1 — Scaffold only
**Work:** `apps/web` Next + TS, `apps/worker` skeleton, `packages/shared`, env example
**Forbidden:** changing routes that are already deployed
**Gate:** `npm run build` passes; worker `tsc` passes; legacy still opens

### Phase 2 — Read layer (no auth)
**Work:** server-only Supabase client, item/profile reads, `/api/health` smoke route
**Gate:** counts match the Python API; service key absent from client bundles; mock untouched

### Phase 3 — Live read-only pages (one at a time)
Order: Overview → All items → Sources → Archive → Ads → Terms/Ideas → Settings (read)
**Gate per page:** data matches legacy, screenshot matches, responsive, no console errors
**Flag:** `NEXT_PUBLIC_LIVE_UI=legacy|next` (switch back anytime)

### Phase 4 — CRUD
**Work:** item edit/delete/archive/move, bulk, profiles, trash, import/export (Next routes)
**Gate:** operation parity; archive/trash filters match; no service key in the browser

### Phase 5 — Local worker + job queue
**Work:** `jobs` table, local worker for Playwright sources, Search Now/Refresh views, cancel/progress, session gate
**Gate:** job from web → local worker → Supabase; retry/cancel; YouTube/GNews still flow through `server.py`
**Forbidden:** calling the worker from the browser with the service key; running Playwright in Vercel

### Phase 6 — Port mock
**Work:** `/` as React + fixtures; UI parity
**Gate:** mock makes no network calls; screenshot parity; `/live` unaffected

### Phase 7 — Cutover + cleanup
**Work:** Vercel serves `/` + `/live`; GitHub Pages retired; `server.py` stays as local collector (no public API needed)
**Gate:** full smoke test; backup; rollback tag; one week of monitoring

---

## 8. Verification matrix

| Level | Tool | Passes when |
|---|---|---|
| Unit | Vitest | shared/types, adapters, collectors parsing |
| Data access | smoke script | next `/api/health` counts match `server.py` /api/status |
| API | smoke script | summary/status/CRUD/job match the schema |
| UI parity | Playwright | screenshot 1440/390 + main flows |
| Data parity | export comparison | count/by_source/top items match legacy |
| Worker | integration | job succeeds, cancel, retry, progress |

**Flows to test at every cutover phase**
1. Open `/live` → Overview
2. Search Now → queued → running → cancel → result (or "worker offline")
3. Filter/sort/pager/CSV
4. Add/edit/delete item
5. Bulk archive → Archive restore/delete
6. Trash restore/purge
7. Profile CRUD
8. Export/import
9. Theme/mobile/patch notes

---

## 9. Rollback

- Every phase uses a branch + tag: `next-p1`, `next-p2`, …
- Feature flag `NEXT_PUBLIC_LIVE_UI` switches legacy/Next
- Never delete `server.py`/`live/index.html` before Phase 7
- If Supabase is down: the legacy local API still works (until cutover)
- If the worker is down: Search Now is disabled with a message; read pages keep working

---

## 10. Risks / open questions

| Risk | Mitigation |
|---|---|
| Rewrite drifts the UI | per-page parity screenshots + flag |
| Open API (no login) | narrow scope accepted by owner; add auth before sharing the URL |
| Worker/Vercel timeouts | job queue + local worker + retry |
| Mock calls live data | import boundary + lint rule |
| Scope creep | separate backlog; new features after Phase 7 |
| Secret leaks | grep before merge; service key only in server env |
| Two UIs at once confuse users | route flag + "legacy/next" banner |

**Decided 2026-11-11**
1. One Supabase project for dev/prod (split only if needed later)
2. No end-user login for now; server-side service role
3. Worker runs locally, Playwright sources only
4. Vercel root directory: `apps/web`
5. GitHub Pages is fallback until Vercel cutover, then retired

**Still open**
1. Search Now when the local worker is offline — show queued forever, or offer "run local collector" button?
2. Should `server.py` expose a job trigger too (same `jobs` table), or stay manual?

---

## 11. Definition of Done (whole project)

- `/` mock and `/live` live stay separate, deployed on Vercel
- full CRUD; Search Now through jobs + local worker for Playwright sources
- YouTube/GNews keep collecting through `server.py`
- no service key in the browser
- no Playwright in Vercel
- parity checklist complete for every page
- legacy server/Pages shut down or redirected
- docs + backup + rollback tag

---

## 12. Progress log

| Phase | Status | Commit | Notes |
|---|---|---|---|
| 0 baseline | ☑ | `54bd389` + tag `pre-next-migration` | tag/backup/50 screenshots/inventory done 2026-11-11 |
| 1 scaffold | ☑ | `Phase 1 commit` | npm workspaces; Next builds `/` + `/live` placeholders; worker tsc passes (2026-11-11) |
| 2 read layer | ☑ | `Phase 2 commit` | server-only Supabase client; `/api/health` matches Python counts (2026-11-11) |
| 3 live read | ☐ | | |
| 4 CRUD | ☐ | | |
| 5 worker/jobs | ☐ | | |
| 6 mock | ☐ | | |
| 7 cutover | ☐ | | |
