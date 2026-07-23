import { NextResponse } from "next/server";

export async function GET() {
  const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
  // Try fetching backend API first
  try {
    const res = await fetch(`${backendUrl}/api/milestones`, { cache: "no-store" });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(data);
    }
  } catch (e) {
    // Fallback if backend is offline
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
