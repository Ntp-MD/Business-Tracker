import { sourceLabel } from "@/lib/data/live";

const COLORS: Record<string, string> = {
  youtube: "#ff0033",
  gnews: "#2f6bff",
  tiktok: "#000000",
  facebook: "#1877F2",
  fbads: "#0b4f9e",
  ttads: "#334155",
};

function color(source: string, index: number): string {
  return COLORS[source] ?? ["#2f6bff", "#06b6d4", "#a855f7", "#f59e0b", "#22c55e"][index % 5];
}

export function Donut({ share }: { share: [string, number][] }) {
  const total = share.reduce((sum, [, value]) => sum + value, 0);
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;

  return (
    <div>
      <div className="donut-wrap">
        <svg className="donut" viewBox="0 0 140 140" role="img" aria-label="score share by source">
          <circle cx="70" cy="70" r={radius} fill="none" stroke="var(--line-2)" strokeWidth="16" />
          {total > 0 &&
            share.map(([source, value], index) => {
              const length = (value / total) * circumference;
              const dash = `${length} ${circumference - length}`;
              const el = (
                <circle
                  key={source}
                  cx="70"
                  cy="70"
                  r={radius}
                  fill="none"
                  stroke={color(source, index)}
                  strokeWidth="16"
                  strokeDasharray={dash}
                  strokeDashoffset={-offset}
                  transform="rotate(-90 70 70)"
                />
              );
              offset += length;
              return el;
            })}
        </svg>
        <div className="kpi-vals">
          <div className="big">{total.toLocaleString("en-US")}</div>
          <div className="delta">
            <small>score share by source</small>
          </div>
        </div>
      </div>
      <div className="donut-legend">
        {share.map(([source, value], index) => (
          <span key={source} className="legend-item">
            <i style={{ background: color(source, index) }} />
            {sourceLabel(source)} {total ? Math.round((value / total) * 100) : 0}%
          </span>
        ))}
      </div>
    </div>
  );
}

export function Bars({ share }: { share: [string, number][] }) {
  const max = Math.max(1, ...share.map(([, value]) => value));
  if (!share.length) return <div className="empty">No data yet</div>;
  return (
    <div className="bars">
      {share.map(([source, value], index) => (
        <div className="bar-col" key={source}>
          <div className="bar-val">{value.toLocaleString("en-US")}</div>
          <div className="bar-track">
            <div
              className="bar-fill"
              style={{ height: `${Math.max(3, Math.round((value / max) * 100))}%`, background: color(source, index) }}
              title={`${sourceLabel(source)}: ${value.toLocaleString("en-US")} score`}
            />
          </div>
          <div className="bar-label">{sourceLabel(source)}</div>
        </div>
      ))}
    </div>
  );
}

export function LineChart({ values }: { values: number[] }) {
  const scored = values.filter((v) => v > 0).sort((a, b) => b - a);
  if (!scored.length) return <svg viewBox="0 0 800 200" preserveAspectRatio="none" role="img" aria-label="Score distribution" />;
  const high = Math.max(...scored);
  const low = Math.min(...scored);
  const span = high - low || 1;
  const points = scored
    .map((value, index) => {
      const x = (index * 800) / Math.max(1, scored.length - 1);
      const y = 185 - ((value - low) / span) * 155;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg viewBox="0 0 800 200" preserveAspectRatio="none" role="img" aria-label="Score distribution line chart">
      {[60, 110, 160].map((y) => (
        <line key={y} x1="0" y1={y} x2="800" y2={y} stroke="var(--line-2)" vectorEffect="non-scaling-stroke" />
      ))}
      <polygon fill="rgba(34,197,94,.12)" points={`0,200 ${points} 800,200`} />
      <polyline fill="none" stroke="#22c55e" strokeWidth="2.5" vectorEffect="non-scaling-stroke" points={points} />
    </svg>
  );
}
