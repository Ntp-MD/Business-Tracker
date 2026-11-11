import Link from "next/link";
import { notFound } from "next/navigation";

import { getItem } from "@/lib/data/items-query";
import { sourceLabel } from "@/lib/data/live";

import { updateItem } from "../../actions";

export const dynamic = "force-dynamic";

export default async function EditItemPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const item = await getItem(id);
  if (!item) notFound();

  return (
    <section className="page active">
      <div className="card">
        <div className="card-head">
          <h3>Edit item</h3>
          <span className="chart-note">{sourceLabel(item.source)}</span>
        </div>
        <form action={updateItem.bind(null, id)} className="item-form">
          <label>
            Keyword
            <input name="keyword" defaultValue={item.keyword} required />
          </label>
          <label>
            Title
            <input name="title" defaultValue={item.title} required />
          </label>
          <label>
            Body
            <textarea name="body" defaultValue={item.body} rows={3} />
          </label>
          <label>
            Channel / page
            <input name="author" defaultValue={item.author} />
          </label>
          <label>
            Score
            <input name="score" type="number" min="0" step="1" defaultValue={Number(item.score) || 0} />
          </label>
          <div className="row-actions">
            <button className="btn btn-primary" type="submit">
              Save
            </button>
            <Link className="btn btn-ghost" href="/live/items">
              Cancel
            </Link>
          </div>
        </form>
      </div>
    </section>
  );
}
