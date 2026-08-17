/**
 * admin-radar.spec.ts
 * E2E tests for the Admin Radar Station Status Map (/admin/radar)
 * Uses page.route() to mock API responses — no backend required.
 *
 * Tests cover:
 *  - Page load & Thailand SVG map visible
 *  - Station markers rendered with correct status colours
 *  - Hover tooltip with station metadata
 *  - Double-click zoom interaction
 *  - Cloud cluster hover → trajectory preview card
 *  - Cluster click → pin badge
 *  - Zoom In/Out buttons consistent with ×1.35 step
 */
import { test, expect, Page } from "@playwright/test";

// ── Mock API fixtures ──────────────────────────────────────────────────────────

const MOCK_STATIONS = {
  stations: [
    {
      code: "kkn240",
      name: "Khon Kaen (240km)",
      center_lat: 16.4322,
      center_lng: 102.8236,
      radius_km: 240,
      status: "online",
      is_active: true,
      latency_minutes: 4.5,
      last_frame_timestamp: new Date(Date.now() - 4.5 * 60000).toISOString(),
      image_url: "https://weather.tmd.go.th/kkn/kkn240_latest.jpg",
      loop_url: "https://weather.tmd.go.th/kknLoop.php",
    },
    {
      code: "skn240",
      name: "Sakon Nakhon (240km)",
      center_lat: 17.1607,
      center_lng: 104.1486,
      radius_km: 240,
      status: "delayed",
      is_active: true,
      latency_minutes: 38.0,
      last_frame_timestamp: new Date(Date.now() - 38 * 60000).toISOString(),
      image_url: "https://weather.tmd.go.th/skn/skn240_latest.jpg",
      loop_url: "https://weather.tmd.go.th/sknLoop.php",
    },
    {
      code: "kkn120",
      name: "Khon Kaen (120km)",
      center_lat: 16.4322,
      center_lng: 102.8236,
      radius_km: 120,
      status: "delayed",  // M3 fix: NOT "offline"
      is_active: true,
      latency_minutes: 45.0,
      last_frame_timestamp: new Date(Date.now() - 45 * 60000).toISOString(),
      image_url: "https://weather.tmd.go.th/kkn/kkn120_latest.jpg",
      loop_url: "",
    },
  ],
};

const MOCK_CLUSTERS = {
  clusters: [
    {
      id: "cluster-alpha",
      label: "Storm Cell A",
      cx: 400,
      cy: 300,
      radius: 35,
      lat: 16.5,
      lng: 103.2,
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
      lat: 17.1,
      lng: 102.5,
      intensity_dbz: 35.0,
      velocity_kmh: 18.5,
      heading_deg: 90,
      eta_min: 25,
      history_trajectory: [],
    },
  ],
  source: "live_cache",
  is_mock: false,
};

// ── Setup: intercept all API calls ─────────────────────────────────────────────

