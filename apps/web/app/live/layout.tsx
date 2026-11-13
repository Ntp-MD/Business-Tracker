import Link from "next/link";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { FetchStrip } from "@/components/live/fetch-strip";
import { Sidebar } from "@/components/live/sidebar";
import { ThemeToggle } from "@/components/live/theme-toggle";
import { authBypassUntil } from "@/lib/auth/bypass";
import { getCounts } from "@/lib/data/counts";
import { listProfiles } from "@/lib/data/live";
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
  if (appVariant() === "mockup") redirect("/");
  const writable = isWritable();
  const bypassUntil = authBypassUntil();
  const bypassLabel = bypassUntil
    ? new Intl.DateTimeFormat("th-TH", {
        dateStyle: "medium",
        timeStyle: "short",
        timeZone: "Asia/Bangkok",
      }).format(bypassUntil)
    : null;

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
      <link rel="stylesheet" href="/assets/css/demo.css" />
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
              <div className="user">
                <span className="avatar">IT</span>
                <span className="uname">ITOPPLUS</span>
              </div>
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
          {bypassLabel ? (
            <div className="bypass-banner" role="status">
              <b>Demo mode</b> · อ่านอย่างเดียว · หมดอายุ {bypassLabel}
            </div>
          ) : null}
          <div id="live-content">{children}</div>
        </div>
      </div>
    </>
  );
}
