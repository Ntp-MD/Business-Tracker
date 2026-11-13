import Link from "next/link";
import { redirect } from "next/navigation";

import { BrandLogo } from "@/components/brand-logo";
import { Bars } from "@/components/live/charts";
import { PatchNotes } from "@/components/live/patch-notes";
import { SourceIcon } from "@/components/live/source-icon";
import { ThemeToggle } from "@/components/live/theme-toggle";
import {
  MOCK_ITEMS,
  MOCK_PROFILES,
  mockBand,
  mockSourceLabel,
  mockTerms,
} from "@/lib/mock/fixtures";
import { appVariant } from "@/lib/variant";

const VIEWS = [
  { key: "overview", label: "Overview" },
  { key: "sources", label: "Sources" },
  { key: "terms", label: "Top Terms" },
  { key: "ideas", label: "Content Ideas" },
  { key: "items", label: "All Items" },
  { key: "archive", label: "Archive" },
  { key: "ads", label: "Ads Manager" },
  { key: "crm", label: "CRM / Leads" },
  { key: "competitors", label: "Competitors" },
  { key: "calendar", label: "Content Calendar" },
  { key: "tasks", label: "Tasks" },
  { key: "reports", label: "Reports" },
  { key: "goals", label: "Goal Tracker" },
  { key: "settings", label: "Settings" },
];

const ICONS: Record<string, string> = {
  overview: "M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z",
  sources: "M4 7h16M4 7v13h16V7M4 7l2-4h12l2 4",
  terms: "M21 11.5a8.5 8.5 0 0 1-12.4 7.5L3 21l2-5.6A8.5 8.5 0 1 1 21 11.5z",
  ideas: "M12 3a6 6 0 0 0-3 11v3h6v-3a6 6 0 0 0-3-11zM9 21h6",
  items: "M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01",
  archive: "M3 4h18v5H3zM5 9v10h14V9M10 13h4",
  ads: "M3 11l18-5-5 18-2.5-7.5L3 11z",
  crm: "M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75",
  competitors: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
  calendar: "M3 4h18v18H3zM16 2v4M8 2v4M3 10h18",
  tasks: "M9 11l3 3L22 4M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11",
  reports:
    "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M16 13H8M16 17H8M10 9H8",
  goals:
    "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 18a6 6 0 1 0 0-12 6 6 0 0 0 0 12zM12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4z",
  settings:
    "M19.4 15a1.7 1.7 0 0 0 .34 1.87 2 2 0 1 1-2.83 2.83 1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1.03 1.56 2 2 0 1 1-4 0 1.7 1.7 0 0 0-1.03-1.56 1.7 1.7 0 0 0-1.87.34 2 2 0 1 1-2.83-2.83 1.7 1.7 0 0 0 .34-1.87 1.7 1.7 0 0 0-1.56-1.03 2 2 0 1 1 0-4 1.7 1.7 0 0 0 1.56-1.03 1.7 1.7 0 0 0-.34-1.87 2 2 0 1 1 2.83-2.83 1.7 1.7 0 0 0 1.87.34 1.7 1.7 0 0 0 1.03-1.56 2 2 0 1 1 4 0 1.7 1.7 0 0 0 1.03 1.56 1.7 1.7 0 0 0 1.87-.34 2 2 0 1 1 2.83 2.83 1.7 1.7 0 0 0-.34 1.87 1.7 1.7 0 0 0 1.56 1.03 2 2 0 1 1 0 4 1.7 1.7 0 0 0-1.56 1.03z",
};

const MOCK_CRM = [
  {
    stage: "New",
    tone: "blue",
    leads: [
      { name: "คุณมายด์", need: "LINE OA + CRM", src: "Facebook" },
      { name: "Baan Cha", need: "Local SEO", src: "TikTok" },
      { name: "K. Ton", need: "Ads audit", src: "LINE" },
    ],
  },
  {
    stage: "Talking",
    tone: "yellow",
    leads: [
      { name: "Glow Clinic", need: "Content retainer", src: "Facebook" },
      { name: "Nok Cafe", need: "TikTok shoot", src: "TikTok" },
    ],
  },
  {
    stage: "Quoted",
    tone: "blue",
    leads: [{ name: "Siam Fitness", need: "6-month package", src: "Referral" }],
  },
  {
    stage: "Won",
    tone: "green",
    leads: [{ name: "ITOPPLUS Case", need: "Full funnel", src: "Facebook" }],
  },
];

const MOCK_COMPETITORS = [
  {
    name: "ITOPPLUS",
    platform: "FB + TikTok",
    followers: "12,450",
    er: "4.82%",
    posts: "15",
    reach: "18,240",
    status: "นำตลาด",
    tone: "green",
  },
  {
    name: "Agency A",
    platform: "Facebook",
    followers: "38,200",
    er: "3.61%",
    posts: "12",
    reach: "24,600",
    status: "ตามใกล้",
    tone: "yellow",
  },
  {
    name: "Agency B",
    platform: "TikTok + IG",
    followers: "91,000",
    er: "6.40%",
    posts: "21",
    reach: "48,000",
    status: "แรง",
    tone: "red",
  },
  {
    name: "Agency C",
    platform: "YouTube + Blog",
    followers: "33,000",
    er: "2.91%",
    posts: "8",
    reach: "9,600",
    status: "Niche",
    tone: "blue",
  },
];

const MOCK_ALERTS = [
  { title: "Agency B เปิดแคมเปญ TikTok ใหม่", detail: "ยอด reach +32% ใน 7 วัน" },
  { title: "Agency A ลดราคา package 20%", detail: "จับตาดีลลูกค้า local" },
  { title: "Local SEO ยังเป็นช่องว่าง", detail: "คู่แข่งยังไม่ทำคอนเทนต์สายนี้" },
];

const MOCK_ADS = [
  {
    name: "Local SEO lead gen",
    channel: "Facebook",
    budget: "15,000",
    reach: "48,200",
    clicks: "1,240",
    cpl: "185",
    roas: "3.8",
    status: "Active",
    tone: "green",
  },
  {
    name: "LINE OA เปิดร้าน",
    channel: "LINE",
    budget: "8,000",
    reach: "21,600",
    clicks: "860",
    cpl: "210",
    roas: "2.9",
    status: "Active",
    tone: "green",
  },
  {
    name: "TikTok Shop awareness",
    channel: "TikTok",
    budget: "12,000",
    reach: "96,400",
    clicks: "1,980",
    cpl: "245",
    roas: "3.2",
    status: "Paused",
    tone: "yellow",
  },
  {
    name: "Retargeting ลูกค้าเก่า",
    channel: "Instagram",
    budget: "5,000",
    reach: "18,900",
    clicks: "540",
    cpl: "160",
    roas: "4.6",
    status: "Active",
    tone: "green",
  },
];

