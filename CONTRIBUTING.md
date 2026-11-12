# Contributing

The repository is private and proprietary (see `LICENSE`). Work on a branch and open a
pull request; do not push directly to `main` unless you are the owner.

## Before you start

- Read `AGENTS.md` for the variant, auth, live read-only, and data rules.
- Ask the owner before adding a dependency, changing Supabase schema/RLS, changing the API
  contract, or touching deployment settings.
- Never commit `.env.local`, service role keys, `data/`, `sessions/`, or generated build
  output.

## Checks

```bash
npm ci
pip install -r requirements-dev.txt
npm run lint
npm run format:check
python -m unittest discover -s tests
npx tsc --noEmit -p apps/web/tsconfig.json
npm run typecheck
npm run build
```

Read-only E2E (deployed variants):

```bash
pip install -r requirements.txt
python -m playwright install chromium
npm run test:e2e
```

## Rules

- Keep `/` mock-free of network calls; keep `/live` read-only.
- Migrations are append-only under `supabase/migrations/`.
- Small diffs; match surrounding patterns; do not reformat unrelated code.
- Run `npm run format` before committing.
