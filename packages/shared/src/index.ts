export type Source = "youtube" | "gnews" | "tiktok" | "fbads" | "ttads";

/** Item shape returned by the legacy API and stored in `items` (snake_case on purpose). */
export interface Item {
  id?: string;
  url: string;
  title: string;
  body: string;
  source: Source | string;
  keyword: string;
  author: string;
  score: number;
  created: string;
  created_at: string;
  asset: string | null;
  canonical_url: string;
  metric: string;
  views: number | null;
  channel_url: string;
  published: string;
  archived_at: string;
  deleted_at: string;
}

/** Mirrors the `profiles` row. */
export interface Profile {
  id?: string;
  name: string;
  keywords: string[];
  sources: Source[];
}

export type JobKind = "fetch" | "refresh_views";
export type JobStatus = "queued" | "running" | "done" | "error" | "cancelled";

/** Worker job row (MIGRATION-NEXT §6). */
export interface Job {
  id: string;
  kind: JobKind;
  status: JobStatus;
  payload: Record<string, unknown>;
  progress: number;
  total: number;
  error?: string | null;
  cancel_requested: boolean;
}
