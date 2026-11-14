"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut } from "@/app/auth/actions";
import { BrandLogo } from "@/components/brand-logo";
import { PatchNotes } from "@/components/live/patch-notes";

const ITEMS = [
  { href: "/live", label: "Overview", icon: "M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z" },
  { href: "/live/sources", label: "Sources", icon: "M4 7h16M4 7v13h16V7M4 7l2-4h12l2 4" },
  {
    href: "/live/terms",
    label: "Top Terms",
    icon: "M21 11.5a8.5 8.5 0 0 1-12.4 7.5L3 21l2-5.6A8.5 8.5 0 1 1 21 11.5z",
  },
  {
    href: "/live/ideas",
    label: "Content Ideas",
    icon: "M12 3a6 6 0 0 0-3 11v3h6v-3a6 6 0 0 0-3-11zM9 21h6",
  },
  {
    href: "/live/items",
    label: "All Items",
    icon: "M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01",
  },
  { href: "/live/archive", label: "Archive", icon: "M3 4h18v5H3zM5 9v10h14V9M10 13h4" },
];

// Only the two roadmap menus stay as locked teasers (owner decision 2026-11-14).
const LOCKED = [
  {
    label: "Content Calendar",
    icon: "M3 4h18v18H3zM8 2v4M16 2v4M3 10h18",
  },
  {
    label: "Reports",
    icon: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M9 15l2 2 4-4",
  },
];

export function Sidebar({
  counts,
  writable = true,
}: {
  counts: { items: number; sources: number; archive: number; ads: number };
  writable?: boolean;
}) {
  const path = usePathname();
  return (
    <aside className="sidebar" aria-label="Primary">
      <div className="logo">
        <BrandLogo />
      </div>
      <nav className="nav">
        {ITEMS.map((item) => (
          <Link key={item.href} href={item.href} className={path === item.href ? "active" : ""}>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <path d={item.icon} />
            </svg>
            {item.label}
            {item.href === "/live/sources" && <span className="badge-n">{counts.sources}</span>}
            {item.href === "/live/items" && <span className="badge-n">{counts.items}</span>}
            {item.href === "/live/archive" && <span className="badge-n">{counts.archive}</span>}
          </Link>
        ))}
        <Link href="/live/ads">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <path d="M3 11l18-5-5 18-2.5-7.5L3 11z" />
          </svg>
          Ads Manager<span className="badge-n">{counts.ads}</span>
        </Link>
        {LOCKED.map((item) => (
          <span key={item.label} className="locked" aria-disabled="true" title="Coming soon">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <path d={item.icon} />
            </svg>
            {item.label}
            <svg
              className="lock-ico"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <rect x="4" y="10.5" width="16" height="9.5" rx="2" />
              <path d="M8 10.5V7a4 4 0 0 1 8 0v3.5" />
            </svg>
          </span>
        ))}
        <hr className="divider" />
        {writable ? (
          <Link href="/live/settings" className={path === "/live/settings" ? "active" : ""}>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.87 2 2 0 1 1-2.83 2.83 1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1.03 1.56 2 2 0 1 1-4 0 1.7 1.7 0 0 0-1.03-1.56 1.7 1.7 0 0 0-1.87.34 2 2 0 1 1-2.83-2.83 1.7 1.7 0 0 0 .34-1.87 1.7 1.7 0 0 0-1.56-1.03 2 2 0 1 1 0-4 1.7 1.7 0 0 0 1.56-1.03 1.7 1.7 0 0 0-.34-1.87 2 2 0 1 1 2.83-2.83 1.7 1.7 0 0 0 1.87.34 1.7 1.7 0 0 0 1.03-1.56 2 2 0 1 1 4 0 1.7 1.7 0 0 0 1.03 1.56 1.7 1.7 0 0 0 1.87-.34 2 2 0 1 1 2.83 2.83 1.7 1.7 0 0 0-.34 1.87 1.7 1.7 0 0 0 1.56 1.03 2 2 0 1 1 0 4 1.7 1.7 0 0 0-1.56 1.03z" />
            </svg>
            Settings
          </Link>
        ) : null}
      </nav>
      <div className="help-card ver-card">
        <div className="ver-top">
          <span className="ver-label">Version</span>
          <span className="ver-num">0.4</span>
        </div>
        <div className="ver-date">14 พ.ย. 2026</div>
        <PatchNotes />
        {writable ? (
          <form action={signOut}>
            <button className="btn btn-ghost" type="submit" style={{ width: "100%", marginTop: 8 }}>
              Sign out
            </button>
          </form>
        ) : null}
        <Link className="ver-legal" href="/privacy">
          Privacy &amp; cookies
        </Link>
      </div>
    </aside>
  );
}
