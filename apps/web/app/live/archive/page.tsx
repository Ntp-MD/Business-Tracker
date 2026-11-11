import Link from "next/link";

import { ItemRows } from "@/components/live/item-rows";
import { countArchived, queryItems } from "@/lib/data/items-query";
import { deleteItem, restoreItem } from "@/app/live/items/actions";
import { sourceLabel } from "@/lib/data/live";
import { isWritable } from "@/lib/variant";

export const dynamic = "force-dynamic";

const PAGE_SIZE = 100;

export default async function ArchivePage({
  searchParams,
}: {
  searchParams: Promise<{ source?: string; q?: string; page?: string }>;
}) {
  const sp = await searchParams;
  const source = sp.source ?? "";
  const q = (sp.q ?? "").trim();
  const page = Math.max(1, Number(sp.page) || 1);
  const writable = isWritable();
  const [counts, data] = await Promise.all([
    countArchived(),
    queryItems({ state: "archived", source, q, page, pageSize: PAGE_SIZE }),
  ]);

  function href(patch: { source?: string; q?: string; page?: number }) {
    const merged = { source, q, page, ...patch };
    const params = new URLSearchParams();
    if (merged.source) params.set("source", merged.source);
    if (merged.q) params.set("q", merged.q);
    if (merged.page > 1) params.set("page", String(merged.page));
    const query = params.toString();
    return `/live/archive${query ? `?${query}` : ""}`;
  }

  const tabs = Object.entries(counts.bySource).sort((a, b) => b[1] - a[1]);

  return (
    <section className="page active" id="page-archive">
      <h2 className="visually-hidden">Archive</h2>
      <div className="card">
        <div className="card-head">
          <h3>Archived items ({data.total.toLocaleString("en-US")})</h3>
          <span className="chart-note">
            {source ? sourceLabel(source) : "Saved for later"}
            {q ? ` · ค้นหา “${q}”` : ""}
          </span>
        </div>
        <form className="items-filters" action="/live/archive" method="get">
          <label>
            ค้นหา
            <input type="search" name="q" defaultValue={q} placeholder="Filter title/source…" />
          </label>
          {source ? <input type="hidden" name="source" value={source} /> : null}
          <button className="btn btn-primary" type="submit">
            Filter
          </button>
          <Link className="btn btn-ghost" href={href({ q: "", page: 1 })}>
            Reset
          </Link>
        </form>
        <div className="tbl-tabs" role="tablist" aria-label="Archive by platform" style={{ marginBottom: 10 }}>
          <Link href={href({ source: "", page: 1 })} className={source ? "" : "active"} role="tab" aria-selected={!source}>
            All {counts.total}
          </Link>
          {tabs.map(([item, count]) => (
            <Link
              key={item}
              href={href({ source: item, page: 1 })}
              className={source === item ? "active" : ""}
              role="tab"
              aria-selected={source === item}
            >
              {sourceLabel(item)} {count}
            </Link>
          ))}
        </div>
        <div className="tbl-scroll">
          {data.items.length ? (
            <ItemRows
              items={data.items}
              actions={writable ? (item) => (
                <div className="row-actions">
                  <form action={restoreItem.bind(null, item.id!)}>
                    <button className="mini-btn" type="submit">
                      Restore
                    </button>
                  </form>
                  <form action={deleteItem.bind(null, item.id!)}>
                    <button className="mini-btn danger" type="submit">
                      Delete
                    </button>
                  </form>
                </div>
              ) : undefined}
            />
          ) : (
            <div className="empty">
              Archive is empty — open All items and choose Archive on a row.
            </div>
          )}
        </div>
        {data.pages > 1 && (
          <div className="pager">
            <span>
              Page {data.page} / {data.pages}
            </span>
            <div className="pager-btns">
              {data.page > 1 && <Link href={href({ page: data.page - 1 })}>← Prev</Link>}
              {data.page < data.pages && <Link href={href({ page: data.page + 1 })}>Next →</Link>}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
