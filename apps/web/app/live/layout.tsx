import Link from "next/link";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { FetchStrip } from "@/components/live/fetch-strip";
import { Sidebar } from "@/components/live/sidebar";
import { ThemeToggle } from "@/components/live/theme-toggle";
import { UserMenu } from "@/components/live/user-menu";
import { getCounts } from "@/lib/data/counts";
import { listProfiles } from "@/lib/data/live";
import { createSupabaseServerClient } from "@/lib/supabase/ssr";
import type { Profile } from "@/lib/types";
import { appVariant, isWritable } from "@/lib/variant";

export const dynamic = "force-dynamic";

const MOBILE = [
  { href: "/live", label: "Overview" },
  { href: "/live/sources", label: "Sources" },
  { href: "/live/terms", label: "Top Terms" },
  { href: "/live/ideas", label: "Ideas" },
  { href: "/live/items", label: "Items" },
  { href: "/live/archive", label: "Archive" },
  { href: "/live/ads", label: "Ads" },
  { href: "/live/settings", label: "Settings" },
];

export default async function LiveLayout({ children }: { children: ReactNode }) {
  const variant = appVariant();
  if (variant === "mockup") redirect("/");
  const writable = isWritable();

  let accountName = "";
  let accountEmail = "";
  if (variant === "prod") {
    try {
      const supabase = await createSupabaseServerClient();
      const {
        data: { user },
      } = await supabase.auth.getUser();
      const metadata = user?.user_metadata as Record<string, unknown> | undefined;
      accountName =
        (typeof metadata?.full_name === "string" && metadata.full_name) ||
        (typeof metadata?.name === "string" && metadata.name) ||
        user?.email?.split("@")[0] ||
        "Account";
      accountEmail = user?.email ?? "";
    } catch {
      // Auth is guarded by the proxy; keep the shell usable if lookup fails.
    }
  }

  let counts = { items: 0, sources: 0, archive: 0, ads: 0 };
  let profiles: Profile[] = [];
  try {
    counts = await getCounts();
  } catch {
    // Supabase not configured yet: shell still renders.
  }
  if (writable) {
    try {
      profiles = await listProfiles();
    } catch {
      // Profiles table missing: keep the keyword-only fetch form.
    }
  }

  return (
    <>
      <link rel="stylesheet" href="/assets/css/variables.css" />
      <link rel="stylesheet" href="/assets/css/base.css" />
      <link rel="stylesheet" href="/assets/css/component.css" />
      <link rel="stylesheet" href="/assets/css/layout.css" />
      <link rel="stylesheet" href="/assets/css/user-menu.css" />
      <a className="skip-link" href="#live-content">
        Skip to content
      </a>
      <div className="app">
        <Sidebar counts={counts} writable={writable} />
        <div className="main" id="top">
          <div className="topbar">
            <h1>Analytics</h1>
            <div className="top-actions">
              <ThemeToggle />
              <UserMenu
                mode={variant === "prod" ? "prod" : "public"}
                name={accountName}
                email={accountEmail}
              />
            </div>
          </div>
          <nav className="mobile-nav" aria-label="Mobile">
            {MOBILE.filter((item) => writable || item.href !== "/live/settings").map((item) => (
              <Link key={item.href} href={item.href}>
                {item.label}
              </Link>
            ))}
          </nav>
          <FetchStrip profiles={profiles} enabled={writable} />
          <div id="live-content">{children}</div>
        </div>
      </div>
    </>
  );
}
