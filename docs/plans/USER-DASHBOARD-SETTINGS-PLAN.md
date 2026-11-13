# Software — User menu and account settings plan

Status: **implemented 2026-11-13**. Read-only account information shipped first; the
scope decisions at the end remain open for any later editing feature. This document does
not authorize a schema, API, auth, deployment, or business-policy change. Follow
[AGENTS.md](../../AGENTS.md) before further implementation and keep existing unrelated
work intact. Review the
[security and project health reminders](../notes/SECURITY-AND-PROJECT-HEALTH.md)
throughout this work.

## Goal

Make the user control useful: an authenticated user can open a compact account menu,
see whose account is signed in, reach Settings, and sign out. Make the control usable
on desktop and mobile while preserving the existing TrendRail dashboard design.

**Proposed first release:** read-only account information, a link to existing Settings,
and Sign out. Editing a name or photo is a separate scope decision. The owner may
change this proposal before implementation.

## Current state

- In [`apps/web/app/live/layout.tsx`](../../apps/web/app/live/layout.tsx), the top-right
  `IT` / `ITOPPLUS` control is static markup, not a button. The mock preview at
  [`apps/web/app/page.tsx`](../../apps/web/app/page.tsx) has its own static copy.
- The mobile CSS hides `.top-actions .user` at widths of 600px and below; the
  current control is therefore unavailable on small screens.
- [`Sidebar`](../../apps/web/components/live/sidebar.tsx) already provides Settings and
  Sign out when the deployment is writable. [`/live/settings`](../../apps/web/app/live/settings/page.tsx)
  manages collection profiles, backups, and other operational settings; those
  **search profiles are not user accounts**.
- `prod` requires an authenticated and authorized user. The owner is allowed and an
  optional email allowlist can admit invited users; invited users currently share the
  owner's data and write access. This plan does not change that access model.
- The `live` variant is public and read-only; its proxy blocks `/live/settings` and
  non-GET requests. `/` is a fixture-only mock in all variants. The actual deployment
  and provider configuration were not checked as part of this plan.

## Proposed behavior

| Surface | User control | Available actions |
|---|---|---|
| `prod` at `/live` | A button opens the signed-in user's menu. Show the account email from the authenticated user and a display name when available; use a neutral fallback. | Account details, Settings, Sign out |
| Public `live` at `/live` | Show a neutral **Public view** label instead of a personal account. Do not reveal the owner's identity. | No account or write action; retain existing public navigation and theme toggle |
| `/` mock preview and `mockup` | Provide a clearly labeled sample-account menu using fixture data only. | Offer a client-only demo of account/settings behavior; do not offer a real sign-out or initiate network calls |

In `prod`, **Account details** points to a proposed Account section on the existing
`/live/settings` page, for example `/live/settings#account`. The section shows the
current signed-in user's available display name and email as read-only information.
**Settings** reaches the existing operational settings; the existing search profiles,
backup, and collector controls retain their behavior. **Sign out** reuses the existing
sign-out action. Do not claim a different session-revocation scope without verifying
and, if necessary, separately approving a change.

Only show identity data obtained from the verified server-side session in `prod`.
An invited user must see their own identity, not the owner's email or a hard-coded
`ITOPPLUS` name. If no trustworthy name is available, show a generic account label;
derive initials safely and provide a fallback. Keep personal identity, session data,
and service credentials out of public `live` and the mock. Do not cache a user's menu
or account details across sessions. If the session is missing, expired, or cannot be
verified, follow the existing auth guard and never show another user's details.

For the first release, use initials rather than fetching an external avatar image.
Do not add display-name edits, photo uploads, email/password changes, account linking,
invitations, roles, account deletion, or new storage as part of this proposal.

## Interface and accessibility

- Preserve the current topbar, dashboard typography, spacing, and light/dark tokens.
  The account control stays beside the existing theme switch, with a visible focus
  state and a comfortable touch target.
- Use a real button with an accessible name, `aria-expanded`, and an association to
  its menu. Use normal links and a form/button for actions; do not use menu-specific
  ARIA roles unless their complete keyboard behavior is implemented.
