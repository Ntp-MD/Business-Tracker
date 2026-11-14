# TrendRail docs

Last updated: 2026-11-14. Code is the source of truth; this folder tracks active reference,
the remaining plan, post-cutover checks, and notes.

## Current reference

| Document | Use |
|---|---|
| [AGENTS.md](../AGENTS.md) | Working rules, verification, failure protocol |
| [DB.md](DB.md) | Supabase schema, mapping from `data/*.json`, dedup/upsert |
| [DEPLOY.md](DEPLOY.md) | Vercel, Render, local worker, env vars |
| [PRIVACY.md](PRIVACY.md) | PDPA notice, cookie inventory, owner review checklist |
| [DESIGN.md](DESIGN.md) | Visual language and design system |
| [Favicon (120×120 PNG)](brand/trendrail-favicon-120.png) | Square train-and-rail mark for Next.js and legacy pages |
| [Favicon square master](brand/trendrail-favicon-square.png) | 1254×1254 source artwork |
| [Logo master](brand/logo-master.png) | Source artwork for the header logo used by the web and legacy apps |
| [Favicon source](brand/fav.png) | Earlier favicon export kept for reference |
| [Earlier symbol explorations](brand/trendrail-highspeed-logo-concepts.html) | Superseded concept study |
| [Earlier full logo board](brand/trendrail-full-logo-concepts-16x10.png) | Ten options; the logo master above is selected |
| [Earlier train logo board](brand/trendrail-train-logo-concepts.png) | Concept board kept for reference |
| [Unselected vector studies](brand/trendrail-logo-train-t.svg) and [logo trace](brand/trendrail-logo.svg) | Drafts kept for reference; not used by the app |

## Remaining work

Google owner sign-in and owner-only authorization are implemented locally. Deployment,
Supabase Google-provider configuration, and end-to-end OAuth verification are pending.

| Plan | What is left |
|---|---|
| [plans/COLLECTOR-INTEGRATION-PLAN.md](plans/COLLECTOR-INTEGRATION-PLAN.md) | **Open collector work.** GDELT live sample and first write run, live cancel test, deploy, source reject counts, backup decision, Render, RLS history, monitoring, recurring schedule, next source |
| [plans/USER-DASHBOARD-SETTINGS-PLAN.md](plans/USER-DASHBOARD-SETTINGS-PLAN.md) | **Implemented 2026-11-13.** Only the menu decisions remain: editing scope, public/mock confirmation, duplicate sign-out, deployment check |

Local features deployed to Vercel on 2026-11-14: the AI analysis export, cancel control,
source-health labels, and job progress. The export passed a live smoke; a live cancel and
progress check still need the worker running. See the collector plan for the exact next
steps.

## Post-cutover

Migration completed 2026-11-11:
- Vercel production deployed; legacy redirects return 307 → `/live`; GitHub Pages disabled (404)
- Vercel variants: `mockup` (fixtures), `prod` (writes), `live` (read-only, same Supabase) — see `docs/DEPLOY.md`
- Phase 3/4 parity done: quick dates, page size, select-all, archive/terms search,
  `Refresh views` without a keyword
- Rollback: git tag `pre-next-migration` and the previous Vercel deployment
- Open ops actions (Render API, monitoring window, restore drill) are tracked in the
  collector plan, not duplicated here.

Collector progress: framework, persistence, and the GDELT adapter are implemented locally;
the live sample and first write run are blocked by GDELT access and local credentials. The
next source is undecided; Hacker News was removed on 2026-11-12.

## Reference input

| Document | Use |
|---|---|
| [reference/public_data_collector_agent_integration_guide.md](reference/public_data_collector_agent_integration_guide.md) | External collector guide; input to the remaining plan |

## Notes

| Document | Use |
|---|---|
| [notes/SECURITY-AND-PROJECT-HEALTH.md](notes/SECURITY-AND-PROJECT-HEALTH.md) | Security, code quality, operational health, and handoff reminders |

## Layout

```
docs/
  README.md
  DB.md
  DEPLOY.md
  DESIGN.md
  plans/       COLLECTOR-INTEGRATION-PLAN.md, USER-DASHBOARD-SETTINGS-PLAN.md
  reference/   public_data_collector_agent_integration_guide.md
  notes/       SECURITY-AND-PROJECT-HEALTH.md
```
