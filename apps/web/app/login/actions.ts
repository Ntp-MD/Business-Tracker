"use server";

import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { createSupabaseServerClient } from "@/lib/supabase/ssr";

function siteUrl(requestHeaders: Headers): string {
  const configured = process.env.NEXT_PUBLIC_SITE_URL;
  if (configured) return configured.replace(/\/$/, "");

  const host = requestHeaders.get("host");
  if (!host) return "http://localhost:3000";
  const proto = requestHeaders.get("x-forwarded-proto") ?? "http";
  return `${proto}://${host}`;
}

function safeNext(value: FormDataEntryValue | null): string {
  const next = String(value ?? "");
  return next.startsWith("/") && !next.startsWith("//") ? next : "/live";
}

export async function signInWithEmail(form: FormData): Promise<void> {
  const email = String(form.get("email") ?? "").trim().toLowerCase();
  const next = safeNext(form.get("next"));

  if (!email || !email.includes("@")) {
    redirect(`/login?error=${encodeURIComponent("Enter a valid email address.")}&next=${encodeURIComponent(next)}`);
  }

  const requestHeaders = await headers();
  const supabase = await createSupabaseServerClient();
  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: {
      shouldCreateUser: false,
      emailRedirectTo: `${siteUrl(requestHeaders)}/auth/callback`,
    },
  });

  if (error) {
    console.error("signInWithOtp failed:", error.message);
    redirect(`/login?error=${encodeURIComponent("Could not send the magic link. Try again.")}&next=${encodeURIComponent(next)}`);
  }

  redirect(`/login?sent=1&next=${encodeURIComponent(next)}`);
}
