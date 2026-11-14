// Exercise the owner-only collector counter aggregation; fixtures only.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const Module = require("node:module");
const path = require("node:path");
const test = require("node:test");
const ts = require("typescript");

function load(relativePath) {
  const filename = path.resolve(__dirname, "..", relativePath);
  const source = fs.readFileSync(filename, "utf8");
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const loaded = new Module(filename, module);
  loaded.filename = filename;
  loaded.paths = module.paths;
  loaded._compile(compiled, filename);
  return loaded.exports;
}

const { aggregateCollectorStats } = load("apps/web/lib/data/collector-stats.ts");

test("sums the latest counters across keyword scopes", () => {
  const stats = aggregateCollectorStats([
    {
      connector_id: "gdelt_doc",
      counters: { accepted: 2, rejected_total: 1, rejected: { spam: 1 } },
    },
    {
      connector_id: "gdelt_doc",
      counters: { accepted: 3, rejected_total: 2, rejected: { spam: 1, bad_url: 1 } },
    },
  ]);

  assert.deepEqual(stats.gdelt, {
    accepted: 5,
    rejected: 3,
    byReason: { spam: 2, bad_url: 1 },
  });
});

test("ignores unknown connectors and malformed counters", () => {
  const stats = aggregateCollectorStats([
    { connector_id: "other_source", counters: { accepted: 9 } },
    { connector_id: "gdelt_doc", counters: null },
    { connector_id: "gdelt_doc", counters: { accepted: "many", rejected_total: -1 } },
  ]);

  assert.deepEqual(stats, {});
});

test("clamps invalid reason counts and keeps valid ones", () => {
  const stats = aggregateCollectorStats([
    {
      connector_id: "gdelt_doc",
      counters: { accepted: 1, rejected_total: 2, rejected: { spam: -1, bad_url: 2 } },
    },
  ]);

  assert.deepEqual(stats.gdelt, { accepted: 1, rejected: 2, byReason: { bad_url: 2 } });
});
