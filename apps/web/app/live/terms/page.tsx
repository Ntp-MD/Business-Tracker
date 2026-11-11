import { getSummary } from "@/lib/data/live";

export const dynamic = "force-dynamic";

export default async function TermsPage() {
  const data = await getSummary();
  const byKeyword = new Map<string, number>();
  for (const item of data.items) {
    byKeyword.set(item.keyword, (byKeyword.get(item.keyword) ?? 0) + 1);
  }

  return (
    <section className="page active" id="page-terms">
      <h2 className="visually-hidden">Top terms</h2>
      <div className="card">
        <div className="card-head">
          <h3>Top terms · {data.items.length.toLocaleString("en-US")} items</h3>
          <span className="chart-note">Words ≥ 4 characters</span>
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
      <div className="card" style={{ marginTop: 12 }}>
        <div className="card-head">
          <h3>Keywords</h3>
          <span className="chart-note">{byKeyword.size} keywords</span>
        </div>
        <div className="terms">
          {[...byKeyword.entries()]
            .sort((a, b) => b[1] - a[1])
            .map(([keyword, count]) => (
              <span className="term" key={keyword}>
                {keyword}
                <b>{count}</b>
              </span>
            ))}
        </div>
      </div>
    </section>
  );
}
