import "server-only";

import { itemsTable } from "@/lib/data/read-tables";
import { supabaseAdmin } from "@/lib/supabase/server";
import type { Item, Profile } from "@/lib/types";

export type ItemState = "active" | "archived" | "trash";

/** Apply the archive/trash filters used by the legacy app (docs/DB.md). */
function scoped(state: ItemState) {
  const table = supabaseAdmin().from(itemsTable());
  if (state === "active") return table.select("*").is("deleted_at", null).is("archived_at", null);
  if (state === "archived")
    return table.select("*").is("deleted_at", null).not("archived_at", "is", null);
  return table.select("*").not("deleted_at", "is", null);
}

export async function listItems(
  opts: { keyword?: string; state?: ItemState; limit?: number } = {},
): Promise<Item[]> {
  let query = scoped(opts.state ?? "active")
    .order("score", { ascending: false })
    .limit(opts.limit ?? 50);
  if (opts.keyword) query = query.eq("keyword", opts.keyword);

  const { data, error } = await query;
  if (error) throw new Error(`items: ${error.message}`);
  return (data ?? []) as Item[];
}

export async function countItems(state: ItemState = "active"): Promise<number> {
  let query = supabaseAdmin().from(itemsTable()).select("id", { count: "exact", head: true });
  if (state === "active") query = query.is("deleted_at", null).is("archived_at", null);
  else if (state === "archived")
    query = query.is("deleted_at", null).not("archived_at", "is", null);
  else query = query.not("deleted_at", "is", null);

  const { count, error } = await query;
  if (error) throw new Error(`items count: ${error.message}`);
  return count ?? 0;
}

export async function listProfiles(): Promise<Profile[]> {
  const { data, error } = await supabaseAdmin()
    .from("profiles")
    .select("id,name,keywords,sources")
    .order("name");
  if (error) throw new Error(`profiles: ${error.message}`);
  return (data ?? []) as Profile[];
}
