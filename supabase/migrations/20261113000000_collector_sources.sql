-- Owner decision 2026-11-13: GDELT is the first approved collector source.
-- Additive only: widens the two source allowlists so a GDELT record can project
-- into items and report source_status. No other source is approved yet.
-- Apply before enabling the GDELT adapter; the adapter stays disabled until then.

alter table public.items drop constraint if exists items_source_check;
alter table public.items add constraint items_source_check
  check (source in ('youtube', 'gnews', 'tiktok', 'facebook', 'fbads', 'ttads', 'manual', 'gdelt'));

alter table public.source_status drop constraint if exists source_status_source_check;
alter table public.source_status add constraint source_status_source_check
  check (source in ('youtube', 'gnews', 'tiktok', 'facebook', 'fbads', 'ttads', 'gdelt'));
