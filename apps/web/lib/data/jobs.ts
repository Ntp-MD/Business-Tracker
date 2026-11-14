import "server-only";

import { supabaseAdmin } from "@/lib/supabase/server";

export type FetchPayload = {
  q?: string;
  profile_id?: string;
  sources?: string[];
  mode?: string;
  max_age_days?: number;
};

export type CollectPayload = {
  connector_id: string;
  scope: { keyword: string };
  mode?: string;
  dry_run?: boolean;
  max_records?: number;
};

export async function createFetchJob(payload: FetchPayload): Promise<number> {
  return createJob("fetch", payload);
}

export async function createRefreshJob(payload: FetchPayload): Promise<number> {
  return createJob("refresh_views", payload);
}

export async function createCollectJob(payload: CollectPayload): Promise<number> {
  return createJob("collect", payload);
}

async function createJob(
  kind: "fetch" | "refresh_views" | "collect",
  payload: Record<string, unknown>,
): Promise<number> {
  const userId = process.env.SUPABASE_USER_ID;
  if (!userId) throw new Error("SUPABASE_USER_ID missing");

  const { data, error } = await supabaseAdmin()
    .from("jobs")
    .insert({ user_id: userId, kind, payload })
    .select("id")
    .single();
  if (error) throw new Error(error.message);
  return Number((data as { id: number }).id);
}

export async function getJob(id: number) {
  const db = supabaseAdmin();
  const [{ data, error }, worker] = await Promise.all([
    db
      .from("jobs")
      .select("id,status,progress,total,error,created_at,started_at,finished_at")
      .eq("id", id)
      .maybeSingle(),
    db.from("worker_status").select("last_seen").eq("id", 1).maybeSingle(),
  ]);
  if (error) throw new Error(error.message);

  const lastSeen = (worker.data as { last_seen?: string } | null)?.last_seen ?? null;
  return {
    job: data,
    worker: {
      lastSeen,
      online: Boolean(lastSeen && Date.now() - Date.parse(lastSeen) < 30_000),
    },
  };
}

export type CollectJob = {
  id: number;
  status: string;
  progress: number;
  total: number;
  error: string | null;
  created_at: string;
};

export async function listCollectJobs(limit = 5): Promise<CollectJob[]> {
  const userId = process.env.SUPABASE_USER_ID;
  if (!userId) return [];
  const { data, error } = await supabaseAdmin()
    .from("jobs")
    .select("id,status,progress,total,error,created_at")
    .eq("user_id", userId)
    .eq("kind", "collect")
    .order("created_at", { ascending: false })
    .limit(limit);
  if (error) throw new Error(error.message);
  return (data ?? []) as CollectJob[];
}
