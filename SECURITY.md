# Security policy

## Reporting

Do not open a public issue for a vulnerability or leaked secret. Email the owner at
`ntpsrm.md@gmail.com` with:

- what is affected (URL, route, or file)
- reproduction steps
- impact and any suggested fix

There is no formal SLA; the owner acknowledges reports as soon as practical.

## Secrets

- `SUPABASE_SERVICE_ROLE_KEY`, `.env.local`, `data/`, and `sessions/` must never be committed.
- The service role key stays on the server/worker. The browser gets only the publishable key.
- If a key leaks, rotate it in Supabase and Vercel, then redeploy.

## Supported surface

Production: `https://trendrail.vercel.app` (authenticated writes).
Public read-only: `https://trendrail-live.vercel.app`.
Mock: `https://trendrail-mockup.vercel.app` (no database).

Out of scope: findings that require the owner's Supabase dashboard, Vercel dashboard, or
local machine access.
