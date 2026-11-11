---
title: Public Data Collector Integration Guide
version: 1.0.0
last_reviewed: 2026-11-11
language: en
scope: Thailand-focused social, news, trend, and open-data monitoring
artifact_type: implementation-runbook
status: implementation-reference; endpoints must be smoke-tested in deployment environment
---

# Public Data Collector: Agent Integration Guide

> **For coding agents:** This is an implementation specification, not a claim that every endpoint is guaranteed to be available from every IP at every time. Validate each source using the provided smoke tests before adding it to production. Do not invent undocumented endpoints, authenticated credentials, access privileges, data coverage, or licensing rights.

## 0. Mission and acceptance criteria

Build a **Thailand-focused, low-cost public-data monitoring pipeline** that observes news, trending topics, selected public social posts, channel uploads, advertising intelligence, and official datasets. Prioritize **free, anonymous, documented programmatic interfaces**. Treat manual-only or approval-restricted services as separate workflows; do not silently scrape them.

**Definition of done**

1. Each enabled source has a documented adapter, a successful smoke test, and a source-specific checkpoint policy.
2. Every collected record is normalized into the common event schema below and preserves a link to its original source.
3. Jobs deduplicate records and survive restarts, transient failures, pagination, and rate limits without data loss where supported.
4. The dashboard distinguishes social posts, news, search trends, pageviews, archival snapshots, government statistics, and advertising observations. **Never add these different units into a single raw engagement total.**
5. Data provenance, timestamps, limitations, and ingestion health are observable.
6. No collection relies on bypassing login, CAPTCHAs, platform restrictions, anti-bot defenses, or unpublished private API endpoints.
7. All licenses and platform terms are reviewed separately before commercial redistribution or long-term storage of content.

**Not in scope:** access to private content; unrestricted Facebook/Instagram/TikTok APIs; guaranteed comprehensive coverage of Thai social conversation; evasion of rate limits; purchase of API services.

## 1. Source inventory and deployment decision

**Access labels**: `ANON` = no login/key required by documented public path; `CONDITIONAL` = host/dataset/config dependent; `APPROVAL` = login, token, or approval needed for API; `MANUAL` = official public UI, no verified general-purpose public machine API. `ANON` is not a redistribution license.

| ID | Source | Data type | Access | Primary interface | Production recommendation |
|---|---|---|---|---|---|
| S01 | Bluesky AppView | Public posts and post metrics | ANON | JSON HTTP | Enable for keyword discovery |
| S01b | Bluesky Jetstream | Network event stream | ANON | WebSocket / archive client | Enable only with stream processing capacity |
| S02 | GDELT | News article metadata and event datasets | ANON | DOC API, bulk ZIP | Enable; strong news source |
| S03 | Google Trends Trending Now | Rising search topics | ANON for UI/RSS | RSS / CSV export | Enable with feed health checks |
| S04 | Hacker News / Algolia | Stories and comments | ANON | JSON HTTP | Enable for technology monitoring |
| S05 | Mastodon | Public posts and hashtag timelines | CONDITIONAL | JSON HTTP by instance | Enable per authorized/accessible instance |
| S06 | YouTube channel feed | New/updated uploads | ANON | Atom RSS / WebSub | Enable for a configured channel list |
| S07 | Wikimedia Analytics | Wiki pageviews and top pages | ANON, rate-limited | JSON HTTP | Enable for interest signals |
| S08 | Common Crawl | Historical web snapshots | ANON | CDX index + WARC | On-demand enrichment, not live polling |
| S09 | Thailand data.go.th | Open government datasets | CONDITIONAL | CSV/JSON/XLSX; registered API | Enable by dataset, not as generic social feed |
| S10 | RSSHub (self-hosted) | Feeds from supported routes | CONDITIONAL by route | RSS/Atom | Enable only for tested, permitted routes |
| S11 | Meta Ad Library | Public advertisement observations | UI public; API APPROVAL and limited scope | Official UI / restricted API | Manual-first; separately gate API |
| S12 | TikTok Creative Center | Public hashtag trend displays | UI partially public; deep views login | Official UI | Manual/research-first; no assumed anonymous API |
| S13 | Google News RSS | News query feed | ANON feed; use rights require review | RSS | Optional: legal approval before commercial backend use |

**Recommended initial automation order:** S02 → S03 → S06 → S01 AppView → S04 → S07 → S05 → S10. Handle S08/S09 as specialist adapters and S11/S12 as manually reviewed intelligence. S13 is optional and rights-sensitive.

## 2. Baseline technical design

### 2.1 Architecture

```text
                 source registry (enable flags / keyword sets / channels)
                                      |
                   scheduler + connector worker / stream worker
                                      |
               GET / RSS / WSS / file ingest / manual observation
                                      |
                validation -> parsing -> Thai-aware normalization
                                      |
            deduplication -> provenance -> storage -> enrichment
                                      |
               trend jobs / topic clustering / search / dashboard

                  checkpoint store + audit logs + health metrics
```

