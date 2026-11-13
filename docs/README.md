# TrendRail docs

Last updated: 2026-11-13. Code is the source of truth; this folder tracks active reference,
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
| [Selected logo master (transparent PNG)](brand/trendrail-logo-final-transparent.png) | Owner-approved final artwork |
| [Header crop (transparent PNG)](brand/trendrail-logo-horizontal-transparent.png) | Used in the web and legacy headers |
| [Earlier 16:10 artwork](brand/trendrail-logo-final-16x10.png) | Superseded by the transparent final |
| [Earlier symbol explorations](brand/trendrail-highspeed-logo-concepts.html) | Superseded concept study |
| [Earlier full logo board](brand/trendrail-full-logo-concepts-16x10.png) | Ten options; the transparent logo above is selected |
| [Modern minimal variants (16:10 PNG)](brand/trendrail-logo-modern-minimal-variants-16x10.png) | Eight fresh full-logo directions; awaiting selection |
| [Creative logo directions (16:10 PNG)](brand/trendrail-logo-creative-directions-16x10.png) | Eight distinct concepts with more varied T, rail, and wordmark constructions |
| [Unselected vector studies](brand/trendrail-logo-train-t.svg) and [logo trace](brand/trendrail-logo.svg) | Drafts kept for reference; not used by the app |

## Remaining work

Google owner sign-in and owner-only authorization are implemented locally. Deployment,
Supabase Google-provider configuration, and end-to-end OAuth verification are pending.

| Plan | Status |
|---|---|
| [plans/COLLECTOR-INTEGRATION-PLAN.md](plans/COLLECTOR-INTEGRATION-PLAN.md) | **Consolidated backlog.** Collector integration and the proposed AI analysis export |
| [plans/USER-DASHBOARD-SETTINGS-PLAN.md](plans/USER-DASHBOARD-SETTINGS-PLAN.md) | **Proposed.** User menu and account settings; implementation not started |

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

Collector plan phases: freeze scope → normalization/persistence → future adapters (GDELT/
Bluesky if access checks pass) → Thailand Trends/channel feeds → recurring collection.
Hacker News was removed on 2026-11-12.

## Reference input

| Document | Use |
|---|---|
| [reference/public_data_collector_agent_integration_guide.md](reference/public_data_collector_agent_integration_guide.md) | External collector guide; input to the remaining plan |

## Notes

| Document | Use |
|---|---|
| [notes/SECURITY-AND-PROJECT-HEALTH.md](notes/SECURITY-AND-PROJECT-HEALTH.md) | Security, code quality, operational health, and handoff reminders |
| [notes/note-idea.md](notes/note-idea.md) | AI analysis export idea and sample prompt; implementation is planned, not started |

## Layout

```
docs/
  README.md
  DB.md
  DEPLOY.md
  DESIGN.md
  plans/       COLLECTOR-INTEGRATION-PLAN.md, USER-DASHBOARD-SETTINGS-PLAN.md
  reference/   public_data_collector_agent_integration_guide.md
  notes/       SECURITY-AND-PROJECT-HEALTH.md, note-idea.md
```
