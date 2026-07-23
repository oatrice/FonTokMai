import { NextResponse } from "next/server";

export async function GET() {
  const data = {
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
  };

  return NextResponse.json(data);
}
