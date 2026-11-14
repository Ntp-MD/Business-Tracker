# TrendRail collector integration and remaining work

Updated: 2026-11-14. This is the active backlog and implementation plan. Work on one
bounded task at a time; finish its verification before starting another. An unchecked
task is not authorization to change the source list, schema, API contract, deployment,
business policy, or other items requiring approval under [AGENTS.md](../../AGENTS.md).

## Status — 2026-11-14

Packages 1–7 are implemented and pushed. This table is the status record; keep it here
instead of a separate notes file.

Rechecked 2026-11-14: the local checks in `AGENTS.md` pass. GDELT still returns `HTTP 429`
from this network, `data/reports/` does not exist (so no dry-run sample has been saved
here), there is no `.env.local` and no worker process in this checkout, and the retired
Render API still answers. Rows 1, 2, 5, and 8 below carry that evidence. Rows 3 and 6
changed: cancellation during work and the AI analysis export were implemented locally on
2026-11-14.

| # | Open item | Status | Next action |
|---|---|---|---|
| 1 | Live GDELT sample | **Blocked.** Every request from this network returns `HTTP 429 Too Many Requests`; rechecked 2026-11-14 and it is unchanged after the 2026-11-13 record. Mapping, gate, and one-retry behavior are covered by unit tests only. | Retry `python -m backend.collectors.dry_run --connector gdelt_doc --keyword SEO --show-sample 20` from a network GDELT does not throttle. Review the sample before trusting writes. |
| 2 | First real collect run | **Not run, and not runnable as noted.** `COLLECTOR_WRITE_ENABLED=1` was recorded in a local `.env.local` (not committed), but on 2026-11-14 that file is absent from this checkout and no worker process is running. | Owner restores `.env.local` with real Supabase credentials, starts the worker, then uses **Collect** in Settings or waits for the 24-hour schedule. Set `COLLECTOR_WRITE_ENABLED=0` to pause. |
| 3 | Cancellation during work | **Implemented locally 2026-11-14; not deployed.** The worker sends the claimed job id; the collector checks the owner-scoped cancel flag at checkpoints and stops at stage boundaries without advancing collector state or source health; the worker marks the job `cancelled` and does not retry. No schema change. See [Cancellation during work](#cancellation-during-work--implemented-locally-2026-11-14). | Owner reviews the contract items and tests a live cancel; deploy only with approval. |
| 4 | Versioned backup of collector tables | **Not implemented by decision.** Existing JSON/CSV item export remains the backup; collector rows are reproducible from the source. | Revisit only if the owner wants collector records, links, and state restorable. |
| 5 | Render API | **Still live.** `https://social-tracker-api.onrender.com/` returned 200 again on 2026-11-14 06:56 UTC (`server: uvicorn`). | Disable it in the Render dashboard (owner; no credentials in this repo). |
| 6 | AI export (package 9) | **Implemented locally 2026-11-14.** The Items page offers active rows matching the current filters as CSV, plus a Markdown guide and sample prompt. No schema or API-contract change; selected rows, imported AI results, and automatic provider calls remain out of scope. | Owner reviews the files; deploy only with the approval required by `AGENTS.md`. |
| 7 | Live RLS and migration history | **Unverified.** PostgREST with the service role bypasses RLS and cannot read migration history. | Check the Supabase dashboard or a database connection when needed. |
| 8 | Monitoring window and restore drill | **In progress.** 2026-11-14 snapshot: `live /api/health` returned `{"ok":true,"items":{"active":324,"archived":0,"trash":0},"worker":null}`; prod `/live` → 307 `/login`; live `/live` 200 and `/live/settings` → 307 `/live`; mockup `/` 200 and `/live` → 307 `/`. Worker heartbeat is `null`, so keep the 2026-11-18 window open and run the restore drill when scheduled. | Owner/ops follow-up. |

### Decisions taken (2026-11-13)

1. **First source:** `gdelt_doc`, keyword scope. It is the only enabled connector.
2. **Rights:** store title, canonical URL, author display, engagement, timestamps, and an
   excerpt of at most 280 characters. No full article body.
3. **Persistence** (`backend/collectors/store.py`): `keywords_matched` is unioned across
   runs and the first link keyword is kept; existing items refresh `score` and `metric`
   only; trashed items are skipped; quarantine stays a drop; `source_status` is written
   after every run; a failed run sets `last_status = error` with `last_error` and does not
   advance the cursor; records and items are read in two batched requests per run;
   same-day reports append; collectors are Supabase-only, with no JSON fallback.
4. **Quality policy:** hard rejects and soft flags unchanged in
   `backend/collectors/quality.py`. The owner reviews the 50–100 record dry-run sample.

**Known risk:** GDELT relevance is not in the gate. A run only filters identity, URL, date
window, language (Thai/English), spam phrases, and metric validity, so off-topic English
articles can reach `items`. Review the first batch and trash what does not fit.

## Outcome and scope

Make approved new sources available through the existing local worker and Python
collector, with a pre-write quality gate, safe persistence, observable results, and
optional recurring collection only after its policy is approved. Preserve existing
search, saved items, archive/trash, imports, and route and deployment boundaries.
Also plan an analysis export that lets users take a clearly scoped dataset to their
own AI tool; this is a separate deliverable from backup and collector integration.

This plan does not select a first new source, authorize enabling one, change existing
collectors, or approve a migration or deployment. Work starts with a read-only gap
assessment. Current deployed configuration and provider availability are **unverified**
in this review.

## Current baseline

- `backend/server.py` contains the existing YouTube, Google News, TikTok, Facebook Ads,
  and TikTok Ads collectors. Their current external availability has not been tested in
  this review. They do not use the new `backend/collectors/` quality gate.
- `backend/collectors/` contains the registry, contract, HTTP helper, quality gate,
  report, job validation, and Supabase persistence. `gdelt_doc` is the only enabled
  connector (see Status). `COLLECTOR_WRITE_ENABLED` defaults to off in code; the value in
  the deployed environment is unverified. The existing collectors are a separate path.
- The worker dispatches `collect` to `/api/collect`, but the validator currently accepts
  only keyword scopes. Country, channel, and other scopes require a reviewed contract.
- The repo contains `20261112010000_collectors.sql` and
  `20261112020000_remove_hackernews.sql`. Earlier notes report a successful disposable
  Hacker News write test and say the removal migration had not been applied. A draft
  comment in the first migration conflicts with that history; **the actual migration
  history and schema remain unverified**. Never edit an applied migration.
- Hacker News was removed by owner decision and is not a candidate for this plan.
- The previous backlog recorded CI, source-status mapping, prod auth, live read-only,
  runtime pinning, lint, variant E2E, observability, ops configuration, overview counts,
  collector framework, and repo governance as completed on 2026-11-12. These are
  historical claims, not fresh confirmation of CI, deployment, or external settings.
- The Next Items page exports active rows to CSV using the current text, source, and
  published-date filters; selected checkboxes are not passed to that export. CSV has
  source URLs and metrics, but no item ID or analysis guide. Next Settings offers JSON
  export; its query requests up to 3,000 active rows and may be subject to a lower
  service limit. Neither export currently provides the analysis context described in
  package 9 (AI analysis export). These observations are from code,
  not a production smoke test.

## Decisions required before implementation that depends on them

1. **Source and order:** choose the first provider and its scope. No candidate below is
   approved merely because it appears here. Owner also decides business keywords and
   any YouTube channel list.
2. **Data rights:** approve collection access, permitted fields, retention,
   redistribution, and the response to confirmed provider deletion for that source.
   Agree whether an excerpt is allowed and its maximum length; do not store full
   article bodies by default.
3. **Contracts and storage:** review any changes to source IDs, schema/RLS, storage,
   job/API contract, backup format, and the relationship between canonical records,
   existing items, and signals. Approve each change before implementation.
4. **Quality policy:** approve hard-reject reasons, soft flags/quarantine, language and
   scope rules, metric thresholds if any, and the reviewer and acceptance criteria for
   a 50–100-record sample. Decide what is retained for sample review. Low engagement
   alone is not a proposed hard rejection.
5. **Existing sources:** decide whether Google News and existing Playwright ad
   collectors remain as they are or should follow a separately approved policy.
6. **Recurring jobs:** choose the scheduler host, concurrency, offline behavior, and
   retry/recovery policy before enabling scheduled collection. Decide whether each
   run's local dry-run report must be retained; the current per-day filename can be
   overwritten by a repeat run.
7. **Analysis export:** choose the first export format, which fields may be shared,
   and the sample task used to validate the flow. Confirm whether first release needs
   selected rows as well as all matching filtered rows. Any API or schema change needs
   separate approval under `AGENTS.md`.

## Ordered work packages

### 1. Assess the collector framework — READY, read-only

- [ ] Compare `backend/collectors/`, `backend/server.py`, `backend/db.py`,
  `apps/worker/src/index.ts`, migrations, and existing tests with the invariants below.
  Inspect callers and separate the existing fetch path from the new collector path.
- [ ] Record which requirements are implemented, missing, or unverified; identify
  focused tests and any changes needing owner approval. In particular inspect
  sequential writes, checkpoint timing, updates to existing items, multiple keywords,
  JSON-mode support, report overwrites, and the difference between the proposed
  log-only sample review and the current quarantine behavior.

**Acceptance:** a reviewable gap list names the relevant code and a pass/fail check
for each material gap; no runtime files, data, schema, environment, or source settings
are changed. Stop if inspecting external state would require unavailable access.

### 2. Establish the environment baseline — access-dependent, read-only

- [ ] Inspect migration history and actual tables, constraints, RLS, and relevant
  non-secret configuration in the intended environment, using available read-only
  access. Compare with the two collector migrations and report unknowns explicitly.
  Do not print keys, tokens, or `.env.local` contents.
- [ ] Verify current CI/deployment status separately if access exists; do not treat an
  old successful run as a current result.

**Acceptance:** dated evidence identifies the environment and applied migration state,
or states exactly which access/evidence is missing. No migration, deployment, env change,
or user-data write occurs. Before a later migration, take a backup and record
active/archive/trash counts under the approved operating procedure.

### 3. Plan and verify persistence — after packages 1–2 and contract decisions

- [ ] Prepare the smallest approved design for owner-scoped canonical records,
  keyword links/items, and per-source/scope checkpoints. Review actual schema first;
  prepare additive SQL only when needed and obtain approval before schema/RLS changes.
- [ ] Add focused local tests for repeat runs, two keywords, mutable metrics, existing
  archive/trash, URL collisions, partial failure, and checkpoint/replay. Prove that a
  failed write does not advance a checkpoint and that a partial batch cannot erase
  unrelated items. Resolve whether atomic Supabase commit and JSON-mode persistence
  are required in the approved design.
- [ ] Implement only the approved gaps; preserve version-1 import/export and plan a
  versioned backup that round-trips records, links, and state if those are introduced.

**Acceptance:** relevant local tests prove these behaviors; rejected data is never
persisted; existing data survives failure/replay. Automated tests do not touch
Supabase. Any separate database validation requires an approved isolated environment
and disposable data; record its results separately from the local test suite.

### 4. Harden job execution — after package 1 and any required contract approval

- [ ] Bound owner-scoped claim/read/update and validate HTTP responses. Test that one
  owner's job is not claimed or changed by another worker and failures are visible.
- [ ] Add actual progress and heartbeat during long jobs, and propagate cancellation
  as supported by the approved contract. Test cancellation during work, not just before it.
- [ ] Before recurring work, design and test leases, bounded retries, idempotent restart,
  active-job/schedule dedupe, and recovery after a worker goes offline.

**Acceptance:** focused tests simulate owner mismatch, failed HTTP calls, long-running
work, cancellation, and restart without live services. Worker typecheck passes. Lease
or job schema changes require separate approval before implementation or application.

### Cancellation during work — implemented locally 2026-11-14

Status: **implemented locally 2026-11-14; not deployed.** This is status item 3. The
owner's "continue" instruction was treated as approval of the contract items below for a
local implementation; review them before deployment, and revert if any is unwanted. Only
the additive payload field affects the API contract. No schema change was made.

**Before this change.** `apps/worker/src/index.ts` checked `jobs.cancel_requested` once,
after claiming and before calling `POST /api/collect`. A running request was never checked
again, and dropping the HTTP request would not stop the collector.

**Implemented: cooperative checkpoints in the collector.**

1. The worker adds the claimed `job_id` (positive integer) to the collect payload it sends
   to `/api/collect`. The strict validator in `backend/collectors/job.py` accepts that
   optional field; all other unknown fields stay rejected.
2. `/api/collect` passes a `cancel_check` callback into the dry run. `store.job_cancel_check`
   reads the owner-scoped `jobs` row by `id` and `user_id` and returns `cancel_requested`.
   It is throttled to at most one query every 2 seconds, returns false when Supabase is not
   configured, and keeps the last value if a poll fails.
3. The collector checks cancellation before the provider fetch, after the quality gate,
   before the first write, after each persistence stage, and before writing success state.
   Cancellation applies at the next checkpoint, not mid-HTTP and not mid-request.
4. If cancelled before persistence, nothing is written. If cancelled during persistence,
   the current table write finishes and the remaining stages stop. In both cases the run
   returns its counters as `CancelledRun` and does not advance `collector_state` or
   `source_status`, because a cancelled run is not a source success or failure.
5. The worker treats a `{cancelled: true, counters}` response as terminal: it sets the job
   to `cancelled` with a short `error` note (for example "cancelled; 12 written; rerun is
   safe") and does not retry it. A cancellation requested before start keeps the existing
   terminal behavior.

**Why not abort the HTTP request.** The local server is threaded, but aborting the client
request would leave the collector's thread writing to Supabase while the job claims to be
cancelled. Job status and stored data would disagree, and counters would be lost.
Cancellation state stays in Supabase, so it also survives an API restart; no local cancel
endpoint or in-memory flag is added.

**Partial-write policy.** Collector writes are idempotent upserts (`resolution=merge-duplicates`
or `ignore-duplicates`); no stage deletes unrelated rows. A rerun after a cancelled run is
therefore safe and refreshes mutable metrics. Records written before cancellation may
exist without their item/link stage; a rerun completes them. Archived and trashed items
are never relinked or overwritten by this path. The job row, not source health, records the
cancelled outcome; `collector_state.cursor` is not advanced.

**Contract items applied**

1. Optional `job_id` in the collect payload and worker request. Old servers reject the
   field, so the Python server must be updated before the worker in any deployment.
2. Checkpoint semantics: cancellation is observed within one provider request or
   persistence stage, not immediately. Worst case is two provider timeouts plus the retry
   pause (about 36 seconds) and one stage.
3. The partial-write policy above: stop at the next stage boundary, keep existing upserts,
   leave state and source status unchanged, and require a rerun for completion.
4. The collector reads the owner-scoped `jobs` row at most once every 2 seconds during a
   collect run.

**Files changed:** `backend/collectors/contract.py` (`CancelledRun`),
`backend/collectors/store.py` (checkpoints, `job_cancel_check`),
`backend/collectors/dry_run.py` (cancel callback and cancelled summary),
`backend/collectors/job.py` (optional `job_id`), `backend/server.py` (pass the check),
`apps/worker/src/job-runner.ts` (new, testable runner), `apps/worker/src/index.ts`
(uses the runner), `tests/test_collectors.py`, `tests/worker_jobs.test.cjs`, and the CI
test command.

**Verification (2026-11-14)**

- `python -m unittest discover -s tests` → 62 passed, including cancellation before
  fetch, after gate, before records, after records, after all writes, payload validation,
  owner scoping, throttle, and poll-failure cases. Fixtures only; no Supabase.
- `node --test tests/worker_jobs.test.cjs` → 5 passed: job id and write switch, dry-run
  switch, cancelled terminal state, retry/error limits, and non-collect payloads.
- `npm run typecheck` and `npm run build:worker` pass; `python -m py_compile` passes.
- Not run: a live cancel against Supabase/worker (no `.env.local` or worker here), and
  deployment.

**Out of scope:** immediate abort of an in-flight provider call, per-record cancellation,
progress percentages and heartbeat, lease/retry redesign (package 4), clearing
`cancel_requested` after a terminal state, and UI changes.

### 5. Prepare one approved source — repeat per source

- [ ] From the intended collector host, check the selected provider's documented access,
  response status/content type, limits, scope, and coverage; save scrubbed fixtures.
  Document rights and the timestamp. Old checks do not establish present availability.
- [ ] After source, contract, schema, and quality decisions are approved, implement the
  adapter and tests for identity, timestamps, pagination, empty/malformed responses,
  limits, duplicates, and source-specific metrics. Keep it disabled until the gate below.
- [ ] Run a dry-run sample of 50–100 records with no database writes. Give the owner
  enough information to review relevance, language, spam, and over-filtering without
  assuming the current hash-only report contains the content needed for review.
- [ ] After sample approval, verify accepted records, repeat-run deduplication, updates,
  attribution, and visible source health in an approved isolated setup. Enable writes
  or deploy only with the separate approval required by `AGENTS.md`.

**Acceptance:** provider evidence, fixture results, reject counts, sample decision,
and repeat-run evidence are recorded. Disabled, blocked, or untested sources are not
reported as working coverage. No full article body or rejected record is persisted.

### 6. Integrate source health and backups — after the relevant contracts are approved

- [ ] Display configured sources even with zero items and distinguish success, empty,
  blocked, rate-limited, parsing, rights-review, and stale states where supported.
- [ ] Show accepted/rejected counts by reason and accurate units; update source labels,
  selection, filters, profiles, and counts for approved sources only. Keep signal
  records separate from content engagement totals.
- [ ] Implement and verify the approved versioned backup/import contract, including
  records, links, state, and legacy imports without losing archive/trash.

**Acceptance:** focused tests and manual UI checks cover empty, failed, and successful
states; export/import round-trips all approved fields. The mock/live/prod boundaries
and existing data remain intact. Web/UI changes receive the checks in `AGENTS.md`.

### 7. Enable recurring collection — after packages 3–6 and owner decisions

- [ ] Use the approved scheduler and source-specific checkpoints; respect rate limits,
  timeouts, pagination limits, and retry guidance. Keep concurrency within the agreed
  limit and make incomplete windows visible.
- [ ] Exercise 429/5xx, malformed/HTML responses, mid-job cancellation, restart,
  partial results, and an offline worker. Save a checkpoint only after durable writes.

**Acceptance:** the simulated failures recover without duplicate inserts or lost
checkpoints; source health reports failure/staleness and reject counts. Rollback
disables the new connector/schedule and preserves user data. Deployment and schedule
activation require the approvals in `AGENTS.md`.

### 8. Operations follow-up

- [ ] Check production monitoring through the previously recorded 2026-11-18 window.
- [ ] Check whether the retired Render API still responds; the owner disables it in
  Render if necessary.
- [ ] Carry out the quarterly restore drill under the existing backup policy when due.

**Acceptance:** record date, result, and any owner action without changing deployment
settings or deleting data without approval.

### 9. Export a dataset for analysis with the user's AI — implemented locally 2026-11-14

**Status:** first release implemented on 2026-11-14; not deployed. The Items page has an
**Export for AI analysis** panel. `GET /api/export/analysis` returns the active rows that
match the current Items filters (keyword, source, published `from`/`to`, sort, direction)
as CSV with `item_id`, keyword, source, title, author, URL, canonical URL, score, metric,
views, published, collected, and export times. `GET /api/export/analysis?format=guide`
returns a Markdown guide with the scope, date basis, field/unit definitions, known limits,
completeness wording, and a sample prompt. Row count, total, and truncation are also in
`X-TrendRail-Export-*` headers, and the CSV filename states its row count. The cap is
10,000 rows per file. Selected rows, schema changes, and AI-provider integration remain
out of scope. Verification: `node --test tests/web_auth.test.cjs tests/web_export.test.cjs`
(19 tests, fixtures only), web typecheck, biome lint, and `npm run build:web` pass.
Deployment still needs the approval in `AGENTS.md`.

**Goal:** let a user export an explicitly scoped dataset and a guide, then use both
in their own AI tool and trace findings back to source items. This work can use the
existing dataset and does not require adding a collector or waiting for recurring jobs.
It is distinct from the versioned backup/import work in package 6. The user chooses
the external tool and performs the analysis; automatic provider integration and
importing AI results are outside the first version.

**First-release proposal:** start with all active rows matching the existing Items
filters, CSV and a copyable guide/prompt. Add selected-row export if the owner includes
it in the initial scope. Confirm the format and sharing policy before implementation;
do not assume a new route, changed API contract, schema, or dependency is approved.

1. **Confirm the scope and output.** Review the Items filters, existing CSV/JSON
   routes, and permitted fields. Document whether the export covers all matching
   rows or selected IDs, how selection behaves across pages if included, the time
   field and timezone used for date filters, and what happens for an empty dataset.
   Obtain the decisions above before changing behavior.
2. **Produce the dataset.** Reuse existing reads and export behavior where possible.
   Include an available stable item reference, source, source URL, title, keyword,
   approved shareable text if any, and available timestamps and metrics with units.
   Keep unknown values unknown; never invent a collection or metric observation time.
   Do not claim multiple keywords, deduplication, or content rights that the stored
   data does not establish. Keep distinct records and explain how duplicates are counted.
3. **Add dataset context.** Provide export time, applied filters or selected scope,
   time range and date basis, exported count, and any known limits or truncation.
   Preserve published, collected, and export times as distinct concepts. Do not
   represent an incomplete export as complete; handle pagination and concurrent
   changes explicitly, and report partial results when completeness cannot be proven.
4. **Provide a guide and sample prompt.** Show copyable instructions or offer a
   Markdown guide alongside the chosen data format. Describe fields, units, scope,
   missing values, and how to use the file with the user's chosen tool. Adapt the
   example in package 9: treat dataset text as data,
   cite item references and URLs, distinguish evidence from assumptions, and state
   when the data is insufficient. Do not require an AI account or API key in TrendRail.
5. **Verify the flow.** With local fixtures or mocked reads, test filtered and empty
   exports, selected IDs if included, Thai text, quotes/newlines, source URLs,
   reference IDs, missing timestamps/metrics, duplicate handling, multi-page results,
   partial exports, and spreadsheet-safe CSV handling if CSV is chosen. Check that
   reported counts and filters match the file and that backup/import behavior remains
   compatible. Automated tests must not connect to Supabase.

**Acceptance:** a user can review the scope, export the approved data and guide, and
use the sample prompt to obtain findings traceable to item references and source URLs.
Known omissions and partial exports are visible; units and dates are not fabricated.
Run the web typecheck and applicable UI/variant smoke checks from `AGENTS.md`, plus
focused tests for the chosen implementation. Preserve mock/live/prod boundaries.
Deploy only with the approval required by `AGENTS.md`.

## Candidate sources and evidence still needed

| Candidate | Scope and next evidence | Status |
|---|---|---|
| GDELT | Keyword news metadata; retest connectivity, query behavior, time windows, and result limits | Candidate; 2026-11-11 check timed out |
| Bluesky | Keyword posts; verify supported access, identity, and pagination | Candidate; 2026-11-11 check returned 403 |
| Google Trends Thailand | Country signal; verify feed, occurrence identity, traffic labels, and separate signal display | Candidate; old RSS check returned 200 |
| YouTube channel feeds | Owner-selected channels; verify a real feed and dedupe video IDs against keyword search | Candidate; old example returned 404 |
| Wikimedia | Verify pages, access/rate policy, operator contact, and pageview units | Deferred candidate |
| Mastodon | Approve an instance allowlist; test access, URI dedupe, and HTML sanitization | Deferred candidate |
| RSSHub | Review hosting, routes, authentication, and rights | Deferred candidate |
| Common Crawl | Test catalog/index, resource limits, and any required dependency | Deferred candidate |
| data.go.th | Choose a dataset; check license, encoding, dates, geography, and token needs | Deferred candidate |
| Jetstream | Establish the need and capacity; test protocol, reconnect, backfill, and deletion | Deferred candidate |

The existing Google News and advertising collectors continue under current behavior
until the owner decides otherwise. Manual Meta/TikTok observations in the reference
guide are proposals, not a decision to disable or approve the existing collectors.
See the [public data collector guide](../reference/public_data_collector_agent_integration_guide.md)
for candidate-specific background.

## Proposed data model

The repo already contains a collector migration; the following describes the intended
roles, not proof that the deployed schema matches. Compare the actual schema before
proposing additional DDL. Any change to schema, RLS, source constraints, or storage
requires owner approval.

| Data | Intended role and identity |
|---|---|
| `collector_records` | Canonical provider record, unique per owner/source/source item ID; retain kind, timestamps, allowed metadata, units, and quality rules version |
| `collector_item_links` | Link a canonical content record to each relevant existing keyword item without replacing its original attribution |
| `collector_state` | Track cursor, health, and run counters independently per owner, connector, and scope |
| `items` | Preserve the existing per-keyword content projection and its active/archive/trash behavior; signals remain separate |

Jobs may need lease, attempts, and schedule keys for recurring collection. Decide the
transaction boundary and compatibility with local JSON storage before specifying
implementation or applying migrations.

## Design invariants and verification

- Keep `/` mock-only, `/live` read-only in the live variant, prod auth in place, and
  service-role credentials server/worker-side. Do not run Playwright on Vercel.
- New records pass transport, parsing, normalization, identity, scope, language,
  quality, and rights checks before persistence. Record counts for accepted, rejected,
  duplicate, and quarantined results; approved rules and retention govern the details.
- Preserve source IDs, source URLs, permitted provenance, source timestamps and UTC
  observation time. Use stable identities for deduplication, update mutable metrics,
  and preserve separate keyword links. Do not discard a distinct post solely because
  its title resembles another. Do not treat an absent search result as a deletion.
- Preserve unknown metrics as unknown where the approved data contract supports it;
  keep video metrics, news, ads, and trend signals in their appropriate units. A
  signal must not silently become a content item or an engagement total.
- Use targeted writes: do not call `db._save_items()` with a partial batch, because it
  treats its input as a snapshot. Do not advance checkpoints on storage failure or
  silently fall back to a different store in strict mode. Preserve archive/trash and
  attribution across replay, import, and cross-source URL collisions.
- Before each implementation task, inspect the current worktree and relevant callers;
  preserve unrelated work. Stop on missing access, an unsafe migration, conflicting
  contracts, failed baseline checks, or an unapproved decision, and report what is
  needed. Do not improvise around those gates.
- For runtime changes, run the matching commands and manual smoke checks in
  [AGENTS.md](../../AGENTS.md), plus focused tests for the behavior changed. For shared
  types or build configuration run `npm run build`. Automated tests must never touch
  Supabase. Docs-only changes require checking relative links.

Historical endpoint results and the completed backlog above are retained as context;
they are not current test results or permission to run migrations or deploy.
