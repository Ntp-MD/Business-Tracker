"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { createFetchJob } from "@/lib/data/jobs";

export async function enqueueFetch(form: FormData): Promise<void> {
  const q = String(form.get("q") ?? "").trim();
  if (!q) redirect("/live?error=keyword");

  const payload = {
    q,
    sources: form.getAll("src").map(String),
    mode: String(form.get("mode") ?? "public"),
    max_age_days: Number(form.get("fresh") ?? 30) || 0,
  };

  let id: number;
  try {
    id = await createFetchJob(payload);
  } catch {
    redirect("/live?error=jobs_table");
  }
  revalidatePath("/live");
  redirect(`/live?job=${id}`);
}
