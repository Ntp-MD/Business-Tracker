// Exercise the worker job runner with an in-memory fetch and patch; no network.
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

const runner = load("apps/worker/src/job-runner.ts");

function job(over = {}) {
  return {
    id: 7,
    kind: "collect",
    payload: {
      connector_id: "gdelt_doc",
      scope: { keyword: "SEO" },
      mode: "manual",
      max_records: 50,
      dry_run: true,
    },
    ...over,
  };
}

function deps({ response, requests = [], patches = [], collectorWrites = true, maxAttempts = 3 } = {}) {
  return {
    fetch: async (url, init) => {
      requests.push({ url, body: init?.body ? JSON.parse(init.body) : null });
      return response;
    },
    patch: async (id, body) => {
      patches.push({ id, body });
    },
    api: "http://127.0.0.1:8000",
    collectorWrites,
    maxAttempts,
  };
}

function ok(body) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

test("collect jobs send the job id and the write switch", async () => {
  const requests = [];
  const patches = [];
  await runner.runJob(
    job(),
    1,
    deps({ response: ok({ counters: { written: 1 } }), requests, patches }),
  );

  assert.equal(requests[0].url, "http://127.0.0.1:8000/api/collect");
  assert.equal(requests[0].body.job_id, 7);
  assert.equal(requests[0].body.dry_run, false);
  assert.equal(requests[0].body.connector_id, "gdelt_doc");
  assert.equal(patches[0].body.status, "done");
  assert.equal(patches[0].body.progress, 4);
  assert.equal(patches[0].body.total, 4);
  assert.equal(patches[0].body.lease_owner, null);
});

test("dry runs keep dry_run true when writes are disabled", async () => {
  const requests = [];
  await runner.runJob(
    job(),
    1,
    deps({ response: ok({}), requests, collectorWrites: false }),
  );
  assert.equal(requests[0].body.dry_run, true);
});

test("a cancelled response is terminal and not retried", async () => {
  const patches = [];
  await runner.runJob(
    job(),
    1,
    deps({ response: ok({ cancelled: true, counters: { written: 3 } }), patches }),
  );

  assert.equal(patches.length, 1);
  assert.equal(patches[0].body.status, "cancelled");
  assert.match(patches[0].body.error, /cancelled; 3 written; rerun is safe/);
});

test("failures requeue until the attempt limit", async () => {
  const patches = [];
  const failed = () => new Response("boom", { status: 500 });

  await runner.runJob(job(), 1, deps({ response: failed(), patches }));
  await runner.runJob(job(), 3, deps({ response: failed(), patches }));

  assert.equal(patches[0].body.status, "queued");
  assert.equal(patches[0].body.started_at, null);
  assert.equal(patches[1].body.status, "error");
  assert.match(patches[1].body.error, /fetch 500: boom/);
});

test("non-collect jobs do not add a job id", async () => {
  const requests = [];
  await runner.runJob(
    { id: 7, kind: "fetch", payload: { q: "SEO", sources: ["youtube"] } },
    1,
    deps({ response: ok({ added: 1 }), requests }),
  );
  assert.equal(requests[0].url, "http://127.0.0.1:8000/api/fetch");
  assert.equal(Object.hasOwn(requests[0].body, "job_id"), false);
  assert.equal(Object.hasOwn(requests[0].body, "dry_run"), false);
});
