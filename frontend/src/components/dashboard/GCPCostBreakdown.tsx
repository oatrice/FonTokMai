"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Cloud,
  HardDrive,
  Wifi,
  MoreHorizontal,
  RefreshCw,
  AlertCircle,
  TrendingUp,
} from "lucide-react";
import { GlassCard } from "../ui/GlassCard";
import { GlassBadge } from "../ui/GlassBadge";

// ─── Types ────────────────────────────────────────────────────────────────────

interface GCPCostData {
  cloud_run_usd: number;
  cloud_storage_usd: number;
  egress_usd: number;
  other_usd: number;
  total_usd: number;
  period_start: string;
  period_end: string;
  currency: string;
  is_mock: boolean;
}

// ─── Config ───────────────────────────────────────────────────────────────────

const SERVICE_ITEMS = [
  {
    key: "cloud_run_usd" as keyof GCPCostData,
    label: "Cloud Run",
    icon: Cloud,
    colorClass: "text-cyan-400",
    bgClass: "bg-cyan-500/10",
    barClass: "from-cyan-500 to-blue-500",
  },
  {
    key: "cloud_storage_usd" as keyof GCPCostData,
    label: "Cloud Storage",
    icon: HardDrive,
    colorClass: "text-emerald-400",
    bgClass: "bg-emerald-500/10",
    barClass: "from-emerald-500 to-teal-500",
  },
  {
    key: "egress_usd" as keyof GCPCostData,
    label: "Network Egress",
    icon: Wifi,
    colorClass: "text-amber-400",
    bgClass: "bg-amber-500/10",
    barClass: "from-amber-500 to-orange-500",
  },
  {
    key: "other_usd" as keyof GCPCostData,
    label: "Other Services",
    icon: MoreHorizontal,
    colorClass: "text-slate-400",
    bgClass: "bg-slate-500/10",
    barClass: "from-slate-500 to-slate-600",
  },
] as const;

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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCosts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/metrics/gcp-costs", { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json: GCPCostData = await res.json();
      setData(json);
    } catch {
      setError("ไม่สามารถโหลดข้อมูลค่าใช้จ่าย GCP ได้");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCosts();
  }, [fetchCosts]);

  return (
    <GlassCard variant="default" glowColor="cyan" className="p-6 space-y-5">
      {/* ── Header ── */}
      <div className="flex items-center justify-between">
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
          {data?.is_mock && (
            <GlassBadge variant="amber">Mock Data</GlassBadge>
          )}
          <button
            id="gcp-cost-refresh-btn"
            onClick={fetchCosts}
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
            ${data.total_usd.toFixed(2)}
          </span>
          <span className="text-slate-400 ml-2 text-sm font-medium">
            USD / month
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
          SERVICE_ITEMS.map(({ key, label, icon: Icon, colorClass, bgClass, barClass }) => {
            const cost = data[key] as number;
            const pct = data.total_usd > 0 ? (cost / data.total_usd) * 100 : 0;

            return (
              <div key={key} className="flex items-center gap-3">
                <div
                  className={`flex-shrink-0 p-1.5 rounded-lg ${bgClass} border border-white/5 ${colorClass}`}
                >
                  <Icon className="h-4 w-4" />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex justify-between text-sm mb-1.5">
                    <span className="text-slate-300 font-medium">{label}</span>
                    <span className="font-bold text-white tabular-nums">
                      ${cost.toFixed(2)}
                    </span>
                  </div>
                  <div className="w-full bg-slate-950/80 rounded-full h-1.5 overflow-hidden border border-white/5">
                    <div
                      className={`h-full rounded-full bg-gradient-to-r ${barClass} transition-all duration-700 ease-out`}
                      style={{ width: `${pct}%` }}
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
