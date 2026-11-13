/** Production data belongs to the configured owner, regardless of sign-in method. */
export function isOwner(userId: string | null | undefined): boolean {
  const ownerId = process.env.SUPABASE_USER_ID;
  return Boolean(ownerId && userId && ownerId === userId);
}
