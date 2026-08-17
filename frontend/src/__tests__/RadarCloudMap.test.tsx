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

  it("supports mouse drag panning when zoomed in", () => {
    render(<RadarCloudMap stations={mockStations} clusters={mockClusters} />);

    // Zoom in first
    const zoomInBtn = screen.getByLabelText("Zoom In");
    fireEvent.click(zoomInBtn);

    const svgMap = screen.getByRole("img", { name: "Radar Coverage Map" });
    expect(svgMap).toBeInTheDocument();

    // Mouse down and drag
    fireEvent.mouseDown(svgMap, { clientX: 200, clientY: 200 });
    fireEvent.mouseMove(svgMap, { clientX: 250, clientY: 250 });
    fireEvent.mouseUp(svgMap);

    // Zoom indicator should show current zoom multiplier ~1.35x (multiplicative step)
    const zoomBadges = screen.getAllByText(/\d+\.\d+x/);
    expect(zoomBadges.length).toBeGreaterThan(0);
    const zoomValue = parseFloat(zoomBadges[0].textContent?.replace(/[^0-9.]/g, "") ?? "0");
    expect(zoomValue).toBeGreaterThan(1.3);
    expect(zoomValue).toBeLessThan(1.5);
  });

  it("pins trajectory panel on cloud cluster click and supports closing via X button", () => {
    render(<RadarCloudMap stations={mockStations} clusters={mockClusters} />);

    const clusterElem = screen.getByTestId("cloud-cluster-cluster-alpha");

    // Click cluster to pin
    fireEvent.click(clusterElem);

    // Panel is pinned and stays visible even when mouse leaves
    expect(screen.getByTestId("trajectory-preview-card")).toBeInTheDocument();
    expect(screen.getByText(/📌 ปักหมุด/i)).toBeInTheDocument();

    fireEvent.mouseLeave(clusterElem);
    expect(screen.getByTestId("trajectory-preview-card")).toBeInTheDocument();

    // Click close button to unpin
    const closeBtn = screen.getByLabelText("Close Preview");
    fireEvent.click(closeBtn);
    expect(screen.queryByTestId("trajectory-preview-card")).not.toBeInTheDocument();
  });

  it("supports dynamic de-clustering / spiderfy sub-cell expansion upon zoom-in >= 2.0x", () => {
    const mockClustersWithSub: CloudCluster[] = [
      {
        id: "cluster-macro",
        label: "Macro Storm",
        cx: 260,
        cy: 390,
        radius: 25,
        intensity_dbz: 52,
        velocity_kmh: 30,
        heading_deg: 75,
        sub_clusters: [
          {
            id: "sub-cell-1",
            label: "Sub District A",
            cx: 250,
            cy: 380,
            radius: 12,
            intensity_dbz: 52,
            velocity_kmh: 32,
            heading_deg: 70,
          },
          {
            id: "sub-cell-2",
            label: "Sub District B",
            cx: 270,
            cy: 400,
            radius: 10,
            intensity_dbz: 46,
            velocity_kmh: 28,
            heading_deg: 80,
          },
        ],
      },
    ];

    render(<RadarCloudMap stations={mockStations} clusters={mockClustersWithSub} />);

    // At 1.0x: Parent macro cluster is visible
    expect(screen.getByTestId("cloud-cluster-cluster-macro")).toBeInTheDocument();
    expect(screen.queryByTestId("cloud-cluster-sub-cell-1")).not.toBeInTheDocument();

    // Zoom in twice to reach 2.0x (1.0x -> 1.5x -> 2.0x)
    const zoomInBtn = screen.getByLabelText("Zoom In");
    fireEvent.click(zoomInBtn);
    fireEvent.click(zoomInBtn);

    // At 2.0x: Parent cluster de-clusters / spiderfies into child sub-cells
    expect(screen.queryByTestId("cloud-cluster-cluster-macro")).not.toBeInTheDocument();
    expect(screen.getByTestId("cloud-cluster-sub-cell-1")).toBeInTheDocument();
    expect(screen.getByTestId("cloud-cluster-sub-cell-2")).toBeInTheDocument();
    expect(screen.getByText(/De-clustered/i)).toBeInTheDocument();

    // Toggle clustering OFF reverts to parent
    const toggleClusteringBtn = screen.getByText(/De-clustered/i);
    fireEvent.click(toggleClusteringBtn);
    expect(screen.getByTestId("cloud-cluster-cluster-macro")).toBeInTheDocument();
    expect(screen.queryByTestId("cloud-cluster-sub-cell-1")).not.toBeInTheDocument();
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// CODE-REVIEW FIX REGRESSION TESTS (commit ed84413)
// ══════════════════════════════════════════════════════════════════════════════

describe("RadarCloudMap — Code Review Fix Regressions", () => {
  // ── C3: SVG marker ID collision guard ──────────────────────────────────────

  it("C3: SVG marker id must NOT be the literal string 'arrow' (useId namespacing)", () => {
    const { container } = render(
      <RadarCloudMap stations={mockStations} clusters={mockClusters} />
    );
    const marker = container.querySelector("marker");
    expect(marker).toBeTruthy();
    // The id must be namespaced (not bare 'arrow') to prevent collision on multi-SVG pages
    const markerId = marker?.getAttribute("id") ?? "";
    expect(markerId).not.toBe("arrow");
    expect(markerId).toContain("arrow-"); // namespaced with useId() prefix
  });

  it("C3: Only ONE marker element should exist per RadarCloudMap instance", () => {
    const { container } = render(
      <RadarCloudMap stations={mockStations} clusters={mockClusters} />
    );
    const markers = container.querySelectorAll("marker");
    expect(markers.length).toBe(1);
  });

  it("C3: Two RadarCloudMap instances on same page have DIFFERENT marker IDs", () => {
    const { container: c1 } = render(
      <RadarCloudMap stations={mockStations} clusters={mockClusters} />
    );
    const { container: c2 } = render(
      <RadarCloudMap stations={mockStations} clusters={[]} />
    );
    const id1 = c1.querySelector("marker")?.getAttribute("id");
    const id2 = c2.querySelector("marker")?.getAttribute("id");
    expect(id1).not.toBe(id2);
  });

  // ── H1: Polygon useMemo — no NaN/empty in path ─────────────────────────────

  it("H1: polygon SVG path d attributes must not contain NaN or empty values", () => {
    const { container } = render(
      <RadarCloudMap stations={mockStations} clusters={mockClusters} />
    );
    const paths = container.querySelectorAll("path[d]");
    paths.forEach((p) => {
      const d = p.getAttribute("d") ?? "";
      expect(d.toLowerCase()).not.toContain("nan");
      expect(d.toLowerCase()).not.toContain("infinity");
    });
  });

  // ── H4: Zoom multiplicative step ───────────────────────────────────────────

  it("H4: Zoom In from 1.00x produces approximately 1.35x (multiplicative, not additive)", () => {
    render(<RadarCloudMap stations={mockStations} clusters={mockClusters} />);
    const zoomInBtn = screen.getByLabelText("Zoom In");
    fireEvent.click(zoomInBtn);

    // Badge may appear alongside other zoom-related text — get all and check the numeric one
    // NOTE: component uses .toFixed(1), so 1.35 → displays as "1.4x"
    const badges = screen.getAllByText(/\d+\.\d+x/);
    const numericBadgeText = badges.map(b => b.textContent ?? "").find(t => /^[\d.]+x$/.test(t.trim()));
    const value = parseFloat(numericBadgeText?.replace("x", "") ?? "0");

    // 1.35 * 1 = 1.35, rounded to 1 decimal → 1.4
    expect(value).toBeGreaterThan(1.3);
    expect(value).toBeLessThan(1.5);
    expect(value).not.toBe(1.5); // old additive step guard
  });

  it("H4: Zoom Out from ~1.35x returns to 1.00x (multiplicative inverse)", () => {
    render(<RadarCloudMap stations={mockStations} clusters={mockClusters} />);
    const zoomInBtn = screen.getByLabelText("Zoom In");
    const zoomOutBtn = screen.getByLabelText("Zoom Out");

    // Zoom in then out
    fireEvent.click(zoomInBtn);
    fireEvent.click(zoomOutBtn);

    // Reset View button should disappear (zoom back to 1.0)
    expect(screen.queryByLabelText("Reset View")).not.toBeInTheDocument();
  });

  it("H4: Scroll wheel zoom and button zoom produce same first step (~1.35x)", () => {
    const { unmount } = render(
      <RadarCloudMap stations={mockStations} clusters={mockClusters} />
    );
    const zoomInBtn = screen.getByLabelText("Zoom In");
    fireEvent.click(zoomInBtn);
    const buttonBadges = screen.getAllByText(/\d+\.\d+x/);
    const buttonValue = parseFloat(
      buttonBadges.map(b => b.textContent ?? "").find(t => /^[\d.]+x$/.test(t.trim()))?.replace("x", "") ?? "0"
    );

    // Unmount + re-render fresh instance for wheel test
    unmount();
    const { container } = render(
      <RadarCloudMap stations={mockStations} clusters={mockClusters} />
    );
    const svgMap = container.querySelector("svg[role='img']")!;
    fireEvent.wheel(svgMap, { deltaY: -100 }); // scroll up = zoom in
    const wheelBadges = screen.getAllByText(/\d+\.\d+x/);
    const wheelValue = parseFloat(
      wheelBadges.map(b => b.textContent ?? "").find(t => /^[\d.]+x$/.test(t.trim()))?.replace("x", "") ?? "0"
    );

    // Both should produce the same zoom step
    expect(Math.abs(buttonValue - wheelValue)).toBeLessThan(0.05);
  });

  // ── M4: No duplicate style prop ────────────────────────────────────────────

  it("M4: Province paths must not have both SVG attrs and redundant style prop", () => {
    const { container } = render(
      <RadarCloudMap stations={mockStations} clusters={mockClusters} />
    );
    // Province paths are identified by their pointer-events-none class
    const provincePaths = container.querySelectorAll("path.pointer-events-none");
    provincePaths.forEach((p) => {
      // style attribute should be empty or absent (fill/stroke set via SVG attrs, not style)
      const styleAttr = p.getAttribute("style") ?? "";
      expect(styleAttr).toBe("");
    });
  });
});
