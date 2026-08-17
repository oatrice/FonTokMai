/**
 * radarUtils.test.ts
 * Unit tests for @/lib/radarUtils — shared colour utilities (M5 fix).
 * These guard against regressions in getDbzColor and getStatusColor.
 */
import { getDbzColor, getStatusColor } from "@/lib/radarUtils";

// ── getDbzColor ────────────────────────────────────────────────────────────────

describe("getDbzColor", () => {
  it("returns cyan (#06b6d4) for dBZ below 20", () => {
    expect(getDbzColor(0)).toBe("#06b6d4");
    expect(getDbzColor(19)).toBe("#06b6d4");
    expect(getDbzColor(-5)).toBe("#06b6d4");
  });

  it("returns green (#22c55e) for dBZ 20-29 (Light rain boundary)", () => {
    expect(getDbzColor(20)).toBe("#22c55e");
    expect(getDbzColor(25)).toBe("#22c55e");
    expect(getDbzColor(29)).toBe("#22c55e");
  });

  it("returns yellow (#eab308) for dBZ 30-39 (Moderate rain boundary)", () => {
    expect(getDbzColor(30)).toBe("#eab308");
    expect(getDbzColor(35)).toBe("#eab308");
    expect(getDbzColor(39)).toBe("#eab308");
  });

  it("returns orange (#f97316) for dBZ 40-49 (Heavy rain boundary)", () => {
    expect(getDbzColor(40)).toBe("#f97316");
    expect(getDbzColor(45)).toBe("#f97316");
    expect(getDbzColor(49)).toBe("#f97316");
  });

  it("returns red (#ef4444) for dBZ >= 50 (Severe rain boundary)", () => {
    expect(getDbzColor(50)).toBe("#ef4444");
    expect(getDbzColor(65)).toBe("#ef4444");
    expect(getDbzColor(999)).toBe("#ef4444");
  });

  it("handles exact boundary values correctly (no off-by-one)", () => {
    // Boundary crossings — these are the most common regression sites
    expect(getDbzColor(19)).toBe("#06b6d4"); // just below light
    expect(getDbzColor(20)).toBe("#22c55e"); // exactly light
    expect(getDbzColor(29)).toBe("#22c55e"); // just below moderate
    expect(getDbzColor(30)).toBe("#eab308"); // exactly moderate
    expect(getDbzColor(39)).toBe("#eab308"); // just below heavy
    expect(getDbzColor(40)).toBe("#f97316"); // exactly heavy
    expect(getDbzColor(49)).toBe("#f97316"); // just below severe
    expect(getDbzColor(50)).toBe("#ef4444"); // exactly severe
  });
});

// ── getStatusColor ─────────────────────────────────────────────────────────────

describe("getStatusColor", () => {
  it("returns emerald colours for 'online' status", () => {
    const c = getStatusColor("online");
    expect(c.stroke).toBe("#10b981");
    expect(c.fill).toBe("#059669");
    expect(c.bg).toContain("emerald");
  });

  it("returns amber colours for 'delayed' status", () => {
    const c = getStatusColor("delayed");
    expect(c.stroke).toBe("#f59e0b");
    expect(c.fill).toBe("#d97706");
    expect(c.bg).toContain("amber");
  });

  it("returns red colours for 'offline' status", () => {
    const c = getStatusColor("offline");
    expect(c.stroke).toBe("#ef4444");
    expect(c.fill).toBe("#dc2626");
    expect(c.bg).toContain("red");
  });

  it("returns red colours for unknown/empty status (safe default)", () => {
    expect(getStatusColor("").stroke).toBe("#ef4444");
    expect(getStatusColor("unknown").stroke).toBe("#ef4444");
    expect(getStatusColor("maintenance").stroke).toBe("#ef4444");
  });

  it("returns all three required keys: stroke, fill, bg", () => {
    for (const status of ["online", "delayed", "offline", ""]) {
      const c = getStatusColor(status);
      expect(c).toHaveProperty("stroke");
      expect(c).toHaveProperty("fill");
      expect(c).toHaveProperty("bg");
    }
  });

  it("bg string is valid Tailwind utility classes (non-empty string)", () => {
    for (const status of ["online", "delayed", "offline"]) {
      const c = getStatusColor(status);
      expect(typeof c.bg).toBe("string");
      expect(c.bg.length).toBeGreaterThan(0);
    }
  });
});
