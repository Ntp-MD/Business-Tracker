"use client";

import { usePathname } from "next/navigation";

const TITLES: [string, string][] = [
  ["/live/sources", "Sources"],
  ["/live/terms", "Top Terms"],
  ["/live/ideas", "Content Ideas"],
  ["/live/items", "All Items"],
  ["/live/archive", "Archive"],
  ["/live/ads", "Ads Manager"],
  ["/live/settings", "Settings"],
  ["/live/trash", "Trash"],
  ["/live", "Overview"],
];

/** Page name in the topbar so the shell says where you are. */
export function PageTitle() {
  const path = usePathname();
  const title = TITLES.find(([href]) => path === href || path.startsWith(`${href}/`))?.[1];
  return <h1>{title ?? "Analytics"}</h1>;
}
