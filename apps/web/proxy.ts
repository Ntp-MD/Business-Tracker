import { NextResponse, type NextRequest } from "next/server";

type Variant = "prod" | "mockup" | "live";

function variant(): Variant {
  const value = process.env.APP_VARIANT;
  return value === "mockup" || value === "live" ? value : "prod";
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const app = variant();

  if (app === "mockup" && (pathname === "/live" || pathname.startsWith("/live/") || pathname.startsWith("/api/"))) {
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
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/", "/live", "/live/:path*", "/api/:path*"],
};
