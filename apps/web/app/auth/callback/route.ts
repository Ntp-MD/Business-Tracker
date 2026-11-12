import { NextResponse } from "next/server";

import { createSupabaseServerClient } from "@/lib/supabase/ssr";

function safeNext(value: string | null): string {
  return value && value.startsWith("/") && !value.startsWith("//") ? value : "/live";
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const next = safeNext(url.searchParams.get("next"));

  const providerError = url.searchParams.get("error_description") ?? url.searchParams.get("error");
  if (providerError) {
    return NextResponse.redirect(
      new URL(`/login?error=${encodeURIComponent(providerError)}&next=${encodeURIComponent(next)}`, url.origin),
    );
  }

  const code = url.searchParams.get("code");
  const tokenHash = url.searchParams.get("token_hash");
  const otpType = url.searchParams.get("type");
  if (!code && !(tokenHash && otpType)) {
    return NextResponse.redirect(
      new URL(`/login?error=${encodeURIComponent("Missing login code.")}&next=${encodeURIComponent(next)}`, url.origin),
    );
  }

  const supabase = await createSupabaseServerClient();
  const { error } = code
    ? await supabase.auth.exchangeCodeForSession(code)
    : await supabase.auth.verifyOtp({ token_hash: tokenHash!, type: otpType as "magiclink" });
  if (error) {
    return NextResponse.redirect(
      new URL(`/login?error=${encodeURIComponent("This login link is invalid or expired.")}&next=${encodeURIComponent(next)}`, url.origin),
    );
  }

  return NextResponse.redirect(new URL(next, url.origin));
}
