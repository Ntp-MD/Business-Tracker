# TrendRail

**Social intelligence for content research.**

TrendRail brings social content, news, and advertising research into one dashboard. It helps
teams collect results by keyword, review their sources, and organize material for further work.

> Proprietary software. All rights reserved.

[View the live dashboard](https://trendrail-live.vercel.app) ·
[Explore the mockup](https://trendrail-mockup.vercel.app) ·
[Documentation](docs/README.md)

## Capabilities

- **Collect:** search YouTube, Google News, TikTok, Facebook Ads Library, and TikTok Creative
  Center through the existing collectors.
- **Review:** search and filter stored items by text, source, and date; inspect source links and metrics.
- **Organize:** manage items, archive or restore them, and export data as CSV or JSON.
- **Share:** use the public read-only dashboard or the separate mockup with sample data.

Collection runs through a local worker and Python API; source availability and login
requirements vary. The mockup uses fixtures and does not connect to production data.

## Architecture

The web application is built with Next.js. Supabase stores the live data and job queue,
while a local TypeScript worker dispatches collection jobs to the Python API. The legacy
static dashboard remains available through the Python server.

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
docs/         Documentation and plans (see docs/README.md)
data/         Runtime JSON cache (gitignored)
sessions/     Playwright login sessions (gitignored)
```

## Run

Node 22 and Python 3.12 are the pinned runtimes. Configure the environment using
`.env.example` and [the deployment guide](docs/DEPLOY.md) before running the live application.

```bash
# Next app
npm ci
npm run dev                 # http://localhost:3000

# Python collector API (used by Search Now)
python backend/server.py    # http://127.0.0.1:8000

# Worker (separate terminal)
npm run build:worker
node --env-file=.env.local apps/worker/dist/index.js

# Tests
python -m unittest discover -s tests

# Lint / format (dev only)
pip install -r requirements-dev.txt
npm run lint
npm run format:check

# Playwright collectors only (TikTok / FB Ads / TikTok Ads)
pip install -r requirements.txt
```

Node is pinned in `.nvmrc` and `engines.node`; Python in `.python-version`. Backend code is
stdlib-only and runs on Python 3.10+; Playwright is pinned in
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

## Collector framework

`backend/collectors/` keeps the registry, quality gate, dry-run report and targeted
persistence for future approved sources. **No adapter is enabled** — Hacker News was removed
by owner decision on 2026-11-12, so there is no collector CLI command until a new adapter is
added and approved.

The collector schema remains in `supabase/migrations/20261112010000_collectors.sql`;
`20261112020000_remove_hackernews.sql` narrows the source/metric checks back. Writes stay off
unless `COLLECTOR_WRITE_ENABLED=1` is set intentionally for a future adapter.

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
| `mockup` | `https://trendrail-mockup.vercel.app` | full static mock data | no |
| `prod` | `https://trendrail.vercel.app` | Supabase | yes |
| `live` | `https://trendrail-live.vercel.app` | same Supabase | no (read-only) |

The same codebase runs all three; `APP_VARIANT` selects behavior. See
[docs/DEPLOY.md](docs/DEPLOY.md).

## Docs

Start at [docs/README.md](docs/README.md). Working rules are in [AGENTS.md](AGENTS.md).
Active backlog and remaining plan: [docs/plans/COLLECTOR-INTEGRATION-PLAN.md](docs/plans/COLLECTOR-INTEGRATION-PLAN.md).

## License

TrendRail is proprietary software and is not offered under an open-source license.
Copyright © 2026 TrendRail. All rights reserved. See [LICENSE](LICENSE) for terms;
third-party dependencies retain their respective licenses.

Security reports: [SECURITY.md](SECURITY.md). Contributor guidance for authorized
maintainers: [CONTRIBUTING.md](CONTRIBUTING.md).
