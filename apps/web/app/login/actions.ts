"use server";

import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { DEFAULT_NEXT, loginPath, safeNext } from "@/lib/auth/next";
import { createSupabaseServerClient } from "@/lib/supabase/ssr";

function siteUrl(requestHeaders: Headers): string {
  const configured = process.env.NEXT_PUBLIC_SITE_URL;
  if (configured) return configured.replace(/\/$/, "");

  const host = requestHeaders.get("host");
  if (!host) return "http://localhost:3000";
  const proto = requestHeaders.get("x-forwarded-proto") ?? "http";
  return `${proto}://${host}`;
}

export async function signInWithEmail(form: FormData): Promise<void> {
  const email = String(form.get("email") ?? "")
    .trim()
    .toLowerCase();
  const next = safeNext(form.get("next"));

  if (!email.includes("@")) {
    redirect(loginPath({ error: "Enter a valid email address.", next }));
  }

  const requestHeaders = await headers();
  const supabase = await createSupabaseServerClient();
  const callback = new URL(`${siteUrl(requestHeaders)}/auth/callback`);
  if (next !== DEFAULT_NEXT) callback.searchParams.set("next", next);
  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: {
      shouldCreateUser: false,
      emailRedirectTo: callback.toString(),
    },
  });

  if (error) {
    console.error("signInWithOtp failed:", error.message);
    redirect(loginPath({ error: "Could not send the magic link. Try again.", next }));
  }

  redirect(loginPath({ sent: true, next }));
}

export async function signInWithPassword(form: FormData): Promise<void> {
  const email = String(form.get("email") ?? "")
    .trim()
    .toLowerCase();
  const password = String(form.get("password") ?? "");
  const next = safeNext(form.get("next"));

  if (!email || !password) {
    redirect(loginPath({ error: "Enter email and password.", password: true, next }));
  }

  const supabase = await createSupabaseServerClient();
  const { error } = await supabase.auth.signInWithPassword({ email, password });

  if (error) {
    console.error("signInWithPassword failed:", error.message);
    redirect(loginPath({ error: "Invalid email or password.", password: true, next }));
  }

  redirect(next);
}
