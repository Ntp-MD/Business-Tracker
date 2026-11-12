import "server-only";
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

import { appVariant } from "@/lib/variant";

let cached: SupabaseClient | null = null;

/**
 * Server-only Supabase client. Prod uses the service role key. Live uses the
 * public anon key plus the read-only views, so a code bypass still cannot write.
 */
export function supabaseAdmin(): SupabaseClient {
  if (cached) return cached;

  const liveAnon = appVariant() === "live" && process.env.LIVE_READ_ANON === "1";
  const url = liveAnon ? process.env.NEXT_PUBLIC_SUPABASE_URL : process.env.SUPABASE_URL;
  const key = liveAnon
    ? process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
    : process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    throw new Error(
      liveAnon
        ? "Supabase live read env missing: NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY"
        : "Supabase env missing: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY",
    );
  }

  cached = createClient(url, key, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
  return cached;
}
