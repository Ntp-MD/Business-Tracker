import Link from "next/link";

import { Bars, Donut, LineChart } from "@/components/live/charts";
import { formatScore, ItemRows } from "@/components/live/item-rows";
import { JobStatus } from "@/components/live/job-status";
import { getSummary, sourceLabel } from "@/lib/data/live";

export const dynamic = "force-dynamic";

export default async function OverviewPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; platform?: string; job?: string; error?: string }>;
}) {
  const { q = "", platform = "all", job, error } = await searchParams;
  const data = await getSummary(q);

  const sources = Object.entries(data.bySource).sort((a, b) => b[1] - a[1]);
  const share: [string, number][] = Object.entries(data.scoreBySource).sort((a, b) => b[1] - a[1]);
  const compact = (value: number) =>
    new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value);

  const top = data.items
    .filter((item) => platform === "all" || item.source === platform)
    .sort((a, b) => (Number(b.score) || 0) - (Number(a.score) || 0))
    .slice(0, 8);

  const scores = data.items
    .map((item) => Number(item.score) || 0)
    .filter((score) => score > 0)
    .sort((a, b) => b - a);
  const high = scores[0] ?? 0;
  const low = scores[scores.length - 1] ?? 0;
  const topItem = data.items[0];
  const latest = [...data.items]
    .sort((a, b) => (Date.parse(b.published || "") || 0) - (Date.parse(a.published || "") || 0))
    .slice(0, 3);

  function href(nextPlatform: string) {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (nextPlatform !== "all") params.set("platform", nextPlatform);
    const query = params.toString();
    return `/live${query ? `?${query}` : ""}`;
  }

  return (
    <section className="page active" id="page-overview">
      <h2 className="visually-hidden">Overview</h2>
      {job ? <JobStatus jobId={Number(job)} /> : null}
      {error === "keyword" ? (
        <div className="status err">Type a keyword before Search Now.</div>
      ) : null}
      {error === "jobs_table" ? (
        <div className="status err">
          Jobs table missing — run supabase/migrations/20261111000000_jobs.sql.
        </div>
      ) : null}
      <div className="kpis">
        <div className="card kpi">
          <div className="label">
            <span>Items saved</span>
          </div>
          <div className="big">{data.total.toLocaleString("en-US")}</div>
          <div className="delta">
            <small>Saved to Supabase · unique URL</small>
          </div>
        </div>
        <div className="card kpi">
          <div className="label">
            <span>Sources</span>
          </div>
          <div className="big">{sources.length}</div>
          <div className="delta">
            <small>
              {sources.length
                ? sources
                    .slice(0, 3)
                    .map(([source]) => sourceLabel(source))
                    .join(" · ")
                : "No sources"}
            </small>
          </div>
        </div>
        <div className="card kpi kpi-donut">
          <div className="label">
            <span>Signal points</span>
          </div>
          <Donut share={share} />
        </div>
        <div className="card kpi kpi-top">
          <div className="label">
            <span>Top item</span>
          </div>
          <div className="big">{topItem ? formatScore(topItem) : "0"}</div>
          <div className="top-title">{topItem?.title ?? "—"}</div>
          <div className="delta">
            <small>{topItem ? `${sourceLabel(topItem.source)} · highest score` : "—"}</small>
          </div>
        </div>
      </div>

      <div className="bottom">
        <div className="card">
          <div className="tbl-head">
            <h3>
              Top items ({top.length} of {data.total.toLocaleString("en-US")}
              {data.sampled ? " · sampled" : ""})
            </h3>
            <div className="tbl-tabs" role="tablist" aria-label="Top items by platform">
              <Link
                href={href("all")}
                className={platform === "all" ? "active" : ""}
                role="tab"
                aria-selected={platform === "all"}
              >
                All
              </Link>
              {sources.map(([source]) => (
                <Link
                  key={source}
                  href={href(source)}
                  className={platform === source ? "active" : ""}
                  role="tab"
                  aria-selected={platform === source}
                >
                  {sourceLabel(source)}
                </Link>
              ))}
            </div>
            <Link
              className="btn btn-ghost"
              href={`/live/items${q ? `?q=${encodeURIComponent(q)}` : ""}`}
              style={{ padding: "6px 12px", fontSize: 12 }}
            >
              View all →
            </Link>
          </div>
          <div className="tbl-scroll">
            {top.length ? (
              <ItemRows items={top} withSignal={false} />
            ) : (
              <div className="empty">No data yet. Choose a keyword and click Fetch now.</div>
            )}
          </div>
        </div>
        <div className="side-stack">
          <div className="card">
            <div className="card-head">
              <h3>Top terms (sample)</h3>
              <span className="chart-note">
                {data.sampled
                  ? `top ${data.sampleSize.toLocaleString("en-US")} of ${data.total.toLocaleString("en-US")} items`
                  : "all items"}
              </span>
              <Link
                className="btn btn-ghost"
                href="/live/terms"
                style={{ padding: "6px 12px", fontSize: 12 }}
              >
                Details →
              </Link>
            </div>
            <div className="terms">
              {data.topTerms.length ? (
                data.topTerms.map(([word, count]) => (
                  <span className="term" key={word}>
                    {word}
                    <b>{count}</b>
                  </span>
                ))
              ) : (
                <div className="empty">No data yet</div>
              )}
            </div>
          </div>
          <div className="card">
            <div className="card-head">
              <h3>Latest saved</h3>
              <Link
                className="btn btn-ghost"
                href="/live/items"
                style={{ padding: "6px 12px", fontSize: 12 }}
              >
                All items →
              </Link>
            </div>
            <ul className="latest-list">
              {latest.length ? (
                latest.map((item) => (
                  <li key={item.id ?? item.url}>
                    <a href={item.url} target="_blank" rel="noopener noreferrer">
                      {item.title}
                    </a>
                    <span>
                      {sourceLabel(item.source)}
                      {item.published
                        ? ` · ${new Date(item.published).toLocaleDateString("en-GB", {
                            day: "2-digit",
                            month: "short",
                          })}`
                        : ""}
                    </span>
                  </li>
                ))
              ) : (
                <li className="empty">No items yet — run a manual collect first.</li>
              )}
            </ul>
          </div>
        </div>
      </div>

      <div className="mid">
        <div className="card chart-card">
          <div className="card-head">
            <h3>Score by source</h3>
            <span className="chart-note">
              Signal points · {compact(data.metrics.views)} views · {compact(data.metrics.plays)}{" "}
              plays · {compact(data.metrics.likes)} likes
            </span>
          </div>
          <Bars share={share} />
        </div>
        <div className="mid-side">
          <div className="card inv">
            <div className="label">
              <span>Average score</span>
            </div>
            <div className="amount">{data.avgScore.toLocaleString("en-US")}</div>
            <div className="sub">Per scored item</div>
          </div>
          <div className="card inv">
            <div className="label">
              <span>Keyword coverage</span>
            </div>
            <div className="amount">{data.topTerms.length} terms</div>
            <div className="sub">Top terms found</div>
          </div>
        </div>
      </div>

      <div className="extra">
        <div className="card">
          <div className="card-head">
            <h3>Score distribution</h3>
            <span className="chart-note">
              {scores.length
                ? data.sampled
                  ? `sample ${data.sampleSize.toLocaleString("en-US")} of ${data.total.toLocaleString("en-US")} · ${low.toLocaleString("en-US")}–${high.toLocaleString("en-US")}`
                  : `${scores.length}/${data.total} scored · ${low.toLocaleString("en-US")}–${high.toLocaleString("en-US")}`
                : "No scored items"}
            </span>
          </div>
          <div className="line-box">
            <LineChart values={data.items.map((item) => Number(item.score) || 0)} />
          </div>
          <div className="metric-grid" style={{ marginTop: 12 }}>
            <div className="m">
              <b>{high.toLocaleString("en-US")}</b>
              <span>Highest score</span>
            </div>
            <div className="m">
              <b>{low.toLocaleString("en-US")}</b>
              <span>Lowest score</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
