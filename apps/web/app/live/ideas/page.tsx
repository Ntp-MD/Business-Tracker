import { getSummary } from "@/lib/data/live";

export const dynamic = "force-dynamic";

export default async function IdeasPage() {
  const data = await getSummary();
  const keywords = [...new Set(data.items.map((item) => item.keyword))].slice(0, 5);

  return (
    <section className="page active" id="page-ideas">
      <h2 className="visually-hidden">Content ideas</h2>
      {keywords.length ? (
        keywords.map((keyword) => (
          <div className="card" key={keyword} style={{ marginBottom: 12 }}>
            <div className="card-head">
              <h3>{keyword}</h3>
              <span className="chart-note">
                {data.items.filter((item) => item.keyword === keyword).length} items
              </span>
            </div>
            <ul className="suggest">
              {[
                `30-sec clip: open on the pain behind ${keyword}, demo the fix, close with one LINE CTA.`,
                `SEO post: answer "${keyword}" in one clear headline + hashtags + a single CTA.`,
                `3-part FAQ: three shorts answering the most-asked questions about ${keyword}.`,
              ].map((idea) => (
                <li key={idea}>{idea}</li>
              ))}
            </ul>
          </div>
        ))
      ) : (
        <div className="card">
          <div className="empty">No ideas yet — fetch a keyword first</div>
        </div>
      )}
    </section>
  );
}
