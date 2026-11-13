/** Production data belongs to the configured owner, regardless of sign-in method. */
export function isOwner(userId: string | null | undefined): boolean {
  const ownerId = process.env.SUPABASE_USER_ID;
  return Boolean(ownerId && userId && ownerId === userId);
}

/**
 * Owner is always allowed. Invite mode is opt-in and email-allowlisted, so a
 * public OAuth signup cannot get in even if Supabase signups are left on.
 */
export function canAccess(
  userId: string | null | undefined,
  email: string | null | undefined,
): boolean {
  if (isOwner(userId)) return true;
  if (process.env.ALLOW_INVITED_USERS !== "1") return false;
  if (!email) return false;
  const allowed = (process.env.INVITED_EMAILS ?? "")
    .split(",")
    .map((value) => value.trim().toLowerCase())
    .filter(Boolean);
  return allowed.includes(email.toLowerCase());
}