For a lightweight implementation, prefer a single backend service, SQLite/Postgres, and scheduled workers. Do not add a broker or distributed queue until throughput or reliability measurements justify it.

### 2.2 Suggested directory layout

```text
src/
  collectors/
    types.ts
    registry.ts
    http.ts
    rss.ts
    bluesky-search.ts
    bluesky-jetstream.ts
    gdelt.ts
    google-trends.ts
    hacker-news.ts
    mastodon.ts
    youtube.ts
    wikimedia.ts
    common-crawl.ts
    data-go-th.ts
    rsshub.ts
  observations/
    meta-ad-library.ts          # manual/approved sources only
    tiktok-creative-center.ts   # manual/approved sources only
  pipeline/
    normalize.ts
    dedupe.ts
    checkpoints.ts
    enrich.ts
    persist.ts
  tests/
    contracts/
    fixtures/
```

File names are a proposed design, not required existing files. Implement in the target repository's established language and style; do not duplicate services already in place.

### 2.3 Canonical normalized record

Use JSON or an equivalent typed model. Distinguish `content`, `signal`, and `dataset`.

```json
{
  "source": "bluesky",
  "source_item_id": "at://did:plc:.../app.bsky.feed.post/...",
  "record_kind": "content",
  "content_type": "social_post",
  "url": "https://bsky.app/profile/example.bsky.social/post/EXAMPLE",
  "title": null,
  "text": "Example public post",
  "author_id": "did:plc:...",
  "author_display": "example.bsky.social",
  "language": "th",
  "market_hint": "TH",
  "published_at": "2026-11-11T06:00:00Z",
  "observed_at": "2026-11-11T06:05:00Z",
  "engagement": {"likes": 0, "reposts": 0, "replies": 0, "views": null},
  "numeric_signal": null,
  "signal_unit": null,
  "keywords_matched": ["example"],
  "raw_source_ref": "storage://raw/bluesky/<opaque-id>",
  "is_deleted": false,
  "metadata": {"source_instance": "public.api.bsky.app"}
}
```

Required rules:

- `source + source_item_id` must be a stable unique key; on new observations, update mutable counters while maintaining optional historical snapshots.
- `published_at` is source-provided time; `observed_at` is the time the collector saw the record; both UTC ISO 8601.
- Preserve source URL and a permissible minimal raw response for debugging. Do not assume public availability equals permission to reproduce full content.
- `market_hint=TH` means query, publication, dataset, or configuration indicated Thailand; **it does not prove a user's residency**.
- For `record_kind=signal`, populate `numeric_signal` and `signal_unit` (e.g. `pageviews`, `trend_search_bucket`, `articles_per_bucket`). Never reinterpret Google Trends bucket labels as exact search totals.
- Store a `license_or_terms_status` in source registry (`approved`, `review_required`, `restricted`) rather than inventing a universal license.
- A deletion event or content removal must have a handling path; keep only the permitted audit information.

### 2.4 Connector contract (pseudocode)

```ts
type CollectorResult = {
  records: NormalizedRecord[];
  nextCheckpoint?: string;
  sourceFetchedAt: string;
  warnings?: string[];
};

interface Collector {
  id: string;
  smokeTest(): Promise<{ ok: boolean; message: string }>;
  collect(checkpoint?: string): Promise<CollectorResult>;
}
```

Required worker behavior: bounded retries with jitter, `Retry-After` support, conditional `ETag`/`Last-Modified` when honored, request timeouts, payload-size limit, content-type validation, checkpoint after successful durable persistence, stable deduplication, and separate metrics for `success`, `zero_results`, `blocked`, `rate_limited`, `parse_error` and `rights_review_required`.

**Suggested start-only polling defaults (engineering recommendations, not provider guarantees):** Google Trends every 15–30 minutes; GDELT every 15–30 minutes; HN / Bluesky Search every 5–15 minutes; channel RSS every 10–30 minutes; Wikimedia daily; government datasets daily/weekly by source; Common Crawl on-demand. Respect service responses and adapt rather than blindly persisting with these intervals.

---

## 3. Source-by-source integration

### S01. Bluesky — Public AppView Search API

- **Purpose:** Find public posts about keywords, brands, and hashtags.
- **Official reference:** https://docs.bsky.app/docs/api/app-bsky-feed-search-posts ; general API: https://docs.bsky.app/
- **Auth:** Public `app.bsky.*` GETs generally work at `https://public.api.bsky.app` without a token.
- **Example:**

```bash
curl -G 'https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts' \
  --data-urlencode 'q=Thailand' \
  --data-urlencode 'limit=25'
```

