import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@social-tracker/shared"],
  agentRules: false,
  allowedDevOrigins: ["127.0.0.1"],
};

export default nextConfig;
