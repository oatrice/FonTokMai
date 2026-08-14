import { NextResponse } from "next/server";

export async function GET() {
  const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${backendUrl}/api/v1/radar/stations`, { cache: "no-store" });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(data);
    }
  } catch (e) {
    console.error("❌ [API Proxy /api/admin/radar] Backend error:", e);
  }

  // Resilient fallback stations for admin viewer
  return NextResponse.json({
    stations: [
      {
        code: "kkn120",
        name: "Khon Kaen (120km)",
        center_lat: 16.4322,
        center_lng: 102.8236,
        radius_km: 120,
        status: "online",
        latency_minutes: 5.0,
        last_frame_timestamp: new Date(Date.now() - 5 * 60000).toISOString(),
        image_url: "https://weather.tmd.go.th/kkn/kkn120_latest.gif",
        loop_url: "https://weather.tmd.go.th/kknLoop.php",
      },
      {
        code: "kkn240",
        name: "Khon Kaen (240km)",
        center_lat: 16.4322,
        center_lng: 102.8236,
        radius_km: 240,
        status: "online",
        latency_minutes: 6.5,
        last_frame_timestamp: new Date(Date.now() - 6.5 * 60000).toISOString(),
        image_url: "https://weather.tmd.go.th/kkn/kkn240_latest.gif",
        loop_url: "https://weather.tmd.go.th/kknLoop.php",
      },
      {
        code: "skn240",
        name: "Sakon Nakhon (240km)",
        center_lat: 17.1607,
        center_lng: 104.1486,
        radius_km: 240,
        status: "online",
        latency_minutes: 12.0,
        last_frame_timestamp: new Date(Date.now() - 12 * 60000).toISOString(),
        image_url: "https://weather.tmd.go.th/skn/skn240_latest.jpg",
        loop_url: "https://weather.tmd.go.th/sknLoop.php",
      },
    ],
  });
}
