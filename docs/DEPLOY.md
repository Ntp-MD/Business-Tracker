# Deploy (Vercel + local worker)

## Vercel environments

| Variant | Vercel project | URL | Data | Writes |
|---|---|---|---|---|
| `mockup` | `trendrail-mockup` | `https://trendrail-mockup.vercel.app` | Fixtures only, no Supabase env | No |
| `prod` | `trendrail` | `https://trendrail.vercel.app` | Supabase (shared) | Yes |
| `live` | `trendrail-live` | `https://trendrail-live.vercel.app` | Same Supabase, read-only UI/API | No |

All three projects use root directory `apps/web`, framework Next.js, and deployment protection off.

- `APP_VARIANT` selects behavior: `mockup` → `/` only, `/live` + `/api` redirect to `/`; `live` → `/` redirects to `/live`, `/live/settings`, `/live/trash`, edit routes redirect, non-GET requests return 403; `prod` → full app (default when unset).
- **mockup** has only `APP_VARIANT=mockup`; it must not receive Supabase keys.
- **prod** has `APP_VARIANT=prod` for Production and `APP_VARIANT=live` for Preview, so preview deployments are read-only. Supabase env is available to Production + Preview.
- **live** has `APP_VARIANT=live` plus the same Supabase keys. Writes are blocked by `apps/web/proxy.ts` and `assertWritable()` in server actions. Caveat: live still runs with the service role key because reads need it; a code bug could bypass the guard.
- Vercel cannot run Playwright or the Python collectors; Search Now uses the local worker (prod only).
- Legacy redirects: `/dashboard-live.html`, `/dashboard.html`, `/app/dashboard.html` → 307 `/live`.
- GitHub Pages is disabled. The old static app stays under `legacy/` for the Python server.

Deploy from the repo root (project root is `apps/web`):

```bash
vercel deploy --project trendrail-mockup --prod
vercel deploy --project trendrail --prod
vercel deploy --project trendrail-live --prod
```

## Local Python API + legacy UI

```bash
python backend/server.py     # 127.0.0.1:8000
```

| Path | Source |
|---|---|
| `/` | `legacy/index.html` |
| `/live/` | `legacy/live/index.html` |
| `/assets/` | `legacy/assets/` |

Old links `/dashboard-live.html` and `/app/dashboard.html` redirect to `/live/`.

## Self-host the Python API (optional)

Host `backend/server.py` on Fly.io, a VPS, or a tunnel; expose HTTPS and set the same env vars.
The process needs Chromium for TikTok / FB Ads / TikTok Ads; YouTube + GNews only need stdlib
HTTP.

```bash
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<server only>
SUPABASE_USER_ID=<auth user uuid>
SUPABASE_STRICT=1
ALLOW_ORIGIN=https://<allowed-origin>
```

`HOST=0.0.0.0` and `$PORT` are supported by `backend/server.py` and the `Dockerfile`. Keep
`ALLOW_ORIGIN` narrow; never `*`. The filesystem is ephemeral: Supabase is the data store,
and TikTok/Facebook sessions need a persistent disk or public mode.

The old Render service (`social-tracker-api`) may still be running; disable it in the Render
dashboard when no longer needed.

## Local worker (Search Now)

Search Now writes a `jobs` row; a local worker claims it and calls the Python API.

1. Apply `supabase/migrations/20261111000000_jobs.sql` in the Supabase SQL editor (once).
2. `python backend/server.py` — collectors + API on `127.0.0.1:8000`.
3. `npm run build -w apps/worker`
4. `node --env-file=.env.local apps/worker/dist/index.js` — polls every 3 s, writes a heartbeat.

If the worker is offline, jobs stay `queued` and the UI says so. TikTok / FB Ads / TikTok Ads
also need a logged-in session: `python backend/pw_login.py <platform>`.

## Mock

`legacy/index.html` is static sample data and needs no backend. The live legacy page is
`legacy/live/index.html`; both load CSS from `legacy/assets/css/`.
