import Link from "next/link";
import { redirect } from "next/navigation";

import { BrandLogo } from "@/components/brand-logo";
import { CookieNotice } from "@/components/cookie-notice";
import { DEFAULT_NEXT, loginPath, safeNext } from "@/lib/auth/next";
import { createSupabaseServerClient } from "@/lib/supabase/ssr";
import { appVariant } from "@/lib/variant";

import { signInWithEmail, signInWithPassword } from "./actions";

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
  if (user) redirect(target);

  return (
    <>
      <link rel="stylesheet" href="/assets/css/variables.css" />
      <link rel="stylesheet" href="/assets/css/base.css" />
      <link rel="stylesheet" href="/assets/css/component.css" />
      <link rel="stylesheet" href="/assets/css/layout.css" />
      <main className="login-shell">
        <section className="login-brand" aria-labelledby="login-brand-title">
          <div className="login-wordmark">
            <BrandLogo />
          </div>
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
          <div className="login-brand-bottom">
            <CookieNotice variant="brand" />
            <div className="login-brand-foot">
              <span>TrendRail 0.2</span>
              <span>Owner console</span>
            </div>
          </div>
        </section>

        <section className="login-main" aria-labelledby="login-title">
          <div className="card login-card">
            <div className="login-card-head">
              <span className="login-eyebrow">Owner access</span>
              <h2 id="login-title">Sign in to TrendRail</h2>
              <p>
                {password
                  ? "Use the owner email and password, or switch back to a magic link."
                  : "Use the owner email. We send a one-time link — no password is stored."}
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

            {password ? (
              <Link className="login-alt" href={loginPath({ next: target })}>
                Use a magic link instead
              </Link>
            ) : (
              <Link className="login-alt" href={loginPath({ password: true, next: target })}>
                Use a password instead
              </Link>
            )}

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
