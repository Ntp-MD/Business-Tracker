import Link from "next/link";
import { redirect } from "next/navigation";

import { createSupabaseServerClient } from "@/lib/supabase/ssr";
import { appVariant } from "@/lib/variant";

import { signInWithEmail } from "./actions";

export const dynamic = "force-dynamic";

function safeNext(value: string | undefined): string {
  return value && value.startsWith("/") && !value.startsWith("//") ? value : "/live";
}

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ sent?: string; error?: string; next?: string }>;
}) {
  const variant = appVariant();
  if (variant !== "prod") redirect(variant === "mockup" ? "/" : "/live");

  const { sent, error, next } = await searchParams;
  const target = safeNext(next);

  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (user) redirect(target);

  return (
    <>
      <link rel="stylesheet" href="/assets/css/variables.css" />
      <link rel="stylesheet" href="/assets/css/base.css" />
      <link rel="stylesheet" href="/assets/css/component.css" />
      <link rel="stylesheet" href="/assets/css/layout.css" />
      <main style={{ maxWidth: 430, margin: "10vh auto", padding: 20 }}>
        <div className="card">
          <div className="card-head">
            <h3>Sign in</h3>
            <span className="chart-note">Owner only</span>
          </div>
          <p className="src-detail">
            We send a one-time magic link to the owner email. No password is stored in this app.
          </p>
          <form action={signInWithEmail} className="item-form">
            <input type="hidden" name="next" value={target} />
            <label>
              Email
              <input name="email" type="email" autoComplete="email" placeholder="owner@example.com" required />
            </label>
            <button className="btn btn-primary" type="submit">
              Send magic link
            </button>
          </form>
          {sent ? <div className="status">Check your email for the login link.</div> : null}
          {error ? <div className="status err">{error}</div> : null}
          <p className="src-detail" style={{ marginTop: 12 }}>
            <Link href="/">Back to mockup</Link>
          </p>
        </div>
      </main>
    </>
  );
}
