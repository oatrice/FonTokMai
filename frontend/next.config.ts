import type { NextConfig } from "next";
import fs from "fs";
import path from "path";

let appVersion = "unknown";
try {
  appVersion = fs.readFileSync(path.join(process.cwd(), '../VERSION'), 'utf8').trim();
} catch (e) {
  try {
    appVersion = fs.readFileSync(path.join(process.cwd(), 'VERSION'), 'utf8').trim();
  } catch (err) {}
}

const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_APP_VERSION: appVersion,
    NEXT_PUBLIC_COMMIT_SHA: process.env.VERCEL_GIT_COMMIT_SHA || process.env.CI_COMMIT_SHORT_SHA || "local",
    NEXT_PUBLIC_ENVIRONMENT: process.env.NEXT_PUBLIC_ENVIRONMENT || "development",
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "api.dicebear.com",
      },
    ],
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: "/health",
        destination: `${backendUrl}/health`,
      }
    ];
  },
};

export default nextConfig;
