import Link from "next/link";

import { ItemRows } from "@/components/live/item-rows";
import { JobStatus } from "@/components/live/job-status";
import { ANALYSIS_PROMPT } from "@/lib/data/analysis-export";
import { queryItems, type SortKey } from "@/lib/data/items-query";
import { getSummary, sourceLabel } from "@/lib/data/live";
import { isWritable } from "@/lib/variant";

import { archiveItem, bulkArchive, bulkDelete, bulkMove, createItem, deleteItem } from "./actions";
import { enqueueRefresh } from "./refresh-action";

export const dynamic = "force-dynamic";

const SORTS: { key: SortKey; label: string }[] = [
  { key: "score", label: "Metric" },
  { key: "published", label: "Date" },
  { key: "created_at", label: "Saved" },
  { key: "source", label: "Source" },
  { key: "title", label: "Title" },
];

const PAGE_SIZES = [25, 50, 100, 200];

function isoDate(timeZone: string): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const get = (type: string) => parts.find((part) => part.type === type)?.value ?? "";
  return `${get("year")}-${get("month")}-${get("day")}`;
}

function shiftDate(date: string, days: number): string {
  const value = new Date(`${date}T00:00:00Z`);
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
}

export default async function ItemsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const sp = await searchParams;
  const q = sp.q ?? "";
  const source = sp.source ?? "";
  const sort = (SORTS.find((s) => s.key === sp.sort)?.key ?? "score") as SortKey;
  const dir = sp.dir === "asc" ? "asc" : "desc";
  const page = Math.max(1, Number(sp.page) || 1);
  const from = sp.from ?? "";
  const to = sp.to ?? "";
  const job = sp.job;
  const writable = isWritable();
  const sizeParam = Number(sp.size);
  const pageSize = PAGE_SIZES.includes(sizeParam) ? sizeParam : 25;

  const [data, summary] = await Promise.all([
    queryItems({ state: "active", q, source, sort, dir, page, pageSize, from, to }),
    getSummary(),
  ]);
  const sources = Object.keys(summary.bySource);

  const today = isoDate("Asia/Bangkok");
  const quickRanges = [
    { key: "all", label: "ทั้งหมด", from: "", to: "" },
    { key: "today", label: "วันนี้", from: today, to: today },
    { key: "7d", label: "7 วัน", from: shiftDate(today, -6), to: today },
    { key: "30d", label: "30 วัน", from: shiftDate(today, -29), to: today },
  ];
  const activeRange = quickRanges.find((range) => range.from === from && range.to === to)?.key;

  function link(patch: Record<string, string | number | undefined>) {
    const params = new URLSearchParams();
    const merged = { q, source, sort, dir, page, size: pageSize, from, to, ...patch };
    for (const [key, value] of Object.entries(merged)) {
      if (value === undefined || value === "") continue;
      if (key === "sort" && value === "score") continue;
      if (key === "dir" && value === "desc") continue;
      if (key === "page" && value === 1) continue;
      if (key === "size" && value === 25) continue;
      params.set(key, String(value));
    }
    const query = params.toString();
    return `/live/items${query ? `?${query}` : ""}`;
  }

  const exportParams = new URLSearchParams();
  for (const [key, value] of Object.entries({ q, source, from, to, sort, dir })) {
    if (!value) continue;
    if (key === "sort" && value === "score") continue;
    if (key === "dir" && value === "desc") continue;
    exportParams.set(key, value);
  }
  const exportHref = `/api/export/items${exportParams.size ? `?${exportParams}` : ""}`;
  const analysisHref = `/api/export/analysis${exportParams.size ? `?${exportParams}` : ""}`;
  const guideHref = `${analysisHref}${exportParams.size ? "&" : "?"}format=guide`;

  return (
    <section className="page active" id="page-items">
      <h2 className="visually-hidden">All items</h2>
      {job ? <JobStatus jobId={Number(job)} /> : null}
      {sp.error === "jobs_table" ? (
        <div className="status err">Jobs table missing — run the jobs migration in Supabase.</div>
      ) : null}
      <div className="card">
        <div className="card-head">
          <h3>All items ({data.total.toLocaleString("en-US")})</h3>
          <span className="chart-note">
            Click a title to open the source · {dir === "desc" ? "high → low" : "low → high"}
          </span>
        </div>

        <form className="items-filters" action="/live/items" method="get">
          <label>
            ค้นหา
            <input type="search" name="q" defaultValue={q} placeholder="Filter title/source…" />
          </label>
          <label>
            แพลตฟอร์ม
            <select name="source" defaultValue={source}>
              <option value="">ทุกแพลตฟอร์ม</option>
              {sources.map((item) => (
                <option key={item} value={item}>
                  {sourceLabel(item)}
                </option>
              ))}
            </select>
          </label>
          <label>
            เรียงตาม
            <select name="sort" defaultValue={sort}>
              {SORTS.map((item) => (
                <option key={item.key} value={item.key}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            ทิศทาง
            <select name="dir" defaultValue={dir}>
              <option value="desc">มาก → น้อย</option>
              <option value="asc">น้อย → มาก</option>
            </select>
          </label>
          <label>
            ตั้งแต่
            <input type="date" name="from" defaultValue={from} />
          </label>
          <label>
            ถึง
            <input type="date" name="to" defaultValue={to} />
          </label>
          <label>
            ต่อหน้า
            <select name="size" defaultValue={String(pageSize)}>
              {PAGE_SIZES.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </label>
          <button className="btn btn-primary" type="submit">
            Filter
          </button>
          <Link className="btn btn-ghost" href="/live/items">
            Reset
          </Link>
        </form>

        {/* biome-ignore lint/a11y/useSemanticElements: styled grouping div; fieldset would change layout */}
        <div className="quick-dates" role="group" aria-label="Quick date range">
          {quickRanges.map((range) => (
            <Link
              key={range.key}
              href={link({ from: range.from, to: range.to, page: 1 })}
              className={`chip qd${activeRange === range.key ? " active" : ""}`}
              aria-current={activeRange === range.key ? "true" : undefined}
            >
              {range.label}
            </Link>
          ))}
        </div>

        {writable ? (
          <details className="add-item">
            <summary
              className="btn btn-ghost"
              style={{ display: "inline-block", marginBottom: 12 }}
            >
              + Add item
            </summary>
            <form action={createItem} className="item-form">
              <label>
                Keyword
                <input name="keyword" placeholder="เช่น AI agent" required />
              </label>
              <label>
                Source
                <select name="source" defaultValue="youtube">
                  {sources.map((item) => (
                    <option key={item} value={item}>
                      {sourceLabel(item)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                URL
                <input name="url" type="url" placeholder="https://…" required />
              </label>
              <label>
                Title
                <input name="title" placeholder="หัวข้อที่ต้องการบันทึก" required />
              </label>
              <label>
                Channel / page
                <input name="author" placeholder="ชื่อช่องหรือเพจ" />
              </label>
              <label>
                Score
                <input name="score" type="number" min="0" step="1" placeholder="0" />
              </label>
              <button className="btn btn-primary" type="submit">
                Save item
              </button>
            </form>
          </details>
        ) : null}

        <div className="card-head" style={{ marginTop: 4 }}>
          <h3>Results</h3>
          <div className="row-actions">
            {writable ? (
              <form action={enqueueRefresh}>
                <input type="hidden" name="q" value={q} />
                <button
                  className="btn btn-ghost"
                  type="submit"
                  title="Refresh YouTube view counts for this keyword; with no keyword, refresh all active items"
                  style={{ padding: "6px 12px", fontSize: 12 }}
                >
                  Refresh views
                </button>
              </form>
            ) : null}
            <a
              className="btn btn-ghost"
              href={exportHref}
              style={{ padding: "6px 12px", fontSize: 12 }}
            >
              Export CSV
            </a>
          </div>
        </div>

        <details className="analysis-panel">
          <summary className="btn btn-ghost">Export for AI analysis</summary>
          <p>
            Downloads every active item matching these filters as CSV, plus a Markdown guide and
            prompt for your own AI tool. TrendRail does not send data anywhere.
          </p>
          <div className="row-actions">
            <a className="btn btn-ghost" href={analysisHref}>
              Dataset CSV
            </a>
            <a className="btn btn-ghost" href={guideHref}>
              Guide + prompt (Markdown)
            </a>
          </div>
          <p className="analysis-note">
            Checkbox selection is not included; use the filters to narrow the scope. Dates filter
            the stored published value.
          </p>
          <pre>{ANALYSIS_PROMPT}</pre>
        </details>

        <form action={bulkArchive}>
          <div className="tbl-scroll">
            {data.items.length ? (
              <ItemRows
                items={data.items}
                selectable={writable}
                actions={
                  writable
                    ? (item) => (
                        <div className="row-actions">
                          <Link className="mini-btn" href={`/live/items/${item.id}/edit`}>
                            Edit
                          </Link>
                          <button
                            className="mini-btn"
                            type="submit"
                            formAction={archiveItem.bind(null, item.id!)}
                          >
                            Archive
                          </button>
                          <button
                            className="mini-btn danger"
                            type="submit"
                            formAction={deleteItem.bind(null, item.id!)}
                          >
                            Delete
                          </button>
                        </div>
                      )
                    : undefined
                }
              />
            ) : (
              <div className="empty">No items match this view.</div>
            )}
          </div>

          {writable ? (
            <div className="bulk-bar bulk-bar-live">
              <button className="btn btn-ghost" type="submit">
                Archive selected
              </button>
              <button className="btn btn-ghost" type="submit" formAction={bulkDelete}>
                Delete selected
              </button>
              <input name="to_keyword" placeholder="ย้ายไป keyword…" aria-label="Move to keyword" />
              <button className="btn btn-ghost" type="submit" formAction={bulkMove}>
                Move
              </button>
            </div>
          ) : null}
        </form>

        <div className="pager">
          <span>
            Page {data.page} / {data.pages} · {pageSize} แถว
          </span>
          <div className="pager-btns">
            {data.page > 1 && <Link href={link({ page: data.page - 1 })}>← Prev</Link>}
            {data.page < data.pages && <Link href={link({ page: data.page + 1 })}>Next →</Link>}
          </div>
        </div>
      </div>
    </section>
  );
}
