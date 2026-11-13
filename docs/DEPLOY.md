# Deploy (Vercel + local worker)

## Vercel environments

| Variant | Vercel project | URL | Data | Writes |
|---|---|---|---|---|
| `mockup` | `trendrail-mockup` | `https://trendrail-mockup.vercel.app` | Fixtures only, no Supabase env | No |
| `prod` | `trendrail` | `https://trendrail.vercel.app` | Supabase (shared) | Yes |
| `live` | `trendrail-live` | `https://trendrail-live.vercel.app` | Same Supabase, read-only UI/API | No |

All three projects use root directory `apps/web`, framework Next.js, and deployment protection off.

### Environment separation for demos

| Environment | Use it for | Data source | Auth | Writes |
|---|---|---|---|---|
| `mockup` | presentations, screenshots, UX review | static fixtures in `apps/web/lib/mock/` | none | none |
| `prod` | owner operations | Supabase service role | Supabase Auth | yes |
| `live` | public read-only sharing | Supabase anon key + `live_items` views | none | none |

- Demo on `https://trendrail-mockup.vercel.app` only. Never seed demo rows into prod or live.
- The mockup project must have no Supabase env and no service key. `/live` and `/api` redirect to `/`.
- Prod and live are separate Vercel projects; live cannot write even if the UI is bypassed.
- Keep the environment label visible: mockup shows `MOCKUP`, prod root is a mock preview and
  labels the real app at `/live`, live is read-only.

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

Production access is limited to the authenticated Supabase user whose UUID matches
`SUPABASE_USER_ID`; a missing ID fails closed. Google sign-in uses the same owner account
and `/auth/callback` as magic-link sign-in. A different Google identity must be linked
to the existing owner user before it can access the console; do not change the owner ID
or link identities without verifying the account. Magic link and password remain available.

### Invite-only team access (off by default)

The owner is always allowed. To let invited people in:

1. Supabase → Authentication → Settings: disable **Allow new users to sign up**.
2. Supabase → Authentication → Users → **Invite user** with the person’s email.
3. Set these server-only variables on the Vercel `trendrail` project:
   - `ALLOW_INVITED_USERS=1`
   - `INVITED_EMAILS=person1@example.com,person2@example.com`
4. Redeploy. Google, magic link and password all use the same allowlist.

Guests must sign in with the exact invited email; an unlisted Google/email account is
signed out and cannot access `/live` or `/api`. Invited users share the owner’s data and
currently have write access, so invite trusted people only. Turn the feature off by
removing both variables (or setting `ALLOW_INVITED_USERS=0`) and redeploying. Never use
`NEXT_PUBLIC_` for these values.

For Google sign-in, configure a web OAuth client with the production origin and the
Supabase Google-provider callback, then store its client ID and secret in Supabase Auth's
Google provider settings. Add the web app's `/auth/callback` to Supabase's allowed
redirect URLs. Keep the client secret out of source control and chat. Deploy and verify
the owner-only guard before enabling the provider; deployment and provider changes
require the approvals in `AGENTS.md`. Test owner and non-owner accounts, magic-link and
password fallback, logout, and the mockup/live variant boundaries. The Google sign-in
button asset is from Google's official [branding package](https://developers.google.com/identity/branding-guidelines).

### Demo link

The prod login shows a “ดูเดโม (mockup)” button. It links to `NEXT_PUBLIC_MOCKUP_URL`
(default `https://trendrail-mockup.vercel.app`) and opens the static mockup — no auth,
no Supabase, and no production data. There is no auth bypass.

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
