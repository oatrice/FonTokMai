import { NextResponse } from "next/server";

export async function GET() {
  const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
  const cronSecret = process.env.CRON_SECRET || "";

  try {
    const res = await fetch(`${backendUrl}/api/locations`, {
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
    return NextResponse.json({ error: "Failed to fetch locations from backend" }, { status: res.status });
  } catch (err) {
    console.error("❌ [API Proxy /api/locations] Backend error:", err);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
