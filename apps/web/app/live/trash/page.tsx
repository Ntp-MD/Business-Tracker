import { ItemRows } from "@/components/live/item-rows";
import { queryItems } from "@/lib/data/items-query";

import { purgeItem, restoreItem } from "../items/actions";

export const dynamic = "force-dynamic";

export default async function TrashPage() {
  const data = await queryItems({ state: "trash", pageSize: 100 });
  return (
    <section className="page active" id="page-trash">
      <h2 className="visually-hidden">Trash</h2>
      <div className="card">
        <div className="card-head">
          <h3>Trash ({data.total.toLocaleString("en-US")})</h3>
          <span className="chart-note">Restore or delete permanently</span>
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
                  <form action={purgeItem.bind(null, item.id!)}>
                    <button className="mini-btn danger" type="submit">
                      Delete forever
                    </button>
                  </form>
                </div>
              )}
            />
          ) : (
            <div className="empty">Trash is empty.</div>
          )}
        </div>
      </div>
    </section>
  );
}
