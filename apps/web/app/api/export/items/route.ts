import { queryItems } from "@/lib/data/items-query";

function cell(value: unknown): string {
  const text = value == null ? "" : String(value);
  return `"${text.replace(/"/g, '""').replace(/\r?\n/g, " ")}"`;
}

export async function GET() {
  const { items } = await queryItems({ pageSize: 3000 });
  const header = ["keyword", "source", "title", "author", "url", "score", "metric", "published", "created_at"];
  const rows = items.map((item) =>
    [
      item.keyword,
      item.source,
      item.title,
      item.author,
      item.url,
      item.score,
      item.metric,
      item.published,
      item.created_at,
    ]
      .map(cell)
      .join(","),
  );
  const csv = "\uFEFF" + [header.join(","), ...rows].join("\r\n");
  return new Response(csv, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": 'attachment; filename="items.csv"',
    },
  });
}
