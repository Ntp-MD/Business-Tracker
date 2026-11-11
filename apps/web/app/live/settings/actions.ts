"use server";

import { revalidatePath } from "next/cache";

import { supabaseAdmin } from "@/lib/supabase/server";

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
  revalidatePath("/live/settings");
}

export async function deleteProfile(id: string): Promise<void> {
  const { error } = await supabaseAdmin().from("profiles").delete().eq("id", id).eq("user_id", userId());
  if (error) throw new Error(error.message);
  revalidatePath("/live/settings");
}