- **Parse:** `posts[]` → `uri`, `cid`, `author.did`, `author.handle`, `record.text`, `record.createdAt`, `likeCount`, `repostCount`, `replyCount`, `indexedAt`; retain `cursor` if returned and supported.
- **Incremental operation:** overlap short time windows, deduplicate by post URI, optionally use server-supported `since`/`until`/pagination parameters documented in the current lexicon. Do not assume any query has exhaustive recall.
- **Thailand caveat:** Thai text and Thai hashtags are useful query hints; there is no guarantee that results originate in Thailand. A language filter does not prove geography.
- **Failure modes:** request 429, index delays, paging limits, posts disappearing, and author handle changing. IDs should be based on DID/AT URI, not handles.
- **Acceptance test:** `HTTP 200`, JSON with `posts` array, at least one mapped record when query matches; `0 posts` is a valid empty result.

### S01b. Bluesky — Jetstream live network events

- **Purpose:** Live ingest of new public AT Protocol records rather than keyword search snapshots.
- **Official documentation:** https://github.com/bluesky-social/jetstream ; v2 details: https://github.com/bluesky-social/jetstream/blob/main/docs/README.md
- **Authentication:** public Jetstream servers permit anonymous WSS where offered. Host availability and public endpoint version must be checked.
- **Simple legacy/v1 WebSocket example (official public legacy host):**

```text
wss://jetstream2.us-east.bsky.network/subscribe?wantedCollections=app.bsky.feed.post
```

- **V1 shape:** JSON events such as `kind: "commit"`, `did`, `time_us`, and `commit` with `collection`, `operation`, `rkey`, `record`.
- **V2 difference:** uses `/xrpc/network.bsky.jetstream.subscribeEvents`; filters are `kinds`, `collections`, `dids` and sequence-number cursors. V1 `wantedCollections` and microsecond `time_us` cursors **are not interchangeable with v2 filters/cursors**. Use official v2 client libraries or follow v2 framing specification.
- **Processing:** filter creation events for `app.bsky.feed.post`, examine `commit.record.text`, build AT URI from `did`, `collection` and `rkey`, persist raw event identifier and cursor, and process deletions/account changes.
- **Backfill:** v1 live socket has limited lookback; v2 supports an archive/backfill path. Do not claim a v1 subscription provides full history.
- **Capacity caution:** a full-network stream can be large; apply event-kind/collection filters, bounded in-memory buffers and durable checkpoints. Implement reconnect without duplicate records.
- **Acceptance test:** connect, receive valid event, parse with current protocol version, disconnect/reconnect successfully. Do not require a positive keyword match to pass transport test.

### S02. GDELT — global news monitoring

- **Purpose:** Discover articles mentioning terms, track news volume, and optionally ingest event/bulk datasets.
- **Official reference:** https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/ ; https://www.gdeltproject.org/
- **Auth:** no key for documented public endpoints.
- **Article search:**

```bash
curl -G 'https://api.gdeltproject.org/api/v2/doc/doc' \
  --data-urlencode 'query=Thailand' \
  --data-urlencode 'mode=artlist' \
  --data-urlencode 'format=json' \
  --data-urlencode 'timespan=1d' \
  --data-urlencode 'maxrecords=50'
```

- **Time-series signal:** change `mode` to `timelinevol` and parse returned series; label the metric with GDELT's definition, not as social mentions.
- **Bulk newest pointer:** `https://data.gdeltproject.org/gdeltv2/lastupdate.txt`. Parse listed file URLs and download only needed files; Events, Mentions and GKG schemas differ.
- **Parsing:** article list typically includes `articles[]` with URL, title, seen date, language/source metadata; validate actual response shape before mapping.
- **Incremental:** poll overlapping windows; dedupe by canonical article URL plus source-specific identifiers. For reliable bulk ingest, checkpoint ZIP filenames/timestamps and process every interval in order.
- **Thailand:** search Thai language terms or news about Thailand. `sourcecountry:thailand` within `query` filters by the source's country metadata, not the article topic's nationality.
- **Limits/rights:** published API can throttle requests; treat 429/503 and errors conservatively. Copyright remains with original article publishers; don't treat article search results as permission to republish full texts.
- **Acceptance test:** DOC API yields valid JSON (an empty result may be valid), latest pointer is parseable; full article ingestion is not required for the initial test.

### S03. Google Trends — Trending Now RSS/CSV

- **Purpose:** Discover spikes in Google search interest by location.
- **Official reference:** https://support.google.com/trends/answer/3076011?hl=en
- **Public UI:** https://trends.google.com/trending?geo=TH
- **RSS candidate URL (verify response on deployment):** `https://trends.google.com/trending/rss?geo=TH`
- **Auth:** the UI and RSS export are accessible without an API key; availability of the underlying feed can vary.
- **UI workflow:** choose Thailand → select 4h/24h/48h/7d, category/status filters → Export → RSS or CSV.
- **Programmatic smoke test:**

```bash
curl -L -i 'https://trends.google.com/trending/rss?geo=TH'
```

