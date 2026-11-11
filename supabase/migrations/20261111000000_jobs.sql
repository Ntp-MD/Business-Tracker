-- Jobs + worker heartbeat for the local Playwright worker.
-- Service role only: RLS is enabled and no policies are granted to anon/authenticated.

create table if not exists jobs (
  id bigserial primary key,
  user_id uuid not null,
  kind text not null default 'fetch',
  status text not null default 'queued'
    check (status in ('queued', 'running', 'done', 'error', 'cancelled')),
  payload jsonb not null default '{}'::jsonb,
  progress int not null default 0,
  total int not null default 0,
  error text,
  cancel_requested boolean not null default false,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz
);

create index if not exists jobs_status_created_idx on jobs (status, created_at);

alter table jobs enable row level security;

create table if not exists worker_status (
  id int primary key default 1,
  last_seen timestamptz not null default now(),
  note text
);

alter table worker_status enable row level security;