const MOCK_CALENDAR = [
  {
    day: "จ.",
    posts: [
      { platform: "FB", title: "Local SEO checklist", status: "ok" },
      { platform: "TikTok", title: "Behind the scenes", status: "draft" },
    ],
  },
  { day: "อ.", posts: [{ platform: "IG", title: "Client result", status: "ok" }] },
  {
    day: "พ.",
    posts: [
      { platform: "FB", title: "Ads vs organic", status: "ok" },
      { platform: "LINE", title: "Broadcast promo", status: "ok" },
    ],
  },
  { day: "พฤ.", posts: [{ platform: "YouTube", title: "SEO for Thai SMEs", status: "draft" }] },
  { day: "ศ.", posts: [{ platform: "TikTok", title: "3 quick tips", status: "ok" }] },
  { day: "ส.", posts: [{ platform: "IG", title: "Weekend reel", status: "draft" }] },
  { day: "อา.", posts: [{ platform: "FB", title: "Weekly recap", status: "ok" }] },
];

const MOCK_TASKS = [
  {
    stage: "To do",
    tone: "blue",
    tasks: [
      { name: "เขียนสคริปต์ TikTok", owner: "Content", due: "วันนี้" },
      { name: "ตรวจแคมเปญ FB Ads", owner: "Ads", due: "พรุ่งนี้" },
    ],
  },
  {
    stage: "Doing",
    tone: "yellow",
    tasks: [
      { name: "ตัดต่อคลิป Local SEO", owner: "Video", due: "วันนี้" },
      { name: "ทำรายงานลูกค้า", owner: "Account", due: "ศุกร์" },
    ],
  },
  {
    stage: "Done",
    tone: "green",
    tasks: [{ name: "ส่งคอนเทนต์สัปดาห์นี้", owner: "Content", due: "เมื่อวาน" }],
  },
  {
    stage: "Review",
    tone: "blue",
    tasks: [{ name: "รีวิวสคริปต์ TikTok", owner: "Founder", due: "พรุ่งนี้" }],
  },
];

const MOCK_REPORT = [
  { label: "Reach", value: "182,600", note: "5 ช่องทาง", pct: 86 },
  { label: "Engagement", value: "8.9%", note: "เฉลี่ยต่อโพสต์", pct: 72 },
  { label: "Leads", value: "34", note: "ลูกค้าจริง", pct: 68 },
  { label: "Followers", value: "12,450", note: "+11.5%", pct: 81 },
];

const MOCK_SOURCE_HEALTH = [
  { name: "youtube", status: "OK", count: 24, checked: "2 นาทีที่แล้ว", note: "YouTube Data API" },
  { name: "gnews", status: "OK", count: 18, checked: "2 นาทีที่แล้ว", note: "Google News RSS" },
  { name: "tiktok", status: "OK", count: 12, checked: "5 นาทีที่แล้ว", note: "Playwright session" },
  { name: "fbads", status: "OK", count: 8, checked: "5 นาทีที่แล้ว", note: "Meta Ad Library" },
  { name: "ttads", status: "ช้า", count: 5, checked: "28 นาทีที่แล้ว", note: "รอ rate limit" },
];

const MOCK_IDEAS = [
  {
    title: "5 checklist Local SEO ที่ร้านไทยทำได้เอง",
    keyword: "Local SEO",
    format: "Carousel",
    owner: "Content",
    status: "Approved",
    due: "13 พ.ย.",
    tone: "green",
  },
  {
    title: "Line OA กับเว็บไซต์ เลือกอะไรก่อน",
    keyword: "LINE OA",
    format: "Reel",
    owner: "Video",
    status: "Draft",
    due: "14 พ.ย.",
    tone: "yellow",
  },
  {
    title: "ทำไมร้านค้าออนไลน์ควรมีเว็บของตัวเอง",
    keyword: "เว็บร้านค้า",
    format: "Blog",
    owner: "SEO",
    status: "Scheduled",
    due: "15 พ.ย.",
    tone: "blue",
  },
  {
    title: "3 สัญญาณว่าร้านควรยิงแอดแล้ว",
    keyword: "Facebook Ads",
    format: "Short",
    owner: "Ads",
    status: "Approved",
    due: "16 พ.ย.",
    tone: "green",
  },
  {
    title: "เคสลูกค้า: ลด no-show ด้วยระบบจอง",
    keyword: "ระบบจองคิว",
    format: "Case study",
    owner: "Account",
    status: "Draft",
    due: "17 พ.ย.",
    tone: "yellow",
  },
];

const MOCK_LEADS = [
  {
    name: "คุณมายด์",
    source: "Facebook",
    owner: "Palm",
    value: "35,000",
    stage: "New",
    next: "โทรครั้งแรก",
  },
  {
    name: "Baan Cha",
    source: "TikTok",
    owner: "Palm",
    value: "18,000",
    stage: "New",
    next: "ส่งแพ็กเกจ",
  },
  { name: "K. Ton", source: "LINE", owner: "Fern", value: "12,000", stage: "New", next: "นัด demo" },
  {
    name: "Glow Clinic",
    source: "Facebook",
    owner: "Fern",
    value: "85,000",
    stage: "Talking",
    next: "รอใบเสนอราคา",
  },
  {
    name: "Nok Cafe",
    source: "TikTok",
    owner: "Palm",
    value: "24,000",
    stage: "Talking",
    next: "นัดถ่ายคลิป",
  },
  {
    name: "Siam Fitness",
    source: "Referral",
    owner: "Fern",
    value: "120,000",
    stage: "Quoted",
    next: "ติดตามผล 14 พ.ย.",
  },
  {
    name: "ITOPPLUS Case",
    source: "Facebook",
    owner: "Palm",
    value: "180,000",
    stage: "Won",
    next: "เริ่ม onboarding",
  },
  {
    name: "Cafe Amazon",
    source: "Facebook",
    owner: "Fern",
    value: "45,000",
    stage: "Won",
    next: "ส่งรายงานรอบแรก",
  },
];

