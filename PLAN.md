# PLAN — Social Tracker (owner-approved checklist)

> Companion: `docs/ARCHITECTURE.md` (spec), `docs/AGENTS.md` (how we work).
> แผนนี้คือ checklist ทำงาน — ติ๊ก [x] เมื่อเสร็จ + ผ่าน verification แล้วเท่านั้น.
> ไม่ลงโค้ดจนกว่าเฟส 1 (spec lock) จะผ่านและ owner บอก "go".

## ความเห็นที่ล็อกแล้ว (locked decisions)

- แยก dashboard 2 ตัว: `app/dashboard.html` = mockup (Pages/แชร์), `app/dashboard-live.html` = live (localhost)
- Sources เป้าหมาย: YouTube + TikTok + TikTok Ads + FB Ads + Google News (LINE ข้าม — ไม่มี public trend จริง; Facebook organic ตัดออก 2026-11-13)
- เก็บข้อมูลบน disk: `data/items.json`, `data/index.json`, `data/analysis.json`, `data/profiles.json`
- Profile = keywords + sources; เก็บฝั่ง server; fetch ครบทุก keyword; ผลแยกดูเป็น tab ตาม keyword
- manual fetch เท่านั้น (กดเอง); accuracy/ครบถ้วนสำคัญกว่าความเร็ว
- stdlib เป็นหลัก; Playwright เป็น dependency ที่ต้องเพิ่ม (แก้ §9.5 ก่อน)

## โฟลเดอร์

```
/server.py          localhost server (stdlib + Playwright)
/pw_login.py        one-time headed login for TikTok/FB sessions
app/dashboard.html  mockup (อ่านอย่างเดียว ห้ามแก้ถ้า owner ไม่ขอ)
app/dashboard-live.html  live UI (แก้ได้)
data/               items.json / index.json / analysis.json / profiles.json (ทิ้งได้)
/assets/             fonts + thumbnails YouTube (assets/{vid}.jpg)
docs/ARCHITECTURE.md  spec (ตัดสินใจลง §9.5)
```

---

## Phase 0 — เสร็จแล้ว (slice: YouTube)

- [x] แยก mock/live (live ไม่เรียก MOCK, อ่าน `/api/summary`)
- [x] `server.py` — GET `/` (mock), `/dashboard-live.html`, `/fonts/*`, `/assets/*`, `/api/summary`
- [x] YouTube collect (stdlib urllib, `ytInitialData`, ไม่ login) + merge disk + dedup `url` + atomic write
- [x] thumbnails YouTube → `assets/{vid}.jpg` (fail-soft)
- [x] `parse_views` รองรับไทย `การดู 109,674 ครั้ง`
- [x] UI: checkbox เลือก platform ก่อน Fetch (YouTube เดียวตอนนี้, อันอื่น disabled soon)
- [x] `.gitignore`: `data/`, `assets/*.jpg`, `__pycache__/`, `shots/`
- [x] ตรวจจริง: keyword `เว็บขายของ` ได้ 16 items, total score 1,914,999, ไม่มี JS error
- [x] **สำรวจแล้ว (2026-11-09):** screenshot + API + restart (ทำซ้ำได้ทุกเมื่อด้วย `python server.py`)

## Phase 1 — spec lock

- [x] โปรไฟล์ล็อก: keywords + sources / server disk / tabs ตาม keyword (owner เลือกแล้ว)
- [x] แก้ `ARCHITECTURE.md §9.5`: เพิ่ม profiles row (YouTube scrape เดิม + GNews deferred, Playwright ยังไม่เข้าใน build นี้)
- [x] ล็อกแล้ว: YouTube = scrape เดิม (stdlib, ไม่ login) — แม่นสุด ไม่แตะ Playwright
- [x] ล็อกแล้ว: scope = ช่อง `q` กลาง + profiles (keywords[] + sources[]) เก็บ server disk
- [x] ล็อกแล้ว: GNews ทำแล้ว (ดู Phase 2); §9.7 ลบ FB/TikTok ออกจาก exclusion แล้ว
- [x] ตรวจแล้ว: Playwright + chromium ติดตั้งได้จริง (playwright 1.64.1 + chromium 1248, python 3.14)

## Phase 2 — backend: profiles + หลาย source

