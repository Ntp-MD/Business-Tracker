"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { createFetchJob } from "@/lib/data/jobs";
import { assertWritable } from "@/lib/variant";

export async function enqueueFetch(form: FormData): Promise<void> {
  assertWritable();
  const q = String(form.get("q") ?? "").trim();
  const profile = String(form.get("profile") ?? "").trim();
  if (!q && !profile) redirect("/live?error=keyword");

  const mode = String(form.get("mode") ?? "public");
  const max_age_days = Number(form.get("fresh") ?? 30) || 0;
  const payload = profile
    ? { profile_id: profile, mode, max_age_days }
    : { q, sources: form.getAll("src").map(String), mode, max_age_days };

  let id: number;
  try {
    id = await createFetchJob(payload);
  } catch {
    redirect("/live?error=jobs_table");
  }
  revalidatePath("/live");
  redirect(`/live?job=${id}`);
}
