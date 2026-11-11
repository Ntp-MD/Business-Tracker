import Link from "next/link";

import { ItemRows } from "@/components/live/item-rows";
import { queryItems } from "@/lib/data/items-query";
import { deleteItem, restoreItem } from "@/app/live/items/actions";
import { sourceLabel } from "@/lib/data/live";

export const dynamic = "force-dynamic";

export default async function ArchivePage({
  searchParams,
}: {
  searchParams: Promise<{ source?: string }>;
}) {
  const { source = "" } = await searchParams;
  const all = await queryItems({ state: "archived", pageSize: 500 });
  const counts = all.items.reduce<Record<string, number>>((acc, item) => {
    acc[item.source] = (acc[item.source] ?? 0) + 1;
    return acc;
  }, {});
  const data = source ? await queryItems({ state: "archived", source, pageSize: 200 }) : all;

  return (
    <section className="page active" id="page-archive">
      <h2 className="visually-hidden">Archive</h2>
      <div className="card">
        <div className="card-head">
          <h3>Archived items ({all.total.toLocaleString("en-US")})</h3>
          <span className="chart-note">Saved for later</span>
        </div>
        <div className="tbl-tabs" role="tablist" aria-label="Archive by platform" style={{ marginBottom: 10 }}>
          <Link href="/live/archive" className={source ? "" : "active"} role="tab" aria-selected={!source}>
            All {all.total}
          </Link>
          {Object.entries(counts).map(([item, count]) => (
            <Link
              key={item}
              href={`/live/archive?source=${item}`}
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
              actions={(item) => (
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
              )}
            />
          ) : (
            <div className="empty">Archive ว่าง — เลือกรายการใน All items แล้วกด Archive</div>
          )}
        </div>
      </div>
    </section>
  );
}
