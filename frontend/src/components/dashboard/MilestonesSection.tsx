"use client";

import React from "react";
import useSWR from "swr";
import { GlassCard } from "@/components/ui/GlassCard";
import { GlassBadge } from "@/components/ui/GlassBadge";
import { Lock, Flag, CheckCircle2 } from "lucide-react";

interface MilestoneData {
  target_thb: number;
  current_thb: number;
  is_locked: boolean;
  lock_reason: string | null;
}

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export function MilestonesSection() {
  const { data } = useSWR<MilestoneData>("/api/milestones", fetcher, {
    refreshInterval: 15000,
    revalidateOnFocus: true,
  });

  const milestone = data || {
    target_thb: 10000,
    current_thb: 5140,
    is_locked: false,
    lock_reason: null,
  };

  const progressPercent = Math.min(100, Math.round((milestone.current_thb / milestone.target_thb) * 100));

  return (
    <GlassCard className="p-6 md:p-8">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
            <Flag className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white tracking-tight">Milestone Progress & Donation Lock</h3>
            <p className="text-xs text-zinc-400">Automated kill-switch when target runway is reached</p>
          </div>
        </div>
        <GlassBadge variant={milestone.is_locked ? "danger" : "success"}>
          {milestone.is_locked ? "DONATION LOCKED" : "ACCEPTING DONATIONS"}
        </GlassBadge>
      </div>

      {milestone.is_locked && (
        <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-center gap-3">
          <Lock className="w-5 h-5 flex-shrink-0" />
          <div>
            <strong className="block font-semibold">Donation Lock Active</strong>
            {milestone.lock_reason || "Runway target reached. Further donations are automatically disabled to prevent overfunding."}
          </div>
        </div>
      )}

      <div className="space-y-3">
        <div className="flex justify-between text-sm">
          <span className="text-zinc-400 font-medium">Current Goal Progress</span>
          <span className="text-white font-bold">
            ฿{milestone.current_thb.toLocaleString()} / ฿{milestone.target_thb.toLocaleString()} THB ({progressPercent}%)
          </span>
        </div>

        <div className="w-full h-3 rounded-full bg-white/5 overflow-hidden p-0.5 border border-white/10 relative">
          <div
            className="h-full rounded-full bg-gradient-to-r from-cyan-500 via-blue-500 to-indigo-500 transition-all duration-700 shadow-lg shadow-cyan-500/30"
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        <div className="flex items-center justify-between text-xs text-zinc-500 pt-2">
          <span className="flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            Milestone 1: 90-Day Server Fund
          </span>
          <span>Target: 3 Months Runway</span>
        </div>
      </div>
    </GlassCard>
  );
}
