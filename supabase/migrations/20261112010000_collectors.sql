-- Collector canonical records, links and state (Phase 1b).
-- DRAFT: not applied yet. Review before running; then set COLLECTOR_WRITE_ENABLED=1
-- only after the dry-run sample and this schema are approved.

-- New source ids used by the collector registry.
alter table public.items drop constraint if exists items_source_check;
alter table public.items add constraint items_source_check
  check (source in ('youtube', 'gnews', 'tiktok', 'facebook', 'fbads', 'ttads', 'manual', 'hackernews'));

alter table public.items drop constraint if exists items_metric_check;
alter table public.items add constraint items_metric_check
  check (metric in ('views', 'plays', 'likes', 'points'));

alter table public.source_status drop constraint if exists source_status_source_check;
alter table public.source_status add constraint source_status_source_check
  check (source in ('youtube', 'gnews', 'tiktok', 'facebook', 'fbads', 'ttads', 'hackernews'));

create table if not exists public.collector_records (
  id                    uuid primary key default gen_random_uuid(),
  user_id               uuid not null default auth.uid() references auth.users (id) on delete cascade,
  source                text not null,
  connector_id          text not null,
  source_item_id        text not null,
  record_kind           text not null check (record_kind in ('content', 'signal')),
  content_type          text not null default 'story',
  url                   text not null,
  canonical_url         text not null,
  title                 text not null default '',
  text_excerpt          text,
  author_id             text,
  author_display        text not null default '',
  language              text,
  market                text,
  published_at          timestamptz,
  observed_at           timestamptz not null default now(),
  engagement            jsonb not null default '{}'::jsonb,
  numeric_signal        numeric,
  signal_unit           text,
  keywords_matched      text[] not null default '{}',
  raw_source_ref        jsonb not null default '{}'::jsonb,
  quality_score         int not null default 0,
  quality_flags         text[] not null default '{}',
  quality_rules_version text not null,
  is_deleted            boolean not null default false,
  deleted_at            timestamptz,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  unique (user_id, source, source_item_id)
);

create index if not exists collector_records_feed_idx
  on public.collector_records (user_id, source, observed_at desc);
create index if not exists collector_records_url_idx
  on public.collector_records (canonical_url);

create trigger collector_records_touch before update on public.collector_records
  for each row execute function public.touch_updated_at();

alter table public.collector_records enable row level security;
create policy "own collector_records" on public.collector_records
  for all to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

create table if not exists public.collector_item_links (
  user_id       uuid not null default auth.uid() references auth.users (id) on delete cascade,
  record_id     uuid not null references public.collector_records (id) on delete cascade,
  item_id       uuid not null references public.items (id) on delete cascade,
  keyword       text not null,
  connector_id  text not null,
  first_seen_at timestamptz not null default now(),
  unique (record_id, item_id)
);

create index if not exists collector_item_links_item_idx
  on public.collector_item_links (item_id);

alter table public.collector_item_links enable row level security;
create policy "own collector_item_links" on public.collector_item_links
  for all to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

create table if not exists public.collector_state (
  user_id         uuid not null default auth.uid() references auth.users (id) on delete cascade,
  connector_id    text not null,
  scope_key       text not null,
  cursor          jsonb not null default '{}'::jsonb,
  cache_validators jsonb not null default '{}'::jsonb,
  last_run_at     timestamptz,
  last_status     text,
  last_error      text,
  counters        jsonb not null default '{}'::jsonb,
  next_due_at     timestamptz,
  updated_at      timestamptz not null default now(),
  primary key (user_id, connector_id, scope_key)
);

create index if not exists collector_state_due_idx
  on public.collector_state (next_due_at);

alter table public.collector_state enable row level security;
create policy "own collector_state" on public.collector_state
  for all to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

-- Worker leases and recurring-job keys.
alter table jobs add column if not exists lease_owner text;
alter table jobs add column if not exists lease_until timestamptz;
alter table jobs add column if not exists attempts int not null default 0;
alter table jobs add column if not exists schedule_key text;

create unique index if not exists jobs_schedule_key_idx
  on jobs (schedule_key) where schedule_key is not null;
