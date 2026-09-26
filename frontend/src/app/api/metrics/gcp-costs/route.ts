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
export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const period = searchParams.get("period") || "current_month";
  const forceRefresh = searchParams.get("force_refresh") || "false";

  const backendUrl =
    process.env.BACKEND_URL || "http://localhost:8000";
  const cronSecret = process.env.CRON_SECRET || "";

  try {
    const res = await fetch(`${backendUrl}/api/v1/metrics/gcp-costs?period=${encodeURIComponent(period)}&force_refresh=${encodeURIComponent(forceRefresh)}`, {
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
  } catch (err) {
    console.error("[gcp-costs proxy] Backend unreachable, falling back to mock data:", err);
    // Backend offline — fall through to mock data
  }

  // Mock fallback for development / offline environments
  const now = new Date();
  const periodStart = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
  const periodEnd = now.toISOString().slice(0, 10);

  return NextResponse.json({
    cloud_run_thb: 294.0,
    cloud_storage_thb: 42.0,
    egress_thb: 21.0,
    other_thb: 28.0,
    total_thb: 385.0,
    period_start: periodStart,
    period_end: periodEnd,
    currency: "THB",
    is_mock: true,
  });
}
