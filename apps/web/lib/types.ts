/** Row shapes shared with the legacy API/DB (snake_case on purpose). */
export type Source = "youtube" | "gnews" | "tiktok" | "facebook" | "fbads" | "ttads";

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

export interface Profile {
  id?: string;
  name: string;
  keywords: string[];
  sources: Source[];
}
