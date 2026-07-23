import { NextResponse } from "next/server";

export async function GET() {
  const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
  console.log("🌐 [Next.js Route Handler] Fetching milestones from:", `${backendUrl}/api/milestones`);
  
  try {
    const res = await fetch(`${backendUrl}/api/milestones`, { cache: "no-store" });
    console.log("📡 [Next.js Route Handler] Milestones Response Status:", res.status, res.statusText);
    
    if (res.ok) {
      const data = await res.json();
      console.log("✅ [Next.js Route Handler] Live Milestones Received from Backend!");
      return NextResponse.json(data);
    } else {
      console.warn("⚠️ [Next.js Route Handler] Milestones returned non-200 status:", res.status);
    }
  } catch (e) {
    console.error("❌ [Next.js Route Handler] Milestones Fetch Error (Falling back to static data):", e);
  }

  return NextResponse.json({
    target_thb: 10000,
    current_thb: 5140,
    is_locked: false,
    lock_reason: null,
    milestones: [
      {
        id: 1,
        title: "Milestone 1: 90-Day Server Fund",
        target_thb: 10000,
        current_thb: 5140,
        completed: false,
      },
    ],
  });
}
