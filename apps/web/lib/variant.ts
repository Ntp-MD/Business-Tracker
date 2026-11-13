import "server-only";

export type AppVariant = "prod" | "mockup" | "live";

export function appVariant(): AppVariant {
  const value = process.env.APP_VARIANT;
  return value === "mockup" || value === "live" ? value : "prod";
}

export function isWritable(): boolean {
  return appVariant() === "prod";
}

export function assertWritable(): void {
  if (!isWritable()) throw new Error("Read-only deployment: writes are disabled");
}
