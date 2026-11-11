import "server-only";

import { supabaseAdmin } from "@/lib/supabase/server";

export type Counts = { items: number; sources: number; archive: number; ads: number };

export async function getCounts(): Promise<Counts> {
  const db = supabaseAdmin();
  const [items, archive, ads, sources] = await Promise.all([
    db.from("items").select("id", { count: "exact", head: true }).is("deleted_at", null).is("archived_at", null),
    db.from("items").select("id", { count: "exact", head: true }).is("deleted_at", null).not("archived_at", "is", null),
    db
      .from("items")
      .select("id", { count: "exact", head: true })
      .is("deleted_at", null)
      .is("archived_at", null)
      .in("source", ["fbads", "ttads"]),
    db
      .from("items")
      .select("source")
      .is("deleted_at", null)
      .is("archived_at", null),
  ]);
  return {
    items: items.count ?? 0,
    archive: archive.count ?? 0,
    ads: ads.count ?? 0,
    sources: new Set((sources.data ?? []).map((row: { source: string }) => row.source)).size || 5,
  };
}
