import { queryItems, type SortKey } from "@/lib/data/items-query";
import type { Item } from "@/lib/types";

const SORTS: SortKey[] = ["score", "published", "created_at", "source", "title"];

function cell(value: unknown): string {
  const text = value == null ? "" : String(value);
  return `"${text.replace(/"/g, '""').replace(/\r?\n/g, " ")}"`;
}

export async function GET(request: Request) {
  const sp = new URL(request.url).searchParams;
  const q = sp.get("q") ?? "";
  const source = sp.get("source") ?? "";
  const from = sp.get("from") ?? "";
  const to = sp.get("to") ?? "";
  const sortParam = sp.get("sort") as SortKey | null;
  const sort = sortParam && SORTS.includes(sortParam) ? sortParam : "score";
  const dir = sp.get("dir") === "asc" ? "asc" : "desc";

  const items: Item[] = [];
  for (let page = 1; ; page += 1) {
    const chunk = await queryItems({
      state: "active",
      q,
      source,
      from,
      to,
      sort,
      dir,
      page,
      pageSize: 1000,
    });
    items.push(...chunk.items);
    if (!chunk.items.length || items.length >= chunk.total) break;
  }

  const header = [
    "keyword",
    "source",
    "title",
    "author",
    "url",
    "score",
    "metric",
    "published",
    "created_at",
  ];
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
  const csv = `\uFEFF${[header.join(","), ...rows].join("\r\n")}`;
  return new Response(csv, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": 'attachment; filename="items.csv"',
    },
  });
}
