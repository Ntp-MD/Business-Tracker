# Target architecture and structure

Status: **proposal, 2026-11-14**. It describes where the project should go for
normalization, practice, performance, and serving. It does not authorize a framework,
schema, API, dependency, or deployment change; follow [AGENTS.md](../AGENTS.md).

Progress 2026-11-14: `collectors/adapters/` exists with GDELT + GNews on one contract
(live GNews collect verified), `COLLECT_CONNECTORS` replaces the hard-coded connector in
the UI and worker, the Items list uses an explicit column projection, and `/api/health`
has a short CDN cache. **Phase 1 is done:** `server.py` went 2,682 → 94 lines with the
handler in `backend/api/`, services in `backend/services/`, and process state in
`backend/runtime.py`, behavior unchanged (79 Python tests and a live endpoint smoke).
Still open: the Python worker and the `record_id` / `keyword_key` migration.

## 1. Principles

1. **One writer per table.** Every table has exactly one code path that mutates it.
   Legacy fetch, collector jobs, imports, and UI actions must not write the same rows
   through different logic.
2. **Normalize at ingestion, denormalize at serving.** Keep canonical provider records;
   project them into the row shape the UI reads. Do not make every page join five tables.
3. **One contract per boundary.** Provider -> adapter -> gate -> store; HTTP -> service;
   DB -> repository. A layer never reaches across two boundaries.
4. **Idempotent, observable jobs.** A rerun is safe, failures carry a reason, and health
   is measured, not assumed.
5. **Keep the proven runtime.** Python stdlib, Next.js App Router, Supabase, and the
   three Vercel variants stay. No new framework, queue, or microservice without approval.
6. **Browser work stays local.** Playwright never runs on Vercel.

## 2. Target topology

```
Vercel `mockup`   /                    fixtures only, no Supabase/worker/network
Vercel `live`     /live, /live/*       anon key + live_* views, GET only, cached 30–60 s
Vercel `prod`     /live, /live/*, /api/*  server-side auth, service role (server only), writes
Supabase          Postgres + RLS + Storage; daily/automatic backup target
Owner PC          collector worker (Python); claims Supabase jobs; calls GDELT/Playwright
Retired           Render `social-tracker-api`; legacy static UI after parity
```

Prod and live stay separate deployments on the same schema. `mockup` never receives a
service key. Deployed Python HTTP is not needed once the legacy static UI retires: the
Next app reads Supabase directly and the worker runs on the owner's PC.

## 3. Repository structure

The first extraction is done (2026-11-14): `backend/server.py` is a 94-line entrypoint,
`backend/api/` holds the HTTP handler and static/JSON helpers, `backend/services/` holds
item, archive, profile, and status use-cases plus the legacy collectors, and
`backend/runtime.py` owns paths, env, locks, progress, and cancel state. `backend/db.py`
still mixes transport and row mapping; a Node worker still calls the local HTTP API.
Target: same repo, split by responsibility, no new services.

```
apps/web/                     Next.js shell; variants by APP_VARIANT
backend/
  server.py                   entrypoint: `python backend/server.py` + test re-exports
  runtime.py                  process state: paths, env, locks, progress, cancel, file helpers
  api/
    server.py                 HTTP handler (do_GET/do_POST/...) + listen loop
    http.py                   JSON/static/CORS response helpers
    routes/                   (later) one handler module per area if server.py grows again
  services/                   use-cases shared by HTTP and the worker (no HTTP imports)
    items.py                  items, archive/trash, import/export, analyze, refresh
    profiles.py               profile validation + keyword/source fan-out
    status.py                 source log, status payload, keyword list
    sources.py                legacy source collectors (ported one by one)
    window.py                 fetch-window timestamp helpers
  collectors/
    registry.py contract.py quality.py http.py
    adapters/                 gdelt.py, gnews.py, ... one module per source
    store.py                  only module that writes collector tables
    worker.py                 (later) claim loop, cancellation, rate limiting, scheduling
  db/
    client.py                 PostgREST transport (requests, retries, errors)
    repositories.py           row mapping per table; no business rules
supabase/migrations/          append-only, tracked history
tests/                        Python unit tests + Node fixture/contract tests
docs/                         reference, plans, notes
```

Dependency rule: `api -> services -> collectors/db`; `collectors -> adapters`;
`worker -> collectors + db`. Services never import `api/`, and collectors never import
services.

## 4. Data model

**Ingestion (normalized):**

| Table | Role |
|---|---|
| `collector_records` | Canonical provider record; unique `(user_id, source, source_item_id)` |
| `collector_item_links` | Which record produced which keyword item; unique `(record_id, item_id)` |
| `collector_state` | Cursor, health, counters per owner/connector/scope |
| `source_status` | Last run per source (owner and live view) |

**Serving (denormalized projection):** `items` stays the UI row: one row per
`(user_id, keyword, canonical_url)` with edit/archive/trash state, unique already enforced.
It is a projection, not a second source of truth. Add, in one append-only migration:

- `items.record_id uuid null references collector_records(id)` + index, so every projected
  row carries lineage and reconciliation is a join, not a guess.
