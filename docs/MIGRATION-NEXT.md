# Migration Plan — Next.js + Supabase + TypeScript worker

> **Status (2026-11-11): PLAN ONLY — ยังไม่เริ่ม rewrite.** แอปปัจจุบันยังเป็น
> Python `server.py` + static HTML (`/` mock, `/live` live) และ deploy ได้แล้ว.
> เอกสารนี้เป็น rail สำหรับอนาคต; ห้ามเริ่มโดยไม่ทำ Phase 0.
>
> เป้าหมาย: ย้ายจาก Python `server.py` + static HTML ไป stack ที่เข้ากับ Vercel/Supabase
> โดย **คง `/` = mockup และ `/live/` = live แยกกันเสมอ**
>
> ทุกเฟสต้องผ่าน gate ก่อนไปเฟสถัดไป; ห้ามเพิ่ม feature ใหม่ระหว่าง migrate จนกว่า parity จะครบ

---

## 0. Decisions ที่ล็อกแล้ว

| หัวข้อ | ตัดสิน |
|---|---|
| Framework | Next.js (App Router) + TypeScript |
| Host frontend | Vercel |
| Data/Auth/Storage | Supabase (Postgres + Auth + Storage + RLS) |
| Worker | Node + TypeScript + Playwright (Render/Fly/VPS) |
| Routes | `/` = mockup, `/live` = live; ห้ามรวม |
| Mock | sample/fixture เท่านั้น; ห้ามเรียก Supabase/worker |
| Search Now | enqueue job → worker; ห้ามรัน Playwright ใน Next/Vercel |
| Secrets | `SUPABASE_SERVICE_ROLE_KEY` อยู่ worker/server เท่านั้น |
| Legacy | คง `index.html` + `live/index.html` จนถึง Phase 7 |

---

## 1. Rails (กฎกันหลุด)

1. **One page per PR** — ห้าม port หลายหน้าใน PR เดียว
2. **No redesign** — CSS/รูปแบบต้องเท่าเดิม; เปลี่ยนเฉพาะที่ระบุ
3. **Parity before new features** — feature ใหม่ลง backlog ห้ามแทรก
4. **Mock แยกจริง** — ไม่มี import จาก `apps/web/lib/supabase` ใน mock route
5. **Legacy ยังรันได้** — ทุกเฟสต้องเปิด `/` และ `/live/` เดิมได้
6. **Every phase has a rollback** — feature flag หรือ revert commit
7. **No service key in browser** — ตรวจด้วย grep ก่อน merge ทุกครั้ง
8. **No Playwright in Vercel functions** — worker แยกเท่านั้น
9. **Data writes ผ่าน RLS** — web ใช้ user JWT; worker ใช้ service role
10. **ทุกPhaseต้องมี:** unit test + Playwright screenshot 1440/390 + parity checklist

---

## 2. Current baseline (ก่อนเริ่ม)

- Live: `/live/` ใช้ `server.py` + `data/*.json` หรือ Supabase ผ่าน `db.py`
- Mock: `/` ใช้ sample data ในตัว; ไม่เรียก network
- CSS: `assets/css/variables|base|component|layout|layout-live.css`; ไม่มี inline `<style>`
- Icons: `assets/icons/*.png` (platform เท่านั้น)
- Server: `server.py` (~2.7k บรรทัด) + `db.py` adapter; collectors + API
- Tests: `tests/test_core.py` 17 tests; forced local adapter (ไม่แตะ Supabase)
- Deploy: `Dockerfile` + `render.yaml` (Render API), GitHub Pages static + static guard
- QOL ล่าสุด: filter/sort/pager/CRUD/bulk/archive/trash/toast/undo ครบใน live
- **ยังไม่มี Next/Vercel/worker** — ทั้งหมดคือเป้าหมายของ plan นี้

**Baseline actions (Phase 0)**
- Tag commit ปัจจุบัน: `git tag pre-next-migration`
- Export backup: `GET /api/export.zip` เก็บไว้นอก repo
- เก็บ screenshot ทุกหน้าของ `/live/` + `/` (1440/390)
- จด feature inventory ตาม §4
- ห้ามเริ่มแก้โค้ดก่อน baseline เสร็จ

**Exit gate 0:** มี tag, backup, screenshots, inventory ครบ

---

## 3. Target structure

```
apps/web/                    Next.js + TypeScript (Vercel)
  app/(mock)/page.tsx        mockup  /
  app/live/…                 live    /live
  components/…               shared UI
  lib/supabase/browser.ts    anon client
  lib/supabase/server.ts     server client (cookies)
  lib/api/legacy.ts          adapter คุย API เดิมช่วง migrate
  middleware.ts              auth guard /live

apps/worker/                 Node 22 + TS + Playwright
  src/collectors/youtube.ts
  src/collectors/gnews.ts
  src/collectors/tiktok.ts
  src/collectors/fbads.ts
  src/collectors/ttads.ts
  src/jobs.ts                claim/run/update jobs
  src/index.ts               poll loop

packages/shared/             types + zod
  src/item.ts, profile.ts, job.ts

supabase/migrations/…        schema/RLS
vercel.json                  root/rewrites (ถ้าจำเป็น)
render.yaml                  worker service
```

