-- Owner decision 2026-11-12: remove Hacker News from the source list.
-- Verified no items/collector_records with source = 'hackernews' before writing
-- this migration; it only narrows the allowed values. Apply after the code removal.

alter table public.items drop constraint if exists items_source_check;
alter table public.items add constraint items_source_check
  check (source in ('youtube', 'gnews', 'tiktok', 'facebook', 'fbads', 'ttads', 'manual'));

alter table public.items drop constraint if exists items_metric_check;
alter table public.items add constraint items_metric_check
  check (metric in ('views', 'plays', 'likes'));

alter table public.source_status drop constraint if exists source_status_source_check;
alter table public.source_status add constraint source_status_source_check
  check (source in ('youtube', 'gnews', 'tiktok', 'facebook', 'fbads', 'ttads'));
