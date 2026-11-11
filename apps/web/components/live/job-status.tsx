"use client";

import { useEffect, useState } from "react";

type JobState = {
  job: { id: number; status: string; progress: number; total: number; error: string | null } | null;
  worker: { online: boolean; lastSeen: string | null };
};

const LABELS: Record<string, string> = {
  queued: "Queued",
  running: "Running",
  done: "Done",
  error: "Error",
  cancelled: "Cancelled",
};

export function JobStatus({ jobId }: { jobId: number }) {
  const [state, setState] = useState<JobState | null>(null);

  useEffect(() => {
    let stop = false;
    async function tick() {
      try {
        const res = await fetch(`/api/jobs/${jobId}`, { cache: "no-store" });
        if (res.ok) {
          const data = (await res.json()) as JobState;
          if (!stop) setState(data);
          if (["done", "error", "cancelled"].includes(data.job?.status ?? "")) return;
        }
      } catch {
        /* keep polling */
      }
      if (!stop) setTimeout(tick, 2500);
    }
    tick();
    return () => {
      stop = true;
    };
  }, [jobId]);

  if (!state?.job) return <div className="status">Job #{jobId} · loading…</div>;

  const { job, worker } = state;
  const hint =
    job.status === "queued" && !worker.online
      ? "Worker offline — job stays queued in Supabase. Start it on the owner's PC: python backend/server.py + npm run worker (see docs/DEPLOY.md)."
      : job.status === "queued"
        ? "Worker online — waiting for it to claim the job."
        : "";

  return (
    <div className={job.status === "error" ? "status err" : "status"} role="status" aria-live="polite">
      Job #{job.id} · {LABELS[job.status] ?? job.status}
      {job.total > 0 ? ` · ${job.progress}/${job.total}` : ""}
      {job.error ? ` · ${job.error}` : ""}
      {hint ? <div>{hint}</div> : null}
    </div>
  );
}
