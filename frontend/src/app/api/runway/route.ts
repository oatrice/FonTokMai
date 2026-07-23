import { NextResponse } from "next/server";

export async function GET() {
  const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
  console.log("🌐 [Next.js Route Handler] Fetching from:", `${backendUrl}/api/runway`);
  
  try {
    const res = await fetch(`${backendUrl}/api/runway`, { cache: "no-store" });
    console.log("📡 [Next.js Route Handler] Response Status:", res.status, res.statusText);
    
    if (res.ok) {
      const data = await res.json();
      console.log("✅ [Next.js Route Handler] Live Data Received from Backend! seconds_remaining:", data.seconds_remaining);
      return NextResponse.json(data);
    } else {
      console.warn("⚠️ [Next.js Route Handler] Backend returned non-200 status:", res.status);
    }
  } catch (e) {
    console.error("❌ [Next.js Route Handler] Fetch Error (Falling back to static data):", e);
  }

  return NextResponse.json({
    days_remaining: 42,
    hours_remaining: 18,
    seconds_remaining: 3693600,
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
        color: "from-blue-500 to-cyan-500",
      },
      {
        name: "TMD Radar & Weather APIs",
        percentage: 30,
        allocated_thb: 1542,
        description: "Radar image processing & storage",
        color: "from-purple-500 to-indigo-500",
      },
      {
        name: "Emergency Reserve Jar",
        percentage: 20,
        allocated_thb: 1028,
        description: "Locked buffer for unexpected spikes",
        color: "from-emerald-500 to-teal-500",
      },
    ],
  });
}