const MOCK_GOALS_DETAIL = [
  {
    name: "Reach",
    owner: "Content",
    target: "200,000",
    actual: "182,600",
    pct: 91,
    status: "On track",
    tone: "green",
  },
  {
    name: "Leads",
    owner: "Sales",
    target: "50",
    actual: "34",
    pct: 68,
    status: "At risk",
    tone: "yellow",
  },
  {
    name: "ROAS",
    owner: "Ads",
    target: "4.0x",
    actual: "4.2x",
    pct: 105,
    status: "Exceeded",
    tone: "green",
  },
  {
    name: "Followers",
    owner: "Content",
    target: "15,000",
    actual: "12,450",
    pct: 83,
    status: "On track",
    tone: "green",
  },
  {
    name: "Retention",
    owner: "Account",
    target: "95%",
    actual: "96%",
    pct: 100,
    status: "Exceeded",
    tone: "green",
  },
];

const MOCK_REPORTS_HISTORY = [
  {
    name: "ITOPPLUS · พ.ย. 2026",
    period: "1–12 พ.ย.",
    owner: "Fern",
    status: "Ready",
    tone: "green",
  },
  {
    name: "ITOPPLUS · ต.ค. 2026",
    period: "1–31 ต.ค.",
    owner: "Fern",
    status: "Sent",
    tone: "blue",
  },
  {
    name: "Local Heroes · ต.ค. 2026",
    period: "1–31 ต.ค.",
    owner: "Palm",
    status: "Sent",
    tone: "blue",
  },
];

const MOCK_COMP_SOV: [string, number][] = [
  ["ITOPPLUS", 38],
  ["Agency A", 22],
  ["Agency B", 17],
  ["Agency C", 16],
  ["DIY", 7],
];

function score(value: number): string {
  return value.toLocaleString("en-US");
}

