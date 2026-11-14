-- DRAFT: not applied. Phase 3 of docs/ARCHITECTURE.md (data normalization).
--
-- Adds lineage from the serving projection (`items`) back to the canonical collector
-- record, and a normalized keyword key for case/whitespace-insensitive identity.
-- Both additions are backward compatible: existing writers keep working because
-- `keyword_key` is generated and `record_id` stays nullable until the projection writer
-- sets it.
--
-- Apply only after a Supabase backup and after the preflight checks below are clean.
-- After applying, update `live_items` if the public view should expose the new columns,
-- then change the collector projection in backend/collectors/store.py to set record_id.

-- 1) Normalized keyword key (NFC/trim/collapse/lowercase in code, same shape here).
--    Generated so legacy fetch, collector projection, import, and UI edits need no change.
alter table public.items
  add column if not exists keyword_key text generated always as (
    lower(regexp_replace(btrim(keyword), '\s+', ' ', 'g'))
  ) stored;

create index if not exists items_keyword_key_idx
  on public.items (user_id, keyword_key) where deleted_at is null;

-- Preflight: treat this as a report first. Any row here is a keyword pair that a unique
-- index would reject (for example "SEO" vs "seo").
--   select user_id, keyword_key, canonical_url, array_agg(distinct keyword) as variants
--   from public.items
--   group by user_id, keyword_key, canonical_url
--   having count(distinct keyword) > 1;
--
-- Enable uniqueness only after that report is empty (design decision, section 4):
-- create unique index if not exists items_keyword_key_url_key
--   on public.items (user_id, keyword_key, canonical_url);

-- 2) Lineage to the canonical record the projection came from.
alter table public.items
  add column if not exists record_id uuid
  references public.collector_records (id) on delete set null;

create index if not exists items_record_idx
  on public.items (record_id) where record_id is not null;

-- Backfill draft: only for rows already linked through collector_item_links.
-- Review the row count first; keep it as a one-off script, not an automatic migration.
--   update public.items i
--   set record_id = l.record_id
--   from public.collector_item_links l
--   where l.item_id = i.id and i.record_id is null;

-- 3) Public view: expose the new columns only if the live UI needs them.
-- alter view public.live_items add column keyword_key text;
-- alter view public.live_items add column record_id uuid;
