import { NextRequest, NextResponse } from "next/server";
import { headers } from "next/headers";

/**
 * Next.js API Route — Proxy for GCP billing costs endpoint (Issue #211).
 *
 * Forwards requests to the backend /api/v1/metrics/gcp-costs with the
 * CRON_SECRET header injected server-side (never exposed to browser clients).
 *
 * Falls back to mock data when backend is unreachable.
 */
export async function GET(_req: NextRequest) {
  const backendUrl =
    process.env.BACKEND_URL || "http://localhost:8000";
  const cronSecret = process.env.CRON_SECRET || "";

  try {
    const res = await fetch(`${backendUrl}/api/v1/metrics/gcp-costs`, {
      cache: "no-store",
      headers: {
        "x-cron-secret": cronSecret,
        "Content-Type": "application/json",
      },
    });

    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(data);
    }
  } catch {
    // Backend offline — fall through to mock data
  }

  // Mock fallback for development / offline environments
  const now = new Date();
  const periodStart = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
  const periodEnd = now.toISOString().slice(0, 10);

  return NextResponse.json({
    cloud_run_usd: 8.4,
    cloud_storage_usd: 1.2,
    egress_usd: 0.6,
    other_usd: 0.8,
    total_usd: 11.0,
    period_start: periodStart,
    period_end: periodEnd,
    currency: "USD",
    is_mock: true,
  });
}
