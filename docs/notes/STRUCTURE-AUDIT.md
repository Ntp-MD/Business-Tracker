# Project structure audit

Audited 2026-11-14. Scope: repository layout, dead code, generated clutter, docs accuracy,
and the invariants a future agent must not break. Code is the source of truth; this is a
snapshot, not a status board (status lives in [docs/README.md](../README.md)).

## Current layout

```
apps/web/            Next.js App Router; variants mockup | prod | live (APP_VARIANT)
apps/worker/         legacy job worker: fetch + refresh_views only (never collect)
backend/
  server.py          entrypoint: python backend/server.py (94 lines) + test re-exports
  runtime.py         paths, env, locks, progress, cancel state
  api/               HTTP handler, JSON/static/CORS helpers
  services/          items, archive/trash, import/export, profiles, status, legacy sources
  collectors/        registry, adapters/{gdelt,gnews}, gate, store, Python worker
  db.py              Supabase PostgREST/Storage adapter
  pw_login.py        one-time Playwright login
legacy/              frozen static UI served by the Python API
supabase/migrations/ append-only schema, RLS, storage, items lineage
scripts/             health check, backup, record-id backfill, import, baselines
tests/               Python unittest + Node fixture/contract tests
e2e/                 read-only Playwright variant tests (CI)
docs/                architecture, DB, deploy, design, plans, reference, notes
data/                runtime only, gitignored (reports, backups)
sessions/            Playwright sessions, gitignored
```

## Cleaned in this audit

- Generated clutter removed: `apps/web/.next/` (134 MB: 69.6 dev + 48.5 cache + 15.3 build),
  `__pycache__/` folders, `.ruff_cache/`, `apps/web/tsconfig.tsbuildinfo`. Rebuild with
  `npm run build:web` before `npm start`; `npm run dev` rebuilds automatically.
- Dead code removed: `collectors.store.load_state` (no callers).
- Empty `data/*.json` placeholders removed; the server recreates them when it falls back to
  the local adapter. `data/backups/` (logical Supabase export) and `data/reports/`
  (dry-run evidence) were kept.
- `.gitignore` now covers `.ruff_cache/` and `.pytest_cache/`.
- Docs corrected: AGENTS file map/commands, `docs/DB.md` collector tables + lineage,
  `docs/DEPLOY.md` workers/backup, `docs/ARCHITECTURE.md` phases.

## Invariants confirmed

- **Manual-only collection.** No auto search/collect: no scheduler, no `scheduled` job mode,
  no timer creates jobs. A collect needs a user action plus the Python worker running.
- **Routes stay separate.** `/` mock (no network), `/live` public read-only (anon views),
  `prod` authenticated with server-side service role.
- **Secrets.** Only `.env.example` is tracked; `.env`, `.env.local`, `apps/web/.env.local`
  are ignored, and no service key appears in static bundles or git history.
- **Migrations append-only.** `20261114000000_items_lineage.sql` is applied; do not edit it.
- **Tests never touch Supabase.** Python suite forces the local adapter.

## Open findings (owner decisions)

1. `.env` at the repo root is an unused duplicate of `.env.local` (same key set; the code
   loads only `.env.local`). It is gitignored; delete it once you confirm nothing outside the
   repo reads it.
2. `Dockerfile` + `render.yaml` describe the legacy Render API (`social-tracker-api`). The
   service may still be live; retire the files only after the Render service is suspended.
3. `items.keyword_key` unique index is disabled until the five legacy `Nvidia`/`nvidia`
   duplicate URL pairs are merged (owner data decision).
4. Vercel deployments cannot be verified from this checkout (no `.vercel`/token); confirm in
   the dashboard that pushes deploy, or run `vercel --prod` for the three projects.
5. Local `npx biome check apps` fails on Windows because the worktree uses CRLF while the
   formatter expects LF (`core.autocrlf=true`). CI (Linux) is the authority; do not "fix"
   formatting locally by rewriting files.

## Re-run the audit

```bash
git status --ignored --short            # tracked / ignored files
npx tsc --noEmit -p apps/web/tsconfig.json
npm run typecheck
python -m unittest discover -s tests
python -m ruff check backend tests scripts e2e
python -m ruff format --check backend tests scripts e2e
node --test tests/*.test.cjs
```
