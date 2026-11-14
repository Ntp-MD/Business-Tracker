# TrendRail collector integration and remaining work

Updated: 2026-11-14. This is the single list of open collector work. Completed work is
summarized once under [Completed](#completed-context). Nothing here authorizes a source,
schema, API, deployment, or business-policy change; follow [AGENTS.md](../../AGENTS.md)
and its approval list. Status history lives here instead of a separate notes file.

## Remaining work

### A. Finish the GDELT pathway

1. **GDELT live sample — quality rules shipped; live access now throttled by the provider.**
   The owner approved filtering before writes (2026-11-14), so the adapter and gate changed:
   the query is an exact phrase, one-word keywords also require `repeat2` (the article must
   mention the token twice), the provider's declared `language` wins over the script guess
   (only `en`/`th` pass; an unlisted declared language is rejected), the HTTP timeout is
   30 s, and a transient transport error is retried once. `QUALITY_RULES_VERSION` is
   `2026-11-14.1`.
   Offline replay of the earlier live 22-record payload through the new gate: 14 rejected
   `unsupported_language` (Korean, Japanese, Serbian, French, Bulgarian), 8 English left;
   those 8 still include bare-token noise, which `repeat2` targets.
   The same afternoon the provider returned `429 Too Many Requests` for every new query
   from this network (identical URLs that had answered `200` earlier still worked for a
   while, then stopped). Requests 10 s–13 min apart all failed, so this is a provider-side
   throttle, not an app error.
   Next: when GDELT answers again, capture a 50–100 record sample across the owner's
   keywords with the new query and review it before trusting a live write.

2. **First real collect run — live GNews run succeeded; GDELT still throttled.**
   GNews moved onto the collector contract on 2026-11-14 (same feed, locale, and rights as
   the legacy `collect_gnews`). A live manual collect then ran end to end:
   `gnews_search` job 11 finished `done` 4/4 in one attempt, fetching 20 Google News items;
   the gate accepted 8 (7 `th`, 1 `en`) and rejected 12 `out_of_window`, and it wrote 8
   `collector_records`, 8 links, and 8 `items` rows (gnews 130 → 138). `source_status`
   `gnews ok count 8`, `collector_state` ok, and deployed `live` moved 325 → **333**
   active items. Relevance matched the existing behavior: several Thai SEO/marketing
   stories plus some name matches ("Seo Ye Ji", "Seo Kang Joon") that the owner can trash.
   The Settings **Collect** button and the recurring schedule now read `COLLECT_CONNECTORS`
   (default `gnews_search`, see `.env.example`), so a GDELT restore only needs
   `gnews_search,gdelt_doc` there.
   The earlier GDELT write-path check stubbed only the HTTP transport with a payload
   captured from a live `200`, because that provider blocked new queries; adapter mapping,
   gate, worker, API, and Supabase writes ran for real. Results:
   - Job 9 (`SEO`, manual, max 100) finished `done` 4/4 in one attempt: `collector_records`
     1 (en), `collector_item_links` 1, one `items` row for keyword `SEO`, `collector_state`
     `last_status: ok` with `fetched 2 · accepted 1 · rejected unsupported_language 1 ·
     written 1`, and `source_status` `gdelt ok count 1`.
   - Deployed `live` sees it: `/api/health` went 324 → **325** active, and the anon views
     `live_items` / `live_source_status` return the GDELT row.
   - Job 10 was cancelled at 2/4 with "cancelled; 0 written; rerun is safe"; counters and
     state did not change.
   That first write exposed a real bug: the item metric refresh used a partial PostgREST
   upsert that violates the `items` NOT NULL columns. It now refreshes `score`/`metric`
   with grouped `PATCH` requests, and the tests cover it.
   `COLLECTOR_WRITE_ENABLED=1` is set in `.env.local` after verification; set it to `0` to
   pause writes. A collect needs `python -m backend.collectors.worker`; the local API is
   only needed for the legacy fetch/refresh jobs and the legacy static UI.
   Remaining: a GDELT live fetch and first-batch review once that provider stops
   throttling; GNews already collects live.

### B. Finish and deploy the two local features

3. **Cancellation — implemented, deployed, and exercised end-to-end with a local fixture.**
   Settings lists the latest collect jobs and offers **Cancel** for queued or running ones;
   that action sets `jobs.cancel_requested` for the owner's job. The worker sends the
   claimed job id, the collector checks the flag at checkpoints and stops at a stage
   boundary without advancing `collector_state` or `source_status`, and the worker marks
   the job `cancelled` without retrying. The fixture run cancelled at 2/4 with "0 written".
   Verified again 2026-11-14 through the real worker → API → Supabase job path (job 10,
   captured payload because the provider throttled): 2/4, "cancelled; 0 written; rerun is
   safe", attempts 1, and no `collector_state`/`source_status` change.
   Next: repeat against GDELT when it answers; its slow fetch is the natural window for a
   checkpoint cancel (GNews finishes too fast to cancel mid-run).

4. **Deployment — web app deployed; worker code is local.**
   Vercel deployed 2026-11-14. Live export smoke passed: 324-row CSV with the expected
   header and `X-TrendRail-Export-*` metadata, header-only results for an empty keyword and
   `source=gdelt`, and a guide reporting 19 matching SEO rows with the 10,000-row cap.
   The Python server and worker run on the owner's PC, so restart them to pick up checkpoint
   cancellation, progress, and the Settings job list.
   Next: repeat the cancel/progress checks with a live provider fetch; otherwise deployment
   is complete.

### C. Known gaps in shipped collector work

5. **Source health — implemented and deployed.**
   [`sources/page.tsx`](../../apps/web/app/live/sources/page.tsx) lists configured sources
   even with zero items and labels OK, empty, rate-limited, blocked, parsing, error, not-run,
   and stale (older than 48 hours). The count is the last run's written records. In `prod`
   the owner also sees latest-run accepted/rejected totals and reasons, summed across keyword
   scopes from `collector_state`; public `live` intentionally omits those owner-only counters.
   Counters appear after a write run; dry runs do not write `collector_state`.
   Verified 2026-11-14 with the write runs: `source_status` shows `gdelt` `ok` `count: 1`
   and `gnews` `ok` `count: 8` (live provider run), `collector_state` counters show
   accepted 1 / `unsupported_language` 1 for GDELT and accepted 8 / `out_of_window` 12 for
   GNews, and the anon `live_source_status` view exposes both rows.
   Remaining: confirm the owner-only counters in `prod` after the next live run.

6. **Mid-job progress — implemented, deployed, and observed with a local fixture.**
   The collector PATCHes the owner-scoped `jobs.progress`/`total` at fetch, gate, and
   persistence checkpoints (0–4/4); the worker closes finished collects at 4/4.
   [`job-status.tsx`](../../apps/web/components/live/job-status.tsx) and the Settings list
   display it. The fixture run showed 0→2→4 for a completed dry run and 0→2 for a cancelled
   run; the 2026-11-14 job-path verification showed 0→2→3→4 for a completed collect and
   0→2 for a cancelled one, so the four checkpoints are not noisy.
   Next: observe a live provider run.

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
   The scheduled **Health** workflow is configured every 30 minutes, but GitHub ran it
   about every 7 hours on 2026-11-13/14 (observed runs 01:44Z, 09:00Z, 17:18Z, 22:44Z,
   02:53Z, 09:45Z), so treat the interval as best-effort. It opens or updates a GitHub
   issue on failure and closes it on recovery. The check fails while the local worker is
   stale, so an owner PC that is off will raise the issue; decide whether that is intended
   or whether the worker should be a warning. A 2026-11-14 snapshot showed prod `/live` →
   307 `/login`, live `/live` 200 and `/live/settings` → 307 `/live`, mockup `/` 200 and
   `/live` → 307 `/`; live `/api/health` has since moved to 333 active items.
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
    follow a separately approved policy. GNews now runs through the collector contract with
    its legacy behavior and `rights: existing`, but the feed's terms state personal,
    non-commercial use only, so the owner should confirm that this remains acceptable for
    the product before relying on it.

## Completed (context)

- **Framework and persistence:** collector registry, contract, HTTP helper, quality gate,
  report writer, job validation, and Supabase persistence with targeted upserts; repeat-run
  keyword union, metric refresh, archive/trash preservation, and failure state are tested.
- **Job execution:** owner-scoped claim, lease expiry recovery, bounded retries,
  schedule-key dedupe, check-before-start cancellation, and checkpoint progress (item 6).
  Checkpoint cancellation is item 3.
- **GDELT adapter and quality rules (2026-11-14):** keyword scope; exact-phrase query with
  `repeat2` for one-word keywords; provider-declared language wins (`en`/`th` only, an
  unlisted declared language is rejected); date/spam/metric gate; 30 s timeout and one
  transient retry. Covered by unit tests; the live sample remains item 1.
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
- **Collectors package + GNews (2026-11-14):** [`backend/collectors/adapters/`](../../backend/collectors/adapters)
  now holds one module per provider; GDELT moved there and GNews was ported from the
  legacy `collect_gnews` to the same contract (same RSS feed and locale, rights unchanged,
  language left to the gate's title-script check). `gnews_search` is enabled and both
  adapters are registered. 79 Python tests, including new GNews mapping/limit/dedupe/XML
  tests; the live collect in item 2 used this pipeline.
- **Collect connector list (2026-11-14):** `COLLECT_CONNECTORS` (default `gnews_search`)
  drives both the Settings **Collect** button and the worker's recurring schedule; the
  hard-coded `gdelt_doc` is gone, so restoring GDELT is one env value.
- **Serving quick wins (2026-11-14):** the Items list selects explicit columns (no `body`)
  and `/api/health` is an explicit dynamic route with a 30 s CDN cache.
- **Collector write fix (2026-11-14):** the first write run exposed that the item metric
  refresh used a partial PostgREST upsert, which violates the `items` NOT NULL columns
  (`source`, `url`, ...). It now refreshes `score`/`metric` with one grouped `PATCH` per
  distinct value pair, so a run costs a couple of requests; covered by `StoreTests`.
- **Collector write-path verification (2026-11-14):** worker → local API → adapter → gate →
  Supabase ran with a captured live GDELT payload because the provider throttled new
  queries: job 9 `done` 4/4 (1 record, 1 link, 1 `items` row for `SEO`, `collector_state`
  ok, `source_status` `gdelt ok count 1`), job 10 `cancelled` at 2/4 with no writes, and
  deployed `live` moved 324 → 325 active items with the anon views returning the row.
  `COLLECTOR_WRITE_ENABLED=1` in `.env.local`; 73 Python tests pass.
- **Dry-run console encoding fix (2026-11-14):** `backend/collectors/dry_run.py` now
  switches stdout/stderr to UTF-8 with replacement before printing, so a Thai keyword or a
  non-Latin title cannot abort a run after its report or writes. The CLI previously crashed
  with `UnicodeEncodeError` on the Windows legacy code page while printing GDELT samples,
  and `/api/collect` printed the same summary from the server process. Covered by
  `tests/test_collectors.py::DryRunCancellationTests`.
- **User menu and account settings:** implemented 2026-11-13; its open decisions live
  in [USER-DASHBOARD-SETTINGS-PLAN.md](USER-DASHBOARD-SETTINGS-PLAN.md).

## Fixed decisions (2026-11-13)

- First source: `gdelt_doc`, keyword scope; it is the only enabled new connector.
- Rights: title, canonical URL, author display, engagement, timestamps, and at most a
  280-character excerpt. No full article body.
- Persistence: keywords union across runs; existing items refresh `score` and `metric`
  only; trashed items are skipped; quarantine stays a drop; a failed run records `error`
  and does not advance the cursor; same-day reports append; collectors are Supabase-only.
- Quality (updated 2026-11-14): exact-phrase queries, `repeat2` for one-word keywords, and
  the provider-declared language (en/th only) run before the existing hard rejects and soft
  flags. A 50–100 record live sample is still required before trusting a live write.

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
