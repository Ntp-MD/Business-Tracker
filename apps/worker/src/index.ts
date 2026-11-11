/**
 * Worker entry — Phase 1 scaffold.
 * Collectors, job claim loop, and Playwright sessions arrive in Phase 5.
 */
const pollMs = Number(process.env.WORKER_POLL_MS ?? 2000);

async function tick(): Promise<void> {
  // Phase 5: claim one queued job atomically, run its collectors, write results.
  void pollMs;
}

console.log("social-tracker worker scaffold: no collectors yet (Phase 5)");
await tick();