function Table({ rows }: { rows: typeof MOCK_ITEMS }) {
  return (
    <table>
      <caption className="visually-hidden">Top items by score</caption>
      <thead>
        <tr>
          <th scope="col">Source</th>
          <th scope="col">Title</th>
          <th scope="col">Metric</th>
          <th scope="col">Signal</th>
          <th scope="col">Link</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((item) => (
          <tr key={item.id}>
            <td>
              <span className="src-cell">
                <SourceIcon source={item.source} />
                <span className="src-name">{mockSourceLabel(item.source)}</span>
              </span>
            </td>
            <td>
              <span className="row-title">{item.title}</span>
              <div className="row-channel-wrap">
                <span className="row-channel">{item.author}</span>
              </div>
            </td>
            <td>
              <b>{score(Number(item.score))}</b> <span className="metric-unit">{item.metric}</span>
            </td>
            <td>
              <span className={`pill ${mockBand(Number(item.score)).toLowerCase()}`}>
                {mockBand(Number(item.score))}
              </span>
            </td>
            <td style={{ whiteSpace: "nowrap" }}>Open →</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default async function MockPage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>;
}) {
  const { view = "overview" } = await searchParams;
  const variant = appVariant();
  if (variant === "live") redirect("/live");
  const items = MOCK_ITEMS;
  const sources = MOCK_SOURCE_HEALTH.map((source) => source.name);
  const totalScore = items.reduce((sum, item) => sum + Number(item.score), 0);
  const terms = mockTerms();
  const termTotal = terms.reduce((sum, [, count]) => sum + count, 0);

  return (
    <>
      <link rel="stylesheet" href="/assets/css/variables.css" />
      <link rel="stylesheet" href="/assets/css/base.css" />
      <link rel="stylesheet" href="/assets/css/component.css" />
      <link rel="stylesheet" href="/assets/css/layout.css" />
      <div className="app">
        <aside className="sidebar" aria-label="Primary">
          <div className="logo">
            <BrandLogo />
          </div>
          <nav className="nav">
            {VIEWS.map((item) => (
              <Link
                key={item.key}
                href={`/?view=${item.key}`}
                className={view === item.key ? "active" : ""}
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <path d={ICONS[item.key]} />
                </svg>
                {item.label}
                {item.key === "items" && <span className="badge-n">{items.length}</span>}
                {item.key === "sources" && <span className="badge-n">{sources.length}</span>}
              </Link>
            ))}
          </nav>
          <div className="help-card">
            <span className="proto-tag">
              {variant === "mockup" ? "MOCKUP · sample data" : "MOCK PREVIEW · real data at /live"}
            </span>
            <PatchNotes />
          </div>
        </aside>

        <h2 className="visually-hidden">Overview</h2>
        <div className="main">
          <div className="topbar">
            <h1>Analytics</h1>
            <div className="top-actions">
              <ThemeToggle />
              <div className="user">
                <span className="avatar">IT</span>
                <span className="uname">ITOPPLUS</span>
              </div>
            </div>
            <div className="page-sub">
              {variant === "mockup"
                ? "MOCKUP · sample data · no backend"
                : "MOCK PREVIEW · production data lives at /live"}
            </div>
          </div>

          <nav className="mobile-nav" aria-label="Mobile">
            {VIEWS.map((item) => (
              <Link key={item.key} href={`/?view=${item.key}`}>
                {item.label}
              </Link>
            ))}
          </nav>

          <div className="fetch-strip">
            <div className="fetch-main">
              <div className="field">
                <label htmlFor="mockProfile">โปรไฟล์</label>
                <select id="mockProfile" defaultValue="0">
                  <option value="0">Keyword ใหม่</option>
                  {MOCK_PROFILES.map((profile) => (
                    <option key={profile.name}>{profile.name}</option>
                  ))}
                </select>
              </div>
              <div className="field grow">
                <label htmlFor="mockKeyword">Keyword</label>
                <input
                  id="mockKeyword"
                  type="text"
                  placeholder="Keyword…"
                  defaultValue="Digital Marketing"
                />
              </div>
              <div className="field">
                <label htmlFor="mockSources">Sources</label>
                <select id="mockSources" defaultValue="YouTube">
                  <option>YouTube</option>
                  <option>Facebook</option>
                  <option>TikTok</option>
                </select>
              </div>
              <div className="field">
                <label htmlFor="mockFresh">Fresh</label>
                <select id="mockFresh" defaultValue="30">
                  <option value="30">30 วัน</option>
                  <option value="7">7 วัน</option>
                  <option value="0">ทั้งหมด</option>
                </select>
              </div>
              <button className="btn btn-primary fetch-btn" type="button">
                Search Now
              </button>
            </div>
            <div className="status">Sample data (mock) · ปุ่มนี้ไม่เรียก backend</div>
          </div>

          {view === "overview" && (
            <section className="page active">
              <div className="kpis">
                <div className="card kpi">
                  <div className="label">
                    <span>Items saved</span>
                  </div>
                  <div className="big">{items.length}</div>
                  <div className="delta">
                    <small>Sample data · unique URL</small>
                  </div>
                </div>
                <div className="card kpi">
                  <div className="label">
                    <span>Sources</span>
                  </div>
                  <div className="big">{sources.length}</div>
                  <div className="delta">
                    <small>{sources.slice(0, 3).map(mockSourceLabel).join(" · ")}</small>
                  </div>
                </div>
                <div className="card kpi kpi-donut">
                  <div className="label">
                    <span>Total score</span>
                  </div>
                  <div className="big">{score(totalScore)}</div>
                  <div className="delta">
                    <small>score share by source</small>
                  </div>
                </div>
                <div className="card kpi kpi-top">
                  <div className="label">
                    <span>Top item</span>
                  </div>
                  <div className="big">{score(Number(items[0].score))}</div>
                  <div className="top-title">{items[0].title}</div>
                  <div className="delta">
                    <small>{mockSourceLabel(items[0].source)} · highest score</small>
                  </div>
                </div>
              </div>

              <div className="bottom">
                <div className="card">
                  <div className="tbl-head">
                    <h3>Top items (8)</h3>
                    <Link
                      className="btn btn-ghost"
                      href="/?view=items"
                      style={{ padding: "6px 12px", fontSize: 12 }}
                    >
                      View all →
                    </Link>
                  </div>
                  <div className="tbl-scroll">
                    <Table rows={items.slice(0, 8)} />
                  </div>
                </div>
                <div className="side-stack">
                  <div className="card">
                    <div className="card-head">
                      <h3>Top terms (summary)</h3>
                    </div>
                    <div className="terms">
                      {terms.map(([word, count]) => (
                        <span className="term" key={word}>
                          {word}
                          <b>{count}</b>
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="card">
                    <div className="card-head">
                      <h3>Content ideas (summary)</h3>
                    </div>
                    <ul className="suggest">
                      <li>
                        30-sec clip: open on the pain behind Digital Marketing, demo the fix, close
                        with one LINE CTA.
                      </li>
                      <li>
                        SEO post: answer &quot;Digital Marketing&quot; in one clear headline +
                        hashtags + a single CTA.
                      </li>
                      <li>
                        3-part FAQ: three shorts answering the most-asked questions about Digital
                        Marketing.
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </section>
          )}

          {view === "items" && (
            <section className="page active">
              <div className="card">
                <div className="card-head">
                  <h3>All items ({items.length})</h3>
                  <span className="chart-note">Mock table · no backend</span>
                </div>
                <div className="items-filters">
                  <label>
                    ค้นหา
                    <input type="search" name="q" placeholder="Filter title/source…" />
                  </label>
                  <label>
                    Source
                    <select name="source" defaultValue="">
                      <option value="">ทุกแหล่ง</option>
                      {sources.map((source) => (
                        <option key={source} value={source}>
                          {mockSourceLabel(source)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Sort
                    <select name="sort" defaultValue="score">
                      <option value="score">Score</option>
                      <option value="published">Published</option>
                      <option value="title">Title</option>
                    </select>
                  </label>
                  <label>
                    จาก
                    <input type="date" name="from" defaultValue="2026-11-01" />
                  </label>
                  <label>
                    ถึง
                    <input type="date" name="to" defaultValue="2026-11-13" />
                  </label>
                  <button className="btn btn-primary" type="button">
                    Filter
                  </button>
                  <button className="btn btn-ghost" type="button">
                    Reset
                  </button>
                </div>
                <div className="tbl-head">
                  <div className="tbl-tabs" role="tablist" aria-label="Items by source">
                    <a className="active" href="?view=items" role="tab" aria-selected="true">
                      All {items.length}
                    </a>
                    {sources.map((source) => (
                      <a key={source} href="?view=items" role="tab" aria-selected="false">
                        {mockSourceLabel(source)}{" "}
                        {items.filter((item) => item.source === source).length}
                      </a>
                    ))}
                  </div>
                  <span className="chart-note">Page 1 / 1</span>
                </div>
                <div className="tbl-scroll">
                  <Table rows={items} />
                </div>
                <div className="pager">
                  <span>
                    Showing 1–{items.length} of {items.length}
                  </span>
                  <a className="active" href="?view=items">
                    1
                  </a>
                </div>
              </div>
            </section>
          )}

          {view === "sources" && (
            <section className="page active">
              <div className="src-grid">
                {MOCK_SOURCE_HEALTH.map((source) => (
                  <div className="card src-card" key={source.name}>
                    <div className="card-head">
                      <h3>
                        <SourceIcon source={source.name} size={20} />
                        {mockSourceLabel(source.name)}
                      </h3>
                      <span className={`pill pill-${source.status === "OK" ? "green" : "yellow"}`}>
                        {source.status}
                      </span>
                    </div>
                    <p className="src-detail">{source.note}</p>
                    <div className="metric-grid" style={{ marginTop: 10 }}>
                      <div className="m">
                        <b>{source.count}</b>
                        <span>items</span>
                      </div>
                      <div className="m">
                        <b>{source.checked}</b>
                        <span>last run</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="card" style={{ marginTop: 16 }}>
                <div className="card-head">
                  <h3>Source health</h3>
                  <span className="chart-note">Mock run · 13 พ.ย. 2026</span>
                </div>
                <div className="tbl-scroll">
                  <table>
                    <caption className="visually-hidden">Source health</caption>
                    <thead>
                      <tr>
                        <th scope="col">Source</th>
                        <th scope="col">Status</th>
                        <th scope="col">Items</th>
                        <th scope="col">Last run</th>
                        <th scope="col">Note</th>
                      </tr>
                    </thead>
                    <tbody>
                      {MOCK_SOURCE_HEALTH.map((source) => (
                        <tr key={source.name}>
                          <td>
                            <b>{mockSourceLabel(source.name)}</b>
                          </td>
                          <td>
                            <span
                              className={`pill pill-${source.status === "OK" ? "green" : "yellow"}`}
                            >
                              {source.status}
                            </span>
                          </td>
                          <td>{source.count}</td>
                          <td>{source.checked}</td>
                          <td>{source.note}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </section>
          )}

          {view === "terms" && (
            <section className="page active">
              <div className="kpis">
                <div className="card kpi">
                  <div className="label">Unique terms</div>
                  <div className="big">{terms.length}</div>
                  <div className="delta">
                    <small>จาก {items.length} sample items</small>
                  </div>
                </div>
                <div className="card kpi">
                  <div className="label">Top term</div>
                  <div className="big">{terms[0]?.[0] ?? "—"}</div>
                  <div className="delta up">{terms[0]?.[1] ?? 0} mentions</div>
                </div>
                <div className="card kpi">
                  <div className="label">Mentions</div>
                  <div className="big">{termTotal}</div>
                  <div className="delta">
                    <small>รวมทุก term</small>
                  </div>
                </div>
                <div className="card kpi">
                  <div className="label">Avg / item</div>
                  <div className="big">{(termTotal / Math.max(items.length, 1)).toFixed(1)}</div>
                  <div className="delta">
                    <small>term ต่อ item</small>
                  </div>
                </div>
              </div>
              <div className="card" style={{ marginTop: 16 }}>
                <div className="card-head">
                  <h3>Top terms · {items.length} sample items</h3>
                  <span className="chart-note">Mock analysis</span>
                </div>
                <div className="tbl-scroll">
                  <table>
                    <caption className="visually-hidden">Top terms</caption>
                    <thead>
                      <tr>
                        <th scope="col">Term</th>
                        <th scope="col">Mentions</th>
                        <th scope="col">Share</th>
                        <th scope="col">Trend</th>
                      </tr>
                    </thead>
                    <tbody>
                      {terms.map(([word, count], index) => (
                        <tr key={word}>
                          <td>
                            <b>{word}</b>
                          </td>
                          <td>{count}</td>
                          <td>
                            <span className="term-bar" style={{ display: "block", width: 160 }}>
                              <i
                                style={{
                                  width: `${Math.max(8, Math.round((count / Math.max(terms[0][1], 1)) * 100))}%`,
                                }}
                              />
                            </span>
                          </td>
                          <td>
                            <span className={`pill pill-${index < 3 ? "green" : "blue"}`}>
                              {index < 3 ? "Rising" : "Steady"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </section>
          )}

          {view === "ideas" && (
            <section className="page active">
              <div className="kpis">
                <div className="card kpi">
                  <div className="label">Ideas ทั้งหมด</div>
                  <div className="big">{MOCK_IDEAS.length}</div>
                  <div className="delta up">พร้อมผลิต</div>
                </div>
                <div className="card kpi">
                  <div className="label">Approved</div>
                  <div className="big">
                    {MOCK_IDEAS.filter((idea) => idea.status === "Approved").length}
                  </div>
                  <div className="delta">
                    <small>รอเข้า calendar</small>
                  </div>
                </div>
                <div className="card kpi">
                  <div className="label">Draft</div>
                  <div className="big">
                    {MOCK_IDEAS.filter((idea) => idea.status === "Draft").length}
                  </div>
                  <div className="delta">
                    <small>รอรีวิว</small>
                  </div>
                </div>
                <div className="card kpi">
                  <div className="label">Scheduled</div>
                  <div className="big">
                    {MOCK_IDEAS.filter((idea) => idea.status === "Scheduled").length}
                  </div>
                  <div className="delta">
                    <small>ตั้งเวลาแล้ว</small>
                  </div>
                </div>
              </div>
              <div className="card" style={{ marginTop: 16 }}>
                <div className="card-head">
                  <h3>Content ideas</h3>
                  <span className="chart-note">Mock pipeline</span>
                </div>
                <div
                  className="tbl-tabs"
                  role="tablist"
                  aria-label="Ideas by profile"
                  style={{ marginBottom: 10 }}
                >
                  {MOCK_PROFILES.map((profile, index) => (
                    <a
                      key={profile.name}
                      className={index === 0 ? "active" : ""}
                      href="?view=ideas"
                      role="tab"
                      aria-selected={index === 0}
                    >
                      {profile.name}
                    </a>
                  ))}
                </div>
                <div className="tbl-scroll">
                  <table>
                    <caption className="visually-hidden">Content ideas</caption>
                    <thead>
                      <tr>
                        <th scope="col">Idea</th>
                        <th scope="col">Keyword</th>
                        <th scope="col">Format</th>
                        <th scope="col">Owner</th>
                        <th scope="col">Status</th>
                        <th scope="col">Due</th>
                      </tr>
                    </thead>
                    <tbody>
                      {MOCK_IDEAS.map((idea) => (
                        <tr key={idea.title}>
                          <td>
                            <b>{idea.title}</b>
                          </td>
                          <td>{idea.keyword}</td>
                          <td>{idea.format}</td>
                          <td>{idea.owner}</td>
                          <td>
                            <span className={`pill pill-${idea.tone}`}>{idea.status}</span>
                          </td>
                          <td>{idea.due}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </section>
          )}

          {view === "archive" && (
            <section className="page active">
              <div className="card">
                <div className="card-head">
                  <h3>Archived items (4)</h3>
                  <span className="chart-note">Mock archive · saved for later</span>
                </div>
                <div className="items-filters">
                  <label>
                    ค้นหา
                    <input type="search" name="q" placeholder="Filter title/source…" />
                  </label>
                  <label>
                    Source
                    <select name="source" defaultValue="">
                      <option value="">ทุกแหล่ง</option>
                      {sources.map((source) => (
                        <option key={source} value={source}>
                          {mockSourceLabel(source)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button className="btn btn-primary" type="button">
                    Filter
                  </button>
                  <button className="btn btn-ghost" type="button">
                    Reset
                  </button>
                </div>
                <div
                  className="tbl-tabs"
                  role="tablist"
                  aria-label="Archive by source"
                  style={{ marginBottom: 10 }}
                >
                  <a className="active" href="?view=archive" role="tab" aria-selected="true">
                    All 4
                  </a>
                  {sources.slice(0, 3).map((source) => (
                    <a key={source} href="?view=archive" role="tab" aria-selected="false">
                      {mockSourceLabel(source)}{" "}
                      {items.slice(0, 4).filter((item) => item.source === source).length}
                    </a>
                  ))}
                </div>
                <div className="tbl-scroll">
                  <Table rows={items.slice(0, 4)} />
                </div>
                <div className="pager">
                  <span>Showing 1–4 of 4</span>
                  <a className="active" href="?view=archive">
                    1
                  </a>
                </div>
              </div>
            </section>
          )}

          {view === "ads" && (
            <section className="page active">
              <div className="kpis">
                <div className="card kpi">
                  <div className="label">ใช้จ่ายเดือนนี้</div>
                  <div className="big">45,000</div>
                  <div className="delta up">+15% จากเดือนก่อน</div>
                </div>
                <div className="card kpi">
                  <div className="label">CPL เฉลี่ย</div>
                  <div className="big">210</div>
                  <div className="delta up">-12% ดีขึ้น</div>
                </div>
                <div className="card kpi">
                  <div className="label">ROAS</div>
                  <div className="big">3.4</div>
                  <div className="delta up">ยังมีกำไร</div>
                </div>
                <div className="card kpi">
                  <div className="label">Clicks</div>
                  <div className="big">3,214</div>
                  <div className="delta">
                    <small>CTR 2.8% · 21 clicks/วัน</small>
                  </div>
                </div>
              </div>
              <div className="card" style={{ marginTop: 16 }}>
                <div className="card-head">
                  <h3>แคมเปญตามช่องทาง</h3>
                  <span className="chart-note">Mock data</span>
                </div>
                <div className="tbl-scroll">
                  <table>
                    <caption className="visually-hidden">Ad campaigns</caption>
                    <thead>
                      <tr>
                        <th scope="col">แคมเปญ</th>
                        <th scope="col">ช่องทาง</th>
                        <th scope="col">งบ</th>
                        <th scope="col">Reach</th>
                        <th scope="col">Clicks</th>
                        <th scope="col">CPL</th>
                        <th scope="col">ROAS</th>
                        <th scope="col">สถานะ</th>
                      </tr>
                    </thead>
                    <tbody>
                      {MOCK_ADS.map((ad) => (
                        <tr key={ad.name}>
                          <td>
                            <b>{ad.name}</b>
                          </td>
                          <td>{ad.channel}</td>
                          <td>{ad.budget}</td>
                          <td>{ad.reach}</td>
                          <td>{ad.clicks}</td>
                          <td>{ad.cpl}</td>
                          <td>{ad.roas}</td>
                          <td>
                            <span className={`pill pill-${ad.tone}`}>{ad.status}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              <div className="card" style={{ marginTop: 16 }}>
                <div className="card-head">
                  <h3>Collected ads (2)</h3>
                  <span className="chart-note">Sample ads</span>
                </div>
                <div className="tbl-scroll">
                  <Table rows={items.slice(0, 2)} />
                </div>
              </div>
            </section>
          )}

          {view === "crm" && (
            <section className="page active">
              <div className="kpis">
                <div className="card kpi">
                  <div className="label">Leads (30 วัน)</div>
                  <div className="big">8</div>
                  <div className="delta up">+3 จากเดือนก่อน</div>
                </div>
                <div className="card kpi">
                  <div className="label">กำลังคุย</div>
                  <div className="big">2</div>
                  <div className="delta">
                    <small>รอเอกสาร</small>
                  </div>
                </div>
                <div className="card kpi">
                  <div className="label">เสนอราคา</div>
                  <div className="big">1</div>
                  <div className="delta">
                    <small>รอ 7 วัน</small>
                  </div>
                </div>
                <div className="card kpi">
                  <div className="label">ปิดได้</div>
                  <div className="big">1</div>
                  <div className="delta up">85,000 บาท</div>
                </div>
              </div>
              <div className="kanban" style={{ marginTop: 16 }}>
                {MOCK_CRM.map((column) => (
                  <div className="card kcol" key={column.stage}>
                    <h4>
                      {column.stage}
                      <span className="badge-n kcount">{column.leads.length}</span>
                    </h4>
                    {column.leads.map((lead) => (
                      <div className="card lead" key={lead.name}>
                        <b>{lead.name}</b>
                        <span>{lead.need}</span>
                        <span className={`pill pill-${column.tone} lead-src`}>{lead.src}</span>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
              <div className="card" style={{ marginTop: 16 }}>
                <div className="card-head">
                  <h3>Lead pipeline</h3>
                  <span className="chart-note">{MOCK_LEADS.length} leads · mock</span>
                </div>
                <div className="tbl-scroll">
                  <table>
                    <caption className="visually-hidden">Lead pipeline</caption>
                    <thead>
                      <tr>
                        <th scope="col">Lead</th>
                        <th scope="col">Source</th>
                        <th scope="col">Owner</th>
                        <th scope="col">Value</th>
                        <th scope="col">Stage</th>
                        <th scope="col">Next action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {MOCK_LEADS.map((lead) => (
                        <tr key={lead.name}>
                          <td>
                            <b>{lead.name}</b>
                          </td>
                          <td>{lead.source}</td>
                          <td>{lead.owner}</td>
                          <td>{lead.value}</td>
                          <td>
                            <span className="pill pill-blue">{lead.stage}</span>
                          </td>
                          <td>{lead.next}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </section>
          )}

          {view === "competitors" && (
            <section className="page active">
              <div className="kpis">
                <div className="card kpi">
                  <div className="label">SoV ITOPPLUS</div>
                  <div className="big">38%</div>
                  <div className="delta up">+5% จากเดือนก่อน</div>
                </div>
                <div className="card kpi">
                  <div className="label">ติดตามอยู่</div>
                  <div className="big">{MOCK_COMPETITORS.length}</div>
                  <div className="delta">
                    <small>FB · TikTok · YouTube</small>
                  </div>
                </div>
                <div className="card kpi">
                  <div className="label">Alert ใหม่</div>
                  <div className="big">{MOCK_ALERTS.length}</div>
                  <div className="delta">
                    <small>มีแคมเปญ/ราคาใหม่</small>
                  </div>
                </div>
                <div className="card kpi">
                  <div className="label">โอกาสว่าง</div>
                  <div className="big">Local SEO</div>
                  <div className="delta up">คู่แข่งยังไม่ทำ</div>
                </div>
              </div>
              <div className="card" style={{ marginTop: 16 }}>
                <div className="card-head">
                  <h3>Share of voice</h3>
                  <span className="chart-note">Mock · 5 แบรนด์</span>
                </div>
                <Bars share={MOCK_COMP_SOV} />
              </div>
              <div className="card" style={{ marginTop: 16 }}>
                <div className="card-head">
                  <h3>สรุปคู่แข่ง</h3>
                  <span className="chart-note">Mock data</span>
                </div>
                <div className="tbl-scroll">
                  <table>
                    <caption className="visually-hidden">Competitor summary</caption>
                    <thead>
                      <tr>
                        <th scope="col">คู่แข่ง</th>
                        <th scope="col">แพลตฟอร์ม</th>
                        <th scope="col">Followers</th>
                        <th scope="col">ER</th>
                        <th scope="col">โพสต์/สัปดาห์</th>
                        <th scope="col">Reach/โพสต์</th>
                        <th scope="col">สถานะ</th>
                      </tr>
                    </thead>
                    <tbody>
                      {MOCK_COMPETITORS.map((item) => (
                        <tr key={item.name}>
                          <td>
                            <b>{item.name}</b>
                          </td>
                          <td>{item.platform}</td>
                          <td>{item.followers}</td>
                          <td>{item.er}</td>
                          <td>{item.posts}</td>
                          <td>{item.reach}</td>
                          <td>
                            <span className={`pill pill-${item.tone}`}>{item.status}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              <div className="comp-detail">
                <div className="card">
                  <div className="card-head">
                    <h3>จุดแข็ง / จุดอ่อน</h3>
                  </div>
                  <div className="kv">
                    <span>ITOPPLUS</span>
                    <b>Local SEO + ปิดการขายเร็ว</b>
                  </div>
                  <div className="kv">
                    <span>Agency A</span>
                    <b>Ads + strategy แต่แพง</b>
                  </div>
                  <div className="kv">
                    <span>Agency B</span>
                    <b>TikTok แรง แต่ผูกกับ influencer</b>
                  </div>
                  <div className="kv">
                    <span>Agency C</span>
                    <b>SEO ลึก แต่ไม่มี TikTok</b>
                  </div>
                </div>
                <div className="card">
                  <div className="card-head">
                    <h3>Alert สัปดาห์นี้</h3>
                    <span className="chart-note">Mock data</span>
                  </div>
                  {MOCK_ALERTS.map((alert) => (
                    <div className="card alert" key={alert.title}>
                      <b>{alert.title}</b>
                      <div className="src-detail">{alert.detail}</div>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          )}

          {view === "calendar" && (
            <section className="page active">
              <div className="kpis">
                <div className="card kpi">
                  <div className="label">โพสต์สัปดาห์นี้</div>
                  <div className="big">15</div>
                  <div className="delta up">ครบทุกช่องทาง</div>
                </div>
                <div className="card kpi">
                  <div className="label">Approved</div>
                  <div className="big">8</div>
                  <div className="delta up">พร้อมโพสต์</div>
                </div>
                <div className="card kpi">
                  <div className="label">Draft</div>
                  <div className="big">4</div>
                  <div className="delta">
                    <small>รอรีวิว</small>
                  </div>
                </div>
                <div className="card kpi">
                  <div className="label">Scheduled</div>
                  <div className="big">3</div>
                  <div className="delta">
                    <small>ตั้งเวลาแล้ว</small>
                  </div>
                </div>
              </div>
              <div className="cal-week" style={{ marginTop: 16 }}>
                {MOCK_CALENDAR.map((day) => (
                  <div className="card cal-day" key={day.day}>
                    <h5>{day.day}</h5>
                    {day.posts.map((post) => (
                      <div className={`post ${post.status}`} key={`${day.day}-${post.title}`}>
                        <b>{post.platform}</b> {post.title}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </section>
          )}

          {view === "tasks" && (
            <section className="page active">
              <div className="kpis">
                <div className="card kpi">
                  <div className="label">งานทั้งหมด</div>
                  <div className="big">
                    {MOCK_TASKS.reduce((sum, column) => sum + column.tasks.length, 0)}
                  </div>
                  <div className="delta">
                    <small>4 คอลัมน์</small>
                  </div>
                </div>
                <div className="card kpi">
                  <div className="label">Due วันนี้</div>
                  <div className="big">2</div>
                  <div className="delta up">ต้องส่งก่อน 18:00</div>
                </div>
                <div className="card kpi">
                  <div className="label">เสร็จแล้ว</div>
                  <div className="big">1</div>
                  <div className="delta up">Content ส่งแล้ว</div>
                </div>
                <div className="card kpi">
                  <div className="label">รอรีวิว</div>
                  <div className="big">1</div>
                  <div className="delta">
                    <small>Founder review</small>
                  </div>
                </div>
              </div>
              <div
                className="tbl-tabs"
                role="tablist"
                aria-label="Task filters"
                style={{ margin: "12px 0" }}
              >
                <a className="active" href="?view=tasks" role="tab" aria-selected="true">
                  All
                </a>
                <a href="?view=tasks" role="tab" aria-selected="false">
                  Mine
                </a>
                <a href="?view=tasks" role="tab" aria-selected="false">
                  Due today
                </a>
                <a href="?view=tasks" role="tab" aria-selected="false">
                  Overdue
                </a>
              </div>
              <div className="kanban" style={{ marginTop: 4 }}>
                {MOCK_TASKS.map((column) => (
                  <div className="card kcol" key={column.stage}>
                    <h4>
                      {column.stage}
                      <span className="badge-n kcount">{column.tasks.length}</span>
                    </h4>
                    {column.tasks.map((task) => (
                      <div className="card lead" key={task.name}>
                        <b>{task.name}</b>
                        <span>
                          {task.owner} · {task.due}
                        </span>
                        <span className={`pill pill-${column.tone} lead-src`}>{column.stage}</span>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </section>
          )}

          {view === "reports" && (
            <section className="page active">
              <div className="report-grid">
                <div className="card">
                  <div className="card-head">
                    <h3>ITOPPLUS overview (30 วัน)</h3>
                    <span className="chart-note">Mock report</span>
                  </div>
                  <div className="metric-grid">
                    {MOCK_REPORT.map((row) => (
                      <div className="m" key={row.label}>
                        <b>{row.value}</b>
                        <span>
                          {row.label} · {row.note}
                        </span>
                      </div>
                    ))}
                  </div>
                  <button className="btn btn-primary" type="button" style={{ marginTop: 14 }}>
                    Export PDF (demo)
                  </button>
                </div>
                <div className="card">
                  <div className="card-head">
                    <h3>Client progress</h3>
                    <span className="chart-note">% ของเป้าหมาย</span>
                  </div>
                  {MOCK_REPORT.map((row) => (
                    <div className="progress-row" key={row.label}>
                      <span className="lbl">{row.label}</span>
                      <span className="bar">
                        <i style={{ width: `${row.pct}%` }} />
                      </span>
                      <span className="pct">{row.pct}%</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="card" style={{ marginTop: 16 }}>
                <div className="card-head">
                  <h3>Report history</h3>
                  <span className="chart-note">Mock archive</span>
                </div>
                <div className="tbl-scroll">
                  <table>
                    <caption className="visually-hidden">Report history</caption>
                    <thead>
                      <tr>
                        <th scope="col">Report</th>
                        <th scope="col">Period</th>
                        <th scope="col">Owner</th>
                        <th scope="col">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {MOCK_REPORTS_HISTORY.map((report) => (
                        <tr key={report.name}>
                          <td>
                            <b>{report.name}</b>
                          </td>
                          <td>{report.period}</td>
                          <td>{report.owner}</td>
                          <td>
                            <span className={`pill pill-${report.tone}`}>{report.status}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </section>
          )}

          {view === "goals" && (
            <section className="page active">
              <div className="kpis">
                <div className="card kpi">
                  <div className="label">เป้าหมายทั้งหมด</div>
                  <div className="big">{MOCK_GOALS_DETAIL.length}</div>
                  <div className="delta">
                    <small>5 ตัวชี้วัด</small>
                  </div>
                </div>
                <div className="card kpi">
                  <div className="label">On track</div>
                  <div className="big">
                    {MOCK_GOALS_DETAIL.filter((goal) => goal.status === "On track").length}
                  </div>
                  <div className="delta up">ตามแผน</div>
                </div>
                <div className="card kpi">
                  <div className="label">At risk</div>
                  <div className="big">
                    {MOCK_GOALS_DETAIL.filter((goal) => goal.status === "At risk").length}
                  </div>
                  <div className="delta">
                    <small>Leads ต่ำกว่าเป้า</small>
                  </div>
                </div>
                <div className="card kpi">
                  <div className="label">Exceeded</div>
                  <div className="big">
                    {MOCK_GOALS_DETAIL.filter((goal) => goal.status === "Exceeded").length}
                  </div>
                  <div className="delta up">ROAS + Retention</div>
                </div>
              </div>
              <div className="card" style={{ marginTop: 16 }}>
                <div className="card-head">
                  <h3>เป้าหมายลูกค้า vs ผลจริง</h3>
                  <span className="chart-note">Mock data</span>
                </div>
                <div className="tbl-scroll">
                  <table>
                    <caption className="visually-hidden">Goal tracker</caption>
                    <thead>
                      <tr>
                        <th scope="col">Goal</th>
                        <th scope="col">Owner</th>
                        <th scope="col">Target</th>
                        <th scope="col">Actual</th>
                        <th scope="col">Progress</th>
                        <th scope="col">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {MOCK_GOALS_DETAIL.map((goal) => (
                        <tr key={goal.name}>
                          <td>
                            <b>{goal.name}</b>
                          </td>
                          <td>{goal.owner}</td>
                          <td>{goal.target}</td>
                          <td>{goal.actual}</td>
                          <td>
                            <span className="term-bar" style={{ display: "block", width: 140 }}>
                              <i style={{ width: `${Math.min(goal.pct, 100)}%` }} />
                            </span>
                          </td>
                          <td>
                            <span className={`pill pill-${goal.tone}`}>{goal.status}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </section>
          )}

          {view === "settings" && (
            <section className="page active">
              <div className="set-grid">
                <div className="set-col">
                  <div className="card">
                    <div className="card-head">
                      <h3>Keyword profiles</h3>
                      <span className="chart-note">{MOCK_PROFILES.length} profiles</span>
                    </div>
                    {MOCK_PROFILES.map((profile) => (
                      <div className="set-row" key={profile.name}>
                        <div className="t">
                          <b>{profile.name}</b>
                          <span>{profile.keywords.join(" · ")}</span>
                        </div>
                        <div style={{ display: "flex", gap: 6 }}>
                          <button
                            className="btn btn-ghost"
                            type="button"
                            style={{ padding: "6px 12px", fontSize: 12 }}
                          >
                            Edit
                          </button>
                          <button
                            className="btn btn-ghost"
                            type="button"
                            style={{ padding: "6px 12px", fontSize: 12 }}
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    ))}
                    <div className="set-row wide">
                      <div className="t">
                        <b>เพิ่ม profile</b>
                        <span>Mock only — nothing is saved</span>
                      </div>
                      <input
                        className="set-input"
                        type="text"
                        placeholder="ชื่อ profile"
                        aria-label="Mock profile name"
                      />
                    </div>
                    <div className="set-row wide">
                      <div className="t">
                        <b>Keywords</b>
                        <span>คั่นด้วย comma</span>
                      </div>
                      <textarea
                        rows={3}
                        defaultValue="Local SEO, LINE OA, Facebook Ads"
                        aria-label="Mock profile keywords"
                      />
                    </div>
                    <button className="btn btn-primary" type="button" style={{ marginTop: 8 }}>
                      Add profile
                    </button>
                  </div>
                </div>
                <div className="set-col">
                  <div className="card">
                    <div className="card-head">
                      <h3>Sources</h3>
                      <span className="chart-note">Mock toggles</span>
                    </div>
                    {MOCK_SOURCE_HEALTH.map((source) => (
                      <div className="set-row" key={source.name}>
                        <div className="t">
                          <b>
                            <SourceIcon source={source.name} size={16} />{" "}
                            {mockSourceLabel(source.name)}
                          </b>
                          <span>{source.note}</span>
                        </div>
                        <input
                          type="checkbox"
                          defaultChecked
                          aria-label={`Enable ${source.name}`}
                        />
                      </div>
                    ))}
                  </div>
                  <div className="card" style={{ marginTop: 12 }}>
                    <div className="card-head">
                      <h3>Data</h3>
                      <span className="chart-note">Mock only</span>
                    </div>
                    <div className="set-row">
                      <div className="t">
                        <b>Export demo</b>
                        <span>JSON snapshot</span>
                      </div>
                      <button className="btn btn-ghost" type="button">
                        Export
                      </button>
                    </div>
                    <div className="set-row">
                      <div className="t">
                        <b>Import demo</b>
                        <span>JSON / ZIP</span>
                      </div>
                      <button className="btn btn-ghost" type="button">
                        Import
                      </button>
                    </div>
                    <div className="set-row">
                      <div className="t">
                        <b>Reset demo</b>
                        <span>คืนค่า mock data</span>
                      </div>
                      <button className="btn btn-ghost" type="button">
                        Reset
                      </button>
                    </div>
                    <div className="metric-grid" style={{ marginTop: 12 }}>
                      <div className="m">
                        <b>{items.length}</b>
                        <span>Sample items</span>
                      </div>
                      <div className="m">
                        <b>{sources.length}</b>
                        <span>Sample sources</span>
                      </div>
                    </div>
                  </div>
                  <div className="card" style={{ marginTop: 12 }}>
                    <div className="card-head">
                      <h3>Appearance</h3>
                    </div>
                    <div className="set-row">
                      <div className="t">
                        <b>Theme</b>
                        <span>Light / Dark</span>
                      </div>
                      <ThemeToggle />
                    </div>
                    <div className="set-row">
                      <div className="t">
                        <b>ภาษา</b>
                        <span>ไทย / English</span>
                      </div>
                      <select defaultValue="th" aria-label="Language">
                        <option value="th">ไทย</option>
                        <option value="en">English</option>
                      </select>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          )}

          {!VIEWS.some((item) => item.key === view) && (
            <section className="page active">
              <div className="card">
                <div className="empty">หน้านี้ยังไม่เปิด — mock แสดงเฉพาะหน้าที่อยู่ในเมนู</div>
              </div>
            </section>
          )}
        </div>
      </div>
    </>
  );
}
