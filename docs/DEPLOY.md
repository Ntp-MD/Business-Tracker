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
- **live** has `APP_VARIANT=live`, `LIVE_READ_ANON=1`, `NEXT_PUBLIC_SUPABASE_URL`, and
  `NEXT_PUBLIC_SUPABASE_ANON_KEY`. It has no service role key; reads go through the public
  `live_items` / `live_source_status` views, so DB writes are denied even if the proxy is bypassed.

### Project env

| Project | `APP_VARIANT` | Supabase env |
|---|---|---|
| `trendrail-mockup` | `mockup` | none |
| `trendrail` | `prod` (Production), `live` (Preview) | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_USER_ID`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_SITE_URL` |
| `trendrail-live` | `live` | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `LIVE_READ_ANON=1` |

Vercel cannot run Playwright or the Python collectors; Search Now uses the local worker (prod only).
- Legacy redirects: `/dashboard-live.html`, `/dashboard.html`, `/app/dashboard.html` → 307 `/live`.
- GitHub Pages is disabled. The old static app stays under `legacy/` for the Python server.

Deploy from the repo root (project root is `apps/web`):

```bash
vercel deploy --project trendrail-mockup --prod
vercel deploy --project trendrail --prod
vercel deploy --project trendrail-live --prod
```

## Live read-only views

The `live` deployment does not use the service role key.

1. Apply `supabase/migrations/20261112000000_live_read_views.sql` in the Supabase SQL editor.
2. On the `trendrail-live` Vercel project set:
   - `APP_VARIANT=live`
   - `LIVE_READ_ANON=1`
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - Remove `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `SUPABASE_USER_ID`
3. Redeploy `trendrail-live`.

`live_items` exposes active + archived content without `user_id` or trash; `live_source_status`
exposes source health. Both are select-only for `anon`, so a code bypass still cannot write.

## Prod auth

Only the `prod` variant requires login. `mockup` and `live` stay public; `live` remains read-only.

- Provider: Supabase Auth magic link (PKCE, `@supabase/ssr`), with a password fallback for
  email-quota outages. For production reliability, configure custom SMTP in Supabase.
- Owner: `ntpsrm.md@gmail.com`.
- Routes: `/login` (send link), `/auth/callback` (exchange code), `/auth/logout`.
- Guard: `apps/web/proxy.ts` redirects unauthenticated `/live` + `/api` to `/login`;
  non-GET returns 401. `/api/health` stays public.
- Prod env: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` (publishable),
  `NEXT_PUBLIC_SITE_URL=https://trendrail.vercel.app`.
- Supabase Dashboard → Authentication → URL Configuration:
  - Site URL `https://trendrail.vercel.app`
  - Redirect URLs `https://trendrail.vercel.app/auth/callback` and
    `http://localhost:3000/auth/callback`

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

## Collector persistence

The collector framework and schema are installed, but **no adapter is enabled**: Hacker News
was removed on 2026-11-12. Apply `20261112020000_remove_hackernews.sql` after the code removal
to narrow the source/metric checks. `COLLECTOR_WRITE_ENABLED` stays 0; set it to 1 only for a
future approved adapter. Records, keyword items, links and state upsert by stable keys;
rejected records are never stored. See `backend/collectors/`.

## Backups and retention

- Supabase is the source of truth. Check Dashboard → Database → Backups for the plan's
  retention window, and take a manual export before schema changes.
- Exports: `GET /api/export` on the Python API, or All Items → Export CSV in prod.
- Active and archived items are kept until deleted. Trash auto-purges after 7 days
  (`TRASH_RETENTION_DAYS`); "Delete forever" is immediate and unrecoverable.
- `jobs` rows stay for audit until manually cleaned; `source_status` keeps one row per source.
- Restore drill quarterly: restore a backup into a scratch project, then run
  `scripts/check_health.py` and the read-only E2E tests against it.

## Mock

`legacy/index.html` is static sample data and needs no backend. The live legacy page is
`legacy/live/index.html`; both load CSS from `legacy/assets/css/`.
