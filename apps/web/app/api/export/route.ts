import { queryItems } from "@/lib/data/items-query";

export async function GET() {
  const { items } = await queryItems({ pageSize: 3000 });
  const payload = {
    format: "social-tracker.items",
    version: 1,
    app_version: "0.2-next",
    exported_at: new Date().toISOString(),
    count: items.length,
    items,
  };
  return new Response(JSON.stringify(payload, null, 1), {
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Content-Disposition": 'attachment; filename="social-tracker-export.json"',
    },
  });
}
