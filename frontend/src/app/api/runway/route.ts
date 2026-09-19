import { NextResponse } from "next/server";

export async function GET() {
  const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${backendUrl}/api/runway`, { cache: "no-store" });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(data);
    }
    console.warn(`⚠️ [API Proxy /api/runway] Backend returned non-200 status: ${res.status} ${res.statusText}`);
  } catch (e) {
    console.error("❌ [API Proxy /api/runway] Failed to connect to Backend URL:", backendUrl, e);
  }

  const nowSeconds = Math.floor(Date.now() / 1000);
  const fallbackDays = 42;
  const fallbackHours = 18;
  const fallbackSecondsRemaining = fallbackDays * 86400 + fallbackHours * 3600;

  return NextResponse.json({
    days_remaining: fallbackDays,
    hours_remaining: fallbackHours,
    seconds_remaining: fallbackSecondsRemaining,
    target_exhaustion_time: nowSeconds + fallbackSecondsRemaining,
    server_time: nowSeconds,
    burn_rate_per_day: 120,
    total_balance_thb: 5140,
    circuit_breaker_active: false,
    emergency_overdrive: false,
    budget_jars: [
      {
        name: "Cloud Run Infrastructure",
        percentage: 50,
        allocated_thb: 2570,
        description: "Backend API instances & async workers",
        color: "from-blue-600 to-sky-600",
      },
      {
        name: "TMD Radar & Weather APIs",
        percentage: 30,
        allocated_thb: 1542,
        description: "Radar image processing & storage",
        color: "from-sky-600 to-teal-600",
      },
      {
        name: "Emergency Reserve Jar",
        percentage: 20,
        allocated_thb: 1028,
        description: "Locked buffer for unexpected spikes",
        color: "from-emerald-600 to-teal-500",
      },
    ],
  });
}
