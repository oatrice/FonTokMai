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

const gitBranch = process.env.VERCEL_GIT_COMMIT_REF || process.env.CI_COMMIT_BRANCH || "dev";
const envName = gitBranch === "main" ? "production" : gitBranch === "staging" ? "staging" : "development";

let backendUrl = process.env.BACKEND_URL || "http://localhost:8000";

// Auto-correct BACKEND_URL if Vercel injects the 'dev' URL for the 'staging' branch
if (gitBranch === "staging" && backendUrl.includes("-dev-")) {
  backendUrl = backendUrl.replace("-dev-", "-staging-");
}

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_APP_VERSION: appVersion,
    NEXT_PUBLIC_COMMIT_SHA: process.env.VERCEL_GIT_COMMIT_SHA || process.env.CI_COMMIT_SHORT_SHA || "local",
    NEXT_PUBLIC_ENVIRONMENT: envName, // Force it to use the branch-derived name to prevent Vercel preview override
    BACKEND_URL: backendUrl, // Auto-corrected backend URL globally for all API routes
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
