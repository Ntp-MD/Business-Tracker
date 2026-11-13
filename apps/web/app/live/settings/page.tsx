import { isOwner } from "@/lib/auth/owner";
import { getCounts } from "@/lib/data/counts";
import { getSummary, sourceLabel } from "@/lib/data/live";
import { createSupabaseServerClient } from "@/lib/supabase/ssr";

import { createProfile, deleteProfile, importItems, pruneOld } from "./actions";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  const [summary, counts] = await Promise.all([getSummary(), getCounts()]);

  let accountName = "—";
  let accountEmail = "—";
  let accountId: string | null = null;
  try {
    const supabase = await createSupabaseServerClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    const metadata = user?.user_metadata as Record<string, unknown> | undefined;
    accountName =
      (typeof metadata?.full_name === "string" && metadata.full_name) ||
      (typeof metadata?.name === "string" && metadata.name) ||
      user?.email?.split("@")[0] ||
      "—";
    accountEmail = user?.email ?? "—";
    accountId = user?.id ?? null;
  } catch {
    // The layout/proxy already guards this page; keep the section read-only.
  }

  const ownerLabel = isOwner(accountId) ? "Owner" : accountEmail !== "—" ? "Invited member" : "—";

  return (
    <section className="page active" id="page-settings">
      <h2 className="visually-hidden">Settings</h2>
      <div className="card account-card" id="account">
        <div className="card-head">
          <h3>Account</h3>
          <span className="chart-note">Read-only</span>
        </div>
        <div className="account-grid">
          <div>
            <span className="account-label">Name</span>
            <div className="account-value">{accountName}</div>
          </div>
          <div>
            <span className="account-label">Email</span>
            <div className="account-value">{accountEmail}</div>
          </div>
          <div>
            <span className="account-label">Access</span>
            <div className="account-value">{ownerLabel}</div>
          </div>
        </div>
        <p className="account-note">
          {ownerLabel === "Owner"
            ? "You own this workspace and its data."
            : "Invited members share this workspace and its data."}
        </p>
      </div>

      <div className="card" style={{ marginTop: 12 }}>
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
          <label>
            Profile name
            <input name="name" placeholder="เช่น ITOPPLUS" required />
          </label>
          <label>
            Keywords
            <input name="keywords" placeholder="คั่นด้วย ," />
          </label>
          <label>
            Sources
            <input name="sources" placeholder="youtube, gnews, tiktok" />
          </label>
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
          <label>
            JSON backup file
            <input type="file" name="file" accept="application/json,.json" required />
          </label>
          <button className="btn btn-primary" type="submit">
            Import JSON
          </button>
        </form>
      </div>

      <div className="card" style={{ marginTop: 12 }}>
        <div className="card-head">
          <h3>Collector sessions</h3>
          <span className="chart-note">Local only</span>
        </div>
        <p className="src-detail">
          TikTok / FB Ads / TikTok Ads ต้อง login session บนเครื่อง owner:{" "}
          <code>python backend/pw_login.py</code> แล้วรัน worker. Production ดูสถานะ session ไม่ได้ (ไม่มี
          service key ฝั่ง browser).
        </p>
      </div>

      <div className="card" style={{ marginTop: 12 }}>
        <div className="card-head">
          <h3>Prune old items</h3>
          <span className="chart-note">Organic sources only</span>
        </div>
        <form action={pruneOld} className="item-form">
          <label>
            Older than (days)
            <input name="days" type="number" min="1" step="1" placeholder="เช่น 30" required />
          </label>
          <button className="btn btn-ghost" type="submit">
            Prune
          </button>
        </form>
        <p className="src-detail">ลบถาวรเฉพาะ youtube / gnews / tiktok ที่เก่ากว่า N วัน; ads ไม่ถูกลบ</p>
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
