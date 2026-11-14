/** Sum the latest collector_state counters per source; pure and fixture-testable. */

export type CollectorStatRow = { connector_id: string; counters: unknown };

export type SourceStats = {
  accepted: number;
  rejected: number;
  byReason: Record<string, number>;
};

const CONNECTOR_SOURCE: Record<string, string> = {
  gdelt_doc: "gdelt",
};

function count(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) && value > 0 ? Math.floor(value) : 0;
}

export function aggregateCollectorStats(rows: CollectorStatRow[]): Record<string, SourceStats> {
  const bySource: Record<string, SourceStats> = {};

  for (const row of rows) {
    const source = CONNECTOR_SOURCE[row.connector_id];
    if (!source) continue;
    const counters = row.counters;
    if (!counters || typeof counters !== "object") continue;

    const value = counters as {
      accepted?: unknown;
      rejected_total?: unknown;
      rejected?: unknown;
    };
    const stats = bySource[source] ?? { accepted: 0, rejected: 0, byReason: {} };
    stats.accepted += count(value.accepted);
    stats.rejected += count(value.rejected_total);

    if (value.rejected && typeof value.rejected === "object") {
      for (const [reason, amount] of Object.entries(value.rejected as Record<string, unknown>)) {
        const rejected = count(amount);
        if (rejected > 0) {
          stats.byReason[reason] = (stats.byReason[reason] ?? 0) + rejected;
        }
      }
    }
    if (stats.accepted > 0 || stats.rejected > 0 || Object.keys(stats.byReason).length > 0) {
      bySource[source] = stats;
    }
  }

  return bySource;
}
