/**
 * Local Playwright worker — polls Supabase `jobs` and drives the local collector
 * (`python backend/server.py` on 127.0.0.1:8000). Results are written by server.py to Supabase.
 *
 * Run: node --env-file=../../.env.local dist/index.js
 * Requires: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_USER_ID, LOCAL_API.
 */
import { type JobLike, runJob } from "./job-runner.js";

const SUPABASE_URL = (process.env.SUPABASE_URL ?? "").replace(/\/$/, "");
const KEY = process.env.SUPABASE_SERVICE_ROLE_KEY ?? "";
const USER_ID = process.env.SUPABASE_USER_ID ?? "";
const API = (process.env.LOCAL_API ?? "http://127.0.0.1:8000").replace(/\/$/, "");
const POLL_MS = Number(process.env.WORKER_POLL_MS ?? 3000);
const LEASE_MS = Number(process.env.WORKER_LEASE_MS ?? 3_600_000);
const MAX_ATTEMPTS = Number(process.env.WORKER_MAX_ATTEMPTS ?? 3);
const SCHEDULE_HOURS = Number(process.env.COLLECT_SCHEDULE_HOURS ?? 0);
const CONNECTORS = (process.env.COLLECT_CONNECTORS ?? "gnews_search")
  .split(",")
  .map((value) => value.trim())
  .filter(Boolean);
const COLLECTOR_WRITES = ["1", "true", "yes"].includes(
  (process.env.COLLECTOR_WRITE_ENABLED ?? "0").toLowerCase(),
);
const WORKER_ID = `${process.env.COMPUTERNAME ?? "worker"}-${process.pid}`;

type Job = JobLike & {
  attempts?: number;
  payload: {
    q?: string;
    sources?: string[];
    mode?: string;
    max_age_days?: number;
    profile_id?: string;
    connector_id?: string;
    scope?: { keyword?: string };
    dry_run?: boolean;
    max_records?: number;
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
  const now = new Date().toISOString();
  await fetch(
    `${SUPABASE_URL}/rest/v1/jobs?status=eq.running&lease_until=lt.${encodeURIComponent(now)}&user_id=eq.${USER_ID}`,
    {
      method: "PATCH",
      headers: headers(),
      body: JSON.stringify({ status: "queued", lease_owner: null, lease_until: null }),
    },
  );

  // `collect` jobs belong to the Python collector worker (backend/collectors/worker.py);
  // this worker keeps the legacy fetch and refresh jobs.
  const list = await fetch(
    `${SUPABASE_URL}/rest/v1/jobs?status=eq.queued&kind=neq.collect&user_id=eq.${USER_ID}&order=created_at&limit=1&select=id,kind,payload,attempts`,
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
      started_at: now,
      user_id: USER_ID,
      lease_owner: WORKER_ID,
      lease_until: new Date(Date.now() + LEASE_MS).toISOString(),
      attempts: (job.attempts ?? 0) + 1,
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

let lastScheduleCheck = 0;

async function scheduleCollect(): Promise<void> {
  if (!SCHEDULE_HOURS) return;
  if (Date.now() - lastScheduleCheck < 60_000) return;
  lastScheduleCheck = Date.now();

  const active = await fetch(
    `${SUPABASE_URL}/rest/v1/jobs?status=in.(queued,running)&kind=eq.collect&user_id=eq.${USER_ID}&select=id&limit=1`,
    { headers: headers() },
  );
  if (((await active.json()) as unknown[]).length) return;

  const res = await fetch(
    `${SUPABASE_URL}/rest/v1/profiles?select=keywords&user_id=eq.${USER_ID}`,
    { headers: headers() },
  );
  const profiles = (await res.json()) as { keywords?: string[] }[];
  const keywords = [
    ...new Set(profiles.flatMap((profile) => profile.keywords ?? []).filter(Boolean)),
  ];
  if (!keywords.length) return;

  const window = Math.floor(Date.now() / (SCHEDULE_HOURS * 3_600_000));
  const rows = keywords.flatMap((keyword) =>
    CONNECTORS.map((connector) => ({
      user_id: USER_ID,
      kind: "collect",
      payload: {
        connector_id: connector,
        scope: { keyword },
        mode: "scheduled",
        dry_run: true,
        max_records: 50,
      },
      schedule_key: `${connector}:${window}:${keyword}`,
    })),
  );
  // The schedule_key index is partial, so ignore a duplicate-key response instead of
  // using on_conflict.
  await fetch(`${SUPABASE_URL}/rest/v1/jobs`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(rows),
  });
}

async function tick(): Promise<void> {
  await heartbeat();
  await scheduleCollect();
  const job = await claim();
  if (!job) return;

  const check = await fetch(
    `${SUPABASE_URL}/rest/v1/jobs?id=eq.${job.id}&select=cancel_requested`,
    { headers: headers() },
  );
  const [row] = (await check.json()) as { cancel_requested: boolean }[];
  if (row?.cancel_requested) {
    await patch(job.id, {
      status: "cancelled",
      finished_at: new Date().toISOString(),
      lease_owner: null,
      lease_until: null,
    });
    return;
  }
  await runJob(job, job.attempts ?? 1, {
    fetch,
    patch,
    api: API,
    collectorWrites: COLLECTOR_WRITES,
    maxAttempts: MAX_ATTEMPTS,
  });
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
