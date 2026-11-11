import { getSourceStatus } from "@/lib/data/items-query";
import { getSummary, sourceLabel } from "@/lib/data/live";
import { SourceIcon } from "@/components/live/source-icon";

export const dynamic = "force-dynamic";

export default async function SourcesPage() {
  const [summary, status] = await Promise.all([getSummary(), getSourceStatus()]);
  const sources = Object.entries(summary.bySource).sort((a, b) => b[1] - a[1]);

  return (
    <section className="page active" id="page-sources">
      <h2 className="visually-hidden">Sources</h2>
      <div className="src-grid">
        {sources.map(([source, count]) => {
          const last = status[source];
          return (
            <div className="card src-card" key={source}>
              <div className="card-head">
                <h3>
                  <SourceIcon source={source} size={20} />
                  {sourceLabel(source)}
                </h3>
                <span className="badge-n">{count}</span>
              </div>
              <p className="src-detail">
                {last ? (
                  last.ok ? (
                    <>Last run OK · {new Date(last.at).toLocaleString("th-TH")}</>
                  ) : (
                    <>Last error · {last.message}</>
                  )
                ) : (
                  <>No run recorded on this project</>
                )}
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
