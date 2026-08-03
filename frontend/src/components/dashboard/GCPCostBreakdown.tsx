"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Cloud,
  HardDrive,
  Wifi,
  MoreHorizontal,
  RefreshCw,
  AlertCircle,
  Info,
  TrendingUp,
} from "lucide-react";
import { GlassCard } from "../ui/GlassCard";
import { GlassBadge } from "../ui/GlassBadge";

// ─── Types ────────────────────────────────────────────────────────────────────

interface GCPCostData {
  cloud_run_thb?: number;
  cloud_storage_thb?: number;
  egress_thb?: number;
  other_thb?: number;
  total_thb?: number;
  // Fallbacks for backwards compatibility
  cloud_run_usd?: number;
  cloud_storage_usd?: number;
  egress_usd?: number;
  other_usd?: number;
  total_usd?: number;
  period_start: string;
  period_end: string;
  currency: string;
  is_mock: boolean;
  service_details?: Record<string, ServiceCostDetail[]>;
}

interface ServiceCostDetail {
  project_id?: string;
  service: string;
  sku?: string;
  cost_thb: number;
}

// ─── Config ───────────────────────────────────────────────────────────────────

const SERVICE_ITEMS = [
  {
    key: "cloud_run_thb" as keyof GCPCostData,
    fallbackKey: "cloud_run_usd" as keyof GCPCostData,
    label: "Cloud Run",
    icon: Cloud,
    colorClass: "text-cyan-400",
    bgClass: "bg-cyan-500/10",
    barClass: "from-cyan-500 to-blue-500",
  },
  {
    key: "cloud_storage_thb" as keyof GCPCostData,
    fallbackKey: "cloud_storage_usd" as keyof GCPCostData,
    label: "Cloud Storage",
    icon: HardDrive,
    colorClass: "text-emerald-400",
    bgClass: "bg-emerald-500/10",
    barClass: "from-emerald-500 to-teal-500",
  },
  {
    key: "egress_thb" as keyof GCPCostData,
    fallbackKey: "egress_usd" as keyof GCPCostData,
    label: "Network Egress",
    icon: Wifi,
    colorClass: "text-amber-400",
    bgClass: "bg-amber-500/10",
    barClass: "from-amber-500 to-orange-500",
  },
  {
    key: "other_thb" as keyof GCPCostData,
    fallbackKey: "other_usd" as keyof GCPCostData,
    label: "Other Services",
    icon: MoreHorizontal,
    colorClass: "text-slate-400",
    bgClass: "bg-slate-500/10",
    barClass: "from-slate-500 to-slate-600",
  },
] as const;

const serviceGradients: Record<string, string> = {
  cloud_run_thb: "linear-gradient(to right, #06b6d4, #3b82f6)",
  cloud_storage_thb: "linear-gradient(to right, #10b981, #14b8a6)",
  egress_thb: "linear-gradient(to right, #f59e0b, #f97316)",
  other_thb: "linear-gradient(to right, #64748b, #475569)",
};

// ─── Sub-components ───────────────────────────────────────────────────────────

