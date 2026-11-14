import { SourceIcon } from "@/components/live/source-icon";
import { getCollectorStats, getSourceStatus, KNOWN_SOURCES } from "@/lib/data/items-query";
import { getSummary, sourceLabel } from "@/lib/data/live";
import { sourceHealth } from "@/lib/data/source-health";

export const dynamic = "force-dynamic";

export default async function SourcesPage() {
  const [summary, status, stats] = await Promise.all([
    getSummary(),
    getSourceStatus(),
    getCollectorStats(),
  ]);
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
          const stat = stats[source];
          const reasons = stat ? Object.entries(stat.byReason) : [];
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
              {stat ? (
                <p
                  className="src-detail"
                  title="Latest counters summed across keyword scopes; a record can count once per scope."
                >
                  Latest runs · accepted {stat.accepted.toLocaleString("en-US")} · rejected{" "}
                  {stat.rejected.toLocaleString("en-US")}
                  {reasons.length
                    ? ` (${reasons
                        .map(([reason, amount]) => `${reason} ${amount.toLocaleString("en-US")}`)
                        .join(", ")})`
                    : ""}
                </p>
              ) : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}