- [x] ตรวจแล้ว: `data/profiles.json` + init/validate + CRUD ผ่าน (`GET/POST/PUT/DELETE /api/profiles`; คีย์ผิด → 400, id ผิด → 404)
- [x] ตรวจแล้ว: `POST /api/fetch` รับ `profile_id` → วน collect ทีละ keyword × ทีละ source (sequential, manual; ตรวจจริง 2 คำได้ `per_keyword` ครบ)
- [x] ติ๊ก: response มี `per_keyword` (added/errors ต่อ keyword) + `errors` รวม
- [x] ตรวจแล้ว: GNews slice เสร็จ (stdlib RSS 10 items, author=google-news score=0; ตรวจจริง `ธุรกิจอาหาร` ได้ 10 ชิ้น)
- [x] ตรวจแล้ว: TikTok public ทำงานได้โดยไม่ต้อง login — เปิด search page ด้วย Playwright แล้วอ่าน JSON ที่หน้าโหลดเอง (`createTime`, `playCount`, `desc`, author) กรองตาม window ได้; ตรวจจริง `AI Agent` 30d ได้ 2 คลิป, 365d ได้ 12 คลิป (มีวันที่จริง); session mode ยังใช้ได้ถ้า owner login
- [x] ตรวจแล้ว: 2 โหมด TikTok/FB — `public` (ไม่ login) vs `session` (profile ใน `sessions/`) ส่ง `mode` มากับ `/api/fetch` ได้ทั้ง keyword เดี่ยว + profile; public FB เจอแต่ลิงก์เปล่า `/watch/` โดนกรองทิ้ง (added=0 + errors ซื่อสัตย์) ไม่ปน disk แล้ว
- [x] ตรวจแล้ว: กฎ session — แยก profile ต่อ platform ใน `sessions/` เครื่องเท่านั้น, `.gitignore` แล้ว, ไม่ commit
- [x] ตรวจแล้ว: freshness window ตอน fetch — `max_age_days` (7/30/365/ทั้งหมด, default 30): YouTube ใส่ `sp` + parse `publishedTimeText` (ไทย/อังกฤษ), GNews ใส่ `when:` + กรอง `pubDate`, prune แถวเดิมของ keyword นั้นที่เก่ากว่า window; ตรวจจริง 7d/1d/365d + UI ส่งค่าและจำค่า
- [x] ตรวจแล้ว: ad libraries — FB Ad Library (keyword, TH, active; อ่าน Library ID/advertiser/copy/วันเริ่ม) + TikTok Creative Center Top Ads (TH, period ตาม window) ผ่าน Playwright public ไม่ต้อง login; ตรวจจริง `ขายของ` ได้ FB 12 + TikTok 4, UI มี tab `FB Ads`/`TikTok Ads`, ads ไม่ถูก prune ด้วย window
- [x] ติ๊ก: ต่อ source ใหม่: try/except แยก แพ้ 1 source ไม่ล้มทั้งรอบ (`errors[]`) — ตรวจจริง: kw แรก `ytInitialData not found` แต่ kw ที่ 2 ได้ 12 ชิ้นตามปกติ

## Phase 3 — frontend live: profiles + tabs

- [x] ตรวจแล้ว: ตัวเลือก profile (dropdown) ใน fetch strip — เลือกแล้วล็อกช่อง keyword
- [x] ตรวจแล้ว: สร้าง/แก้/ลบ profile ใน Settings (ฟอร์มชื่อ + keywords หลายบรรทัด/คั่นจุลภาค + sources) + ตัวเลือก Mode (Public/Login) ใน fetch strip จำค่าตอน refresh
- [x] ตรวจแล้ว: ผล fetch แยก tab ตาม keyword (overview เปลี่ยนตาม tab; ดูภาพ `live-profile-tabs.png`)
- [x] ติ๊ก: โหลด disk ตาม tab ผ่าน summary ต่อ keyword
- [x] ตรวจแล้ว: ตาราง Top items แยก tab ตาม platform (All + ทุก source ที่มีข้อมูล) กรองแถวตาม tab และจำข้าม reload; ตรวจจริง 2 platform (YouTube/Google News), การ์ด Top item ยังเป็นภาพรวมเหมือนเดิม
- [x] status แสดง progress ทีละ keyword (client วนทีละ keyword ตาม profile + status รายคำ) + errors ราย keyword ต่อ source (แยกบรรทัดแล้ว); ไม่แตะ `dashboard.html` (mockup คงเดิม)

## Phase 4 — installer (removed by owner 2026-11-13)

- ~~`setup.bat`~~ — ตัดทิ้งแล้ว: เปิดแบบ local อย่างเดียวด้วย `python server.py`
- TikTok session (ถ้าต้องการ): `python pw_login.py tiktok` แล้ว login ด้วยมือครั้งเดียว (เก็บใน `sessions/` ที่ gitignore แล้ว); public mode ใช้ได้โดยไม่ต้อง login
- ขั้นตอน install (ถ้าใช้ TikTok/FB): `python -m pip install playwright` + `python -m playwright install chromium`

## Phase 5 — verification

- [x] §9.6: เปิดได้ (`python server.py` → 200), fetch ได้, summary ถูก, GNews 10 ชิ้น, dedup (fetch ซ้ำ added=0), analyze เขียนไฟล์, ไม่มี `.db`
- [x] ของใหม่: profile CRUD ครบ, fetch หลาย keyword ครบ (`per_keyword`), tab แยกถูก, source ล้ม 1 อันที่เหลือยังรอด (TikTok/FB ไม่มี session → errors ชัดเจน ไม่พัง)
- [x] แคปจอ + ตรวจ console 0 errors, mock 0 ชิ้นทุกหน้า; `.gitignore` ปิด data/session/thumbs/jpg แล้ว
- [x] ตัด Facebook organic แล้ว (2026-11-13): login wall + ไม่มีวันที่ → เอา `facebook` ออกจาก COLLECTORS/UI, ลบ item เก่าออกจาก disk 5 ชิ้น; เหลือ FB Ads เป็นช่องทาง Facebook เดียว

---

## เกณฑ์ Done (จบทั้งหมดเท่านั้น)

- ทุกกล่องด้านบนติ๊กครบ + §9.6 ผ่าน (2026-11-09: summary/dedup/analyze/profile CRUD ผ่าน, ไม่มี `.db` ของแอป, mock เปิดได้ปกติ)
- mock render เป็นชุดเดียวกับ live ในส่วนที่กระทบ UI (band/tabs/bar ค่าพิกเซล/ไอคอน); โฟลเดอร์ `.taste-skill/chrome-*` มี cache Chrome ของเครื่องตรวจเท่านั้น ไม่ใช่ข้อมูลแอป

## ประเด็นค้าง (parked, ต้อง owner ตอบก่อน Phase 1)

1. YouTube: scrape เดิม หรือ Playwright?
2. keyword scope กลาง หรือแยกต่อ profile?
3. ญี่ปุ่นยังไม่แตะ: GNews (รับ spec เดิม) จะทำเมื่อไหร่
4. business §8.1 (keywords ชุดแรกของธุรกิจ, KPI 2 ตัว) กระทบการทดสอบ — ใช้ keyword ตัวอย่าง `เว็บขายของ` ไปก่อนได้ไหม
