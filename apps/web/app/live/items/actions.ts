"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { supabaseAdmin } from "@/lib/supabase/server";

function userId(): string {
  const id = process.env.SUPABASE_USER_ID;
  if (!id) throw new Error("SUPABASE_USER_ID missing");
  return id;
}

function text(form: FormData, key: string): string {
  return String(form.get(key) ?? "").trim();
}

export async function createItem(form: FormData): Promise<void> {
  const keyword = text(form, "keyword");
  const url = text(form, "url");
  const title = text(form, "title");
  if (!keyword || !url || !title) throw new Error("keyword, url and title are required");

  const { error } = await supabaseAdmin()
    .from("items")
    .upsert(
      {
        user_id: userId(),
        keyword,
        source: text(form, "source") || "youtube",
        url,
        canonical_url: url,
        title,
        body: text(form, "body"),
        author: text(form, "author"),
        score: Number(form.get("score")) || 0,
        metric: "views",
        published: text(form, "published") || null,
      },
      { onConflict: "user_id,keyword,canonical_url" },
    );
  if (error) throw new Error(error.message);

  revalidatePath("/live");
  revalidatePath("/live/items");
  redirect("/live/items");
}

export async function archiveItem(id: string): Promise<void> {
  const { error } = await supabaseAdmin()
    .from("items")
    .update({ archived_at: new Date().toISOString(), deleted_at: null })
    .eq("id", id)
    .eq("user_id", userId());
  if (error) throw new Error(error.message);
  revalidatePath("/live");
  revalidatePath("/live/items");
  revalidatePath("/live/archive");
}

export async function restoreItem(id: string): Promise<void> {
  const { error } = await supabaseAdmin()
    .from("items")
    .update({ archived_at: null, deleted_at: null })
    .eq("id", id)
    .eq("user_id", userId());
  if (error) throw new Error(error.message);
  revalidatePath("/live");
  revalidatePath("/live/archive");
  revalidatePath("/live/trash");
}

export async function deleteItem(id: string): Promise<void> {
  const { error } = await supabaseAdmin()
    .from("items")
    .update({ deleted_at: new Date().toISOString() })
    .eq("id", id)
    .eq("user_id", userId());
  if (error) throw new Error(error.message);
  revalidatePath("/live");
  revalidatePath("/live/items");
  revalidatePath("/live/archive");
  revalidatePath("/live/trash");
}

export async function purgeItem(id: string): Promise<void> {
  const { error } = await supabaseAdmin().from("items").delete().eq("id", id).eq("user_id", userId());
  if (error) throw new Error(error.message);
  revalidatePath("/live/trash");
}

export async function updateItem(id: string, form: FormData): Promise<void> {
  const { error } = await supabaseAdmin()
    .from("items")
    .update({
      title: text(form, "title"),
      body: text(form, "body"),
      author: text(form, "author"),
      keyword: text(form, "keyword"),
      score: Number(form.get("score")) || 0,
    })
    .eq("id", id)
    .eq("user_id", userId());
  if (error) throw new Error(error.message);
  revalidatePath("/live/items");
  redirect("/live/items");
}
