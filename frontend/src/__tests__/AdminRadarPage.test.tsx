import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import AdminRadarPage from "@/app/admin/radar/page";

jest.mock("@/components/RadarCoverageMap", () => ({
  RadarCoverageMap: ({ onSelectStation, stations }: any) => (
    <div data-testid="mock-coverage-map">
      <button onClick={() => onSelectStation?.("kkn120")}>Select KKN120</button>
      <div data-testid="mock-stations-count">{stations?.length || 0}</div>
    </div>
  ),
  DEFAULT_STATIONS: [],
}));

const mockDbStations = [
  {
    code: "kkn120",
    name: "Khon Kaen (120km) / ขอนแก่น",
    static_image_url: "https://weather.tmd.go.th/kkn/kkn120_latest.gif",
    center_lat: 16.4322,
    center_lng: 102.8236,
    radius_km: 120,
    static_crop: { x: 80, y: 40, width: 720, height: 720 },
    is_active: true,
  },
  {
    code: "skn240",
    name: "Sakon Nakhon (240km) / สกลนคร",
    static_image_url: "https://weather.tmd.go.th/skn/skn240_latest.jpg",
    center_lat: 17.1607,
    center_lng: 104.1486,
    radius_km: 240,
    static_crop: { x: 72, y: 28, width: 728, height: 728 },
    is_active: true,
  },
];

const mockStatusResponse = {
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
  global.fetch = jest.fn((url: string) => {
    if (url.includes("/api/v1/admin/radar/stations")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockDbStations),
      } as any);
    }
    if (url.includes("/api/admin/radar")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockStatusResponse),
      } as any);
    }
    if (url.includes("/api/v1/admin/radar/presets")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve([]),
      } as any);
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({}),
    } as any);
  });
});

afterEach(() => {
  jest.restoreAllMocks();
});

describe("Admin Radar Page (/admin/radar) Unified Interactive Experience", () => {
  it("renders nationwide coverage map, calibration controls, Telegram simulated UI, and station list", async () => {
    render(<AdminRadarPage />);

    expect(screen.getByText(/TMD Radar Administration & Live Operations/i)).toBeInTheDocument();
    expect(screen.getByText(/1\. แผนที่เรดาร์และขอบเขตความคุ้มครองประเทศไทย/i)).toBeInTheDocument();
    expect(screen.getByText(/2\. เครื่องมือปรับจูนขอบเขตเรดาร์สด/i)).toBeInTheDocument();
    expect(screen.getByText(/3\. Telegram Live Preview & Coordinate Inspector/i)).toBeInTheDocument();
    expect(screen.getByText(/4\. รายการสถานีเรดาร์ทั้งหมดในระบบ/i)).toBeInTheDocument();

    // Wait for stations to load
    await waitFor(() => {
      expect(screen.getAllByText(/Khon Kaen \(120km\) \/ ขอนแก่น/i).length).toBeGreaterThan(0);
    });

    expect(screen.getAllByText(/Sakon Nakhon \(240km\) \/ สกลนคร/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Total Stations/i)).toBeInTheDocument();
  });

  it("WCAG & Screen Reader: provides accessible headings, semantic regions, and interactive labels", async () => {
    render(<AdminRadarPage />);

    // Screen reader accessible landmarks & headings
    const headings = screen.getAllByRole("heading");
    expect(headings.length).toBeGreaterThan(0);

    // Interactive buttons have accessible text or aria-label
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThan(0);
    buttons.forEach((btn) => {
      const label = btn.getAttribute("aria-label") || btn.textContent;
      expect(label?.trim().length).toBeGreaterThan(0);
    });
  });
});
