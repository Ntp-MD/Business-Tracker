# AGENTS.md — working rules

Operational brief for coding agents in this repo. Keep this file about **rules and commands**.
Status and remaining work live in [`docs/README.md`](docs/README.md); do not duplicate them here.

## 1. System

| Part | What it is |
|---|---|
| `apps/web/` | Next.js App Router; three Vercel variants (`mockup`, `prod`, `live`) selected by `APP_VARIANT` |
| `apps/worker/` | TypeScript worker on the owner's PC; claims Supabase `jobs` and calls the local collector |
| `backend/` | Python stdlib HTTP API + collectors (`server.py`, `db.py`, `pw_login.py`); serves the legacy static app |
| `legacy/` | Old static UI served by `backend/server.py` at `/` and `/live/` |
| `supabase/migrations/` | Postgres schema, RLS, storage |
| `data/`, `sessions/` | Runtime only; gitignored |

The Next app requires Supabase. The Python side uses Supabase when `SUPABASE_URL`,
`SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_USER_ID` are set; otherwise it falls back to
`data/*.json`.

## 2. Commands

```bash
# Python API + legacy static UI (127.0.0.1:8000)
python backend/server.py

# Next app (localhost:3000)
npm run dev

# Builds
npm run build                 # web + worker
npm run build:web
npm run build:worker

# Tests / checks
python -m unittest discover -s tests
python -m py_compile backend/server.py backend/db.py backend/pw_login.py
npx tsc --noEmit -p apps/web/tsconfig.json
npm run typecheck             # worker

# Worker (after build; from repo root)
node --env-file=.env.local apps/worker/dist/index.js

# Playwright session login
python backend/pw_login.py tiktok
python backend/pw_login.py facebook
```

## 3. Non-negotiables

- **Keep routes separate.** `/` is mock only: no Supabase, no worker, no network calls.
  `/live` is real data. Never merge them.
- **Vercel variants:** `mockup` has no Supabase env and serves `/` only; `live` is read-only
  and blocks non-GET; only `prod` may write. Never copy the service key into `mockup`.
- **Service role key stays server/worker side.** Never expose it to the browser, never prefix
  with `NEXT_PUBLIC_`, never commit `.env.local`.
- **No Playwright in serverless.** Vercel cannot run collectors; the worker runs locally.
- **Don't delete `legacy/`.** It is still served by the Python API. Remove only on explicit
  owner instruction.
- **Don't delete user data** (`data/`, `sessions/`, Supabase rows) or add destructive UI
  without confirmation.
- **CSS:** Next styles live in `apps/web/public/assets/css/`; legacy styles in
  `legacy/assets/css/`. Treat them as separate copies and change them only for the task.
  No inline `<style>` in legacy pages.
- **Icons:** inline SVG via `apps/web/components/live/source-icon.tsx`; `legacy/assets/icons/*.png`
  is legacy-only.
- **Tests never touch Supabase.** Keep the forced local adapter in `tests/test_core.py`.
- **Migrations are append-only.** Add a new file in `supabase/migrations/`; never edit one
  that has been applied.
- **Don't edit generated output:** `apps/web/.next/`, `apps/worker/dist/`, `__pycache__/`.
- **Small diffs.** Match existing patterns; don't reformat or rename unrelated code.
- **Python stdlib first.** Playwright is approved only for TikTok / FB Ads / TikTok Ads.

## 4. Ask before

- adding a dependency or changing the framework/toolchain
- changing Supabase schema, RLS, storage, source list, or API contract
- exposing the API publicly, widening CORS, or adding auth
- deploying to Vercel/Render, changing DNS, or touching GitHub Pages settings
- changing `APP_VARIANT`, Vercel project env vars/domains, or deployment protection
- deleting user files or rewriting a whole page
- business decisions (keywords, KPI, content strategy, LINE OA)
- changing the collector integration plan

## 5. Verification

Run the checks that match the change; all must pass before claiming done.

1. `python -m unittest discover -s tests` — forced local adapter, never Supabase
2. `python -m py_compile backend/server.py backend/db.py backend/pw_login.py`
3. `npx tsc --noEmit -p apps/web/tsconfig.json` for web changes
4. `npm run typecheck` for worker changes
5. `npm run build` when touching build config or shared types
6. Manual smoke for UI/API changes:
   - `python backend/server.py` → `/`, `/live/`, `/api/status`
   - `npm run dev` → `/live`, filters, CRUD, archive/trash, no console errors
   - Variant smoke: `mockup` `/` 200 and `/live` → `/`; `live` `/` → `/live`, `/live` 200,
     `POST /live/items` 403; `prod` full UI and writes
7. Docs-only changes: verify relative links resolve.

If a check fails, report it. Never claim done with a failing check.

## 6. File map

| Path | Purpose |
|---|---|
| `apps/web/` | Next.js app; Vercel root directory |
| `apps/worker/` | Supabase job worker; local Playwright |
| `backend/server.py` | API, collectors, routing, legacy static serving |
| `backend/db.py` | Supabase PostgREST/Storage adapter |
| `backend/pw_login.py` | One-time headed login for TikTok/FB sessions |
| `legacy/` | Static mock + live pages, CSS, icons, logo |
| `supabase/migrations/` | Schema, RLS, storage bucket |
| `scripts/import_to_supabase.py` | One-time JSON/thumbnail import |
| `scripts/capture_baseline.py` | Parity screenshots of legacy pages |
| `tests/test_core.py` | Python unittest suite |
| `Dockerfile`, `render.yaml` | Render API deployment |
| `docs/` | DB, deploy, design, plans, reference, notes (index: `docs/README.md`) |

## 7. Report

End every task with:

1. **Changed** — one line per file/area
2. **Verified** — exact commands and results
3. **Blocked** — owner action needed, if any
4. **Remaining** — anything not done

Do not include status/history in this file; update `docs/README.md` instead.
