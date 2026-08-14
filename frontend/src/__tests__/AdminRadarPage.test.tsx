import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import AdminRadarPage from "@/app/admin/radar/page";

const mockResponse = {
  stations: [
    {
      code: "kkn120",
      name: "Khon Kaen (120km)",
      center_lat: 16.4322,
      center_lng: 102.8236,
      radius_km: 120,
      status: "online",
      latency_minutes: 5.2,
      last_frame_timestamp: "2026-08-14T06:20:00Z",
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
      latency_minutes: 6.0,
      last_frame_timestamp: "2026-08-14T06:20:00Z",
      image_url: "https://weather.tmd.go.th/kkn/kkn240_latest.gif",
      loop_url: "https://weather.tmd.go.th/kknLoop.php",
    },
    {
      code: "skn240",
      name: "Sakon Nakhon (240km)",
      center_lat: 17.1607,
      center_lng: 104.1486,
      radius_km: 240,
      status: "delayed",
      latency_minutes: 42.0,
      last_frame_timestamp: "2026-08-14T05:40:00Z",
      image_url: "https://weather.tmd.go.th/skn/skn240_latest.jpg",
      loop_url: "https://weather.tmd.go.th/sknLoop.php",
    },
  ],
};

beforeEach(() => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    } as any)
  );
});

afterEach(() => {
  jest.restoreAllMocks();
});

describe("Admin Radar Station Status Page (/admin/radar) (Issue #270)", () => {
  it("renders admin radar dashboard header, metrics, and station list", async () => {
    render(<AdminRadarPage />);

    expect(screen.getByText(/Radar Station Monitoring/i)).toBeInTheDocument();
    
    // Wait for stations to load
    await waitFor(() => {
      expect(screen.getAllByText(/Khon Kaen \(120km\)/i).length).toBeGreaterThan(0);
    });

    expect(screen.getAllByText(/Sakon Nakhon \(240km\)/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Total Stations/i)).toBeInTheDocument();
    expect(screen.getByText(/Active Online/i)).toBeInTheDocument();
  });

  it("filters stations by status", async () => {
    render(<AdminRadarPage />);

    await waitFor(() => {
      expect(screen.getAllByText(/Khon Kaen \(120km\)/i).length).toBeGreaterThan(0);
    });

    // Click Delayed filter
    const delayedTab = screen.getByRole("button", { name: /^delayed$/i });
    fireEvent.click(delayedTab);

    // Sakon Nakhon should be visible
    expect(screen.getAllByText(/Sakon Nakhon \(240km\)/i).length).toBeGreaterThan(0);
    // Table rows should filter out online stations
    expect(screen.queryByRole("cell", { name: /Khon Kaen \(120km\)/i })).not.toBeInTheDocument();
  });
});
