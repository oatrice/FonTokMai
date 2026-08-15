import React from "react";
import { render, screen, fireEvent, within } from "@testing-library/react";
import "@testing-library/jest-dom";
import { RadarCloudMap, CloudCluster, RadarStation } from "@/components/map/RadarCloudMap";

const mockStations: RadarStation[] = [
  {
    code: "kkn240",
    name: "Khon Kaen (240km)",
    center_lat: 16.4322,
    center_lng: 102.8236,
    radius_km: 240,
    status: "online",
    latency_minutes: 4.5,
    last_frame_timestamp: "2026-08-14T06:20:00Z",
  },
  {
    code: "skn240",
    name: "Sakon Nakhon (240km)",
    center_lat: 17.1607,
    center_lng: 104.1486,
    radius_km: 240,
    status: "delayed",
    latency_minutes: 38.0,
    last_frame_timestamp: "2026-08-14T05:45:00Z",
  },
];

const mockClusters: CloudCluster[] = [
  {
    id: "cluster-alpha",
    label: "Storm Cell A",
    cx: 400,
    cy: 300,
    radius: 35,
    intensity_dbz: 48.5,
    velocity_kmh: 32.0,
    heading_deg: 75,
    eta_min: 15,
    history_trajectory: [
      { time_offset_min: -15, cx: 340, cy: 330, dbz: 42.0 },
      { time_offset_min: -10, cx: 360, cy: 320, dbz: 45.0 },
      { time_offset_min: -5, cx: 380, cy: 310, dbz: 47.0 },
    ],
  },
  {
    id: "cluster-beta",
    label: "Rain Band B",
    cx: 250,
    cy: 200,
    radius: 25,
    intensity_dbz: 35.0,
    velocity_kmh: 18.5,
    heading_deg: 90,
    eta_min: 25,
    history_trajectory: [
      { time_offset_min: -10, cx: 220, cy: 200, dbz: 32.0 },
      { time_offset_min: -5, cx: 235, cy: 200, dbz: 34.0 },
    ],
  },
];

describe("RadarCloudMap Component (Issue #188 & #270)", () => {
  it("renders radar stations with coverage markers", () => {
    render(<RadarCloudMap stations={mockStations} clusters={mockClusters} />);
    expect(screen.getByText(/Khon Kaen \(240km\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Sakon Nakhon \(240km\)/i)).toBeInTheDocument();
  });

  it("registers hover on cloud cluster and displays historical trajectory vectors (Issue #188)", () => {
    render(<RadarCloudMap stations={mockStations} clusters={mockClusters} />);
    
    // Find the cloud cluster element
    const clusterElem = screen.getByTestId("cloud-cluster-cluster-alpha");
    expect(clusterElem).toBeInTheDocument();

    // Before hover, trajectory preview info is not active
    expect(screen.queryByTestId("trajectory-preview-card")).not.toBeInTheDocument();

    // Trigger mouse hover / mouse enter
    fireEvent.mouseEnter(clusterElem);

    // Trajectory details should now be visible
    const previewCard = screen.getByTestId("trajectory-preview-card");
    expect(previewCard).toBeInTheDocument();
    expect(within(previewCard).getByText(/Storm Cell A/i)).toBeInTheDocument();
    expect(within(previewCard).getByText(/32.0 km\/h/i)).toBeInTheDocument();
    expect(within(previewCard).getByText(/^Historical Movement:$/i)).toBeInTheDocument();

    // Verify historical trajectory points are rendered
    expect(screen.getByTestId("trajectory-path-cluster-alpha")).toBeInTheDocument();

    // Mouse leave removes preview card
    fireEvent.mouseLeave(clusterElem);
    expect(screen.queryByTestId("trajectory-preview-card")).not.toBeInTheDocument();
  });

  it("handles station selection callback", () => {
    const onSelect = jest.fn();
    render(<RadarCloudMap stations={mockStations} clusters={mockClusters} onSelectStation={onSelect} />);
    
    const stationMarker = screen.getByTestId("station-marker-kkn240");
    fireEvent.click(stationMarker);
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ code: "kkn240" }));
  });

  it("toggles UI debug display elements (station centers, cloud clusters, dBZ labels)", () => {
    render(<RadarCloudMap stations={mockStations} clusters={mockClusters} />);

    // Station marker initially visible
    expect(screen.getByTestId("station-marker-kkn240")).toBeInTheDocument();
    expect(screen.getByText("49")).toBeInTheDocument();

    // Toggle Station Centers OFF
    const toggleStationBtn = screen.getByText(/ศูนย์กลางเรดาร์/i);
    fireEvent.click(toggleStationBtn);
    expect(screen.queryByTestId("station-marker-kkn240")).not.toBeInTheDocument();

    // Toggle dBZ Labels OFF
    const toggleDbzBtn = screen.getByText(/ค่า dBZ/i);
    fireEvent.click(toggleDbzBtn);
    expect(screen.queryByText("49")).not.toBeInTheDocument();
  });

  it("supports Google Maps-style zoom controls and cloud focus buttons", () => {
    render(<RadarCloudMap stations={mockStations} clusters={mockClusters} />);

    const zoomInBtn = screen.getByLabelText("Zoom In");
    const zoomOutBtn = screen.getByLabelText("Zoom Out");

    expect(zoomInBtn).toBeInTheDocument();
    expect(zoomOutBtn).toBeInTheDocument();

    // Click Zoom In
    fireEvent.click(zoomInBtn);
    expect(screen.getByLabelText("Reset View")).toBeInTheDocument();

    // Focus on specific cloud
    const cloudFocusBtn = screen.getByText(/Storm/i);
    fireEvent.click(cloudFocusBtn);
    expect(screen.getByLabelText("Reset View")).toBeInTheDocument();

    // Reset View
    fireEvent.click(screen.getByLabelText("Reset View"));
    expect(screen.queryByLabelText("Reset View")).not.toBeInTheDocument();
  });
});
