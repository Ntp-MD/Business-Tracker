/**
 * Local Playwright worker — polls Supabase `jobs` and drives the local collector
 * (`python backend/server.py` on 127.0.0.1:8000). Results are written by server.py to Supabase.
 *
 * Run: node --env-file=../../.env.local dist/index.js
 * Requires: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_USER_ID, LOCAL_API.
 */
const SUPABASE_URL = (process.env.SUPABASE_URL ?? "").replace(/\/$/, "");
const KEY = process.env.SUPABASE_SERVICE_ROLE_KEY ?? "";
const USER_ID = process.env.SUPABASE_USER_ID ?? "";
const API = (process.env.LOCAL_API ?? "http://127.0.0.1:8000").replace(/\/$/, "");
const POLL_MS = Number(process.env.WORKER_POLL_MS ?? 3000);

type Job = {
  id: number;
  kind: string;
  payload: {
    q?: string;
    sources?: string[];
    mode?: string;
    max_age_days?: number;
    profile_id?: string;
  };
};

function headers(extra: Record<string, string> = {}) {
  return {
    apikey: KEY,
    Authorization: `Bearer ${KEY}`,
    "Content-Type": "application/json",
    ...extra,
  };
}

async function heartbeat(): Promise<void> {
  await fetch(`${SUPABASE_URL}/rest/v1/worker_status`, {
    method: "POST",
    headers: headers({ Prefer: "resolution=merge-duplicates" }),
    body: JSON.stringify({
      id: 1,
      last_seen: new Date().toISOString(),
      note: `pid ${process.pid}`,
    }),
  });
}

async function claim(): Promise<Job | null> {
  const list = await fetch(
    `${SUPABASE_URL}/rest/v1/jobs?status=eq.queued&order=created_at&limit=1&select=id,kind,payload`,
    {
      headers: headers(),
    },
  );
  const rows = (await list.json()) as Job[];
  const job = rows[0];
  if (!job) return null;

  const claimed = await fetch(`${SUPABASE_URL}/rest/v1/jobs?id=eq.${job.id}&status=eq.queued`, {
    method: "PATCH",
    headers: headers({ Prefer: "return=representation" }),
    body: JSON.stringify({
      status: "running",
      started_at: new Date().toISOString(),
      user_id: USER_ID,
    }),
  });
  const updated = (await claimed.json()) as Job[];
  return updated[0] ?? null;
}

async function patch(id: number, body: Record<string, unknown>): Promise<void> {
  await fetch(`${SUPABASE_URL}/rest/v1/jobs?id=eq.${id}`, {
    method: "PATCH",
    headers: headers(),
    body: JSON.stringify(body),
  });
}

async function run(job: Job): Promise<void> {
  const payload = job.payload ?? {};
  try {
    const endpoint = job.kind === "refresh_views" ? "/api/refresh-stats" : "/api/fetch";
    const res = await fetch(`${API}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`fetch ${res.status}: ${(await res.text()).slice(0, 200)}`);
    const out = (await res.json()) as { added?: number; duplicates?: number; errors?: string[] };
    await patch(job.id, {
      status: "done",
      finished_at: new Date().toISOString(),
      progress: 1,
      total: 1,
      error: out.errors?.length ? out.errors.join(" · ").slice(0, 500) : null,
    });
  } catch (err) {
    await patch(job.id, {
      status: "error",
      finished_at: new Date().toISOString(),
      error: err instanceof Error ? err.message : String(err),
    });
  }
}

async function tick(): Promise<void> {
  await heartbeat();
  const job = await claim();
  if (!job) return;

  const check = await fetch(
    `${SUPABASE_URL}/rest/v1/jobs?id=eq.${job.id}&select=cancel_requested`,
    { headers: headers() },
  );
  const [row] = (await check.json()) as { cancel_requested: boolean }[];
  if (row?.cancel_requested) {
    await patch(job.id, { status: "cancelled", finished_at: new Date().toISOString() });
    return;
  }
  await run(job);
}

async function main(): Promise<void> {
  if (!SUPABASE_URL || !KEY || !USER_ID) {
    console.error("missing SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SUPABASE_USER_ID");
    process.exit(1);
  }
  console.log(`worker polling every ${POLL_MS}ms; collector at ${API}`);
  for (;;) {
    try {
      await tick();
    } catch (err) {
      console.error("tick failed:", err instanceof Error ? err.message : err);
    }
    await new Promise((resolve) => setTimeout(resolve, POLL_MS));
  }
}

void main();
