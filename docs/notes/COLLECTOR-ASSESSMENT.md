# Collector — remaining work

Date: 2026-11-13. Plan: [COLLECTOR-INTEGRATION-PLAN.md](../plans/COLLECTOR-INTEGRATION-PLAN.md).
Packages 1-7 are implemented; the table below is only what is still open.

## Open items

| # | Item | Status | Next action |
|---|---|---|---|
| 1 | Live GDELT sample | **Blocked.** Every request from this network returns `HTTP 429 Too Many Requests`, even after 5 minutes. Adapter mapping, gate, and one-retry behavior are covered by unit tests only. | Retry `python -m backend.collectors.dry_run --connector gdelt_doc --keyword SEO --show-sample 20` when GDELT responds. Review the sample before trusting writes. |
| 2 | First real collect run | **Not run.** `COLLECTOR_WRITE_ENABLED=1` is set in local `.env.local`, but no collect job has executed. | Start the worker, then use **Collect** in Settings or wait for the 24-hour schedule. Set `COLLECTOR_WRITE_ENABLED=0` to pause. |
| 3 | Cancellation during work | **Not implemented.** The worker checks `cancel_requested` only before a job starts. | Needs a collector/API change; separate scope. |
| 4 | Versioned backup of collector tables | **Not implemented by decision.** Existing JSON/CSV item export remains the backup; collector rows are reproducible from the source. | Revisit only if the owner wants collector records/links/state restorable. |
| 5 | Render API | **Still live.** `https://social-tracker-api.onrender.com/` returned 200 on 2026-11-13. | Disable it in the Render dashboard (owner, no credentials in this repo). |
| 6 | AI export (package 9) | **Proposed.** No output format or sharing policy approved. | Confirm scope and format before implementation. |
| 7 | Live RLS and migration history | **Unverified.** PostgREST with the service role bypasses RLS and cannot read migration history. | Check the Supabase dashboard or a database connection when needed. |
| 8 | Monitoring window and restore drill | **Not due yet.** Monitor production through 2026-11-18; run the restore drill when scheduled. | Owner/ops follow-up. |

## Known risk

GDELT relevance is not part of the quality gate. A run only filters by identity, URL,
date window, language (Thai/English), spam phrases, and metric validity. Off-topic
English articles can reach `items`; review the first batch and trash what does not fit.
