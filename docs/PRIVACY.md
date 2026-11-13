# Privacy & cookies (PDPA)

Public notice: `/privacy` (`apps/web/app/privacy/page.tsx`). Cookie notice:
`apps/web/components/cookie-notice.tsx`, shown once per browser and acknowledged in
`localStorage` (`trendrail-cookie-notice-v1`).

## Current data map

| Data | Purpose | Storage | Retention |
|---|---|---|---|
| Owner email | magic-link login | Supabase Auth | while the account is active |
| Auth session cookies (`sb-*-auth-token*`) | keep the owner signed in / PKCE | browser | until logout or expiry |
| IP + technical logs | security and operations | Vercel / Supabase | provider retention |
| Keyword, URL, title, author, engagement | dashboard content | Supabase (`items`, `collector_records`) | until deleted; trash after 7 days |
| Theme + cookie acknowledgement | UI preference | browser `localStorage` | until browser data is cleared |

No analytics, advertising or cross-site tracking cookies are used. Because only strictly
necessary cookies are set, the notice is informational; there is no optional-cookie toggle.

## Owner actions before a public/commercial launch

- Confirm the legal controller identity and a contact address (the page currently uses
  `TrendRail` and `ntpsrm.md@gmail.com`).
- Decide whether a DPO is required and add their contact if so.
- Confirm the email sender/SMTP provider and its data-processing terms.
- Review cross-border transfer terms for Supabase and Vercel.
- Confirm retention for provider logs/backups and add it to the notice.
- Have Thai counsel review the notice before relying on it commercially.

This is an implementation checklist, not legal advice.
