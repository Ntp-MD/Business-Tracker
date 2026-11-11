import { getCounts } from "@/lib/data/counts";
import { getSummary, sourceLabel } from "@/lib/data/live";

import { createProfile, deleteProfile, importItems } from "./actions";

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
          <div className="tbl-scroll">
            <table>
              <thead>
                <tr>
                  <th scope="col">Profile</th>
                  <th scope="col">Keywords</th>
                  <th scope="col">Sources</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {summary.profiles.map((profile) => (
                  <tr key={profile.id ?? profile.name}>
                    <td>{profile.name}</td>
                    <td>{(profile.keywords ?? []).join(", ") || "—"}</td>
                    <td>{(profile.sources ?? []).map(sourceLabel).join(", ") || "—"}</td>
                    <td>
                      <div className="row-actions">
                        <form action={deleteProfile.bind(null, profile.id!)}>
                          <button className="mini-btn danger" type="submit">
                            Delete
                          </button>
                        </form>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty">No profiles yet.</div>
        )}

        <form action={createProfile} className="item-form" style={{ marginTop: 12 }}>
          <input name="name" placeholder="Profile name" required aria-label="Profile name" />
          <input name="keywords" placeholder="keywords คั่นด้วย ," aria-label="Keywords" />
          <input name="sources" placeholder="youtube, gnews, tiktok" aria-label="Sources" />
          <button className="btn btn-primary" type="submit">
            Save profile
          </button>
        </form>
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
          <h3>Backup</h3>
          <span className="chart-note">JSON export/import</span>
        </div>
        <div className="row-actions" style={{ marginBottom: 12 }}>
          <a className="btn btn-ghost" href="/api/export">
            Export JSON
          </a>
          <a className="btn btn-ghost" href="/api/export/items">
            Export CSV
          </a>
        </div>
        <form action={importItems} className="item-form">
          <input type="file" name="file" accept="application/json,.json" required aria-label="Import JSON" />
          <button className="btn btn-primary" type="submit">
            Import JSON
          </button>
        </form>
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
