# Collector assessment — packages 1 and 2

Date: 2026-11-13. Read-only. No code, data, schema, environment, or source setting was
changed by this assessment. Plan: [COLLECTOR-INTEGRATION-PLAN.md](../plans/COLLECTOR-INTEGRATION-PLAN.md).

## Verdict

The framework is dry-run safe and has no enabled adapter, so nothing can collect or write
today. Persistence semantics, state/health reporting, and the worker lease path are not
ready for a real source. Four owner decisions below block package 3.

## Package 1 — gap list

Status: **pass** = requirement met and evidenced; **fail** = missing or wrong;
**decision** = behavior is intentional or ambiguous and needs an owner choice.

| # | Area | Evidence | Status |
|---|---|---|---|
| 1 | Adapter allowlist empty, every connector disabled | `backend/collectors/registry.py:25-98`, `dry_run.py:21` | pass |
| 2 | Triple write gate (payload, CLI, store) | `job.py:52-53`, `dry_run.py:89-91`, `store.py:138-139` | pass |
| 3 | Strict job payload validation | `job.py:11-19,25-60`; `tests/test_collectors.py:131-179` | pass |
| 4 | Sequential writes and request count | `store.py:146-177`: one GET per record, then one GET and one POST per new item. 100 records is roughly 250 sequential HTTP calls | fail — rate and latency risk |
| 5 | Checkpoint timing and failure state | `store.py:201-211` writes state only after every write succeeds; no per-record checkpoint; `last_status` is only ever `"ok"` | fail — a mid-run failure leaves rows written with no state or error record |
| 6 | Updates to existing items | `store.py:159-164` returns the existing item id and skips the insert; no PATCH anywhere in `store.py` | fail — score, metric, and title never refresh on re-collection |
| 7 | Multiple keywords | `store.py:104` sets `keywords_matched: [keyword]` on every upsert; `store.py:184-193` upserts links on `record_id,item_id`, so `keyword` is overwritten by the latest run | fail — earlier keywords are lost |
| 8 | Trashed or archived items | `_find_item_id` (`store.py:55-67`) does not filter `deleted_at` or `archived_at` | decision — a re-collected item can link to a trashed row and record `ok` while nothing is visible |
| 9 | Cross-source dedupe | `quality.py:130-140` dedupes only by `source_item_id`; `items` is unique per `user_id,keyword,canonical_url`, so one URL from two sources produces two records and one item | decision — define whether records merge or stay separate |
| 10 | Quarantine versus log-only review | `quality.py:203-206` moves flagged records out of `accepted`; `dry_run.py:50-58` reports only status, reason, and URL hash; no quarantine table exists | decision — quarantine is currently a silent drop, not reviewable output |
| 11 | Report overwrite | `dry_run.py:110-111` uses `collector-<id>-<day>.jsonl` and `write_text`, so a second run on the same day replaces the first | fail — audit history is lost |
| 12 | Local JSON fallback | `store.py:140-141` requires configured Supabase; no JSON adapter exists | decision — acceptable if collectors are Supabase-only |
| 13 | Enqueue path for `collect` | `apps/web/lib/data/jobs.ts:21` only accepts `fetch` and `refresh_views`; no UI or action creates a `collect` job | fail — `/api/collect` is reachable only by a manual POST |
| 14 | Worker lease, attempts, retry | `supabase/migrations/20261112010000_collectors.sql:109-115` adds `lease_owner`, `lease_until`, `attempts`, `schedule_key`; `apps/worker/src/index.ts` never reads or writes them | fail — a crashed worker leaves a job `running` forever, and nothing retries |
| 15 | Atomic claim | `apps/worker/src/index.ts:58-68` PATCHes with `status=eq.queued`, so only one worker can win | pass for duplicates; no lease expiry |
| 16 | Quality rules version | `job.py:68` returns `quality_rules_version`, `backend/server.py` drops it before `collector_dry_run.run`; `quality.py:199` always stamps the code constant | fail — a stale job silently uses the current rules |
| 17 | `/api/collect` error handling | `backend/server.py` catches `ValueError`, `RuntimeError`, `SystemExit`; `db._request` re-raises `urllib.error.HTTPError` (`backend/db.py:102`) | fail — a Supabase error becomes an uncaught 500 |
| 18 | Outbound HTTP guard | `http.py:19-65`: scheme check, IP-literal block, 15 s timeout, 2 MB cap, JSON-only | pass; DNS rebinding and port allowlisting are open hardening items for package 4 |
| 19 | Source health | `store.py` never writes `source_status`; only the legacy fetch path does | fail — Sources will not show collector runs |
| 20 | Item projection | `store.py:112-128` writes `body=""`, `channel_url=""`, `views=None`, `score=int(numeric_signal)` | pass for first release; float signals truncate |
| 21 | Test coverage | `tests/test_collectors.py` covers gate rules, payload validation, report redaction, and one store upsert path | partial — no test for item update, multi-keyword merge, state error, report overwrite, or worker claim/lease |

Related separation check: the legacy fetch path (`/api/fetch`, Playwright collectors) and the
collector path (`/api/collect`, `backend/collectors/`) share `items` but not code or state.
That is correct for now; package 5 must define whether a source lives in both paths.

## Package 2 — environment baseline

Read-only probes against the Supabase project using the service key (names only, no values
printed). `Range: 0-0` with exact counts.

