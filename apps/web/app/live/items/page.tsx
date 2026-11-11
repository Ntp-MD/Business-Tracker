import Link from "next/link";

import { ItemRows } from "@/components/live/item-rows";
import { queryItems, type SortKey, type ItemState } from "@/lib/data/items-query";
import { getSummary, sourceLabel } from "@/lib/data/live";

export const dynamic = "force-dynamic";

const SORTS: { key: SortKey; label: string }[] = [
  { key: "score", label: "Metric" },
  { key: "published", label: "Date" },
  { key: "created_at", label: "Saved" },
  { key: "source", label: "Source" },
  { key: "title", label: "Title" },
];

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

  const [data, summary] = await Promise.all([
    queryItems({ state: "active", q, source, sort, dir, page }),
    getSummary(),
  ]);
  const sources = Object.keys(summary.bySource);

  function link(patch: Record<string, string | number | undefined>) {
    const params = new URLSearchParams();
    const merged = { q, source, sort, dir, page, ...patch };
    for (const [key, value] of Object.entries(merged)) {
      if (value !== undefined && value !== "" && value !== "score" && value !== "desc" && value !== 1) {
        params.set(key, String(value));
      }
    }
    const query = params.toString();
    return `/live/items${query ? `?${query}` : ""}`;
  }

  return (
    <section className="page active" id="page-items">
      <h2 className="visually-hidden">All items</h2>
      <div className="card">
        <div className="card-head">
          <h3>All items ({data.total.toLocaleString("en-US")})</h3>
          <span className="chart-note">Click a title to open the source · {dir === "desc" ? "high → low" : "low → high"}</span>
        </div>

        <form className="items-filters" action="/live/items" method="get">
          <input type="search" name="q" defaultValue={q} placeholder="Filter title/source…" aria-label="Filter" />
          <select name="source" defaultValue={source} aria-label="Platform">
            <option value="">ทุกแพลตฟอร์ม</option>
            {sources.map((item) => (
              <option key={item} value={item}>
                {sourceLabel(item)}
              </option>
            ))}
          </select>
          <select name="sort" defaultValue={sort} aria-label="Sort">
            {SORTS.map((item) => (
              <option key={item.key} value={item.key}>
                {item.label}
              </option>
            ))}
          </select>
          <select name="dir" defaultValue={dir} aria-label="Direction">
            <option value="desc">มาก → น้อย</option>
            <option value="asc">น้อย → มาก</option>
          </select>
          <button className="btn btn-primary" type="submit">
            Filter
          </button>
          <Link className="btn btn-ghost" href="/live/items">
            Reset
          </Link>
        </form>

        <div className="tbl-scroll">
          {data.items.length ? <ItemRows items={data.items} /> : <div className="empty">No items match this view.</div>}
        </div>

        <div className="pager">
          <span>
            Page {data.page} / {data.pages}
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
