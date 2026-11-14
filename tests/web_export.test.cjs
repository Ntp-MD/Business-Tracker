// Exercise the analysis export CSV, guide, paging, and route with local fixtures only.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const Module = require("node:module");
const path = require("node:path");
const test = require("node:test");
const ts = require("typescript");

function load(relativePath, mocks = {}) {
  const filename = path.resolve(__dirname, "..", relativePath);
  const source = fs.readFileSync(filename, "utf8");
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const loaded = new Module(filename, module);
  loaded.filename = filename;
  loaded.paths = module.paths;
  loaded.require = (id) => (Object.hasOwn(mocks, id) ? mocks[id] : require(id));
  loaded._compile(compiled, filename);
  return loaded.exports;
}

const lib = load("apps/web/lib/data/analysis-export.ts");

function item(over = {}) {
  return {
    id: "item-1",
    url: "https://example.test/a",
    title: "Title",
    body: "body text",
    source: "youtube",
    keyword: "SEO",
    author: "Channel",
    score: 12,
    created: "",
    created_at: "2026-11-01T00:00:00Z",
    asset: null,
    canonical_url: "https://example.test/a",
    metric: "views",
    views: 12,
    channel_url: "",
    published: "2026-10-31T10:00:00Z",
    archived_at: "",
    deleted_at: "",
    ...over,
  };
}

const scope = { q: "", source: "", from: "", to: "", sort: "score", dir: "desc" };

test("CSV keeps the stable reference, units, and context", () => {
  const csv = lib.analysisCsv([item()], {
    scope,
    exportedAt: "2026-11-14T07:05:00.000Z",
    rows: 1,
    matching: 1,
    truncated: false,
  });
  const [header, row] = csv.replace(/^\uFEFF/, "").split("\r\n");
  assert.equal(
    header,
    "item_id,keyword,source,title,author,url,canonical_url,score,metric,views,published,collected_at,exported_at",
  );
  assert.equal(
    row,
    '"item-1","SEO","youtube","Title","Channel","https://example.test/a","https://example.test/a","12","views","12","2026-10-31T10:00:00Z","2026-11-01T00:00:00Z","2026-11-14T07:05:00.000Z"',
  );
  assert.equal(csv.charCodeAt(0), 0xfeff);
});

test("CSV escapes quotes, newlines, commas, and formulas", () => {
  const csv = lib.analysisCsv(
    [
      item({
        title: 'He said "hi",\nthen left',
        url: "https://example.test/a,b",
        author: "=HYPERLINK(\"https://evil.test\")",
      }),
    ],
    { scope, exportedAt: "2026-11-14T07:05:00.000Z", rows: 1, matching: 1, truncated: false },
  );
  const row = csv.split("\r\n")[1];
  assert.match(row, /"He said ""hi"", then left"/);
  assert.match(row, /"https:\/\/example\.test\/a,b"/);
  assert.match(row, /"'=HYPERLINK\(""https:\/\/evil\.test""\)"/);
  assert.equal(csv.split("\r\n").length, 2);
});

test("CSV keeps unknown metric values unknown", () => {
  const csv = lib.analysisCsv([item({ metric: "none", views: null, created_at: "", published: "" })], {
    scope,
    exportedAt: "2026-11-14T07:05:00.000Z",
    rows: 1,
    matching: 1,
    truncated: false,
  });
  const row = csv.split("\r\n")[1];
  assert.match(row, /"none","","",""/);
});

test("CSV keeps Thai text and repeated canonical URLs", () => {
  const csv = lib.analysisCsv(
    [
      item({
        id: "th-1",
        keyword: "ข่าว",
        title: "ข่าว SEO ภาษาไทย",
        url: "https://example.test/th",
        canonical_url: "https://example.test/th",
      }),
      item({
        id: "th-2",
        keyword: "SEO",
        title: "ข่าว SEO ภาษาไทย",
        url: "https://example.test/th",
        canonical_url: "https://example.test/th",
      }),
    ],
    { scope, exportedAt: "2026-11-14T07:05:00.000Z", rows: 2, matching: 2, truncated: false },
  );
  const rows = csv.split("\r\n");
  assert.equal(rows.length, 3);
  assert.match(rows[1], /"th-1","ข่าว","youtube","ข่าว SEO ภาษาไทย"/);
  assert.match(rows[2], /"th-2","SEO","youtube","ข่าว SEO ภาษาไทย"/);
  assert.equal(rows[1].match(/https:\/\/example\.test\/th/g).length, 2);
  assert.equal(rows[2].match(/https:\/\/example\.test\/th/g).length, 2);
});