| Object | Result |
|---|---|
| `items` | 324 rows |
| `collector_records` | exists, 0 rows |
| `collector_item_links` | exists, 0 rows |
| `collector_state` | exists, 0 rows |
| `jobs` | 1 row; `lease_owner`, `lease_until`, `attempts`, `schedule_key` present |
| `source_status` | 1 row (`gnews`) |
| `profiles` | 1 row |

Configuration: `.env.local` defines `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`,
`SUPABASE_USER_ID`, `SUPABASE_STRICT`, `ALLOW_ORIGIN`. `COLLECTOR_WRITE_ENABLED` is absent,
so writes are off.

Unknowns that PostgREST cannot answer:

- Applied migration history. Table and column presence proves the collector migration ran,
  but not that `20261112020000_remove_hackernews.sql` ran after it. If it did not, the
  `items` and `source_status` check constraints still allow `hackernews`.
- Live RLS policy definitions. Service-role probes bypass RLS. The policies exist in SQL;
  the deployed definitions need a dashboard check or a database connection.
- Queue state of the single `jobs` row.

CI at the time of this assessment: green on `e96f755`.

## Owner decisions needed before package 3

1. **First source and scope.** Pick one provider from the registry and its keyword or
   country scope. Recommended start: `gdelt_doc` (keyword, public documents) because it has
   no login and the smallest rights surface. Alternative: finish the existing Google News or
   Playwright ad path first.
2. **Data rights.** Approve fields, retention, redistribution, deletion response, and whether
   an excerpt is stored (`text_excerpt` exists and is unused). Default proposal: store title,
   canonical URL, author display, engagement, timestamps, and a 280-character excerpt.
3. **Persistence semantics.** Decide each:
   - merge `keywords_matched` and keep the first link keyword instead of overwriting;
   - update existing `items` score/metric, or freeze the first projection;
   - re-collected trashed items: skip, restore, or link silently;
   - store quarantined records for review, or keep the current drop;
   - write `source_status` after each run.
4. **Quality policy.** Approve hard rejects, soft flags, language set, and who reviews the
   50-100 record sample. Current gate rejects `missing_identity`, `malformed`, `bad_url`,
   `out_of_window`, `unsupported_language`, `spam`, `metric_invalid`, and quarantines
   `short_title` and `all_caps`.

Package 5 also needs decision 1; packages 6-7 need decision 3; package 7 additionally needs a
scheduler owner and cadence, which is plan decision 6.

## Owner decisions (2026-11-13)

The owner accepted the recommendations in this document. Scope of each decision:

1. **First source:** `gdelt_doc`, keyword scope. The adapter stays disabled until the
   package 5 access check and sample review pass.
2. **Rights:** store title, canonical URL, author display, engagement, timestamps, and an
   excerpt of at most 280 characters. No full article body. Excerpt capture lands with the
   package 5 adapter; `collector_records.text_excerpt` already exists.
3. **Persistence:** implemented in `backend/collectors/store.py`:
   - `keywords_matched` is unioned across runs; the first link keyword is kept.
   - Existing items refresh `score` and `metric` only; body, author, channel, archive, and
     trash fields are never rewritten.
   - Trashed items are skipped: no link, no projection refresh.
   - Quarantine stays a drop. Review happens on the local dry-run sample (titles printed by
     `--show-sample`), not in Postgres.
   - `source_status` is written after every run; a failed run records `last_status = error`
     and does not advance the cursor.
   - Records and items are read in two batched requests per run instead of one request per
     record.
   - Same-day reports append instead of overwrite.
   - Local JSON fallback is not required; collectors are Supabase-only.
4. **Quality policy:** unchanged hard rejects and soft flags in `backend/collectors/quality.py`.
   The owner reviews the 50-100 record sample from a dry run. Low engagement alone is not a
   hard rejection.

Schema: `supabase/migrations/20261113000000_collector_sources.sql` adds `gdelt` to the
`items` and `source_status` source allowlists. It is additive and has **not** been applied.
Applying it is an owner step before the GDELT adapter can write.

## Status after the decisions

- Packages 1-2: done (this document).
- Package 3: done locally; migration applied by the owner on 2026-11-13.
- Package 4: done locally. Jobs are owner-scoped, leased for 60 minutes, retried up to
  3 attempts, and expired leases return to `queued`. Cancellation is still checked only
  before a job starts.
- Package 5: `backend/collectors/gdelt.py` is implemented and `gdelt_doc` is enabled for
  dry-run only. Unit tests cover mapping and the gate. A live sample could not be
  collected because GDELT returned HTTP 429 from this network; rerun
  `python -m backend.collectors.dry_run --connector gdelt_doc --keyword technology --show-sample 10`
  from another network before enabling writes.
- Package 6: `source_status` is written on every collector run and the Sources page reads
  it. Existing JSON/CSV item export is unchanged; collector records, links, and state are
  not part of the backup. That is accepted for now because the JSON files remain the
  version-1 backup and collector rows are reproducible from the source.
- Package 7: Settings has a per-profile **Collect** button that queues one `collect` job
  per keyword. The worker can also self-schedule when `COLLECT_SCHEDULE_HOURS` is set;
  it is off by default, so recurring collection needs an owner cadence decision.
- Package 8: the Render API still needs to be disabled in its dashboard (owner action).
- Package 9 (AI export): still proposed, no format approved.

## Remaining fixes

Still open: a successful live GDELT sample, cancellation during work, versioned backup
of collector tables (if the owner wants it), Render cleanup, and the AI export format.
