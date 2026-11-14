import { SourceIcon } from "@/components/live/source-icon";
import { getCollectorStats, getSourceStatus, KNOWN_SOURCES } from "@/lib/data/items-query";
import { getSummary, sourceLabel } from "@/lib/data/live";
import { sourceHealth } from "@/lib/data/source-health";

export const dynamic = "force-dynamic";

const STALE_LABEL = "stale";

/** Compact "when" so the status line stays one short phrase. */
function relativeTime(iso: string): string {
  const then = Date.parse(iso);
  if (!Number.isFinite(then)) return "";
  const minutes = Math.max(0, Math.round((Date.now() - then) / 60_000));
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

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
          // Items can exist from the legacy collectors without a collector run.
          const earlierOnly = !last && count > 0;
          const label = earlierOnly ? "No recent run" : health.label;
          const detail = earlierOnly ? `${count} items from an earlier run.` : health.detail;
          return (
            <div className={`card src-card src-${health.state}`} key={source}>
              <div className="card-head">
                <h3>
                  <SourceIcon source={source} size={20} />
                  {sourceLabel(source)}
                </h3>
                <span className="badge-n">{count}</span>
              </div>
              <p className="src-detail src-status">
                <b>
                  {label}
                  {health.stale ? ` · ${STALE_LABEL}` : ""}
                </b>
                {" · "}
                {detail}
                {last ? <> · checked {relativeTime(last.at)}</> : null}
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
                        .map(
                          ([reason, amount]) =>
                            `${reason.replace(/_/g, " ")} ${amount.toLocaleString("en-US")}`,
                        )
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
