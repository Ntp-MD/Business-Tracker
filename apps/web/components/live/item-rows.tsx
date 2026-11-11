import type { ReactNode } from "react";
import type { Item } from "@social-tracker/shared";

import { scoreBand, sourceLabel } from "@/lib/data/live";

export function formatScore(item: Item): string {
  const score = Number(item.score) || 0;
  if (!score) return "—";
  const unit = item.metric && item.metric !== "none" ? ` ${item.metric}` : "";
  return score.toLocaleString("en-US") + unit;
}

export function ItemRows({
  items,
  withSignal = true,
  actions,
}: {
  items: Item[];
  withSignal?: boolean;
  actions?: (item: Item) => ReactNode;
}) {
  return (
    <table>
      <caption className="visually-hidden">Items by score</caption>
      <thead>
        <tr>
          <th scope="col">Source</th>
          <th scope="col">Title</th>
          <th scope="col">Metric</th>
          {withSignal && <th scope="col">Signal</th>}
          <th scope="col">Link</th>
          {actions && <th scope="col">Actions</th>}
        </tr>
      </thead>
      <tbody>
        {items.map((item) => {
          const band = scoreBand(Number(item.score) || 0);
          return (
            <tr key={item.id ?? `${item.keyword}-${item.canonical_url || item.url}`}>
              <td>
                <span className="src-name">{sourceLabel(item.source)}</span>
              </td>
              <td title={item.title}>
                <a className="row-title" href={item.url} target="_blank" rel="noopener noreferrer">
                  {item.title}
                </a>
                {item.author && (
                  <div className="row-channel-wrap">
                    <span className="row-channel">{item.author}</span>
                  </div>
                )}
              </td>
              <td>
                <b>{formatScore(item)}</b>
              </td>
              {withSignal && (
                <td>
                  <span className={`pill ${band.cls}`}>{band.label}</span>
                </td>
              )}
              <td>
                <a href={item.url} target="_blank" rel="noopener noreferrer" style={{ whiteSpace: "nowrap" }}>
                  Open →
                </a>
              </td>
              {actions && <td>{actions(item)}</td>}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
