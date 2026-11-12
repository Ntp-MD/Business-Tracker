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
- [ ] Add `requirements.txt` with the Playwright version
- [ ] Add `.nvmrc` and `engines.node`
- [ ] State the supported Python version
- [ ] Verify clean install + tests + build

**Done when:** a fresh machine/CI installs the same versions.
**Decision needed:** supported Node/Python versions.

### 6. Lint and format
- [ ] Choose web tooling: ESLint + Prettier or Biome
- [ ] Add Ruff for Python
- [ ] Root scripts: `lint`, `format`, `format:check`, `test`
- [ ] Run lint in CI

**Done when:** lint passes and CI enforces it.
**Decision needed:** dependency approval for the chosen tools.

### 7. E2E smoke for 3 variants
- [ ] Playwright suite: mockup `/` and `/live` redirect
- [ ] Live `/` redirect, `/live` 200, settings redirect, `POST /live/items` 403
- [ ] Prod full UI, filters, archive/trash
- [ ] Read-only tests in CI; write tests use disposable data only

**Done when:** suite passes against the three deployed URLs.
**Decision needed:** test data strategy for prod writes.

### 8. Observability
- [ ] Structured server logs with request IDs
- [ ] Error tracking (Sentry or equivalent)
- [ ] Alert when worker heartbeat is stale or API errors spike

**Done when:** an alert fires on a real simulated failure.
**Decision needed:** provider/account.

---

## P2 — debt

### 9. Ops config cleanup
- [ ] `render.yaml`: remove the retired GitHub Pages `ALLOW_ORIGIN`
- [ ] `.env.example`: remove unused `NEXT_PUBLIC_SUPABASE_*`
- [ ] Document Vercel project/env settings
- [ ] Define backup/retention policy

**Done when:** configs match the active 3-variant setup.
**Decision needed:** backup retention.

### 10. Data correctness
- [ ] Replace `getSummary()` 3,000-row cap with count aggregates for totals
- [ ] Separate metrics: views/plays/points/signals
- [ ] Label sampled top-items/terms explicitly

**Done when:** totals and units are correct with more than 3,000 items.
**Decision needed:** none; follow `COLLECTOR-INTEGRATION-PLAN.md`.

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
