-- Public read-only views for the `live` Vercel variant.
-- The live deployment uses the publishable/anon key against these views only,
-- so a code bypass still cannot write. Prod keeps using the base tables with
-- the service role.
--
-- Apply in Supabase SQL editor (or `supabase db push`) before setting
-- LIVE_READ_ANON=1 on the live project.

create or replace view public.live_items as
select
  id,
  keyword,
  source,
  url,
  canonical_url,
  title,
  body,
  author,
  channel_url,
  score,
  metric,
  views,
  published,
  asset_path,
  archived_at,
  deleted_at,
  created_at,
  updated_at
from public.items
where deleted_at is null;

comment on view public.live_items is 'Read-only projection for the public live deployment (no user_id, no trash).';

grant select on public.live_items to anon;

create or replace view public.live_source_status as
select
  source,
  checked_at,
  ok,
  count,
  error
from public.source_status;

comment on view public.live_source_status is 'Read-only source health for the public live deployment.';

grant select on public.live_source_status to anon;