---

## 4. Feature inventory (parity checklist)

### Live `/live`
- [ ] Fetch strip: profile, keyword, sources, mode, fresh
- [ ] Search Now: start job, progress, cancel, errors
- [ ] Overview: KPI, top items, terms, ideas, charts
- [ ] Sources: cards, counts, last error/log
- [ ] Terms: list/detail
- [ ] Ideas: cards/tabs
- [ ] All items: filters (platform/date/text), sort, pager, CSV
- [ ] Items CRUD: add/edit/delete, bulk move/delete
- [ ] Archive: tabs, multi-select, restore, delete permanently
- [ ] Trash: restore/purge
- [ ] Ads: collected ads + counts
- [ ] Settings: profiles CRUD, sources toggles, keywords, export/import,
      disk status, clear/prune, theme, sessions
- [ ] Patch notes/version
- [ ] Locked pages behavior
- [ ] Responsive 390/768/1440
- [ ] Reduced motion / focus traps / aria

### Mock `/`
- [ ] ทุกหน้า sample ครบเหมือนปัจจุบัน
- [ ] ไม่เรียก network/Supabase
- [ ] ปุ่ม mock ทำงานในหน่วยความจำ
- [ ] แยก route จาก live

**กฎ:** หน้าไหนยังไม่ parity ให้ใช้ legacy UI ต่อผ่าน feature flag ห้ามตัดของเดิม

---

## 5. Data/API mapping

| Legacy | ใหม่ | หมายเหตุ |
|---|---|---|
| `POST /api/fetch` | `jobs` table + worker | web สร้าง job; worker claim |
| `GET /api/progress` | `jobs` row / Realtime | ใช้ polling ก่อน |
| `POST /api/cancel` | `jobs.cancel_requested` | worker เช็คก่อน source ถัดไป |
| `GET /api/summary?q=` | Supabase query + `keyword_stats` | หรือ RPC `summary(q)` |
| `GET /api/status` | counts + `source_status` | 1 RPC/หลาย query |
| `/api/profiles` CRUD | Supabase table ตรง (RLS) | ไม่ต้องมี API กลาง |
| `/api/items` CRUD | Supabase `items` (RLS) | soft delete/archive |
| `/api/archive` | `items.archived_at` | |
| `/api/trash` | `items.deleted_at` | purge 7 วัน |
| `/api/refresh-stats` | `jobs` kind=`refresh_views` | worker |
| `/api/export/import` | browser + Supabase Storage/JSON | |
| `GET /api/keywords` | view/query | |

**ห้าม** ให้ web เขียนด้วย service role; RLS ต้องผ่าน user JWT

---

## 6. Worker design (ประสิทธิภาพ)

- ตาราง `jobs`: `id, user_id, kind, status(queued|running|done|error|cancelled), payload jsonb, progress, total, error, created_at, started_at, finished_at`
- Worker poll ทุก 2 วิ, claim แบบ atomic:
  `update jobs set status='running', started_at=now() where id = (select id ... for update skip locked limit 1) returning *`
- 1 job = 1 keyword/source set; เขียนผลลง `items`/`source_status`
- Concurrency เริ่มที่ 1 (Playwright หนัก) แล้วเพิ่มเป็น 2 เมื่อ session แยก
- Cancel: `cancel_requested=true`; worker เช็คระหว่าง source
- Retry: error ชั่วคราว 2 ครั้ง, backoff
- Progress: อัปเดต `progress/total`
- Session login: เก็บ Playwright profile บน persistent disk ของ worker; ไม่ขึ้น Vercel

---

## 7. Phases + gates

### Phase 0 — Freeze baseline
**งาน:** tag, backup, screenshots, inventory
**Gate:** ครบ §2; ยังไม่แตะโค้ด

### Phase 1 — Scaffold only
**งาน:** `apps/web` Next + TS, `apps/worker` skeleton, `packages/shared`, env example
**ห้าม:** เปลี่ยน route ที่ deploy อยู่
**Gate:** `npm run build` ผ่าน; worker `tsc` ผ่าน; legacy ยังเปิดได้

### Phase 2 — Auth + read layer
**งาน:** Supabase Auth (email/password), middleware `/live`, queries อ่าน items/profiles/stats
**Gate:** login/logout ได้; อ่านข้อมูลด้วย RLS ได้; mock ไม่ถูกแตะ