- Open by pointer or keyboard; allow Tab/Shift+Tab through actions. Close on Escape,
  outside click, or navigation. Restore focus to the trigger after Escape; do not
  steal focus from an outside click. Avoid nested forms and inaccessible controls.
- Keep the control reachable at 390px and wider, and keep the panel within the
  viewport. Check long names/emails, Thai text, zoom, light/dark themes, and reduced
  motion. Do not hide an essential account action on mobile.
- Show only working actions. Explain the public and demo states with concise labels;
  do not use a disabled-looking action that implies real account management exists.

## Implementation sequence — future work

1. **Confirm scope.** Owner confirms the first-release proposal, desired behavior in
   public live and mock preview, and whether account editing or photo upload belongs
   in this release. Treat changes to auth, schema/RLS, storage, dependencies, or API
   contracts as separate approval gates.
2. **Establish the identity contract.** Inspect the current auth implementation,
   including `canAccess`, invited-user behavior, `getUser`, and `signOut`. Define a
   minimal server-side view model for the current authenticated user, with safe
   missing-name/email behavior. Reuse existing session infrastructure; do not pass
   auth tokens or the service role to the browser.
3. **Build the prod menu.** Replace the static topbar label in the live layout with
   a small accessible interactive control. Reuse the existing Settings route and
   sign-out action. Keep authorization enforced server-side, including for direct
   requests and server actions.
4. **Add account details.** Add a focused read-only Account section to the existing
   Settings page without rewriting it or changing collection profiles. Label the
   account from the current session; do not imply that invited users have separate
   data or permissions.
5. **Handle public and mock variants.** Render the agreed public state without
   fetching personal data. Implement any mock menu using client-side fixtures only;
   `/` and its account controls must remain free of Supabase, worker, and network calls.
   Do not assume existing `/?view=settings` navigation is network-free; verify it
   and use a client-only demonstration or omit that action if it cannot satisfy this rule.
6. **Verify and document.** Run the checks below, update the documentation index and
   relevant operating docs, and report exact results. Deploy only after the separate
   approval required by `AGENTS.md`.

## Acceptance and verification

- A prod owner can open the menu, identify their account, navigate to account details
  and Settings, and sign out. The same flow shows the invited user's own identity
  when invite mode is enabled. Authentication and authorization failures must not
  reveal another user's data.
- The account menu works with keyboard, touch, outside click, and Escape; it remains
  visible and contained at 390, 768, 1024, and 1440px in both themes. Confirm that
  the accessible name, expanded state, focus, and announced content are correct.
- Public live remains accessible and read-only, blocks `/live/settings` and writes,
  and exposes no owner identity. Mock `/` uses fixtures only; opening and using its
  account control initiates no network calls. Existing Settings, theme switching, magic link, password,
  Google login, and sign-out behavior remain intact.
- Test missing name/email, long and Thai text, expired session, switching accounts,
  owner versus invited user, direct URL access, repeated open/close, and menu
  navigation. Use local fixtures and mocked auth; **automated tests never touch
  Supabase or production data**. Do not create or delete real user data for testing.
- Run `python -m unittest discover -s tests`,
  `python -m py_compile backend/server.py backend/db.py backend/pw_login.py`,
  `npx tsc --noEmit -p apps/web/tsconfig.json`, `node --test tests/web_auth.test.cjs`,
  `npm run lint`, and `npm run format:check`. Add focused UI tests for the new
  behavior; run `npm run build` if shared types or build config change. Perform the
  applicable local UI and three-variant smoke checks from `AGENTS.md` with an
  isolated or mocked environment. Report any check or real-provider smoke not run.

## Decisions and stop conditions

- Confirm whether read-only account details are sufficient, or whether editable
  display name and/or photo is required. Editing requires a separate design for data
  ownership, validation, error handling, provider behavior, and any storage/API or
  privacy changes; obtain the applicable approvals before implementation.
- Confirm the proposed **Public view** and mock-demo behavior and whether Sign out
  should remain in the sidebar as well as the new menu.
- Stop if current deployment behavior differs from the repo, if the correct session
  identity cannot be established, if a solution requires an unapproved contract or
  deployment change, or if baseline tests fail. Report the evidence and owner
  decision needed instead of inventing a role or exposing account information.
