import Link from "next/link";
import type { ReactNode } from "react";

import { FetchStrip } from "@/components/live/fetch-strip";
import { Sidebar } from "@/components/live/sidebar";
import { ThemeToggle } from "@/components/live/theme-toggle";
import { getCounts } from "@/lib/data/counts";

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
  let counts = { items: 0, sources: 0, archive: 0, ads: 0 };
  try {
    counts = await getCounts();
  } catch {
    // Supabase not configured yet: shell still renders.
  }

  return (
    <>
      <link rel="stylesheet" href="/assets/css/variables.css" />
      <link rel="stylesheet" href="/assets/css/base.css" />
      <link rel="stylesheet" href="/assets/css/component.css" />
      <link rel="stylesheet" href="/assets/css/layout-live.css" />
      <a className="skip-link" href="#live-content">
        Skip to content
      </a>
      <div className="app">
        <Sidebar counts={counts} />
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
            {MOBILE.map((item) => (
              <Link key={item.href} href={item.href}>
                {item.label}
              </Link>
            ))}
          </nav>
          <FetchStrip />
          <div id="live-content">{children}</div>
        </div>
      </div>
    </>
  );
}
