import "server-only";

import { appVariant } from "@/lib/variant";

const useLiveViews = appVariant() === "live" && process.env.LIVE_READ_ANON === "1";

/** Read-only views for the public live deployment; base tables for prod. */
export function itemsTable(): "items" | "live_items" {
  return useLiveViews ? "live_items" : "items";
}

export function sourceStatusTable(): "source_status" | "live_source_status" {
  return useLiveViews ? "live_source_status" : "source_status";
}