- `items.keyword_key text` = NFC, trim, collapse spaces, lowercase; unique
  `(user_id, keyword_key, canonical_url)`; keep `keyword` for display. Today `SEO` and
  `seo` would become two rows.
- `items (user_id, keyword, published desc) where deleted_at is null` for date sorting.

**One writer:** collector jobs write `collector_records` and `collector_item_links`, then
the projection function writes `items`. The legacy fetch path and `importItems` retire or
call the same projection code. A view `collector_items_unlinked` (records with no keyword
item) is the audit surface.

**Canonical formats:** UTC ISO-8601 timestamps, language codes (`en`, `th`, ...), canonical
URLs through one function, keyword normalization through one function. No full article
bodies.

**Source registry as data:** one `contracts/sources.json` (id, label, icon key, accepted
languages, rights, rate limit, enabled) read by Python and checked against
`apps/web/lib/types.ts` source list and the DB `source` checks in a contract test. Today
the list is duplicated in Python, TypeScript, SQL, and source health code.

**Optional later:** `record_metrics(record_id, observed_at, signal, unit)` if movement over
time is needed; the current design overwrites mutable metrics and keeps no history.

## 5. Performance budget

- **Queries:** never `select("*")` for list pages; select the columns the card renders.
  Stop asking for `count: "exact"` on every list request; keep counts where the UI needs
  them, otherwise use `planned`/head-count on demand. Fetch item detail rows separately.
- **Indexes:** current partial indexes are good. Add the two from section 4 and verify the
  live list, keyword filter, date sort, and export with `EXPLAIN`.
- **Caching:** `live` is public read-only, so serve it with `revalidate = 30–60` (or a tag
  cache invalidated by writes) instead of `force-dynamic` on every request; keep `prod`
  dynamic. Cache `/api/health` for 30 s.
- **Worker:** a token bucket per connector (GDELT: start at one request per ~60 s and back
  off on 429) instead of burst retries; batch upserts in one request per table; one job at
  a time.
- **Exports:** keep the 10,000-row cap and select only exported columns; stream if the cap
  grows.
- **Egress:** live reads go through `live_*` views with anon key; prod reads use service
  role server-side. No query should pull bodies it does not render.

## 6. Serving, operations, and security

- Keep the three Vercel projects; do not merge them. `prod` is the only writer, `live` is
  anon + views + GET only, `mockup` is fixtures with no secrets.
- Suspend the old Render API; it runs the legacy image with a service key and is not needed.
- Run the worker as an OS service or scheduled task with restart, single instance. The job
  lease already prevents double execution.
- Monitoring: the GitHub schedule is best-effort (observed ~7 h gaps, not 30 min). Either
  accept that, add an external uptime check, or relax `check_health.py` so a stopped
  local worker is a warning, not a failure that opens issues.
- Backups: schedule a `pg_dump` (weekly) to private storage and run a restore drill. This
  is the only blocking gap for the security/health checklist.
- Add the build SHA and deployed variant to `/api/health` so a check can tell which commit
  is serving.
- Keep RLS: authenticated owner policies; service role server-side only; anon sees only
  `live_*` views. Re-verify after every migration.

## 7. Tests and contracts

- Python: adapter, gate, store, and job tests use fixtures; never network or Supabase.
- Node: auth/variant, export, source health, worker fixture tests.
- Add contract tests: source registry parity (Python ↔ TypeScript ↔ SQL), keyword
  normalization, and a schema-drift check that selects the exact columns each repository
  writes against a test project (or validates against `information_schema`).
- Migrations stay append-only; adopt tracked history (`supabase_migrations`) so the
  deployed schema is verifiable instead of "applied manually".

## 8. Migration roadmap

| Phase | Work | Acceptance |
|---|---|---|
| 0 | Freeze legacy features; keep the current green suite | No new code in `server.py` legacy paths |
| 1 | Extract `server.py` into `api/` + `services/` with no behavior change — **done 2026-11-14** | Same routes, same responses, tests green |
| 2 | Port gnews to the collector framework, then tiktok/fbads/ttads; move the worker to Python (`collectors/worker.py`) and delete the Node HTTP hop | Legacy sources produce through one contract; one worker |
| 3 | Data normalization: `record_id`, `keyword_key`, single projection writer, backfill legacy items | One writer per table; reconciliation view empty for new runs |
| 4 | Serving performance: projections, caching, monitoring policy, backup/restore | Live p75 under the agreed budget; backups restore |
| 5 | Retire Render and the legacy static UI | No traffic to retired surfaces |

Phase 1 and 2 are the highest value per risk; phase 3 changes data, so it needs a
migration review and a backup first.

## 9. Anti-goals

- No microservices, message broker, or separate collector service.
- No framework or dependency change for its own sake.
- No full article bodies, no cross-user reads, no service key outside server/worker.
- No merging the three variants, and no Playwright on Vercel.
- No schema edits to applied migrations; only new files.

## 10. Open decisions

1. Archive/trash ownership: keep it on the `items` projection (current) or move it to the
   keyword link. Keeping it on `items` is simpler and the recommendation.
2. Keyword matching: casefold for uniqueness while preserving display text.
3. Worker host: always-on PC service vs. scheduled manual runs.
4. Monitoring: warn vs. fail on a stopped worker, and whether to add an external checker.
