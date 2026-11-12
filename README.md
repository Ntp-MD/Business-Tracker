# TrendRail

Thai social-trend collector and dashboard. Next.js app on Vercel, Supabase for storage, and a
local Python collector driven by a job worker.

## Layout

```
apps/
  web/        Next.js app; 3 Vercel variants via APP_VARIANT (mockup/prod/live)
  worker/     TypeScript worker: claims Supabase jobs, calls the local collector
backend/      Python collector API (`server.py`, `db.py`, `pw_login.py`)
legacy/       Old static dashboard served by the Python API at `/` and `/live/`
  index.html  mock `/`
  live/       live `/live/`
  assets/     CSS, fonts, icons, runtime thumbnails
  app/        logo
supabase/     SQL migrations
scripts/      One-off import / baseline capture tools
tests/        Python unittest suite
docs/         Current docs + plans + notes (see docs/README.md)
data/         Runtime JSON cache (gitignored)
sessions/     Playwright login sessions (gitignored)
```

## Run

```bash
# Next app
npm install
npm run dev                 # http://localhost:3000

# Python collector API (used by Search Now)
python backend/server.py    # http://127.0.0.1:8000

# Worker (separate terminal)
npm run build:worker
npm run start -w apps/worker

# Tests
python -m unittest discover -s tests
```

Copy `.env.example` to `.env.local` for the Python side. The Next app reads its env from
`apps/web/.env.local` or the host's environment.

## Deployments

| Variant | URL | Data | Writes |
|---|---|---|---|
| `mockup` | `https://trendrail-mockup.vercel.app` | fixtures only | no |
| `prod` | `https://trendrail.vercel.app` | Supabase | yes |
| `live` | `https://trendrail-live.vercel.app` | same Supabase | no (read-only) |

The same codebase runs all three; `APP_VARIANT` selects behavior. See
[docs/DEPLOY.md](docs/DEPLOY.md).

## Docs

Start at [docs/README.md](docs/README.md). Working rules are in [AGENTS.md](AGENTS.md).
Migration closed 2026-11-11: redirects live, Pages disabled; monitoring through 2026-11-18 and
Render API shutdown are tracked in [docs/README.md](docs/README.md).
Active backlog: [docs/plans/2026-11-12-task-backlog.md](docs/plans/2026-11-12-task-backlog.md).
Remaining plan: [docs/plans/COLLECTOR-INTEGRATION-PLAN.md](docs/plans/COLLECTOR-INTEGRATION-PLAN.md).
Notes and ideas are in `docs/notes/`.
