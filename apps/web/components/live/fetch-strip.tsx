import { enqueueFetch } from "@/app/live/actions";
import type { Profile } from "@/lib/types";

import { SourceIcon } from "./source-icon";

export function FetchStrip({
  profiles = [],
  enabled = true,
}: {
  profiles?: Profile[];
  enabled?: boolean;
}) {
  if (!enabled) {
    return (
      <div className="status">Read-only live deployment — Search Now and edits are disabled.</div>
    );
  }

  return (
    <div className="fetch-strip">
      <form className="fetch-main" action={enqueueFetch}>
        <div className="field">
          <label htmlFor="profileSel">โปรไฟล์</label>
          <select id="profileSel" name="profile" defaultValue="">
            <option value="">Keyword ใหม่</option>
            {profiles.map((profile) => (
              <option key={profile.id ?? profile.name} value={profile.id}>
                {profile.name}
              </option>
            ))}
          </select>
        </div>
        <div className="field grow">
          <label htmlFor="q">Keyword</label>
          <input type="text" id="q" name="q" placeholder="Keyword…" />
        </div>
        <div className="field">
          <span className="field-label">Sources</span>
          <details className="src-pop">
            <summary>
              <span style={{ whiteSpace: "nowrap" }}>เลือกช่องทาง</span>
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                aria-hidden="true"
              >
                <path d="M6 9l6 6 6-6" />
              </svg>
            </summary>
            {/* biome-ignore lint/a11y/useSemanticElements: styled grouping div; fieldset would change layout */}
            <div className="src-picker" role="group" aria-label="fetch sources">
              <label className="src-option">
                <input type="checkbox" name="src" value="youtube" defaultChecked />
                <SourceIcon source="youtube" />
                <span className="src-main">
                  <span className="src-name">YouTube</span>
                  <span className="src-detail">youtube.com/results · stdlib scrape</span>
                </span>
              </label>
              <label className="src-option">
                <input type="checkbox" name="src" value="gnews" />
                <SourceIcon source="gnews" />
                <span className="src-main">
                  <span className="src-name">ข่าว (GNews)</span>
                  <span className="src-detail">news.google.com/rss · RSS</span>
                </span>
              </label>
              <label className="src-option">
                <input type="checkbox" name="src" value="tiktok" />
                <SourceIcon source="tiktok" />
                <span className="src-main">
                  <span className="src-name">TikTok</span>
                  <span className="src-detail">tiktok.com/search · Playwright</span>
                </span>
              </label>
              <label className="src-option">
                <input type="checkbox" name="src" value="fbads" />
                <SourceIcon source="fbads" />
                <span className="src-main">
                  <span className="src-name">FB Ads</span>
                  <span className="src-detail">facebook.com/ads/library · Playwright</span>
                </span>
              </label>
              <label className="src-option">
                <input type="checkbox" name="src" value="ttads" />
                <SourceIcon source="ttads" />
                <span className="src-main">
                  <span className="src-name">TikTok Ads</span>
                  <span className="src-detail">ads.tiktok.com/creativecenter · Playwright</span>
                </span>
              </label>
            </div>
          </details>
        </div>
        <div className="field">
          <label htmlFor="fetchMode">Mode</label>
          <select id="fetchMode" name="mode" defaultValue="public">
            <option value="public">Public</option>
            <option value="session">Login session</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="freshDays">Fresh</label>
          <select id="freshDays" name="fresh" defaultValue="30">
            <option value="1">1 วัน</option>
            <option value="3">3 วัน</option>
            <option value="7">7 วัน</option>
            <option value="15">15 วัน</option>
            <option value="30">30 วัน</option>
            <option value="0">ทั้งหมด</option>
          </select>
        </div>
        <button className="btn btn-primary fetch-btn" type="submit">
          Search Now
        </button>
      </form>
      <div className="status" role="status" aria-live="polite">
        Queued jobs run on the local worker · data in Supabase
      </div>
    </div>
  );
}
