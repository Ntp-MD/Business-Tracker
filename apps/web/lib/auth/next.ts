export const DEFAULT_NEXT = "/live";

/** Only allow same-origin absolute paths; never protocol-relative or external URLs. */
export function safeNext(value: unknown): string {
  const next = typeof value === "string" ? value : String(value ?? "");
  const hasUnsafeCharacter = [...next].some((char) => {
    const code = char.charCodeAt(0);
    return char === "\\" || code < 32 || code === 127;
  });
  return next.startsWith("/") && !next.startsWith("//") && !hasUnsafeCharacter
    ? next
    : DEFAULT_NEXT;
}

/** Keep `/login` clean: omit the default `/live` target and empty options. */
export function loginPath(
  options: { error?: string; sent?: boolean; password?: boolean; next?: string } = {},
): string {
  const params = new URLSearchParams();
  if (options.error) params.set("error", options.error);
  if (options.sent) params.set("sent", "1");
  if (options.password) params.set("password", "1");
  const next = safeNext(options.next);
  if (next !== DEFAULT_NEXT) params.set("next", next);
  const query = params.toString();
  return query ? `/login?${query}` : "/login";
}
