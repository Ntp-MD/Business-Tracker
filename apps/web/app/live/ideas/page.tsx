import Link from "next/link";

import { getSummary, sourceLabel } from "@/lib/data/live";

export const dynamic = "force-dynamic";

/** Ideas come from collected items, not invented prompts: recent high-score rows per keyword. */
export default async function IdeasPage() {
  const data = await getSummary();
  const byKeyword = new Map<string, typeof data.items>();
  for (const item of [...data.items].sort(
    (a, b) => (Number(b.score) || 0) - (Number(a.score) || 0),
  )) {
    const list = byKeyword.get(item.keyword) ?? [];
    if (list.length < 3 && item.title) list.push(item);
    byKeyword.set(item.keyword, list);
  }
  const groups = [...byKeyword.entries()].slice(0, 5);

  return (
    <section className="page active" id="page-ideas">
      <h2 className="visually-hidden">Content ideas</h2>
      {groups.length ? (
        groups.map(([keyword, items]) => (
          <div className="card" key={keyword} style={{ marginBottom: 12 }}>
            <div className="card-head">
              <h3>{keyword}</h3>
              <span className="chart-note">
                {data.items.filter((item) => item.keyword === keyword).length} items · repurpose the
                top {items.length}
              </span>
            </div>
            <ul className="latest-list">
              {items.map((item) => (
                <li key={item.id ?? item.url}>
                  <a href={item.url} target="_blank" rel="noopener noreferrer">
                    {item.title}
                  </a>
                  <span>
                    {sourceLabel(item.source)}
                    {Number(item.score) ? ` · ${Number(item.score).toLocaleString("en-US")}` : ""}
                  </span>
                </li>
              ))}
            </ul>
            <div className="card-head" style={{ marginTop: 10, marginBottom: 0 }}>
              <Link
                className="btn btn-ghost"
                href="/live/items?q="
                style={{ padding: "6px 12px", fontSize: 12 }}
              >
                Open in All Items →
              </Link>
            </div>
          </div>
        ))
      ) : (
        <div className="card">
          <div className="empty">No ideas yet — collect a keyword first.</div>
        </div>
      )}
    </section>
  );
}
