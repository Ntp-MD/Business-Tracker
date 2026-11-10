-- Social Tracker — Supabase schema (initial)
-- Source of truth today: data/*.json (items, archive, trash, profiles, sources, analysis).
-- archive/trash are soft-deletes of items: archived_at / deleted_at.

create extension if not exists pg_trgm;

-- ─────────────────────────────── profiles ───────────────────────────────
create table public.profiles (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null default auth.uid() references auth.users (id) on delete cascade,
  name       text not null,
  keywords   text[] not null default '{}',
  sources    text[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, name)
);

-- ──────────────────────────────── items ─────────────────────────────────
-- One row per (keyword, canonical_url). Archive = archived_at, trash = deleted_at.
create table public.items (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null default auth.uid() references auth.users (id) on delete cascade,
  keyword       text not null,
  source        text not null check (source in ('youtube', 'gnews', 'tiktok', 'facebook', 'fbads', 'ttads', 'manual')),
  url           text not null,
  canonical_url text not null,
  title         text not null default '',
  body          text not null default '',
  author        text not null default '',
  channel_url   text not null default '',
  score         bigint not null default 0 check (score >= 0),
  metric        text check (metric in ('views', 'plays', 'likes')),
  views         bigint,
  published     timestamptz,
  asset_path    text,                          -- storage: thumbnails/<user_id>/<file>.jpg
  archived_at   timestamptz,
  deleted_at    timestamptz,
  created_at    timestamptz not null default now(),   -- was item.created_at
  updated_at    timestamptz not null default now(),
  unique (user_id, keyword, canonical_url)
);

create index items_feed_idx      on public.items (user_id, keyword, score desc) where deleted_at is null;
create index items_source_idx    on public.items (user_id, keyword, source)    where deleted_at is null;
create index items_published_idx on public.items (user_id, published desc)    where deleted_at is null;
create index items_archive_idx   on public.items (user_id, archived_at desc)  where archived_at is not null and deleted_at is null;
create index items_trash_idx     on public.items (user_id, deleted_at desc)   where deleted_at is not null;
create index items_title_trgm    on public.items using gin (title gin_trgm_ops);

-- ───────────────────────────── keyword_stats ────────────────────────────
-- Replaces data/analysis.json + data/index.json. Recompute after each fetch.
create table public.keyword_stats (
  user_id     uuid not null default auth.uid() references auth.users (id) on delete cascade,
  keyword     text not null,
  total       integer not null default 0,
  by_source   jsonb not null default '{}'::jsonb,   -- {"youtube":23,"gnews":19}
  hot         text,
  top_terms   jsonb not null default '[]'::jsonb,   -- [["e-commerce",6],...]
  suggestions jsonb not null default '[]'::jsonb,
  computed_at timestamptz not null default now(),
  primary key (user_id, keyword)
);

-- ───────────────────────────── source_status ────────────────────────────
-- Replaces data/sources.json: last result per source.
create table public.source_status (
  user_id    uuid not null default auth.uid() references auth.users (id) on delete cascade,
  source     text not null check (source in ('youtube', 'gnews', 'tiktok', 'facebook', 'fbads', 'ttads')),
  checked_at timestamptz not null default now(),
  ok         boolean not null default false,
  count      integer not null default 0,
  error      text,
  primary key (user_id, source)
);

-- ───────────────────────────── updated_at ───────────────────────────────
create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

create trigger profiles_touch before update on public.profiles
  for each row execute function public.touch_updated_at();
create trigger items_touch before update on public.items
  for each row execute function public.touch_updated_at();

-- ──────────────────────────── counts / summary ──────────────────────────
-- Dashboard totals without reading keyword_stats (security_invoker keeps RLS).
create or replace view public.v_keyword_totals
with (security_invoker = true) as
select
  user_id,
  keyword,
  count(*)                                                          as total,
  count(*) filter (where source = 'youtube')                        as youtube,
  count(*) filter (where source = 'gnews')                          as gnews,
  count(*) filter (where source = 'tiktok')                         as tiktok,
  count(*) filter (where source = 'fbads')                          as fbads,
  count(*) filter (where source = 'ttads')                          as ttads,
  max(created_at)                                                   as last_item_at
from public.items
where deleted_at is null
group by user_id, keyword;

-- ──────────────────────────────── RLS ───────────────────────────────────
alter table public.profiles      enable row level security;
alter table public.items         enable row level security;
alter table public.keyword_stats enable row level security;
alter table public.source_status enable row level security;

create policy "own profiles" on public.profiles
  for all to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

create policy "own items" on public.items
  for all to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

create policy "own keyword_stats" on public.keyword_stats
  for all to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

create policy "own source_status" on public.source_status
  for all to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

-- ─────────────────────────────── storage ────────────────────────────────
insert into storage.buckets (id, name, public)
values ('thumbnails', 'thumbnails', false)
on conflict (id) do nothing;

create policy "own thumbnails" on storage.objects
  for all to authenticated
  using (bucket_id = 'thumbnails' and (storage.foldername(name))[1] = (select auth.uid())::text)
  with check (bucket_id = 'thumbnails' and (storage.foldername(name))[1] = (select auth.uid())::text);

-- Trash purge (optional, pg_cron):
-- select cron.schedule('purge-trash', '0 3 * * *',
--   $$ delete from public.items where deleted_at < now() - interval '7 days' $$);
