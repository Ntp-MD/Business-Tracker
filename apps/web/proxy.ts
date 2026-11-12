import { createServerClient } from "@supabase/ssr";
import { type NextRequest, NextResponse } from "next/server";

type Variant = "prod" | "mockup" | "live";

function variant(): Variant {
  const value = process.env.APP_VARIANT;
  return value === "mockup" || value === "live" ? value : "prod";
}

function needsAuth(pathname: string): boolean {
  if (pathname === "/api/health") return false;
  return pathname === "/live" || pathname.startsWith("/live/") || pathname.startsWith("/api/");
}

export async function proxy(request: NextRequest) {
  const requestId = request.headers.get("x-request-id") ?? crypto.randomUUID();
  const started = Date.now();
  try {
    const response = await handleRequest(request, requestId);
    response.headers.set("x-request-id", requestId);
    console.log(
      JSON.stringify({
        level: response.status >= 500 ? "error" : "info",
        event: "request",
        request_id: requestId,
        method: request.method,
        path: request.nextUrl.pathname,
        status: response.status,
        duration_ms: Date.now() - started,
      }),
    );
    return response;
  } catch (err) {
    const message = err instanceof Error ? err.message : "unknown error";
    console.error(
      JSON.stringify({
        level: "error",
        event: "proxy_failed",
        request_id: requestId,
        path: request.nextUrl.pathname,
        error: message,
      }),
    );
    throw err;
  }
}

async function handleRequest(request: NextRequest, requestId: string) {
  const { pathname } = request.nextUrl;
  const app = variant();

  if (
    app === "mockup" &&
    (pathname === "/live" || pathname.startsWith("/live/") || pathname.startsWith("/api/"))
  ) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  if (app === "live") {
    if (pathname === "/") return NextResponse.redirect(new URL("/live", request.url));
    if (
      pathname === "/live/settings" ||
      pathname.startsWith("/live/settings/") ||
      pathname === "/live/trash" ||
      pathname.startsWith("/live/trash/") ||
      /^\/live\/items\/[^/]+\/edit\/?$/.test(pathname)
    ) {
      return NextResponse.redirect(new URL("/live", request.url));
    }
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new NextResponse("Read-only live deployment", { status: 403 });
    }
    return NextResponse.next();
  }

  if (!needsAuth(pathname)) return NextResponse.next();

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) {
    console.error(
      JSON.stringify({
        level: "error",
        event: "auth_config_missing",
        request_id: requestId,
        error: "NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY missing",
      }),
    );
    return new NextResponse("Authentication is not configured", { status: 503 });
  }

  let response = NextResponse.next({ request });
  const supabase = createServerClient(url, key, {
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll: (cookiesToSet) => {
        for (const { name, value } of cookiesToSet) request.cookies.set(name, value);
        response = NextResponse.next({ request });
        for (const { name, value, options } of cookiesToSet)
          response.cookies.set(name, value, options);
      },
    },
  });

  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();

  const sessionMissing =
    error?.name === "AuthSessionMissingError" || error?.message === "Auth session missing!";
  if (error && !sessionMissing) {
    console.error(
      JSON.stringify({
        level: "error",
        event: "auth_check_failed",
        request_id: requestId,
        error: error.message,
      }),
    );
    return new NextResponse("Authentication is unavailable", { status: 503 });
  }

  if (!user) {
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new NextResponse("Unauthorized", { status: 401 });
    }
    const login = new URL("/login", request.url);
    login.searchParams.set("next", `${pathname}${request.nextUrl.search}`);
    return NextResponse.redirect(login);
  }

  return response;
}

export const config = {
  matcher: ["/", "/live", "/live/:path*", "/api/:path*"],
};
