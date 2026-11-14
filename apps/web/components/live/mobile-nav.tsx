"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";

const ITEMS = [
  { href: "/live", label: "Overview" },
  { href: "/live/sources", label: "Sources" },
  { href: "/live/terms", label: "Top Terms" },
  { href: "/live/ideas", label: "Ideas" },
  { href: "/live/items", label: "Items" },
  { href: "/live/archive", label: "Archive" },
  { href: "/live/ads", label: "Ads" },
];

// Same roadmap teasers as the desktop sidebar (owner decision 2026-11-14).
const LOCKED = [{ label: "Calendar" }, { label: "Reports" }];

function LockIcon() {
  return (
    <svg
      className="lock-ico"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden="true"
      focusable="false"
    >
      <rect x="4" y="10.5" width="16" height="9.5" rx="2" />
      <path d="M8 10.5V7a4 4 0 0 1 8 0v3.5" />
    </svg>
  );
}

export function MobileNav({ writable = true }: { writable?: boolean }) {
  const path = usePathname();
  const navRef = useRef<HTMLElement>(null);

  // biome-ignore lint/correctness/useExhaustiveDependencies: re-scroll whenever the route changes
  useEffect(() => {
    // Keep the current page visible when the strip overflows on a phone.
    navRef.current
      ?.querySelector(".active")
      ?.scrollIntoView({ block: "nearest", inline: "center" });
  }, [path]);

  return (
    <nav className="mobile-nav" aria-label="Mobile" ref={navRef}>
      {ITEMS.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className={path === item.href ? "active" : undefined}
          aria-current={path === item.href ? "page" : undefined}
        >
          {item.label}
        </Link>
      ))}
      {LOCKED.map((item) => (
        <span key={item.label} className="locked" aria-disabled="true" title="Coming soon">
          {item.label}
          <LockIcon />
        </span>
      ))}
      {writable ? (
        <Link
          href="/live/settings"
          className={path === "/live/settings" ? "active" : undefined}
          aria-current={path === "/live/settings" ? "page" : undefined}
        >
          Settings
        </Link>
      ) : null}
    </nav>
  );
}
