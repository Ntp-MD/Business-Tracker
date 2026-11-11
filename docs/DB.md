# Database (Supabase)

> **Current mode:** `server.py` uses `db.py` when `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` + `SUPABASE_USER_ID` are set; otherwise it uses local `data/*.json`. The browser never gets the service key. Static `/live` cannot read these tables directly because RLS requires `authenticated` — that needs Supabase Auth + anon key (planned in `MIGRATION-NEXT.md`), or the hosted API.
>
> Schema: `supabase/migrations/20261110000000_init.sql`. Apply it in the Supabase SQL editor (or `supabase db push`). Postgres 15, RLS on every table (`user_id = auth.uid()`).

## Mapping from `data/*.json`

| JSON today | Table | Notes |
|---|---|---|
| `items.json` | `items` | one row per `(keyword, canonical_url)`; `deleted_at is null` |
| `archive.json` | `items` | same row, `archived_at` set |
| `trash.json` | `items` | same row, `deleted_at` set; purge after 7 days |
| `profiles.json` | `profiles` | `keywords` / `sources` stay `text[]` |
| `analysis.json`, `index.json` | `keyword_stats` | derived cache, recompute after each fetch |
| `sources.json` | `source_status` | last result per source |
| thumbnails in `assets/` | Storage bucket `thumbnails` | path `<user_id>/<file>.jpg` stored in `items.asset_path` |

Dropped on purpose: `created` (empty string in old data; use `published` / `created_at`), and localStorage-only data (history, page, theme).

## Dedup / upsert

```sql
insert into items (keyword, source, url, canonical_url, title, body, author, channel_url, score, metric, views, published, asset_path)
values (:keyword, :source, :url, :canonical_url, :title, :body, :author, :channel_url, :score, :metric, :views, :published, :asset_path)
on conflict (user_id, keyword, canonical_url) do update
set title = excluded.title, body = excluded.body, author = excluded.author,
    channel_url = excluded.channel_url, score = excluded.score, metric = excluded.metric,
    views = excluded.views, published = excluded.published, asset_path = excluded.asset_path,
    updated_at = now();
```

Soft delete instead of moving rows:

```sql
update items set archived_at = now() where user_id = auth.uid() and id = :id;  -- archive
update items set deleted_at = now() where user_id = auth.uid() and id = :id;   -- trash
update items set archived_at = null where id = :id;                             -- restore
```

## Queries the dashboard needs

```sql
-- All items / archive / trash for a keyword, sorted
select * from items
where keyword = :q and archived_at is null and deleted_at is null
order by score desc;

-- Counts per keyword (replaces by_source math)
select * from v_keyword_totals where keyword = :q;

-- Text filter without a Thai tokenizer
select id, title from items
where title ilike '%' || :q || '%' or body ilike '%' || :q || '%';
```

`pg_trgm` gives `ilike` a GIN index on `title`. Postgres full-text search has no Thai dictionary, so do not use `to_tsvector` for Thai.

## Wiring the app

`db.py` is a PostgREST adapter. Set in `.env.local`:

```
SUPABASE_URL=https://ajjjaqjlxutuqigthisy.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...   # server only
SUPABASE_USER_ID=<auth user uuid>
```

With all three set, `server.py` reads/writes Supabase instead of `data/*.json`; with any missing it keeps the JSON files (safe fallback). Import the old data once:

```
python scripts/import_to_supabase.py --dry-run
python scripts/import_to_supabase.py              # or --create-user you@example.com --password '...'
```

Thumbnails are copied to `storage://thumbnails/<user_id>/<file>.jpg`; `items.asset_path` keeps the existing `assets/<file>.jpg` value so the local page keeps working. In DB mode `GET /assets/<file>.jpg` is proxied from the bucket (local `assets/` is only a fallback when `SUPABASE_STRICT=0`), and every new fetch uploads its thumbnail.

`SUPABASE_STRICT=1` (default): a Supabase error raises and the request fails loudly instead of writing local JSON. Set `0` only for a planned offline run.

## Notes

- Fetcher (`server.py` / Playwright) should use the service role key; the browser client uses anon key and RLS.
- Realtime is off by default; enable it only for `items` if another device must see fetches live.
- Trash purge: `pg_cron` job at the bottom of the migration (commented).
- Local single-user mode: `user_id` defaults to `auth.uid()`, so no code change is needed once auth is added.
