"use client";

import React, { useEffect, useState } from "react";

interface HealthStatus {
  version: string;
  environment: string;
  commit_sha: string;
}

export function SiteFooter() {
  const [backendHealth, setBackendHealth] = useState<HealthStatus | null>(null);

  useEffect(() => {
    fetch('/health')
      .then(res => res.json())
      .then(data => {
        if (data.version) {
          setBackendHealth(data);
        }
      })
      .catch(err => console.error("Failed to fetch backend health:", err));
  }, []);

  const frontendVersion = process.env.NEXT_PUBLIC_APP_VERSION || "unknown";
  const frontendCommit = process.env.NEXT_PUBLIC_COMMIT_SHA?.substring(0, 7) || "local";
  const frontendEnv = process.env.NEXT_PUBLIC_ENVIRONMENT || "development";

  return (
    <footer className="w-full py-4 text-center text-xs text-slate-500 border-t border-white/5 bg-slate-950 mt-auto">
      <div className="flex flex-col md:flex-row justify-center items-center gap-2">
        <span>
          v{frontendVersion} ({frontendCommit}) [{frontendEnv}]
        </span>
        <span className="hidden md:inline">|</span>
        <span>
          Backend v{backendHealth?.version || "..."} 
          {backendHealth?.commit_sha ? ` (${backendHealth.commit_sha.substring(0, 7)})` : ""} 
          [{backendHealth?.environment || "..."}]
        </span>
      </div>
    </footer>
  );
}
