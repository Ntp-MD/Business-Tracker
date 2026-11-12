import "server-only";

import { itemsTable } from "@/lib/data/read-tables";
import { supabaseAdmin } from "@/lib/supabase/server";
import type { Item, Profile } from "@/lib/types";
import { appVariant } from "@/lib/variant";

/** Words ignored by the legacy top-terms counter (server.py EN_STOP). */
const EN_STOP = new Set(
  `the and for with from this that these those have what when your you our into more than then them they about which their there`.split(
    " ",
  ),
);

export type Summary = {
  q: string;
  total: number;
  items: Item[];
  bySource: Record<string, number>;
  scoreBySource: Record<string, number>;
  totalScore: number;
  avgScore: number;
  metrics: { views: number; plays: number; likes: number; signals: number };
  sampleSize: number;
  sampled: boolean;
  topTerms: [string, number][];
  suggestions: string[];
  profiles: Profile[];
};

/** PostgREST caps a response at 1,000 rows; page through so totals are not sampled. */
const SUMMARY_PAGE_SIZE = 1000;
const SAMPLE_SIZE = 3000;

type SummaryRow = {
  source: string;
  metric: string | null;
  score: number | string | null;
  views: number | string | null;
};

const SUGGESTIONS = [
  "30-sec clip: open on the pain behind {q}, demo the fix, close with one LINE CTA.",
  'SEO post: answer "{q}" in one clear headline + hashtags + a single CTA.',
  "3-part FAQ: three shorts answering the most-asked questions about {q}.",
];

export function topTerms(items: Item[], limit = 12): [string, number][] {
  const counts = new Map<string, number>();
  for (const item of items) {
    const text = `${item.title ?? ""} ${item.body ?? ""}`.toLowerCase();
    for (const raw of text.split(/\s+/)) {
      const word = raw.replace(/^[.,:;()"'[\]*]+|[.,:;()"'[\]*]+$/g, "");
      if (word.length >= 4 && !EN_STOP.has(word)) {
        counts.set(word, (counts.get(word) ?? 0) + 1);
      }
    }
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, limit);
}

export async function getSummary(q = ""): Promise<Summary> {
  const db = supabaseAdmin();

  let countQuery = db
    .from(itemsTable())
    .select("id", { count: "exact", head: true })
    .is("deleted_at", null)
    .is("archived_at", null);
  if (q) countQuery = countQuery.eq("keyword", q);

  const profilePromise =
    appVariant() === "live"
      ? Promise.resolve({ data: [] as Profile[], error: null })
      : db.from("profiles").select("id,name,keywords,sources").order("name");

  const [{ count, error: countError }, profileRes] = await Promise.all([
    countQuery,
    profilePromise,
  ]);
  if (countError) throw new Error(`items count: ${countError.message}`);
  if (profileRes.error) throw new Error(`profiles: ${profileRes.error.message}`);

  const items: Item[] = [];
  for (let from = 0; from < SAMPLE_SIZE; from += SUMMARY_PAGE_SIZE) {
    const to = Math.min(from + SUMMARY_PAGE_SIZE, SAMPLE_SIZE) - 1;
    let sampleQuery = db
      .from(itemsTable())
      .select("*")
      .is("deleted_at", null)
      .is("archived_at", null)
      .order("score", { ascending: false })
      .order("id")
      .range(from, to);
    if (q) sampleQuery = sampleQuery.eq("keyword", q);
    const { data, error } = await sampleQuery;
    if (error) throw new Error(`items: ${error.message}`);
    items.push(...((data ?? []) as Item[]));
    if ((data?.length ?? 0) < to - from + 1) break;
  }

  const rows: SummaryRow[] = [];
  for (let from = 0; ; from += SUMMARY_PAGE_SIZE) {
    let pageQuery = db
      .from(itemsTable())
      .select("source,metric,score,views")
      .is("deleted_at", null)
      .is("archived_at", null)
      .order("id")
      .range(from, from + SUMMARY_PAGE_SIZE - 1);
    if (q) pageQuery = pageQuery.eq("keyword", q);
    const { data, error } = await pageQuery;
    if (error) throw new Error(`items summary: ${error.message}`);
    rows.push(...((data ?? []) as SummaryRow[]));
    if ((data?.length ?? 0) < SUMMARY_PAGE_SIZE) break;
  }

  const bySource: Record<string, number> = {};
  const scoreBySource: Record<string, number> = {};
  const metrics = { views: 0, plays: 0, likes: 0, signals: 0 };
  let totalScore = 0;
  let scoredCount = 0;
  for (const row of rows) {
    const score = Number(row.score) || 0;
    const views = Number(row.views) || 0;
    bySource[row.source] = (bySource[row.source] ?? 0) + 1;
    scoreBySource[row.source] = (scoreBySource[row.source] ?? 0) + score;
    totalScore += score;
    if (score > 0) scoredCount += 1;
    metrics.signals += score;
    if (row.metric === "views") metrics.views += views;
    else if (row.metric === "plays") metrics.plays += views;
    else if (row.metric === "likes") metrics.likes += views;
  }

  return {
    q,
    total: count ?? rows.length,
    items,
    bySource,
    scoreBySource,
    totalScore,
    avgScore: scoredCount ? Math.round(totalScore / scoredCount) : 0,
    metrics,
    sampleSize: items.length,
    sampled: (count ?? rows.length) > items.length,
    topTerms: topTerms(items),
    suggestions: q ? SUGGESTIONS.map((s) => s.replace("{q}", q)) : [],
    profiles: (profileRes.data ?? []) as Profile[],
  };
}

export async function listProfiles(): Promise<Profile[]> {
  const { data, error } = await supabaseAdmin()
    .from("profiles")
    .select("id,name,keywords,sources")
    .order("name");
  if (error) throw new Error(`profiles: ${error.message}`);
  return (data ?? []) as Profile[];
}

export const SOURCE_LABELS: Record<string, string> = {
  youtube: "YouTube",
  gnews: "Google News",
  tiktok: "TikTok",
  facebook: "Facebook",
  fbads: "FB Ads",
  ttads: "TikTok Ads",
  hackernews: "Hacker News",
};

export function sourceLabel(source: string): string {
  return SOURCE_LABELS[source] ?? source;
}

export function scoreBand(score: number): { label: string; cls: string } {
  if (score >= 500000) return { label: "Hot", cls: "hot" };
  if (score >= 100000) return { label: "Rising", cls: "rising" };
  return { label: "Steady", cls: "steady" };
}
