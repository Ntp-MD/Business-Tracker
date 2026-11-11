import { getCounts } from "@/lib/data/counts";
import { getSummary, sourceLabel } from "@/lib/data/live";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  const [summary, counts] = await Promise.all([getSummary(), getCounts()]);

  return (
    <section className="page active" id="page-settings">
      <h2 className="visually-hidden">Settings</h2>
      <div className="card">
        <div className="card-head">
          <h3>Profiles</h3>
          <span className="chart-note">{summary.profiles.length} saved</span>
        </div>
        {summary.profiles.length ? (
          <div className="terms">
            {summary.profiles.map((profile) => (
              <span className="term" key={profile.id ?? profile.name}>
                {profile.name}
                <b>{profile.keywords?.length ?? 0}</b>
              </span>
            ))}
          </div>
        ) : (
          <div className="empty">No profiles yet.</div>
        )}
      </div>

      <div className="card" style={{ marginTop: 12 }}>
        <div className="card-head">
          <h3>Data</h3>
          <span className="chart-note">Supabase (service role, server-side)</span>
        </div>
        <div className="metric-grid">
          <div className="m">
            <b>{counts.items.toLocaleString("en-US")}</b>
            <span>Active items</span>
          </div>
          <div className="m">
            <b>{counts.archive.toLocaleString("en-US")}</b>
            <span>Archived</span>
          </div>
          <div className="m">
            <b>{counts.ads.toLocaleString("en-US")}</b>
            <span>Ads</span>
          </div>
          <div className="m">
            <b>{counts.sources}</b>
            <span>Sources</span>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 12 }}>
        <div className="card-head">
          <h3>Sources</h3>
          <span className="chart-note">Collectors</span>
        </div>
        <div className="terms">
          {Object.entries(summary.bySource).map(([source, count]) => (
            <span className="term" key={source}>
              {sourceLabel(source)}
              <b>{count}</b>
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