- **Parse:** RSS `item.title`, publication time, source link, and any namespace-specific search-volume/news fields present in the XML. Do not hard-code optional namespace fields without a sample fixture.
- **Normalization:** `record_kind=signal`, `content_type=search_trend`; keep volume as a **bucket/string** if that's what is provided, not a precise number; capture `geo=TH` in metadata.
- **Caveats:** Exported UI filters may not map exactly to a manually constructed RSS URL; feed results may represent a subset of visible UI. Trending Now is not an arbitrary historical keyword time-series API.
- **Acceptance test:** XML parses as RSS; record country and fetch timestamp; fail gracefully if service returns HTML, consent/interstitial page or non-200.

### S04. Hacker News — Algolia Search API

- **Purpose:** Track technology product and community discussions.
- **Reference:** https://hn.algolia.com/api
- **Auth:** no key for public search API.
- **Search stories by newest:**

```bash
curl -G 'https://hn.algolia.com/api/v1/search_by_date' \
  --data-urlencode 'query=OpenAI' \
  --data-urlencode 'tags=story' \
  --data-urlencode 'hitsPerPage=25'
```

- **Search comments:** set `tags=comment`.
- **Incremental time filter:** `numericFilters=created_at_i>UNIX_SECONDS` (and optionally `created_at_i<...`). `search` sorts by relevance; `search_by_date` sorts by recency.
- **Parse:** `hits[]`, `objectID`, `title`, `story_title`, `url`, `story_url`, `comment_text`, `points`, `num_comments`, `author`, `created_at`, `created_at_i`, `nbPages`.
- **Caveats:** comment text is HTML; sanitize for display. Comments and stories have different fields. Rate limits can change; respect 429 and published service rules. Popular HN ≠ popular in Thailand.
- **Acceptance test:** JSON `hits` array, mapped stable `objectID`, a successful `page=0` call and a controlled empty query.

### S05. Mastodon — public instance timelines

- **Purpose:** Read public statuses or hashtag timelines visible to a selected server.
- **Official reference:** https://docs.joinmastodon.org/methods/timelines/
- **Auth:** conditional: some instances disable unauthenticated timeline access or enforce server restrictions.
- **Public timeline:**

```bash
curl -i 'https://mastodon.social/api/v1/timelines/public?limit=20'
```

- **Hashtag timeline:**

```bash
curl -i 'https://mastodon.social/api/v1/timelines/tag/Thailand?limit=20'
```

- **Parse:** `id`, `uri`, `url`, `content` (HTML), `created_at`, `account`, `favourites_count`, `reblogs_count`, `replies_count`, `visibility`.
- **Pagination:** honor response `Link` headers and available `since_id`, `min_id`, `max_id` parameters. Deduplicate on canonical URI; remote federated copies may appear on multiple instances.
- **Multi-instance:** configure a small, explicit allowlist of public instances; do not claim that one instance's timeline is the global Fediverse. Inaccessible instances must be marked `blocked`, not scraped using a workaround.
- **Acceptance test:** the chosen instance returns 200 JSON statuses without auth; if 401/403, disable anonymous adapter or use an authorized integration path.

### S06. YouTube — channel uploads Atom feed and WebSub

- **Purpose:** Detect new/updated videos for known YouTube channel IDs. **Not** keyword search across all YouTube.
- **Official reference:** https://developers.google.com/youtube/data/guides/push_notifications
- **Pollable Atom feed:**

```text
https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID
```

- **WebSub topic URL documented in Oct 2026:**

```text
https://www.youtube.com/xml/feeds/videos.xml?channel_id=CHANNEL_ID
```

**Important:** These two paths differ. Use the `xml/feeds` topic for WebSub subscription as documented by Google; do not blindly reuse the pollable URL as the hub topic.

- **Polling:** GET feed → parse Atom `entry` → collect `yt:videoId`, `yt:channelId`, title, link, published, updated; dedupe by video ID and retain last updated time.
- **Push:** expose public HTTPS callback → POST subscription form to `https://pubsubhubbub.appspot.com/subscribe` with `hub.mode=subscribe`, `hub.topic` set to WebSub topic, and `hub.callback` set to your HTTPS endpoint → respond to verification challenge → accept Atom notifications. Check current renewal/lease requirements.
- **Limitations:** upload/update notifications only, not all views/comments/likes; discovering new channels or arbitrary YouTube text search generally needs another permitted mechanism such as YouTube Data API and quota.
- **Acceptance test:** given an existing channel ID, valid Atom XML; optional WebSub webhook subscription verifies and receives a test update.

### S07. Wikimedia Analytics API — Wikipedia interest signals

- **Purpose:** Pageviews or top pages as indicators of information-seeking interest, including Thai Wikipedia.
- **Official reference:** https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/ ; https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/reference/page-views.html
- **Auth:** can be used without credentials but **Wikimedia introduced API rate-limiting changes in 2026**.
- **Daily pageviews per article (example):**

```text
https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/th.wikipedia.org/all-access/all-agents/ประเทศไทย/daily/20261001/20261031
```

Encode page title as a URL path segment, replacing spaces appropriately. Confirm that the page exists and the API's title normalization.

