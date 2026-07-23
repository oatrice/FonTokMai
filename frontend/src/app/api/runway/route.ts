import { NextResponse } from "next/server";

export async function GET() {
  const data = {
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
  };

  return NextResponse.json(data);
}
