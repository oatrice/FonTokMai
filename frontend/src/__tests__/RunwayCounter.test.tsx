import React from "react";
import { render, screen, act } from "@testing-library/react";
import { RunwayCounter } from "../components/dashboard/RunwayCounter";
import useSWR from "swr";

jest.mock("swr");
const mockUseSWR = useSWR as jest.Mock;

describe("RunwayCounter", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("renders loading state when data is not yet available", () => {
    mockUseSWR.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: undefined,
    });

    render(<RunwayCounter />);
    expect(screen.getAllByText("Syncing...").length).toBeGreaterThanOrEqual(1);
  });

  it("renders countdown correctly using target_exhaustion_time", () => {
    const now = 1700000000000;
    jest.setSystemTime(now);

    // 10 days, 2 hours, 30 mins, 15 secs in future
    const secondsRemaining = 10 * 86400 + 2 * 3600 + 30 * 60 + 15;
    const serverTimeSec = Math.floor(now / 1000);
    const targetExhaustionTimeSec = serverTimeSec + secondsRemaining;

    mockUseSWR.mockReturnValue({
      data: {
        days_remaining: 10,
        hours_remaining: 2,
        seconds_remaining: secondsRemaining,
        target_exhaustion_time: targetExhaustionTimeSec,
        server_time: serverTimeSec,
        burn_rate_per_day: 120.0,
        total_balance_thb: 5140.0,
        circuit_breaker_active: false,
        emergency_overdrive: false,
      },
      isLoading: false,
      error: undefined,
    });

    render(<RunwayCounter />);

    expect(screen.getAllByText("10").length).toBeGreaterThanOrEqual(1); // 10 days
    expect(screen.getByText("02")).toBeInTheDocument(); // 02 hours
    expect(screen.getByText("30")).toBeInTheDocument(); // 30 mins
    expect(screen.getByText("15")).toBeInTheDocument(); // 15 secs

    // Verify target timestamp is stored in localStorage for page refresh persistence
    expect(localStorage.getItem("runwayTargetEndTime")).toBe(String(now + secondsRemaining * 1000));

    // Fast forward 5 seconds
    act(() => {
      jest.advanceTimersByTime(5000);
    });

    // 15 - 5 = 10 seconds (now both days=10 and secs=10 exist)
    expect(screen.getAllByText("10").length).toBe(2);
  });

  it("resumes countdown smoothly when refreshed with cached target in localStorage", () => {
    const now = 1700000000000;
    jest.setSystemTime(now);

    // 2 days, 3 hours, 4 mins, 50 secs
    const secondsRemaining = 2 * 86400 + 3 * 3600 + 4 * 60 + 50;
    const targetEndTimeMs = now + secondsRemaining * 1000;
    localStorage.setItem("runwayTargetEndTime", targetEndTimeMs.toString());

    mockUseSWR.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: undefined,
    });

    render(<RunwayCounter />);

    // Even before API completes, cached target in localStorage allows counter to show 50s and 2 days
    expect(screen.getByText("50")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("displays INFINITY when emergency overdrive is active", () => {
    mockUseSWR.mockReturnValue({
      data: {
        days_remaining: -1,
        hours_remaining: -1,
        seconds_remaining: -1,
        target_exhaustion_time: -1,
        burn_rate_per_day: 120.0,
        total_balance_thb: 5140.0,
        circuit_breaker_active: false,
        emergency_overdrive: true,
      },
      isLoading: false,
      error: undefined,
    });

    render(<RunwayCounter />);
    expect(screen.getByText(/INFINITY/i)).toBeInTheDocument();
    expect(screen.getByText(/Extended Lifespan Mode/i)).toBeInTheDocument();
  });
});