- **Other operations:** list top pages by project/country; consult current reference for each parameter combination.
- **Headers:** a descriptive `User-Agent` with a way to contact the operator, e.g. `ThailandTrendCollector/1.0 (https://your-project.example/contact)` **using a real operator-controlled contact URL**. Never ship fake contact data. Observe current concurrency/rate-limit guidance and `Retry-After`.
- **Normalization:** `record_kind=signal`, `signal_unit=pageviews`, series granularity daily/monthly, market classification based on wiki project (e.g. `th.wikipedia.org` = Thai-language wiki, not necessarily Thai viewers).
- **Caveats:** aggregate pageviews are not social conversations, unique people or sentiment.
- **Acceptance test:** a valid existing title returns time-series JSON; 429 must be retried per provider guidance without bypassing limits.

### S08. Common Crawl — historical web archive

- **Purpose:** Recover historic webpage captures, discover older coverage or website changes. Not suitable as a real-time news source.
- **Official reference:** https://index.commoncrawl.org/ ; https://commoncrawl.org/get-started
- **Auth:** no key for public index and HTTPS archive downloads.
- **Discover current crawl collections:**

```bash
curl 'https://index.commoncrawl.org/collinfo.json'
```

- **Select latest index dynamically:** the catalog contains `id` and `cdx-api`. Do **not** hard-code a stale `CC-MAIN-YYYY-WW` index forever.
- **Query a selected index:**

```text
https://index.commoncrawl.org/CC-MAIN-2026-43-index?url=example.com%2F*&output=json
```

This crawl ID is an **example known as of the document date**, not a guaranteed latest index. Use the `cdx-api` URL from `collinfo.json` when possible.

- **Parse:** newline-delimited JSON index records with `url`, `timestamp`, `status`, `mime`, `filename`, `offset`, `length`, `digest`.
- **Fetch record:** construct `https://data.commoncrawl.org/{filename}` and GET with `Range: bytes={offset}-{offset+length-1}`; parse WARC using an established parser such as `warcio` rather than treating the response as plain text.
- **Caveats:** no guarantee the target page was crawled; snapshots may be stale or incomplete; bulk downloads can be huge and incur infrastructure/network costs. Copyright and privacy obligations still apply.
- **Acceptance test:** catalog loads, query returns index records or an explicit no-match, and a selected WARC byte range returns a parseable record.

### S09. Thailand data.go.th — government open data

- **Purpose:** Import official datasets for analytical context: economy, demographics, agencies, geographical statistics, and other published open data. Not a social-post feed.
- **Portal:** https://data.go.th/
- **Official API onboarding:** https://opend.data.go.th/register_api/ ; https://data.go.th/pages/data-go-th-api_v2
- **Auth:** downloadable resources may be anonymous; the portal's Data API onboarding explicitly describes registration and token issuance for some API access.
- **Manual discovery workflow:** search dataset on portal → inspect metadata, publisher, update frequency, license, geographic granularity, resource links → download an open CSV/JSON/XLSX resource if available.
- **Automated workflow:** save the **actual** download/resource URL from the dataset metadata; fetch conditional on cache/updated metadata when supported; parse according to the dataset schema. Only use an API after registering and following the current service-specific instructions.
- **Do not invent:** a universal anonymous `data.go.th` API endpoint, universal CKAN route, or guaranteed JSON field names across datasets.
- **Data quality checks:** validate header names and Thai encoding, date formats (Buddhist Era vs Gregorian), geographic units, source organization, revision dates and licensing conditions.
- **Normalization:** `record_kind=dataset`; store dataset ID, agency, resource URL, version, observation period, and geographic unit separately from collection timestamp.
- **Acceptance test:** one named public dataset can be downloaded and parsed reproducibly, with its source license and update timestamp recorded.

### S10. RSSHub — self-hosted RSS route aggregator

- **Purpose:** Create usable feeds for platforms/websites covered by a maintained RSSHub route. It is software, not a universal provider-owned dataset.
- **Docs:** https://docs.rsshub.app/ ; deployment reference: https://github.com/RSSNext/rsshub-docs/blob/main/src/deploy/index.md
- **Cost:** open-source and free to run; hosting/network/browser automation may cost money.
- **Basic self-hosted launch:**

```bash
docker run -d --name rsshub -p 127.0.0.1:1200:1200 diygod/rsshub
```

Visit `http://127.0.0.1:1200`. For routes requiring a browser, consult the documented Chromium-bundled image and resource requirements.

- **Per-route integration:** locate an explicit route in current docs → read path, parameters, dependencies, auth needs and anti-scraping notes → test at self-hosted base URL → parse RSS/Atom → checkpoint GUID/link and publication time.
- **No universal guarantees:** some routes need login or other secrets; some break when sites change; some are subject to permission restrictions. Do not assume an RSSHub route makes Facebook, Instagram, or TikTok freely accessible in a legitimate, stable way.
- **Security:** do not expose a public RSSHub instance without access controls/rate limits; do not log secret cookies or credentials; prefer allowlisted routes for internal backend use.
- **Acceptance test:** at least one **documented and permitted** route returns parseable XML from local RSSHub and is ingested with deduplication.

