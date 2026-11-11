import "server-only";
import type { Item } from "@social-tracker/shared";

import { supabaseAdmin } from "@/lib/supabase/server";

export type ItemState = "active" | "archived" | "trash";
export type SortKey = "score" | "published" | "created_at" | "source" | "title";

export type ItemQuery = {
  state?: ItemState;
  q?: string;
  source?: string;
  sort?: SortKey;
  dir?: "asc" | "desc";
  page?: number;
  pageSize?: number;
};

export async function queryItems({
  state = "active",
  q = "",
  source = "",
  sort = "score",
  dir = "desc",
  page = 1,
  pageSize = 25,
}: ItemQuery): Promise<{ items: Item[]; total: number; page: number; pages: number }> {
  let query = supabaseAdmin().from("items").select("*", { count: "exact" });

  if (state === "active") query = query.is("deleted_at", null).is("archived_at", null);
  else if (state === "archived") query = query.is("deleted_at", null).not("archived_at", "is", null);
  else query = query.not("deleted_at", "is", null);

  if (source) query = query.eq("source", source);
  if (q) query = query.or(`title.ilike.%${q.replace(/[,%]/g, " ")}%,body.ilike.%${q.replace(/[,%]/g, " ")}%`);

  const from = (page - 1) * pageSize;
  const { data, error, count } = await query
    .order(sort, { ascending: dir === "asc", nullsFirst: false })
    .range(from, from + pageSize - 1);

  if (error) throw new Error(`items: ${error.message}`);
  const total = count ?? 0;
  return {
    items: (data ?? []) as Item[],
    total,
    page,
    pages: Math.max(1, Math.ceil(total / pageSize)),
  };
}

export async function getItem(id: string): Promise<Item | null> {
  const { data, error } = await supabaseAdmin().from("items").select("*").eq("id", id).maybeSingle();
  if (error) throw new Error(`item: ${error.message}`);
  return (data as Item) ?? null;
}

export async function getSourceStatus(): Promise<Record<string, { ok: boolean; message: string; at: string }>> {
  const { data, error } = await supabaseAdmin().from("source_status").select("source,ok,message,updated_at");
  if (error) return {};
  return Object.fromEntries(
    (data ?? []).map((row: { source: string; ok: boolean; message: string; updated_at: string }) => [
      row.source,
      { ok: row.ok, message: row.message, at: row.updated_at },
    ]),
  );
}
