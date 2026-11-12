import Link from "next/link";
import { redirect } from "next/navigation";

import { BrandLogo } from "@/components/brand-logo";
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
  { key: "settings", label: "Settings" },
];

const LOCKED = [
  "CRM / Leads",
  "Competitors",
  "Content Calendar",
  "Tasks",
  "Reports",
  "Goal Tracker",
];

const ICONS: Record<string, string> = {
  overview: "M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z",
  sources: "M4 7h16M4 7v13h16V7M4 7l2-4h12l2 4",
  terms: "M21 11.5a8.5 8.5 0 0 1-12.4 7.5L3 21l2-5.6A8.5 8.5 0 1 1 21 11.5z",
  ideas: "M12 3a6 6 0 0 0-3 11v3h6v-3a6 6 0 0 0-3-11zM9 21h6",
  items: "M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01",
  archive: "M3 4h18v5H3zM5 9v10h14V9M10 13h4",
  ads: "M3 11l18-5-5 18-2.5-7.5L3 11z",
  settings:
    "M19.4 15a1.7 1.7 0 0 0 .34 1.87 2 2 0 1 1-2.83 2.83 1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1.03 1.56 2 2 0 1 1-4 0 1.7 1.7 0 0 0-1.03-1.56 1.7 1.7 0 0 0-1.87.34 2 2 0 1 1-2.83-2.83 1.7 1.7 0 0 0 .34-1.87 1.7 1.7 0 0 0-1.56-1.03 2 2 0 1 1 0-4 1.7 1.7 0 0 0 1.56-1.03 1.7 1.7 0 0 0-.34-1.87 2 2 0 1 1 2.83-2.83 1.7 1.7 0 0 0 1.87.34 1.7 1.7 0 0 0 1.03-1.56 2 2 0 1 1 4 0 1.7 1.7 0 0 0 1.03 1.56 1.7 1.7 0 0 0 1.87-.34 2 2 0 1 1 2.83 2.83 1.7 1.7 0 0 0-.34 1.87 1.7 1.7 0 0 0 1.56 1.03 2 2 0 1 1 0 4 1.7 1.7 0 0 0-1.56 1.03z",
};

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
  if (appVariant() === "live") redirect("/live");
  const items = MOCK_ITEMS;
  const sources = [...new Set(items.map((item) => item.source))];
  const totalScore = items.reduce((sum, item) => sum + Number(item.score), 0);
  const terms = mockTerms();

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
            {LOCKED.map((label) => (
              <span key={label} className="locked" aria-disabled="true" title="not compatible">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <rect x="4" y="10.5" width="16" height="9.5" rx="2" />
                  <path d="M8 10.5V7a4 4 0 0 1 8 0v3.5" />
                </svg>
                {label}
              </span>
            ))}
          </nav>
          <div className="help-card">
            <span className="proto-tag">PROTOTYPE · mock data — not production</span>
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
            <div className="page-sub">Mockup · sample data · no backend</div>
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
                  <span className="chart-note">Sample data · mock table</span>
                </div>
                <div className="tbl-scroll">
                  <Table rows={items} />
                </div>
              </div>
            </section>
          )}

          {view === "sources" && (
            <section className="page active">
              <div className="src-grid">
                {sources.map((source) => (
                  <div className="card src-card" key={source}>
                    <div className="card-head">
                      <h3>
                        <SourceIcon source={source} size={20} />
                        {mockSourceLabel(source)}
                      </h3>
                      <span className="badge-n">
                        {items.filter((item) => item.source === source).length}
                      </span>
                    </div>
                    <p className="src-detail">Sample rows only — live data is on /live</p>
                  </div>
                ))}
              </div>
            </section>
          )}

          {view === "terms" && (
            <section className="page active">
              <div className="card">
                <div className="card-head">
                  <h3>Top terms · {items.length} sample items</h3>
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
            </section>
          )}

          {view === "ideas" && (
            <section className="page active">
              {MOCK_PROFILES.map((profile) => (
                <div className="card" key={profile.name} style={{ marginBottom: 12 }}>
                  <div className="card-head">
                    <h3>{profile.name}</h3>
                    <span className="chart-note">{profile.keywords.length} keywords</span>
                  </div>
                  <ul className="suggest">
                    {profile.keywords.map((keyword) => (
                      <li key={keyword}>
                        SEO post: answer &quot;{keyword}&quot; in one clear headline + hashtags + a
                        single CTA.
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </section>
          )}

          {view === "archive" && (
            <section className="page active">
              <div className="card">
                <div className="card-head">
                  <h3>Archived items (4)</h3>
                  <span className="chart-note">Sample archive</span>
                </div>
                <div className="tbl-scroll">
                  <Table rows={items.slice(0, 4)} />
                </div>
              </div>
            </section>
          )}

          {view === "ads" && (
            <section className="page active">
              <div className="card">
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

          {view === "settings" && (
            <section className="page active">
              <div className="card">
                <div className="card-head">
                  <h3>Profiles</h3>
                  <span className="chart-note">{MOCK_PROFILES.length} sample profiles</span>
                </div>
                <div className="terms">
                  {MOCK_PROFILES.map((profile) => (
                    <span className="term" key={profile.name}>
                      {profile.name}
                      <b>{profile.keywords.length}</b>
                    </span>
                  ))}
                </div>
              </div>
              <div className="card" style={{ marginTop: 12 }}>
                <div className="card-head">
                  <h3>Data</h3>
                  <span className="chart-note">Mock — nothing is stored</span>
                </div>
                <div className="metric-grid">
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