### S11. Meta Ad Library — ads intelligence, limited API

- **Purpose:** Manually inspect active ads from advertisers/brands and supported transparency categories.
- **Official public page:** https://www.facebook.com/ads/library/
- **Official API information:** https://www.facebook.com/ads/library/api/
- **UI workflow:** select country `Thailand` → choose appropriate ad category → search brand or advertiser → review active ads, creative, platform, start date, and library ID → capture only permitted metadata plus original Ad Library link.
- **API scope (documented):** access requires an approved/authenticated Meta setup; public API coverage emphasizes social issue/election/political ads and other supported categories (including broader UK/EU ads). Do **not** assume it provides all standard commercial Thai ads via an anonymous endpoint.
- **Recommended implementation:** `manual_observation` record with `record_kind=advertising_observation`, reviewer, timestamp, selected ad/library ID, public URL, metadata and rights status. If approved credentials are granted later, implement a separate authenticated adapter using **current Meta docs only**.
- **Prohibited assumptions:** scraping internal GraphQL endpoints, spoofing sessions, silently evading login/CAPTCHA, claiming impression/spend figures are available for all advertisements.
- **Acceptance test:** reviewer can record a reproducible publicly visible ad observation and its timestamp; API adapter stays disabled without approved credentials and verified coverage.

### S12. TikTok Creative Center — trend research

- **Purpose:** Discover popular hashtags, categories, regions, and public creative examples for Thailand.
- **Public landing page:** https://ads.tiktok.com/creative/creativeCenter/trends?deviceType=pc&locale=th&region=TH
- **Official help:** https://ads.tiktok.com/resources/help/article/how-to-use-trends
- **UI workflow:** select `Thailand` → choose hashtag category and date range → inspect visible posts/views and trends → sign in when analytics detail is required → record observed metrics together with date, region, and filter selections.
- **Auth:** some high-level public information is visible anonymously; official help instructs users to log in for Trends analytics details. There is **no general anonymous public Creative Center trends API established here**.
- **Recommended implementation:** manual / rights-reviewed observation importer, with optional approved integration if TikTok documents an authorized API for the desired fields.
- **Metric warning:** views and post counts shown in Creative Center depend on product-defined scope, date range, region and availability; do not assume exhaustive lifetime TikTok counts.
- **Do not implement:** private endpoint reverse engineering, login bypass, headless anti-bot evasion or fabricated official endpoints.
- **Acceptance test:** analyst can capture source URL, selected filters, observation timestamp, hashtag and visible values; automation remains disabled until an authorized access method is established.

### S13. Google News RSS — query feed, legally gated

- **Purpose:** Obtain article discovery links from Google News keyword searches.
- **User-facing page:** https://news.google.com/
- **Example RSS search pattern (test before enabling):**

```text
https://news.google.com/rss/search?q=Thailand&hl=th&gl=TH&ceid=TH:th
```

- **Parameters commonly used:** `q` query, `hl` display language, `gl` country, `ceid` edition. These URL patterns are commonly used but should not be treated as a promised permanent API contract.
- **Parsing:** RSS `title`, `link`, `pubDate`, `source`, `guid`; preserve Google News redirect URL and publisher attribution; resolve to original publisher only by a permitted method.
- **Rights warning:** historical Google News service terms contain personal/non-commercial restrictions and restrictions on automated copying/redisplay. Their age and exact applicability need legal/terms review; **do not enable commercial redistribution solely because the RSS feed responds to unauthenticated GET**. Prefer GDELT and directly licensed publisher RSS where the use case requires a commercial backend.
- **Acceptance test:** RSS fetch/parsing passes; production flag remains `rights_review_required` unless the intended use has been approved.

---

## 4. Practical smoke-test script (read-only public HTTP sources)

The following minimal Python script tests a few anonymous HTTP sources. It **does not** test WebSockets, provider-specific licensing, TikTok/Meta permissions, RSSHub routes, or all schema mappings. It avoids third-party Python packages.

```python
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from xml.etree import ElementTree as ET
import json

SOURCES = {
    "bluesky": (
        "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?"
        + urlencode({"q": "Thailand", "limit": 5}), "json"
    ),
    "gdelt": (
        "https://api.gdeltproject.org/api/v2/doc/doc?"
        + urlencode({"query": "Thailand", "mode": "artlist", "format": "json", "timespan": "1d", "maxrecords": 5}), "json"
    ),
    "hacker_news": (
        "https://hn.algolia.com/api/v1/search_by_date?"
        + urlencode({"query": "Thailand", "tags": "story", "hitsPerPage": 5}), "json"
    ),
    "mastodon": (
        "https://mastodon.social/api/v1/timelines/public?limit=5", "json"
    ),
    "google_trends_rss": (
        "https://trends.google.com/trending/rss?geo=TH", "xml"
    ),
    "common_crawl_catalog": (
        "https://index.commoncrawl.org/collinfo.json", "json"
    ),
}

# Replace with a real contact URL before production use.
HEADERS = {"User-Agent": "PublicDataCollectorDev/0.1 (local smoke test)"}

for name, (url, fmt) in SOURCES.items():
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=20) as res:
            payload = res.read(2_000_000)
            status = res.status
            ctype = res.headers.get("Content-Type", "")
        parsed = json.loads(payload) if fmt == "json" else ET.fromstring(payload)
        print(f"OK   {name}: HTTP {status}, {ctype}, parsed={type(parsed).__name__}")
    except (HTTPError, URLError, ValueError, ET.ParseError, TimeoutError) as exc:
        print(f"FAIL {name}: {type(exc).__name__}: {exc}")
```

