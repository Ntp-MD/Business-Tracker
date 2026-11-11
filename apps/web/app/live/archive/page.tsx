import { ItemRows } from "@/components/live/item-rows";
import { queryItems } from "@/lib/data/items-query";

export const dynamic = "force-dynamic";

export default async function ArchivePage() {
  const data = await queryItems({ state: "archived", pageSize: 100 });
  return (
    <section className="page active" id="page-archive">
      <h2 className="visually-hidden">Archive</h2>
      <div className="card">
        <div className="card-head">
          <h3>Archived items ({data.total.toLocaleString("en-US")})</h3>
          <span className="chart-note">Saved for later</span>
        </div>
        <div className="tbl-scroll">
          {data.items.length ? (
            <ItemRows items={data.items} />
          ) : (
            <div className="empty">Archive ว่าง — เลือกรายการใน All items แล้วกด Archive</div>
          )}
        </div>
      </div>
    </section>
  );
}
