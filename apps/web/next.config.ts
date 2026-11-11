import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  agentRules: false,
  allowedDevOrigins: ["127.0.0.1", "172.16.11.228"],
  async redirects() {
    return [
      { source: "/dashboard-live.html", destination: "/live", permanent: false },
      { source: "/dashboard.html", destination: "/live", permanent: false },
      { source: "/app/dashboard.html", destination: "/live", permanent: false },
    ];
  },
};

export default nextConfig;
