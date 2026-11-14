# TrendRail collector integration and remaining work

Updated: 2026-11-14. This is the single list of open collector work. Completed work is
summarized once under [Completed](#completed-context). Nothing here authorizes a source,
schema, API, deployment, or business-policy change; follow [AGENTS.md](../../AGENTS.md)
and its approval list. Status history lives here instead of a separate notes file.

## Remaining work

### A. Finish the GDELT pathway

1. **GDELT live sample — blocked.**
   Every request from this network returns `HTTP 429 Too Many Requests` (rechecked
   2026-11-14). No sample has been saved: `data/reports/` does not exist here. Mapping,
   gate, and one-retry behavior are covered by unit tests only.
   Next: run
   `python -m backend.collectors.dry_run --connector gdelt_doc --keyword SEO --limit 100 --show-sample 100`
   from a network GDELT accepts, then review the records for relevance, language, and
   spam before trusting writes.

2. **First real collect run — not run and not runnable here.**
   `COLLECTOR_WRITE_ENABLED=1` was recorded in a local `.env.local`, but that file is
   absent from this checkout and no worker process is running (2026-11-14).
   Next: owner restores `.env.local` with real Supabase credentials, starts the API and
   worker, queues one profile **Collect** job, and reviews the first batch. Set
   `COLLECTOR_WRITE_ENABLED=0` to pause writes.
   Known risk: GDELT relevance is not in the gate, so off-topic English articles can
   reach `items`; trash what does not fit.

### B. Finish and deploy the two local features

3. **Cancellation — implemented locally; live run not tested.**
   Settings now lists the latest collect jobs and offers **Cancel** for queued or running
   ones; that action sets `jobs.cancel_requested` for the owner's job. The worker sends the
   claimed job id, the collector checks the flag at checkpoints and stops at a stage
   boundary without advancing `collector_state` or `source_status`, and the worker marks
   the job `cancelled` without retrying (2026-11-14, fixture tests only).
   Next: run a live cancel with a worker and confirm the job turns `cancelled`, the row
   stops progressing, and source health stays unchanged.

4. **Deploy the local work — not deployed.**
   The AI analysis export, the cancel control, source-health states, and job progress are
   local commits only. The export is read-only; cancellation adds an optional `job_id`
   field to `/api/collect` and uses the existing jobs columns.
   Next: owner approves push/deploy. Update the Python server before the worker because an
   old server rejects the new field. Smoke `/live/items` export (filters, empty result,
   guide), one Settings cancel, and the progress/health labels.

### C. Known gaps in shipped collector work

5. **Source health is partial.**
   [`sources/page.tsx`](../../apps/web/app/live/sources/page.tsx) now lists configured
   sources even with zero items and labels OK, empty, rate-limited, blocked, parsing, error,
   not-run, and stale (older than 48 hours). The count is the last run's written records.
   Still missing: accepted/rejected counts by reason and per-source coverage. Reject counts
   need a read view or schema decision because `source_status` stores only the written count.
   Next: decide whether reject counts are needed; if yes, approve the view and contract.

6. **Mid-job progress — implemented locally; live check pending.**
   The collector PATCHes the owner-scoped `jobs.progress`/`total` at fetch, gate, and
   persistence checkpoints (0–4/4); the worker closes finished collects at 4/4.
   [`job-status.tsx`](../../apps/web/components/live/job-status.tsx) and the Settings list
   display it.
   Next: confirm the steps during a live run and adjust the checkpoint count if it feels
   noisy.

7. **Collector-table backup — not implemented by decision.**
   The JSON/CSV item exports do not include `collector_records`, links, or state; collector
   rows are reproducible from the source.
   Next: revisit only if records, links, and state must be restorable.

### D. Owner and operations actions

8. **Render API is still live.**
   `https://social-tracker-api.onrender.com/` returned 200 on 2026-11-14 06:56 UTC
   (`server: uvicorn`). Owner action: disable it in the Render dashboard; no credentials
   are in this repo.

9. **Live RLS and migration history are unverified.**
   PostgREST with the service role bypasses RLS and cannot read migration history.
   Next: check the Supabase dashboard or a database connection and record the applied
   migrations plus policies.

10. **Monitoring window and restore drill are in progress.**
    2026-11-14 snapshot: live `/api/health` returned
    `{"ok":true,"items":{"active":324,"archived":0,"trash":0},"worker":null}`; prod
    `/live` → 307 `/login`; live `/live` 200 and `/live/settings` → 307 `/live`; mockup
    `/` 200 and `/live` → 307 `/`. The worker heartbeat is `null`.
    Next: keep the window open through 2026-11-18 and run the quarterly restore drill when
    due.

11. **Recurring collection is coded but disabled.**
    The worker supports `COLLECT_SCHEDULE_HOURS`, active-job dedupe, and schedule keys;
    the default is `0`. Decide the host, interval, concurrency, offline behavior, and
    whether per-run local reports must be retained before enabling it.

12. **Next source and existing-source policy need an owner decision.**
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
- **Source health:** configured sources with zero items and derived OK/empty/rate-limited/
  blocked/parsing/error/stale labels (item 5). Reject counts remain item 5; the existing
  JSON/CSV exports cover `items` only, not a collector backup (item 7).
- **Recurring schedule (code):** support exists but is disabled; enabling it is item 11.
- **AI analysis export:** shipped locally on 2026-11-14. The Items page exports active rows
  matching the current filters as CSV with `item_id`, keyword, source, title, author, URL,
  canonical URL, score, metric, views, published, collected, and export times, plus a
  Markdown guide and prompt (`/api/export/analysis`, `format=guide`). The cap is 10,000
  rows; the filename and `X-TrendRail-Export-*` headers state rows/total/truncation.
  Selected rows, schema changes, and AI-provider calls are out of scope.
- **Cancellation and job UI:** shipped locally on 2026-11-14. Settings lists the latest
  collect jobs with a Cancel action; the collector stops at checkpoints and reports
  progress. Verification: 65 Python tests, 32 Node tests (27 web including export, cancel,
  and health; 5 worker), web/worker typecheck, worker build, and Python compile.
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
