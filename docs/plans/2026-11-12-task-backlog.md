# Task backlog — 2026-11-12

Status: active. Work one item at a time; do not start the next item until the current one is
verified.

**Definition of done for every item:** code + focused test + CI green + deploy when runtime
changes + docs updated. Never claim done with a failing check.

## Order

`P0` first: CI → source-status → prod auth → live read-only. Then `P1`, then `P2`.

---

## P0 — start here

### 1. CI pipeline
- [x] Add `.github/workflows/ci.yml`
- [x] Run: `python -m unittest discover -s tests`
- [x] Run: `python -m py_compile backend/server.py backend/db.py backend/pw_login.py`
- [x] Run: `npx tsc --noEmit -p apps/web/tsconfig.json`
- [x] Run: `npm run typecheck` and `npm run build`
- [x] Cache npm; no secrets in CI

**Done when:** push/PR is green and a failing check blocks merge.
**Decision needed:** none.
**Done:** 2026-11-12

### 2. Fix source-status mapping
- [x] `apps/web/lib/data/items-query.ts` selects `message,updated_at`; schema has `error,checked_at`
- [x] Map `checked_at → at`, `error → message`; surface read errors instead of returning `{}`
- [x] Test against the deployed schema

**Done when:** Sources page shows last run/ok/error instead of "No run recorded".
**Decision needed:** none.
**Done:** 2026-11-12

### 3. Auth for prod
- [x] Choose Supabase Auth magic link
- [x] Update owner email to 
tpsrm.md@gmail.com
- [x] Add login/callback/logout, password fallback and prod auth guard
- [x] Set Supabase Site URL + redirect URLs
- [x] Set Vercel public env and deploy
- [x] Verify unauthenticated prod access is blocked; password login + logout work
- [ ] Verify magic-link delivery/login (blocked by Supabase email rate limit)

**Done when:** magic-link login works on production and unauth writes are blocked.
**Blocked by:** Supabase default email quota; configure custom SMTP for reliable magic links.
Password fallback is available at /login.

### 4. Live read-only hardening
- [x] Choose anon key + public read views (single Supabase project)
- [x] Add live_items / live_source_status migration and read switch
- [x] Apply migration in Supabase SQL editor
- [x] Set LIVE_READ_ANON=1, remove service-role env, redeploy live
- [x] Prove anon insert is denied (401 RLS)

**Done when:** live reads through the anon key and a direct write is rejected by the DB.
**Done:** 2026-11-12. Live uses live_items/live_source_status; anon insert returns 401.

---

## P1 — after P0

### 5. Pin runtime and Python dependencies
- [x] Add `requirements.txt` with the Playwright version
- [x] Add `.nvmrc` and `engines.node`
- [x] State the supported Python version
- [x] Verify clean install + tests + build

**Done when:** a fresh machine/CI installs the same versions.
**Done:** 2026-11-12. Node 22.x, Python 3.12, Playwright 1.64.1; fresh-venv tests and
`npm ci` + typecheck + build pass.

### 6. Lint and format
- [x] Choose web tooling: Biome (lint + format) and Ruff for Python
- [x] Add Ruff for Python
- [x] Root scripts: `lint`, `format`, `format:check`, `test`
- [x] Run lint in CI

**Done when:** lint passes and CI enforces it.
**Done:** 2026-11-12. `biome.json`, `pyproject.toml`, `@biomejs/biome` + `ruff==0.17.4`
(`requirements-dev.txt`); one-time format applied; lint + format check pass.

### 7. E2E smoke for 3 variants
- [x] Playwright suite: mockup `/` and `/live` redirect
- [x] Live `/` redirect, `/live` 200, settings redirect, `POST /live/items` 403
- [x] Prod full UI, filters, archive/trash
- [x] Read-only tests in CI; write tests use disposable data only

**Done when:** suite passes against the three deployed URLs.
**Done:** 2026-11-12. `e2e/test_variants.py` (Python Playwright, reuses `requirements.txt`);
read-only tests run in CI. Prod lifecycle runs only with `E2E_PROD_EMAIL` /
`E2E_PROD_PASSWORD`, creates one `__e2e__` item, archives/trashes/purges it, and cleans up
on failure.

### 8. Observability
- [x] Structured server logs with request IDs
- [x] Error tracking through the health workflow + GitHub issues (no Sentry account)
- [x] Alert when worker heartbeat is stale or the API health check fails

**Done when:** an alert fires on a real simulated failure.
**Done:** 2026-11-12. `/api/health` reports worker heartbeat; proxy/Python logs are JSON with
`request_id`; `.github/workflows/health.yml` runs every 30 min and opens/closes a
`Health check failing` issue. Simulated failure opened issue #1; recovery run closed it.
**Provider:** GitHub-native (no external account). Per-error spikes would need Sentry.

---

## P2 — debt

### 9. Ops config cleanup
- [x] `render.yaml`: remove the retired GitHub Pages `ALLOW_ORIGIN`
- [x] `.env.example`: drop the unused `WORKER_SUPABASE_SERVICE_ROLE_KEY`; keep
      `NEXT_PUBLIC_SUPABASE_*` (prod auth + live reads need them)
- [x] Document Vercel project/env settings
- [x] Define backup/retention policy

**Done when:** configs match the active 3-variant setup.
**Done:** 2026-11-12. `docs/DEPLOY.md` has the project/env table and backups/retention;
trash 7 days, items indefinite, Supabase plan backups + manual export before schema changes.
**Decision:** backup retention follows the Supabase plan; restore drill quarterly.

### 10. Data correctness
- [x] Replace `getSummary()` 3,000-row cap with count aggregates for totals
- [x] Separate metrics: views/plays/points/signals
- [x] Label sampled top-items/terms explicitly

**Done when:** totals and units are correct with more than 3,000 items.
**Done:** 2026-11-12. Overview totals use an exact count and paged score aggregation; only
top terms / charts use a labeled 3,000-item sample. Units are shown as signal points plus
views / plays / likes. Verified with 3,500 disposable rows (`__e2e_count__`, deleted after).
**Note:** aggregation pages through rows because PostgREST aggregates are disabled; a DB
summary view would be needed for very large datasets.

### 11. Collector ingestion quality gate
- [ ] Follow `docs/plans/COLLECTOR-INTEGRATION-PLAN.md`
- [ ] Do not start until schema, source list, retention and quality policy are approved
- [ ] First release: HN only, dry-run sample, no rejected records in Postgres

**Done when:** the plan's Phase 0 gate is approved and Phase 1a passes.
**Decision needed:** owner approvals listed in that plan.

### 12. Repo governance
- [ ] Decide LICENSE (private or public)
- [ ] Add `SECURITY.md` and `CONTRIBUTING.md` if the repo is shared

**Done when:** the repository has an explicit usage/security policy.
**Decision needed:** license choice.

---

## Decisions needed

1. Prod auth: Supabase Auth magic link or owner password?
2. Live isolation: DB-level read-only or app guard + rate limit?
3. Node/Python versions to pin.
4. Lint tooling: ESLint/Prettier or Biome.
5. Observability provider.
6. License/private policy.