**Important:** this smoke test makes real network calls when run by an agent with network access. It is provided for the user's environment; it was not executed in this artifact-generation environment. A successful transport test does not prove commercial reuse rights or data coverage.

## 5. Optional operational examples

### 5.1 Schedule recommendations

| Source | Suggested initial cadence | State/cursor |
|---|---|---|
| Bluesky Search | 5–15 min | last seen URI + overlap window |
| Jetstream | continuous | versioned stream cursor + last stored event |
| GDELT DOC | 15–30 min | overlap window + URL dedupe |
| GDELT bulk | per available batch | last successful batch filename |
| Google Trends | 15–30 min | feed item ID/title+time + snapshot |
| Hacker News | 5–15 min | `created_at_i` overlap + objectID |
| Mastodon | 5–15 min | per-instance timeline IDs |
| YouTube RSS | 10–30 min or WebSub | channel ID + video ID/update |
| Wikimedia | daily | article + date |
| Common Crawl | on demand | collection ID + record digest |
| data.go.th | per dataset cadence | publisher resource version/datestamp |
| RSSHub | 15–60 min by route | feed GUID/link + date |
| Meta / TikTok | scheduled human review | reviewer + observed-at + filters |
| Google News | disabled until rights approved | feed GUID + time |

These cadences are **design defaults**, not provider-published quotas.

### 5.2 Thai-language processing

- Store Unicode text in UTF-8 and normalize to NFC. Keep unmodified source text in the permitted raw record.
- Recognize Thai/English mixed text, multiple spellings/transliterations, hashtags, company aliases and spacing variations.
- Use a keyword dictionary with aliases and exclusions; track why a match was made.
- Apply Thai-specific tokenization/NLP only after reliable collection; do not let AI sentiment overwrite source truth.
- Preserve source-language and inferred language separately when they differ.
- Avoid inferring individual nationality, residence, politics, or other sensitive characteristics from text.

### 5.3 Analytics semantics

- `mention_count`: count of **collected** records mentioning a term per selected source, not all online conversation.
- `news_volume`: count of GDELT article records in a documented window, subject to indexing limitations.
- `search_trend`: Google Trends-defined trend/bucket, **not** absolute search market share.
- `wiki_interest`: Wikipedia pageview totals, **not** number of distinct people.
- `engagement`: source-specific counters at an observed timestamp; never compare a like and a pageview as if equivalent.
- `trend_score`: optional calculated dashboard metric, with published explicit weighting and normalization; never claim provider-endorsed values.
- Separate `TH-related content`, `Thai-language content`, and `Thai-located audience` — these are not interchangeable.

### 5.4 Failure matrix

| HTTP/event state | Action |
|---|---|
| 200 but empty | Treat as successful empty response, unless provider contract says otherwise |
| 200 HTML instead of expected JSON/XML | Mark schema/consent/interstitial failure; don't parse HTML as API output |
| 401/403 | Disable or require approved auth; do not bypass |
| 404 | Confirm endpoint/resource; disable stale resource if gone |
| 429 | Respect `Retry-After`, exponential backoff, reduce throughput |
| 5xx / timeout | Retry with bounded jitter; alert after repeated failures |
| malformed record | Quarantine record, preserve minimal diagnostic fields |
| deleted event | Apply source-specific deletion/tombstone policy |
| stale cursor | Reconcile via documented backfill, if available; expose gaps |
| license uncertain | Stop publication/redistribution until approved |

## 6. Source registry template

```yaml
sources:
  bluesky_search:
    enabled: true
    access: anonymous
    mode: http_json
    search_terms: ["Thailand"]
  bluesky_jetstream:
    enabled: false
    access: anonymous
    mode: websocket
    protocol: v1 # explicitly select v1 or v2 and keep cursor formats separate
  gdelt:
    enabled: true
    access: anonymous
    mode: http_json
    search_terms: ["Thailand"]
  google_trends_th:
    enabled: true
    access: anonymous
    mode: rss
    geo: TH
  hacker_news:
    enabled: true
    access: anonymous
    mode: http_json
    search_terms: ["Thailand"]
  mastodon:
    enabled: false
    access: conditional_anonymous
    instances: ["mastodon.social"]
  youtube_channels:
    enabled: false
    access: anonymous
    channel_ids: [] # add legitimate UC... channel IDs
  wikimedia:
    enabled: false
    access: anonymous_rate_limited
    project: th.wikipedia.org
    pages: []
  common_crawl:
    enabled: false
    mode: on_demand_archive
  thailand_open_data:
    enabled: false
    datasets: [] # explicit, license-checked dataset resource URLs
  rsshub:
    enabled: false
    base_url: "http://127.0.0.1:1200"
    routes: [] # documented, authorized, tested routes only
  meta_ad_library:
    enabled: false
    mode: manual_observation
  tiktok_creative_center:
    enabled: false
    mode: manual_observation
  google_news:
    enabled: false
    mode: rss
    rights_status: review_required
```

