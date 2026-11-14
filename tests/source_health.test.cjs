// Exercise the derived source health used by the Sources page; fixtures only.
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

const { sourceHealth } = load("apps/web/lib/data/source-health.ts");
const NOW = Date.parse("2026-11-14T12:00:00Z");

function status(over = {}) {
  return { ok: true, message: "", at: "2026-11-14T11:00:00Z", count: 0, ...over };
}

test("missing status is not run", () => {
  const health = sourceHealth(undefined, NOW);
  assert.equal(health.state, "not_run");
  assert.match(health.detail, /No run recorded/);
  assert.equal(health.stale, false);
});

test("successful run with records is OK", () => {
  const health = sourceHealth(status({ count: 3 }), NOW);
  assert.equal(health.state, "ok");
  assert.match(health.detail, /3 record/);
  assert.equal(health.stale, false);
});

test("successful run with no records is empty", () => {
  const health = sourceHealth(status({ count: 0 }), NOW);
  assert.equal(health.state, "empty");
  assert.match(health.detail, /0 records/);
});

test("throttle and access errors get their own states", () => {
  assert.equal(
    sourceHealth(status({ ok: false, message: "HTTP 429 Too Many Requests" }), NOW).state,
    "rate_limited",
  );
  assert.equal(
    sourceHealth(status({ ok: false, message: "HTTP 403 Forbidden" }), NOW).state,
    "blocked",
  );
  assert.equal(
    sourceHealth(status({ ok: false, message: "invalid JSON response" }), NOW).state,
    "parsing",
  );
  assert.equal(
    sourceHealth(status({ ok: false, message: "socket hang up" }), NOW).state,
    "error",
  );
});

test("old checks are marked stale", () => {
  assert.equal(sourceHealth(status({ at: "2026-11-10T11:00:00Z" }), NOW).stale, true);
  assert.equal(sourceHealth(status({ at: "not-a-date" }), NOW).stale, false);
});
