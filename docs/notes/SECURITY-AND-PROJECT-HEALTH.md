# Security and project health reminders

Use these prompts when planning, implementing, reviewing, and handing off work. They
complement [AGENTS.md](../../AGENTS.md); they do not replace its rules or approvals.
Record current status and remaining work in [docs/README.md](../README.md).

## Security and data

- Check which variant, route, user, and data are affected. Keep `/` mock-only,
  `live` public and read-only, and `prod` protected by server-side authentication
  and authorization. Do not rely on hidden buttons as an access control.
- Check owner and invited-user behavior when relevant. Invited users can share the
  owner's data and write permissions; do not imply per-user isolation without evidence.
- Keep service-role keys, OAuth secrets, and session tokens out of client code, logs,
  screenshots, fixtures, and commits. Do not commit `.env.local` or put real personal
  information in logs, screenshots, or fixtures. Use the reporting process in
  [SECURITY.md](../../SECURITY.md) for incidents.
- Preserve user data and archive/trash; do not revoke unrelated sessions. Do not delete data,
  expose the API, broaden access, change auth, or deploy without the approvals
  required by `AGENTS.md`.
- For account UI, use the current verified server-side session, avoid sharing private
  identity on public views, and test expired sessions and unauthorized requests.

## Code health

- Inspect the current implementation and callers first. Prefer a small, complete
  change that follows existing patterns and addresses the actual cause.
- Keep validation and error handling at trust boundaries. Make failures observable;
  do not mask a failed fetch, write, or auth check as an empty success.
- Cover meaningful behavior and failure cases with focused tests; protect existing
  user workflows, accessibility, responsive layouts, and rollback paths. Automated
  tests must use local or mocked data, never Supabase or production data.
- Avoid unnecessary dependencies, duplicated logic, generated-file edits, unrelated
  formatting, and speculative features. Ask before dependency or toolchain changes.

## Project health and handoff

- Run the checks and variant smoke tests that match the change in `AGENTS.md`.
  Report exact results, including failures and checks that could not be run.
- When relevant, inspect `/api/health`, worker heartbeat, and source status; distinguish
  offline, stale, failed, and genuinely empty results. Treat external status as unknown
  until checked in the intended environment.
- Keep the active plan and documentation index current. State dependencies, owner
  decisions, deployment status, and remaining work; do not claim production is healthy
  or a task is complete without evidence.
