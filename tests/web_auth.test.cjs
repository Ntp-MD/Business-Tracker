// Exercise the real proxy and callback with an in-memory auth provider; no network.
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

class Response {
  constructor(body = "", options = {}) {
    this.body = body;
    this.status = options.status ?? 200;
    this.headers = new Headers();
    this.cookies = { set() {} };
  }
  static next() {
    return new Response();
  }
  static redirect(url) {
    const response = new Response("", { status: 307 });
    response.location = String(url);
    return response;
  }
}

const next = load("apps/web/lib/auth/next.ts");
const owner = load("apps/web/lib/auth/owner.ts");
const config = ["APP_VARIANT", "SUPABASE_USER_ID", "NEXT_PUBLIC_SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_ANON_KEY", "NEXT_PUBLIC_SITE_URL"];
const initial = Object.fromEntries(config.map((key) => [key, process.env[key]]));
test.after(() => {
  for (const key of config) {
    if (initial[key] === undefined) delete process.env[key];
    else process.env[key] = initial[key];
  }
});

function request(url, method = "GET") {
  return { nextUrl: new URL(url), url, method, headers: new Headers(), cookies: { getAll: () => [], set() {} } };
}

test("prod allows the configured owner only and preserves variant boundaries", async () => {
  process.env.APP_VARIANT = "prod";
  process.env.SUPABASE_USER_ID = "owner-id";
  process.env.NEXT_PUBLIC_SUPABASE_URL = "https://example.invalid";
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "test-key";
  let user = { id: "owner-id" };
  const { proxy } = load("apps/web/proxy.ts", {
    "next/server": { NextResponse: Response },
    "@supabase/ssr": { createServerClient: () => ({ auth: { getUser: async () => ({ data: { user }, error: null }) } }) },
    "@/lib/auth/next": next,
    "@/lib/auth/owner": owner,
  });
  assert.equal((await proxy(request("https://example.test/live"))).status, 200);
  user = { id: "other-id" };
  assert.equal((await proxy(request("https://example.test/live"))).status, 403);
  assert.equal((await proxy(request("https://example.test/api/export", "POST"))).status, 403);
  user = null;
  assert.equal((await proxy(request("https://example.test/live"))).status, 307);
  assert.equal((await proxy(request("https://example.test/live/items", "POST"))).status, 401);
  delete process.env.SUPABASE_USER_ID;
  assert.equal((await proxy(request("https://example.test/live"))).status, 503);
  process.env.APP_VARIANT = "live";
  assert.equal((await proxy(request("https://example.test/live"))).status, 200);
  assert.equal((await proxy(request("https://example.test/live/items", "POST"))).status, 403);
  process.env.APP_VARIANT = "mockup";
  assert.equal((await proxy(request("https://example.test/api/export"))).status, 307);
});

test("callback keeps owner sessions and signs out other accounts", async () => {
  process.env.SUPABASE_USER_ID = "owner-id";
  let user = { id: "owner-id" };
  let signedOut = 0;
  let signOutScope;
  const auth = {
    exchangeCodeForSession: async () => ({ data: { user }, error: null }),
    verifyOtp: async () => ({ data: { user }, error: null }),
    signOut: async (options) => { signedOut += 1; signOutScope = options.scope; },
  };
  const { GET } = load("apps/web/app/auth/callback/route.ts", {
    "next/server": { NextResponse: Response },
    "@/lib/auth/next": next,
    "@/lib/auth/owner": owner,
    "@/lib/supabase/ssr": { createSupabaseServerClient: async () => ({ auth }) },
  });
  const good = await GET(request("https://example.test/auth/callback?code=valid&next=%2Flive%2Fitems"));
  assert.equal(good.location, "https://example.test/live/items");
  assert.equal(signedOut, 0);
  user = { id: "other-id" };
  const denied = await GET(request("https://example.test/auth/callback?code=valid"));
  assert.equal(new URL(denied.location).pathname, "/login");
  assert.match(new URL(denied.location).searchParams.get("error"), /owner access/);
  assert.equal(signedOut, 1);
  assert.equal(signOutScope, "local");
  const otp = await GET(request("https://example.test/auth/callback?token_hash=valid&type=magiclink"));
  assert.equal(new URL(otp.location).pathname, "/login");
  assert.equal(signedOut, 2);
});

test("Google sign-in starts the PKCE flow with a safe callback", async () => {
  process.env.SUPABASE_USER_ID = "owner-id";
  process.env.NEXT_PUBLIC_SITE_URL = "https://example.test";
  let options;
  const auth = { signInWithOAuth: async (value) => {
    options = value;
    return { data: { url: "https://provider.example/authorize" }, error: null };
  } };
  const { signInWithGoogle } = load("apps/web/app/login/actions.ts", {
    "next/headers": { headers: async () => new Headers() },
    "next/navigation": { redirect: (url) => { throw new Error(`REDIRECT:${url}`); } },
    "@/lib/auth/next": next,
    "@/lib/auth/owner": owner,
    "@/lib/supabase/ssr": { createSupabaseServerClient: async () => ({ auth }) },
    "@/lib/variant": { appVariant: () => "prod" },
  });
  const form = new FormData();
  form.set("next", "/live/items?q=test");
  await assert.rejects(signInWithGoogle(form), /REDIRECT:https:\/\/provider\.example\/authorize/);
  assert.equal(options.provider, "google");
  const callback = new URL(options.options.redirectTo);
  assert.equal(callback.origin + callback.pathname, "https://example.test/auth/callback");
  assert.equal(callback.searchParams.get("next"), "/live/items?q=test");
  for (const unsafe of ["//evil.test", "/\\evil.test", "/\nevil.test"]) {
    assert.equal(next.safeNext(unsafe), "/live");
  }
});

test("password sign-in rejects non-owner accounts and clears the session", async () => {
  process.env.SUPABASE_USER_ID = "owner-id";
  let user = { id: "other-id" };
  let signedOut = 0;
  let signOutScope;
  const auth = {
    signInWithPassword: async () => ({ data: { user }, error: null }),
    signOut: async (options) => { signedOut += 1; signOutScope = options.scope; },
  };
  const { signInWithPassword } = load("apps/web/app/login/actions.ts", {
    "next/headers": { headers: async () => new Headers() },
    "next/navigation": { redirect: (url) => { throw new Error(`REDIRECT:${url}`); } },
    "@/lib/auth/next": next,
    "@/lib/auth/owner": owner,
    "@/lib/supabase/ssr": { createSupabaseServerClient: async () => ({ auth }) },
    "@/lib/variant": { appVariant: () => "prod" },
  });
  const form = new FormData();
  form.set("email", "owner@example.test");
  form.set("password", "test-password");
  await assert.rejects(signInWithPassword(form), /REDIRECT:\/login\?error=/);
  assert.equal(signedOut, 1);
  assert.equal(signOutScope, "local");
  user = { id: "owner-id" };
  await assert.rejects(signInWithPassword(form), /REDIRECT:\/live/);
  assert.equal(signedOut, 1);
});
