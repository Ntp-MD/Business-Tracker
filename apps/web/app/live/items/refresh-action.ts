"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { createRefreshJob } from "@/lib/data/jobs";

export async function enqueueRefresh(form: FormData): Promise<void> {
  const q = String(form.get("q") ?? "").trim();
  let id: number;
  try {
    id = await createRefreshJob({ q });
  } catch {
    redirect("/live/items?error=jobs_table");
  }
  revalidatePath("/live/items");
  redirect(`/live/items?job=${id}`);
}
