import {
  ANALYSIS_FORMAT,
  ANALYSIS_MAX_ROWS,
  type AnalysisPage,
  type AnalysisScope,
  analysisCsv,
  analysisFilename,
  analysisGuide,
  analysisGuideFilename,
  collectAnalysisRows,
} from "@/lib/data/analysis-export";
import { queryItems, type SortKey } from "@/lib/data/items-query";

const SORTS: SortKey[] = ["score", "published", "created_at", "source", "title"];

function scopeFrom(sp: URLSearchParams): AnalysisScope {
  const sortParam = sp.get("sort") as SortKey | null;
  return {
    q: sp.get("q") ?? "",
    source: sp.get("source") ?? "",
    from: sp.get("from") ?? "",
    to: sp.get("to") ?? "",
    sort: sortParam && SORTS.includes(sortParam) ? sortParam : "score",
    dir: sp.get("dir") === "asc" ? "asc" : "desc",
  };
}

async function pageOf(scope: AnalysisScope, page: number, pageSize: number): Promise<AnalysisPage> {
  return queryItems({ state: "active", ...scope, page, pageSize });
}

type Counts = { rows: number; matching: number; truncated: boolean };

function responseHeaders(
  name: string,
  type: string,
  at: string,
  counts: Counts,
): Record<string, string> {
  return {
    "Content-Type": type,
    "Content-Disposition": `attachment; filename="${name}"`,
    "X-TrendRail-Export-Format": ANALYSIS_FORMAT,
    "X-TrendRail-Export-At": at,
    "X-TrendRail-Export-Rows": String(counts.rows),
    "X-TrendRail-Export-Total": String(counts.matching),
    "X-TrendRail-Export-Truncated": counts.truncated ? "1" : "0",
  };
}

export async function GET(request: Request) {
  const sp = new URL(request.url).searchParams;
  const scope = scopeFrom(sp);
  const exportedAt = new Date().toISOString();

  if (sp.get("format") === "guide") {
    // The guide reports the current filter count only; the CSV states its own row count.
    const { total } = await pageOf(scope, 1, 1);
    const guide = {
      scope,
      generatedAt: exportedAt,
      matching: total,
      truncated: total > ANALYSIS_MAX_ROWS,
    };
    return new Response(analysisGuide(guide), {
      headers: responseHeaders(
        analysisGuideFilename(guide),
        "text/markdown; charset=utf-8",
        exportedAt,
        { rows: 0, matching: total, truncated: guide.truncated },
      ),
    });
  }

  const { items, total, truncated } = await collectAnalysisRows((page, pageSize) =>
    pageOf(scope, page, pageSize),
  );
  const counts = { rows: items.length, matching: total, truncated };
  return new Response(analysisCsv(items, { scope, exportedAt, ...counts }), {
    headers: responseHeaders(
      analysisFilename({ scope, exportedAt, ...counts }),
      "text/csv; charset=utf-8",
      exportedAt,
      counts,
    ),
  });
}
