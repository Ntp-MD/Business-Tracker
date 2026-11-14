import "server-only";

import { aggregateCollectorStats, type SourceStats } from "@/lib/data/collector-stats";
import { itemsTable, sourceStatusTable } from "@/lib/data/read-tables";
import { supabaseAdmin } from "@/lib/supabase/server";
import type { Item } from "@/lib/types";

/** Columns the list/table renders; `body` is only read by the editor detail page. */
const ITEM_LIST_COLUMNS =
  "id,keyword,source,url,canonical_url,title,author,channel_url,score,metric,views,published,asset_path,archived_at,deleted_at,created_at,updated_at";
import { isWritable } from "@/lib/variant";

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
  from?: string;
  to?: string;
};

export async function queryItems({
  state = "active",
  q = "",
  source = "",
  sort = "score",
  dir = "desc",
  page = 1,
  pageSize = 25,
  from = "",
  to = "",
}: ItemQuery): Promise<{ items: Item[]; total: number; page: number; pages: number }> {
  let query = supabaseAdmin().from(itemsTable()).select(ITEM_LIST_COLUMNS, { count: "exact" });

  if (state === "active") query = query.is("deleted_at", null).is("archived_at", null);
  else if (state === "archived")
    query = query.is("deleted_at", null).not("archived_at", "is", null);
  else query = query.not("deleted_at", "is", null);

  if (source) query = query.eq("source", source);
  if (q) {
    const term = q.replace(/[,%]/g, " ").trim();
    if (term) {
      query = query.or(
        `title.ilike.%${term}%,body.ilike.%${term}%,source.ilike.%${term}%,author.ilike.%${term}%`,
      );
    }
  }
  if (from) query = query.gte("published", from);
  if (to) query = query.lte("published", `${to}T23:59:59`);

  const offset = (page - 1) * pageSize;
  const { data, error, count } = await query
    .order(sort, { ascending: dir === "asc", nullsFirst: false })
    .range(offset, offset + pageSize - 1);

  if (error) throw new Error(`items: ${error.message}`);
  const total = count ?? 0;
  // List rows omit `body` (ITEM_LIST_COLUMNS); nothing on the list/table renders it.
  return {
    items: (data ?? []) as unknown as Item[],
    total,
    page,
    pages: Math.max(1, Math.ceil(total / pageSize)),
  };
}

export const KNOWN_SOURCES = ["youtube", "gnews", "tiktok", "facebook", "fbads", "ttads"] as const;

export async function countArchived(): Promise<{
  total: number;
  bySource: Record<string, number>;
}> {
  const db = supabaseAdmin();
  const archived = () =>
    db
      .from(itemsTable())
      .select("id", { count: "exact", head: true })
      .is("deleted_at", null)
      .not("archived_at", "is", null);

  const [total, ...counts] = await Promise.all([
    archived(),
    ...KNOWN_SOURCES.map((source) => archived().eq("source", source)),
  ]);
  const firstError = [total, ...counts].find((res) => res.error)?.error;
  if (firstError) throw new Error(`archive: ${firstError.message}`);

  const bySource: Record<string, number> = {};
  KNOWN_SOURCES.forEach((source, index) => {
    const count = counts[index].count ?? 0;
    if (count > 0) bySource[source] = count;
  });
  return { total: total.count ?? 0, bySource };
}

export async function getItem(id: string): Promise<Item | null> {
  const { data, error } = await supabaseAdmin()
    .from(itemsTable())
    .select("*")
    .eq("id", id)
    .maybeSingle();
  if (error) throw new Error(`item: ${error.message}`);
  return (data as Item) ?? null;
}

export async function getSourceStatus(): Promise<
  Record<string, { ok: boolean; message: string; at: string; count: number }>
> {
  const { data, error } = await supabaseAdmin()
    .from(sourceStatusTable())
    .select("source,ok,error,checked_at,count");
  if (error) throw new Error(`source_status: ${error.message}`);
  return Object.fromEntries(
    (data ?? []).map(
      (row: {
        source: string;
        ok: boolean;
        error: string | null;
        checked_at: string;
        count: number | null;
      }) => [
        row.source,
        {
          ok: row.ok,
          message: row.error ?? "",
          at: row.checked_at,
          count: row.count ?? 0,
        },
      ],
    ),
  );
}

/** Owner-only accepted/rejected totals; public live intentionally omits them. */
export async function getCollectorStats(): Promise<Record<string, SourceStats>> {
  if (!isWritable()) return {};
  const userId = process.env.SUPABASE_USER_ID;
  if (!userId) return {};
  const { data, error } = await supabaseAdmin()
    .from("collector_state")
    .select("connector_id,counters")
    .eq("user_id", userId);
  if (error) return {};
  return aggregateCollectorStats((data ?? []) as { connector_id: string; counters: unknown }[]);
}
