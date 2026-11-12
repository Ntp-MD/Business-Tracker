import { ItemRows } from "@/components/live/item-rows";
import { queryItems } from "@/lib/data/items-query";

export const dynamic = "force-dynamic";

export default async function AdsPage() {
  const [fb, tt] = await Promise.all([
    queryItems({ source: "fbads", pageSize: 100 }),
    queryItems({ source: "ttads", pageSize: 100 }),
  ]);
  const total = fb.total + tt.total;

  return (
    <section className="page active" id="page-ads">
      <h2 className="visually-hidden">Ads manager</h2>
      <div className="card">
        <div className="card-head">
          <h3>Collected ads ({total.toLocaleString("en-US")})</h3>
          <span className="chart-note">
            FB Ads {fb.total} · TikTok Ads {tt.total}
          </span>
        </div>
        <div className="tbl-scroll">
          {total ? (
            <ItemRows items={[...fb.items, ...tt.items]} />
          ) : (
            <div className="empty">No ads collected yet.</div>
          )}
        </div>
      </div>
    </section>
  );
}
