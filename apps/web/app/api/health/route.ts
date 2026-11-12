import { countItems } from "@/lib/data/items";
import { supabaseAdmin } from "@/lib/supabase/server";
import { appVariant } from "@/lib/variant";

const WORKER_STALE_MS = 5 * 60 * 1000;

/** Read-only smoke check: proves the server can reach Supabase and the worker is alive. */
export async function GET() {
  const requestId = crypto.randomUUID();
  try {
    const [active, archived, trash] = await Promise.all([
      countItems("active"),
      countItems("archived"),
      countItems("trash"),
    ]);

    let worker: { lastSeen: string | null; stale: boolean } | null = null;
    if (appVariant() !== "live") {
      const { data, error } = await supabaseAdmin()
        .from("worker_status")
        .select("last_seen")
        .eq("id", 1)
        .maybeSingle();
      if (error) throw new Error(`worker_status: ${error.message}`);
      const lastSeen = data?.last_seen ?? null;
      const stale = !lastSeen || Date.now() - new Date(lastSeen).getTime() > WORKER_STALE_MS;
      worker = { lastSeen, stale };
    }

    return Response.json(
      { ok: true, items: { active, archived, trash }, worker },
      { headers: { "x-request-id": requestId } },
    );
  } catch (err) {
    const message = err instanceof Error ? err.message : "unknown error";
    console.error(
      JSON.stringify({
        level: "error",
        event: "health_failed",
        request_id: requestId,
        error: message,
      }),
    );
    return Response.json(
      { ok: false, error: message },
      { status: 500, headers: { "x-request-id": requestId } },
    );
  }
}
