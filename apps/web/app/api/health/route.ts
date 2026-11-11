import { countItems } from "@/lib/data/items";

/** Read-only smoke check: proves the server can reach Supabase. */
export async function GET() {
  try {
    const [active, archived, trash] = await Promise.all([
      countItems("active"),
      countItems("archived"),
      countItems("trash"),
    ]);
    return Response.json({ ok: true, items: { active, archived, trash } });
  } catch (err) {
    const message = err instanceof Error ? err.message : "unknown error";
    return Response.json({ ok: false, error: message }, { status: 500 });
  }
}