test("empty export keeps the header and zero rows", () => {
  const csv = lib.analysisCsv([], {
    scope,
    exportedAt: "2026-11-14T07:05:00.000Z",
    rows: 0,
    matching: 0,
    truncated: false,
  });
  const lines = csv.replace(/^\uFEFF/, "").split("\r\n");
  assert.equal(lines.length, 1);
  assert.match(lines[0], /^item_id,keyword,/);
  assert.equal(
    lib.analysisFilename({
      scope,
      exportedAt: "2026-11-14T07:05:00.000Z",
      rows: 0,
      matching: 0,
      truncated: false,
    }),
    "trendrail-analysis-20261114T070500Z-0rows.csv",
  );
});

test("filenames carry the timestamp and included row count", () => {
  const ctx = {
    scope,
    exportedAt: "2026-11-14T07:05:00.000Z",
    rows: 324,
    matching: 324,
    truncated: false,
  };
  assert.equal(lib.analysisFilename(ctx), "trendrail-analysis-20261114T070500Z-324rows.csv");
  assert.equal(
    lib.analysisGuideFilename({ scope, generatedAt: ctx.exportedAt, matching: 324, truncated: false }),
    "trendrail-analysis-guide-20261114T070500Z.md",
  );
});

test("guide states scope, units, limits, and the sample prompt", () => {
  const guide = lib.analysisGuide({
    scope: { ...scope, q: "SEO|AI", source: "youtube", from: "2026-11-01", to: "2026-11-07" },
    generatedAt: "2026-11-14T07:05:00.000Z",
    matching: 42,
    truncated: false,
  });
  assert.match(guide, /Format: analysis-v1/);
  assert.match(guide, /Guide generated: 2026-11-14T07:05:00.000Z \(UTC\)/);
  assert.match(guide, /Rows matching these filters at generation: 42/);
  assert.match(guide, /Keyword search \(q\): SEO\\\|AI/);
  assert.match(guide, /Published from: 2026-11-01/);
  assert.match(guide, /No timezone conversion is applied/);
  assert.match(guide, /\| `item_id` \|/);
  assert.match(guide, /No metric observation time is stored/);
  assert.match(guide, /same `canonical_url` can appear more than once/);
  assert.match(guide, /body` is not exported/);
  assert.match(guide, /filename row count should equal the filter count above/);
  assert.ok(guide.includes(lib.ANALYSIS_PROMPT));
  assert.doesNotMatch(guide, /capped at/);
});

test("guide marks a capped export as truncated", () => {
  const guide = lib.analysisGuide({
    scope,
    generatedAt: "2026-11-14T07:05:00.000Z",
    matching: 12000,
    truncated: true,
  });
  assert.match(guide, /capped at 10,000 rows/);
});

test("paging stops at the reported total and at the row cap", async () => {
  const calls = [];
  const page = (items, total) => async (number) => {
    calls.push(number);
    return { items, total };
  };
  const single = await lib.collectAnalysisRows(page([item()], 1));
  assert.deepEqual(calls, [1]);
  assert.equal(single.truncated, false);

  calls.length = 0;
  const capped = await lib.collectAnalysisRows(
    page([item({ id: "a" }), item({ id: "b" })], 5),
    4,
  );
  assert.deepEqual(calls, [1, 2]);
  assert.equal(capped.items.length, 4);
  assert.equal(capped.truncated, true);

  calls.length = 0;
  const short = await lib.collectAnalysisRows(async (number) => {
    calls.push(number);
    return { items: number < 3 ? [item()] : [], total: 5 };
  });
  assert.equal(short.items.length, 2);
  assert.equal(short.total, 5);
  assert.equal(short.truncated, false);
});

test("route returns paged CSV with export metadata and filters", async () => {
  const calls = [];
  const queryItems = async (input) => {
    calls.push(input);
    return { items: [item()], total: 1, page: input.page, pages: 1 };
  };
  const { GET } = load("apps/web/app/api/export/analysis/route.ts", {
    "@/lib/data/items-query": { queryItems },
    "@/lib/data/analysis-export": lib,
  });
  const response = await GET(
    new Request("https://example.test/api/export/analysis?q=SEO&source=youtube&sort=evil&dir=asc"),
  );
  assert.equal(response.headers.get("content-type"), "text/csv; charset=utf-8");
  assert.match(
    response.headers.get("content-disposition"),
    /^attachment; filename="trendrail-analysis-\d{8}T\d{6}Z-1rows\.csv"$/,
  );
  assert.equal(response.headers.get("x-trendrail-export-format"), "analysis-v1");
  assert.equal(response.headers.get("x-trendrail-export-rows"), "1");
  assert.equal(response.headers.get("x-trendrail-export-total"), "1");
  assert.equal(response.headers.get("x-trendrail-export-truncated"), "0");
  assert.equal(calls[0].state, "active");
  assert.equal(calls[0].q, "SEO");
  assert.equal(calls[0].source, "youtube");
  assert.equal(calls[0].sort, "score");
  assert.equal(calls[0].dir, "asc");
  assert.equal(calls[0].pageSize, 1000);
  const bytes = Buffer.from(await response.arrayBuffer());
  assert.deepEqual([...bytes.subarray(0, 3)], [0xef, 0xbb, 0xbf]);
  assert.match(bytes.toString("utf8"), /"item-1","SEO"/);
});

test("route handles an empty filtered result", async () => {
  const queryItems = async (input) => ({ items: [], total: 0, page: input.page, pages: 1 });
  const { GET } = load("apps/web/app/api/export/analysis/route.ts", {
    "@/lib/data/items-query": { queryItems },
    "@/lib/data/analysis-export": lib,
  });
  const response = await GET(new Request("https://example.test/api/export/analysis?q=nomatch"));
  assert.equal(response.headers.get("x-trendrail-export-rows"), "0");
  assert.equal(response.headers.get("x-trendrail-export-total"), "0");
  assert.match(response.headers.get("content-disposition"), /-0rows\.csv"$/);
  const text = Buffer.from(await response.arrayBuffer()).toString("utf8");
  assert.equal(text.replace(/^\uFEFF/, "").split("\r\n").length, 1);
});

test("route returns a guide without downloading rows", async () => {
  const calls = [];
  const queryItems = async (input) => {
    calls.push(input);
    return { items: [item()], total: 7, page: 1, pages: 7 };
  };
  const { GET } = load("apps/web/app/api/export/analysis/route.ts", {
    "@/lib/data/items-query": { queryItems },
    "@/lib/data/analysis-export": lib,
  });
  const response = await GET(
    new Request("https://example.test/api/export/analysis?format=guide&from=2026-11-01"),
  );
  assert.equal(response.headers.get("content-type"), "text/markdown; charset=utf-8");
  assert.match(
    response.headers.get("content-disposition"),
    /^attachment; filename="trendrail-analysis-guide-\d{8}T\d{6}Z\.md"$/,
  );
  assert.equal(calls.length, 1);
  assert.equal(calls[0].pageSize, 1);
  assert.equal(calls[0].from, "2026-11-01");
  const guide = await response.text();
  assert.match(guide, /Rows matching these filters at generation: 7/);
  assert.match(guide, /Published from: 2026-11-01/);
  assert.ok(guide.includes(lib.ANALYSIS_PROMPT));
});

test("guide flags a scope above the row cap", async () => {
  const queryItems = async () => ({ items: [item()], total: lib.ANALYSIS_MAX_ROWS + 1, page: 1, pages: 2 });
  const { GET } = load("apps/web/app/api/export/analysis/route.ts", {
    "@/lib/data/items-query": { queryItems },
    "@/lib/data/analysis-export": lib,
  });
  const response = await GET(new Request("https://example.test/api/export/analysis?format=guide"));
  assert.equal(response.headers.get("x-trendrail-export-truncated"), "1");
  assert.match(await response.text(), /capped at 10,000 rows/);
});
