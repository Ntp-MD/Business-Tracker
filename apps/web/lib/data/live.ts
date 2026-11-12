import "server-only";
import type { Item, Profile } from "@/lib/types";

import { itemsTable } from "@/lib/data/read-tables";
import { supabaseAdmin } from "@/lib/supabase/server";
import { appVariant } from "@/lib/variant";

/** Words ignored by the legacy top-terms counter (server.py EN_STOP). */
const EN_STOP = new Set(
  `the and for with from this that these those have what when your you our into more than then them they about which their there`
    .split(" "),
);

export type Summary = {
  q: string;
  total: number;
  items: Item[];
  bySource: Record<string, number>;
  totalScore: number;
  avgScore: number;
  topTerms: [string, number][];
  suggestions: string[];
  profiles: Profile[];
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
  let query = db
    .from(itemsTable())
    .select("*")
    .is("deleted_at", null)
    .is("archived_at", null)
    .order("score", { ascending: false })
    .limit(3000);
  if (q) query = query.eq("keyword", q);

  const profilePromise =
    appVariant() === "live"
      ? Promise.resolve({ data: [] as Profile[], error: null })
      : db.from("profiles").select("id,name,keywords,sources").order("name");

  const [{ data, error }, profileRes] = await Promise.all([query, profilePromise]);
  if (error) throw new Error(`items: ${error.message}`);
  if (profileRes.error) throw new Error(`profiles: ${profileRes.error.message}`);

  const items = (data ?? []) as Item[];
  const bySource: Record<string, number> = {};
  let totalScore = 0;
  let scoredCount = 0;
  for (const item of items) {
    bySource[item.source] = (bySource[item.source] ?? 0) + 1;
    const score = Number(item.score) || 0;
    totalScore += score;
    if (score > 0) scoredCount += 1;
  }

  return {
    q,
    total: items.length,
    items,
    bySource,
    totalScore,
    avgScore: scoredCount ? Math.round(totalScore / scoredCount) : 0,
    topTerms: topTerms(items),
    suggestions: q ? SUGGESTIONS.map((s) => s.replace("{q}", q)) : [],
    profiles: (profileRes.data ?? []) as Profile[],
  };
}

export async function listProfiles(): Promise<Profile[]> {
  const { data, error } = await supabaseAdmin().from("profiles").select("id,name,keywords,sources").order("name");
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
};

export function sourceLabel(source: string): string {
  return SOURCE_LABELS[source] ?? source;
}

export function scoreBand(score: number): { label: string; cls: string } {
  if (score >= 500000) return { label: "Hot", cls: "hot" };
  if (score >= 100000) return { label: "Rising", cls: "rising" };
  return { label: "Steady", cls: "steady" };
}
