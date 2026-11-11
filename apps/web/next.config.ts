import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@social-tracker/shared"],
  agentRules: false,
};

export default nextConfig;
