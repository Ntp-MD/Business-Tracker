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
| [ARCHITECTURE.md](ARCHITECTURE.md) | Target topology, module split, data model, performance, serving, phased roadmap (proposal) |
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
| [plans/COLLECTOR-INTEGRATION-PLAN.md](plans/COLLECTOR-INTEGRATION-PLAN.md) | **Open collector work.** GNews collects live (source health ok) and the lineage migration is applied; auto search/collect was removed by owner decision (manual-only). GDELT quality rules shipped but the provider throttles this network (429), so its live sample is pending. Then: Render (different workspace), backups/restore drill, monitoring window, next source |
| [plans/USER-DASHBOARD-SETTINGS-PLAN.md](plans/USER-DASHBOARD-SETTINGS-PLAN.md) | **Implemented 2026-11-13.** Only the menu decisions remain: editing scope, public/mock confirmation, duplicate sign-out, deployment check |

Deployed to Vercel on 2026-11-14: the AI analysis export, cancel control, source health
(including owner-only reject counters), and job progress. The live export smoke passed, and
the worker pipeline was exercised with a local fixture (cancel at 2/4, normal at 4/4). The
collector path now also runs against Supabase with a live provider: GNews ran through the
worker → gate → `items` several times (SEO and Digital Marketing, later nvidia; live active
333 → 357) with source health `ok`, and cancellation was verified at 2/4 with no writes.
`items.record_id` now carries collector lineage (33 linked rows). GDELT still returns `429`
for new queries from this network, so its live sample review is pending. Collector writes are
enabled (`COLLECTOR_WRITE_ENABLED=1`); `COLLECT_CONNECTORS` selects what the Collect button
runs. Collection is manual-only: no scheduler and no `scheduled` job mode. See the collector
plan for details.

UI/UX pass v0.4 (2026-11-14): the topbar names the current page, the mobile nav scrolls and
highlights the active page, locked menus (Calendar, Reports) are clearly disabled, Content
Ideas uses collected items instead of templates, Sources shows readable status and relative
time, and the cookie banner, tables, and KPI grid follow the CSS token system on phones.

## Post-cutover

Migration completed 2026-11-11:
- Vercel production deployed; legacy redirects return 307 → `/live`; GitHub Pages disabled (404)
- Vercel variants: `mockup` (fixtures), `prod` (writes), `live` (read-only, same Supabase) — see `docs/DEPLOY.md`
- Phase 3/4 parity done: quick dates, page size, select-all, archive/terms search,
  `Refresh views` without a keyword
- Rollback: git tag `pre-next-migration` and the previous Vercel deployment
- Open ops actions (Render API, monitoring window, restore drill) are tracked in the
  collector plan, not duplicated here.

Collector progress: framework, persistence, the GDELT and GNews adapters, and the Supabase
write/cancel paths are implemented; GNews runs live while GDELT's public API throttles new
queries from this network (see the collector plan). The next source is undecided; Hacker News
was removed on 2026-11-12.

## Reference input

| Document | Use |
|---|---|
| [reference/public_data_collector_agent_integration_guide.md](reference/public_data_collector_agent_integration_guide.md) | External collector guide; input to the remaining plan |

## Notes

| Document | Use |
|---|---|
| [notes/SECURITY-AND-PROJECT-HEALTH.md](notes/SECURITY-AND-PROJECT-HEALTH.md) | Security, code quality, operational health, and handoff reminders |
| [notes/STRUCTURE-AUDIT.md](notes/STRUCTURE-AUDIT.md) | Layout audit, dead-code/clutter cleanup, invariants, and open structure findings |

## Layout

```
docs/
  README.md
  ARCHITECTURE.md
  DB.md
  DEPLOY.md
  DESIGN.md
  plans/       COLLECTOR-INTEGRATION-PLAN.md, USER-DASHBOARD-SETTINGS-PLAN.md
  reference/   public_data_collector_agent_integration_guide.md
  notes/       SECURITY-AND-PROJECT-HEALTH.md, STRUCTURE-AUDIT.md
```