function SkeletonRow() {
  return (
    <div className="flex items-center gap-3">
      <div className="h-8 w-8 rounded-lg bg-slate-800/60 animate-pulse flex-shrink-0" />
      <div className="flex-1 space-y-1.5">
        <div className="h-3 w-24 rounded bg-slate-800/60 animate-pulse" />
        <div className="h-1.5 w-full rounded-full bg-slate-800/60 animate-pulse" />
      </div>
      <div className="h-3 w-12 rounded bg-slate-800/60 animate-pulse" />
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

/**
 * GCPCostBreakdown — Glassmorphic card that displays monthly GCP infrastructure costs
 * broken down by service (Cloud Run, Storage, Egress, Other).
 *
 * Automatically shows "Mock Data" badge when backend returns mock data
 * (e.g., GCP credentials not configured).
 */
export function GCPCostBreakdown() {
  const [data, setData] = useState<GCPCostData | null>(null);
  const [period, setPeriod] = useState<string>("current_month");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCosts = useCallback(async (selectedPeriod: string = period) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/metrics/gcp-costs?period=${selectedPeriod}`, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json: GCPCostData = await res.json();
      setData(json);
    } catch {
      setError("ไม่สามารถโหลดข้อมูลค่าใช้จ่าย GCP ได้");
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => {
    fetchCosts(period);
  }, [period]);

  const totalThb = data
    ? data.total_thb !== undefined
      ? data.total_thb
      : (data.total_usd ?? 0) * (data.currency === "THB" ? 1 : 35)
    : 0;

  return (
    <GlassCard variant="default" glowColor="cyan" className="p-6 space-y-5">
      {/* ── Header ── */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-cyan-400" />
            GCP Infrastructure Costs
          </h3>
          {data && (
            <p className="text-xs text-slate-400 mt-0.5">
              {data.period_start} — {data.period_end}
            </p>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Period Selector Dropdown */}
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            disabled={loading}
            className="bg-slate-900/80 border border-white/15 text-xs text-slate-200 rounded-lg px-2.5 py-1 font-medium cursor-pointer focus:outline-none focus:border-cyan-400 transition-colors disabled:opacity-50"
            aria-label="Select billing period"
          >
            <option value="current_month" className="bg-slate-900 text-white">Current Month</option>
            <option value="last_month" className="bg-slate-900 text-white">Last Month</option>
            <option value="30d" className="bg-slate-900 text-white">Last 30 Days</option>
            <option value="7d" className="bg-slate-900 text-white">Last 7 Days</option>
          </select>

          {data?.is_mock && (
            <GlassBadge variant="amber">Mock Data</GlassBadge>
          )}
          <button
            id="gcp-cost-refresh-btn"
            onClick={() => fetchCosts(period)}
            disabled={loading}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors disabled:opacity-50"
            aria-label="Refresh GCP costs"
          >
            <RefreshCw
              className={`h-4 w-4 transition-transform ${loading ? "animate-spin" : ""}`}
            />
          </button>
        </div>
      </div>

      {/* ── Total ── */}
      {data && !loading && (
        <div className="text-center py-1">
          <span className="text-4xl font-black text-white tabular-nums">
            ฿{totalThb.toFixed(2)}
          </span>
          <span className="text-slate-400 ml-2 text-sm font-medium">
            THB / month
          </span>
        </div>
      )}

      {/* ── Service Rows ── */}
      <div className="space-y-3">
        {loading ? (
          // Skeleton loader
          <>
            <SkeletonRow />
            <SkeletonRow />
            <SkeletonRow />
            <SkeletonRow />
          </>
        ) : error ? (
          // Error state
          <div className="flex items-center gap-2 text-red-400 text-sm py-4 justify-center">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        ) : data ? (
          // Data rows
          SERVICE_ITEMS.map(({ key, fallbackKey, label, icon: Icon, colorClass, bgClass, barClass }) => {
            const rawCost = data[key] !== undefined ? (data[key] as number) : (data[fallbackKey] as number) || 0;
            const costThb = data.currency === "THB" || data[key] !== undefined ? rawCost : rawCost * 35;
            const pct = totalThb > 0 ? (costThb / totalThb) * 100 : 0;
            const details = data.service_details?.[key] ?? [];
            const tooltip = details.length > 0
              ? details
                  .map((item) => {
                    const sku = item.sku ? ` / ${item.sku}` : "";
                    const project = item.project_id ? ` (${item.project_id})` : "";
                    return `${item.service}${sku}${project}: ฿${item.cost_thb.toFixed(2)}`;
                  })
                  .join("\n")
              : `${label}: ฿${costThb.toFixed(2)}`;

            return (
              <div key={key} className="flex items-center gap-3">
                <div
                  className={`flex-shrink-0 p-1.5 rounded-lg ${bgClass} border border-white/5 ${colorClass}`}
                >
                  <Icon className="h-4 w-4" />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex justify-between text-sm mb-1.5">
                    <span className="text-slate-300 font-medium inline-flex items-center gap-1.5">
                      {label}
                      <span
                        aria-label={`${label} cost details`}
                        title={tooltip}
                        className="inline-flex"
                      >
                        <Info className="h-3.5 w-3.5 text-slate-500" aria-hidden="true" />
                      </span>
                    </span>
                    <span className="font-bold text-white tabular-nums">
                      ฿{costThb.toFixed(2)}
                    </span>
                  </div>
                  <div className="w-full rounded-full h-1.5 overflow-hidden border border-white/10" style={{ background: "rgba(255,255,255,0.05)" }}>
                    <div
                      className="h-full rounded-full transition-all duration-700 ease-out"
                      style={{
                        width: `${Math.max(pct, pct > 0 ? 3 : 0)}%`,
                        background: serviceGradients[key] || "linear-gradient(to right, #06b6d4, #3b82f6)",
                        boxShadow: pct > 0 ? `0 0 6px ${key === 'cloud_run_thb' ? 'rgba(6,182,212,0.4)' : key === 'cloud_storage_thb' ? 'rgba(16,185,129,0.4)' : key === 'egress_thb' ? 'rgba(245,158,11,0.4)' : 'rgba(100,116,139,0.4)'}` : "none",
                      }}
                      role="progressbar"
                      aria-valuenow={pct}
                      aria-valuemin={0}
                      aria-valuemax={100}
                    />
                  </div>
                </div>

                <span className="text-xs text-slate-500 w-10 text-right tabular-nums">
                  {pct.toFixed(0)}%
                </span>
              </div>
            );
          })
        ) : null}
      </div>
    </GlassCard>
  );
}