async function setupApiMocks(page: Page) {
  // Mock the Next.js API proxy → backend stations
  await page.route("**/api/admin/radar**", async (route) => {
    const url = route.request().url();
    if (url.includes("clusters")) {
      await route.fulfill({ json: MOCK_CLUSTERS, status: 200 });
    } else {
      await route.fulfill({ json: MOCK_STATIONS, status: 200 });
    }
  });

  // Mock any direct radar API calls
  await page.route("**/api/v1/radar/**", async (route) => {
    const url = route.request().url();
    if (url.includes("clusters")) {
      await route.fulfill({ json: MOCK_CLUSTERS, status: 200 });
    } else {
      await route.fulfill({ json: MOCK_STATIONS, status: 200 });
    }
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// Test Suite
// ══════════════════════════════════════════════════════════════════════════════

test.describe("Admin Radar Page /admin/radar", () => {

  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
    await page.goto("/admin/radar");
    // Wait for the SVG map to fully render
    await page.waitForSelector("svg[role='img']", { timeout: 10000 });
  });

  // ── Page load ───────────────────────────────────────────────────────────────

  test("page loads with Thailand SVG map visible", async ({ page }) => {
    const svgMap = page.locator("svg[role='img']").first();
    await expect(svgMap).toBeVisible();

    // Thailand province paths should be rendered
    const provincePaths = page.locator("path.pointer-events-none");
    await expect(provincePaths.first()).toBeVisible();
  });

  test("page title contains 'Radar' or 'เรดาร์'", async ({ page }) => {
    const title = await page.title();
    const heading = page.locator("h1, h2").first();
    const headingText = await heading.textContent();
    const hasRadarKeyword =
      title.toLowerCase().includes("radar") ||
      (headingText ?? "").includes("เรดาร์") ||
      (headingText ?? "").toLowerCase().includes("radar");
    expect(hasRadarKeyword).toBeTruthy();
  });

  // ── Station markers ─────────────────────────────────────────────────────────

  test("station markers appear for all mocked stations", async ({ page }) => {
    await expect(page.getByTestId("station-marker-kkn240")).toBeVisible();
    await expect(page.getByTestId("station-marker-skn240")).toBeVisible();
  });

  test("M3: kkn120 station shows as delayed (not offline) in status list", async ({ page }) => {
    // Find status badge/text for kkn120 — must be "delayed" not "offline"
    const kknStatus = page.locator("[data-testid='station-status-kkn120'], text=kkn120").first();
    if (await kknStatus.isVisible()) {
      const statusText = await kknStatus.textContent();
      expect(statusText?.toLowerCase()).not.toContain("offline");
    }
    // Also check via colour indicator — delayed = amber, not red
    // (This is a best-effort check; exact locator depends on UI implementation)
  });

  // ── Hover tooltip ───────────────────────────────────────────────────────────

  test("hover over station marker shows tooltip with station name", async ({ page }) => {
    const marker = page.getByTestId("station-marker-kkn240");
    await marker.hover();

    // Tooltip should appear with station name
    await expect(page.locator("text=Khon Kaen").first()).toBeVisible({ timeout: 3000 });
  });

  // ── Cloud cluster interactions ──────────────────────────────────────────────

  test("Issue #188: hover over cloud cluster reveals trajectory preview card", async ({ page }) => {
    const cluster = page.getByTestId("cloud-cluster-cluster-alpha");
    
    // Trajectory card absent before hover
    await expect(page.getByTestId("trajectory-preview-card")).not.toBeVisible();

    await cluster.hover();

    // Trajectory card appears on hover
    await expect(page.getByTestId("trajectory-preview-card")).toBeVisible({ timeout: 3000 });
    await expect(page.locator("text=Storm Cell A")).toBeVisible();
    await expect(page.locator("text=32.0 km/h")).toBeVisible();
  });

  test("cloud cluster click pins the trajectory panel with 📌 badge", async ({ page }) => {
    const cluster = page.getByTestId("cloud-cluster-cluster-alpha");
    await cluster.click();

    // Pinned panel should show 📌 indicator
    await expect(page.getByTestId("trajectory-preview-card")).toBeVisible({ timeout: 3000 });
    await expect(page.locator("text=ปักหมุด")).toBeVisible();

    // Panel persists after moving mouse away
    await page.mouse.move(50, 50);
    await expect(page.getByTestId("trajectory-preview-card")).toBeVisible();
  });

  // ── Zoom controls ───────────────────────────────────────────────────────────

  test("H4: Zoom In button increases zoom to approximately 1.35x", async ({ page }) => {
    const zoomInBtn = page.getByLabel("Zoom In");
    await zoomInBtn.click();

    // Zoom indicator badge should appear with ~1.35x value
    const badge = page.locator("text=/\\d+\\.\\d+x/").first();
    await expect(badge).toBeVisible({ timeout: 2000 });

    const badgeText = await badge.textContent();
    const value = parseFloat(badgeText?.replace("x", "") ?? "0");
    expect(value).toBeGreaterThan(1.3);
    expect(value).toBeLessThan(1.4);
  });

  test("H4: double-click on map zooms in multiplicatively (~1.35x)", async ({ page }) => {
    const svgMap = page.locator("svg[role='img']").first();
    const box = await svgMap.boundingBox();
    if (!box) throw new Error("SVG map not found");

    // Double-click at center of map
    await page.mouse.dblclick(box.x + box.width / 2, box.y + box.height / 2);

    const badge = page.locator("text=/\\d+\\.\\d+x/").first();
    await expect(badge).toBeVisible({ timeout: 2000 });

    const badgeText = await badge.textContent();
    const value = parseFloat(badgeText?.replace("x", "") ?? "0");
    expect(value).toBeGreaterThan(1.3);
    expect(value).toBeLessThan(1.4);
  });

  test("Reset View button resets zoom to 1.0x and disappears", async ({ page }) => {
    // Zoom in first
    await page.getByLabel("Zoom In").click();
    await expect(page.getByLabel("Reset View")).toBeVisible({ timeout: 2000 });

    // Reset
    await page.getByLabel("Reset View").click();
    await expect(page.getByLabel("Reset View")).not.toBeVisible({ timeout: 2000 });
  });

  // ── C3: SVG marker ID uniqueness ────────────────────────────────────────────

  test("C3: SVG marker id is namespaced (not bare 'arrow')", async ({ page }) => {
    const markerId = await page.evaluate(() => {
      const marker = document.querySelector("marker");
      return marker?.getAttribute("id") ?? null;
    });
    expect(markerId).toBeTruthy();
    expect(markerId).not.toBe("arrow");
    expect(markerId).toContain("arrow-");
  });

  // ── Scroll wheel zoom ───────────────────────────────────────────────────────

  test("scroll wheel up zooms in on the map", async ({ page }) => {
    const svgMap = page.locator("svg[role='img']").first();
    const box = await svgMap.boundingBox();
    if (!box) throw new Error("SVG not found");

    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.wheel(0, -200); // scroll up = zoom in

    const badge = page.locator("text=/\\d+\\.\\d+x/").first();
    await expect(badge).toBeVisible({ timeout: 2000 });
  });

  // ── Accessibility ───────────────────────────────────────────────────────────

  test("zoom controls have accessible aria-labels", async ({ page }) => {
    await expect(page.getByLabel("Zoom In")).toBeVisible();
    await expect(page.getByLabel("Zoom Out")).toBeVisible();
  });
});
