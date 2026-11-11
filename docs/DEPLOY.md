# Deploy (Render API + static frontend)

## Vercel (current production)

| URL | What |
|---|---|
| `https://social-tracker-pink.vercel.app` | Next.js app (`/` mock, `/live` live) |
| `https://social-tracker-ntpsrms-projects.vercel.app` | project alias |

- Project `social-tracker`, root directory `apps/web`, framework Next.js.
- Env (Production + Preview): `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_USER_ID` (server-only).
- Deployment protection (Vercel Authentication) is **off** so the app is public; the data API has no login by owner decision.
- GitHub Pages still serves the legacy app until it is retired.

## Paths

| Path | Page | Source |
|---|---|---|
| `/Business-Tracker/` | mockup | `index.html` |
| `/Business-Tracker/live/` | real dashboard | `live/index.html` |
| `/Business-Tracker/assets/` | CSS / icons / fonts / thumbnails | `assets/` |

Locally `python server.py` serves the same layout:

- `http://127.0.0.1:8000/` → mockup
- `http://127.0.0.1:8000/live/` → live
- old links `/dashboard-live.html` and `/app/dashboard.html` redirect.

## Vercel

Vercel can host the static `/` and `/live/` pages, but **cannot run Playwright or the Python collectors**. Point `api-base` at the Render/Fly/VPS API exactly like GitHub Pages. A Next.js migration is planned in `docs/MIGRATION-NEXT.md`; do not run Playwright in serverless functions.

## GitHub Pages

Push `main`; Pages serves the repository root. Root and `/live/` both load statically, but **`live/` needs an API** for data (`/api/summary`, `/api/status`, …). GitHub Pages cannot run `server.py`.

Until `api-base` is set, `/live/` shows a **Static preview** notice and disables Search Now.

### Render (recommended)

1. Push this repo (the included `Dockerfile` + `render.yaml` are ready).
2. Render → **New → Blueprint** → select the repo. It creates `social-tracker-api` (Docker, free).
3. Fill the secret env vars in Render:
   ```
   SUPABASE_URL=https://<project>.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=<service role — server only>
   SUPABASE_USER_ID=<auth user uuid>
   SUPABASE_STRICT=1
   ALLOW_ORIGIN=https://ntp-md.github.io
   ```
4. Deploy and copy the HTTPS URL, e.g. `https://social-tracker-api.onrender.com`.
5. Set it in `live/index.html`:
   ```html
   <meta name="api-base" content="https://social-tracker-api.onrender.com" />
   ```
6. Push; Pages rebuilds and live becomes read/write via the API.

`HOST=0.0.0.0` / `$PORT` are already supported by `server.py` and the Dockerfile.
CORS is handled by `ALLOW_ORIGIN`; the API has no login, so keep the origin narrow and do not set `ALLOW_ORIGIN=*`.
Container filesystem is ephemeral: Supabase is the data store; TikTok/Facebook *session* logins need a persistent disk or use public mode.
Free Render services sleep after idle and may take ~30–60s on the first request; Playwright collectors are memory-heavy.

### Other hosts

Host `server.py` on Fly.io / a VPS / a tunnel, expose HTTPS, set the same env vars, then point `api-base` at it. The Python process must be able to run Chromium for TikTok / FB Ads / TikTok Ads; YouTube + GNews only need stdlib HTTP.

## Local worker (Search Now)

Vercel can't run Playwright. Search Now writes a `jobs` row; a local worker claims it and drives the collector.

1. Apply `supabase/migrations/20261111000000_jobs.sql` in the Supabase SQL editor (once).
2. `python server.py` — collectors + API on `127.0.0.1:8000`.
3. `npm run build -w apps/worker`
4. `node --env-file=.env.local apps/worker/dist/index.js` — polls Supabase every 3 s, writes a heartbeat.

If the worker is offline, jobs stay `queued` and the UI says so. TikTok / FB Ads / TikTok Ads also need a logged-in session (`python pw_login.py`).

## Mockup

`index.html` is static sample data and needs no backend. The live page keeps its own copy only through `live/index.html`; both load CSS from `assets/css/`.
