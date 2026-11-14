import Link from "next/link";
import { redirect } from "next/navigation";
import { signOut } from "@/app/auth/actions";
import { BrandLogo } from "@/components/brand-logo";
import { CookieNotice } from "@/components/cookie-notice";
import { DEFAULT_NEXT, loginPath, safeNext } from "@/lib/auth/next";
import { canAccess } from "@/lib/auth/owner";
import { createSupabaseServerClient } from "@/lib/supabase/ssr";
import { appVariant } from "@/lib/variant";

import { signInWithEmail, signInWithGoogle, signInWithPassword } from "./actions";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Sign in · TrendRail",
  description: "Owner access to the TrendRail social intelligence console.",
};

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ sent?: string; error?: string; next?: string; password?: string }>;
}) {
  const variant = appVariant();
  if (variant !== "prod") redirect(variant === "mockup" ? "/" : "/live");

  const { sent, error, next, password } = await searchParams;
  const target = safeNext(next);
  const mockupUrl = process.env.NEXT_PUBLIC_MOCKUP_URL ?? "https://trendrail-mockup.vercel.app";

  // Old bookmarks such as /login?next=%2Flive should land on the clean /login.
  if (next && target === DEFAULT_NEXT) {
    redirect(
      loginPath({
        sent: Boolean(sent),
        error,
        password: Boolean(password),
      }),
    );
  }

  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (canAccess(user?.id, user?.email)) redirect(target);

  return (
    <>
      <link rel="stylesheet" href="/assets/css/variables.css" />
      <link rel="stylesheet" href="/assets/css/base.css" />
      <link rel="stylesheet" href="/assets/css/component.css" />
      <link rel="stylesheet" href="/assets/css/layout.css" />
      <link rel="stylesheet" href="/assets/css/demo.css" />
      <main className="login-shell">
        <section className="login-brand" aria-labelledby="login-brand-title">
          <div className="login-wordmark">
            <BrandLogo />
          </div>
          <div className="login-brand-body">
            <div className="login-brand-copy">
              <span className="login-eyebrow">Social intelligence</span>
              <h1 id="login-brand-title">
                Every signal.
                <br />
                One rail.
              </h1>
              <p>
                Trends, content, ads and leads for Thai brands — collected in one console and ready
                for the next move.
              </p>
            </div>
            <ul className="login-points">
              <li>
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <path d="M20 6 9 17l-5-5" />
                </svg>
                YouTube, Google News, TikTok, Facebook and TikTok Ads
              </li>
              <li>
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <path d="M20 6 9 17l-5-5" />
                </svg>
                Read-only live sharing for clients
              </li>
              <li>
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <path d="M20 6 9 17l-5-5" />
                </svg>
                Magic-link access with password fallback
              </li>
            </ul>
          </div>
          <div className="login-brand-bottom">
            <div className="login-brand-foot">
              <span>TrendRail 0.4</span>
              <span>Owner console</span>
            </div>
            <CookieNotice variant="brand" />
          </div>
        </section>

        <section className="login-main" aria-labelledby="login-title">
          <div className="card login-card">
            <div className="login-card-head">
              <span className="login-eyebrow">Owner access</span>
              <h2 id="login-title">Sign in to TrendRail</h2>
              <p>
                {password
                  ? "Continue with Google, or use the owner email and password."
                  : "Continue with Google, or use the owner email. We send a one-time link — no password is stored."}
              </p>
            </div>

            {sent ? (
              <div className="login-alert login-alert-ok" role="status">
                Check your inbox. The link expires shortly.
              </div>
            ) : null}
            {error ? (
              <div className="login-alert login-alert-err" role="alert">
                {error}
              </div>
            ) : null}

            {user ? (
              <div className="login-alert login-alert-err" role="alert">
                This account does not have access. Ask the owner for an invite.
                <form action={signOut}>
                  <button className="btn btn-ghost" type="submit">
                    Sign out and switch account
                  </button>
                </form>
              </div>
            ) : null}

            {password ? (
              <form action={signInWithPassword} className="login-form">
                <input type="hidden" name="next" value={target} />
                <label>
                  Owner email
                  <input
                    name="email"
                    type="email"
                    autoComplete="email"
                    placeholder="owner@email.com"
                    required
                  />
                </label>
                <label>
                  Password
                  <input
                    name="password"
                    type="password"
                    autoComplete="current-password"
                    placeholder="Enter your password"
                    required
                  />
                </label>
                <button className="btn btn-primary" type="submit">
                  Sign in with password
                </button>
              </form>
            ) : (
              <form action={signInWithEmail} className="login-form">
                <input type="hidden" name="next" value={target} />
                <label>
                  Owner email
                  <input
                    name="email"
                    type="email"
                    autoComplete="email"
                    placeholder="owner@email.com"
                    required
                  />
                </label>
                <button className="btn btn-primary" type="submit">
                  Send magic link
                </button>
              </form>
            )}

            <div className="login-divider">
              <span>or</span>
            </div>

            <form action={signInWithGoogle} className="login-form">
              <input type="hidden" name="next" value={target} />
              <button className="google-signin-btn" type="submit">
                <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                  <path
                    fill="#4285F4"
                    d="M21.35 12.2c0-.7-.06-1.37-.18-2.02H12v3.82h5.24a4.48 4.48 0 0 1-1.94 2.94v2.45h3.14c1.84-1.7 2.91-4.2 2.91-7.19z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 21.6c2.62 0 4.82-.87 6.43-2.35l-3.14-2.45c-.87.58-1.98.93-3.29.93-2.53 0-4.67-1.71-5.44-4.01H3.32v2.52A9.72 9.72 0 0 0 12 21.6z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M6.56 13.72a5.84 5.84 0 0 1 0-3.44V7.76H3.32a9.72 9.72 0 0 0 0 8.48l3.24-2.52z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 6.27c1.42 0 2.7.49 3.71 1.45l2.78-2.78A9.3 9.3 0 0 0 12 2.4a9.72 9.72 0 0 0-8.68 5.36l3.24 2.52C7.33 7.98 9.47 6.27 12 6.27z"
                  />
                </svg>
                Continue with Google
              </button>
            </form>

            {password ? (
              <Link className="login-alt" href={loginPath({ next: target })}>
                Use a magic link instead
              </Link>
            ) : (
              <Link className="login-alt" href={loginPath({ password: true, next: target })}>
                Use a password instead
              </Link>
            )}

            <div className="login-demo">
              <span className="login-demo-label">ยังไม่พร้อมเข้าสู่ระบบ?</span>
              <Link className="login-demo-link" href={mockupUrl}>
                ดู mockup <span aria-hidden="true">→</span>
              </Link>
            </div>

            <div className="login-foot-links">
              <Link className="login-back" href="/">
                ← Back to home
              </Link>
              <Link className="login-back" href="/privacy">
                Privacy &amp; cookies
              </Link>
            </div>
          </div>
        </section>
      </main>
    </>
  );
}
