import { SourceIcon } from "@/components/live/source-icon";
import { getSourceStatus, KNOWN_SOURCES } from "@/lib/data/items-query";
import { getSummary, sourceLabel } from "@/lib/data/live";
import { sourceHealth } from "@/lib/data/source-health";

export const dynamic = "force-dynamic";

export default async function SourcesPage() {
  const [summary, status] = await Promise.all([getSummary(), getSourceStatus()]);
  const configured = Array.from(
    new Set([...KNOWN_SOURCES, "gdelt", ...Object.keys(summary.bySource), ...Object.keys(status)]),
  );
  const sources = configured.sort(
    (a, b) => (summary.bySource[b] ?? 0) - (summary.bySource[a] ?? 0) || a.localeCompare(b),
  );

  return (
    <section className="page active" id="page-sources">
      <h2 className="visually-hidden">Sources</h2>
      <div className="src-grid">
        {sources.map((source) => {
          const count = summary.bySource[source] ?? 0;
          const last = status[source];
          const health = sourceHealth(last);
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
                <b>
                  {health.label}
                  {health.stale ? " · stale" : ""}
                </b>
                {" · "}
                {health.detail}
                {last ? (
                  <>
                    {" · last checked "}
                    {new Date(last.at).toLocaleString("th-TH", { timeZone: "Asia/Bangkok" })}
                  </>
                ) : null}
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
