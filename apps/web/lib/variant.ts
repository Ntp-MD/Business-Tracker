import "server-only";

import { authBypassActive } from "@/lib/auth/bypass";

export type AppVariant = "prod" | "mockup" | "live";

export function appVariant(): AppVariant {
  const value = process.env.APP_VARIANT;
  return value === "mockup" || value === "live" ? value : "prod";
}

export function isWritable(): boolean {
  return appVariant() === "prod" && !authBypassActive();
}

export function assertWritable(): void {
  if (!isWritable()) throw new Error("Read-only deployment: writes are disabled");
}
