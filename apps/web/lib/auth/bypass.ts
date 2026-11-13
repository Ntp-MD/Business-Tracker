/**
 * Temporary, server-only demo access. Both variables are required and the
 * window is enforced on every request; unset/expired means normal auth.
 * Never expose these as NEXT_PUBLIC_*.
 */
export function authBypassUntil(): Date | null {
  if (process.env.AUTH_BYPASS !== "1") return null;
  const raw = process.env.AUTH_BYPASS_UNTIL;
  if (!raw) return null;
  const until = new Date(raw);
  if (Number.isNaN(until.getTime()) || until.getTime() <= Date.now()) return null;
  return until;
}

export function authBypassActive(): boolean {
  return authBypassUntil() !== null;
}
