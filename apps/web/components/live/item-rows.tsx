import type { ReactNode } from "react";
import { scoreBand, sourceLabel } from "@/lib/data/live";
import type { Item } from "@/lib/types";
import { SelectAll } from "./select-all";
import { SourceIcon } from "./source-icon";

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
  selectable = false,
}: {
  items: Item[];
  withSignal?: boolean;
  actions?: (item: Item) => ReactNode;
  selectable?: boolean;
}) {
  return (
    <table>
      <caption className="visually-hidden">Items by score</caption>
      <thead>
        <tr>
          {selectable && (
            <th scope="col" className="sel-cell">
              <SelectAll />
            </th>
          )}
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
              {selectable && (
                <td className="sel-cell">
                  <label className="check-hit">
                    <input
                      type="checkbox"
                      name="ids"
                      value={item.id}
                      aria-label={`Select ${item.title}`}
                    />
                  </label>
                </td>
              )}
              <td>
                <span className="src-cell">
                  <SourceIcon source={item.source} />
                  <span className="src-name">{sourceLabel(item.source)}</span>
                </span>
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
                <a
                  className="row-open"
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ whiteSpace: "nowrap" }}
                >
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
