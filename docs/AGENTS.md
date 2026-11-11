# AGENTS.md — current operating brief

> **Current direction (2026-11-11):** local Python app + optional Supabase storage,
> deployable API (Render Docker), static `/` mock + `/live` live.
> `docs/ARCHITECTURE.md` still contains the original 2026-11 spec; where it conflicts with
> this file or the “CURRENT” header there, **this file wins**.
>
> Future: `docs/MIGRATION-NEXT.md` (Next.js + TS worker) is a gated plan — do not start it
> without the owner’s go-ahead and Phase 0 baseline.

---

## 0. Project in one line

Thai social trends → collect → store (local JSON or Supabase) → dashboard → content angles.
Mockup and live are separate products: `/` = mock sample data, `/live` = real data.

---

## 1. Non-negotiables

- **Keep mock and live separate**: `index.html` (`/`) and `live/index.html` (`/live`).
  Never merge routes or reuse live data in mock.
- **No inline `<style>`**: CSS lives in `assets/css/` (`variables`, `base`, `component`,
  `layout`, `layout-live`).
- **Platform icons**: only `assets/icons/*.png` (owner-supplied); no other icon set.
- **Backend**: `server.py` + `db.py`. Python stdlib first; Playwright is approved for
  TikTok / FB Ads / TikTok Ads.
- **Supabase mode**: when `.env.local` has `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`,
  `SUPABASE_USER_ID`, storage goes through `db.py` (PostgREST), **instead of** local JSON.
  `SUPABASE_STRICT=1` fails loudly; `0` falls back to local files.
- **Secrets**: service role key only on the server/worker. Never in HTML/JS, never committed.
  `.env.local` is gitignored.
- **Deploy**: local `python server.py`; Render API (`Dockerfile`, `render.yaml`);
  GitHub Pages serves static `/` and a guarded `/live` until `api-base` is set.
- **Search Now requires a real server**: Playwright cannot run on GitHub Pages/Vercel
  serverless. Static Pages shows a preview notice and disables Search.
- **No service-role writes from browser**; web auth/CRUD must use Supabase Auth + RLS.
- **Do not delete user data** (`data/`, `archive`, `trash`, Supabase rows) without explicit
  owner instruction; destructive UI requires confirmation.

### Must ask before

- adding any dependency (npm/Next included) or changing the future migration phases
- changing Supabase schema/RLS, source list, or API contract
- exposing the API publicly / widening CORS / adding auth
- deleting user files or rewriting a whole page
- business decisions (keywords, KPI, content strategy, LINE OA)

---

## 2. Tool ladder

1. Python stdlib (`urllib`, `json`, `http.server`, `re`, `collections`, `os`)
2. Manual stdlib code around it
3. Approved: `playwright` (+ chromium); Supabase via `db.py` REST (no SDK)
4. New dependency/framework (Next.js, etc.) — **ask first**

Do not substitute collectors: YouTube `ytInitialData`; GNews RSS; TikTok/FB/TT Ads Playwright.
Storage writes are atomic; GET endpoints never write.

---

## 3. Verification (current)

Run before claiming done:

1. `python -m unittest discover -s tests -t .` → all tests pass
2. `python -m py_compile server.py db.py`
3. Inline scripts: extract each `<script>` body to a temp `.js` and run `node --check`
4. Local: `python server.py` → `/live/` loads; Search Now; CRUD; archive/trash; no console error
5. Static: `/` mock loads with no network calls; `/live` on GitHub Pages shows static notice,
   no JSON parse error, when `api-base` is empty
6. Supabase mode: rows land in Supabase (`items`, `profiles`, `keyword_stats`,
   `source_status`); service key never in browser
7. Mobile 390 / desktop 1440 screenshots unchanged where expected

---

## 4. Failure protocol

- Collector error → `errors[]`, continue other sources, never crash.
- Playwright browser missing → clear error; suggest `python -m playwright install chromium`
  or a host with Chromium. Do not silently drop the source.
- `Connection closed` → ensure one server instance / one `PW_LOCK`; retry once.
- Supabase error with `SUPABASE_STRICT=1` → request fails with the Supabase message;
  `0` → local fallback. Report which mode is active.
- Static host `/api` returns HTML → show static preview, not `Unexpected token '<'`.
- Corrupt local JSON → disposable; re-fetch. Do not delete Supabase rows without confirmation.
- Doc/spec inconsistency → flag it; do not silently resolve.

---

## 5. How to report

1. What changed (one line each)
2. How verified (tests / exact flows / screenshots)
3. Blocked + owner action
4. Remaining

Never claim done if a listed verification failed.

---

## 6. File map (current)

| File | Purpose |
|---|---|
| `index.html` | Mockup `/`; sample data, no backend |
| `live/index.html` | Live `/live/`; API/Supabase, QOL features |
| `assets/css/*.css` | Layered CSS; no inline styles |
| `assets/icons/*.png` | Platform icons (Flaticon; see README) |
| `server.py` | Local/Render API, collectors, routing, static serving |
| `db.py` | Supabase adapter (PostgREST/Storage); service role only |
| `pw_login.py` | One-time headed login for TikTok/FB sessions |
| `supabase/migrations/` | Schema + RLS + storage bucket |
| `scripts/import_to_supabase.py` | Import `data/*.json` + thumbnails |
| `tests/` | stdlib unittest; forced local adapter, never Supabase |
| `Dockerfile`, `render.yaml`, `.dockerignore` | Render API deployment |
| `docs/DEPLOY.md` | Pages + Render + `api-base` + CORS |
| `docs/DB.md` | Supabase schema/mapping |
| `docs/MIGRATION-NEXT.md` | Future Next.js rails/phases (plan only) |
| `docs/DESGIN.md` | Design spec / visual language |
| `data/`, `sessions/`, `assets/*.jpg` | Runtime/disposable; gitignored |

---

## 7. First moves

1. Read this file + `docs/DEPLOY.md` + `docs/DB.md`
2. Check `.env.local` mode (Supabase vs local)
3. Run tests + local smoke before editing
4. Make the smallest change; verify with §3
5. For Next migration, follow `docs/MIGRATION-NEXT.md` gates — no big-bang rewrite
