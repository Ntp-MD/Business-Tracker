/**
 * One job execution, separate from polling so tests can inject fetch and patch.
 * Cancellation is cooperative: the collector checks `jobs.cancel_requested` at
 * checkpoints and returns `{cancelled: true}`; the job is then terminal, never retried.
 */

export type JobLike = {
  id: number;
  kind: string;
  payload: Record<string, unknown>;
};

export type RunnerDeps = {
  fetch: (input: string, init?: RequestInit) => Promise<Response>;
  patch: (id: number, body: Record<string, unknown>) => Promise<void>;
  api: string;
  collectorWrites: boolean;
  maxAttempts: number;
};

type JobOutput = {
  added?: number;
  duplicates?: number;
  errors?: string[];
  cancelled?: boolean;
  counters?: { accepted?: number; written?: number };
};

function cancelledNote(out: JobOutput): string {
  const written = out.counters?.written ?? 0;
  return `cancelled; ${written} written; rerun is safe`.slice(0, 500);
}

export async function runJob(job: JobLike, attempts: number, deps: RunnerDeps): Promise<void> {
  const payload = job.payload ?? {};
  const body =
    job.kind === "collect"
      ? { ...payload, job_id: job.id, dry_run: !deps.collectorWrites }
      : payload;
  try {
    const endpoint =
      job.kind === "refresh_views"
        ? "/api/refresh-stats"
        : job.kind === "fetch"
          ? "/api/fetch"
          : job.kind === "collect"
            ? "/api/collect"
            : null;
    if (!endpoint) throw new Error(`unknown job kind: ${job.kind}`);
    const res = await deps.fetch(`${deps.api}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`fetch ${res.status}: ${(await res.text()).slice(0, 200)}`);
    const out = (await res.json()) as JobOutput;
    if (out.cancelled) {
      await deps.patch(job.id, {
        status: "cancelled",
        finished_at: new Date().toISOString(),
        error: cancelledNote(out),
        lease_owner: null,
        lease_until: null,
      });
      return;
    }
    await deps.patch(job.id, {
      status: "done",
      finished_at: new Date().toISOString(),
      progress: 1,
      total: 1,
      error: out.errors?.length ? out.errors.join(" · ").slice(0, 500) : null,
      lease_owner: null,
      lease_until: null,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    if (attempts < deps.maxAttempts) {
      await deps.patch(job.id, {
        status: "queued",
        started_at: null,
        error: message.slice(0, 500),
        lease_owner: null,
        lease_until: null,
      });
      return;
    }
    await deps.patch(job.id, {
      status: "error",
      finished_at: new Date().toISOString(),
      error: message.slice(0, 500),
      lease_owner: null,
      lease_until: null,
    });
  }
}
