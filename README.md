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

# Lint / format (dev only)
pip install -r requirements-dev.txt
npm run lint
npm run format:check

# Playwright collectors only (TikTok / FB Ads / TikTok Ads)
pip install -r requirements.txt
```

Node 22 (`.nvmrc`, `engines.node`) and Python 3.12 (`.python-version`) are the pinned
versions. Backend code is stdlib-only and runs on Python 3.10+; Playwright is pinned in
`requirements.txt` to match `Dockerfile`. Web lint/format uses Biome (`biome.json`), Python
uses Ruff (`pyproject.toml`); `npm run format` applies fixes.

### E2E smoke

`e2e/` checks the three deployed variants. Read-only tests run in CI; the prod write test
creates one disposable item and deletes it, so it runs only with owner credentials:

```bash
python -m playwright install chromium
npm run test:e2e

# Prod filter + archive/trash lifecycle (writes one temp item)
E2E_PROD_EMAIL=owner@example.com E2E_PROD_PASSWORD=... npm run test:e2e
```

URLs default to the Vercel deployments; override with `E2E_MOCKUP_URL`, `E2E_LIVE_URL`,
`E2E_PROD_URL`.

## Observability

- `GET /api/health` reports item counts and the worker heartbeat (`stale` after 5 minutes).
- The Next proxy and the Python API emit JSON logs with a `request_id` per request.
- `.github/workflows/health.yml` runs every 30 minutes against prod + live, opens or updates
  a `Health check failing` issue on failure, and closes it after recovery.
- To test the alert path: `gh workflow run health.yml -f simulate_failure=true`.

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
