import { NextResponse } from "next/server";

import { loginPath, safeNext } from "@/lib/auth/next";
import { isOwner } from "@/lib/auth/owner";
import { createSupabaseServerClient } from "@/lib/supabase/ssr";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const next = safeNext(url.searchParams.get("next"));

  const providerError = url.searchParams.get("error_description") ?? url.searchParams.get("error");
  if (providerError) {
    return NextResponse.redirect(new URL(loginPath({ error: providerError, next }), url.origin));
  }

  const code = url.searchParams.get("code");
  const tokenHash = url.searchParams.get("token_hash");
  const otpType = url.searchParams.get("type");
  if (!code && !(tokenHash && otpType)) {
    return NextResponse.redirect(
      new URL(loginPath({ error: "Missing login code.", next }), url.origin),
    );
  }

  const supabase = await createSupabaseServerClient();
  const { data, error } = code
    ? await supabase.auth.exchangeCodeForSession(code)
    : await supabase.auth.verifyOtp({ token_hash: tokenHash!, type: otpType as "magiclink" });
  if (error) {
    return NextResponse.redirect(
      new URL(loginPath({ error: "This login link is invalid or expired.", next }), url.origin),
    );
  }

  if (!isOwner(data.user?.id)) {
    await supabase.auth.signOut({ scope: "local" });
    return NextResponse.redirect(
      new URL(loginPath({ error: "This account does not have owner access.", next }), url.origin),
    );
  }

  return NextResponse.redirect(new URL(next, url.origin));
}
