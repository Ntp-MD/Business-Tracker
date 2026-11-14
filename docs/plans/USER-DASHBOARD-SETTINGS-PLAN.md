# User menu and account settings plan

Status: **implemented 2026-11-13**. This document records what shipped and the decisions
still open. It does not authorize an auth, schema, API, storage, dependency, or deployment
change; follow [AGENTS.md](../../AGENTS.md) and the
[security and project health reminders](../notes/SECURITY-AND-PROJECT-HEALTH.md).

## Shipped

- `apps/web/components/live/user-menu.tsx` is a real button with `aria-expanded`, a
  labelled panel, Escape close with focus return, outside-click close, and mobile-safe CSS.
- `prod` shows the signed-in user's display name (provider metadata or email prefix) and
  email from the verified server-side session, with initials and an "Account" fallback.
  Invited users see their own identity.
- **Account details** opens `/live/settings#account`, a read-only section showing name,
  email, and Owner/Invited member access.
- **Settings** opens the existing operational settings; **Sign out** reuses the existing
  action. Sign out also remains in the sidebar.
- Public `live` shows a neutral **Public view** label; the mock and `mockup` use a fixture
  account (`ITOPPLUS`, `demo@trendrail.app`) with a demo note and no real sign-out.
- No avatar fetch, display-name edit, photo upload, role, invitation, account deletion, or
  new storage was added.

Files: `user-menu.tsx`, `user-menu.css`, `app/live/layout.tsx`,
`app/live/settings/page.tsx`, `app/page.tsx`.

Verification recorded on 2026-11-14: web typecheck, `npm run build:web`, and 19 fixture
tests (`tests/web_auth.test.cjs`, `tests/web_export.test.cjs`) pass. The auth tests cover
owner, invited-user, public, and mockup boundaries; they do not exercise the menu's
pointer/keyboard behavior. No manual UI or deployed-provider smoke was recorded in this
review.

## Remaining decisions

1. **Is read-only enough?** If an editable display name and/or photo is wanted, that is a
   separate design and approval: ownership, validation, error handling, provider behavior,
   and any storage/API/privacy change. Do not add editing under this plan.
2. **Are the public and mock states right?** Confirm the **Public view** label and the
   fixture account menu, including that the mock must stay network-free.
3. **Keep two sign-out controls?** Sign out is currently in both the account menu and the
   sidebar. Confirm both, or remove one in a later small change.
4. **Deployment check.** The menu is in the repo; deployed OAuth and invited-user identity
   were not verified here. Production sign-in deployment and end-to-end OAuth remain
   pending per [docs/README.md](../README.md).

## Constraints for later changes

- Use only the verified server-side session in `prod`; never show another user's identity,
  never expose tokens or the service role, and follow the auth guard for missing/expired
  sessions.
- Keep public `live` free of personal identity and the mock free of Supabase, worker, and
  network calls.
- Keep the menu available at 390px and wider, contained in the viewport, usable by keyboard
  and touch, with a visible focus state; do not use menu ARIA roles without full keyboard
  behavior.
- Do not cache account details across sessions. Missing name/email must fall back safely.
- Automated tests use fixtures and mocked auth only; never Supabase or production data.
  Run the checks in [AGENTS.md](../../AGENTS.md) before handoff.

## If editing is approved later

Define the data owner and write path, validation and error states, provider
(`user_metadata` or profile) behavior, any schema/API/storage change, privacy notice
updates, and tests for owner vs invited users, long/Thai text, expired sessions, and
repeated edits. Obtain every approval required by `AGENTS.md` before implementation.
