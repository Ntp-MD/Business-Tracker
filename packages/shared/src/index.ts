export type Source = "youtube" | "gnews" | "tiktok" | "fbads" | "ttads";

/** Mirrors the current `items` row (docs/DB.md). */
export interface Item {
  id: string;
  keyword: string;
  source: Source;
  url: string;
  canonicalUrl: string;
  title: string;
  body?: string | null;
  author?: string | null;
  channelUrl?: string | null;
  score: number;
  metric?: string | null;
  views?: number | null;
  published?: string | null;
  assetPath?: string | null;
  archivedAt?: string | null;
  deletedAt?: string | null;
}

/** Mirrors the current `profiles` row. */
export interface Profile {
  id: string;
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
  cancelRequested: boolean;
}