### Phase 3 — Live read-only pages (ทีละหน้า)
ลำดับ: Overview → All items → Sources → Archive → Ads → Terms/Ideas → Settings (read)
**Gate ต่อหน้า:** ข้อมูลตรง legacy, screenshot ตรง, responsive, ไม่มี console error
**Flag:** `NEXT_PUBLIC_LIVE_UI=legacy|next` (สลับกลับได้)

### Phase 4 — CRUD
**งาน:** item edit/delete/archive/move, bulk, profiles, trash, import/export
**Gate:** RLS test ด้วย user A/B; user A ห้ามเห็น/แก้ข้อมูล B; operation parity

### Phase 5 — Worker + job queue
**งาน:** jobs table, worker Node collectors, Search Now/Refresh views, cancel/progress
**Gate:** job จาก web → worker → Supabase; retry/cancel; legacy fetch ยัง fallback ได้
**ห้าม:** เรียก worker จาก browser ด้วย service key

### Phase 6 — Port mock
**งาน:** `/` เป็น React + fixtures; UI parity
**Gate:** mock ไม่มี network call; screenshot parity; `/live` ไม่กระทบ

### Phase 7 — Cutover + cleanup
**งาน:** Vercel routes `/` + `/live`; legacy redirect; ลบ Python server เมื่อ parity ครบ
**Gate:** smoke ทั้งระบบ; backup; rollback tag; monitoring 1 สัปดาห์

---

## 8. Verification matrix

| ระดับ | เครื่องมือ | ผ่านเมื่อ |
|---|---|---|
| Unit | Vitest | shared/types, adapters, collectors parsing |
| DB/RLS | SQL tests | user A/B แยกกัน; anon อ่านไม่ได้ |
| API | smoke script | summary/status/CRUD/job ตรง schema |
| UI parity | Playwright | screenshot 1440/390 + flow หลัก |
| Data parity | export เทียบ | count/by_source/top items ตรง legacy |
| Worker | integration | job สำเร็จ, cancel, retry, progress |

**Flow ที่ต้องเทสทุกPhase cutover**
1. Login → Overview
2. Search Now → progress → cancel → result
3. Filter/sort/pager/CSV
4. Add/edit/delete item
5. Bulk archive → Archive restore/delete
6. Trash restore/purge
7. Profile CRUD
8. Export/import
9. Theme/mobile/patch notes

---

## 9. Rollback

- ทุก phase ใช้ branch + tag: `next-p1`, `next-p2`, …
- Feature flag `NEXT_PUBLIC_LIVE_UI` สลับ legacy/Next
- ห้ามลบ `server.py`/`live/index.html` ก่อน Phase 7
- ถ้า Supabase ล่ม: legacy local API ยังใช้ได้ (จน cutover)
- ถ้า worker ล่ม: Search Now disabled พร้อมข้อความ; หน้าอ่านยังทำงาน

---

## 10. Risks / open questions

| Risk | mitigation |
|---|---|
| Rewrite ทำ UI เพี้ยน | parity screenshots ต่อหน้า + flag |
| Supabase RLS ผิด | test user A/B + service key audit |
| Worker/Vercel timeout | queue + worker แยก + retry |
| Mock ไปเรียก live data | import boundary + lint rule |
| Scope creep | backlog แยก; feature ใหม่หลัง Phase 7 |
| Secrets รั่ว | grep before merge; anon เท่านั้นใน web |
| 2 UI พร้อมกันสับสน | route flag + banner "legacy/next" |

**ต้องตัดสินก่อน Phase 2**
1. ใช้ Supabase project เดียวกันสำหรับ dev/prod หรือแยก
2. Auth: email/password อย่างเดียว หรือ magic link/OAuth
3. Worker host: Render/Fly/VPS
4. Vercel root directory: `apps/web`
5. จะคง GitHub Pages ระหว่าง migrate หรือย้ายไป Vercel เลย

---

## 11. Definition of Done (ทั้งโปรเจกต์)

- `/` mock และ `/live` live แยกกัน, deploy Vercel
- live login + RLS; CRUD ครบ; Search Now ผ่าน worker
- ไม่มี service key ฝั่ง browser
- ไม่มี Playwright ใน Vercel
- parity checklist ครบทุกหน้า
- legacy server/Pages ปิดหรือ redirect
- docs + backup + rollback tag

---

## 12. Progress log

| Phase | สถานะ | Commit | หมายเหตุ |
|---|---|---|---|
| 0 baseline | ☐ | | |
| 1 scaffold | ☐ | | |
| 2 auth/read | ☐ | | |
| 3 live read | ☐ | | |
| 4 CRUD | ☐ | | |
| 5 worker/jobs | ☐ | | |
| 6 mock | ☐ | | |
| 7 cutover | ☐ | | |
