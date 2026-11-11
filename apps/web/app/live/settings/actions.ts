"use server";

import { revalidatePath } from "next/cache";

import { supabaseAdmin } from "@/lib/supabase/server";
import { assertWritable } from "@/lib/variant";

function userId(): string {
  const id = process.env.SUPABASE_USER_ID;
  if (!id) throw new Error("SUPABASE_USER_ID missing");
  return id;
}

function list(value: FormDataEntryValue | null): string[] {
  return String(value ?? "")
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);
}

export async function createProfile(form: FormData): Promise<void> {
  assertWritable();
  const name = String(form.get("name") ?? "").trim();
  if (!name) return;
  const { error } = await supabaseAdmin().from("profiles").upsert(
    {
      user_id: userId(),
      name,
      keywords: list(form.get("keywords")),
      sources: list(form.get("sources"))
    },
    { onConflict: "user_id,name" },
  );
  if (error) throw new Error(error.message);
  revalidatePath("/live", "layout");
  revalidatePath("/live/settings");
}

export async function deleteProfile(id: string): Promise<void> {
  assertWritable();
  const { error } = await supabaseAdmin().from("profiles").delete().eq("id", id).eq("user_id", userId());
  if (error) throw new Error(error.message);
  revalidatePath("/live", "layout");
  revalidatePath("/live/settings");
}

type ImportItem = {
  keyword?: string;
  source?: string;
  url?: string;
  canonical_url?: string;
  title?: string;
  body?: string;
  author?: string;
  channel_url?: string;
  score?: number;
  metric?: string;
  views?: number | null;
  published?: string | null;
  asset?: string | null;
};

export async function pruneOld(form: FormData): Promise<void> {
  assertWritable();
  const days = Number(form.get("days") ?? 0);
  if (!Number.isFinite(days) || days <= 0) return;
  const cutoff = new Date(Date.now() - days * 86_400_000).toISOString();
  const { error } = await supabaseAdmin()
    .from("items")
    .delete()
    .lt("published", cutoff)
    .in("source", ["youtube", "gnews", "tiktok"])
    .eq("user_id", userId());
  if (error) throw new Error(error.message);
  revalidatePath("/live");
  revalidatePath("/live/items");
  revalidatePath("/live/settings");
}

export async function importItems(form: FormData): Promise<void> {
  assertWritable();
  const file = form.get("file");
  if (!(file instanceof File) || !file.size) return;

  const parsed = JSON.parse(await file.text()) as { format?: string; items?: ImportItem[] };
  if (parsed.format && parsed.format !== "social-tracker.items") throw new Error("unsupported format");
  const incoming = Array.isArray(parsed.items) ? parsed.items : [];
  const rows = incoming
    .filter((item) => item.keyword && item.url && item.title)
    .map((item) => ({
      user_id: userId(),
      keyword: item.keyword,
      source: item.source || "youtube",
      url: item.url,
      canonical_url: item.canonical_url || item.url,
      title: item.title,
      body: item.body ?? "",
      author: item.author ?? "",
      channel_url: item.channel_url ?? "",
      score: Number(item.score) || 0,
      metric: item.metric || "none",
      views: item.views ?? null,
      published: item.published || null,
      asset_path: item.asset || null,
    }));

  if (!rows.length) return;
  const { error } = await supabaseAdmin().from("items").upsert(rows, { onConflict: "user_id,keyword,canonical_url" });
  if (error) throw new Error(error.message);
  revalidatePath("/live");
  revalidatePath("/live/items");
  revalidatePath("/live/settings");
}
