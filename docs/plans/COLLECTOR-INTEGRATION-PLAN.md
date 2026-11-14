# TrendRail collector integration and remaining work

Updated: 2026-11-14. This is the single list of open collector work. Completed work is
summarized once under [Completed](#completed-context). Nothing here authorizes a source,
schema, API, deployment, or business-policy change; follow [AGENTS.md](../../AGENTS.md)
and its approval list. Status history lives here instead of a separate notes file.

## Remaining work

### A. Finish the GDELT pathway

1. **GDELT live sample — reachable but throttled; sample too small and noisy.**
   Access changed on 2026-11-14: the endpoint now answers `200` intermittently from this
   network instead of always failing. Evidence from that day:
   - `SEO`, `timespan=1d`, `maxrecords=100`: `200` with **2** articles; both passed the
     gate (`accepted: 2`) and the report was appended to
     `data/reports/collector-gdelt_doc-2026-11-14.jsonl`. One is a Serbian story
     (`blic.rs`, provider language `Serbian`) that the title-script heuristic labels
     `en`; the other is an English marketing-agency post (`pctechmag.com`, Uganda).
   - `SEO`, `timespan=3d`, `maxrecords=250`: `200` with **22** articles. Only about four
     are topical (two syndications of "From Years Without SEO Enquiries…", one
     DesignRush placement, one mobile-app-development post); the rest are Korean,
     Japanese, Serbian, Bulgarian, and French stories, so the bare `SEO` token also
     matches unrelated pages.
   - Bursts return `429 Too Many Requests` with a plain-text body. Requests 10–90 s
     apart failed; one after about three minutes succeeded, and a later one after four
     minutes still failed. The single 6-second retry in `gdelt.py` did not clear the
     throttle in any run.
   Blocker: a one-day window yields about two records per keyword, far below the 50–100
   record review this plan requires, and the relevant share is low. Owner decisions
   needed: keep manual cleanup for noisy writes, widen the window, and/or filter on
   relevance and the provider's `language` field (a quality-gate change).
   Next: agree those rules, then capture and review a 50–100 record sample across the
   owner's keywords before trusting writes.

2. **First real collect run — not started; writes stay off.**
   `.env.local` is present with `COLLECTOR_WRITE_ENABLED=0`. On 2026-11-14 the full
   worker → API → collector path was exercised with a local slow fixture and writes
   disabled: a cancel job stopped at 2/4 with "0 written", and a normal job finished 4/4.
   The test jobs were deleted. Rechecked 2026-11-14: `collector_state` has no rows, no
   collect job is queued, and `items` still holds 324 active rows, so no collector write
   has ever run here. `/api/health` reported `worker: null`, so the local API and worker
   also need starting.
   Remaining: resolve item 1's quality rules, set `COLLECTOR_WRITE_ENABLED=1`, queue a
   real GDELT **Collect**, review the first batch, then set it back to `0` to pause.
   Known risk: GDELT relevance is not in the gate, so off-topic articles can reach
   `items`; the 22-record sample above shows that this is likely without a filter.

### B. Finish and deploy the two local features

3. **Cancellation — implemented, deployed, and exercised end-to-end with a local fixture.**
   Settings lists the latest collect jobs and offers **Cancel** for queued or running ones;
   that action sets `jobs.cancel_requested` for the owner's job. The worker sends the
   claimed job id, the collector checks the flag at checkpoints and stops at a stage
   boundary without advancing `collector_state` or `source_status`, and the worker marks
   the job `cancelled` without retrying. The fixture run cancelled at 2/4 with "0 written".
   Next: repeat with a real GDELT job once items 1–2 unblock.

4. **Deployment — web app deployed; worker code is local.**
   Vercel deployed 2026-11-14. Live export smoke passed: 324-row CSV with the expected
   header and `X-TrendRail-Export-*` metadata, header-only results for an empty keyword and
   `source=gdelt`, and a guide reporting 19 matching SEO rows with the 10,000-row cap.
   The Python server and worker run on the owner's PC, so restart them to pick up checkpoint
   cancellation, progress, and the Settings job list.
   Next: real-provider cancel/progress check (blocked by items 1–2); otherwise deployment
   is complete.

### C. Known gaps in shipped collector work

5. **Source health — implemented and deployed.**
   [`sources/page.tsx`](../../apps/web/app/live/sources/page.tsx) lists configured sources
   even with zero items and labels OK, empty, rate-limited, blocked, parsing, error, not-run,
   and stale (older than 48 hours). The count is the last run's written records. In `prod`
   the owner also sees latest-run accepted/rejected totals and reasons, summed across keyword
   scopes from `collector_state`; public `live` intentionally omits those owner-only counters.
   Counters appear after a write run; dry runs do not write `collector_state`.
   Next: verify the counters with the first real write run.

6. **Mid-job progress — implemented, deployed, and observed with a local fixture.**
   The collector PATCHes the owner-scoped `jobs.progress`/`total` at fetch, gate, and
   persistence checkpoints (0–4/4); the worker closes finished collects at 4/4.
   [`job-status.tsx`](../../apps/web/components/live/job-status.tsx) and the Settings list
   display it. The fixture run showed 0→2→4 for a completed dry run and 0→2 for a cancelled
   run.
   Next: observe a real GDELT run and adjust the checkpoint count if it feels noisy.

7. **Collector-table backup — not implemented by decision.**
   The JSON/CSV item exports do not include `collector_records`, links, or state; collector
   rows are reproducible from the source.
   Next: revisit only if records, links, and state must be restorable.

### D. Owner and operations actions

8. **Render API is still live, under a different workspace.**
   `https://social-tracker-api.onrender.com/` still returns 200. The provided Render API
   key is valid but sees only the **My Workspace** team and its `Mod-Vite` service; it has
   no access to `social-tracker-api`, so nothing was suspended. Owner action: switch to the
   workspace that owns `social-tracker-api` and suspend it there (or create a scoped key
   from that workspace). Do not suspend `Mod-Vite`.

9. **Monitoring is automated; backups and the restore drill are not available.**
   The scheduled **Health** workflow checks prod and live every 30 minutes, opens or
   updates a GitHub issue on failure, and closes it on recovery; the last recorded run
   succeeded on 2026-11-14T02:53Z. A 2026-11-14 snapshot also showed live `/api/health`
   `{"ok":true,"items":{"active":324,...}}`, prod `/live` → 307 `/login`, live `/live` 200
   and `/live/settings` → 307 `/live`, mockup `/` 200 and `/live` → 307 `/`.
   The Supabase dashboard shows **LAST BACKUP: No backups**, so the quarterly restore
   drill cannot run until a backup exists (manual dump or a plan with backups).
   Still open: finish the 2026-11-18 window and run the drill once a backup is available.

10. **Recurring collection is coded but disabled.**
    The worker supports `COLLECT_SCHEDULE_HOURS`, active-job dedupe, and schedule keys;
    the default is `0`. Decide the host, interval, concurrency, offline behavior, and
    whether per-run local reports must be retained before enabling it.

11. **Next source and existing-source policy need an owner decision.**
    GDELT is the only approved new source. Choose the next candidate and its order; decide
    whether Google News and the Playwright ad collectors keep their current behavior or
    follow a separately approved policy.

## Completed (context)

- **Framework and persistence:** collector registry, contract, HTTP helper, quality gate,
  report writer, job validation, and Supabase persistence with targeted upserts; repeat-run
  keyword union, metric refresh, archive/trash preservation, and failure state are tested.
- **Job execution:** owner-scoped claim, lease expiry recovery, bounded retries,
  schedule-key dedupe, check-before-start cancellation, and checkpoint progress (item 6).
  Checkpoint cancellation is item 3.
- **GDELT adapter:** keyword scope, language/date/spam/metric gate, one throttle retry, and
  unit tests. Live sample remains item 1.
- **Source health:** configured sources with zero items, derived OK/empty/rate-limited/
  blocked/parsing/error/stale labels, and owner-only accepted/rejected counters in `prod`
  (item 5). The existing JSON/CSV exports cover `items` only, not a collector backup (item 7).
- **RLS and migration history (2026-11-14):** RLS is enabled on `items`, `jobs`, `profiles`,
  `source_status`, `worker_status`, and all three collector tables. The only policies are
  authenticated `ALL` policies with `user_id = auth.uid()` for items, profiles, source_status,
  keyword_stats, and the collector tables; jobs and worker_status have no policies (service
  role only). Anon reads return 0 rows; live views return rows. The `supabase_migrations`
  schema does not exist, so there is no CLI-tracked migration history; the repo tables exist
  and were applied manually.
- **Recurring schedule (code):** support exists but is disabled; enabling it is item 11.
- **AI analysis export:** shipped and deployed on 2026-11-14. The Items page exports active
  rows matching the current filters as CSV with `item_id`, keyword, source, title, author,
  URL, canonical URL, score, metric, views, published, collected, and export times, plus a
  Markdown guide and prompt (`/api/export/analysis`, `format=guide`). The cap is 10,000
  rows; the filename and `X-TrendRail-Export-*` headers state rows/total/truncation. Live
  smoke: 324-row CSV, empty and `source=gdelt` header-only results, 19-row SEO guide.
  Selected rows, schema changes, and AI-provider calls are out of scope.
- **Cancellation and job UI:** shipped and deployed on 2026-11-14. Settings lists the latest
  collect jobs with a Cancel action; the collector stops at checkpoints and reports progress.
  Verification: 65 Python tests, 35 Node tests (30 web including export, cancel, health, and
  counters; 5 worker), web/worker typecheck, worker build, Python compile, and an end-to-end
  fixture run with a real worker: cancelled at 2/4, normal done at 4/4, no writes, test jobs
  deleted.
- **Dry-run console encoding fix (2026-11-14):** `backend/collectors/dry_run.py` now
  switches stdout/stderr to UTF-8 with replacement before printing, so a Thai keyword or a
  non-Latin title cannot abort a run after its report or writes. The CLI previously crashed
  with `UnicodeEncodeError` on the Windows legacy code page while printing GDELT samples,
  and `/api/collect` printed the same summary from the server process. Covered by
  `tests/test_collectors.py::DryRunCancellationTests` (66 Python tests pass).
- **User menu and account settings:** implemented 2026-11-13; its open decisions live
  in [USER-DASHBOARD-SETTINGS-PLAN.md](USER-DASHBOARD-SETTINGS-PLAN.md).

## Fixed decisions (2026-11-13)

- First source: `gdelt_doc`, keyword scope; it is the only enabled new connector.
- Rights: title, canonical URL, author display, engagement, timestamps, and at most a
  280-character excerpt. No full article body.
- Persistence: keywords union across runs; existing items refresh `score` and `metric`
  only; trashed items are skipped; quarantine stays a drop; a failed run records `error`
  and does not advance the cursor; same-day reports append; collectors are Supabase-only.
- Quality: hard rejects and soft flags stay as implemented; the owner reviews a 50–100
  record sample before writes.

## Candidate sources

GDELT is selected. The rest still need owner selection, access/rights evidence, and a
quality contract before any adapter work.

| Candidate | Scope and evidence still needed |
|---|---|
| Bluesky | Keyword posts; verify supported access, identity, and pagination |
| Google Trends Thailand | Country signal; verify feed, occurrence identity, traffic labels, and separate signal display |
| YouTube channel feeds | Owner-selected channels; verify a real feed and dedupe video IDs against keyword search |
| Wikimedia | Pages, access/rate policy, operator contact, and pageview units |
| Mastodon | Instance allowlist, access, URI dedupe, and HTML sanitization |
| RSSHub | Hosting, routes, authentication, and rights |
| Common Crawl | Catalog/index, resource limits, and any dependency |
| data.go.th | Dataset, license, encoding, dates, geography, and token needs |
| Jetstream | Need, capacity, protocol, reconnect, backfill, and deletion |

## Data model

The repo contains a collector migration; the deployed state is unverified (item 9).

| Data | Intended role |
|---|---|
| `collector_records` | Canonical provider record, unique per owner/source/source item ID |
| `collector_item_links` | Link a record to each keyword item without replacing attribution |
| `collector_state` | Cursor, health, and counters per owner, connector, and scope |
| `items` | Existing per-keyword projection; archive/trash behavior is preserved |

No schema change is proposed. Jobs already have lease, attempts, schedule key, and
`cancel_requested`; progress columns exist but are only written at completion (item 6).

## Design invariants

- Keep `/` mock-only, `live` public and read-only, `prod` behind server-side auth, and
  service-role credentials server/worker-side. No Playwright on Vercel.
- New records pass transport, parsing, normalization, identity, scope, language, quality,
  and rights checks before persistence. Rejected records are never stored.
- Preserve stable identities, source URLs, provenance, and source/observation times.
  Update mutable metrics, keep keyword links separate, and never treat a missing search
  result as a deletion.
- Use targeted writes: never call `db._save_items()` with a partial batch, never advance a
  checkpoint after a failed write, and never silently change stores in strict mode.
  Preserve archive/trash and attribution across replay and URL collisions.
- Automated tests never touch Supabase. Stop on missing access, unsafe migration,
  conflicting contract, failed baseline, or an unapproved decision; report what is needed.
  Run the matching checks in [AGENTS.md](../../AGENTS.md) for every runtime change.