## 7. Agent execution checklist

Use this exact order when integrating into an existing codebase:

- [ ] Inspect the current repository, language, ORM, job scheduler, logging and test conventions. Avoid unnecessary dependencies.
- [ ] Read source docs listed above and check for deprecations, changed URL formats, authentication requirements, availability, licensing and terms.
- [ ] Run one read-only smoke test per candidate; save scrubbed example fixtures and HTTP status/content type.
- [ ] Agree on allowed content storage and redistribution rules before production collection.
- [ ] Implement the canonical schema and deduplication keys; add source provenance and ingestion timestamps.
- [ ] Implement the **first three simplest permitted adapters** (recommended GDELT, HN, Bluesky Search) and their contract tests.
- [ ] Add RSS parsing for Google Trends and YouTube; keep feed-specific fields rather than assuming identical XML schemas.
- [ ] Add per-source worker scheduling/checkpoints/backoff/observability.
- [ ] Add Wikimedia and Mastodon with their access restrictions; then optional specialist adapters.
- [ ] Keep Meta and TikTok manual-only until official scope and approvals meet requirements.
- [ ] Verify end-to-end records, dedupe, updates, cursor replay, deleted items, retries and dashboard labels.
- [ ] Produce a report of what is **working**, **untested**, **blocked by approval**, and **not supported**, with evidence and no invented coverage percentages.

**Required output from implementing agent:** `INTEGRATION_REPORT.md` containing endpoint tested, test timestamp, status, fields observed, ingest count, license decision, rate-limit response, known gaps, and next action for every source.

## 8. Official references and verification notes

These are the primary references used to prepare this guide on **2026-11-11**. Provider behavior may change after that date.

1. Bluesky AppView: https://docs.bsky.app/ ; https://docs.bsky.app/docs/api/app-bsky-feed-search-posts
2. Jetstream v2: https://github.com/bluesky-social/jetstream ; https://github.com/bluesky-social/jetstream/blob/main/docs/README.md ; v1 compatibility: https://github.com/bluesky-social/jetstream-legacy
3. GDELT DOC 2.0: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/ ; https://data.gdeltproject.org/gdeltv2/lastupdate.txt
4. Google Trends Trending Now help: https://support.google.com/trends/answer/3076011?hl=en
5. Hacker News Algolia: https://hn.algolia.com/api
6. Mastodon timelines: https://docs.joinmastodon.org/methods/timelines/ ; https://docs.joinmastodon.org/client/public/
7. YouTube WebSub: https://developers.google.com/youtube/data/guides/push_notifications
8. Wikimedia Analytics: https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/ ; rate-limit policy: https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits
9. Common Crawl: https://commoncrawl.org/get-started ; https://index.commoncrawl.org/
10. Thailand open data: https://data.go.th/ ; https://opend.data.go.th/register_api/ ; https://data.go.th/pages/data-go-th-api_v2
11. RSSHub deployment: https://github.com/RSSNext/rsshub-docs/blob/main/src/deploy/index.md
12. Meta Ad Library: https://www.facebook.com/ads/library/ ; https://www.facebook.com/ads/library/api/
13. TikTok Creative Center: https://ads.tiktok.com/creative/creativeCenter/trends?deviceType=pc&locale=th&region=TH ; https://ads.tiktok.com/resources/help/article/how-to-use-trends
14. Google News: https://news.google.com/ ; legacy terms page (verify current applicability): https://www.google.com/intl/en_us/terms_google_news.html

### Confidence and validation status

- **High confidence (documentation):** Bluesky public GETs; Jetstream v1/v2 distinction; GDELT DOC API; Mastodon timeline access variations; YouTube WebSub topic path; Wikimedia 2026 rate-limit policy; Common Crawl catalog/index; Meta API scope; TikTok login requirement for detailed analytics.
- **Medium confidence / dynamic interfaces:** Google Trends RSS URL, public RSSHub routes, Google News RSS URL parameters. Treat example patterns as candidates that require a real HTTP smoke test.
- **Unknown until deployment test:** live availability from the chosen network, real per-source effective rate limits, completeness of Thai content, coverage of specific brands, and production legal eligibility for commercial redistribution.

**Important separation:** An externally readable data source is not automatically an open license, a contractually supported API, a comprehensive dataset, or a guaranteed-free production service.
