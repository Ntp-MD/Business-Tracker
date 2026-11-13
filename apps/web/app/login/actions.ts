"use server";

import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { DEFAULT_NEXT, loginPath, safeNext } from "@/lib/auth/next";
import { canAccess } from "@/lib/auth/owner";
import { createSupabaseServerClient } from "@/lib/supabase/ssr";
import { appVariant } from "@/lib/variant";

function siteUrl(requestHeaders: Headers): string {
  const configured = process.env.NEXT_PUBLIC_SITE_URL;
  if (configured) return configured.replace(/\/$/, "");

  const host = requestHeaders.get("host");
  if (!host) return "http://localhost:3000";
  const proto = requestHeaders.get("x-forwarded-proto") ?? "http";
  return `${proto}://${host}`;
}

export async function signInWithGoogle(form: FormData): Promise<void> {
  const variant = appVariant();
  if (variant !== "prod") redirect(variant === "mockup" ? "/" : "/live");

  const next = safeNext(form.get("next"));
  const requestHeaders = await headers();
  const callback = new URL(`${siteUrl(requestHeaders)}/auth/callback`);
  if (next !== DEFAULT_NEXT) callback.searchParams.set("next", next);

  const supabase = await createSupabaseServerClient();
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: callback.toString(),
      queryParams: { prompt: "select_account" },
    },
  });

  if (error || !data.url) {
    console.error("signInWithOAuth failed:", error?.message ?? "missing redirect URL");
    redirect(
      loginPath({
        error: "Google sign-in is unavailable right now. Use email instead.",
        next,
      }),
    );
  }

  redirect(data.url);
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
  const { data, error } = await supabase.auth.signInWithPassword({ email, password });

  if (error) {
    console.error("signInWithPassword failed:", error.message);
    redirect(loginPath({ error: "Invalid email or password.", password: true, next }));
  }

  if (!canAccess(data.user?.id, data.user?.email)) {
    await supabase.auth.signOut({ scope: "local" });
    redirect(
      loginPath({
        error: "This account does not have access. Ask the owner for an invite.",
        password: true,
        next,
      }),
    );
  }

  redirect(next);
}
