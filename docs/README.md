# TrendRail docs

Last updated: 2026-11-11. Code is the source of truth; this folder tracks active reference,
the remaining plan, post-cutover checks, and notes.

## Current reference

| Document | Use |
|---|---|
| [AGENTS.md](../AGENTS.md) | Working rules, verification, failure protocol |
| [DB.md](DB.md) | Supabase schema, mapping from `data/*.json`, dedup/upsert |
| [DEPLOY.md](DEPLOY.md) | Vercel, Render, local worker, env vars |
| [DESIGN.md](DESIGN.md) | Visual language and design system |

## Remaining work

| Plan | Status |
|---|---|
| [plans/COLLECTOR-INTEGRATION-PLAN.md](plans/COLLECTOR-INTEGRATION-PLAN.md) | **Proposed, not started.** No collectors enabled, no schema change applied. Includes a pre-write quality gate (reject trash before DB) |

## Post-cutover

Migration completed 2026-11-11:
- Vercel production deployed; legacy redirects return 307 → `/live`; GitHub Pages disabled (404)
- Vercel variants: `mockup` (fixtures), `prod` (writes), `live` (read-only, same Supabase) — see `docs/DEPLOY.md`
- Phase 3/4 parity done: quick dates, page size, select-all, archive/terms search,
  `Refresh views` without a keyword
- Monitor production through 2026-11-18
- Render API still responds at `social-tracker-api.onrender.com`; owner action: disable it
  in the Render dashboard (no credentials in this repo)
- Rollback: git tag `pre-next-migration` and the previous Vercel deployment

Collector plan phases: freeze scope → normalization/persistence → first adapters (HN, then
GDELT/Bluesky if access checks pass) → Thailand Trends/channel feeds → recurring collection.

## Reference input

| Document | Use |
|---|---|
| [reference/public_data_collector_agent_integration_guide.md](reference/public_data_collector_agent_integration_guide.md) | External collector guide; input to the remaining plan |

## Notes

| Document | Use |
|---|---|
| [notes/note-idea.md](notes/note-idea.md) | Idea: export a dataset for analysis with the user's own AI (not started) |

## Layout

```
docs/
  README.md
  DB.md
  DEPLOY.md
  DESIGN.md
  plans/       COLLECTOR-INTEGRATION-PLAN.md
  reference/   public_data_collector_agent_integration_guide.md
  notes/       note-idea.md
```
