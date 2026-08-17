/**
 * Shared radar utility functions used across RadarCloudMap and RadarCoverageMap.
 * Centralising these avoids copy-paste drift when thresholds change.
 */

export type DbzColor = string;

/** Returns a hex colour string based on radar reflectivity (dBZ) value. */
export function getDbzColor(dbz: number): DbzColor {
  if (dbz >= 50) return "#ef4444"; // Red — Severe
  if (dbz >= 40) return "#f97316"; // Orange — Heavy
  if (dbz >= 30) return "#eab308"; // Yellow — Moderate
  if (dbz >= 20) return "#22c55e"; // Green — Light
  return "#06b6d4";                 // Cyan — Very light / trace
}

export interface StatusStyle {
  stroke: string;
  fill: string;
  bg: string;
  text: string;
  border: string;
  pulse: string;
}

/** Returns display colour tokens for a radar station status. */
export function getStatusColor(status?: string): StatusStyle {
  switch (status) {
    case "online":
      return {
        stroke: "#10b981",
        fill: "#059669",
        bg: "bg-emerald-500/20",
        text: "text-emerald-400",
        border: "border-emerald-500/30",
        pulse: "rgba(16,185,129,0.18)",
      };
    case "delayed":
      return {
        stroke: "#f59e0b",
        fill: "#d97706",
        bg: "bg-amber-500/20",
        text: "text-amber-400",
        border: "border-amber-500/30",
        pulse: "rgba(245,158,11,0.18)",
      };
    default:
      return {
        stroke: "#ef4444",
        fill: "#dc2626",
        bg: "bg-red-500/20",
        text: "text-red-400",
        border: "border-red-500/30",
        pulse: "rgba(239,68,68,0.18)",
      };
  }
}
