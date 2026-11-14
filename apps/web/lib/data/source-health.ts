/** Derived source health for the Sources page; pure so it can be fixture-tested. */

export type SourceStatus = {
  ok: boolean;
  message: string;
  at: string;
  count: number;
};

export type SourceHealthState =
  | "ok"
  | "empty"
  | "rate_limited"
  | "blocked"
  | "parsing"
  | "error"
  | "not_run";

export type SourceHealth = {
  state: SourceHealthState;
  label: string;
  detail: string;
  stale: boolean;
};

const STALE_MS = 48 * 60 * 60 * 1000;

export function sourceHealth(status: SourceStatus | undefined, now = Date.now()): SourceHealth {
  if (!status) {
    return {
      state: "not_run",
      label: "Not run",
      detail: "No run recorded on this project.",
      stale: false,
    };
  }

  const at = Date.parse(status.at);
  const stale = Number.isFinite(at) && now - at > STALE_MS;

  if (status.ok) {
    return status.count > 0
      ? {
          state: "ok",
          label: "OK",
          detail: `Last run wrote ${status.count.toLocaleString("en-US")} record(s).`,
          stale,
        }
      : { state: "empty", label: "Empty", detail: "Last run wrote 0 records.", stale };
  }

  const detail = (status.message || "Unknown error").slice(0, 200);
  const text = detail.toLowerCase();
  if (/429|rate.?limit|too many/.test(text)) {
    return { state: "rate_limited", label: "Rate-limited", detail, stale };
  }
  if (/403|401|forbidden|unauthorized|blocked|denied/.test(text)) {
    return { state: "blocked", label: "Blocked", detail, stale };
  }
  if (/parse|json|html|decode|invalid/.test(text)) {
    return { state: "parsing", label: "Parsing", detail, stale };
  }
  return { state: "error", label: "Error", detail, stale };
}
