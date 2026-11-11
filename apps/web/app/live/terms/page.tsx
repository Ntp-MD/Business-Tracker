import Link from "next/link";

import { getSummary } from "@/lib/data/live";

export const dynamic = "force-dynamic";

export default async function TermsPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q = "" } = await searchParams;
  const needle = q.trim().toLowerCase();
  const data = await getSummary();

  const byKeyword = new Map<string, number>();
  for (const item of data.items) {
    byKeyword.set(item.keyword, (byKeyword.get(item.keyword) ?? 0) + 1);
  }

  const terms = needle
    ? data.topTerms.filter(([word]) => word.toLowerCase().includes(needle))
    : data.topTerms;
  const keywords = [...byKeyword.entries()]
    .sort((a, b) => b[1] - a[1])
    .filter(([keyword]) => !needle || keyword.toLowerCase().includes(needle));

  return (
    <section className="page active" id="page-terms">
      <h2 className="visually-hidden">Top terms</h2>
      <form className="items-filters" action="/live/terms" method="get">
        <label>
          ค้นหา
          <input type="search" name="q" defaultValue={q} placeholder="Filter terms/keywords…" />
        </label>
        <button className="btn btn-primary" type="submit">
          Filter
        </button>
        <Link className="btn btn-ghost" href="/live/terms">
          Reset
        </Link>
      </form>
      <div className="card">
        <div className="card-head">
          <h3>
            Top terms · {data.items.length.toLocaleString("en-US")} items
            {needle ? ` · ${terms.length} match` : ""}
          </h3>
          <span className="chart-note">Words ≥ 4 characters</span>
        </div>
        <div className="terms">
          {terms.length ? (
            terms.map(([word, count]) => (
              <span className="term" key={word}>
                {word}
                <b>{count}</b>
              </span>
            ))
          ) : (
            <div className="empty">No terms match “{q}”.</div>
          )}
        </div>
      </div>
      <div className="card" style={{ marginTop: 12 }}>
        <div className="card-head">
          <h3>Keywords</h3>
          <span className="chart-note">{keywords.length} keywords</span>
        </div>
        <div className="terms">
          {keywords.length ? (
            keywords.map(([keyword, count]) => (
              <span className="term" key={keyword}>
                {keyword}
                <b>{count}</b>
              </span>
            ))
          ) : (
            <div className="empty">No keywords match “{q}”.</div>
          )}
        </div>
      </div>
    </section>
  );
}
